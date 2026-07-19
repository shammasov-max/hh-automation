"""Отправка сообщения в чат hh.ru REST'ом, с race-check и dry-run.

Использование:
    python3 src/chat_send.py --chat-id N --text-file msg.txt                # dry-run
    python3 src/chat_send.py --chat-id N --text-file msg.txt \
        --expect-last-id 14818061153 --send                                 # отправка

Гейты (все механические; текстовые маркеры «бот закрыл диалог» — забота LLM ДО вызова):
- без --send ничего не уходит;
- writePossibility != ENABLED* → отказ (чат закрыт со стороны hh);
- --expect-last-id: id последнего сообщения чата на момент классификации;
  если в чате появилось что-то новее (ответили/юзер написал с телефона) →
  отказ, чат на переклассификацию. Без флага проверка пропускается — давать всегда.

Верификация: после отправки re-GET истории, новое сообщение по id.
"""
import argparse
import json
import sys
import time

from hh_session import make_session, get_xsrf, log
from chatik import chat_data, history, send


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id", required=True, type=int)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--text-file")
    g.add_argument("--text")
    ap.add_argument("--expect-last-id", type=int,
                    help="id последнего сообщения при классификации (race-check)")
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()

    text = (open(args.text_file).read() if args.text_file else args.text).strip()
    if not text:
        sys.exit("пустой текст")

    s = make_session()
    chat = chat_data(s, args.chat_id)["chat"]
    hist = history(chat)
    wp = (chat.get("writePossibility") or {}).get("name") or ""
    last_id = hist[-1]["id"] if hist else None

    if not wp.startswith("ENABLED"):
        print(json.dumps({"result": "refused", "reason": f"writePossibility={wp}"},
                         ensure_ascii=False))
        return
    if args.expect_last_id is not None and last_id != args.expect_last_id:
        fresh = [m for m in hist if m["id"] > args.expect_last_id]
        print(json.dumps({"result": "refused", "reason": "race: чат ушёл вперёд",
                          "newMessages": fresh}, ensure_ascii=False))
        return

    if not args.send:
        print(json.dumps({"result": "dry-run", "chatId": args.chat_id,
                          "lastId": last_id, "writePossibility": wp,
                          "textLen": len(text), "preview": text[:200]},
                         ensure_ascii=False))
        return

    resp = send(s, get_xsrf(s), args.chat_id, text)
    ok = resp["status"] == 200 and isinstance(resp["body"], dict)
    sent_id = resp["body"].get("id") if ok else None
    verified = False
    if ok:
        time.sleep(2)
        verified = any(m["id"] == sent_id
                       for m in history(chat_data(s, args.chat_id)["chat"]))
    else:
        log(f"send fail: {resp['status']} {str(resp['body'])[:300]}")
    print(json.dumps({"result": "sent" if ok else "fail", "messageId": sent_id,
                      "verified": verified, "httpStatus": resp["status"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
