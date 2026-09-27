import os
import re
import requests
import json
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

class AISCore:
    def __init__(self, corp_id, corp_secret, agent_id):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.access_token = None
        self.token_expiry = 0

    def get_access_token(self):
        """Fetch Enterprise WeChat Access Token."""
        if self.access_token and self.token_expiry > datetime.now().timestamp():
            return self.access_token
        
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
            resp = requests.get(url, timeout=10).json()
            if resp.get("errcode") == 0:
                self.access_token = resp["access_token"]
                self.token_expiry = datetime.now().timestamp() + resp["expires_in"] - 60
                return self.access_token
            else:
                logger.error(f"Failed to get WeChat token: {resp}")
                return None
        except Exception as e:
            logger.error(f"Network error fetching WeChat token: {e}")
            return None

    def safety_filter(self, text):
        """
        Critical Guardrail: Filter crypto speculation and sensitive terms.
        """
        # Forbidden patterns (pumps, speculative phrases). "Token" is explicitly ALLOWED.
        forbidden = [
            r"buy \$?\w+", r"pump and dump", r"100x gem", r"moon soon",
            r"airdrop alert", r"presale", r"initial coin offering",
        ]
        for pattern in forbidden:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Safety filter triggered for pattern: {pattern}")
                return None # Silently drop the message
        return text

    def send_text_with_links(self, user_ids, text):
        """
        Send a pure text message with blue clickable links (Enterprise WeChat format).
        Format: [Link Title](https://example.com) will be rendered as blue text in WeCom.
        """
        token = self.get_access_token()
        if not token:
            logger.error("Skipping WeChat send: No access token available.")
            return {"errcode": -1, "errmsg": "token acquisition failed"}

        send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        
        # Apply safety filter
        safe_text = self.safety_filter(text)
        if not safe_text:
            return {"errcode": 888, "errmsg": "silently dropped due to safety filter"}

        payload = {
            "touser": "|".join(user_ids),
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": safe_text
            },
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 0
        }
        
        try:
            resp = requests.post(send_url, json=payload, timeout=10).json()
            if resp.get('errcode') != 0:
                logger.error(f"WeChat message send failed: {resp}")
            return resp
        except Exception as e:
            logger.error(f"Network error sending WeChat message: {e}")
            return {"errcode": -1, "errmsg": f"network error: {e}"}

