"""
CasinoBlocker — блокировка сайтов казино.
Лог отладки: casino_blocker.log (в папке скрипта)
"""
import sys
import os
from datetime import datetime


def _startup_log(msg: str):
    try:
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        path = os.path.join(script_dir, "casino_blocker.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()} | {msg}\n")
    except Exception:
        pass


_startup_log(f"START argv={sys.argv} cwd={os.getcwd()} exe={sys.executable}")

from pywinauto import Application          # ← заменён Desktop на Application
import pygetwindow as gw
from urllib.parse import urlparse
import subprocess
import time

_startup_log("Imports OK")

CONSOLE_MODE = "--console" in sys.argv or "-c" in sys.argv


def log(msg: str):
    if CONSOLE_MODE:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)
    _startup_log(msg)


# ── Ключевые слова ──────────────────────────────────────────────
KEYWORDS = [
    "casino", "slots", "poker", "blackjack",
    "roulette", "betting", "jackpot", "gambling",
    "sportbet", "bookmaker", "hotskins",
    "казино", "ставки", "ставок", "покер",
    "рулетка", "слоты", "букмекер", "игровые автоматы",
    "фриспин", "джекпот", "ставк",
]

IGNORE_DOMAINS = [
    "google.com", "ya.ru", "yandex.ru", "bing.com",
    "dzen.ru", "youtube.com", "rutube.ru",
]

# FIX #2: суффиксы заголовков для фильтрации НЕ-браузерных окон
#          (чтобы не делать дорогой UIA-вызов к Проводнику и т.п.)
BROWSER_NAMES = [
    "google chrome", "chrome", "microsoft edge", "edge",
    "mozilla firefox", "firefox", "opera", "brave",
    "vivaldi", "яндекс браузер", "yandex browser",
]

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"


# ── Проверки ────────────────────────────────────────────────────

def is_casino(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in KEYWORDS)


def is_browser_window(title: str) -> bool:
    """Быстрая проверка по заголовку — похоже ли окно на браузер."""
    t = title.lower()
    return any(name in t for name in BROWSER_NAMES)


# ── FIX #1: получаем URL по HWND конкретного окна ───────────────

def get_browser_url(hwnd: int) -> str | None:
    """
    Подключается к конкретному окну браузера по дескриптору (HWND)
    и читает значение адресной строки через UI Automation.
    """
    try:
        app = Application(backend="uia").connect(handle=hwnd)
        window = app.window(handle=hwnd)
        address_bar = window.child_window(
            control_type="Edit", found_index=0
        )
        return address_bar.get_value()
    except Exception:
        return None


# ── Работа с доменами ───────────────────────────────────────────

def extract_domain(url: str) -> str | None:
    url = (url or "").strip()
    if not url or url.startswith(
        ("about:", "chrome:", "edge:", "file:", "view-source:", "browser:")
    ):
        return None
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    return parsed.netloc or None


def normalize_domain(domain: str) -> str:
    domain = domain.strip().lower()
    while domain.startswith("www."):
        domain = domain[4:]
    return domain


# FIX #3: учитываем поддомены (mail.google.com → google.com)
def is_ignored_domain(domain: str) -> bool:
    d = normalize_domain(domain)
    return any(d == ign or d.endswith("." + ign) for ign in IGNORE_DOMAINS)


# ── Hosts ───────────────────────────────────────────────────────

# FIX #4: обёрнуто в try/except
def is_domain_already_blocked(domain: str) -> bool:
    domain = normalize_domain(domain)
    if not domain:
        return True
    try:
        with open(HOSTS_PATH, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return False
    return (
        f"127.0.0.1 {domain}" in content
        or f"127.0.0.1 www.{domain}" in content
    )


def add_domain_to_hosts(domain: str):
    domain = normalize_domain(domain)
    if not domain:
        return
    lines = f"\n127.0.0.1 {domain}\n127.0.0.1 www.{domain}\n"
    try:
        with open(HOSTS_PATH, "a", encoding="utf-8") as f:
            f.write(lines)
    except OSError as e:
        log(f"Не удалось записать в hosts: {e}")


def flush_dns():
    try:
        subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True, check=True,
        )
    except Exception:
        pass


# ── Планировщик ─────────────────────────────────────────────────

def setup_scheduler() -> bool:
    script_path = os.path.abspath(sys.argv[0])
    script_dir = os.path.dirname(script_path)
    task_name = "CasinoBlocker"

    if script_path.endswith(".py"):
        command = sys.executable
        arguments = f'"{script_path}" --console'
    else:
        command = script_path
        arguments = "--console"

    xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2"
      xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Casino Blocker — блокировка сайтов казино</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal>
      <RunLevel>HighestAvailable</RunLevel>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
  </Settings>
  <Actions>
    <Exec>
      <Command>{command}</Command>
      <Arguments>{arguments}</Arguments>
      <WorkingDirectory>{script_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''

    xml_path = os.path.join(os.environ["TEMP"], "casino_blocker_task.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(xml)

    subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True,
    )
    result = subprocess.run(
        ["schtasks", "/Create", "/TN", task_name, "/XML", xml_path, "/IT"],
        capture_output=True, text=True,
    )
    try:
        os.remove(xml_path)
    except OSError:
        pass

    if result.returncode == 0:
        log("Задача в Планировщике создана/обновлена")
    else:
        log(f"Ошибка создания задачи: {result.stderr or result.stdout}")
    return result.returncode == 0


# ── Основная логика ─────────────────────────────────────────────

def block_casino(hwnd: int, title: str):
    url = get_browser_url(hwnd)
    if not url:
        return

    domain = extract_domain(url)
    if not domain:
        return

    if is_ignored_domain(domain):
        return

    if is_domain_already_blocked(domain):
        return

    add_domain_to_hosts(domain)
    flush_dns()
    log(f"Заблокирован: {normalize_domain(domain)}  (окно: «{title}»)")


def main():
    log("CasinoBlocker запущен, мониторинг окон...")

    # FIX #5: кеш (hwnd, title) — не дёргаем UIA повторно
    #         для того же окна с тем же заголовком
    seen: set[tuple[int, str]] = set()

    while True:
        try:
            active_hwnds: set[int] = set()
            windows = gw.getAllWindows()

            for w in windows:
                if not w.title:
                    continue

                active_hwnds.add(w._hWnd)
                key = (w._hWnd, w.title)

                if key in seen:
                    continue                     # уже обработано
                seen.add(key)

                if not is_browser_window(w.title):
                    continue                     # не браузер — пропускаем

                if is_casino(w.title):
                    block_casino(w._hWnd, w.title)

            # чистим кеш от закрытых окон
            seen = {(h, t) for h, t in seen if h in active_hwnds}

        except Exception as e:
            log(f"Ошибка в цикле: {e}")

        time.sleep(1)


# ── Точка входа ─────────────────────────────────────────────────

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("CasinoBlocker — блокировка сайтов казино")
        print("  --console, -c   видимое окно CMD с логами")
        sys.exit(0)
    try:
        _startup_log("Calling setup_scheduler")
        setup_scheduler()
        _startup_log("Calling main")
        main()
    except Exception as e:
        _startup_log(f"FATAL: {type(e).__name__}: {e}")
        raise