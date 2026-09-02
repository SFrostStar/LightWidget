import sys
import asyncio
import threading
import time
import os
import re
import traceback
from telethon import TelegramClient ,events
from telethon .errors import (
SessionPasswordNeededError ,
PhoneCodeInvalidError ,
PhoneCodeExpiredError ,
FloodWaitError ,
AuthKeyDuplicatedError ,
AuthKeyUnregisteredError ,
AuthKeyInvalidError ,
SecurityError
)
from core .parser import parse_message
from core .notifier import send_macos_notification
from core .crypto import DATA_DIR

if sys .platform =="win32":
    try :
        asyncio .set_event_loop_policy (asyncio .WindowsSelectorEventLoopPolicy ())
    except Exception :
        pass

class TelegramService :
    def __init__ (self ,config_manager ,storage_manager ,on_state_updated =None ,on_status_change =None ,session_name ="telethon_session"):
        self .config_manager =config_manager
        self .storage_manager =storage_manager
        self .on_state_updated =on_state_updated
        self .on_status_change =on_status_change
        self .session_name =session_name
        self .session_path =os .path .join (DATA_DIR ,session_name )

        self .client =None
        self .loop =None
        self .thread =None
        self .is_running =False
        self .connection_status ="DISCONNECTED"
        self .phone_code_hash =None
        self .phone =None
        self .auth_event =None

    def _set_status (self ,status :str ,message :str =""):
        self .connection_status =status
        print (f"[TelegramService] Status: {status } | Msg: {message }")
        if self .on_status_change :
            self .on_status_change (status ,message )

    def _reset_session_file (self ):
        for ext in [".session",".session-journal"]:
            fpath =f"{self .session_path }{ext }"
            if os .path .exists (fpath ):
                try :
                    os .remove (fpath )
                    print (f"[TelegramService] Removed invalid session file: {fpath }")
                except Exception as e :
                    print (f"[TelegramService] Could not remove {fpath }: {e }")

    def start (self ):
        if self .is_running :
            self .stop ()

        cfg =self .config_manager .get ("telegram",{})
        api_id =cfg .get ("api_id")
        api_hash =cfg .get ("api_hash")

        if not api_id or not api_hash :
            self ._set_status ("NO_CREDENTIALS","API ID или API Hash не заполнены")
            return

        self .is_running =True
        self ._set_status ("CONNECTING","Подключение к Telegram...")

        self .thread =threading .Thread (target =self ._run_async_loop ,daemon =True )
        self .thread .start ()

    def _run_async_loop (self ):
        if sys .platform =="win32":
            try :
                self .loop =asyncio .WindowsSelectorEventLoopPolicy ().new_event_loop ()
            except Exception :
                self .loop =asyncio .new_event_loop ()
        else :
            self .loop =asyncio .new_event_loop ()
        asyncio .set_event_loop (self .loop )
        self .auth_event =asyncio .Event ()
        try :
            self .loop .run_until_complete (self ._connect_and_listen ())
        except (AuthKeyDuplicatedError ,AuthKeyUnregisteredError ,AuthKeyInvalidError ,SecurityError )as e :
            print (f"[TelegramService] Session key conflict: {e }")
            self ._reset_session_file ()
            self ._set_status ("AUTH_CODE_REQUIRED","Сессия сброшена (одновременный вход). Нажмите 'Подключиться' и введите код.")
        except Exception as e :
            traceback .print_exc ()
            self ._set_status ("ERROR",f"Ошибка: {str (e )}")
        finally :
            self .is_running =False

    async def _connect_and_listen (self ):
        cfg =self .config_manager .get ("telegram",{})
        api_id =int (str (cfg .get ("api_id")).strip ())
        api_hash =str (cfg .get ("api_hash")).strip ()
        phone =str (cfg .get ("phone","")).strip ()
        self .phone =phone

        os .makedirs (DATA_DIR ,exist_ok =True )

        try :
            self .client =TelegramClient (self .session_path ,api_id ,api_hash ,loop =self .loop )
            await self .client .connect ()
        except (AuthKeyDuplicatedError ,AuthKeyUnregisteredError ,AuthKeyInvalidError ,SecurityError )as e :
            print (f"[TelegramService] Caught session error during connect: {e }")
            self ._reset_session_file ()
            self .client =TelegramClient (self .session_path ,api_id ,api_hash ,loop =self .loop )
            await self .client .connect ()

        if not await self .client .is_user_authorized ():
            if not phone :
                self ._set_status ("AUTH_CODE_REQUIRED","Введите номер телефона в настройках")
                return
            try :
                sent_code =await self .client .send_code_request (phone )
                self .phone_code_hash =sent_code .phone_code_hash
                self ._set_status ("AUTH_CODE_REQUIRED",f"Код подтверждения отправлен на {phone }")
            except FloodWaitError as e :
                self ._set_status ("ERROR",f"Слишком много попыток. Подождите {e .seconds } сек.")
                return
            except Exception as e :
                self ._set_status ("ERROR",f"Ошибка авторизации: {str (e )}")
                return

            if self .auth_event :
                self .auth_event .clear ()
            while self .is_running and self .auth_event and not self .auth_event .is_set ():
                try :
                    await asyncio .wait_for (self .auth_event .wait (),timeout =1.0 )
                except asyncio .TimeoutError :
                    pass

            if not self .is_running :
                return

        self ._set_status ("CONNECTED","Успешно подключено к Telegram")

        bot_username =cfg .get ("bot_username","dtek_odeski_elektromerezhi_bot")

        @self .client .on (events .NewMessage (chats =bot_username ))
        async def handler (event ):
            msg_text =event .raw_text
            print (f"[TelegramService] Received message from @{bot_username }:\n{msg_text [:100 ]}...")
            self ._process_message (msg_text )

        await self ._fetch_recent_history (bot_username )

        while self .is_running :
            await asyncio .sleep (1 )

    async def _fetch_recent_history (self ,bot_username ):
        try :
            entity =await self .client .get_entity (bot_username )
            messages =await self .client .get_messages (entity ,limit =5 )
            for msg in messages :
                if msg .text :
                    parsed =self ._process_message (msg .text ,is_history =True )
                    if parsed :
                        break
        except Exception as e :
            print (f"[TelegramService] History fetch warning: {e }")

    def _process_message (self ,text :str ,is_history :bool =False ):
        cfg =self .config_manager .get ("telegram",{})
        filter_address =cfg .get ("filter_address","").strip ().lower ()

        parsed =parse_message (text )
        if not parsed :
            return None

        if (not parsed .get ("address")or parsed .get ("address")=="Не указан")and cfg .get ("filter_address"):
            parsed ["address"]=cfg .get ("filter_address").strip ()

        if filter_address :
            addr =parsed .get ("address","").lower ()
            raw =text .lower ()
            if addr !="не указан"and filter_address not in addr and filter_address not in raw :
                print (f"[TelegramService] Message ignored (filter '{filter_address }' not in address '{parsed .get ('address')}')")
                return None

        prev_state =self .storage_manager .get_state ()
        prev_status =prev_state .get ("status","ON")

        self .storage_manager .save_state (parsed )
        self .storage_manager .add_history (parsed )

        if not is_history :
            notif =self .config_manager .get ("notifications",{})
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
                    "💡 Свет есть!",
                    parsed ['address'],
                    "Электросеть работает в штатном режиме.",
                    sound =snd
                    )

        if self .on_state_updated :
            self .on_state_updated (parsed )

        return parsed

    def submit_code (self ,code :str ):
        if not self .client or not self .loop or not self .is_running :
            return {"success":False ,"error":"Клиент не запущен"}

        async def _submit ():
            try :
                clean_code =str (code ).strip ().replace (" ","").replace ("-","")
                await self .client .sign_in (phone =self .phone ,code =clean_code ,phone_code_hash =self .phone_code_hash )
                self ._set_status ("CONNECTED","Авторизация успешна!")
                if self .auth_event :
                    self .auth_event .set ()
                return {"success":True }
            except SessionPasswordNeededError :
                self ._set_status ("PASSWORD_REQUIRED","Требуется 2FA пароль")
                return {"success":False ,"requires_password":True }
            except (PhoneCodeInvalidError ,PhoneCodeExpiredError )as e :
                return {"success":False ,"error":f"Неверный или просроченный код: {str (e )}"}
            except Exception as e :
                return {"success":False ,"error":str (e )}

        future =asyncio .run_coroutine_threadsafe (_submit (),self .loop )
        try :
            return future .result (timeout =20.0 )
        except Exception as e :
            return {"success":False ,"error":f"Таймаут запроса: {str (e )}"}

    def submit_password (self ,password :str ):
        if not self .client or not self .loop or not self .is_running :
            return {"success":False ,"error":"Клиент не запущен"}

        async def _submit_pwd ():
            try :
                await self .client .sign_in (password =str (password ).strip ())
                self ._set_status ("CONNECTED","2FA авторизация успешна!")
                if self .auth_event :
                    self .auth_event .set ()
                return {"success":True }
            except Exception as e :
                return {"success":False ,"error":f"Ошибка пароля: {str (e )}"}

        future =asyncio .run_coroutine_threadsafe (_submit_pwd (),self .loop )
        try :
            return future .result (timeout =20.0 )
        except Exception as e :
            return {"success":False ,"error":f"Таймаут запроса: {str (e )}"}

    def sync_now (self ):
        if not self .client or not self .loop or not self .client .is_connected ():
            return {"success":False ,"error":"Не подключено к Telegram"}

        async def _sync ():
            try :
                bot_username =self .config_manager .get ("telegram",{}).get ("bot_username","dtek_odeski_elektromerezhi_bot")
                entity =await self .client .get_entity (bot_username )

                print (f"[TelegramService] Sending '/start' to @{bot_username }...")
                await self .client .send_message (entity ,"/start")

                await asyncio .sleep (1.2 )

                clicked =False
                messages =await self .client .get_messages (entity ,limit =4 )
                for msg in messages :
                    if msg .buttons :
                        for row in msg .buttons :
                            for btn in row :
                                btn_text =(btn .text or "").lower ()
                                if "можливі відключення"in btn_text or "відключен"in btn_text :
                                    try :
                                        print (f"[TelegramService] Clicking button: '{btn .text }'...")
                                        await btn .click ()
                                        clicked =True
                                        break
                                    except Exception as be :
                                        print (f"[TelegramService] Button click note: {be }")
                            if clicked :
                                break
                    if clicked :
                        break

                if not clicked :
                    print (f"[TelegramService] Sending '💡Можливі відключення' text...")
                    await self .client .send_message (entity ,"💡Можливі відключення")

                await asyncio .sleep (1.5 )
                await self ._fetch_recent_history (bot_username )

                if self .on_state_updated :
                    self .on_state_updated (self .storage_manager .get_state ())
                return {"success":True }
            except Exception as e :
                print (f"[TelegramService] Sync error: {e }")
                return {"success":False ,"error":str (e )}

        future =asyncio .run_coroutine_threadsafe (_sync (),self .loop )
        try :
            return future .result (timeout =25.0 )
        except Exception as e :
            return {"success":False ,"error":f"Таймаут синхронизации: {str (e )}"}

    def stop (self ):
        self .is_running =False
        if self .auth_event :
            self .auth_event .set ()
        if self .client and self .loop and self .loop .is_running ():
            async def _disconnect ():
                try :
                    await self .client .disconnect ()
                except Exception :
                    pass
            asyncio .run_coroutine_threadsafe (_disconnect (),self .loop )
        self ._set_status ("DISCONNECTED","Отключено от Telegram")
