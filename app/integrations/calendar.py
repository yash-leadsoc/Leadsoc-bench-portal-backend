"""Availability calendar. Availability is stored on employees; this assembles a
calendar view and (optionally) merges Google Calendar busy blocks."""
from ..config import GOOGLE_OAUTH_TOKEN


def availability_events(db, bu: str | None = None) -> list[dict]:
    q = {} if not bu else {"bu": bu}
    events = []
    for e in db["employees"].find(q):
        for slot in e.get("availability", []):
            events.append({
                "employeeId": e["_id"], "employeeName": e.get("name"),
                "bu": e.get("bu"), "date": slot.get("date"),
                "start": slot.get("start"), "end": slot.get("end"),
                "status": slot.get("status", "free")})
    events.sort(key=lambda x: (x.get("date") or "", x.get("start") or ""))
    return events


def google_connected() -> bool:
    return bool(GOOGLE_OAUTH_TOKEN)
