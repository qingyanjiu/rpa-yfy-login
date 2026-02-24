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
                        "url": "http://103.172.135.153:18888/final.jpg"
                    }
                },
                {
                    "type": "text",
                    "text": "请描述这张图片内容。"
                }
            ]
        }
    ]
}

response = requests.post(API_URL, json=payload_url, headers=headers)
print("== 识别结果（图片URL） ==")
print(response.json())
