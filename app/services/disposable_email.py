import httpx
from app.config import settings


class DisposableEmailChecker:
    def __init__(self):
        self._disposable_domains: set[str] = set()
        self._loaded = False

    async def load_blocklist(self):
        if self._loaded:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(settings.disposable_domains_url)
                if resp.status_code == 200:
                    text = resp.text
                    for line in text.splitlines():
                        line = line.strip().lower()
                        if line and not line.startswith("#"):
                            self._disposable_domains.add(line)
            self._loaded = True
        except Exception:
            self._disposable_domains = {
                "mailinator.com", "guerrillamail.com", "tempmail.com",
                "10minutemail.com", "throwaway.email", "yopmail.com",
                "maildrop.cc", "trashmail.com", "temp-mail.org",
            }
            self._loaded = True

    def is_disposable(self, email: str) -> bool:
        if "@" not in email:
            return True
        domain = email.split("@", 1)[1].strip().lower()
        if not domain or "." not in domain:
            return True
        return domain in self._disposable_domains
