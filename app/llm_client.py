import requests


class LLMError(Exception):
    pass


def _base(cfg):
    return cfg["server_url"].rstrip("/")


def _auth(cfg):
    return {"Authorization": f"Bearer {cfg.get('session_token', '')}"}


def _check(r):
    try:
        data = r.json()
    except Exception:
        raise LLMError(f"پاسخ نامعتبر از سرور (HTTP {r.status_code})")
    if r.status_code == 401:
        raise LLMError(data.get("error") or "نشست شما منقضی شده. دوباره وارد شوید.")
    if not data.get("ok"):
        raise LLMError(data.get("error") or f"HTTP {r.status_code}")
    return data


def login_user(cfg, username, password):
    r = requests.post(_base(cfg) + "/login.php",
                      json={"username": username, "password": password}, timeout=20)
    return _check(r)


def fetch_me(cfg):
    r = requests.get(_base(cfg) + "/me.php", headers=_auth(cfg), timeout=20)
    return _check(r)


def apply_me(cfg, me):
    """Copy the account state from the server into the local config."""
    cfg["models"] = me.get("models", [])
    cfg["forced_model"] = me.get("forced_model", "")
    cfg["used"] = me.get("used", 0)
    cfg["limit"] = me.get("limit", 0)
    cfg["remaining"] = me.get("remaining", 0)
    cfg["reset_at"] = me.get("reset_at", 0)
    cfg["window_cost"] = me.get("window_cost", 0)
    cfg["lifetime_cost"] = me.get("lifetime_cost", 0)
    if cfg.get("model_name") not in cfg["models"]:
        cfg["model_name"] = cfg["models"][0] if cfg["models"] else ""


def chat(cfg, messages, timeout=240):
    r = requests.post(
        _base(cfg) + "/chat.php",
        headers={**_auth(cfg), "Content-Type": "application/json"},
        json={"model": cfg["model_name"].strip(), "messages": messages},
        timeout=timeout,
    )
    data = _check(r)
    cfg["used"] = data.get("used", cfg.get("used"))
    cfg["remaining"] = data.get("remaining", cfg.get("remaining"))
    return data.get("content", "")


def transcribe(cfg, wav_path, timeout=180):
    with open(wav_path, "rb") as f:
        r = requests.post(
            _base(cfg) + "/transcribe.php",
            headers=_auth(cfg),
            files={"file": ("speech.wav", f, "audio/wav")},
            data={"language": cfg.get("stt_language", "fa")},
            timeout=timeout,
        )
    return _check(r).get("text", "")
