from fastapi import FastAPI
import asyncio
import uuid
from ws_client import WSClient

app = FastAPI()
ws_client = WSClient()

# 单用户锁
task_lock = asyncio.Lock()
current_task_id = None

@app.post("/start_task")
async def start_task(count: int = 1000):
    global current_task_id

    if task_lock.locked():
        return {"error": "WebSocket 正在被占用，请稍后再试"}

    # 获取锁
    await task_lock.acquire()
    task_id = str(uuid.uuid4())
    current_task_id = task_id

    # 启动后台协程执行任务
    asyncio.create_task(run_task(task_id, count))
    return {"task_id": task_id, "status": "started"}

async def run_task(task_id: str, count: int):
    global current_task_id

    try:
        # 连接 WebSocket
        try:
            await ws_client.connect_once()  # 只连接一次，不循环重连
        except Exception as e:
            print("❌ WebSocket 连接失败:", e)
            return  # 连接失败直接退出，锁会在 finally 释放

        # 注册通道
        await ws_client.register_channel()

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