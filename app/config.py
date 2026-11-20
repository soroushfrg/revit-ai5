import copy
import json
import os

APP_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "RevitAgent")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

DEFAULTS = {
    "user_name": "",
    "language": "fa",
    "server_url": "https://jesusisgood.shop/revitupdate/api",
    "session_token": "",
    "username": "",
    "models": [],
    "model_name": "",
    "remaining": None,
    "reset_at": 0,
    "forced_model": "",
    "used": 0,
    "limit": 0,
    "window_cost": 0,
    "lifetime_cost": 0,
    "stt_language": "fa",
    "bridge_dir": os.path.join(APP_DIR, "bridge"),
    "backup_dir": os.path.join(APP_DIR, "backups"),
    "require_approval": True,
    "max_retries": 3,
    "job_timeout_sec": 600,
    "update_url": "https://jesusisgood.shop/revitupdate/app.json",
}


def load_config():
    os.makedirs(APP_DIR, exist_ok=True)
    cfg = copy.deepcopy(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    if not cfg.get("update_url"):
        cfg["update_url"] = DEFAULTS["update_url"]
    return cfg


def save_config(cfg):
    os.makedirs(APP_DIR, exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)
