import requests
import json
import time
from utils.logger import get_logger

logger = get_logger(__name__)

class GeminiClient:
    def __init__(self, api_key, generation_config=None):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        cfg = generation_config or {}
        self.score_timeout_sec = int(cfg.get("score_timeout_sec", 12))
        self.generate_timeout_sec = int(cfg.get("generate_timeout_sec", 35))
        self.score_max_retries = int(cfg.get("score_max_retries", 1))
        self.generate_max_retries = int(cfg.get("generate_max_retries", 2))
        self.retry_backoff_sec = int(cfg.get("retry_backoff_sec", 2))

    def _call_gemini(self, model_name, prompt, timeout_sec, max_retries):
        url = f"{self.base_url}/{model_name}:generateContent"
        headers = {'Content-Type': 'application/json'}
        params = {'key': self.api_key}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        for attempt in range(max_retries + 1):
            try:
                http_resp = requests.post(url, params=params, headers=headers, json=payload, timeout=timeout_sec)
                http_resp.raise_for_status()
                resp = http_resp.json()
                if 'candidates' in resp and len(resp['candidates']) > 0:
                    return resp['candidates'][0]['content']['parts'][0]['text']
                logger.error(f"Gemini API returned unexpected format (Model: {model_name}): {json.dumps(resp)}")
                return None
            except requests.exceptions.HTTPError as e:
                logger.error(f"Gemini HTTP error ({model_name}): {e}")
                return None
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    logger.warning(
                        f"Gemini request timeout ({model_name}), retry {attempt + 1}/{max_retries} after backoff."
                    )
                    time.sleep(self.retry_backoff_sec * (attempt + 1))
                    continue
                logger.error(f"Gemini request timeout ({model_name}).")
                return None
            except ValueError as e:
                logger.error(f"Gemini JSON parse error ({model_name}): {e}")
                return None
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(
                        f"Gemini transient error ({model_name}): {e}. retry {attempt + 1}/{max_retries}."
                    )
                    time.sleep(self.retry_backoff_sec * (attempt + 1))
                    continue
                logger.error(f"Network or Parsing Error calling Gemini ({model_name}): {e}")
                return None
        return None

    def score_alpha(self, data_feed):
        """Step 1: Use gemini-3-flash-preview for fast scoring."""
        prompt = f"""Evaluate this information for 'Alpha' (high-value asymmetry and disruptive potential).
        Scale: 0-10.
        Consider these breakthrough dimensions:
        1. 认知反差 (Contrarian Value): Does this challenge current mainstream consensus?
        2. 商业距离 (Time-to-Market): Can this quickly translate to commercial advantage or paradigm shift?
        3. 跨界杠杆 (Cross-domain Impact): Does it combine unexpected fields (e.g., AI x Crypto, AI x Biotech) to unlock new capabilities?
        4. 技术壁垒 (Technical Moat): Is it a fundamental breakthrough or just an incremental tweak?

        Strong negative signals:
        - Event announcements, summit invitations, webinar notices, conference reminders
        - Recruiting posts, community updates, generic opinion essays, policy slogans
        - Product marketing copy without concrete new technical or commercial facts
        - Simple commentary on already-known themes without a new mechanism or signal
        
        Output ONLY the integer score (0-10).
        Input: {data_feed}"""
        return self._call_gemini(
            "gemini-3-flash-preview",
            prompt,
            timeout_sec=self.score_timeout_sec,
            max_retries=self.score_max_retries,
        )

    def generate_alpha(self, data_feed, persona="Yingying"):
        """Step 2: Use gemini-3.1-pro-preview for deep synthesis."""
        prompt = f"""
        Role: {persona}, an Elite Silicon Valley AI/Web3 Analyst.
        Input: {data_feed}
        
        Task:
        请提取Input内容，并严格按照以下5个模块输出。
        必须且只能包含这5个模块名称（带【】）：
        【破局信号】: (一句话概括，高信息密度)
        【Alpha评分】: (0-10分，必须和分数在同一行，且不能换行，例：【Alpha评分】: 8.5分)
        【核心洞察】: (通俗易懂的形象比喻，说明其商业或技术颠覆性)
        【深度推演】: (分析未来几个月带来的改变)
        【信源链接】: (直接提取Input里的URL作为纯文本输出)
        
        Length Ratio & Constraints:
        - 【破局信号】:【核心洞察】:【深度推演】 的字数比例大约为 1 : 2 : 4。
        - 总体字数扩充到之前的1.5倍（总计约 120-150 中文字符）。
        
        Formatting Rules (CRITICAL STRICT):
        - 绝对禁止换行 (NO LINE BREAKS)：整个输出必须是一整段连续的纯文本。模块与模块之间用空格隔开，绝对不允许使用任何换行符 (\\n) 或段落分隔符！
        - 例如：【破局信号】: xxx 【Alpha评分】: x分 【核心洞察】: xxx 【深度推演】: xxx 【信源链接】: url
        - Output MUST be entirely in Chinese (except necessary technical terms and the URL).
        - DO NOT output meta-words like "焦虑" or "Anxiety".
        - DO NOT use Markdown asterisks (**bold**) or special symbols.
        - Tone MUST be restrained, analytical, and specific. Prefer calm institutional language over hype.
        - Avoid exaggerated phrases like "血洗", "降维打击", "歼星舰", "疯狂涌入", "彻底颠覆", "暴力压缩" unless directly supported by the source.
        - If the source is mainly an event notice, generic promotion, or community announcement, do not dramatize it; stay conservative and factual.
        """
        return self._call_gemini(
            "gemini-3.1-pro-preview",
            prompt,
            timeout_sec=self.generate_timeout_sec,
            max_retries=self.generate_max_retries,
        )
