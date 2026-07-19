"""Батч-выход из чатов hh (чистка списка). Только по команде юзера — см. skill hh-inbox.

Использование:
    python3 src/chat_leave.py --rejected              # dry-run: кандидаты-отказы
    python3 src/chat_leave.py --rejected --send
    python3 src/chat_leave.py --ids 123,456 --send    # явный список (лимбо — только так,
                                                      # после подтверждения юзером)

Семантика leave — docstring src/chatik.py (negotiation цела, работодатель видит
событие, обратимо). Селектор --rejected берёт ТОЛЬКО status=rejected с chatId и
без события «чат покинут» в dialog; interview/awaiting_user не трогает никогда.
Успех логируется в applied.json событием (схема applied_log).
"""
import argparse
import json
import pathlib
import time

from hh_session import make_session, get_xsrf, log
from chatik import leave
from applied_log import now_iso

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
THROTTLE = 1.0
LEFT_MARK = "чат покинут"


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rejected", action="store_true")
    g.add_argument("--ids", help="vacancyId через запятую")
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()

    f = DATA / "applied.json"
    applied = json.loads(f.read_text())

    def already_left(a):
        return any(LEFT_MARK in (d.get("text") or "") for d in a.get("dialog") or [])

    if args.rejected:
        cand = [a for a in applied
                if a.get("status") == "rejected" and a.get("chatId")
                and not already_left(a)]
    else:
        want = {int(x) for x in args.ids.split(",")}
        cand = [a for a in applied if a["id"] in want and a.get("chatId")]
        blocked = [a for a in cand if a.get("status") in ("interview", "awaiting_user")]
        if blocked:
            for a in blocked:
                log(f"  SKIP {a['id']} {a.get('company')}: status={a['status']} — не выходим")
            cand = [a for a in cand if a not in blocked]

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
            a.setdefault("dialog", []).append(
                {"at": now_iso(), "from": "system", "kind": "event",
                 "text": f"{LEFT_MARK} (chat_leave)"})
            f.write_text(json.dumps(applied, ensure_ascii=False, indent=1))
        if i < len(cand) - 1:
            time.sleep(THROTTLE)
    print(json.dumps({"mode": "send", "ok": ok, "fail": fail}, ensure_ascii=False))


if __name__ == "__main__":
    main()
