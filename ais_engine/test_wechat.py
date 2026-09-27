import os
import requests
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

CORP_ID = os.getenv('WECHAT_CORP_ID')
SECRET = os.getenv('WECHAT_SECRET')
AGENT_ID = os.getenv('WECHAT_AGENT_ID')

def get_access_token():
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={SECRET}"
    response = requests.get(url)
    data = response.json()
    if data.get('errcode') == 0:
        return data.get('access_token')
    else:
        print(f"❌ 获取 Access Token 失败: {data}")
        return None

def send_markdown_message(access_token):
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    
    payload = {
        "touser": "@all",
        "msgtype": "markdown",
        "agentid": int(AGENT_ID),
        "markdown": {
            "content": "# 🚀 Alpha Intelligence System 初始化成功\n\n> 你的私人情报官 Yingying 已上线。\n\n**当前状态**: 🟢 API 连接正常\n**核心模型**: Gemini 3.1 Pro\n**部署节点**: Tristan's Mac mini\n\n准备好接收第一份 **[顶级认知 Alpha]** 了吗？"
        }
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    if data.get('errcode') == 0:
        print("✅ 消息发送成功！请检查你的企业微信。")
    else:
        print(f"❌ 消息发送失败: {data}")

if __name__ == "__main__":
    print("正在测试企业微信 API 连接...")
    token = get_access_token()
    if token:
        print("✅ 成功获取 Access Token")
        send_markdown_message(token)
