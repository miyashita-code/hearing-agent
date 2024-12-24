import asyncio
import socketio
import json
from datetime import datetime
import argparse
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

class DebugClient:
    def __init__(self, uri: str, user_id: str):
        self.uri = uri
        self.user_id = user_id
        self.session = PromptSession()
        self.sio = socketio.AsyncClient()
        
        # Socket.IOイベントハンドラの設定
        @self.sio.event
        async def connect():
            print(f"Connected to {self.uri}")

        @self.sio.event
        async def disconnect():
            print("\nDisconnected from server")

        @self.sio.event
        async def message(data):
            try:
                if isinstance(data, dict):
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Received:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Received: {data}")
            except Exception as e:
                print(f"\nError parsing message: {e}")

    async def connect(self):
        """サーバーに接続"""
        try:
            await self.sio.connect(
                self.uri,
                headers={'User-ID': self.user_id},
                wait_timeout=10,
                socketio_path='socket.io'
            )
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    async def send_message(self, message: str):
        """メッセージ送信"""
        try:
            await self.sio.emit('message', message)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sent: {message}")
        except Exception as e:
            print(f"Failed to send message: {e}")

    async def input_loop(self):
        """ユーザー入力ループ"""
        while True:
            try:
                with patch_stdout():
                    message = await self.session.prompt_async("\nEnter message (or 'quit' to exit): ")
                
                if message.lower() == 'quit':
                    break
                    
                await self.send_message(message)
            except (KeyboardInterrupt, EOFError):
                break

    async def run(self):
        """メインループ"""
        if not await self.connect():
            return

        try:
            await self.input_loop()
        finally:
            await self.sio.disconnect()

def main():
    parser = argparse.ArgumentParser(description='Debug Socket.IO Client')
    parser.add_argument('--uri', default='http://localhost:8000', help='Socket.IO server URI')
    parser.add_argument('--user-id', default='debug_user', help='User ID for the session')
    args = parser.parse_args()

    client = DebugClient(args.uri, args.user_id)
    print("\n"*50)
    
    try:
        asyncio.run(client.run())
        
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 