from google import genai
from google.genai import types
from app.config import settings
from sqlalchemy import select
from app.database import async_session as async_session_maker
from app.models.setting import Setting

SYSTEM_PROMPT = """أنت مساعد ذكي لنظام الوسيط لإدارة العقارات. أنت تتحدث العربية بشكل أساسي ولكنك تفهم الإنجليزية أيضاً.

مهامك:
- مساعدة السماسرة في إدارة جهات الاتصال والعقارات والصفقات والمهام
- البحث في قاعدة البيانات
- إنشاء تقارير Excel
- حساب العمولات
- إدارة التذكيرات
- الإجابة عن أسئلة حول السوق العقاري

قواعد مهمة:
1. لا تقدم نصائح قانونية أو مالية رسمية
2. إذا طلب المستخدم شيئاً خارج نطاق إدارة العقارات، أخبره بلطف أن هذا خارج تخصصك
3. كن مختصراً ومباشراً - السماسرة مشغولون
4. استخدم اللغة العربية بشكل أساسي، unless the user speaks English"""


class GeminiService:
    def __init__(self):
        self._client = None
        self._current_key = ""

    async def _get_setting(self, key: str) -> str:
        try:
            async with async_session_maker() as db:
                result = await db.execute(select(Setting).where(Setting.key == key))
                setting = result.scalar_one_or_none()
                if setting and setting.value:
                    return setting.value
        except Exception:
            pass
        return ""

    async def _get_api_key(self) -> str:
        db_key = await self._get_setting("gemini_api_key")
        if db_key:
            return db_key
        if settings.gemini_api_key:
            return settings.gemini_api_key
        return ""

    async def _get_model(self) -> str:
        db_model = await self._get_setting("gemini_model")
        if db_model:
            return db_model
        return settings.gemini_model

    def _ensure_client(self, api_key: str):
        if not api_key:
            return None
        if api_key != self._current_key:
            self._client = genai.Client(api_key=api_key)
            self._current_key = api_key
        return self._client

    async def chat(self, message: str, history: list[dict] | None = None) -> str:
        api_key = await self._get_api_key()
        client = self._ensure_client(api_key)
        if not client:
            return "⚠️ Gemini API key not configured. Add it in Settings."

        try:
            contents = []
            if history:
                for msg in history[-10:]:
                    contents.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})

            contents.append({"role": "user", "parts": [{"text": message}]})

            model = await self._get_model()
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1000,
                temperature=0.7,
            )

            response = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            return response.text.strip()
        except Exception as e:
            return f"⚠️ Error: {str(e)}"

    async def analyze_image(self, image_bytes: bytes, mime_type: str, prompt: str = "Describe this image") -> str:
        api_key = await self._get_api_key()
        client = self._ensure_client(api_key)
        if not client:
            return "⚠️ Gemini API key not configured."
        try:
            import base64
            img_b64 = base64.b64encode(image_bytes).decode()
            # Use image-capable model: fall back to 2.0-flash which definitely supports vision
            model = "gemini-2.0-flash"
            response = await client.aio.models.generate_content(
                model=model,
                contents=[
                    {"role": "user", "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": img_b64}},
                        {"text": prompt}
                    ]}
                ],
                config=types.GenerateContentConfig(max_output_tokens=1000, temperature=0.7),
            )
            return response.text.strip()
        except Exception as e:
            return f"⚠️ Error analyzing image: {str(e)}"


gemini_service = GeminiService()
