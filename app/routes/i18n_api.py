from fastapi import APIRouter, Query
from app.services.i18n_service import i18n

router = APIRouter(prefix="/api/i18n", tags=["i18n"])


@router.get("/strings")
async def get_strings(lang: str = Query("ar")):
    from app.translations import translations
    return translations.get(lang, translations.get("ar", {}))
