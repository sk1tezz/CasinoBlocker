"""
CasinoBlocker — блокировка сайтов казино.
Лог отладки: %TEMP%\\casino_blocker.log
"""
import sys
import os
from datetime import datetime

# Лог в файл — работает даже если скрипт падает до импортов (для отладки Планировщика)
def _startup_log(msg: str):
    try:
        # Папка скрипта — доступна и при запуске из Планировщика
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        path = os.path.join(script_dir, "casino_blocker.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()} | {msg}\n")
    except Exception:
        pass

_startup_log(f"START argv={sys.argv} cwd={os.getcwd()} exe={sys.executable}")

from pywinauto import Desktop
import pygetwindow as gw

from urllib.parse import urlparse
import subprocess
import time

_startup_log("Imports OK")

CONSOLE_MODE = "--console" in sys.argv or "-c" in sys.argv


def log(msg: str):
    """Вывод в консоль (виден только при запуске через python.exe, не pythonw)."""
    if CONSOLE_MODE:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)


KEYWORDS = [
    # Английские
    "casino", "slots", "poker", "blackjack",
    "roulette", "betting", "jackpot", "gambling",
    "sportbet", "bookmaker", "hotskins",

    # Русские
    "казино", "ставки", "ставок", "покер",
    "рулетка", "слоты", "букмекер", "игровые автоматы",
    "фриспин", "джекпот", "ставк"
]

IGNORE_DOMAINS = [
    "google.com", "ya.ru", "yandex.ru", "bing.com", "dzen.ru", "youtube.com", "rutube.ru"
]

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"


def is_casino(title: str) -> bool:
    title_lower = title.lower()
    return any(kw in title_lower for kw in KEYWORDS)


def get_browser_url(browser: str):
    """Получает URL из адресной строки Chrome."""
    desktop = Desktop(backend="uia")
    chrome = desktop.window(title_re=f".*{browser}.*")
    address_bar = chrome.child_window(control_type="Edit", found_index=0)
    url = address_bar.get_value()
    return url


def extract_domain(url: str) -> str | None:
    """
    'https://super-casino.com/play?id=1' → 'super-casino.com'
    'super-casino.com/play'              → 'super-casino.com'
    Возвращает None для пустых, about:, chrome: и т.п.
    """
    url = (url or "").strip()
    if not url or url.startswith(("about:", "chrome:", "edge:", "file:", "view-source:")):
        return None
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    domain = parsed.netloc
    return domain if domain else None


def normalize_domain(domain: str) -> str:
    """Убирает www. в начале, чтобы избежать www.www.domain.com."""
    domain = domain.strip().lower()
    while domain.startswith("www."):
        domain = domain[4:]
    return domain


def is_domain_already_blocked(domain: str) -> bool:
    """Проверяет, заблокирован ли домен (с www и без)."""
    domain = normalize_domain(domain)
    if not domain:
        return True
    with open(HOSTS_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return (
        f"127.0.0.1 {domain}" in content
        or f"127.0.0.1 www.{domain}" in content
    )


def add_domain_to_hosts(domain: str):
    """Добавляет домен в hosts файл."""

    # Убираем лишнее из домена
    domain = domain.strip().lower()
    if domain.startswith("http"):
        domain = urlparse(domain).netloc
    domain = normalize_domain(domain)
    if not domain:
        return

    # Формируем строки для записи (без дублирования www)
    lines = f"\n127.0.0.1 {domain}\n127.0.0.1 www.{domain}\n"

    # Дописываем в hosts
    with open(HOSTS_PATH, "a", encoding="utf-8") as f:
        f.write(lines)


def flush_dns():
    """Сбрасывает DNS-кеш системы."""
    try:
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True, check=True)
    except Exception:
        pass


def setup_scheduler() -> bool:
    """
    Создаёт задачу в планировщике Windows.
    Запуск при входе в систему, с правами администратора, без UAC.
    Первый запуск скрипта — от имени администратора.
    LogonType=InteractiveToken — задача выполняется в сессии пользователя (видит окна).
    """
    script_path = os.path.abspath(sys.argv[0])
    script_dir = os.path.dirname(script_path)
    task_name = "CasinoBlocker"

    # Задача в Планировщике — python.exe + --console (видимое окно CMD)
    if script_path.endswith(".py"):
        command = sys.executable
        arguments = f'"{script_path}" --console'
    else:
        command = script_path
        arguments = "--console"

    # LogonType=InteractiveToken — задача в сессии пользователя (видит окна), НЕ в Session 0
    # Delay=PT30S — задержка 30 сек после входа, чтобы рабочий стол успел загрузиться
    xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
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

    # /IT — задача только при входе пользователя (интерактивная сессия)
    result = subprocess.run(
        ["schtasks", "/Create", "/TN", task_name, "/XML", xml_path, "/IT"],
        capture_output=True,
        text=True,
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


def block_casino(browser: str):
    try:
        url = get_browser_url(browser)
    except Exception:
        return
    
    domain = extract_domain(url)

    if not domain:
        return
    domain_norm = normalize_domain(domain)
    if domain_norm in IGNORE_DOMAINS:
        return

    if not is_domain_already_blocked(domain):
        add_domain_to_hosts(domain)
        flush_dns()
        log(f"Заблокирован: {domain}")


def main():
    log("CasinoBlocker запущен, мониторинг окон...")
    while True:
        windows = gw.getAllWindows()

        for w in windows:
            if is_casino(w.title):
                title_parts = w.title.rsplit("-", maxsplit=1)
                if len(title_parts) != 2:
                    continue

                browser = title_parts[1].strip()
                block_casino(browser)

        time.sleep(1)


if __name__ == '__main__':
    if "--help" in sys.argv or "-h" in sys.argv:
        print("CasinoBlocker — блокировка сайтов казино")
        print("  --console, -c   видимое окно CMD с логами (для отладки)")
        print("  Лог отладки: %TEMP%\\casino_blocker.log")
        sys.exit(0)
    try:
        _startup_log("Calling setup_scheduler")
        setup_scheduler()
        _startup_log("Calling main")
        main()
    except Exception as e:
        _startup_log(f"FATAL: {type(e).__name__}: {e}")
        raise
