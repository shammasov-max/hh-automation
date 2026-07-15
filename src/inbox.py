"""Входящие по разосланным откликам: новые сообщения работодателей.

Использование:
    python3 src/inbox.py            # все чаты по applied-откликам
    python3 src/inbox.py --unread   # только с непрочитанными

Канал (выстрадано@2026-07-09): chatik.hh.ru/api/chat/messages?chatId=<любой>
отдаёт SSR-конфиг, в котором chats.chats.items — ВСЕ чаты юзера с lastMessage,
unreadCount, workflowTransition.applicantState и participantDisplay.isBot.
Полная история сообщений этим путём недоступна (SPA грузит её отдельно) —
для inbox-цикла достаточно последнего сообщения. Отправка ответов — только
через Playwright (см. скилл hh-inbox).

Выход: data/inbox.json + сводка в stdout.
"""
import argparse
import json
import pathlib

from hh_session import make_session, log

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG_URL = "https://chatik.hh.ru/api/chat/messages"


def fetch_chats(s) -> dict:
    r = s.get(CONFIG_URL, params={"chatId": "1"}, timeout=30,
              headers={"Accept": "application/json"})
    r.raise_for_status()
    cfg = r.json()
    return cfg["chats"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unread", action="store_true")
    args = ap.parse_args()

    applied = {a["id"]: a for a in json.loads((DATA / "applied.json").read_text())}

    s = make_session()
    ch = fetch_chats(s)
    items = ch["chats"]["items"]
    vac_res = (ch.get("resources") or {}).get("vacancies") or {}

    out = []
    for it in items:
        vac_ids = [int(v) for v in (it.get("resources") or {}).get("VACANCY", [])]
        vid = next((v for v in vac_ids if v in applied), None)
        if vid is None:
            continue
        lm = it.get("lastMessage") or {}
        wt = lm.get("workflowTransition") or {}
        pd = lm.get("participantDisplay") or {}
        vinfo = vac_res.get(str(vid)) or {}
        topic_ids = (it.get("resources") or {}).get("NEGOTIATION_TOPIC", [])
        mine = str(lm.get("participantId")) == str(it.get("currentParticipantId"))
        rec = {
            "vacancyId": vid,
            "vacancyName": vinfo.get("name", ""),
            "company": ((vinfo.get("company") or {}).get("visibleName")
                        or (vinfo.get("company") or {}).get("name", "")),
            "chatId": it["id"],
            "topicId": topic_ids[0] if topic_ids else None,
            "unread": it.get("unreadCount", 0),
            "state": wt.get("applicantState"),          # DISCARD / INTERVIEW / ...
            "lastMessage": {
                "time": lm.get("creationTime"),
                "text": (lm.get("text") or "")[:2000],
                "from": pd.get("name"),
                "isBot": pd.get("isBot", False),
                "isMine": mine,
            },
            "chatUrl": f"https://hh.ru/applicant/negotiations/item?topicId={topic_ids[0]}" if topic_ids else None,
        }
        if args.unread and not rec["unread"]:
            continue
        out.append(rec)

    out.sort(key=lambda r: (-(r["unread"] > 0), r["lastMessage"]["time"] or ""))
    (DATA / "inbox.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

    summary = {
        "chatsMatched": len(out),
        "unread": sum(1 for r in out if r["unread"]),
        "rejected": sum(1 for r in out if r["state"] == "DISCARD"),
        "awaitingMe": sum(1 for r in out if r["unread"] and not r["lastMessage"]["isMine"]),
        "out": str(DATA / "inbox.json"),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
