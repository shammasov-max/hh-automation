"""Батч-выход из чатов hh (чистка списка). Только по команде юзера — см. skill hh-inbox.

Использование:
    python3 src/chat_leave.py --rejected              # dry-run: кандидаты-отказы
    python3 src/chat_leave.py --rejected --send
    python3 src/chat_leave.py --ids 123,456 --send    # явный список (лимбо — только так,
                                                      # после подтверждения юзером)

Семантика leave — docstring src/chatik.py (negotiation цела, работодатель видит
событие, обратимо). Гейты:
- --rejected берёт ТОЛЬКО status=rejected с chatId без события выхода;
- interview / awaiting_user не покидаются НИКОГДА (даже --ids);
- sent / replied в --ids — только с --force (живой диалог, возможен
  неотвеченный вопрос к нам — проверить history перед force);
- уже покинутые (event «чат покинут») отсекаются в обеих ветках.
Успех логируется в applied.json событием (схема applied_log, атомарно).
"""
import argparse
import json
import time

from hh_session import make_session, get_xsrf, log
from chatik import leave
from applied_log import applied_store, now_iso, APPLIED

THROTTLE = 1.0
LEFT_MARK = "чат покинут"


def already_left(a: dict) -> bool:
    return any(LEFT_MARK in (d.get("text") or "")
               and d.get("from") == "system" and d.get("kind") == "event"
               for d in a.get("dialog") or [])


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rejected", action="store_true")
    g.add_argument("--ids", help="vacancyId через запятую")
    ap.add_argument("--force", action="store_true",
                    help="разрешить sent/replied в --ids (проверь history!)")
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()

    applied = json.loads(APPLIED.read_text())

    if args.rejected:
        cand = [a for a in applied
                if a.get("status") == "rejected" and a.get("chatId")
                and not already_left(a)]
    else:
        want = {int(x) for x in args.ids.split(",")}
        cand = []
        for a in applied:
            if a["id"] not in want or not a.get("chatId"):
                continue
            st = a.get("status")
            if st in ("interview", "awaiting_user"):
                log(f"  SKIP {a['id']} {a.get('company')}: status={st} — не выходим никогда")
            elif st in ("sent", "replied") and not args.force:
                log(f"  SKIP {a['id']} {a.get('company')}: status={st} — живой диалог, нужен --force")
            elif already_left(a):
                log(f"  SKIP {a['id']} {a.get('company')}: уже покинут")
            else:
                cand.append(a)

    if not args.send:
        print(json.dumps({"mode": "dry-run", "candidates": len(cand),
                          "list": [{"id": a["id"], "company": a.get("company"),
                                    "name": a.get("name"), "status": a.get("status")}
                                   for a in cand]}, ensure_ascii=False, indent=1))
        return

    s = make_session()
    xsrf = get_xsrf(s)
    ok, fail = 0, 0
    for i, a in enumerate(cand):
        resp = leave(s, xsrf, a["chatId"])
        good = resp["status"] == 200
        ok += good
        fail += not good
        log(f"  {a['id']} {a.get('company')}: {'OK' if good else 'FAIL '+str(resp)[:120]}")
        if good:
            with applied_store() as fresh:
                rec = next((x for x in fresh if x["id"] == a["id"]), None)
                if rec:
                    rec.setdefault("dialog", []).append(
                        {"at": now_iso(), "from": "system", "kind": "event",
                         "text": f"{LEFT_MARK} (chat_leave)"})
        if i < len(cand) - 1:
            time.sleep(THROTTLE)
    print(json.dumps({"mode": "send", "ok": ok, "fail": fail}, ensure_ascii=False))


if __name__ == "__main__":
    main()
