"""Отклик на вакансии hh.ru с сопроводительным письмом.

Использование:
    python3 src/apply.py --input data/to-apply.json            # dry-run (по умолчанию)
    python3 src/apply.py --input data/to-apply.json --send     # реальная отправка

Формат to-apply.json: [{"id": 134273648, "letter": "...", "resume": "senior-en"}, ...]
"resume" опционален (default senior-en).

Безопасность: без --send НИЧЕГО не отправляется. При --send троттлинг 8с,
детект капчи/лимита → немедленный стоп. Лог: data/applied.json.
"""
import argparse
import json
import pathlib
import sys
import time

from hh_session import make_session, get_xsrf, log

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# hash'и резюме юзера (hh.ru/applicant/resumes, подтверждено@2026-07-09)
RESUMES = {
    "senior-en": "a9b8705eff071acdfd0039ed1f4a7037456369",   # Senior fullstack engineer (EN)
    "fullstack-en": "0089d497ff029e1ed70039ed1f4b71324f454f",  # Fullstack developer (EN)
    "lead-ru": "642ff2bdff0e740e680039ed1f62646b466c53",     # Ведущий разработчик (RU)
    "head-ru": "6330a4fdff073a23460039ed1f393835535469",     # Head of IT, Principal (RU)
}
DEFAULT_RESUME = "senior-en"
# выстрадано@2026-07-09: POST на /applicant/vacancy_response (без /popup) отдаёт
# HTTP 406 (HTML), но отклик ПРИ ЭТОМ СОЗДАЁТСЯ — падает только рендер ответа.
# Рабочий XHR-путь фронта — /popup + заголовки X-Requested-With/Origin/Referer:
# отвечает чистым JSON (400 {"error":"alreadyApplied"} на дубль).
# Вакансии с userTestPresent=true этим POST'ом НЕ откликаются (нужен тест на сайте).
RESPONSE_URL = "https://hh.ru/applicant/vacancy_response/popup"
THROTTLE_SEC = 8


def send_response(s, xsrf: str, vacancy_id: int, resume_hash: str,
                  letter: str) -> dict:
    data = {
        "_xsrf": xsrf,
        "vacancy_id": str(vacancy_id),
        "resume_hash": resume_hash,
        "ignore_postponed": "true",
        "incomplete": "false",
        "lux": "true",
        "letter": letter or "",
        "letterRequired": "false",
    }
    r = s.post(RESPONSE_URL, data=data,
               headers={"X-Xsrftoken": xsrf,
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                        "Origin": "https://hh.ru",
                        "Referer": f"https://hh.ru/vacancy/{vacancy_id}"},
               timeout=30)
    out = {"status": r.status_code}
    try:
        out["body"] = r.json()
    except Exception:
        out["body"] = r.text[:500]
    return out


def details_info(vid: int) -> dict | None:
    """name/company в момент отклика из скан-файлов текущего прогона
    (data/details/ их НЕ содержит — там только description/keySkills;
    позже вакансия может уйти в архив/за captcha-стену — писать сразу)."""
    for fname in ("scored.json", "enriched.json", "vacancies.json"):
        p = DATA / fname
        if not p.exists():
            continue
        for v in json.loads(p.read_text()):
            if v.get("id") == vid:
                return {"name": v.get("name"), "company": v.get("company")}
    return None


def verify_sent(s, vacancy_ids: set) -> set:
    """Фактическая сверка по hh.ru/applicant/negotiations — что реально создано."""
    from hh_session import get_lux_state
    st = get_lux_state(s, "https://hh.ru/applicant/negotiations", {"filter": "all"})
    topics = (st.get("applicantNegotiations") or {}).get("topicList") or []
    return {t.get("vacancyId") for t in topics} & vacancy_ids


def is_blocker(resp: dict) -> str | None:
    """Капча/лимит/бан → причина остановки всей пачки."""
    body = json.dumps(resp.get("body", ""), ensure_ascii=False).lower()
    # выстрадано@2026-07-13: hh шлёт 'negotiations-limit-exceeded' (дефисы!) — старый
    # маркер 'limit_exceeded' его не ловил, скрипт долбил лимит до конца пачки.
    for marker in ("captcha", "limit_exceeded", "limit-exceeded", "too_many"):
        if marker in body:
            return marker
    if resp["status"] in (403, 429):
        return f"http-{resp['status']}"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--send", action="store_true",
                    help="реально отправить (без флага — dry-run)")
    args = ap.parse_args()

    items = json.loads(pathlib.Path(args.input).read_text())
    applied_file = DATA / "applied.json"
    applied = json.loads(applied_file.read_text()) if applied_file.exists() else []
    already = {a["id"] for a in applied}

    s = make_session()
    xsrf = get_xsrf(s) if args.send else None

    results = []
    for i, it in enumerate(items):
        vid = it["id"]
        resume_key = it.get("resume", DEFAULT_RESUME)
        rhash = RESUMES[resume_key]
        letter = (it.get("letter") or "").strip()

        if vid in already:
            log(f"  {vid}: SKIP (уже в applied.json)")
            results.append({"id": vid, "result": "skip-already"})
            continue

        if not args.send:
            log(f"  DRY-RUN {vid} resume={resume_key} letter={len(letter)} chars")
            log(f"    {letter[:120]}...")
            results.append({"id": vid, "result": "dry-run"})
            continue

        resp = send_response(s, xsrf, vid, rhash, letter)
        body = resp.get("body")
        if isinstance(body, dict) and body.get("error") == "alreadyApplied":
            log(f"  {vid}: SKIP (alreadyApplied)")
            results.append({"id": vid, "result": "skip-already"})
            continue
        blocker = is_blocker(resp)
        ok = resp["status"] == 200 and not blocker
        log(f"  {vid}: {'OK' if ok else 'FAIL'} {resp['status']} {str(resp['body'])[:200]}")
        body = resp.get("body") if isinstance(resp.get("body"), dict) else {}
        # сырой HTTP-ответ НЕ хранить (раздули applied.json до 34МБ, срезано@2026-07-19
        # → data/archive/); полезное из body: topic_id/chat_id — ключи для inbox/чатов
        info = details_info(vid) or {}
        rec = {"id": vid, "result": "ok" if ok else "fail",
               "name": info.get("name"), "company": info.get("company"),
               "resume": resume_key, "letter": letter,
               "status": "sent",
               "topicId": body.get("topic_id"), "chatId": body.get("chat_id"),
               "httpStatus": resp["status"],
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        if not ok:
            rec["error"] = str(resp.get("body"))[:300]
        results.append(rec)
        if ok:
            applied.append(rec)
            applied_file.write_text(json.dumps(applied, ensure_ascii=False, indent=1))
        if blocker:
            log(f"STOP: блокер «{blocker}» — дальше не шлём, сообщи юзеру")
            break
        if i < len(items) - 1:
            time.sleep(THROTTLE_SEC)

    verified = None
    if args.send:
        try:
            verified = sorted(verify_sent(s, {it["id"] for it in items}))
        except Exception as e:
            log(f"verify_sent failed: {e}")

    print(json.dumps({
        "mode": "send" if args.send else "dry-run",
        "total": len(items),
        "ok": sum(1 for r in results if r["result"] == "ok"),
        "verifiedInNegotiations": verified,
        "results": [{k: r[k] for k in ("id", "result")} for r in results],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
