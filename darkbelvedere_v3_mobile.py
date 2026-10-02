#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DARK BELVEDERE V3 — Mobile HUD
Termux / Android için tasarlanmış, yatay taşma yapmayan,
tek ekran odaklı, kırmızı/siyah, read-only terminal dashboard.

Kontroller:
  ↑ / ↓       menü
  ENTER       seç
  1-8         hızlı seçim
  B / ESC     geri
  Q           çıkış

Not:
Terminal arayüzü gerçek Android "dokunmatik buton" olaylarını standart
Termux stdin üzerinden alamaz; bu yüzden telefon klavyesindeki sayı tuşları
ve ok tuşlarıyla dokunmatik uygulama hissi veren büyük kartlar kullanılır.
"""

import os
import re
import sys
import time
import socket
import shutil
import platform
import subprocess
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# ANSI
# ─────────────────────────────────────────────────────────────────────────────
R = "\033[0m"
B = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
DR = "\033[31m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"

def clear():
    print("\033[2J\033[H", end="")

def cursor(show=True):
    print("\033[?25h" if show else "\033[?25l", end="", flush=True)

def term_size():
    s = shutil.get_terminal_size((48, 24))
    return max(32, s.columns), max(12, s.lines)

def compact(s, n):
    s = str(s).replace("\n", " ")
    return s if len(s) <= n else s[:max(1, n-1)] + "…"

def run(cmd, timeout=2):
    try:
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=timeout
        )
        return p.stdout.strip()
    except Exception:
        return ""

def prop(name):
    return run(["getprop", name]) or "N/A"

def wait_key():
    try:
        import termios, tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                # Arrow keys: ESC [ A/B/C/D
                seq = sys.stdin.read(2)
                return ch + seq
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        try:
            return input().strip()[:1]
        except EOFError:
            return "q"

def pause():
    print()
    print(GRAY + "  [B/ESC] geri   [Q] ana menü" + R)
    while True:
        k = wait_key()
        if k in ("\x1b", "\x1b[A", "\x1b[B", "b", "B", "\r", "\n", " "):
            return

def hr():
    w, _ = term_size()
    print(DR + "─" * w + R)

# ─────────────────────────────────────────────────────────────────────────────
# MOBILE ART
# ─────────────────────────────────────────────────────────────────────────────
# Narrow art deliberately avoids horizontal scrolling on portrait phones.
REAPER = [
"        . . . . . .",
"      . . . . . . . .",
"    . . . . . . . . . .",
"   . . . . . . . . . . .",
"  . . . .  ██████  . . .",
" . . . .  ████████  . . .",
" . . . .  ██  ██  ██ . .",
" . . . .  ██  ▄▄  ██ . .",
" . . . .  ██████████ . .",
"  . . . .  ██████  . . .",
"   . . . .  ████  . . .",
"    . . . . ████ . . .",
"     . . .  ████ . . .",
"       . . ██████ . .",
"        .  ██████  .",
"       .  /██████\\ .",
"      .  /████████\\ .",
"     .  /██████████\\ .",
]

def logo():
    w, _ = term_size()
    print()
    for row in REAPER:
        print(RED + row.center(w) + R)
    print()

# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────
def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.1.1.1", 80))
        return s.getsockname()[0]
    except Exception:
        return "N/A"
    finally:
        s.close()

def gateway():
    out = run(["ip", "route"])
    m = re.search(r"default via\s+(\S+)", out)
    return m.group(1) if m else "N/A"

def dns():
    values = []
    for key in ("net.dns1", "net.dns2", "net.dns3"):
        x = prop(key)
        if x != "N/A" and x not in values:
            values.append(x)
    return ", ".join(values) if values else "N/A"

def interfaces():
    out = run(["ip", "-o", "addr", "show"])
    result = []
    for ln in out.splitlines():
        m = re.match(r"\d+:\s+(\S+)\s+inet\s+(\S+)", ln)
        if m:
            result.append((m.group(1), m.group(2)))
    return result

def mem():
    data = {}
    try:
        text = open("/proc/meminfo", encoding="utf-8").read()
    except Exception:
        return data
    for ln in text.splitlines():
        if ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        p = v.strip().split()
        if p and p[0].isdigit():
            data[k] = int(p[0]) * 1024
    return data

def human(n):
    try:
        n = float(n)
    except Exception:
        return "N/A"
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"

def uptime():
    try:
        sec = int(float(open("/proc/uptime").read().split()[0]))
    except Exception:
        return "N/A"
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, _ = divmod(sec, 60)
    return f"{d}d {h:02d}h {m:02d}m"

# ─────────────────────────────────────────────────────────────────────────────
# HUD COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────
def topbar():
    w, _ = term_size()
    clear()
    title = "DARK BELVEDERE"
    print(RED + B + "┏" + "━" * (w-2) + "┓" + R)
    print(RED + B + "┃" + title.center(w-2) + "┃" + R)
    print(RED + B + "┗" + "━" * (w-2) + "┛" + R)
    status = "● ONLINE" if local_ip() != "N/A" else "○ OFFLINE"
    print(GRAY + compact(
        datetime.now().strftime("%H:%M:%S") + "  " + status +
        "  •  SAFE HUD  •  READ-ONLY", w
    ) + R)
    hr()

def card(number, title, subtitle, selected=False):
    w, _ = term_size()
    inner = max(24, min(w-4, 54))
    if selected:
        c = RED + B
        mark = "▶"
    else:
        c = DR
        mark = " "
    print(c + "┌" + "─" * (inner-2) + "┐" + R)
    print(c + "│" + R + f" {mark} [{number}] " + B +
          compact(title, inner-10).ljust(inner-10) + R + c + "│" + R)
    print(c + "│" + R + "   " + compact(subtitle, inner-5).ljust(inner-5) + c + "│" + R)
    print(c + "└" + "─" * (inner-2) + "┘" + R)

def data_panel(title, rows):
    w, _ = term_size()
    inner = max(26, min(w-4, 58))
    print(RED + B + "┏" + "━"*(inner-2) + "┓" + R)
    print(RED + B + "┃" + compact(title, inner-2).center(inner-2) + "┃" + R)
    print(RED + "┣" + "━"*(inner-2) + "┫" + R)
    for k, v in rows:
        line = f" {k}: {compact(v, inner-4-len(k))}"
        print(RED + "┃" + R + line.ljust(inner-2) + RED + "┃" + R)
    print(RED + "┗" + "━"*(inner-2) + "┛" + R)

# ─────────────────────────────────────────────────────────────────────────────
# SCREENS
# ─────────────────────────────────────────────────────────────────────────────
def boot():
    cursor(False)
    try:
        clear()
        w, _ = term_size()
        print(RED + B + "DARK BELVEDERE".center(w) + R)
        print(GRAY + "MOBILE HUD // V3".center(w) + R)
        logo()
        print(GREEN + "WELCOME TO THE DARK BELVEDERE".center(w) + R)
        print(GRAY + "SAFE INFORMATION SYSTEM".center(w) + R)
        print()
        for label in ("SYSTEM", "NETWORK", "DEVICE", "HUD"):
            print(("  " + RED + "◆" + R + " " + label +
                   GREEN + "  [ READY ]" + R).center(w))
            time.sleep(0.10)
        print()
        print(YELLOW + "PRESS ANY KEY".center(w) + R)
        wait_key()
    finally:
        cursor(True)

def screen_ip():
    topbar()
    data_panel("IP ANALYSIS", [
        ("Local", local_ip()),
        ("Gateway", gateway()),
        ("DNS", dns()),
        ("Host", socket.gethostname()),
        ("Mode", "LOCAL / READ-ONLY"),
    ])
    print(GRAY + "  Yerel cihaz ağ bilgileri." + R)
    pause()

def screen_system():
    topbar()
    data_panel("SYSTEM", [
        ("OS", platform.system()),
        ("Kernel", platform.release()),
        ("Arch", platform.machine()),
        ("Python", platform.python_version()),
        ("Uptime", uptime()),
        ("Termux", prop("com.termux.version")),
    ])
    pause()

def screen_network():
    topbar()
    rows = [(a, b) for a, b in interfaces()[:6]]
    rows += [("Gateway", gateway()), ("WiFi", prop("sys.wifi.state"))]
    data_panel("NETWORK", rows or [("Status", "N/A")])
    pause()

def screen_cpu():
    topbar()
    m = mem()
    total = m.get("MemTotal", 0)
    available = m.get("MemAvailable", m.get("MemFree", 0))
    used = max(total - available, 0)
    load = os.getloadavg()[0] if hasattr(os, "getloadavg") else None
    data_panel("CPU / RAM", [
        ("Cores", os.cpu_count() or 1),
        ("Load", f"{load:.2f}" if load is not None else "N/A"),
        ("Total", human(total)),
        ("Used", human(used)),
        ("Free", human(available)),
    ])
    pause()

def screen_storage():
    topbar()
    total, used, free = shutil.disk_usage("/")
    data_panel("STORAGE", [
        ("Total", human(total)),
        ("Used", human(used)),
        ("Free", human(free)),
        ("Usage", f"{used/total*100:.1f}%" if total else "N/A"),
    ])
    pause()

def screen_device():
    topbar()
    data_panel("DEVICE", [
        ("Brand", prop("ro.product.brand")),
        ("Model", prop("ro.product.model")),
        ("Device", prop("ro.product.device")),
        ("Android", prop("ro.build.version.release")),
        ("SDK", prop("ro.build.version.sdk")),
    ])
    pause()

def screen_status():
    topbar()
    ip = local_ip()
    data_panel("LIVE STATUS", [
        ("Time", datetime.now().strftime("%H:%M:%S")),
        ("Network", "ONLINE" if ip != "N/A" else "UNKNOWN"),
        ("IP", ip),
        ("Terminal", os.environ.get("TERM", "unknown")),
        ("Safety", "READ-ONLY"),
    ])
    print(GREEN + B + "\n  ● SYSTEM READY" + R)
    pause()

def screen_about():
    topbar()
    logo()
    data_panel("ABOUT", [
        ("Version", "DARK BELVEDERE V3"),
        ("Platform", "Termux / Android"),
        ("Style", "RED / BLACK MOBILE HUD"),
        ("Mode", "SAFE / READ-ONLY"),
    ])
    pause()

SCREENS = [
    screen_ip, screen_system, screen_network, screen_cpu,
    screen_storage, screen_device, screen_status, screen_about
]

def menu():
    selected = 0
    items = [
        ("IP ANALYSIS", "Local IP / gateway / DNS"),
        ("SYSTEM", "Android / kernel / uptime"),
        ("NETWORK", "Interfaces / Wi-Fi"),
        ("CPU / RAM", "Memory / processor"),
        ("STORAGE", "Device storage"),
        ("DEVICE", "Android properties"),
        ("LIVE STATUS", "HUD runtime"),
        ("ABOUT", "Version / safety"),
        ("EXIT", "Close"),
    ]

    while True:
        topbar()
        # Keep home screen short enough for a portrait phone.
        print(RED + B + "  // COMMAND CENTER" + R)
        print()
        for i, (title, sub) in enumerate(items):
            card(str(i+1) if i < 8 else "0", title, sub, i == selected)
        print()
        print(GRAY + "  ↑↓  SELECT    ENTER  OPEN    1-8  QUICK    Q  EXIT" + R)

        k = wait_key()
        if k in ("\x1b[A", "k"):
            selected = (selected - 1) % len(items)
        elif k in ("\x1b[B", "j"):
            selected = (selected + 1) % len(items)
        elif k in ("\r", "\n", " "):
            if selected == 8:
                return
            SCREENS[selected]()
        elif k in "12345678":
            SCREENS[int(k)-1]()
        elif k in ("0", "q", "Q"):
            return


def install_dark_prompt():
    """Add an optional Dark Belvedere prompt helper to Termux ~/.bashrc."""
    home = os.path.expanduser("~")
    bashrc = os.path.join(home, ".bashrc")
    function = """
# DARK BELVEDERE prompt
cd_dark_belvedere() {
    mkdir -p "$HOME/Dark"
    builtin cd "$HOME/Dark" || return
    PS1='\\[\\e[91m\\]Dark Belvedere\\[\\e[0m\\] $ '
}
alias Dark='cd_dark_belvedere'
"""
    try:
        existing = ""
        if os.path.exists(bashrc):
            with open(bashrc, "r", encoding="utf-8", errors="ignore") as f:
                existing = f.read()
        if "cd_dark_belvedere()" not in existing:
            with open(bashrc, "a", encoding="utf-8") as f:
                f.write("\n" + function + "\n")
        return True
    except Exception:
        return False

def main():
    try:
        install_dark_prompt()
        boot()
        menu()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        cursor(True)
        print(R + "\n" + RED + "  DARK BELVEDERE // OFFLINE" + R)

if __name__ == "__main__":
    main()
