import httpx
import logging
from ..config import settings

logger = logging.getLogger(__name__)


async def exchange_github_code(code: str) -> str:
    """用GitHub授权码换取access_token"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise ValueError(f"GitHub OAuth error: {data.get('error_description', data['error'])}")

        return data["access_token"]


async def get_github_user_info(access_token: str) -> dict:
    """从GitHub API获取用户信息"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        user_data = resp.json()

        email = user_data.get("email")

        # GitHub用户可能隐藏了邮箱，需要从/user/emails接口获取
        if not email:
            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=10.0,
            )
            email_resp.raise_for_status()
            emails = email_resp.json()
            primary = next((e for e in emails if e.get("primary")), None)
            if primary:
                email = primary["email"]
            elif emails:
                email = emails[0]["email"]
            else:
                raise ValueError("无法获取GitHub用户邮箱")

        return {
            "github_id": str(user_data["id"]),
            "email": email,
            "name": user_data.get("name") or user_data.get("login", "GitHub User"),
            "avatar_url": user_data.get("avatar_url"),
        }
