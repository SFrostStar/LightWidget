import os
import sys
import json
import threading
import webview
from core .config import ConfigManager
from core .storage import StorageManager
from core .parser import parse_message
from core .api_server import APIServer ,get_local_ip
from core .telegram_service import TelegramService
from core .notifier import send_macos_notification
from core .updater import UpdateManager

def get_resource_path (relative_path ):
    if getattr (sys ,'frozen',False )and hasattr (sys ,'_MEIPASS'):
        return os .path .join (sys ._MEIPASS ,relative_path )
    return os .path .join (os .path .dirname (os .path .abspath (__file__ )),relative_path )

UI_DIR =get_resource_path ("ui")
INDEX_PATH =os .path .join (UI_DIR ,"index.html")
IOS_SCRIPT_PATH =get_resource_path (os .path .join ("ios","widget_ios.js"))

class ApiBridge :
    def __init__ (self ,config_mgr :ConfigManager ,storage_mgr :StorageManager ,tg_service :TelegramService ,window =None ):
        self .config_mgr =config_mgr
        self .storage_mgr =storage_mgr
        self .tg_service =tg_service
        self .window =window
        self .update_mgr =UpdateManager ()

    def set_window (self ,window ):
        self .window =window

    def get_state (self ):
        try :
            st =self .storage_mgr .get_state ()
            if isinstance (st ,dict ):
                st =st .copy ()
                st ["account_number"]=self .config_mgr .get ("account_number","")
            return st or {}
        except Exception as e :
            print (f"[Bridge] get_state error: {e }")
            return {}

    def parse_and_apply (self ,text ):
        try :
            parsed =parse_message (text )
            if parsed :
                self .storage_mgr .save_state (parsed )
                self .storage_mgr .add_history (parsed )

                notif =self .config_mgr .get ("notifications",{})
                enable_banner =notif .get ("banner",True )and notif .get ("macos_banner",True )
                enable_sound =notif .get ("sound",True )and notif .get ("macos_sound",True )

                if enable_banner :
                    if parsed ["status"]=="OFF":
                        snd ="Basso"if enable_sound else ""
                        send_macos_notification (
                        "⚡ Внимание: Отключение света!",
                        f"Ориентировочно до {parsed ['end_time_str']or 'неизвестно'}",
                        f"{parsed ['address']} ({parsed ['reason']})",
                        sound =snd
                        )
                    else :
                        snd ="Glass"if enable_sound else ""
                        send_macos_notification (
                        "💡 Свет включен!",
                        parsed ['address'],
                        "Электросеть работает в штатном режиме.",
                        sound =snd
                        )

                self .broadcast_state (parsed )
                return parsed
            return None
        except Exception as e :
            print (f"[Bridge] parse_and_apply error: {e }")
            return None

    def get_config (self ):
        try :
            return self .config_mgr .config or {}
        except Exception as e :
            print (f"[Bridge] get_config error: {e }")
            return {}

    def save_config (self ,cfg ):
        try :
            if isinstance (cfg ,dict ):
                self .config_mgr .update (cfg )
            return True
        except Exception as e :
            print (f"[Bridge] save_config error: {e }")
            return False

    def get_account_number (self ):
        try :
            return str (self .config_mgr .get ("account_number",""))
        except Exception as e :
            print (f"[Bridge] get_account_number error: {e }")
            return ""

    def save_account_number (self ,val ):
        try :
            val_str =str (val or "").strip ()
            self .config_mgr .set ("account_number",val_str )
            return True
        except Exception as e :
            print (f"[Bridge] save_account_number error: {e }")
            return False

    def get_history (self ):
        try :
            res =self .storage_mgr .get_history (limit =500 )
            return res if isinstance (res ,list )else []
        except Exception as e :
            print (f"[Bridge] get_history error: {e }")
            return []

    def get_daily_stats (self ):
        try :
            res =self .storage_mgr .load_daily_stats ()
            return res if isinstance (res ,dict )else {}
        except Exception as e :
            print (f"[Bridge] get_daily_stats error: {e }")
            return {}

    def clear_history (self ):
        try :
            return self .storage_mgr .clear_history ()
        except Exception as e :
            print (f"[Bridge] clear_history error: {e }")
            return False

    def check_for_updates (self ):
        try :
            return self .update_mgr .check_updates ()
        except Exception as e :
            print (f"[Bridge] check_for_updates error: {e }")
            return {"has_update":False ,"error":str (e )}

    def perform_update (self ):
        try :
            return self .update_mgr .pull_update ()
        except Exception as e :
            print (f"[Bridge] perform_update error: {e }")
            return {"success":False ,"error":str (e )}

    def restart_app (self ):
        try :
            self .update_mgr .restart_application ()
            return True
        except Exception as e :
            print (f"[Bridge] restart_app error: {e }")
            return False

    def get_iphone_info (self ):
        try :
            local_ip =get_local_ip ()
            port =self .config_mgr .get ("server",{}).get ("port",8088 )
            endpoint =f"http://{local_ip }:{port }/api/status"

            script_content =""
            if os .path .exists (IOS_SCRIPT_PATH ):
                with open (IOS_SCRIPT_PATH ,"r",encoding ="utf-8")as f :
                    script_content =f .read ()
                    script_content =script_content .replace (
                    'const SERVER_URL = "http://localhost:8088/api/status";',
                    f'const SERVER_URL = "{endpoint }";'
                    )

            return {
            "local_ip":local_ip ,
            "port":port ,
            "endpoint":endpoint ,
            "scriptable_code":script_content
            }
        except Exception as e :
            print (f"[Bridge] get_iphone_info error: {e }")
            return {"local_ip":"127.0.0.1","port":8088,"endpoint":"http://127.0.0.1:8088/api/status","scriptable_code":""}

    def connect_telegram (self ):
        try :
            if self .tg_service :
                self .tg_service .start ()
            return {"status":"started"}
        except Exception as e :
            print (f"[Bridge] connect_telegram error: {e }")
            return {"status":"error","error":str (e )}

    def disconnect_telegram (self ):
        try :
            if self .tg_service :
                self .tg_service .stop ()
            return {"status":"stopped"}
        except Exception as e :
            print (f"[Bridge] disconnect_telegram error: {e }")
            return {"status":"error","error":str (e )}

    def submit_tg_code (self ,code ):
        try :
            if self .tg_service :
                return self .tg_service .submit_code (code )
            return {"success":False ,"error":"Сервис не доступен"}
        except Exception as e :
            print (f"[Bridge] submit_tg_code error: {e }")
            return {"success":False ,"error":str (e )}

    def submit_tg_password (self ,password ):
        try :
            if self .tg_service :
                return self .tg_service .submit_password (password )
            return {"success":False ,"error":"Сервис не доступен"}
        except Exception as e :
            print (f"[Bridge] submit_tg_password error: {e }")
            return {"success":False ,"error":str (e )}

    def sync_history (self ):
        try :
            if self .tg_service :
                self .tg_service .sync_now ()
            return self .storage_mgr .get_state () or {}
        except Exception as e :
            print (f"[Bridge] sync_history error: {e }")
            return {}

    def set_widget_mode (self ,enabled :bool ):
        if not self .window :
            return {"success":False }

        try :
            if sys .platform =="darwin":
                try :
                    import Cocoa
                    import Quartz

                    def apply_cocoa_window_mode ():
                        try :
                            app =Cocoa .NSApplication .sharedApplication ()
                            for w in app .windows ():
                                if w .title ()=="LightWidget":
                                    w .setOpaque_ (False )
                                    w .setBackgroundColor_ (Cocoa .NSColor .clearColor ())
                                    w .setHasShadow_ (True )
                                    if enabled :
                                        behavior =(
                                        Cocoa .NSWindowCollectionBehaviorCanJoinAllSpaces |
                                        Cocoa .NSWindowCollectionBehaviorStationary |
                                        Cocoa .NSWindowCollectionBehaviorIgnoresCycle
                                        )
                                        w .setCollectionBehavior_ (behavior )
                                        w .setLevel_ (Quartz .kCGDesktopIconWindowLevel +1 )
                                    else :
                                        w .setLevel_ (Cocoa .NSNormalWindowLevel )
                                        w .setCollectionBehavior_ (Cocoa .NSWindowCollectionBehaviorDefault )
                        except Exception :
                            pass

                    Cocoa .NSOperationQueue .mainQueue ().addOperationWithBlock_ (apply_cocoa_window_mode )
                except Exception :
                    pass

            if enabled :
                self .window .resize (165 ,165 )
            else :
                self .window .resize (840 ,560 )
            return {"success":True ,"mode":"widget"if enabled else "normal"}
        except Exception as ex :
            print (f"[ApiBridge] Error setting widget mode: {ex }")
            return {"success":True }

    def minimize (self ):
        try :
            if self .window :
                self .window .minimize ()
        except Exception as e :
            print (f"[Bridge] minimize error: {e }")

    def close (self ):
        try :
            if self .tg_service :
                self .tg_service .stop ()
        except Exception :
            pass
        try :
            if self .window :
                self .window .destroy ()
        except Exception :
            pass
        os ._exit (0 )

    def broadcast_state (self ,state ):
        def _evaluate ():
            if self .window :
                try :
                    state_json =json .dumps (state ,ensure_ascii =False )
                    self .window .evaluate_js (f"if (window.onStateUpdatedFromPython) window.onStateUpdatedFromPython({state_json });")
                except Exception as e :
                    print (f"[Bridge] Error evaluating JS broadcast: {e }")
        threading .Thread (target =_evaluate ,daemon =True ).start ()

        def _sync_render ():
            try :
                import urllib .request ,ssl
                ctx =ssl ._create_unverified_context ()
                raw_text =state .get ("raw_text","")
                if not raw_text :
                    if state .get ("status")=="OFF":
                        raw_text =f"❗️ За адресою {state .get ('address')} зафіксовано відключення.\nПричина: {state .get ('reason')}.\n🕦 Час початку: {state .get ('start_time_str')}.\n🕦 Орієнтовний час відновлення електроенергії: {state .get ('end_time_str')}."
                    else :
                        raw_text =f"✅ За адресою {state .get ('address')} електропостачання відновлено!"

                payload =json .dumps ({"text":raw_text },ensure_ascii =False ).encode ("utf-8")
                req =urllib .request .Request (
                "https://lightwidget.onrender.com/api/message",
                data =payload ,
                headers ={"Content-Type":"application/json; charset=utf-8"},
                method ="POST"
                )
                with urllib .request .urlopen (req ,context =ctx ,timeout =6 )as resp :
                    print (f"[CloudSync] Synced status '{state .get ('status')}' to Render ({resp .status })")
            except Exception as ex :
                print (f"[CloudSync] Render sync note: {ex }")

        threading .Thread (target =_sync_render ,daemon =True ).start ()

    def broadcast_tg_status (self ,status ,message ):
        def _evaluate ():
            if self .window :
                try :
                    msg_json =json .dumps (message ,ensure_ascii =False )
                    self .window .evaluate_js (f"if (window.onTelegramStatusChange) window.onTelegramStatusChange('{status }', {msg_json });")
                except Exception as e :
                    print (f"[Bridge] Error evaluating TG status JS: {e }")
        threading .Thread (target =_evaluate ,daemon =True ).start ()

def main ():
    config_mgr =ConfigManager ()
    storage_mgr =StorageManager ()

    bridge =ApiBridge (config_mgr ,storage_mgr ,None )

    def on_state_updated (state ):
        bridge .broadcast_state (state )

    def on_tg_status (status ,message ):
        bridge .broadcast_tg_status (status ,message )

    tg_service =TelegramService (
    config_manager =config_mgr ,
    storage_manager =storage_mgr ,
    on_state_updated =on_state_updated ,
    on_status_change =on_tg_status
    )
    bridge .tg_service =tg_service

    if config_mgr .get ("telegram",{}).get ("api_id")and config_mgr .get ("telegram",{}).get ("api_hash"):
        tg_service .start ()

    api_port =config_mgr .get ("server",{}).get ("port",8088 )
    api_server =APIServer (
    host ="0.0.0.0",
    port =api_port ,
    storage =storage_mgr ,
    on_message =on_state_updated
    )
    api_server .start ()

    is_mac =sys .platform =="darwin"
    if sys .platform =="win32":
        import asyncio
        try :
            asyncio .set_event_loop_policy (asyncio .WindowsSelectorEventLoopPolicy ())
        except Exception :
            pass

    window =webview .create_window (
    title ="LightWidget",
    url =INDEX_PATH ,
    js_api =bridge ,
    width =960 ,
    height =620 ,
    min_size =(880 ,560 ),
    resizable =True ,
    frameless =True ,
    easy_drag =is_mac ,
    transparent =is_mac ,
    background_color ="#141518"
    )
    bridge .set_window (window )
    window .events .closed +=lambda :os ._exit (0 )

    def on_window_loaded ():
        try :
            acc =config_mgr .get ("account_number","")
            appr =config_mgr .get ("appearance",{})
            notif =config_mgr .get ("notifications",{})
            theme =appr .get ("theme","midnight")
            accent =appr .get ("accent","blue")
            show_sec ="true"if appr .get ("show_seconds",True )else "false"
            show_pls ="true"if appr .get ("show_pulse",True )else "false"
            show_stats ="true"if appr .get ("show_stats",True )else "false"
            show_hmap ="true"if appr .get ("show_heatmap",True )else "false"
            sound ="true"if notif .get ("sound",True )else "false"
            banner ="true"if notif .get ("banner",True )else "false"

            if window :
                escaped_acc =acc .replace ("'","\\'")
                window .evaluate_js (f"""
                    (function() {{
                        try {{
                            localStorage.setItem('lightwidget_theme', '{theme }');
                            localStorage.setItem('lightwidget_accent', '{accent }');
                            if (window.applyTheme) window.applyTheme('{theme }', false);
                            if (window.applyAccent) window.applyAccent('{accent }', false);
                            if (window.appSettings) {{
                                window.appSettings.theme = '{theme }';
                                window.appSettings.accent = '{accent }';
                                window.appSettings.showSeconds = {show_sec };
                                window.appSettings.showPulse = {show_pls };
                                window.appSettings.showStats = {show_stats };
                                window.appSettings.showHeatmap = {show_hmap };
                                window.appSettings.sound = {sound };
                                window.appSettings.banner = {banner };
                            }}
                            if (window.applySettingsState) window.applySettingsState();

                            var el = document.getElementById('inputAccountNumber');
                            if (el) {{
                                el.value = '{escaped_acc }';
                                var len = Math.max(8, '{escaped_acc }'.length);
                                el.style.width = (len + 2) + 'ch';
                            }}
                        }} catch(e) {{}}
                    }})();
                """)
        except Exception :
            pass

    window .events .loaded +=on_window_loaded

    try :
        webview .start (debug =False )
    finally :
        api_server .stop ()
        tg_service .stop ()
        os ._exit (0 )

if __name__ =="__main__":
    try :
        main ()
    except Exception as e :
        import traceback
        try :
            with open ("crash.log","w",encoding ="utf-8")as f :
                f .write (traceback .format_exc ())
        except Exception :
            pass
        if sys .platform =="win32":
            try :
                import ctypes
                ctypes .windll .user32 .MessageBoxW (0 ,f"LightWidget error: {e }\n\nCheck crash.log for details.","LightWidget",0x10 )
            except Exception :
                pass
        sys .exit (1 )
