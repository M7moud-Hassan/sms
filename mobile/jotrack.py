import re
import time
import logging
import threading
import requests
from urllib.parse import urljoin
from django.conf import settings

log = logging.getLogger(__name__)


class JoTrackError(Exception):
    pass


class JoTrackClient:
    BASE = getattr(settings, "JOTRACK_BASE_URL", "https://jotrackv2.sama.jo").rstrip("/")
    LOGIN_PATH = getattr(settings, "JOTRACK_LOGIN_PATH", "/en-us/Login")
    # Leave these blank to auto-detect them from the login form:
    LOGIN_POST_PATH = getattr(settings, "JOTRACK_LOGIN_POST_PATH", "")
    USER_FIELD = getattr(settings, "JOTRACK_USER_FIELD", "")
    PASS_FIELD = getattr(settings, "JOTRACK_PASS_FIELD", "")
    LOCATION_PATH = "/MyVehicleService/GetLastLocationFromTerminal"

    _lock = threading.Lock()
    _session = None
    _login_at = 0.0
    _loc_cache = {}

    # ---- helpers -------------------------------------------------------------
    @staticmethod
    def _attr(tag, name):
        m = re.search(r'\b%s\s*=\s*["\']([^"\']*)["\']' % name, tag, re.I)
        return m.group(1) if m else ""

    @staticmethod
    def _login_ok(r):
        if r.status_code >= 400:
            return False
        # AJAX login -> JSON reply such as {"success": true}
        if "json" in r.headers.get("Content-Type", "").lower():
            try:
                j = r.json()
            except ValueError:
                return False
            if isinstance(j, dict):
                for k in ("success", "Success", "IsSuccess", "isSuccess",
                          "result", "Result", "status", "Status"):
                    if k in j:
                        v = j[k]
                        if isinstance(v, str):
                            return v.strip().lower() in ("true", "ok", "success", "1")
                        return bool(v)
            return bool(j)
        # Classic form login -> redirected away from the login page
        if "/login" not in (r.url or "").lower():
            return True
        body = (r.text or "").lower()
        return 'type="password"' not in body and "type='password'" not in body

    # ---- login ---------------------------------------------------------------
    @classmethod
    def _login(cls):
        user = getattr(settings, "JOTRACK_USERNAME", None)
        pwd = getattr(settings, "JOTRACK_PASSWORD", None)
        if not user or not pwd:
            raise JoTrackError("JOTRACK_USERNAME / JOTRACK_PASSWORD are not set.")

        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        })

        # 1) Load the real login page and read its form
        r = s.get(cls.BASE + cls.LOGIN_PATH, timeout=15)
        r.raise_for_status()
        html = r.text or ""
        form_tag = re.search(r"<form\b[^>]*>", html, re.I)
        form_block = re.search(r"<form\b[^>]*>.*?</form>", html, re.I | re.S)
        scope = form_block.group(0) if form_block else html

        payload = {}
        user_field, pass_field = cls.USER_FIELD, cls.PASS_FIELD
        for tag in re.findall(r"<input\b[^>]*>", scope, re.I):
            name = cls._attr(tag, "name")
            if not name:
                continue
            itype = (cls._attr(tag, "type") or "text").lower()
            if itype == "hidden":
                payload[name] = cls._attr(tag, "value")   # anti-forgery token etc.
            elif itype == "password" and not pass_field:
                pass_field = name
            elif itype in ("text", "email") and not user_field:
                user_field = name
        user_field = user_field or "UserName"
        pass_field = pass_field or "Password"
        payload[user_field] = user
        payload[pass_field] = pwd

        # 2) Post to the form's real action URL
        action = (cls.LOGIN_POST_PATH
                  or (cls._attr(form_tag.group(0), "action") if form_tag else "")
                  or cls.LOGIN_PATH)
        post_url = urljoin(r.url, action)
        r2 = s.post(post_url, data=payload,
                    headers={"Referer": r.url, "Origin": cls.BASE},
                    timeout=15, allow_redirects=True)

        # 3) Check the result properly
        if not cls._login_ok(r2):
            log.warning("JoTrack login failed: POST %s fields=%s -> HTTP %s, final url %s, body: %r",
                        post_url, [k for k in payload if k != pass_field],
                        r2.status_code, r2.url, (r2.text or "")[:300])
            raise JoTrackError(
                f"JoTrack login failed (POST {action}, fields {user_field}/{pass_field}, "
                f"HTTP {r2.status_code}). Check credentials / login field names.")
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