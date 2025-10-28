from fastapi import FastAPI
import asyncio
import uuid
from ws_client import WSClient

# uvicorn main:app --reload --host 0.0.0.0 --port 8000

app = FastAPI()
ws_client = WSClient('wss://www.srdcloud.cn/websocket/peerAppgw')

# 单用户锁
task_lock = asyncio.Lock()
current_task_id = None

@app.post("/start_task")
async def start_task(count: int = 5, session_id: str = ""):
  global current_task_id

  if task_lock.locked():
    return {"error": "WebSocket 正在被占用，请稍后再试"}

  # 获取锁
  await task_lock.acquire()
  ws_client.session_id = session_id
  task_id = str(uuid.uuid4())
  current_task_id = task_id

  # 启动后台协程执行任务
  asyncio.create_task(run_task(task_id, count, session_id))
  return {"task_id": task_id, "status": "started"}

async def run_task(task_id: str, count: int, session_id: str):
  global current_task_id
  try:

    # 注册通道
    await ws_client.connect_and_run(task_lock)

    # 循环发送消息
    await ws_client.send_user_activity_loop(count, task_id)

  except Exception as e:
    print("⚠️ 任务异常:", e)

  finally:
    # 释放锁
    if task_lock.locked():
      task_lock.release()
    current_task_id = None
    print("🔓 任务完成，锁已释放")

@app.get("/task_status")
async def task_status():
  if not current_task_id:
    return {"status": "idle", "task_id": None}
  state = ws_client.task_state.get_task(current_task_id)
  return state if state else {"status": "running", "task_id": current_task_id}

@app.post("/logout")
async def logout():
  """
  用户退出：关闭 WS 连接、释放锁
  """
  global current_task_id

  await ws_client.close()

  # 如果有任务在跑，强制释放锁
  if task_lock.locked():
    task_lock.release()
    print("🔓 锁已手动释放")

  current_task_id = None
  return {"status": "logged_out"}
