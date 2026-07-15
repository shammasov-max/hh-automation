"""Общая сессия hh.ru: куки из Chrome + парсер HH-Lux-InitialState.

api.hh.ru анонимно отдаёт 403 (подтверждено@2026-07-09), поэтому работаем
через сайт с куками залогиненного Chrome (browser_cookie3), как kwork/scrape-fl.py.
"""
import html
import json
import re
import sys
import time

import browser_cookie3
import requests

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

_LUX_RE = re.compile(
    r'<template[^>]*id="HH-Lux-InitialState"[^>]*>(\{.*?)</template>', re.S)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def make_session() -> requests.Session:
    s = requests.Session()
    s.cookies = browser_cookie3.chrome(domain_name="hh.ru")
    s.headers.update({"User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9"})
    return s


def get_lux_state(s: requests.Session, url: str, params: dict | None = None,
                  retries: int = 3) -> dict:
    """GET страницы hh.ru → распарсенный HH-Lux-InitialState."""
    for attempt in range(retries):
        r = s.get(url, params=params, timeout=30)
        if r.status_code == 200:
            m = _LUX_RE.search(r.text)
            if m:
                frag = m.group(1)
                # выстрадано@2026-07-13 (вечер): hh начал HTML-экранировать JSON
                # в template (&#34; вместо ") — до этого лежал сырым.
                if frag.startswith("{&#"):
                    frag = html.unescape(frag)
                return json.loads(frag)
            # Балансный fallback: template нашёлся, но regex не взял (вложенный </template> не встречался, но перестрахуемся)
            idx = r.text.find('id="HH-Lux-InitialState"')
            if idx != -1:
                gt = r.text.find(">", idx)
                obj, _ = json.JSONDecoder().raw_decode(r.text[gt + 1:].lstrip())
                return obj
            raise RuntimeError(f"no Lux state in {r.url} (len={len(r.text)})")
        log(f"HTTP {r.status_code} on {url}, attempt {attempt + 1}/{retries}")
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: HTTP {r.status_code}")


def get_xsrf(s: requests.Session) -> str:
    tok = requests.utils.dict_from_cookiejar(s.cookies).get("_xsrf")
    if not tok:
        # куки _xsrf может не быть до первого GET
        s.get("https://hh.ru/", timeout=30)
        tok = requests.utils.dict_from_cookiejar(s.cookies).get("_xsrf")
    if not tok:
        raise RuntimeError("no _xsrf cookie — залогинься на hh.ru в Chrome")
    return tok
