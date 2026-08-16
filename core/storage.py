import sys
import os
import json
from datetime import datetime
from .crypto import encrypt_value, decrypt_value, DATA_DIR

STATE_FILE = os.path.join(DATA_DIR, "state.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

DEFAULT_STATE = {
    "status": "ON",
    "is_outage": False,
    "address": "Не указан",
    "reason": "Електромережі працюють у штатному режимі",
    "start_time_str": None,
    "end_time_str": None,
    "start_timestamp": None,
    "end_timestamp": None,
    "total_seconds": None,
    "remaining_seconds": None,
    "elapsed_seconds": None,
    "progress_percent": 0.0,
    "raw_text": "",
    "updated_at": datetime.now().isoformat()
}

class StorageManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.state = self.load_state()

    def _decrypt_record(self, record: dict) -> dict:
        if not isinstance(record, dict):
            return record
        out = record.copy()
        if "address" in out:
            out["address"] = decrypt_value(out["address"])
        return out

    def _encrypt_record(self, record: dict) -> dict:
        if not isinstance(record, dict):
            return record
        out = record.copy()
        if "address" in out and out["address"]:
            out["address"] = encrypt_value(str(out["address"]))
        return out

    def load_state(self):
        if not os.path.exists(STATE_FILE):
            self.save_state(DEFAULT_STATE)
            return DEFAULT_STATE.copy()
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._decrypt_record(data)
        except Exception:
            return DEFAULT_STATE.copy()

    def save_state(self, state):
        self.state = state
        try:
            encrypted_state = self._encrypt_record(self.state)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(encrypted_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Storage] Error saving state: {e}")

    def get_state(self):
        return self.state

    def add_history(self, record):
        history = self.get_history()
        if "timestamp" not in record:
            record["timestamp"] = datetime.now().isoformat()
        history.insert(0, record)
        history = history[:100]
        try:
            encrypted_history = [self._encrypt_record(item) for item in history]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(encrypted_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Storage] Error saving history: {e}")

    def get_history(self, limit=50):
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [self._decrypt_record(item) for item in data[:limit]]
                return []
        except Exception:
            return []

    def clear_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[Storage] Error clearing history: {e}")
            return False
