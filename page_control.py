import asyncio
from playwright.async_api import async_playwright
import gradio as gr
from PIL import Image
from io import BytesIO
from datetime import datetime

# 获取二维码并启动扫码检测
async def get_qr_code(state):
    state['scanned'] = "正在打开研发云页面，请稍候..."
    
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    page = await browser.new_page()

    # 保存到 state
    state["playwright"] = pw
    state["browser"] = browser
    state["page"] = page
    state["scanned"] = "等待访问研发云网站"
    state["stop"] = False

    # 保留你的页面地址和判断逻辑
    await page.goto('https://www.srdcloud.cn/')
    iframe_el = page.locator('iframe[title="天翼账户登录"]')
    await iframe_el.wait_for(state='visible', timeout=15000)

    page_bytes = await page.screenshot()
    page_img = Image.open(BytesIO(page_bytes))
    state['page_image'] = page_img

    # 异步等待扫码
    asyncio.create_task(wait_scan(state))

    return

# 异步截图
async def screenshot_loop(state):
    page = state["page"]
    i = 0
    while not state.get("stop"):
        page_bytes = await page.screenshot()
        state['page_image'] = Image.open(BytesIO(page_bytes))
        print(f"已截图 {i+1} 张")
        i += 1
        # 非阻塞
        await asyncio.sleep(1)
        if i >= 60*3:  # 最多截图3分钟
            break
    
    # 循环截图结束，关闭浏览器
    if page:
        await page.close()

# 异步检测扫码状态
async def wait_scan(state):
    page = state.get("page")
    asyncio.create_task(screenshot_loop(state))
    
    try:
        await page.wait_for_url(lambda url: "https://www.srdcloud.cn/user/" in url, timeout=60*3*1000)
        state["scanned"] = "扫码成功，您已经成功登陆。如果需要，请继续进行大模型提问操作，如果不需要，直接关闭浏览器即可。"
    except asyncio.TimeoutError:
        state["scanned"] = "超时，请重新点击获取二维码按钮"
    return 

# 查询状态
def check_status(state):
    return state.get("scanned"), state.get('page_image', None)

# 关闭浏览器
def close_browser(state):
    state["stop"] = True
    state['scanned'] = "等待获取二维码..."
    state['page_image'] = None
    state["playwright"] = None
    state["browser"] = None
    state["page"] = None
    return

# 大模型提问 3次
async def do_llm_chat(state):
    
    if state.get("scanned").find('扫码成功') > -1:
        return gr.Toast("请先点击'访问研发云网站'按钮，扫码成功后才能进行大模型提问", duration=2000)  # 弹 2 秒

    state['scanned'] = "正在自动执行大模型提问..."
    
    # 获取当前时间
    now = datetime.now()
    # 获取今年年份
    year = now.year
    print("今年年份:", year)
    # 获取今天日期（格式：YYYY-MM-DD）
    today = now.date()
    print("今天日期:", today)
    # 如果需要自定义格式
    today_date_str = now.strftime("%m月%d日")
    questions = [
        '今天周几?',
        f'{year}年',
        f'{today_date_str}'
    ]
    
    page = state.get("page")
    if page:
        await page.goto('https://www.srdcloud.cn/smartassist/codefree')
        for q in questions:
            await page.fill('textarea[placeholder="请向CodeFree提问"]', q)
            await page.keyboard.press("Enter")
            await asyncio.sleep(5)
            
        state['scanned'] = "大模型提问已完成，您可以点击'关闭浏览器按钮'，结束本次操作。"
    return

# Gradio 页面
with gr.Blocks(title="研发云登录助手", css="""
        .blue-btn {background-color: blue; color: white;}
        .grey-btn {background-color: grey; color: white;}
        .green-btn {background-color: green; color: white;}
    """) as demo:
    # gr.Markdown("### 点击按钮获取登录二维码")
    state = gr.State(value={})  # 每个用户独立 state
    with gr.Row():
        btn = gr.Button("首先 - 访问研发云网站", scale=1, elem_classes="blue-btn")
        btn_llm = gr.Button("可选 - 进行大模型提问（每月一次）", scale=1, elem_classes="grey-btn")
        btn_quit = gr.Button("最后 - 关闭浏览器",  scale=1, elem_classes="green-btn")
        
    tip = gr.Textbox(label="状态", interactive=False)
    img = gr.Image(type="pil", label="登录二维码", interactive=False)

    btn.click(fn=get_qr_code, inputs=state, outputs=[])
    
    btn_llm.click(fn=do_llm_chat, inputs=state, outputs=[])
    
    btn_quit.click(fn=close_browser, inputs=state, outputs=[])

    timer = gr.Timer(value=1.0)  # 每秒触发
    timer.tick(fn=check_status, inputs=state, outputs=[tip, img])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=6006)