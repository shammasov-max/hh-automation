"""Входящие по разосланным откликам: новые сообщения работодателей.

Использование:
    python3 src/inbox.py            # все чаты по applied-откликам
    python3 src/inbox.py --unread   # только с непрочитанными

Канал (выстрадано@2026-07-09): chatik.hh.ru/api/chat/messages?chatId=<любой>
отдаёт SSR-конфиг, в котором chats.chats.items — чаты юзера с lastMessage,
unreadCount, workflowTransition.applicantState и participantDisplay.isBot.
⚠️ Отдаётся ТОЛЬКО ~20 последних чатов (выстрадано@2026-07-18: found=282,
пагинация мертва — nextFrom=null, page игнорируется); усечение видно в сводке
(chatsInConfig vs foundTotal). Полная история сообщений недоступна (SPA),
отправка ответов — только Playwright (см. скилл hh-inbox).

Выход: data/inbox.json (прошлый снимок → inbox-prev.json) + сводка в stdout.
Триггеры обработки: needsAttention (новое чужое сообщение после applied.lastContact —
unread не годится: гаснет от чтения с телефона) и stateChanged (diff с prev-снимком).
"""
import argparse
import datetime
import json
import pathlib
import time

from hh_session import make_session, get_lux_state, log

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG_URL = "https://chatik.hh.ru/api/chat/messages"


def fetch_chats(s) -> dict:
    r = s.get(CONFIG_URL, params={"chatId": "1"}, timeout=30,
              headers={"Accept": "application/json"})
    r.raise_for_status()
    cfg = r.json()
    return cfg["chats"]


def negotiations_pass(s, applied: dict, covered: set) -> list:
    """Полное покрытие: chatik-конфиг отдаёт лишь ~20 чатов, а negotiations
    пагинируется честно (найдено@2026-07-19: total/pageCount/page работают) —
    добираем applied-чаты вне chatik-снимка. lastMessage-текста здесь нет
    (source=negotiations) — его дочитает Playwright-субагент из чата."""
    extras = []
    page = 0
    while True:
        st = get_lux_state(s, "https://hh.ru/applicant/negotiations",
                           {"filter": "all", "page": str(page)})
        neg = st.get("applicantNegotiations") or {}
        topics = neg.get("topicList") or []
        if not topics:
            break
        names = {}
        for v in ((st.get("vacanciesShort") or {}).get("vacanciesList")) or []:
            c = v.get("company") or {}
            names[v.get("vacancyId")] = (v.get("name"),
                                         c.get("visibleName") or c.get("name"))
        for t in topics:
            vid = t.get("vacancyId")
            if vid not in applied or vid in covered:
                continue
            covered.add(vid)
            cursor = _naive(applied[vid].get("lastContact"))
            lm = _naive(t.get("lastModified"))
            nm, co = names.get(vid, (None, None))
            extras.append({
                "vacancyId": vid,
                "vacancyName": nm or applied[vid].get("name", ""),
                "company": co or applied[vid].get("company", ""),
                "chatId": t.get("chatId"),
                "topicId": str(t.get("id")),
                "unread": 1 if t.get("hasNewMessages") else 0,
                "state": t.get("lastState"),
                "lastMessage": None,
                "lastModified": t.get("lastModified"),
                "needsAttention": bool(t.get("hasNewMessages"))
                or (cursor is not None and lm is not None and lm > cursor),
                "source": "negotiations",
                "chatUrl": f"https://chatik.hh.ru/chat/{t.get('chatId')}",
            })
        page += 1
        if page >= int(neg.get("pageCount") or 0):
            break
        time.sleep(1.5)
    return extras


def _naive(ts: str | None) -> datetime.datetime | None:
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(ts).replace(tzinfo=None)
    except ValueError:
        return None


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
        lm_time = _naive(lm.get("creationTime"))
        cursor = _naive(applied[vid].get("lastContact"))
        needs = (not mine) and (cursor is None or (lm_time is not None and lm_time > cursor))
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
                "text": (lm.get("text") or "")[:2000],  # длиннее — субагент дочитает из чата
                "from": pd.get("name"),
                "isBot": pd.get("isBot", False),
                "isMine": mine,
            },
            "needsAttention": needs,
            # top-level chatik-URL: iframe на negotiations-странице — cross-origin
            # OOPIF, page.frames его не берёт (выстрадано@2026-07-10)
            "chatUrl": f"https://chatik.hh.ru/chat/{it['id']}",
        }
        if args.unread and not rec["unread"]:
            continue
        out.append(rec)

    extras = negotiations_pass(s, applied, {r["vacancyId"] for r in out})
    if args.unread:
        extras = [r for r in extras if r["unread"]]
    out.extend(extras)

    out.sort(key=lambda r: (-(r["unread"] > 0),
                            (r["lastMessage"] or {}).get("time") or r.get("lastModified") or ""))

    inbox_file, prev_file = DATA / "inbox.json", DATA / "inbox-prev.json"
    prev_states = {}
    if inbox_file.exists():
        try:
            prev = json.loads(inbox_file.read_text())
            prev_states = {r["vacancyId"]: r.get("state") for r in prev}
            prev_file.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
        except (ValueError, KeyError):
            pass
    state_changed = [r["vacancyId"] for r in out
                     if r["vacancyId"] in prev_states
                     and prev_states[r["vacancyId"]] != r["state"]]
    inbox_file.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    summary = {
        "chatsMatched": len(out),
        "chatikCovered": len(items),
        "negotiationsExtra": len(extras),
        "unread": sum(1 for r in out if r["unread"]),
        "needsAttention": sum(1 for r in out if r["needsAttention"]),
        "stateChanged": state_changed,
        "rejected": sum(1 for r in out if r["state"] == "DISCARD"),
        "out": str(inbox_file),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
