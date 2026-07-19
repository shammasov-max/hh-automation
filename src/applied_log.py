"""Единственный правильный способ писать в data/applied.json (state-машина переписки).

Ручная правка JSON LLM'ом дала 21 набор ключей — потому весь лог только тут.

Использование:
    python3 src/applied_log.py --id 127181421 --status replied \
        --dialog-from user --dialog-kind a --dialog-text "текст ответа"
    python3 src/applied_log.py --id 127181421 --last-contact 2026-07-19T20:00:00
    python3 src/applied_log.py --create --id N --name "..." --company "..." \
        --resume senior-en [--letter-file f] [--topic-id T] [--chat-id C]

- --status: закрытый enum (STATUSES); новое значение = правка ЭТОГО файла.
- --last-contact: 'now' или ISO без таймзоны; голая дата/суффикс зоны — отказ
  (полночь и UTC-сдвиг дают вечный needsAttention, выстрадано@2026-07-19).
  ⚠️ 'now' годится ТОЛЬКО если после обработанного никто не писал; после отправки
  в чат курсор = creationTime СВОЕГО сообщения (бот отвечает в ту же секунду,
  'now' его перешагнёт и вопрос потеряется — chat_send.py логирует сам).
- --dialog-*: append одной записи {at, from, kind, text}; одна запись = один вызов.
- --create: новая запись (для hh-test-apply); отказ, если id уже есть.

Библиотечно: applied_store() — контекст с flock + атомарной записью (tmp +
os.replace). ВСЕ писатели applied.json (apply.py, inbox.py, chat_leave.py,
chat_send.py) обязаны ходить через него: четыре конкурентных read-modify-write
теряли записи, а kill посреди write_text оставлял битый JSON.
"""
import argparse
import contextlib
import datetime
import fcntl
import json
import os
import pathlib
import re
import sys

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
APPLIED = DATA / "applied.json"
LOCK = DATA / ".applied.lock"
STATUSES = {"sent", "replied", "awaiting_user", "interview", "rejected", "closed"}
FROMS = {"user", "employer", "bot", "system"}
KINDS = {"q", "a", "note", "event"}
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def now_iso() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


@contextlib.contextmanager
def applied_store():
    """Эксклюзивный read-modify-write applied.json: yield списка записей,
    по выходу — атомарная запись. Мутируй yielded-список на месте."""
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        data = json.loads(APPLIED.read_text()) if APPLIED.exists() else []
        yield data
        tmp = APPLIED.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        os.replace(tmp, APPLIED)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, type=int)
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--status", choices=sorted(STATUSES))
    ap.add_argument("--last-contact", default="now",
                    help="'now' или YYYY-MM-DDTHH:MM:SS (без зоны)")
    ap.add_argument("--dialog-from", choices=sorted(FROMS))
    ap.add_argument("--dialog-kind", choices=sorted(KINDS))
    ap.add_argument("--dialog-text")
    ap.add_argument("--name")
    ap.add_argument("--company")
    ap.add_argument("--resume")
    ap.add_argument("--letter-file")
    ap.add_argument("--topic-id")
    ap.add_argument("--chat-id", type=int)
    args = ap.parse_args()

    lc = now_iso() if args.last_contact == "now" else args.last_contact
    if not ISO_RE.match(lc):
        sys.exit(f"lastContact «{lc}»: нужен YYYY-MM-DDTHH:MM:SS без таймзоны")

    dialog_args = (args.dialog_from, args.dialog_kind, args.dialog_text)
    if any(dialog_args) and not all(dialog_args):
        sys.exit("--dialog-from/--dialog-kind/--dialog-text — только все вместе")

    with applied_store() as applied:
        rec = next((a for a in applied if a["id"] == args.id), None)

        if args.create:
            if rec is not None:
                sys.exit(f"{args.id} уже в applied.json — --create невозможен")
            if not (args.name and args.company and args.resume):
                sys.exit("--create требует --name --company --resume")
            rec = {"id": args.id, "result": "ok", "name": args.name,
                   "company": args.company, "resume": args.resume,
                   "letter": (open(args.letter_file, encoding="utf-8-sig").read().strip()
                              if args.letter_file else ""),
                   "status": args.status or "sent",
                   "topicId": args.topic_id, "chatId": args.chat_id,
                   "ts": now_iso()}
            applied.append(rec)
        elif rec is None:
            sys.exit(f"{args.id} нет в applied.json — новые записи: apply.py "
                     f"или --create (hh-test-apply)")

        if args.status:
            rec["status"] = args.status
        rec["lastContact"] = lc
        if args.dialog_text:
            rec.setdefault("dialog", []).append(
                {"at": lc, "from": args.dialog_from, "kind": args.dialog_kind,
                 "text": args.dialog_text})

    print(json.dumps({k: rec.get(k) for k in
                      ("id", "name", "company", "status", "lastContact")}
                     | {"dialogLen": len(rec.get("dialog") or [])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
