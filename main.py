from pywinauto import Desktop
import pygetwindow as gw
import psutil

from urllib.parse import urlparse
import subprocess
import time

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
    "google.com", "ya.ru", "yandex.ru", "bing.com", "dzen.ru"
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


def extract_domain(url: str) -> str:
    """
    'https://super-casino.com/play?id=1' → 'super-casino.com'
    'super-casino.com/play'              → 'super-casino.com'
    """
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    return parsed.netloc


def is_domain_already_blocked(domain: str) -> bool:
    """Проверяет, заблокирован ли домен уже."""
    with open(HOSTS_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return f"127.0.0.1 {domain}" in content


def add_domain_to_hosts(domain: str):
    """Добавляет домен в hosts файл."""

    # Убираем лишнее из домена
    domain = domain.strip().lower()
    if domain.startswith("http"):
        from urllib.parse import urlparse
        domain = urlparse(domain).netloc

    # Формируем строки для записи
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


def kill_browser(browser: str) -> bool:
    browser_tags = browser.lower().split()

    killed = False

    for proc in psutil.process_iter(['name']):
        try:
            for tag in browser_tags:
                if tag in proc.info['name'].lower():
                    proc.kill()
                    killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return killed


def block_casino(browser: str):
    url = get_browser_url(browser)
    domain = extract_domain(url)

    if domain in IGNORE_DOMAINS:
        return

    if not is_domain_already_blocked(domain):
        add_domain_to_hosts(domain)
        flush_dns()
        kill_browser(browser)


def main():
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
    main()
