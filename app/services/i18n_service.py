from app.translations import translations


class I18nService:
    _default_lang = "ar"

    def t(self, key: str, lang: str | None = None) -> str:
        lang = lang or self._default_lang
        return translations.get(lang, {}).get(key, translations.get("ar", {}).get(key, key))

    def set_language(self, lang: str):
        if lang in translations:
            self._default_lang = lang

    def get_supported_languages(self) -> list[str]:
        return list(translations.keys())


i18n = I18nService()
