import streamlit as st
from telethon import TelegramClient, functions, types, errors
import os
import asyncio
from typing import Optional, Tuple

class TelegramAuth:
    def __init__(self):
        # API ключи встроены напрямую в код
        # Замените эти значения на свои реальные ключи
        self.api_id = "12345678"  # Введите сюда ваш API ID от Telegram
        self.api_hash = "abcdef0123456789abcdef0123456789"  # Введите сюда ваш API Hash от Telegram
        self.client = None

    async def _connect(self) -> TelegramClient:
        """Initialize Telegram client connection"""
        if not self.client:
            # Проверка наличия API ключей
            if not self.api_id or not self.api_hash:
                print("Ошибка: API ключи отсутствуют!")
                print(f"API ID присутствует: {'Да' if self.api_id else 'Нет'}")
                print(f"API Hash присутствует: {'Да' if self.api_hash else 'Нет'}")
                return None
            
            try:
                # Инициализация клиента с параметрами для user-режима
                self.client = TelegramClient(
                    'nft_analyzer_session',
                    api_id=int(self.api_id),  # Преобразуем в int
                    api_hash=self.api_hash,
                    device_model="NFT Analyzer",
                    system_version="1.0",
                    app_version="1.0",
                    lang_code="ru"
                )
            except Exception as e:
                print(f"Ошибка инициализации клиента: {str(e)}")
                return None

        if not self.client.is_connected():
            await self.client.connect()

        return self.client

    async def send_code(self, phone: str) -> Tuple[bool, str]:
        """Send authentication code to phone number"""
        try:
            client = await self._connect()
            if not client:
                return False, "Ошибка инициализации клиента. Проверьте API ключи в Secrets."
            
            if not client.is_connected():
                try:
                    await client.connect()
                except Exception as conn_err:
                    return False, f"Ошибка подключения к Telegram: {str(conn_err)}"
                
                if not client.is_connected():
                    return False, "Не удалось установить соединение с серверами Telegram"

            # Отправляем код подтверждения
            try:
                result = await client(functions.auth.SendCodeRequest(
                    phone_number=phone,
                    api_id=int(self.api_id),
                    api_hash=self.api_hash,
                    settings=types.CodeSettings(
                        allow_flashcall=False,
                        current_number=True,
                        allow_app_hash=True,
                    )
                ))
                # Сохраняем phone_code_hash для последующей авторизации
                if not hasattr(st.session_state, 'phone_code_hash'):
                    st.session_state.phone_code_hash = result.phone_code_hash
                else:
                    st.session_state.phone_code_hash = result.phone_code_hash
                
                print(f"Получен phone_code_hash: {result.phone_code_hash}")
                return True, "Код подтверждения отправлен"
            except errors.PhoneNumberInvalidError:
                return False, "Неверный формат номера телефона. Используйте международный формат, например +7XXXXXXXXXX"
            except Exception as req_err:
                error_msg = str(req_err)
                print(f"Подробная ошибка при отправке кода: {error_msg}")
                if "api_id" in error_msg.lower() or "api_hash" in error_msg.lower() or "bot" in error_msg.lower():
                    return False, "Ошибка настройки приложения. Пожалуйста, проверьте API ключи."
                return False, f"Ошибка отправки кода: {error_msg}"
        except Exception as e:
            print(f"Общая ошибка в методе send_code: {str(e)}")
            return False, f"Ошибка отправки кода: {str(e)}"

    async def sign_in(self, phone: str, code: str, password: Optional[str] = None) -> Tuple[bool, str]:
        """Sign in with code and optional 2FA password"""
        try:
            client = await self._connect()
            try:
                # Проверяем наличие phone_code_hash в сессии
                phone_code_hash = getattr(st.session_state, 'phone_code_hash', None)
                if not phone_code_hash:
                    return False, "Отсутствует код подтверждения (phone_code_hash). Пожалуйста, запросите код заново."
                
                print(f"Используем phone_code_hash: {phone_code_hash}")
                # Используем сохраненный phone_code_hash для авторизации
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                return True, "Успешная авторизация"
            except errors.SessionPasswordNeededError:
                if password:
                    await client.sign_in(password=password)
                    return True, "Успешная авторизация через 2FA"
                return False, "Требуется пароль 2FA"
            except Exception as e:
                return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка авторизации: {str(e)}"

def show_auth_page():
    """Display authentication page"""
    st.title("Авторизация в Telegram")

    if 'auth_stage' not in st.session_state:
        st.session_state.auth_stage = 'phone'
    if 'auth_message' not in st.session_state:
        st.session_state.auth_message = ''
    if 'phone' not in st.session_state:
        st.session_state.phone = ''

    # Информация о необходимости авторизации
    st.markdown("""
    📱 **Почему нужен вход через Telegram и как это работает?**

    Наше приложение использует Telegram для анализа NFT проектов и трендов в криптовалютном пространстве. Авторизация через Telegram необходима для получения доступа к актуальной информации из различных каналов и групп. Это позволяет нам предоставлять вам самые свежие данные о новых проектах, трендах и возможностях в мире NFT. При входе через Telegram вы получаете возможность автоматического поиска релевантных каналов и групп, что значительно упрощает процесс сбора информации. Мы используем официальное API Telegram, что гарантирует безопасность ваших данных и соответствие всем требованиям платформы. Важно отметить, что мы запрашиваем только доступ для чтения информации - никаких сообщений или действий от вашего имени совершаться не будет. После успешной авторизации вы сможете использовать все функции приложения, включая автоматический поиск NFT проектов, анализ трендов и мониторинг активности в различных сообществах. Это позволит вам всегда быть в курсе последних событий и принимать информированные решения в мире NFT. Безопасность ваших данных является нашим приоритетом - мы не храним ваши личные данные и используем защищенное соединение для всех операций.
    """)

    auth = TelegramAuth()

    if st.session_state.auth_message:
        st.info(st.session_state.auth_message)

    if st.session_state.auth_stage == 'phone':
        phone = st.text_input("Номер телефона (в международном формате)", 
                            value=st.session_state.phone,
                            placeholder="+7XXXXXXXXXX")

        if st.button("Получить код"):
            if phone:
                st.session_state.phone = phone
                # Send code
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success, message = loop.run_until_complete(auth.send_code(phone))
                loop.close()

                if success:
                    st.session_state.auth_stage = 'code'
                    st.session_state.auth_message = message
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Введите номер телефона")

    elif st.session_state.auth_stage == 'code':
        st.text_input("Номер телефона", value=st.session_state.phone, disabled=True)
        code = st.text_input("Код подтверждения", type="password")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Изменить номер"):
                st.session_state.auth_stage = 'phone'
                st.session_state.auth_message = ''
                st.rerun()

        with col2:
            if st.button("Подтвердить"):
                if code:
                    # Verify code
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success, message = loop.run_until_complete(
                        auth.sign_in(st.session_state.phone, code)
                    )
                    loop.close()

                    if success:
                        st.session_state.is_authenticated = True
                        st.session_state.auth_message = message
                        st.rerun()
                    elif "2fa" in message.lower():
                        st.session_state.auth_stage = '2fa'
                        st.session_state.auth_message = message
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Введите код подтверждения")

    elif st.session_state.auth_stage == '2fa':
        st.text_input("Номер телефона", value=st.session_state.phone, disabled=True)
        password = st.text_input("Пароль 2FA", type="password")

        if st.button("Подтвердить"):
            if password:
                # Verify 2FA
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success, message = loop.run_until_complete(
                    auth.sign_in(st.session_state.phone, None, password)
                )
                loop.close()

                if success:
                    st.session_state.is_authenticated = True
                    st.session_state.auth_message = message
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Введите пароль 2FA")