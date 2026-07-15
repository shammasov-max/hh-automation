"""Дотягивает полный текст и ключевые навыки для вакансий из data/vacancies.json.

Использование:
    python3 src/fetch_vacancy.py                 # все из vacancies.json
    python3 src/fetch_vacancy.py --ids 1 2 3     # выборочно
    python3 src/fetch_vacancy.py --limit 30      # первые N (по свежести)

Кэш: data/details/{id}.json (повторно не качает).
Выход: data/enriched.json = vacancies.json + description/keySkills.
"""
import argparse
import html
import json
import pathlib
import re
import time

from hh_session import make_session, get_lux_state, log

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DETAILS = DATA / "details"
THROTTLE_SEC = 1.2

TAG_RE = re.compile(r"<[^>]+>")


def html_to_text(s: str) -> str:
    s = html.unescape(html.unescape(s))          # двойной escape в Lux state
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "• ", s, flags=re.I)
    s = TAG_RE.sub("", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def fetch_one(s, vid: int) -> dict:
    cache = DETAILS / f"{vid}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    state = get_lux_state(s, f"https://hh.ru/vacancy/{vid}")
    vv = state.get("vacancyView") or {}
    # выстрадано@2026-07-13: captcha-редирект отдаёт Lux state БЕЗ vacancyView —
    # раньше молча кэшировалась пустышка (desc="", 107 байт) с рапортом «ok».
    if not vv:
        raise RuntimeError(f"no vacancyView for {vid} — captcha-редирект или не-вакансия")
    ks = (vv.get("keySkills") or {}).get("keySkill") or []
    det = {
        "id": vid,
        "description": html_to_text(vv.get("description", "")),
        "keySkills": ks,
        "address": ((vv.get("address") or {}).get("displayName")
                    if isinstance(vv.get("address"), dict) else None),
        "closedForApplicants": vv.get("closedForApplicants", False),
    }
    cache.write_text(json.dumps(det, ensure_ascii=False, indent=1))
    time.sleep(THROTTLE_SEC)
    return det


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", type=int)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    DETAILS.mkdir(parents=True, exist_ok=True)
    vacs = json.loads((DATA / "vacancies.json").read_text())
    if args.ids:
        vacs = [v for v in vacs if v["id"] in set(args.ids)]
    if args.limit:
        vacs = vacs[:args.limit]

    s = make_session()
    enriched, errors = [], 0
    for i, v in enumerate(vacs):
        try:
            det = fetch_one(s, v["id"])
            enriched.append({**v, **det})
            log(f"  {i + 1}/{len(vacs)} {v['id']} ok "
                f"(skills={len(det['keySkills'])}, desc={len(det['description'])})")
        except Exception as e:
            errors += 1
            log(f"  {i + 1}/{len(vacs)} {v['id']} FAIL: {e}")
            enriched.append(v)

    (DATA / "enriched.json").write_text(
        json.dumps(enriched, ensure_ascii=False, indent=1))
    print(json.dumps({"enriched": len(enriched), "errors": errors,
                      "out": str(DATA / "enriched.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
