"""Единственный правильный способ писать в data/applied.json (state-машина переписки).

Ручная правка JSON LLM'ом дала 5 разных наборов ключей — потому весь лог только тут.

Использование:
    python3 src/applied_log.py --id 127181421 --status replied \
        --dialog-from user --dialog-kind a --dialog-text "текст ответа"
    python3 src/applied_log.py --id 127181421 --last-contact now      # только курсор

- --status: закрытый enum (см. STATUSES); новое значение = правка ЭТОГО файла.
- --last-contact: 'now' (дефолт при любой записи) или ISO без таймзоны;
  голая дата/суффикс зоны — отказ (полночь и UTC-сдвиг дают вечный needsAttention,
  выстрадано@2026-07-19).
- --dialog-*: append одной записи схемы {at, from, kind, text}.
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
STATUSES = {"sent", "replied", "awaiting_user", "interview", "rejected", "closed"}
FROMS = {"user", "employer", "bot", "system"}
KINDS = {"q", "a", "note", "event"}
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def now_iso() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, type=int)
    ap.add_argument("--status", choices=sorted(STATUSES))
    ap.add_argument("--last-contact", default="now",
                    help="'now' или YYYY-MM-DDTHH:MM:SS (без зоны)")
    ap.add_argument("--dialog-from", choices=sorted(FROMS))
    ap.add_argument("--dialog-kind", choices=sorted(KINDS))
    ap.add_argument("--dialog-text")
    args = ap.parse_args()

    lc = now_iso() if args.last_contact == "now" else args.last_contact
    if not ISO_RE.match(lc):
        sys.exit(f"lastContact «{lc}»: нужен YYYY-MM-DDTHH:MM:SS без таймзоны")

    dialog_args = (args.dialog_from, args.dialog_kind, args.dialog_text)
    if any(dialog_args) and not all(dialog_args):
        sys.exit("--dialog-from/--dialog-kind/--dialog-text — только все вместе")

    f = DATA / "applied.json"
    applied = json.loads(f.read_text())
    rec = next((a for a in applied if a["id"] == args.id), None)
    if rec is None:
        sys.exit(f"{args.id} нет в applied.json — отклики создаёт apply.py, не этот скрипт")

    if args.status:
        rec["status"] = args.status
    rec["lastContact"] = lc
    if args.dialog_text:
        rec.setdefault("dialog", []).append(
            {"at": lc, "from": args.dialog_from, "kind": args.dialog_kind,
             "text": args.dialog_text})

    f.write_text(json.dumps(applied, ensure_ascii=False, indent=1))
    print(json.dumps({k: rec.get(k) for k in
                      ("id", "name", "company", "status", "lastContact")}
                     | {"dialogLen": len(rec.get("dialog") or [])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
