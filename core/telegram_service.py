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
from core .parser import parse_message ,is_menu_service_message
from core .notifier import send_status_notification ,send_sync_failure_notification
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
        self ._msg_buffer =[]
        self ._buffer_task =None
        self ._notification_task =None
        self ._sync_task =None
        self ._sync_request_id =None
        self ._sync_message_ids =set ()
        self ._sync_deadline =0.0
        self ._last_message_received_at =0.0
        self ._last_status_received_at =0.0
        self ._last_notification_kind =None
        self ._last_notification_at =0.0

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

        self ._msg_buffer =[]
        self ._buffer_task =None 

        @self .client .on (events .NewMessage (chats =bot_username ,incoming =True ))
        async def handler (event ):
            request_id =self ._sync_request_id
            if request_id is None or event .message .id <=request_id :
                return
            msg_text =event .raw_text 
            if not msg_text or is_menu_service_message (msg_text ):
                return
            messages =await self .client .get_messages (bot_username ,limit =32 )
            if not self ._is_sync_response (messages ,request_id ):
                return
            reply_to =getattr (event .message ,"reply_to_msg_id",None )
            if reply_to and reply_to not in self ._sync_message_ids :
                return
            print (f"[TelegramService] Received message from @{bot_username }:\n{msg_text [:100 ]}...")
            self ._last_message_received_at =time .monotonic ()
            if self ._notification_task and not self ._notification_task .done ():
                self ._notification_task .cancel ()
            self ._msg_buffer .append ((msg_text ,event .message .date ))
            if self ._buffer_task and not self ._buffer_task .done ():
                self ._buffer_task .cancel ()
            self ._buffer_task =asyncio .create_task (self ._flush_message_buffer ())

        while self .is_running :
            await asyncio .sleep (1 )

    def _is_sync_response (self ,messages ,request_id ):
        if self ._sync_request_id !=request_id or time .monotonic ()>=self ._sync_deadline :
            return False
        outgoing =next ((msg for msg in messages if getattr (msg ,"out",False )),None )
        return bool (outgoing and outgoing .id in self ._sync_message_ids )

    def _apply_message_buffer (self ):
        if not self ._msg_buffer :
            return None
        buffered =sorted (self ._msg_buffer ,key =lambda item :item [1 ])
        self ._msg_buffer .clear ()
        combined ="\n\n--------------------------------------\n\n".join (item [0 ]for item in buffered )
        parsed =self ._process_message (combined ,message_date =buffered [-1 ][1 ])
        if parsed :
            self ._last_status_received_at =self ._last_message_received_at
        return parsed

    async def _flush_message_buffer (self ):
        try :
            await asyncio .sleep (0.6 )
            self ._apply_message_buffer ()
        except asyncio .CancelledError :
            pass
        except Exception as e :
            print (f"[TelegramService] Flush buffer error: {e }")

    def _notify_current_status (self ,force =False ):
        state =self .storage_manager .get_state ()or {}
        now =time .time ()
        has_planned =any ((item .get ("end_timestamp")or 0 )>now for item in state .get ("planned_outages",[]))or (state .get ("is_planned")and (state .get ("end_timestamp")or 0 )>now )
        kind ="OFF"if state .get ("status")=="OFF"else ("PLANNED"if has_planned else "ON")
        if not force and kind ==self ._last_notification_kind and time .monotonic ()-self ._last_notification_at <10 :
            return
        if send_status_notification (state ,self .config_manager .get ("notifications",{})):
            self ._last_notification_kind =kind
            self ._last_notification_at =time .monotonic ()

    def _queue_status_notification (self ):
        if self ._notification_task and not self ._notification_task .done ():
            self ._notification_task .cancel ()
        async def _send ():
            try :
                await asyncio .sleep (1.5 )
                if not self ._sync_task or self ._sync_task .done ():
                    self ._notify_current_status ()
            except asyncio .CancelledError :
                pass
        self ._notification_task =asyncio .create_task (_send ())

    async def _fetch_recent_history (self ,bot_username ,min_message_id ):
        entity =await self .client .get_entity (bot_username )
        messages =await self .client .get_messages (entity ,limit =32 )
        if not self ._is_sync_response (messages ,min_message_id ):
            return None
        bot_texts =[]
        for msg in messages :
            if msg .id <=min_message_id :
                break
            if getattr (msg ,"out",False ):
                if msg .id not in self ._sync_message_ids :
                    return None
                break
            reply_to =getattr (msg ,"reply_to_msg_id",None )
            if reply_to and reply_to not in self ._sync_message_ids :
                continue
            t =msg .text or ""
            if t and not is_menu_service_message (t ):
                bot_texts .append ((t ,msg .date ))

        if bot_texts :
            bot_texts .reverse ()
            combined ="\n\n--------------------------------------\n\n".join (item [0 ]for item in bot_texts )
            return self ._process_message (combined ,is_history =True ,message_date =bot_texts [-1 ][1 ])
        return None

    def _process_message (self ,text :str ,is_history :bool =False ,message_date =None ):
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
        if message_date is not None :
            parsed ["updated_at"]=message_date .astimezone ().isoformat ()
        elif is_history and parsed .get ("raw_text")==prev_state .get ("raw_text"):
            parsed ["updated_at"]=prev_state .get ("updated_at")
        if parsed .get ("updated_at"):
            parsed ["timestamp"]=parsed ["updated_at"]

        parsed =self .storage_manager .save_state (parsed )
        self .storage_manager .add_history (parsed )

        if not is_history and (not self ._sync_task or self ._sync_task .done ()):
            self ._queue_status_notification ()

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
        sync_started_at =time .monotonic ()
        sync_deadline =sync_started_at +15.0
        if self .is_running and (not self .client or not self .loop or not self .client .is_connected ()):
            import time as _time
            _wait_start =_time .time ()
            while _time .time ()-_wait_start <7.0 :
                if self .client and self .loop and self .client .is_connected ():
                    break
                _time .sleep (0.25 )
        if not self .client or not self .loop or not self .client .is_connected ():
            return {"success":False ,"error":"Не подключено к Telegram"}

        async def _sync_once ():
            if self ._notification_task and not self ._notification_task .done ():
                self ._notification_task .cancel ()
            response_received =False

            async def _collect_response ():
                nonlocal response_received
                bot_username =self .config_manager .get ("telegram",{}).get ("bot_username","dtek_odeski_elektromerezhi_bot")
                entity =await self .client .get_entity (bot_username )

                print (f"[TelegramService] Sending '/start' to @{bot_username }...")
                request =await self .client .send_message (entity ,"/start")
                self ._sync_request_id =request .id
                self ._sync_message_ids .add (request .id )

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
                                        button_request =await btn .click ()
                                        if getattr (button_request ,"out",False )and isinstance (getattr (button_request ,"id",None ),int ):
                                            self ._sync_message_ids .add (button_request .id )
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
                    button_request =await self .client .send_message (entity ,"💡Можливі відключення")
                    self ._sync_message_ids .add (button_request .id )

                while True :
                    parsed =await self ._fetch_recent_history (bot_username ,min_message_id =request .id )
                    if parsed :
                        response_received =True
                        break
                    await asyncio .sleep (2.0 )

                response_received_at =time .monotonic ()
                settle_deadline =time .monotonic ()+8.0
                while time .monotonic ()<settle_deadline and time .monotonic ()-max (response_received_at ,self ._last_message_received_at )<1.5 :
                    await asyncio .sleep (0.2 )
                if self ._buffer_task and not self ._buffer_task .done ():
                    self ._buffer_task .cancel ()
                self ._apply_message_buffer ()
                await self ._fetch_recent_history (bot_username ,min_message_id =request .id )

            try :
                await asyncio .wait_for (_collect_response (),timeout =max (0.0 ,sync_deadline -time .monotonic ()))
            except asyncio .TimeoutError :
                if sync_started_at <self ._last_message_received_at <=sync_deadline :
                    if self ._buffer_task and not self ._buffer_task .done ():
                        self ._buffer_task .cancel ()
                    self ._apply_message_buffer ()
                response_received =response_received or sync_started_at <self ._last_status_received_at <=sync_deadline
                if not response_received :
                    send_sync_failure_notification (self .config_manager .get ("notifications",{}))
                    return {"success":False ,"error":"Бот не отвечает","error_code":"BOT_NO_RESPONSE"}
            except Exception as e :
                print (f"[TelegramService] Sync error: {e }")
                return {"success":False ,"error":str (e )}

            try :
                if self ._buffer_task and not self ._buffer_task .done ():
                    self ._buffer_task .cancel ()
                self ._apply_message_buffer ()
                self ._notify_current_status (force =True )

                if self .on_state_updated :
                    self .on_state_updated (self .storage_manager .get_state ())
                return {"success":True }
            except Exception as e :
                print (f"[TelegramService] Sync error: {e }")
                return {"success":False ,"error":str (e )}

        async def _sync ():
            self ._sync_deadline =sync_deadline
            self ._sync_request_id =None
            self ._sync_message_ids .clear ()
            self ._msg_buffer .clear ()
            if self ._buffer_task and not self ._buffer_task .done ():
                self ._buffer_task .cancel ()
            try :
                return await _sync_once ()
            finally :
                self ._sync_request_id =None
                self ._sync_message_ids .clear ()
                self ._msg_buffer .clear ()
                if self ._buffer_task and not self ._buffer_task .done ():
                    self ._buffer_task .cancel ()

        async def _sync_request ():
            if not self ._sync_task or self ._sync_task .done ():
                self ._sync_task =asyncio .create_task (_sync ())
            return await asyncio .shield (self ._sync_task )

        future =asyncio .run_coroutine_threadsafe (_sync_request (),self .loop )
        try :
            return future .result (timeout =16.0 )
        except Exception as e :
            return {"success":False ,"error":f"Таймаут синхронизации: {str (e )}"}

    def stop (self ):
        self .is_running =False
        if self .loop and self .loop .is_running ():
            for task in (self ._notification_task ,self ._buffer_task ,self ._sync_task ):
                if task and not task .done ():
                    self .loop .call_soon_threadsafe (task .cancel )
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
