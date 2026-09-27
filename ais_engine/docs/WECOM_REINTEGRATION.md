# WeCom Reintegration Notes

## Two Separate Things

There are two different pieces in the WeCom setup:

1. Callback server URL
- Used for message/event callbacks and URL verification.
- Requires a public HTTPS URL.
- Our local callback server is `wechat_server.py`.
- A tunnel such as ngrok can expose it publicly.

2. Trusted IP
- Used for outbound API calls such as `gettoken` and `message/send`.
- WeCom checks the real egress public IP of the machine making the API call.
- A callback URL or tunnel domain does not replace the trusted IP requirement.

## Local Callback Server

Our callback server now supports:
- `GET /wechat` for WeCom URL verification
- `POST /wechat` for encrypted callback receive/decrypt
- `GET /health` for local health checks

Relevant file:
- `wechat_server.py`

## Required Environment Variables

Callback server:
- `WECOM_SERVER_TOKEN`
- `WECOM_ENCODING_AES_KEY`
- `WECOM_CORP_ID`
- Optional: `WECOM_SERVER_PORT`

Outbound send:
- `WECOM_CORP_ID`
- `WECOM_SECRET`
- `WECOM_AGENT_ID`
- `WECOM_USER_ID`
- `WECHAT_PUSH_ENABLED=1`

## Recommended Setup Path

1. Configure the new WeCom custom app.
2. Prepare callback token and EncodingAESKey in the app settings.
3. Run `wechat_server.py` locally.
4. Expose it with a public HTTPS tunnel if needed.
5. Fill the callback URL in WeCom, for example:
   `https://your-public-domain/wechat`
6. Complete URL verification.
7. Configure the trusted IP to the actual outbound public IP of the machine or server that will call WeCom APIs.
8. Run `test_wechat.py` or the push scripts to verify outbound send.

## Important Practical Note

If AIS runs from a local home/office machine and its public IP changes, trusted IP maintenance becomes fragile.
For production, a fixed-IP cloud host or a stable egress proxy is the safer long-term option.
