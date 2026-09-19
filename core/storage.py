import sys
import os
import json
import time
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
"updated_at":datetime .now ().isoformat ()
}

class StorageManager :
    def __init__ (self ):
        os .makedirs (DATA_DIR ,exist_ok =True )
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

    def save_state (self ,state ):
        if isinstance (state ,dict ):
            now_ts =int (time .time ())
            curr_is_active_outage =False 
            if isinstance (self .state ,dict )and self .state .get ("status")=="OFF":
                e_ts =self .state .get ("end_timestamp")
                if not e_ts or e_ts >now_ts :
                    curr_is_active_outage =True 

            incoming_is_future_planned_only =False 
            if state .get ("is_planned")and not state .get ("is_outage")and state .get ("status")!="OFF":
                incoming_is_future_planned_only =True 

            if curr_is_active_outage and incoming_is_future_planned_only :
                existing_planned =self .state .get ("planned_outages",[])or []
                new_planned =state .get ("planned_outages",[])or []
                combined_planned =list (existing_planned )
                for po in new_planned :
                    if isinstance (po ,dict ):
                        key =(po .get ("start_timestamp"),po .get ("end_timestamp"))
                        if not any ((x .get ("start_timestamp"),x .get ("end_timestamp"))==key for x in combined_planned ):
                            combined_planned .append (po )
                valid_planned =[po for po in combined_planned if (po .get ("end_timestamp")or (po .get ("start_timestamp",0 )+3600 ))>now_ts ]
                valid_planned .sort (key =lambda x :x .get ("start_timestamp")or 0 )
                self .state ["planned_outages"]=valid_planned 
                state =self .state 
            else :
                if state .get ("status")=="ON":
                    if not state .get ("light_on_since"):
                        if isinstance (self .state ,dict )and self .state .get ("status")=="ON"and self .state .get ("light_on_since"):
                            state ["light_on_since"]=self .state ["light_on_since"]
                        else :
                            state ["light_on_since"]=int (time .time ()*1000 )
                else :
                    state ["light_on_since"]=None 

                existing_planned =[]
                if isinstance (self .state ,dict ):
                    existing_planned =self .state .get ("planned_outages",[])or []
                new_planned =state .get ("planned_outages")
                if new_planned :
                    combined_planned =list (new_planned )
                    for po in existing_planned :
                        if isinstance (po ,dict ):
                            key =(po .get ("start_timestamp"),po .get ("end_timestamp"))
                            if not any ((x .get ("start_timestamp"),x .get ("end_timestamp"))==key for x in combined_planned ):
                                combined_planned .append (po )
                    source_planned =combined_planned 
                else :
                    source_planned =existing_planned 

                valid_planned =[]
                seen_planned =set ()
                for po in source_planned :
                    if isinstance (po ,dict ):
                        e_ts =po .get ("end_timestamp")or (po .get ("start_timestamp",0 )+3600 )
                        if e_ts >now_ts :
                            key =(po .get ("start_timestamp"),po .get ("end_timestamp"))
                            if key not in seen_planned :
                                seen_planned .add (key )
                                valid_planned .append (po )
                valid_planned .sort (key =lambda x :x .get ("start_timestamp")or 0 )
                state ["planned_outages"]=valid_planned 
                if valid_planned and state .get ("status")!="OFF":
                    next_po =valid_planned [0 ]
                    state ["is_planned"]=True 
                    state ["start_timestamp"]=next_po .get ("start_timestamp")
                    state ["end_timestamp"]=next_po .get ("end_timestamp")
                    state ["start_time_str"]=next_po .get ("start_time_str")
                    state ["end_time_str"]=next_po .get ("end_time_str")
                elif not valid_planned and state .get ("is_planned"):
                    state ["is_planned"]=False 

            self .state =state 
            try :
                encrypted_state =self ._encrypt_record (self .state )
                with open (STATE_FILE ,"w",encoding ="utf-8")as f :
                    json .dump (encrypted_state ,f ,ensure_ascii =False ,indent =2 )
            except Exception as e :
                print (f"[Storage] Error saving state: {e }")

    def get_state (self ):
        return self .state 

    def delete_planned_outage (self ,start_timestamp :int ,end_timestamp :int =None ):
        state =self .load_state ()
        if isinstance (state ,dict ):
            planned =state .get ("planned_outages",[])or []
            filtered =[]
            for p in planned :
                if isinstance (p ,dict ):
                    s_match =p .get ("start_timestamp")==start_timestamp 
                    e_match =(end_timestamp is None or p .get ("end_timestamp")==end_timestamp )
                    if not (s_match and e_match ):
                        filtered .append (p )
            state ["planned_outages"]=filtered 
            if not filtered :
                state ["is_planned"]=False 
                if state .get ("start_timestamp")==start_timestamp :
                    state ["start_timestamp"]=None 
                    state ["end_timestamp"]=None 
                    state ["start_time_str"]=None 
                    state ["end_time_str"]=None 
            else :
                next_po =filtered [0 ]
                state ["is_planned"]=True 
                state ["start_timestamp"]=next_po .get ("start_timestamp")
                state ["end_timestamp"]=next_po .get ("end_timestamp")
                state ["start_time_str"]=next_po .get ("start_time_str")
                state ["end_time_str"]=next_po .get ("end_time_str")
            self .save_state (state )
        return self .state 

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
        curr_status =record .get ("status","ON")
        now_ts =int (time .time ())
        if curr_status =="ON"and record .get ("is_planned"):
            start_ts =record .get ("start_timestamp")or 0 
            if start_ts >now_ts :
                return 

        history =self .get_history (limit =500 )
        now_iso =datetime .now ().isoformat ()
        if "timestamp"not in record :
            record ["timestamp"]=now_iso 

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
