import os
import sys
import time
import signal
import threading
import urllib .request
from core .config import ConfigManager
from core .storage import StorageManager
from core .api_server import APIServer ,get_local_ip
from core .telegram_service import TelegramService

def start_keep_alive (app_url ):
    def pinger ():
        while True :
            time .sleep (8 *60 )
            try :
                target =f"{app_url .rstrip ('/')}/api/health"
                req =urllib .request .Request (target ,headers ={"User-Agent":"LightWidget-KeepAlive/1.0"})
                with urllib .request .urlopen (req ,timeout =20 )as resp :
                    pass
            except Exception :
                pass

    t =threading .Thread (target =pinger ,daemon =True )
    t .start ()

def main ():
    config_mgr =ConfigManager ()
    storage_mgr =StorageManager ()

    def on_state_updated (state ):
        pass

    def on_tg_status (status ,message ):
        pass

    tg_service =TelegramService (
    config_manager =config_mgr ,
    storage_manager =storage_mgr ,
    on_state_updated =on_state_updated ,
    on_status_change =on_tg_status
    )

    if config_mgr .get ("telegram",{}).get ("api_id")and config_mgr .get ("telegram",{}).get ("api_hash"):
        tg_service .start ()

    api_port =int (os .environ .get ("PORT",config_mgr .get ("server",{}).get ("port",8088 )))
    api_server =APIServer (
    host ="0.0.0.0",
    port =api_port ,
    storage =storage_mgr ,
    on_message =on_state_updated
    )
    api_server .start ()

    external_url =os .environ .get ("RENDER_EXTERNAL_URL")or "https://lightwidget.onrender.com"
    if external_url :
        start_keep_alive (external_url )

    def shutdown (sig ,frame ):
        api_server .stop ()
        tg_service .stop ()
        sys .exit (0 )

    signal .signal (signal .SIGINT ,shutdown )
    signal .signal (signal .SIGTERM ,shutdown )

    while True :
        time .sleep (1 )

if __name__ =="__main__":
    main ()
