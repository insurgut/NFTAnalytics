import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import asyncio

from telegram_parser import TelegramParser
from data_analyzer import NFTAnalyzer
from utils import load_channels, save_data, load_data
from auth import show_auth_page

st.set_page_config(page_title="NFT Analytics", layout="wide")

# Initialize session state
if 'is_authenticated' not in st.session_state:
    st.session_state.is_authenticated = False
if 'data_updated' not in st.session_state:
    st.session_state.data_updated = None
if 'found_channels' not in st.session_state:
    st.session_state.found_channels = None

def search_channels():
    with st.spinner("Поиск NFT каналов и групп..."):
        parser = TelegramParser()
        # Create new event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            channels = loop.run_until_complete(parser.search_nft_groups())
            loop.close()
            
            if channels and len(channels) > 0:
                st.session_state.found_channels = channels
                st.success(f"Найдено {len(channels)} каналов и групп")
            else:
                st.warning("Не найдено каналов и групп. Попробуйте другие ключевые слова или проверьте подключение.")
                # Если нет результатов, проверим хотя бы пустой список
                if channels is None:
                    st.session_state.found_channels = []
                else:
                    st.session_state.found_channels = channels
                    
            return channels
        except Exception as e:
            st.error(f"Ошибка при поиске каналов: {str(e)}")
            st.session_state.found_channels = []
            loop.close()
            return []

def main():
    # Проверка авторизации
    if not st.session_state.is_authenticated:
        show_auth_page()
        return

    st.title("Аналитика NFT Проектов")

    # Sidebar configuration
    st.sidebar.header("Настройки")

    # Поиск каналов
    st.sidebar.subheader("Поиск каналов")
    
    # Фильтр по имени
    channel_name_filter = st.sidebar.text_input("Фильтр по имени канала/группы", "")
    
    # Кнопки для поиска и получения каналов
    col_search1, col_search2 = st.sidebar.columns(2)
    with col_search1:
        if st.button("Найти NFT каналы", use_container_width=True):
            with st.spinner("Поиск NFT каналов и групп..."):
                parser = TelegramParser()
                # Create new event loop for async operations
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Используем фильтр по имени если указан
                    channels = loop.run_until_complete(parser.search_nft_groups(
                        name_filter=channel_name_filter if channel_name_filter else None
                    ))
                    loop.close()
                    
                    if channels and len(channels) > 0:
                        st.session_state.found_channels = channels
                        st.success(f"Найдено {len(channels)} каналов и групп")
                    else:
                        st.warning("Не найдено каналов и групп. Попробуйте другие ключевые слова или проверьте подключение.")
                        # Если нет результатов, проверим хотя бы пустой список
                        if channels is None:
                            st.session_state.found_channels = []
                        else:
                            st.session_state.found_channels = channels
                except Exception as e:
                    st.error(f"Ошибка при поиске каналов: {str(e)}")
                    st.session_state.found_channels = []
                    loop.close()
    
    with col_search2:
        if st.button("Мои подписки", use_container_width=True):
            with st.spinner("Получение списка ваших каналов..."):
                parser = TelegramParser()
                # Create new event loop for async operations
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    channels = loop.run_until_complete(parser.get_user_channels())
                    loop.close()
                    
                    if channels and len(channels) > 0:
                        # Применяем фильтр по имени, если указан
                        if channel_name_filter:
                            channels = [ch for ch in channels if channel_name_filter.lower() in ch['title'].lower()]
                            
                        st.session_state.found_channels = channels
                        st.success(f"Найдено {len(channels)} ваших каналов и групп")
                    else:
                        st.warning("У вас нет подписок на каналы и группы")
                        st.session_state.found_channels = []
                except Exception as e:
                    st.error(f"Ошибка при получении списка каналов: {str(e)}")
                    st.session_state.found_channels = []
                    loop.close()
                    
    # Кнопка для выхода из всех каналов
    if st.sidebar.button("Отписаться от всех каналов"):
        with st.spinner("Выход из каналов Telegram..."):
            parser = TelegramParser()
            # Create new event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(parser.leave_all_chats())
                loop.close()
                
                if result:
                    # Также очищаем список найденных каналов
                    if 'found_channels' in st.session_state:
                        st.session_state.found_channels = []
                    st.success("Успешно выполнен выход из всех каналов Telegram")
                    st.rerun()
                else:
                    st.error("Не удалось выйти из каналов. Проверьте подключение к Telegram API.")
            except Exception as e:
                st.error(f"Ошибка при выходе из каналов: {str(e)}")
                loop.close()

    # Display found channels if available
    channels = []
    if st.session_state.found_channels:
        st.sidebar.subheader("Найденные NFT-сообщества")
        channels_df = pd.DataFrame(st.session_state.found_channels)

        # Add emoji indicators for type and privacy
        channels_df['Статус'] = channels_df.apply(
            lambda x: f"{'📢' if x['type'] == 'channel' else '👥'} "
                     f"{'🔒' if x['is_private'] else '🌐'} {x['title']}", 
            axis=1
        )

        selected_channels = st.sidebar.data_editor(
            channels_df[['Статус', 'participants_count', 'type']],
            hide_index=False,  # Показываем индексы для правильного выбора
            column_config={
                "Статус": "Канал/Группа",
                "participants_count": "Участники",
                "type": "Тип"
            },
            use_container_width=True
        )
        
        # Получаем индексы выбранных строк
        if not selected_channels.empty:
            selected_indices = selected_channels.index.tolist()
            channels = []
            for i in selected_indices:
                if i < len(channels_df):
                    # Используем username если доступен, иначе используем ID канала
                    if channels_df.iloc[i]['username']:
                        channels.append(channels_df.iloc[i]['username'])
                    else:
                        channels.append(str(channels_df.iloc[i]['id']))
        else:
            channels = []
    else:
        # Default channels as fallback
        default_channels = ["NFTCalendar", "NFTDrops", "NFTProject"]
        channels_text = st.sidebar.text_area(
            "Или введите каналы Telegram вручную (по одному на строку)", 
            "\n".join(default_channels)
        )
        channels = [ch.strip() for ch in channels_text.split("\n") if ch.strip()]

    # Date range selection
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("Дата окончания", datetime.now())

    # Update data button
    if st.sidebar.button("Обновить данные"):
        if not channels:
            st.sidebar.error("Необходимо выбрать хотя бы один канал для анализа!")
        else:
            with st.spinner(f"Получение данных из {len(channels)} Telegram каналов..."):
                parser = TelegramParser()
                messages = parser.fetch_messages(channels, start_date, end_date)

                if not messages.empty:
                    save_data(messages)
                    st.session_state.data_updated = datetime.now()
                    st.success(f"Данные успешно обновлены! Получено {len(messages)} сообщений из {messages['channel'].nunique()} каналов.")
                else:
                    st.error("Данные не получены. Это может быть вызвано следующими причинами:\n" +
                            "1. Выбранные каналы не содержат NFT-сообщений\n" +
                            "2. Проблемы с подключением к API Telegram\n" +
                            "3. Необходимо подписаться на каналы перед получением данных")
                    
                    # Предложим пользователю найти больше каналов
                    if st.sidebar.button("Найти больше NFT-каналов"):
                        search_channels()

    # Load and analyze data
    data = load_data()
    if data is not None and not data.empty:
        analyzer = NFTAnalyzer(data)

        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего проектов", analyzer.get_total_projects())
        with col2:
            st.metric("Активные сообщества", len(channels))
        with col3:
            st.metric("Популярные проекты", analyzer.get_trending_count())

        # Trending Projects
        st.subheader("Популярные NFT проекты")
        trending = analyzer.get_trending_projects()
        fig = px.bar(
            trending,
            x='project',
            y='mentions',
            title="Самые упоминаемые NFT проекты",
            labels={'project': 'Проект', 'mentions': 'Упоминания'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Информация о популярных проектах
        if not trending.empty and len(trending) > 0:
            st.info("""
            **Что показывает этот график?**
            1. **Популярность проекта**: Чем выше столбец, тем чаще проект упоминался в сообществах
            2. **Потенциал роста**: Проекты с большим количеством упоминаний обычно имеют активное сообщество
            3. **Тренды рынка**: График отражает текущие тенденции на рынке NFT
            """)

        # Activity Timeline
        st.subheader("Временная шкала активности проектов")
        timeline = analyzer.get_activity_timeline()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timeline.index,
            y=timeline.values,
            mode='lines+markers'
        ))
        fig.update_layout(
            title="Ежедневные упоминания NFT проектов",
            xaxis_title="Дата",
            yaxis_title="Количество упоминаний"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("""
        **О чем говорит этот график?**
        1. **Динамика интереса**: Пики на графике показывают дни с наибольшей активностью обсуждений
        2. **Циклы внимания**: Можно заметить периоды роста и спада интереса к NFT проектам
        3. **Рыночные события**: Резкие скачки часто связаны с важными событиями в индустрии
        """)

        # Project Details Table
        st.subheader("Детали проектов")
        project_details = analyzer.get_project_details()
        
        # Переименовываем колонки для русского языка
        if not project_details.empty:
            project_details = project_details.rename(columns={
                'project': 'Проект',
                'mentions': 'Упоминания',
                'channels': 'Каналы',
                'first_seen': 'Первое упоминание',
                'avg_price': 'Средняя цена',
                'sentiment': 'Настроение'
            })
            
        st.dataframe(project_details, use_container_width=True)
        
        st.info("""
        **Как интерпретировать эту таблицу?**
        1. **Проект**: Название NFT проекта, обнаруженного в сообщениях
        2. **Упоминания**: Сколько раз проект был упомянут во всех отслеживаемых каналах
        3. **Каналы**: В скольких разных каналах обсуждался проект
        4. **Первое упоминание**: Когда проект впервые появился в анализируемых данных
        5. **Средняя цена**: Усредненная стоимость, если она указывалась в сообщениях
        6. **Настроение**: Общее эмоциональное отношение к проекту в сообществе
        """)

    else:
        st.info("Данные отсутствуют. Пожалуйста, обновите данные с помощью кнопки в боковой панели.")

    # Footer
    st.sidebar.markdown("---")
    if st.session_state.data_updated:
        st.sidebar.text(f"Последнее обновление: {st.session_state.data_updated}")

    # Logout button
    if st.sidebar.button("Выйти"):
        st.session_state.is_authenticated = False
        st.rerun()

if __name__ == "__main__":
    main()