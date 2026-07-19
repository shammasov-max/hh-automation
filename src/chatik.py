"""REST API чатика hh.ru (найдено@2026-07-19 грепом чанков remote.chatik.*.js).

Эндпоинты (куки залогиненного Chrome, как везде):
- GET  chatik.hh.ru/chatik/api/chat_data?chatId=N — полная история чата:
  chat.messages.items[] (id/text/creationTime/participantId/participantDisplay/
  workflowTransition), chat.currentParticipantId (mine-check),
  chat.writePossibility, chat.unreadCount. hasMore не встречался (вся история).
- POST chatik.hh.ru/chatik/api/send  JSON {chatId, idempotencyKey: uuid, text}
  (+ metadata обязательна при chat.type BOT|SUPPORT — для NEGOTIATION не нужна;
  подтверждено живой отправкой@2026-07-19) → JSON нового сообщения с id.

Старый канал (SSR-конфиг /api/chat/messages, ~20 чатов) этим заменён полностью.
"""
import uuid

CHAT_DATA_URL = "https://chatik.hh.ru/chatik/api/chat_data"
SEND_URL = "https://chatik.hh.ru/chatik/api/send"


def chat_data(s, chat_id) -> dict:
    r = s.get(CHAT_DATA_URL, params={"chatId": chat_id}, timeout=30,
              headers={"Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def history(chat: dict, text_cap: int = 1500) -> list[dict]:
    """Нормализованная история из chat_data()['chat'] — компакт для LLM."""
    me = chat.get("currentParticipantId")
    out = []
    for m in (chat.get("messages") or {}).get("items") or []:
        pd = m.get("participantDisplay") or {}
        text = m.get("text") or ""
        if len(text) > text_cap:
            text = text[:text_cap] + "…[обрезано]"
        out.append({
            "id": m.get("id"),
            "at": m.get("creationTime"),
            "mine": m.get("participantId") == me,
            "bot": pd.get("isBot", False),
            "name": pd.get("name"),
            "state": (m.get("workflowTransition") or {}).get("applicantState"),
            "text": text,
        })
    return out


def send(s, xsrf: str, chat_id, text: str) -> dict:
    r = s.post(SEND_URL, timeout=30,
               json={"chatId": int(chat_id), "idempotencyKey": str(uuid.uuid4()),
                     "text": text},
               headers={"X-Xsrftoken": xsrf, "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                        "Origin": "https://chatik.hh.ru",
                        "Referer": f"https://chatik.hh.ru/chat/{chat_id}"})
    out = {"status": r.status_code}
    try:
        out["body"] = r.json()
    except Exception:
        out["body"] = r.text[:500]
    return out
