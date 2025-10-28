import json
import asyncio
import websockets
import uuid
from asyncio import Queue

from tasks_state import TaskState

class WSClient:
  def __init__(self, url, session_id: str = '', invoke_id: str = '335793'):
    self.url = url
    self.ws = None
    self.connected = False
    self.api_key = None
    self.channel_id = None
    # 登录的用户id
    self.invoke_id = invoke_id
    # 登录的用户会话id
    self.session_id = session_id
    self.heartbeat_task = None
    # 调用接口时传入
    self.session_id = None
    self.task_state = TaskState()
    self.message_queue = Queue()

  async def connect_and_run(self, task_lock):
    try:
      self.ws = await websockets.connect(self.url)
      self.connected = True
      print("✅ WebSocket 已连接")

      # RegisterChannel
      await self.register_channel()

      # GetUserApiKey
      await self.get_user_api_key()

      # 启动心跳
      self.heartbeat_task = asyncio.create_task(self.send_heartbeat())
      # 启动接收循环
      asyncio.create_task(self.listen(task_lock))
    except Exception as e:
      print("❌ WebSocket 连接失败:", e)
      self.connected = False

  async def register_channel(self):
    msg = {
      "messageName": "RegisterChannel",
      "context": {
        "messageName": "RegisterChannel",
        "appGId": "aicode",
        "invokerId": self.invoke_id,
        "version": "1.6.0",
        "sessionId": f"{self.session_id}" # 这里先随便传，服务器会在GetUserApiKey_resp里返回正确的
      }
    }
    await self.send(msg)
    print(f"📡 RegisterChannel 已发送")
    # 等待响应
    while True:
      resp = await self.ws.recv()
      resp_str = self.parse_wbchannel(resp)
      if "RegisterChannel_resp" in resp_str:
        data = json.loads(resp_str)
        self.channel_id = data["context"]["channelId"]
        print("🔑 拿到 channelId:", self.channel_id)
        break
      else:
        print("忽略非 GetUserApiKey_resp 消息")

  async def get_user_api_key(self):
    req_id = str(uuid.uuid4())
    msg = {
      "messageName": "GetUserApiKey",
      "context": {
        "messageName": "GetUserApiKey",
        "reqId": req_id,
        "invokerId": "335793",
        "sessionId": self.session_id, # 用调用接口传进来的sessionId
        "version": "1.6.0"
      },
      "payload": {
        "clientType": "vscode",
        "clientVersion": "1.100.2",
        "clientPlatform": "windows-x64",
        "gitUrls": [],
        "pluginVersion": "1.6.0"
      }
    }
    await self.send(msg)
    print("📡 GetUserApiKey 已发送")
    # 等待响应
    while True:
      resp = await self.ws.recv()
      resp_str = self.parse_wbchannel(resp)
      if "GetUserApiKey_resp" in resp_str:
        data = json.loads(resp_str)
        self.api_key = data["payload"]["apiKey"]
        print("🔑 拿到 apiKey:", self.api_key)
        break
      else:
        print("忽略非 GetUserApiKey_resp 消息")

  async def send_heartbeat(self):
    while self.connected:
      await self.send({"messageName": "ClientHeartbeat"})
      await asyncio.sleep(10)

  async def send(self, data):
    if self.ws:
      payload = "<WBChannel>" + json.dumps(data, ensure_ascii=False) + "</WBChannel>"
      await self.ws.send(payload)

  async def listen(self, task_lock):
    try:
      async for message in self.ws:
        print("📩 收到:", message)
        await self.message_queue.put(message)
        meesage_text = self.parse_wbchannel(message)
        if "ServerHeartbeat" in meesage_text:
          await self.send({"messageName": "ClientHeartbeatResponse"})
        elif "Closed" in meesage_text:
          print("⚠️ ，准备关闭 WebSocket client 连接...")
          await self.close()
    except websockets.ConnectionClosed:
      print("⚠️ WebSocket 连接被断开，准备关闭 WebSocket client 连接...")
      await self.close()
    finally:
      print("🔌 监听结束，准备关闭 WebSocket client 连接...")
      await asyncio.sleep(10)
      await self.close()
      if task_lock.locked():
        task_lock.release()
        print("锁已释放")

  # 发送代码生成请求
  async def send_user_activity(self, line):
    if not self.channel_id:
      return None

    req_id = str(uuid.uuid4())
    message = {
      "messageName": "UserActivityNotify",
      "context": {
        "messageName": "UserActivityNotify",
        "reqId": req_id,
        "invokerId": f"{self.invoke_id}",
        "version": "1.6.0",
        "apiKey": f"{self.api_key}",
        "channelId": self.channel_id
      },
      "payload": {
        "client": {
          "platform": "windows-x64",
          "type": "vscode",
          "version": "1.100.2",
          "pluginVersion": "1.6.0",
          "projectName": "scan"
        },
        "activityType": "code_display",
        "service": "codegen",
        "lines": line,
        "count": 1
      }
    }

    await self.ws.send(f"<WBChannel>{json.dumps(message)}</WBChannel>")

    # 等待服务器响应
    while True:
      # 从队列取
      resp_text = await self.message_queue.get() 
      resp = json.loads(self.parse_wbchannel(resp_text))
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
        await self.send_user_activity(i + 1)
        self.task_state.update_task(task_id, i + 1)
        print(f"🔄 第{i+1}/{total}条消息发送完成")
      except Exception as e:
        print("⚠️ 消息发送失败:", e)
        break
    self.task_state.finish_task(task_id)
    print("🎉 任务完成")

  def parse_wbchannel(self, raw_text):
    try:
      return raw_text.replace("<WBChannel>", "").replace("</WBChannel>", "")
    except:
      return {}

  async def close(self):
    if self.ws:
      await self.ws.close()
      print("🔌 WebSocket client 连接已关闭")
    self.connected = False
