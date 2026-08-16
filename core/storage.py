import sys
import os
import json
from datetime import datetime
from .crypto import encrypt_value, decrypt_value, DATA_DIR

STATE_FILE = os.path.join(DATA_DIR, "state.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
DAILY_FILE = os.path.join(DATA_DIR, "daily_stats.json")

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
        self._ensure_daily_stats_migrated()

    def _ensure_daily_stats_migrated(self):
        stats = self.load_daily_stats()
        history = self.get_history(limit=500)
        changed = False
        for item in history:
            ts = item.get("timestamp") or item.get("updated_at")
            if ts:
                d_str = ts.split("T")[0]
                if d_str not in stats:
                    stats[d_str] = {"recorded": True, "count": 0, "offSec": 0, "status": "ON"}
                    changed = True
                if item.get("status") == "OFF":
                    stats[d_str]["status"] = "OFF"
                    stats[d_str]["count"] = stats[d_str].get("count", 0) + 1
                    tot = item.get("total_seconds") or 3600
                    stats[d_str]["offSec"] = stats[d_str].get("offSec", 0) + tot
                    changed = True
        if changed:
            self.save_daily_stats(stats)

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
            d_str = datetime.now().strftime("%Y-%m-%d")
            self.update_daily_activity(d_str, state.get("status", "ON"))
        except Exception as e:
            print(f"[Storage] Error saving state: {e}")

    def get_state(self):
        return self.state

    def load_daily_stats(self):
        if not os.path.exists(DAILY_FILE):
            return {}
        try:
            with open(DAILY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save_daily_stats(self, stats):
        try:
            with open(DAILY_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Storage] Error saving daily stats: {e}")

    def update_daily_activity(self, date_str: str, status: str, off_seconds: int = 0):
        stats = self.load_daily_stats()
        if date_str not in stats:
            stats[date_str] = {"recorded": True, "count": 0, "offSec": 0, "status": "ON"}
        entry = stats[date_str]
        entry["recorded"] = True
        if status == "OFF":
            entry["status"] = "OFF"
            entry["count"] = entry.get("count", 0) + 1
            if off_seconds > 0:
                entry["offSec"] = entry.get("offSec", 0) + off_seconds
            else:
                entry["offSec"] = max(entry.get("offSec", 0), 3600)
        self.save_daily_stats(stats)
        return stats

    def add_history(self, record):
        history = self.get_history(limit=500)
        now_iso = datetime.now().isoformat()
        if "timestamp" not in record:
            record["timestamp"] = now_iso
        
        d_str = (record.get("timestamp") or now_iso).split("T")[0]
        off_sec = record.get("total_seconds") or 0
        self.update_daily_activity(d_str, record.get("status", "ON"), off_sec)

        # Skip duplicate ON entry if previous was ON within 10 minutes
        if history and record.get("status") == "ON" and history[0].get("status") == "ON":
            try:
                prev_ts = datetime.fromisoformat(history[0].get("timestamp", ""))
                curr_ts = datetime.fromisoformat(record.get("timestamp", ""))
                if (curr_ts - prev_ts).total_seconds() < 600:
                    return
            except Exception:
                pass

        history.insert(0, record)
        history = history[:500]
        try:
            encrypted_history = [self._encrypt_record(item) for item in history]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(encrypted_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Storage] Error saving history: {e}")

    def get_history(self, limit=200):
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
