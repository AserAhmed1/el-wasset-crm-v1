window.i18n = {
    _lang: localStorage.getItem('lang') || 'ar',
    _cache: {},

    async init() {
        // Sync lang to cookie for server-side rendering
        document.cookie = 'lang=' + this._lang + '; path=/; max-age=31536000';
        const resp = await fetch('/api/i18n/strings?lang=' + this._lang);
        this._cache = await resp.json();
        this.apply();
    },

    t(key) {
        return this._cache[key] || key;
    },

    async setLang(lang) {
        this._lang = lang;
        localStorage.setItem('lang', lang);
        await this.init();
        document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
        document.documentElement.lang = lang;
    },

    apply() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            el.textContent = this.t(el.getAttribute('data-i18n'));
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            el.placeholder = this.t(el.getAttribute('data-i18n-placeholder'));
        });
    },

    getLang() { return this._lang; },
    isRTL() { return this._lang === 'ar'; },
};
