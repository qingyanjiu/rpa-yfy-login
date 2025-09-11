import asyncio
import websockets
import json
import uuid
import random
from tasks_state import TaskState

WS_URL = "wss://www.srdcloud.cn/websocket/peerAppgw"

class WSClient:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.heartbeat_task = None
        self.channel_id = None
        self.task_state = TaskState()

    async def connect_once(self):
        """
        用户调用接口时连接服务器（只尝试一次）
        """
        if self.connected:
            return  # 已经连接
        self.ws = await websockets.connect("wss://www.srdcloud.cn/websocket/peerAppgw")
        self.connected = True
        print("✅ WebSocket 已连接（按需）")

        # 启动心跳
        if not self.heartbeat_task or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self.heartbeat())

    async def heartbeat(self):
        """
        定期发送客户端心跳
        """
        while self.connected:
            try:
                await asyncio.sleep(18 + random.randint(0, 4))
                heartbeat_msg = {"messageName": "ClientHeartbeat"}
                await self.ws.send(f"<WBChannel>{json.dumps(heartbeat_msg)}</WBChannel>")
                print("💓 发送心跳")
            except Exception as e:
                print("⚠️ 心跳失败:", e)
                break

    async def register_channel(self):
        """
        注册通道
        """
        register_msg = {
            "messageName": "RegisterChannel",
            "context": {
                "messageName": "RegisterChannel",
                "appGId": "aicode",
                "invokerId": "306177",
                "version": "1.6.0",
                "apiKey": "22fe13ed-46c4-4f2e-9b58-5c0d3e66a21e"
            }
        }
        await self.ws.send(f"<WBChannel>{json.dumps(register_msg)}</WBChannel>")

        while True:
            resp_text = await self.ws.recv()
            resp = self.parse_wbchannel(resp_text)
            if resp.get("messageName") == "RegisterChannel_resp":
                self.channel_id = resp["context"]["channelId"]
                print("✅ 通道注册成功:", self.channel_id)
                break

    async def send_user_activity(self):
        if not self.channel_id:
            return None

        req_id = str(uuid.uuid4())
        message = {
            "messageName": "UserActivityNotify",
            "context": {
                "messageName": "UserActivityNotify",
                "reqId": req_id,
                "invokerId": "306177",
                "version": "1.6.0",
                "apiKey": "22fe13ed-46c4-4f2e-9b58-5c0d3e66a21e",
                "channelId": self.channel_id
            },
            "payload": {
                "client": {
                    "platform": "windows-x64",
                    "type": "vscode",
                    "version": "1.100.2",
                    "pluginVersion": "1.6.0"
                },
                "activityType": "code_display",
                "service": "codegen",
                "lines": 1,
                "count": 1
            }
        }

        await self.ws.send(f"<WBChannel>{json.dumps(message)}</WBChannel>")

        # 等待服务器响应
        while True:
            resp_text = await self.ws.recv()
            resp = self.parse_wbchannel(resp_text)
            if resp.get("messageName") not in ["ServerHeartbeat"]:
                return resp

    async def send_user_activity_loop(self, total: int, task_id: str):
        """
        循环发送消息，每条等待响应
        """
        self.task_state.create_task(task_id, total)
        for i in range(total):
            if not self.connected:
                print("❌ WebSocket 未连接，终止任务")
                break
            try:
                await self.send_user_activity()
                self.task_state.update_task(task_id, i + 1)
                print(f"🔄 第{i+1}/{total}条消息发送完成")
            except Exception as e:
                print("⚠️ 消息发送失败:", e)
                break
        self.task_state.finish_task(task_id)
        print("🎉 任务完成")

    def parse_wbchannel(self, raw_text):
        try:
            return json.loads(raw_text.replace("<WBChannel>", "").replace("</WBChannel>", ""))
        except:
            return {}