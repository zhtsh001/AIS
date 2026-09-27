import os
from flask import Flask, request, jsonify
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
from dotenv import load_dotenv
from xml.etree import ElementTree as ET

load_dotenv()

app = Flask(__name__)

def _env(*keys, default=""):
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default

# 配置参数
TOKEN = _env("WECHAT_SERVER_TOKEN", "WECOM_SERVER_TOKEN")
ENCODING_AES_KEY = _env("WECHAT_ENCODING_AES_KEY", "WECOM_ENCODING_AES_KEY")
CORP_ID = _env("WECHAT_CORP_ID", "WECOM_CORP_ID")
PORT = int(_env("WECHAT_SERVER_PORT", "WECOM_SERVER_PORT", default="5000"))

if not TOKEN or not ENCODING_AES_KEY or not CORP_ID:
    raise RuntimeError(
        "Missing WECHAT_SERVER_TOKEN/WECOM_SERVER_TOKEN, "
        "WECHAT_ENCODING_AES_KEY/WECOM_ENCODING_AES_KEY, "
        "WECHAT_CORP_ID/WECOM_CORP_ID in environment."
    )

crypto = WeChatCrypto(TOKEN, ENCODING_AES_KEY, CORP_ID)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "corp_id": CORP_ID, "port": PORT})


def _extract_event_type(xml_text):
    try:
        root = ET.fromstring(xml_text)
        info_type = root.findtext("InfoType")
        msg_type = root.findtext("MsgType")
        event = root.findtext("Event")
        return {
            "InfoType": info_type,
            "MsgType": msg_type,
            "Event": event,
        }
    except Exception:
        return {}


@app.route('/wechat', methods=['GET', 'POST'])
def wechat():
    if request.method == 'GET':
        msg_signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        
        try:
            # 解密 echostr
            reply_echostr = crypto.check_signature(
                msg_signature,
                timestamp,
                nonce,
                echostr
            )
            print("✅ 收到微信服务器验证请求，验证成功！")
            return reply_echostr
        except InvalidSignatureException:
            print("❌ 收到微信服务器验证请求，签名错误！")
            return "Invalid Signature", 403

    msg_signature = request.args.get('msg_signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')
    encrypted_body = request.data.decode("utf-8")

    try:
        decrypted_xml = crypto.decrypt_message(
            encrypted_body,
            msg_signature,
            timestamp,
            nonce
        )
        event_info = _extract_event_type(decrypted_xml)
        print(f"📨 收到企微 POST 回调，已解密。event={event_info}")
        # 当前只做验签和观测，不执行业务回复
        return "success"
    except InvalidSignatureException:
        print("❌ 收到企微 POST 回调，但签名错误。")
        return "Invalid Signature", 403
    except Exception as e:
        print(f"❌ 处理企微 POST 回调失败: {e}")
        return "Bad Request", 400

if __name__ == '__main__':
    print(f"🚀 企微回调服务器已在端口 {PORT} 启动...")
    print(f"Token: {TOKEN}")
    app.run(host='0.0.0.0', port=PORT)
