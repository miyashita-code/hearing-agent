import asyncio
from fastapi import FastAPI
from fastapi_socketio import SocketManager
from autogpt_modules.communication import WebSocketManager
from autogpt_modules.core import AutoGPT
from autogpt_modules.tools import (
    ReplyMessage,
    ReplyMessageWithStamp,
    Wait,
    Finish,
    GoNext
)
import os
from datetime import datetime
from langchain_openai import ChatOpenAI
from autogpt_modules.core.custom_congif import MODEL
from hearing_module.goals import hearing_goals
from utils import dict_to_string
app = FastAPI()
# Socket.IOマネージャーの設定を追加
sio = SocketManager(app=app, mount_location='', socketio_path='socket.io')
websocket_manager = WebSocketManager()
websocket_manager.set_socketio(sio)  # Socket.IOインスタンスを設定

def create_autogpt_instance(room):
    """AutoGPTインスタンスを作成"""
    llm = ChatOpenAI(temperature=0, model=MODEL).bind(
        response_format={"type": "json_object"}
    )

    tools = [
        ReplyMessage(
            websocket_manager=websocket_manager,
            room_id=room.id
        ),
        ReplyMessageWithStamp(
            websocket_manager=websocket_manager,
            room_id=room.id
        ),
        Wait(
            websocket_manager=websocket_manager,
            event_manager=room.event_manager,
            room_id=room.id
        ),
        Finish(),
        GoNext()
    ]

    return AutoGPT.from_llm_and_tools(
        ai_name="認知症サポーター",
        ai_role="認知症患者の生活における意思決定支援や不安解消を行う情緒的なケアを行うエージェント",
        tools=tools,
        llm=llm,
        get_chat_history=room.message_manager.get_chat_history,
        get_event_history=room.event_manager.get_event_history,
        verbose=False,
        event_manager=room.event_manager,
        message_manager=room.message_manager
    )

@sio.on('connect')
async def handle_connect(sid, environ, auth):
    user_id = environ['HTTP_USER_ID']
    room = websocket_manager.get_or_create_room(user_id)
    room.sid = sid
    await sio.enter_room(sid, room.id)
    room.autogpt = create_autogpt_instance(room)
    print(f"Client connected: {user_id} (Room: {room.id})")

    # AutoGPTを実行
    asyncio.create_task(room.autogpt.run(
        goals=[dict_to_string(goal_dict) for goal_dict in hearing_goals["plan_details"]],
        common_rule=dict_to_string(hearing_goals["common_rules"])
    ))

@sio.on('message')
async def handle_message(sid, data):
    room = websocket_manager.get_room_by_sid(sid)
    if room:
        # ユーザーからのメッセージを追加（message_historyへの追加）
        await room.message_manager.add_message(data, "user")
        await room.event_manager.add_event("new_message_come", result=data)


@sio.on('disconnect')
async def handle_disconnect(sid):
    room = websocket_manager.get_room_by_sid(sid)
    if room:
        await websocket_manager.on_disconnect(room.id)
        print("connection closed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
