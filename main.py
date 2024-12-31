import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
from autogpt_modules.tools.plan_action import PlanAction
from autogpt_modules.tools.save_result import SaveResult
from hearing_module.goals import hearing_goals
from utils import dict_to_string
import logging
import json
import traceback

# ロギングの設定を強化
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# OpenAI関連のログを WARNING レベルに設定
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI()
# CORS設定
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Reactアプリのデフォルトポート
    "http://127.0.0.1:5173",
    "http://localhost:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

websocket_manager = WebSocketManager(room_timeout=30)

def create_autogpt_instance(room):
    """AutoGPTインスタンスを作成"""

    if room is None:
        raise ValueError("Room not found")
    
    llm = ChatOpenAI(
        temperature=0, 
        model=os.getenv("BASE_MODEL"), 
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        streaming=True,
        base_url=os.getenv("DEEPSEEK_BASE_URL")
    ).bind(
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
        PlanAction(
            websocket_manager=websocket_manager,
            room_id=room.id
        ),
        SaveResult(
            websocket_manager=websocket_manager,
            room_id=room.id
        ),
        Finish(),
        GoNext()
    ]

    return AutoGPT.from_llm_and_tools(
        ai_name="認知症サポーター",
        ai_role="認知症患者の生活における意思決定支援や不安解消を行う情緒的なケアを行うエージェント",
        tools=tools,
        flag_names=["finish", "go_next", "plan_action", "reply_message"],
        llm=llm,
        room_id=room.id,
        verbose=True,
        websocket_manager=websocket_manager
    )

# 起動時のイベントハンドラ
@app.on_event("startup")
async def startup_event():
    print("Starting up...")

# 終了時のイベントハンドラ
@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down...")
    websocket_manager.cleanup_inactive_rooms()

# WebSocketエンドポイント
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    try:
        logger.info(f"WebSocket connection attempt from user_id: {user_id}")
        logger.debug(f"WebSocket headers: {websocket.headers}")
        logger.debug(f"WebSocket query params: {websocket.query_params}")
        
        room = await websocket_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connected successfully for user_id: {user_id}")
        logger.debug(f"Created room with ID: {room.id}")
        logger.debug(f"Current rooms in manager: {list(websocket_manager._rooms.keys())}")

        logger.debug(f"room: {room}")
        
        logger.debug(f"Creating AutoGPT instance for room ID: {room.id}")
        room.autogpt = create_autogpt_instance(room)
        logger.debug(f"AutoGPT instance created for room: {room.id}")
        logger.debug(f"Rooms after AutoGPT creation: {list(websocket_manager._rooms.keys())}")

        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                logger.debug(f"Received message: {data}")

                if data["type"] == "start_hearing":
                    logger.info(f"Starting hearing session for user: {user_id}")
                    asyncio.create_task(room.autogpt.run(
                        goals=[dict_to_string(goal_dict) for goal_dict in hearing_goals["plan_details"]],
                        common_rule=dict_to_string(hearing_goals["common_rules"]),
                        room_id=room.id,
                    ))
                elif data["type"] == "message":
                    logger.debug(f"Processing message from user {user_id}: {data['data']['content']}")
                    await room.message_manager.add_message(data["data"]["content"], "user")
                    await room.event_manager.add_event("new_message_come", result=data["data"]["content"])
                elif data["type"] == "stamp":
                    logger.debug(f"Processing stamp - Package ID: {data['data']['package_id']}, Sticker ID: {data['data']['sticker_id']}")
                elif data["type"] == "finish":
                    logger.info(f"Finishing session for user: {user_id}")

                    room.autogpt.finish()
                    room.event_manager.add_event("finish_session", result="finish")

                    break

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                await websocket.send_text(json.dumps({
                    "error": "Invalid JSON format",
                    "details": str(e)
                }))
            except WebSocketDisconnect as e:
                logger.error(f"WebSocketDisconnect: code={e.code}, reason={e.reason}")
                return
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                try:
                    await websocket.send_text(json.dumps({
                        "error": "Error processing message",
                        "details": str(e)
                    }))
                except RuntimeError:
                    pass

    except Exception as outer_e:
        logger.error(f"Critical error in WebSocket connection: {outer_e}")
        traceback.print_exc()
    finally:
        logger.info("WebSocket cleanup")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, ws="websockets")