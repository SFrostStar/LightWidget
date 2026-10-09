import sys
import os
import json
import time
import threading
from datetime import datetime
from .crypto import encrypt_value ,decrypt_value ,DATA_DIR

STATE_FILE =os .path .join (DATA_DIR ,"state.json")
HISTORY_FILE =os .path .join (DATA_DIR ,"history.json")
DAILY_FILE =os .path .join (DATA_DIR ,"daily_stats.json")

DEFAULT_STATE ={
"status":"ON",
"is_outage":False ,
"is_planned":False ,
"planned_outages":[],
"blocked_planned_outages":[],
"address":"Не указан",
"reason":"Електромережі працюють у штатному режимі",
"start_time_str":None ,
"end_time_str":None ,
"start_timestamp":None ,
"end_timestamp":None ,
"total_seconds":None ,
"remaining_seconds":None ,
"elapsed_seconds":None ,
"progress_percent":0.0 ,
"light_on_since":None ,
"raw_text":"",
"updated_at":None
}

class StorageManager :
    def __init__ (self ):
        self ._state_lock =threading .RLock ()
        os .makedirs (DATA_DIR ,exist_ok =True )
        self .state =DEFAULT_STATE .copy ()
        self .state =self .load_state ()
        if isinstance (self .state ,dict )and self .state .get ("status")=="ON"and not self .state .get ("light_on_since"):
            self .state ["light_on_since"]=int (time .time ()*1000 )
            self .save_state (self .state )
        self ._ensure_daily_stats_migrated ()

    def _ensure_daily_stats_migrated (self ):
        stats =self .load_daily_stats ()
        history =self .get_history (limit =500 )
        changed =False
        for item in history :
            ts =item .get ("timestamp")or item .get ("updated_at")
            if ts :
                d_str =ts .split ("T")[0 ]
                if d_str not in stats :
                    stats [d_str ]={"recorded":True ,"count":0 ,"offSec":0 ,"status":"ON"}
                    changed =True
                if item .get ("status")=="OFF":
                    stats [d_str ]["status"]="OFF"
                    stats [d_str ]["count"]=stats [d_str ].get ("count",0 )+1
                    tot =item .get ("total_seconds")or 3600
                    stats [d_str ]["offSec"]=stats [d_str ].get ("offSec",0 )+tot
                    changed =True
        if changed :
            self .save_daily_stats (stats )

    def _decrypt_record (self ,record :dict )->dict :
        if not isinstance (record ,dict ):
            return record
        out =record .copy ()
        if "address"in out :
            out ["address"]=decrypt_value (out ["address"])
        return out

    def _encrypt_record (self ,record :dict )->dict :
        if not isinstance (record ,dict ):
            return record
        out =record .copy ()
        if "address"in out and out ["address"]:
            out ["address"]=encrypt_value (str (out ["address"]))
        return out

    def load_state (self ):
        if not os .path .exists (STATE_FILE ):
            self .save_state (DEFAULT_STATE )
            return DEFAULT_STATE .copy ()
        try :
            with open (STATE_FILE ,"r",encoding ="utf-8")as f :
                data =json .load (f )
                return self ._decrypt_record (data )
        except Exception :
            return DEFAULT_STATE .copy ()

    def _is_planned_blocked (self ,item ,blocked ):
        return any (entry .get ("start_timestamp")==item .get ("start_timestamp")and (entry .get ("end_timestamp")is None or entry .get ("end_timestamp")==item .get ("end_timestamp"))for entry in blocked )

    def save_state (self ,state ):
        with self ._state_lock :
            return self ._save_state (state )

    def _save_state(self, state, replace_blocked=False):
        if not isinstance(state, dict):
            return self.state
        state = state.copy()
        now_ts = int(time.time())
        previous = getattr(self, "state", None) or {}
        power_update = state.pop("_power_update", True)
        outage_update = state.pop("_outage_update", False)
        planned_changes = state.pop("_planned_changes", [])
        incoming_plans = state.get("planned_outages", []) or []
        blocked = [] if replace_blocked else list(previous.get("blocked_planned_outages", []))
        for entry in state.get("blocked_planned_outages", []):
            if entry not in blocked:
                blocked.append(entry)
        if not power_update and previous:
            incoming = state
            state = previous.copy()
            for key in ("raw_text", "updated_at", "timestamp", "address"):
                if incoming.get(key) and incoming[key] != "Не указан":
                    state[key] = incoming[key]
        elif outage_update and previous.get("status") == "OFF":
            if not state.get("start_timestamp"):
                state["start_timestamp"] = previous.get("start_timestamp")
                state["start_time_str"] = previous.get("start_time_str")
                state["reason"] = previous.get("reason") or state.get("reason")
            start = state.get("start_timestamp")
            end = state.get("end_timestamp")
            if start and end and end <= start:
                state["end_timestamp"] = previous.get("end_timestamp")
                state["end_time_str"] = previous.get("end_time_str")
                end = state["end_timestamp"]
            if start and end:
                state["total_seconds"] = max(0, end - start)
                state["elapsed_seconds"] = max(0, now_ts - start)
                state["remaining_seconds"] = max(0, end - now_ts)
                state["progress_percent"] = min(100.0, state["elapsed_seconds"] / state["total_seconds"] * 100) if state["total_seconds"] else 0.0
        plans = {}
        for item in previous.get("planned_outages", []) or []:
            if isinstance(item, dict) and item.get("start_timestamp"):
                plans[item["start_timestamp"]] = item
        for item in incoming_plans:
            if isinstance(item, dict) and item.get("start_timestamp"):
                plans[item["start_timestamp"]] = item
        for change in planned_changes:
            if change.get("action") == "cancel":
                start = change.get("start_timestamp")
                if start is None:
                    plans.clear()
                else:
                    plans.pop(start, None)
            elif change.get("action") == "upsert":
                item = change.get("item", {})
                if item.get("start_timestamp"):
                    plans[item["start_timestamp"]] = item
        valid_planned = [item for item in plans.values() if item.get("end_timestamp") and item["end_timestamp"] > now_ts and item["end_timestamp"] > item["start_timestamp"] and not self._is_planned_blocked(item, blocked)]
        valid_planned.sort(key=lambda item: item["start_timestamp"])
        if state.get("status") == "OFF" and state.get("end_timestamp") and state["end_timestamp"] <= now_ts:
            state["status"] = "ON"
            state["light_on_since"] = state["end_timestamp"] * 1000
        state["planned_outages"] = valid_planned
        state["blocked_planned_outages"] = blocked
        state["is_outage"] = state.get("status") == "OFF"
        state["is_planned"] = bool(valid_planned and not state["is_outage"])
        state["planned_active"] = False
        if state["is_planned"]:
            nearest = valid_planned[0]
            for key in ("start_timestamp", "end_timestamp", "start_time_str", "end_time_str"):
                state[key] = nearest.get(key)
            state["planned_active"] = nearest["start_timestamp"] <= now_ts < nearest["end_timestamp"]
        elif not state["is_outage"]:
            for key in ("start_timestamp", "end_timestamp", "start_time_str", "end_time_str", "total_seconds", "remaining_seconds", "elapsed_seconds"):
                state[key] = None
            state["progress_percent"] = 0.0
            state["reason"] = "Электросеть работает в штатном режиме."
        if state["is_outage"]:
            state["light_on_since"] = None
        elif not state.get("light_on_since"):
            state["light_on_since"] = previous.get("light_on_since") if previous.get("status") == "ON" else None
            state["light_on_since"] = state["light_on_since"] or int(time.time() * 1000)
        self.state = state
        try:
            encrypted_state = self._encrypt_record(self.state)
            with open(STATE_FILE, "w", encoding="utf-8") as file:
                json.dump(encrypted_state, file, ensure_ascii=False, indent=2)
        except Exception as error:
            print(f"[Storage] Error saving state: {error}")
        return self.state

    def get_state (self ):
        with self ._state_lock :
            if self .state .get ("status")=="OFF"and self .state .get ("end_timestamp")and self .state ["end_timestamp"]<=time .time ():
                return self .save_state (self .state )
            return self .state

    def delete_planned_outage (self ,start_timestamp :int ,end_timestamp :int =None ):
        with self ._state_lock :
            state =self .state .copy ()
            blocked =list (state .get ("blocked_planned_outages",[]))
            entry ={"start_timestamp":int (start_timestamp ),"end_timestamp":int (end_timestamp )if end_timestamp is not None else None }
            if entry not in blocked :
                blocked .append (entry )
            state ["blocked_planned_outages"]=blocked
            return self .save_state (state )

    def restore_planned_outage (self ,outage :dict ):
        if not isinstance (outage ,dict )or not outage .get ("start_timestamp"):
            raise ValueError ("Invalid planned outage")
        item ={key :outage .get (key )for key in ("start_timestamp","end_timestamp","start_time_str","end_time_str","reason")}
        item ["start_timestamp"]=int (item ["start_timestamp"])
        if item ["end_timestamp"]is not None :
            item ["end_timestamp"]=int (item ["end_timestamp"])
            if item ["end_timestamp"]<=item ["start_timestamp"]:
                raise ValueError ("Invalid planned outage interval")
        with self ._state_lock :
            state =self .state .copy ()
            state ["blocked_planned_outages"]=[entry for entry in state .get ("blocked_planned_outages",[])if not (entry .get ("start_timestamp")==item ["start_timestamp"]and (entry .get ("end_timestamp")is None or entry .get ("end_timestamp")==item ["end_timestamp"]))]
            state ["planned_outages"]=list (state .get ("planned_outages",[]))+[item ]
            return self ._save_state (state ,replace_blocked =True )

    def load_daily_stats (self ):
        if not os .path .exists (DAILY_FILE ):
            return {}
        try :
            with open (DAILY_FILE ,"r",encoding ="utf-8")as f :
                data =json .load (f )
                return data if isinstance (data ,dict )else {}
        except Exception :
            return {}

    def save_daily_stats (self ,stats ):
        try :
            with open (DAILY_FILE ,"w",encoding ="utf-8")as f :
                json .dump (stats ,f ,ensure_ascii =False ,indent =2 )
        except Exception as e :
            print (f"[Storage] Error saving daily stats: {e }")

    def update_daily_activity (self ,date_str :str ,status :str ,off_seconds :int =0 ):
        stats =self .load_daily_stats ()
        if date_str not in stats :
            stats [date_str ]={"recorded":True ,"count":0 ,"offSec":0 ,"status":"ON"}
        entry =stats [date_str ]
        entry ["recorded"]=True 
        if status =="OFF":
            entry ["status"]="OFF"
            entry ["count"]=entry .get ("count",0 )+1 
            if off_seconds >0 :
                entry ["offSec"]=entry .get ("offSec",0 )+off_seconds 
            else :
                entry ["offSec"]=max (entry .get ("offSec",0 ),3600 )
        self .save_daily_stats (stats )
        return stats 

    def add_history (self ,record ):
        if not isinstance (record ,dict ):
            return 
        record =record .copy ()
        record .pop ("blocked_planned_outages",None )
        curr_status =record .get ("status","ON")
        now_ts =int (time .time ())
        if curr_status =="ON"and record .get ("is_planned"):
            start_ts =record .get ("start_timestamp")or 0 
            if start_ts >now_ts :
                return 

        history =self .get_history (limit =500 )
        now_iso =datetime .now ().isoformat ()
        if "timestamp"not in record :
            record ["timestamp"]=record .get ("updated_at")or now_iso

        if history :
            prev_status =history [0 ].get ("status","ON")
            if curr_status ==prev_status :
                if curr_status =="OFF":
                    history [0 ].update (record )
                    self ._save_history_list (history )
                    self ._rebuild_daily_stats (history )
                return 

        history .insert (0 ,record )
        history =history [:500 ]
        self ._save_history_list (history )
        self ._rebuild_daily_stats (history )

    def _save_history_list (self ,history ):
        try :
            encrypted_history =[self ._encrypt_record (item )for item in history ]
            with open (HISTORY_FILE ,"w",encoding ="utf-8")as f :
                json .dump (encrypted_history ,f ,ensure_ascii =False ,indent =2 )
        except Exception as e :
            print (f"[Storage] Error saving history: {e }")

    def get_history (self ,limit =200 ):
        if not os .path .exists (HISTORY_FILE ):
            return []
        try :
            with open (HISTORY_FILE ,"r",encoding ="utf-8")as f :
                data =json .load (f )
                if isinstance (data ,list ):
                    decrypted =[self ._decrypt_record (item )for item in data ]
                    deduped =[]
                    for item in decrypted :
                        if not deduped :
                            deduped .append (item )
                        else :
                            if item .get ("status")!=deduped [-1 ].get ("status"):
                                deduped .append (item )
                    return deduped [:limit ]
                return []
        except Exception :
            return []

    def clear_history (self ):
        try :
            with open (HISTORY_FILE ,"w",encoding ="utf-8")as f :
                json .dump ([],f ,ensure_ascii =False ,indent =2 )
            with open (DAILY_FILE ,"w",encoding ="utf-8")as f :
                json .dump ({},f ,ensure_ascii =False ,indent =2 )
            return True
        except Exception as e :
            print (f"[Storage] Error clearing history: {e }")
            return False

    def delete_history_record (self ,timestamp ):
        try :
            history =self .get_history (limit =500 )
            remaining =[item for item in history if item .get ("timestamp")!=timestamp ]
            self ._save_history_list (remaining )
            self ._rebuild_daily_stats (remaining )
            return True
        except Exception as e :
            print (f"[Storage] Error deleting history record: {e }")
            return False

    def _rebuild_daily_stats (self ,history ):
        stats ={}
        seen_outages =set ()
        for item in history :
            ts =item .get ("timestamp")or item .get ("updated_at")
            if not ts :
                continue 
            d_str =ts .split ("T")[0 ]
            if d_str not in stats :
                stats [d_str ]={"recorded":True ,"count":0 ,"offSec":0 ,"status":"ON"}
            if item .get ("status")=="OFF":
                outage_key =(d_str ,item .get ("start_timestamp"),item .get ("end_timestamp")or item .get ("end_time_str"))
                if outage_key in seen_outages :
                    continue 
                seen_outages .add (outage_key )
                stats [d_str ]["status"]="OFF"
                stats [d_str ]["count"]=stats [d_str ].get ("count",0 )+1 
                tot =item .get ("total_seconds")or 3600 
                stats [d_str ]["offSec"]=stats [d_str ].get ("offSec",0 )+tot 
        self .save_daily_stats (stats )
