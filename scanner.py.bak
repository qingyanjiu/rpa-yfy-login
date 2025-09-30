import asyncio
from playwright.async_api import async_playwright
import gradio as gr
from PIL import Image
from io import BytesIO

# 获取二维码并启动扫码检测
async def get_qr_code(state):
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    page = await browser.new_page()

    # 保存到 state
    state["playwright"] = pw
    state["browser"] = browser
    state["page"] = page
    state["scanned"] = "等待扫码"

    # 保留你的页面地址和判断逻辑
    await page.goto('https://www.srdcloud.cn/')
    iframe_el = page.locator('iframe[title="天翼账户登录"]')
    await iframe_el.wait_for(state='visible', timeout=15000)
    iframe_src = await iframe_el.get_attribute('src')
    await page.goto(iframe_src)

    qr = page.locator('#j-qrcodeImage')
    await qr.wait_for(state='visible', timeout=15000)
    qr_bytes = await qr.screenshot()
    qr_image = Image.open(BytesIO(qr_bytes))

    # 异步等待扫码
    asyncio.create_task(wait_scan(state))

    return qr_image, state

# 异步检测扫码状态
async def wait_scan(state):
    page = state.get("page")
    try:
        await page.wait_for_url(lambda url: "https://www.srdcloud.cn/" in url, timeout=60*3*1000)
        state["scanned"] = "扫码成功，您已经成功登陆，直接关闭该页面即可"
    except asyncio.TimeoutError:
        state["scanned"] = "超时，请重新点击获取二维码按钮"
    finally:
        browser = state.get("browser")
        pw = state.get("playwright")
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

# 查询状态
def check_status(state):
    return state.get("scanned", "等待获取二维码...")

# Gradio 页面
with gr.Blocks(title="扫码登录") as demo:
    gr.Markdown("### 点击按钮获取登录二维码")
    state = gr.State(value={})  # 每个用户独立 state
    btn = gr.Button("获取二维码")
    img = gr.Image(type="pil", label="登录二维码", interactive=False)
    tip = gr.Textbox(label="状态", interactive=False)

    btn.click(fn=get_qr_code, inputs=state, outputs=[img, state])

    timer = gr.Timer(value=1.0)  # 每秒触发
    timer.tick(fn=check_status, inputs=state, outputs=tip)

if __name__ == "__main__":
    demo.launch()