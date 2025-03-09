import pandas as pd

class NFTAnalyzer:
    def __init__(self, data):
        self.data = data

    def get_total_projects(self):
        """Get total number of unique projects"""
        if 'project_name' in self.data.columns:
            return self.data['project_name'].dropna().nunique()
        return 0

    def get_trending_projects(self, limit=10):
        """Get trending projects by mention count"""
        if 'project_name' in self.data.columns:
            projects = self.data.dropna(subset=['project_name'])
            counts = projects['project_name'].value_counts().reset_index()
            counts.columns = ['project', 'mentions']
            return counts.head(limit)
        return pd.DataFrame(columns=['project', 'mentions'])

    def get_trending_count(self):
        """Get count of trending projects (mentioned > 3 times)"""
        if 'project_name' in self.data.columns:
            projects = self.data.dropna(subset=['project_name'])
            counts = projects['project_name'].value_counts()
            return len(counts[counts > 3])
        return 0

    def get_activity_timeline(self):
        """Get project mention activity over time"""
        if 'date' in self.data.columns:
            return self.data.groupby(self.data['date'].dt.date).size()
        return pd.Series()

    def get_gift_givers(self, limit=20):
        """Анализ пользователей, которые получают больше всего NFT подарков"""
        import re

        # Создаем пустой DataFrame для результата
        gift_receivers = pd.DataFrame(columns=['Пользователь', 'Получено подарков', 'Проекты', 'Последнее получение'])

        if 'text' not in self.data.columns:
            return gift_receivers

        # Шаблоны для поиска информации о получении NFT
        gift_patterns = [
            r'получи[а-я]+ NFT',
            r'выигра[а-я]+ NFT',
            r'won NFT',
            r'получател[а-я]+ NFT',
            r'airdrop',
            r'giveaway winner',
            r'получи[а-я]+ бесплатн[а-я]+',
            r'congratulations to @\w+',
            r'поздравля[а-я]+ @\w+',
            r'winner[а-я]*: @\w+',
            r'побед[а-я]+ @\w+'
        ]

        # Объединим все шаблоны в один с помощью ИЛИ (|)
        combined_pattern = '|'.join(gift_patterns)

        # Выбираем сообщения, содержащие информацию о получении подарков
        gift_messages = self.data[self.data['text'].str.contains(combined_pattern, case=False, na=False, regex=True)]

        if gift_messages.empty:
            # Если сообщений о победителях нет, используем все сообщения о подарках и извлекаем упоминания
            gift_patterns_general = [
                r'подар[а-я]+ NFT',
                r'дар[а-я]+ NFT',
                r'airdrop',
                r'giveaway',
                r'gift[а-я]* NFT',
                r'бесплатн[а-я]+ NFT',
                r'free NFT',
                r'win[а-я]* NFT'
            ]
            combined_pattern_general = '|'.join(gift_patterns_general)
            gift_messages = self.data[self.data['text'].str.contains(combined_pattern_general, case=False, na=False, regex=True)]
            
            if gift_messages.empty:
                return gift_receivers

        # Извлекаем информацию о пользователях (получателях)
        # Ищем упоминания пользователей в контексте получения подарков
        user_pattern = r'@(\w+)'
        winner_patterns = [
            r'победител[а-я]*\W+@(\w+)',
            r'winner[a-z]*\W+@(\w+)',
            r'congratulations to @(\w+)',
            r'поздравля[а-я]+ @(\w+)',
            r'получател[а-я]*\W+@(\w+)'
        ]

        gift_data = []

        for _, message in gift_messages.iterrows():
            text = message['text'].lower()
            project = message['project_name'] if pd.notna(message['project_name']) else "Неизвестно"
            
            # Сначала ищем упоминания в контексте победителей
            winners = []
            for pattern in winner_patterns:
                winners.extend(re.findall(pattern, text, re.IGNORECASE))
            
            # Если не нашли упоминания в контексте победителей, берем все упоминания
            if not winners:
                winners = re.findall(user_pattern, message['text'])
            
            for user in winners:
                # Проверяем, есть ли уже этот пользователь в нашем списке
                found = False
                for i, (existing_user, gifts, projects, _) in enumerate(gift_data):
                    if existing_user == user:
                        gift_data[i] = (user, gifts + 1, 
                                        projects + [project] if project not in projects else projects, 
                                        message['date'])
                        found = True
                        break

                if not found:
                    gift_data.append((user, 1, [project] if pd.notna(project) else [], message['date']))

        # Сортируем по количеству полученных подарков (по убыванию)
        gift_data.sort(key=lambda x: x[1], reverse=True)

        # Создаем и возвращаем DataFrame
        if gift_data:
            result = pd.DataFrame(gift_data[:limit], 
                                 columns=['Пользователь', 'Получено подарков', 'Проекты', 'Последнее получение'])

            # Преобразуем списки проектов в строки
            result['Проекты'] = result['Проекты'].apply(lambda x: ', '.join(set(x)) if x else "Неизвестно")

            return result

        return gift_receivers

    def get_project_details(self):
        """Get detailed information about projects"""
        if 'project_name' not in self.data.columns:
            return pd.DataFrame()

        projects = []
        for project in self.data['project_name'].dropna().unique():
            project_data = self.data[self.data['project_name'] == project]

            channels = project_data['channel'].nunique() if 'channel' in self.data.columns else 0
            mentions = len(project_data)
            first_seen = project_data['date'].min() if 'date' in self.data.columns else None

            # Calculate average price if price data is available
            avg_price = None
            if 'price' in self.data.columns:
                prices = project_data['price'].dropna()
                if len(prices) > 0:
                    avg_price = prices.mean()

            # Определение настроения (сентимента) на основе текстов сообщений
            sentiment = self._analyze_sentiment(project_data)

            projects.append({
                'project': project,
                'mentions': mentions,
                'channels': channels,
                'first_seen': first_seen,
                'avg_price': avg_price,
                'sentiment': sentiment
            })

        return pd.DataFrame(projects).sort_values('mentions', ascending=False)

    def _analyze_sentiment(self, project_data):
        """Анализ настроения в сообщениях о проекте"""
        if 'text' not in project_data.columns or project_data.empty:
            return "Нейтральное"

        # Простые ключевые слова для определения настроения
        positive_words = [
            'отличн', 'круто', 'супер', 'классн', 'amazing', 'great', 'awesome',
            'крипто-луна', 'moon', 'pump', 'рост', 'выгодн', 'успешн', 'халяв',
            'бесплатн', 'airdrop', 'giveaway', 'выигр', 'win', 'перспектив',
            'потенциал', 'прибыль', 'доход', 'сильн', 'лучш', 'up'
        ]

        negative_words = [
            'плох', 'ужасн', 'bad', 'terrible', 'scam', 'скам', 'обман', 'развод',
            'хуже', 'потер', 'dump', 'падени', 'упад', 'опасн', 'рискован', 'потер', 
            'ошибк', 'проблем', 'down', 'медвеж', 'bear'
        ]

        # Объединяем все тексты
        all_text = ' '.join(project_data['text'].dropna()).lower()

        # Подсчитываем количество позитивных и негативных слов
        positive_count = sum(1 for word in positive_words if word in all_text)
        negative_count = sum(1 for word in negative_words if word in all_text)

        # Определяем преобладающее настроение
        if positive_count > negative_count * 1.5:
            return "Позитивное"
        elif negative_count > positive_count * 1.2:
            return "Негативное"
        else:
            return "Нейтральное"
