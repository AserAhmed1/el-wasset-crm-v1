from datetime import datetime, timedelta, timezone


class RateLimiter:
    def __init__(self):
        self._login_attempts: dict[str, list[datetime]] = {}
        self._registration_ips: dict[str, int] = {}
        self._max_attempts = 5
        self._lockout_minutes = 15
        self._max_registrations = 3

    def check_login(self, identifier: str) -> tuple[bool, int]:
        now = datetime.now(timezone.utc)
        if identifier in self._login_attempts:
            self._login_attempts[identifier] = [
                t for t in self._login_attempts[identifier]
                if t > now - timedelta(minutes=self._lockout_minutes)
            ]
            if len(self._login_attempts[identifier]) >= self._max_attempts:
                return False, 0
        return True, self._max_attempts - len(self._login_attempts.get(identifier, []))

    def record_login_attempt(self, identifier: str, success: bool):
        if not success:
            if identifier not in self._login_attempts:
                self._login_attempts[identifier] = []
            self._login_attempts[identifier].append(datetime.now(timezone.utc))

    def check_registration(self, ip: str) -> bool:
        now_date = datetime.now(timezone.utc).date()
        if ip in self._registration_ips:
            if self._registration_ips[ip] >= self._max_registrations:
                return False
        return True

    def record_registration(self, ip: str):
        self._registration_ips[ip] = self._registration_ips.get(ip, 0) + 1
