"""Отправка сообщения в чат hh.ru REST'ом, с race-check и dry-run.

Использование:
    python3 src/chat_send.py --chat-id N --text-file msg.txt --expect-last-id M   # dry-run
    python3 src/chat_send.py --chat-id N --text-file msg.txt --expect-last-id M --send

Гейты (механические; текстовые маркеры «бот закрыл диалог» — забота LLM ДО вызова):
- без --send ничего не уходит; dry-run обязателен первым (правило проекта);
- --expect-last-id ОБЯЗАТЕЛЕН (id последнего сообщения при классификации;
  race-check: появилось новее → отказ + newMessages). Пустая история → --expect-empty;
- writePossibility != ENABLED* → отказ (чат закрыт со стороны hh);
- статус-гейт: запись applied.json по chatId в status rejected/closed → отказ
  («молчание» правила@2026-07-13/@2026-07-19); осознанное исключение (отказ со
  встречным вопросом, после согласования) — флаг --override-status.

После успешной отправки:
- verify: re-GET истории (в try — сеть после отправки НЕ повод ретраить:
  result:sent при ЛЮБОМ verified означает «ушло, не повторять»);
- newAfterSend: чужие сообщения новее нашего (бот отвечает в ту же секунду) —
  обработать как attention, не терять;
- сам логирует в applied.json: dialog {user, a, text} + lastContact =
  creationTime СВОЕГО сообщения ('now' перешагнул бы мгновенный ответ бота,
  выстрадано@2026-07-19). Отключить: --no-log. Статус ставится отдельно
  (applied_log --status).
"""
import argparse
import datetime
import json
import sys
import time

from hh_session import make_session, get_xsrf, log
from chatik import chat_data, history, send
from applied_log import applied_store, APPLIED


def _naive_iso(ts: str) -> str:
    try:
        return (datetime.datetime.fromisoformat(ts)
                .astimezone().replace(tzinfo=None)
                .strftime("%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id", required=True, type=int)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--text-file")
    g.add_argument("--text")
    e = ap.add_mutually_exclusive_group(required=True)
    e.add_argument("--expect-last-id", type=int,
                   help="id последнего сообщения при классификации (race-check)")
    e.add_argument("--expect-empty", action="store_true",
                   help="история была пуста при классификации")
    ap.add_argument("--override-status", action="store_true",
                    help="писать несмотря на status rejected/closed (согласованный кейс)")
    ap.add_argument("--no-log", action="store_true")
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()

    text = (open(args.text_file, encoding="utf-8-sig").read()
            if args.text_file else args.text).strip()
    if not text:
        sys.exit("пустой текст")

    rec = None
    if APPLIED.exists():
        rec = next((a for a in json.loads(APPLIED.read_text())
                    if str(a.get("chatId")) == str(args.chat_id)), None)
    if rec and rec.get("status") in ("rejected", "closed") and not args.override_status:
        print(json.dumps({"result": "refused",
                          "reason": f"status={rec['status']} — молчание; "
                                    "осознанный кейс → --override-status"},
                         ensure_ascii=False))
        return

    s = make_session()
    chat = chat_data(s, args.chat_id)["chat"]
    hist = history(chat)
    wp = (chat.get("writePossibility") or {}).get("name") or ""
    last_id = hist[-1]["id"] if hist else None

    if not wp.startswith("ENABLED"):
        print(json.dumps({"result": "refused", "reason": f"writePossibility={wp}"},
                         ensure_ascii=False))
        return
    expect = None if args.expect_empty else args.expect_last_id
    if last_id != expect:
        fresh = [m for m in hist if (m["id"] or 0) > (expect or 0)]
        print(json.dumps({"result": "refused", "reason": "race: чат ушёл вперёд",
                          "newMessages": fresh}, ensure_ascii=False))
        return

    if not args.send:
        print(json.dumps({"result": "dry-run", "chatId": args.chat_id,
                          "lastId": last_id, "writePossibility": wp,
                          "status": rec.get("status") if rec else None,
                          "textLen": len(text), "preview": text[:200]},
                         ensure_ascii=False))
        return

    resp = send(s, get_xsrf(s), args.chat_id, text)
    ok = resp["status"] == 200 and isinstance(resp["body"], dict)
    if not ok:
        log(f"send fail: {resp['status']} {str(resp['body'])[:300]}")
        print(json.dumps({"result": "fail", "httpStatus": resp["status"]},
                         ensure_ascii=False))
        return

    sent_id = resp["body"].get("id")
    sent_at = _naive_iso(resp["body"].get("creationTime") or "")
    verified, new_after = "unknown", []
    try:
        time.sleep(2)
        hist2 = history(chat_data(s, args.chat_id)["chat"])
        verified = any(m["id"] == sent_id for m in hist2)
        new_after = [m for m in hist2
                     if (m["id"] or 0) > (sent_id or 0) and not m["mine"]]
    except Exception as ex:
        log(f"verify недоступен ({ex}) — сообщение УЖЕ отправлено, не повторять")

    logged = False
    if rec and not args.no_log:
        with applied_store() as applied:
            a = next((x for x in applied if x["id"] == rec["id"]), None)
            if a:
                a.setdefault("dialog", []).append(
                    {"at": sent_at, "from": "user", "kind": "a", "text": text})
                a["lastContact"] = sent_at
                logged = True

    print(json.dumps({"result": "sent", "messageId": sent_id, "at": sent_at,
                      "verified": verified, "newAfterSend": new_after,
                      "logged": logged}, ensure_ascii=False))


if __name__ == "__main__":
    main()
