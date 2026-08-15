import asyncio
import threading
import os
import re
import traceback
from telethon import TelegramClient, events
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError
)
from core.parser import parse_message
from core.notifier import send_macos_notification
from core.crypto import DATA_DIR

SESSION_PATH = os.path.join(DATA_DIR, "telethon_session")

class TelegramService:
    def __init__(self, config_manager, storage_manager, on_state_updated=None, on_status_change=None):
        self.config_manager = config_manager
        self.storage_manager = storage_manager
        self.on_state_updated = on_state_updated
        self.on_status_change = on_status_change
        
        self.client = None
        self.loop = None
        self.thread = None
        self.is_running = False
        self.connection_status = "DISCONNECTED"
        self.phone_code_hash = None
        self.phone = None

    def _set_status(self, status: str, message: str = ""):
        self.connection_status = status
        print(f"[TelegramService] Status: {status} | Msg: {message}")
        if self.on_status_change:
            self.on_status_change(status, message)

    def start(self):
        if self.is_running:
            self.stop()

        cfg = self.config_manager.get("telegram", {})
        api_id = cfg.get("api_id")
        api_hash = cfg.get("api_hash")
        
        if not api_id or not api_hash:
            self._set_status("NO_CREDENTIALS", "API ID или API Hash не заполнены")
            return

        self.is_running = True
        self._set_status("CONNECTING", "Подключение к Telegram...")
        
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def _run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._connect_and_listen())
        except Exception as e:
            traceback.print_exc()
            self._set_status("ERROR", f"Ошибка: {str(e)}")
        finally:
            self.is_running = False

    async def _connect_and_listen(self):
        cfg = self.config_manager.get("telegram", {})
        api_id = int(str(cfg.get("api_id")).strip())
        api_hash = str(cfg.get("api_hash")).strip()
        phone = str(cfg.get("phone", "")).strip()
        self.phone = phone

        os.makedirs(DATA_DIR, exist_ok=True)
        self.client = TelegramClient(SESSION_PATH, api_id, api_hash, loop=self.loop)

        await self.client.connect()

        if not await self.client.is_user_authorized():
            if not phone:
                self._set_status("AUTH_PHONE_REQUIRED", "Требуется номер телефона для входа")
                return

            try:
                print(f"[TelegramService] Requesting code for phone: {phone}")
                sent = await self.client.send_code_request(phone)
                self.phone_code_hash = sent.phone_code_hash
                self._set_status("AUTH_CODE_REQUIRED", f"Код подтверждения отправлен на {phone}")
            except FloodWaitError as e:
                self._set_status("AUTH_ERROR", f"Слишком много попыток. Подождите {e.seconds} сек.")
                return
            except Exception as ex:
                self._set_status("AUTH_ERROR", f"Ошибка отправки кода: {str(ex)}")
                return

            # Keep client alive while waiting for user to input code
            while self.is_running and not await self.client.is_user_authorized():
                await asyncio.sleep(0.5)

            if not self.is_running or not await self.client.is_user_authorized():
                return

        self._set_status("CONNECTED", "Успешно подключено к Telegram!")
        self._register_handlers()
        await self._sync_recent_history()
        await self.client.run_until_disconnected()

    def submit_code(self, code: str):
        if not self.loop or not self.client:
            return {"success": False, "error": "Клиент не запущен. Нажмите 'Подключиться' снова."}
        
        future = asyncio.run_coroutine_threadsafe(self._auth_with_code(code), self.loop)
        try:
            return future.result(timeout=20)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _auth_with_code(self, code: str):
        code_clean = str(code).strip().replace(" ", "").replace("-", "")
        try:
            print(f"[TelegramService] Signing in with code: {code_clean}")
            await self.client.sign_in(self.phone, code_clean, phone_code_hash=self.phone_code_hash)
            self._set_status("CONNECTED", "Успешно подключено!")
            return {"success": True}
        except SessionPasswordNeededError:
            self._set_status("PASSWORD_REQUIRED", "Требуется 2FA пароль")
            return {"success": False, "requires_password": True, "error": "Требуется 2FA пароль"}
        except PhoneCodeInvalidError:
            self._set_status("AUTH_ERROR", "Неверный код подтверждения")
            return {"success": False, "error": "Неверный код подтверждения"}
        except PhoneCodeExpiredError:
            self._set_status("AUTH_ERROR", "Срок действия кода истек. Запросите заново.")
            return {"success": False, "error": "Срок действия кода истек"}
        except Exception as e:
            err_msg = str(e)
            if "Two-step verification" in err_msg or "password" in err_msg.lower():
                self._set_status("PASSWORD_REQUIRED", "Требуется 2FA пароль")
                return {"success": False, "requires_password": True, "error": err_msg}
            self._set_status("AUTH_ERROR", err_msg)
            return {"success": False, "error": err_msg}

    def submit_password(self, password: str):
        if not self.loop or not self.client:
            return {"success": False, "error": "Клиент не запущен"}
        future = asyncio.run_coroutine_threadsafe(self._auth_with_password(password), self.loop)
        try:
            return future.result(timeout=20)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _auth_with_password(self, password: str):
        try:
            print("[TelegramService] Signing in with 2FA password...")
            await self.client.sign_in(password=password)
            self._set_status("CONNECTED", "Успешно подключено!")
            return {"success": True}
        except Exception as e:
            self._set_status("AUTH_ERROR", str(e))
            return {"success": False, "error": str(e)}

    def _register_handlers(self):
        cfg = self.config_manager.get("telegram", {})
        bot_username = cfg.get("bot_username", "").lstrip("@").strip()
        address_filter = cfg.get("filter_address", "").strip().lower()

        @self.client.on(events.NewMessage())
        async def on_new_message(event):
            try:
                sender = await event.get_sender()
                sender_str = ""
                if sender:
                    sender_username = getattr(sender, 'username', '') or ''
                    sender_title = getattr(sender, 'title', '') or ''
                    sender_first = getattr(sender, 'first_name', '') or ''
                    sender_str = f"{sender_username} {sender_title} {sender_first}".lower()
                
                # Match bot if configured
                if bot_username:
                    bot_clean = bot_username.lower().lstrip("@")
                    if bot_clean not in sender_str:
                        if "відключення" not in (event.text or "") and "відновлено" not in (event.text or ""):
                            return

                msg_text = event.text or ""
                if not msg_text:
                    return

                # If address filter is specified, ensure it matches or is a direct address reply
                is_address_match = not address_filter or (address_filter in msg_text.lower()) or ("за вашою адресою" in msg_text.lower()) or ("не зафіксовано відключень" in msg_text.lower())
                if not is_address_match:
                    print(f"[Telegram] Message ignored (filter '{address_filter}' not found)")
                    return

                parsed = parse_message(msg_text)
                if parsed:
                    print(f"[Telegram] New Outage Status: {parsed['status']} | Address: {parsed['address']}")
                    self.storage_manager.save_state(parsed)
                    self.storage_manager.add_history(parsed)

                    # Send notification
                    if parsed["status"] == "OFF":
                        send_macos_notification(
                            "⚡ Внимание: Отключение света!",
                            f"Ориентировочно до {parsed['end_time_str'] or 'неизвестно'}",
                            f"{parsed['address']} ({parsed['reason']})",
                            sound="Basso"
                        )
                    else:
                        send_macos_notification(
                            "💡 Свет восстановлен!",
                            parsed['address'],
                            "Электроснабжение снова работает в штатном режиме.",
                            sound="Glass"
                        )

                    if self.on_state_updated:
                        self.on_state_updated(parsed)
            except Exception as ex:
                print(f"[Telegram] Error processing message: {ex}")

    async def _query_bot_status(self):
        cfg = self.config_manager.get("telegram", {})
        bot_username = cfg.get("bot_username", "").lstrip("@").strip()
        if not bot_username or not self.client:
            return
        try:
            entity = await self.client.get_input_entity(bot_username)
            print(f"[TelegramService] Resetting bot state with '/start' to @{bot_username}...")
            await self.client.send_message(entity, "/start")
            await asyncio.sleep(1.5)
            print(f"[TelegramService] Sending command '💡Можливі відключення' to @{bot_username}...")
            await self.client.send_message(entity, "💡Можливі відключення")
        except Exception as e:
            print(f"[TelegramService] Error sending query to bot: {e}")

    async def _sync_recent_history(self):
        cfg = self.config_manager.get("telegram", {})
        bot_username = cfg.get("bot_username", "").lstrip("@").strip()
        address_filter = cfg.get("filter_address", "").strip().lower()

        if not bot_username or not self.client:
            return

        try:
            print(f"[TelegramService] Syncing recent messages from @{bot_username}...")
            entity = await self.client.get_input_entity(bot_username)
            messages = await self.client.get_messages(entity, limit=20)
            
            for msg in messages:
                text = msg.text or ""
                if not text:
                    continue
                # If address filter is specified, check if present or direct address reply
                is_address_match = not address_filter or (address_filter in text.lower()) or ("за вашою адресою" in text.lower()) or ("не зафіксовано відключень" in text.lower())
                if not is_address_match:
                    continue

                parsed = parse_message(text)
                if parsed:
                    print(f"[TelegramService] Synced message: {parsed['status']} | {parsed['address']} | End: {parsed['end_time_str']}")
                    self.storage_manager.save_state(parsed)
                    self.storage_manager.add_history(parsed)
                    if self.on_state_updated:
                        self.on_state_updated(parsed)
                    break
        except Exception as e:
            print(f"[TelegramService] History sync info: {e}")

    def sync_now(self):
        if self.client and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._sync_recent_history(), self.loop)
            asyncio.run_coroutine_threadsafe(self._query_bot_status(), self.loop)

    def stop(self):
        self.is_running = False
        if self.client and self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            except Exception:
                pass
        self._set_status("DISCONNECTED", "Отключено")
