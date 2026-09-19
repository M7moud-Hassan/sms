import time
import threading
import requests
from django.conf import settings


class JoTrackError(Exception):
    pass


class JoTrackClient:
    BASE = getattr(settings, "JOTRACK_BASE_URL", "https://jotrackv2.sama.jo").rstrip("/")
    LOGIN_PATH = "/Login/Index"   # verify field names against your login form
    LOCATION_PATH = "/MyVehicleService/GetLastLocationFromTerminal"

    _lock = threading.Lock()
    _session = None
    _login_at = 0.0
    _loc_cache = {}

    # ---- login (unchanged from before) --------------------------------------
    @classmethod
    def _login(cls):
        if not settings.JOTRACK_USERNAME or not settings.JOTRACK_PASSWORD:
            raise JoTrackError("JOTRACK_USERNAME / JOTRACK_PASSWORD are not set.")
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (fleet-integration)",
            "X-Requested-With": "XMLHttpRequest",
        })
        r = s.get(cls.BASE + cls.LOGIN_PATH, timeout=15)
        import re
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', r.text or "")
        payload = {"UserName": settings.JOTRACK_USERNAME,
                   "Password": settings.JOTRACK_PASSWORD}
        if m:
            payload["__RequestVerificationToken"] = m.group(1)
        r = s.post(cls.BASE + cls.LOGIN_PATH, data=payload, timeout=15, allow_redirects=True)
        if "/Login" in (r.url or "") and "Logout" not in (r.text or ""):
            raise JoTrackError("JoTrack login failed. Check credentials / login field names.")
        return s

    @classmethod
    def _get_session(cls):
        if cls._session is None or (time.time() - cls._login_at) > 1500:
            cls._session = cls._login()
            cls._login_at = time.time()
        return cls._session

    # ---- the real endpoint --------------------------------------------------
    @classmethod
    def get_last_location(cls, terminal_id):
        """POST /MyVehicleService/GetLastLocationFromTerminal?strteid=<imei>"""
        ttl = getattr(settings, "JOTRACK_CACHE_SECONDS", 15)
        hit = cls._loc_cache.get(terminal_id)
        if hit and (time.time() - hit[0]) < ttl:
            return hit[1]
        
        url = cls.BASE + cls.LOCATION_PATH

        def _call(sess):
            return sess.post(url, params={"strteid": terminal_id},
                             headers={"X-Requested-With": "XMLHttpRequest"}, timeout=15)

        with cls._lock:
            s = cls._get_session()
            r = _call(s)
            if r.status_code in (401, 403) or "/Login" in (r.url or ""):
                cls._session = None
                r = _call(cls._get_session())
        r.raise_for_status()
        raw = r.json()

        if not raw or not raw.get("success"):
            return None
        try:
            lat = float(raw["Latitude"])
            lng = float(raw["Longtitude"])   # NOTE: JoTrack's spelling
        except (KeyError, TypeError, ValueError):
            return None
        
        result = {
            "lat": lat, "lng": lng,
            "address": raw.get("Address", ""),
            "terminal": raw.get("Teid", terminal_id),
        }
        cls._loc_cache[terminal_id] = (time.time(), result)
        
        return result