import httpx
from app.config import settings
from sqlalchemy import select
from app.database import async_session as async_session_maker
from app.models.setting import Setting


class DeepSeekService:
    BASE_URL = "https://api.deepseek.com/v1/chat/completions"

    async def _get_api_key(self) -> str:
        try:
            async with async_session_maker() as db:
                result = await db.execute(select(Setting).where(Setting.key == "deepseek_api_key"))
                setting = result.scalar_one_or_none()
                if setting and setting.value:
                    return setting.value
        except Exception:
            pass
        return ""

    async def chat(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        api_key = await self._get_api_key()
        if not api_key:
            return "⚠️ DeepSeek API key not configured. Add it in Settings."

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    self.BASE_URL,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 1000,
                        "temperature": 0.7,
                    },
                )
                if resp.status_code != 200:
                    return f"⚠️ DeepSeek error: {resp.status_code} - {resp.text[:200]}"
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"⚠️ DeepSeek error: {str(e)}"


deepseek_service = DeepSeekService()
