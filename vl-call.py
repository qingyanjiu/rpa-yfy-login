import requests
import base64

# —— 配置 —— #
API_KEY = "sk-mzwqslirxtrhdtcdwqpdizesufygfocxjckbpehzslsrtass"
MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct"   # 或你想用的其他 Qwen3-VL 模型
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# —— 选项1：用图片 URL —— #
payload_url = {
    "model": MODEL_NAME,
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        # 这是在线图片地址
                        "url": "http://107.173.83.242:35555/ComfyUI_00022_.png"
                    }
                },
                {
                    "type": "text",
                    "text": "请详细描述这张图片内容，包括环境，人物穿着，姿势，表情细节，光影等，但不要对图片整体氛围做臆测或者总结"
                }
            ]
        }
    ]
}

response = requests.post(API_URL, json=payload_url, headers=headers)
print("== 识别结果（图片URL） ==")
print(response.json())
