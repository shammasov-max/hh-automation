"""Входящие по разосланным откликам: новые сообщения работодателей.

Использование:
    python3 src/inbox.py        # полный проход, сводка в stdout — рабочий вход скилла

Каналы (найдено@2026-07-19):
- hh.ru/applicant/negotiations?filter=all&page=N — пагинация честная
  (total/pageCount), даёт ВСЕ отклики: state/lastModified/hasNewMessages/chatId
  + имена из vacanciesShort. Старый SSR-конфиг chatik (~20 чатов) не нужен.
- chatik.hh.ru/chatik/api/chat_data (src/chatik.py) — полная история чата;
  дёргается только для кандидатов на обработку, история кладётся в запись.

Триггеры обработки (сводка: attention[]):
- needsAttention: чужое сообщение новее курсора. Курсор = applied.lastContact;
  если его нет и status=sent — фолбэк на ts отклика (иначе ответ работодателя,
  прочитанный юзером с телефона, невидим навсегда). hh-флаг hasNewMessages
  решает только при полном отсутствии курсора: он гаснет лишь открытием чата,
  а рунг МОЛЧАНИЕ чат не открывает → вечный залип (выстрадано@2026-07-19).
- stateMismatch: state hh противоречит applied.status (INTERVIEW/DISCARD).
  DISCARD логируется в rejected автоматом (терминальный, ответ запрещён
  правилом@2026-07-13); INTERVIEW — в attention, решает LLM/юзер, но только
  при status sent/replied: awaiting_user уже в сводке, closed — решение юзера
  бросить чат, вечный mismatch-флаг был бы шумом.

Выход: data/inbox.json (полный снимок с history у кандидатов) + сводка stdout.
Отправка ответов: src/chat_send.py (REST); Playwright — только кнопки бота/анкеты.
"""
import datetime
import json
import pathlib
import time

from hh_session import make_session, get_lux_state, log
from chatik import chat_data, history
from applied_log import applied_store, now_iso

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PAGE_THROTTLE = 1.5
CHAT_THROTTLE = 1.0
# state hh ↔ терминальный/особый локальный статус
STATE_STATUS = {"DISCARD": "rejected", "INTERVIEW": "interview"}


def _naive(ts) -> datetime.datetime | None:
    """ISO → naive ЛОКАЛЬНОЕ время (aware конвертируется, не срезается:
    голый strip таймзоны при hh-переходе на UTC дал бы окно слепоты −3ч)."""
    if not ts:
        return None
    try:
        dt = datetime.datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def negotiations(s, applied: dict) -> list[dict]:
    """Все applied-топики из пагинации negotiations."""
    out, page, seen = [], 0, set()
    while True:
        st = get_lux_state(s, "https://hh.ru/applicant/negotiations",
                           {"filter": "all", "page": str(page)})
        neg = st.get("applicantNegotiations") or {}
        topics = neg.get("topicList") or []
        if not topics:
            break
        if page == 0 and neg.get("pageCount") is None:
            log("⚠️ negotiations без pageCount — дрейф формата hh? Возможен обрыв на 1-й странице")
        names = {}
        for v in ((st.get("vacanciesShort") or {}).get("vacanciesList")) or []:
            c = v.get("company") or {}
            names[v.get("vacancyId")] = (v.get("name"),
                                         c.get("visibleName") or c.get("name"))
        for t in topics:
            vid = t.get("vacancyId")
            if vid not in applied or vid in seen:
                continue
            seen.add(vid)
            nm, co = names.get(vid, (None, None))
            cid = t.get("chatId")
            out.append({
                "vacancyId": vid,
                "vacancyName": nm or applied[vid].get("name") or "",
                "company": co or applied[vid].get("company") or "",
                "chatId": cid,
                "topicId": str(t.get("id")),
                "state": t.get("lastState"),
                "hasNewMessages": bool(t.get("hasNewMessages")),
                "lastModified": t.get("lastModified"),
                # top-level chatik-URL для Playwright-веток: iframe на negotiations
                # — cross-origin OOPIF, page.frames не берёт (выстрадано@2026-07-10)
                "chatUrl": f"https://chatik.hh.ru/chat/{cid}" if cid else None,
            })
        page += 1
        try:
            if page >= int(neg.get("pageCount") or 0):
                break
        except (ValueError, TypeError):
            break
        time.sleep(PAGE_THROTTLE)
    return out


def main():
    applied_file = DATA / "applied.json"
    applied = {a["id"]: a for a in json.loads(applied_file.read_text())}

    s = make_session()
    records = negotiations(s, applied)

    backfills, candidates, unparsed_lm = {}, [], 0
    for r in records:
        a = applied[r["vacancyId"]]
        # backfill имён в старые записи (до details_info-эры)
        if not a.get("name") and r["vacancyName"]:
            a["name"], a["company"] = r["vacancyName"], r["company"]
            backfills[r["vacancyId"]] = (r["vacancyName"], r["company"])
        cursor = _naive(a.get("lastContact"))
        if cursor is None and a.get("status") == "sent":
            cursor = _naive(a.get("ts"))       # фолбэк: время отклика
        lm = _naive(r["lastModified"])
        if lm is None and r["lastModified"]:
            unparsed_lm += 1
        target = STATE_STATUS.get(r["state"])
        r["stateMismatch"] = bool(target) and a.get("status") != target \
            and (r["state"] != "INTERVIEW" or a.get("status") in ("sent", "replied"))
        maybe_new = (lm is not None and cursor is not None and lm > cursor) \
            or (cursor is None and r["hasNewMessages"])
        if (maybe_new or r["stateMismatch"]) and r["chatId"]:
            candidates.append(r)
    if unparsed_lm:
        log(f"⚠️ lastModified не парсится у {unparsed_lm} записей — дрейф формата hh?")

    auto_rejected, quiet_stamp = [], []
    for r in candidates:
        a = applied[r["vacancyId"]]
        cursor = _naive(a.get("lastContact"))
        try:
            chat = chat_data(s, r["chatId"]).get("chat") or {}
            hist = history(chat)
            r["history"] = hist
            r["unread"] = chat.get("unreadCount", 0)
            r["writePossibility"] = (chat.get("writePossibility") or {}).get("name")
            foreign = [_naive(m["at"]) for m in hist if not m["mine"]]
            last_foreign = max((t for t in foreign if t), default=None)
            r["needsAttention"] = last_foreign is not None and \
                (cursor is None or last_foreign > cursor)
            if r["state"] == "DISCARD" and a.get("status") != "rejected":
                # пустая/битая история → курсор не двигаем: текст отказа (и
                # возможный встречный вопрос) обязан всплыть в attention
                a["status"] = "rejected"
                a.setdefault("dialog", []).append(
                    {"at": now_iso(), "from": "system", "kind": "event",
                     "text": "hh state → DISCARD (авто-лог inbox.py)"})
                if not (r["needsAttention"] or not hist):
                    a["lastContact"] = now_iso()
                auto_rejected.append(r["vacancyId"])
                r["stateMismatch"] = False
            elif not (r["needsAttention"] or r["stateMismatch"]):
                # чат просмотрен целиком, нового чужого нет → гасим кандидата
                # (иначе fallback-курсор по ts перепроверял бы его каждый прогон)
                quiet_stamp.append(r["vacancyId"])
        except Exception as ex:
            r["error"] = f"{type(ex).__name__}: {ex}"
            log(f"⚠️ чат {r['chatId']} ({r['vacancyId']}): {r['error']} — пропущен")
        time.sleep(CHAT_THROTTLE)

    if auto_rejected or backfills or quiet_stamp:
        with applied_store() as fresh:       # merge в свежий файл: параллельный
            by_id = {a["id"]: a for a in fresh}   # apply.py не должен потеряться
            for vid in auto_rejected:
                src, dst = applied[vid], by_id.get(vid)
                if dst:
                    dst["status"] = src["status"]
                    dst["dialog"] = src.get("dialog")
                    if src.get("lastContact"):
                        dst["lastContact"] = src["lastContact"]
            for vid, (nm, co) in backfills.items():
                if by_id.get(vid):
                    by_id[vid]["name"], by_id[vid]["company"] = nm, co
            for vid in quiet_stamp:
                if by_id.get(vid):
                    by_id[vid]["lastContact"] = now_iso()

    for r in records:
        r.setdefault("needsAttention", False)
        r.setdefault("stateMismatch", False)

    (DATA / "inbox.json").write_text(json.dumps(records, ensure_ascii=False, indent=1))

    attention = [{
        "vacancyId": r["vacancyId"], "name": r["vacancyName"], "company": r["company"],
        "chatId": r["chatId"], "chatUrl": r["chatUrl"],
        "state": r["state"], "status": applied[r["vacancyId"]].get("status"),
        "needsAttention": r["needsAttention"], "stateMismatch": r["stateMismatch"],
        "unread": r.get("unread", 0), "error": r.get("error"),
        "lastMsg": (r.get("history") or [None])[-1],
    } for r in records if r["needsAttention"] or r["stateMismatch"] or r.get("error")]

    awaiting = [{"id": a["id"], "name": a.get("name"), "company": a.get("company"),
                 "since": a.get("lastContact") or a.get("ts")}
                for a in applied.values() if a.get("status") == "awaiting_user"]

    print(json.dumps({
        "total": len(records),
        "checked": len(candidates),
        "attention": attention,
        "autoRejected": auto_rejected,
        "awaitingUser": awaiting,
        "out": str(DATA / "inbox.json"),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
