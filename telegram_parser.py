from telethon import TelegramClient, functions, types, errors
import pandas as pd
from datetime import datetime
import os
import asyncio
from typing import List, Dict, Set
import re

class TelegramParser:
    def __init__(self):
        # API ключи встроены напрямую в код
        # Замените эти значения на свои реальные ключи
        self.api_id = "12345678"  # Введите сюда ваш API ID от Telegram
        self.api_hash = "abcdef0123456789abcdef0123456789"  # Введите сюда ваш API Hash от Telegram
        self.client = None

    async def _connect(self):
        """Initialize Telegram client connection"""
        if not self.client:
            # Проверка наличия API ключей
            if not self.api_id or not self.api_hash:
                print("Ошибка: API ключи Telegram отсутствуют!")
                print(f"API ID присутствует: {'Да' if self.api_id else 'Нет'}")
                print(f"API Hash присутствует: {'Да' if self.api_hash else 'Нет'}")
                return None
                
            try:
                self.client = TelegramClient(
                    'nft_analyzer_session', 
                    api_id=int(self.api_id), 
                    api_hash=self.api_hash,
                    device_model="NFT Analyzer",
                    system_version="1.0",
                    app_version="1.0",
                    lang_code="ru"
                )
                try:
                    await self.client.connect()
                    print("Соединение с Telegram API установлено успешно")
                    
                    # Если нужно полное подключение с авторизацией
                    if not await self.client.is_user_authorized():
                        print("Пользователь не авторизован, необходимо пройти авторизацию через интерфейс приложения")
                    else:
                        print("Пользователь авторизован")
                        
                    return self.client
                except Exception as conn_err:
                    print(f"Ошибка при установке соединения: {str(conn_err)}")
                    self.client = None
                    return None
            except Exception as e:
                print(f"Ошибка при подключении к Telegram API: {str(e)}")
                if "bot" in str(e).lower():
                    print("⚠️ Вы используете Bot API ключи вместо User API ключей.")
                    print("Получите правильные ключи на https://my.telegram.org")
                self.client = None
                return None
        else:
            # Клиент уже существует, просто проверим его статус
            if not self.client.is_connected():
                try:
                    await self.client.connect()
                except Exception as e:
                    print(f"Ошибка при повторном подключении: {str(e)}")
                    return None
        
        return self.client

    async def leave_all_chats(self):
        """Leave all channels and groups that were joined previously"""
        if not self.client:
            await self._connect()
            
        if not self.client:
            print("Не удалось подключиться к Telegram API")
            return False
            
        try:
            count_success = 0
            count_failed = 0
            
            # Получаем диалоги пользователя
            async for dialog in self.client.iter_dialogs():
                if dialog.is_channel or dialog.is_group:
                    try:
                        # Проверяем, не является ли это личным чатом
                        if hasattr(dialog.entity, 'username') or hasattr(dialog.entity, 'title'):
                            chat_name = dialog.entity.username or dialog.entity.title
                            print(f"Попытка выйти из канала/группы: {chat_name}")
                            await self.client(functions.channels.LeaveChannelRequest(dialog.entity))
                            print(f"Успешно покинут канал/группа: {chat_name}")
                            count_success += 1
                            
                            # Добавляем задержку, чтобы избежать ограничений API
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"Ошибка при выходе из {dialog.name}: {str(e)}")
                        count_failed += 1
            
            print(f"Выход выполнен успешно из {count_success} каналов/групп, с ошибками - {count_failed}")
            return True
        except Exception as e:
            print(f"Ошибка при выходе из каналов/групп: {str(e)}")
            return False
    
    async def join_chat(self, chat_id: int, username: str = None) -> bool:
        """Join a channel or group, handling private chats and join requests"""
        try:
            if username:
                entity = await self.client.get_entity(username)
            else:
                entity = await self.client.get_entity(chat_id)

            try:
                await self.client(functions.channels.JoinChannelRequest(entity))
                print(f"Successfully joined {username or chat_id}")
                
                # Архивирование чата после подписки
                try:
                    await self.client(functions.folders.EditPeerFoldersRequest(
                        folder_peers=[types.InputFolderPeer(
                            peer=entity,
                            folder_id=1  # ID 1 - архивный чат
                        )]
                    ))
                    print(f"Archived chat {username or chat_id}")
                except Exception as archive_err:
                    print(f"Error archiving chat {username or chat_id}: {str(archive_err)}")
                
                # Отключение звука для чата
                try:
                    await self.client(functions.account.UpdateNotifySettingsRequest(
                        peer=entity,
                        settings=types.InputPeerNotifySettings(
                            mute_until=2147483647,  # Далекое будущее, отключение навсегда
                            show_previews=True,
                            silent=True
                        )
                    ))
                    print(f"Muted chat {username or chat_id}")
                except Exception as mute_err:
                    print(f"Error muting chat {username or chat_id}: {str(mute_err)}")
                
                return True
            except errors.UserAlreadyParticipantError:
                print(f"Already a member of {username or chat_id}")
                return True
            except errors.InviteRequestSentError:
                print(f"Join request sent to {username or chat_id}")
                return True
            except errors.ChannelPrivateError:
                print(f"Cannot join private channel/group {username or chat_id} without invitation")
                return False

        except Exception as e:
            print(f"Error joining {username or chat_id}: {str(e)}")
            return False

    async def get_user_channels(self) -> List[Dict]:
        """Получить список каналов и групп, на которые подписан пользователь"""
        await self._connect()
        
        if not self.client:
            print("Не удалось подключиться к Telegram API")
            return []
            
        channels_list = []
        chat_ids = set()  # Для отслеживания уникальности
        
        try:
            async for dialog in self.client.iter_dialogs():
                if dialog.is_channel or dialog.is_group:
                    # Проверяем, есть ли этот чат уже в списке
                    if dialog.id in chat_ids:
                        continue
                        
                    chat_type = 'channel' if dialog.is_channel else 'group'
                    chat_info = {
                        'id': dialog.id,
                        'title': dialog.name,
                        'username': dialog.entity.username if hasattr(dialog.entity, 'username') else None,
                        'participants_count': dialog.entity.participants_count if hasattr(dialog.entity, 'participants_count') else 0,
                        'description': dialog.entity.about if hasattr(dialog.entity, 'about') else '',
                        'type': chat_type,
                        'is_private': not hasattr(dialog.entity, 'username')
                    }
                    
                    # Добавляем в список и отмечаем как обработанный
                    chat_ids.add(dialog.id)
                    channels_list.append(chat_info)
                    
            print(f"Найдено {len(channels_list)} каналов и групп в подписках пользователя")
            return channels_list
        except Exception as e:
            print(f"Ошибка при получении списка каналов пользователя: {str(e)}")
            return []
    
    async def search_nft_groups(self, limit: int = 50, name_filter: str = None) -> List[Dict]:
        """Search for NFT-related channels and groups"""
        await self._connect()
        
        if not self.client:
            print("Не удалось подключиться к Telegram API")
            return []

        search_terms = ['NFT', 'nft', 'НФТ', 'нфт', 'crypto', 'blockchain']
        chats_list = []
        chat_ids = set()  # Используем ID для отслеживания уникальности

        for term in search_terms:
            try:
                result = await self.client(functions.contacts.SearchRequest(
                    q=term,
                    limit=limit
                ))

                for chat in result.chats:
                    # Include both channels and groups
                    if isinstance(chat, (types.Channel, types.Chat)):
                        # Проверяем, не добавили ли мы уже этот чат
                        if chat.id in chat_ids:
                            continue
                            
                        # Проверка имени канала/группы если указан фильтр
                        if name_filter and name_filter.lower() not in chat.title.lower():
                            continue
                            
                        chat_type = 'channel' if getattr(chat, 'broadcast', False) else 'group'
                        chat_info = {
                            'id': chat.id,
                            'title': chat.title,
                            'username': chat.username if hasattr(chat, 'username') else None,
                            'participants_count': chat.participants_count if hasattr(chat, 'participants_count') else 0,
                            'description': chat.about if hasattr(chat, 'about') else '',
                            'type': chat_type,
                            'is_private': not hasattr(chat, 'username')
                        }

                        # Добавляем ID в набор для отслеживания уникальности
                        chat_ids.add(chat.id)
                        chats_list.append(chat_info)
                        
                        # Пытаемся присоединиться к чату
                        await self.join_chat(chat.id, chat.username if hasattr(chat, 'username') else None)

            except Exception as e:
                print(f"Error searching for term {term}: {str(e)}")

        return chats_list

    async def _extract_nft_info(self, message: str) -> Dict:
        """Extract NFT project information from message text"""
        info = {
            'project_name': None,
            'price': None,
            'date': None
        }

        # Extract project name (assuming it's in caps or followed by NFT)
        project_match = re.search(r'([A-Z]{2,}(?:\s+[A-Z]{2,})*\s*(?:NFT)?)', message)
        if project_match:
            info['project_name'] = project_match.group(1).strip()

        # Extract price (looking for ETH/SOL/USD amounts)
        price_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ETH|SOL|\$)', message)
        if price_match:
            info['price'] = float(price_match.group(1))

        # Extract date
        date_patterns = [
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, message)
            if date_match:
                try:
                    info['date'] = datetime.strptime(date_match.group(), '%Y-%m-%d')
                except:
                    continue

        return info

    async def _fetch_channel_messages(self, channel: str, start_date, end_date) -> List[Dict]:
        """Fetch messages from a specific channel or group"""
        messages = []
        try:
            # Сначала попробуем получить сущность канала
            try:
                entity = await self.client.get_entity(channel)
                print(f"Успешно получена сущность для канала: {channel}")
            except Exception as entity_err:
                print(f"Ошибка получения сущности для {channel}: {str(entity_err)}")
                return messages
                
            async for message in self.client.iter_messages(
                entity,
                offset_date=end_date,
                reverse=True,
                limit=1000  # Limit the number of messages to analyze
            ):
                if message.date.date() < start_date:
                    break

                if message.text:
                    info = await self._extract_nft_info(message.text)
                    channel_title = entity.title if hasattr(entity, 'title') else channel
                    messages.append({
                        'channel': channel_title,
                        'channel_id': channel,
                        'date': message.date,
                        'text': message.text,
                        'project_name': info['project_name'],
                        'price': info['price'],
                        'views': message.views if hasattr(message, 'views') else 0,
                        'forwards': message.forwards if hasattr(message, 'forwards') else 0
                    })
                    
            print(f"Получено {len(messages)} сообщений из канала {channel}")
            
        except Exception as e:
            print(f"Ошибка получения сообщений из {channel}: {str(e)}")

        return messages

    def fetch_messages(self, channels: List[str], start_date, end_date) -> pd.DataFrame:
        """Fetch messages from multiple channels"""
        async def _fetch_all():
            await self._connect()
            all_messages = []
            for channel in channels:
                try:
                    channel_messages = await self._fetch_channel_messages(
                        channel, start_date, end_date
                    )
                    all_messages.extend(channel_messages)
                except Exception as e:
                    print(f"Error fetching messages from {channel}: {str(e)}")
            return all_messages

        # Create new event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        messages = loop.run_until_complete(_fetch_all())
        loop.close()

        return pd.DataFrame(messages)