"""Скан вакансий hh.ru по поисковым запросам профиля.

Использование:
    python3 src/scan.py                        # полный скан по QUERIES
    python3 src/scan.py --query typescript     # один запрос (отладка)
    python3 src/scan.py --no-state             # не трогать seen-ids (пробный прогон)

Выход: data/vacancies.json (нормализованные, прошедшие префильтр),
stderr — лог, stdout — краткая сводка JSON.
"""
import argparse
import json
import pathlib
import re
import time

from hh_session import make_session, get_lux_state, log

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# --- Поисковая стратегия: (text, extra-params) -------------------------------
# Два контура: удалёнка по всей России + Казань локально.
QUERIES = [
    "typescript node.js",
    "senior fullstack",
    "node.js backend",
    "react next.js",
    "team lead разработка",
    "blockchain rust",
    "LLM AI интеграции",
    # расширено@2026-07-20: недельный пул по основному стеку выбран под ноль
    # (256 найдено → 206 seen → 1 новая), добавлен вторичный стек и лид-роли.
    # "golang разработчик" убран@2026-07-20 — Go выведен из стека (profile.md)
    "python backend",
    "CTO",
    "архитектор",
    "react native",
    "web3 solidity",
    "solana",
]
BASE = {
    "order_by": "publication_time",
    "search_period": "14",         # свежее двух недель
    "items_on_page": "50",
    "experience": ["between3And6", "moreThan6"],
}
CONTOURS = [
    {"area": "113", "work_format": "REMOTE"},   # Россия, удалёнка
    {"area": "88"},                              # Казань, любой формат
]
MAX_PAGES_PER_QUERY = 3
THROTTLE_SEC = 1.5

# --- Префильтр ----------------------------------------------------------------
STOP_NAME = re.compile(
    # выстрадано@2026-07-20: было "тестирование" — не ловило "автоматизации
    # тестированиЯ" (7 таких вакансий пролезло в скоринг); режем по основе
    r"1с|1c|тестировщик|тестирован|qa\b|seo|маркетолог|продаж|поддержк|"
    r"саппорт|контент|битрикс|bitrix|вёрстк|верстальщик|дизайнер|"
    r"mql|pine\s*script|аналитик|devops(?!.*разработчик)|системный администратор|"
    r"крауд|"
    # добавлено@2026-07-20 вместе с запросом "архитектор": строительный
    # архитектор — половина выдачи по этому слову
    r"revit|\bbim\b|градостроит|проектировщик|инженер-конструктор|визуализатор|"
    r"архитектурн\w+ бюро|"
    # Go выведен из стека@2026-07-20: режем Go-primary по названию. \bgo\b
    # обязателен — без границ ловит Django/Mongo/Algorithm
    r"\bgolang\b|\bgo\b[-\s]?(?:разработчик|developer|dev\b|engineer)|"
    r"(?:разработчик|developer|engineer)\s+go\b", re.I)
JUNIOR_EXP = {"noExperience", "between1And3"}
MIN_SALARY_RUB = 150_000


def norm_compensation(c: dict | None) -> dict:
    if not c or "noCompensation" in c:
        return {"from": None, "to": None, "currency": None, "gross": None}
    return {
        "from": c.get("from"),
        "to": c.get("to"),
        "currency": c.get("currencyCode") or c.get("currency"),
        "gross": c.get("gross"),
    }


def salary_below_floor(comp: dict) -> bool:
    """Отсекаем только явный мусор: рублёвая вилка целиком ниже пола."""
    if comp["currency"] not in (None, "RUR", "RUB"):
        return False
    hi = comp["to"] or comp["from"]
    return hi is not None and hi < MIN_SALARY_RUB


def normalize(v: dict) -> dict:
    comp = norm_compensation(v.get("compensation"))
    company = v.get("company") or {}
    reviews = company.get("employerReviews") or {}
    work_formats = [wf for grp in (v.get("workFormats") or [])
                    for wf in (grp.get("workFormatsElement") or [])]
    return {
        "id": v["vacancyId"],
        "name": v.get("name", ""),
        "url": (v.get("links") or {}).get("desktop",
                                          f"https://hh.ru/vacancy/{v['vacancyId']}"),
        "company": company.get("visibleName") or company.get("name", ""),
        "companyAccreditedIT": company.get("accreditedITEmployer", False),
        "companyRating": reviews.get("totalRating"),
        "companyReviews": reviews.get("reviewsCount"),
        "salary": comp,
        "area": (v.get("area") or {}).get("name", ""),
        "workFormats": work_formats,
        "experience": v.get("workExperience", ""),
        "employment": v.get("employmentForm") or (v.get("employment") or {}).get("@type", ""),
        "publishedAt": (v.get("publicationTime") or {}).get("$", ""),
        "publishedTs": (v.get("publicationTime") or {}).get("@timestamp", 0),
        "snippet": v.get("snippet") or {},
        "responsesCount": v.get("responsesCount", 0),
        "letterRequired": v.get("@responseLetterRequired", False),
        "testPresent": v.get("userTestPresent", False),
        "closed": v.get("closedForApplicants", False),
        "userLabels": v.get("userLabels", []),
    }


def prefilter(n: dict, seen: set) -> str | None:
    """Причина отброса или None (оставить)."""
    if n["id"] in seen:
        return "seen"
    if n["closed"]:
        return "closed"
    if n["userLabels"]:
        return f"userLabels:{n['userLabels']}"     # уже откликался / отказ
    if STOP_NAME.search(n["name"]):
        return "stop-name"
    if n["experience"] in JUNIOR_EXP:
        return "junior"
    if salary_below_floor(n["salary"]):
        return "salary-floor"
    return None


def search(s, text: str, contour: dict, max_pages: int) -> list[dict]:
    out = []
    for page in range(max_pages):
        params = {**BASE, **contour, "text": text, "page": str(page)}
        state = get_lux_state(s, "https://hh.ru/search/vacancy", params)
        vsr = state.get("vacancySearchResult") or {}
        vacs = vsr.get("vacancies") or []
        total = vsr.get("totalResults", 0)
        log(f"  [{text!r} {contour}] page {page}: {len(vacs)} items, total {total}")
        out.extend(vacs)
        if (page + 1) * int(BASE["items_on_page"]) >= total or not vacs:
            break
        time.sleep(THROTTLE_SEC)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", action="append", help="переопределить QUERIES")
    ap.add_argument("--no-state", action="store_true",
                    help="не читать/не писать seen-ids")
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES_PER_QUERY)
    args = ap.parse_args()

    DATA.mkdir(exist_ok=True)
    seen_file = DATA / "seen-ids.json"
    seen = set() if args.no_state else set(
        json.loads(seen_file.read_text()) if seen_file.exists() else [])

    s = make_session()
    queries = args.query or QUERIES

    raw: dict[int, dict] = {}
    for text in queries:
        for contour in CONTOURS:
            for v in search(s, text, contour, args.max_pages):
                raw.setdefault(v["vacancyId"], v)
            time.sleep(THROTTLE_SEC)

    dropped: dict[str, int] = {}
    kept = []
    for v in raw.values():
        n = normalize(v)
        reason = prefilter(n, seen)
        if reason:
            key = reason.split(":")[0]
            dropped[key] = dropped.get(key, 0) + 1
        else:
            kept.append(n)

    kept.sort(key=lambda n: -n["publishedTs"])
    (DATA / "vacancies.json").write_text(
        json.dumps(kept, ensure_ascii=False, indent=1))

    summary = {
        "uniqueFound": len(raw),
        "kept": len(kept),
        "dropped": dropped,
        "out": str(DATA / "vacancies.json"),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
