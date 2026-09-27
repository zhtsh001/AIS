import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

CORP_ID = os.getenv('WECHAT_CORP_ID')
SECRET = os.getenv('WECHAT_SECRET')
AGENT_ID = os.getenv('WECHAT_AGENT_ID')

def get_access_token():
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={SECRET}"
    response = requests.get(url)
    data = response.json()
    return data.get('access_token')

def send_text_message(access_token, content):
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    payload = {
        "touser": "@all",
        "msgtype": "text",
        "agentid": int(AGENT_ID),
        "text": {
            "content": content
        }
    }
    response = requests.post(url, json=payload)
    return response.json()

if __name__ == "__main__":
    token = get_access_token()
    if token:
        # 纯文本排版测试，使用 Emoji 和换行符模拟结构
        report = """🔥 【AIS 每日内参】2026-03-20

💡 核心提要：
1. 马斯克深夜确认 FSD v13 核心架构大改。
2. 以太坊 L2 排序器出现重大漏洞。

➖➖➖➖➖➖➖➖
🚀 Alpha 1: 特斯拉彻底放弃 Transformer？
【源头】X (Twitter) @elonmusk
【Yingying 研判】
马斯克暗示下一代 FSD 将采用全新的状态空间模型 (SSM) 如 Mamba架构。这意味着当前基于 Transformer 的端到端智驾路线可能遇到算力墙。
👉 商业影响：直接利空现有的 Transformer 算力芯片供应商，利好边缘计算和高效能推理芯片初创公司。

➖➖➖➖➖➖➖➖
⚠️ 提示：更多深度研判，请每天早 08:08 锁定本对话框。
<a href="https://github.com">点击这里查看完整技术文档</a>"""
        
        res = send_text_message(token, report)
        print("发送纯文本测试:", res)
