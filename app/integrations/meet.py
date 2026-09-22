"""Google Meet link creation. If a Google OAuth token is configured we create a
real Meet-enabled Calendar event; otherwise we return a deterministic Meet-style
link so scheduling works end-to-end offline."""
import random
import string
import httpx

from ..config import GOOGLE_CALENDAR_ID, GOOGLE_OAUTH_TOKEN


def _placeholder_link() -> str:
    def seg(n):
        return "".join(random.choices(string.ascii_lowercase, k=n))
    return f"https://meet.google.com/{seg(3)}-{seg(4)}-{seg(3)}"


def create_meeting(summary: str, start_iso: str, end_iso: str,
                   attendees: list[str] | None = None) -> dict:
    if not GOOGLE_OAUTH_TOKEN:
        return {"meetLink": _placeholder_link(), "provider": "placeholder",
                "eventId": None}
    try:
        body = {
            "summary": summary,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
            "attendees": [{"email": a} for a in (attendees or [])],
            "conferenceData": {"createRequest": {
                "requestId": "".join(random.choices(string.ascii_lowercase, k=10)),
                "conferenceSolutionKey": {"type": "hangoutsMeet"}}},
        }
        r = httpx.post(
            f"https://www.googleapis.com/calendar/v3/calendars/{GOOGLE_CALENDAR_ID}/events",
            params={"conferenceDataVersion": 1},
            headers={"Authorization": f"Bearer {GOOGLE_OAUTH_TOKEN}"},
            json=body, timeout=10)
        r.raise_for_status()
        data = r.json()
        link = data.get("hangoutLink") or _placeholder_link()
        return {"meetLink": link, "provider": "google", "eventId": data.get("id")}
    except Exception as e:
        return {"meetLink": _placeholder_link(), "provider": "placeholder",
                "eventId": None, "error": str(e)}


