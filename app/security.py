import base64, hashlib, hmac, json, os, time
from .config import SECRET, TOKEN_HOURS


def _b64(b): return base64.urlsafe_b64encode(b).rstrip(b"=")
def _unb64(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_hex), 100_000)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def create_token(payload: dict) -> str:
    body = dict(payload); body["exp"] = int(time.time()) + TOKEN_HOURS * 3600
    header = {"alg": "HS256", "typ": "JWT"}
    seg = _b64(json.dumps(header, separators=(",", ":")).encode()) + b"." + \
        _b64(json.dumps(body, separators=(",", ":")).encode())
    sig = hmac.new(SECRET.encode(), seg, hashlib.sha256).digest()
    return (seg + b"." + _b64(sig)).decode()


def decode_token(token: str):
    try:
        h, p, s = token.split(".")
        signing = f"{h}.{p}".encode()
        expected = _b64(hmac.new(SECRET.encode(), signing, hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(expected, s):
            return None
        payload = json.loads(_unb64(p))
        if payload.get("exp") and payload["exp"] < time.time():
            return None
        return payload
    except Exception:
        return None
