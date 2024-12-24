# src/app.py
import logging
import streamlit as st
from src.collector import TwitterCollector
from src.analyzer import TweetAnalyzer
from src.database import TweetDatabase
from src.exceptions import NetworkError, RateLimitError, ParsingError
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='twitter_analyzer.log'  # файл для логів
)
logger = logging.getLogger(__name__)

def init_components():
    """Ініціалізація компонентів програми"""
    return TwitterCollector(), TweetAnalyzer(), TweetDatabase()

def main():
    st.title("Twitter Analyzer 📊")

    # Ініціалізуємо компоненти
    collector, analyzer, db = init_components()
    
    # Sidebar
    st.sidebar.header("Про програму")
    st.sidebar.info(
        "Цей інструмент дозволяє:\n"
        "- Аналізувати текстовий контент твітів\n"
        "- Виконувати пошукові запити\n"
        "- Генерувати статистичні звіти"
    )

    # Додаємо роздільник в sidebar
    st.sidebar.markdown("---")

    # Історія пошуків в sidebar
    st.sidebar.header("Історія пошуків")
    previous_queries = db.get_all_queries()
    if previous_queries:
        selected_query = st.sidebar.selectbox(
            "Виберіть попередній запит",
            [""] + previous_queries,
            index=0
        )
    else:
        st.sidebar.info("Історія пошуків порожня")

    analysis = {}
    
    # Додаємо секцію пошуку перед вкладками
    st.header("🔍 Пошук твітів")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("Топ-5 ключових слів:")
        for keyword_data in analysis.get('trending_topics', [])[:5]:
            st.write(f"- {keyword_data['keyword']} (Контекст: {keyword_data['context']})")
            st.caption(f"Кількість: {keyword_data['count']}, Семантичний бал: {keyword_data['semantic_score']}")
    with col2:
        max_results = st.slider(
            "Максимальна кількість твітів",
            min_value=5,
            max_value=25,
            value=10,
            key="max_results_slider_main"
        )

    query = st.text_input(
        "Введіть пошуковий запит",
        help="Введіть ключові слова для пошуку твітів"
    )

    max_results = st.slider(
        "Максимальна кількість твітів",
        min_value=5,
        max_value=25,
        value=10,
        key="max_results_slider_search"
    )

    if st.button("Пошук", type="primary"):
        if query:
            # Спочатку перевіряємо кеш
            if db.is_cache_valid(query):
                result = db.get_tweets_by_query(query)
                st.info(f"Використовуємо кешовані дані (дійсні до {result['cached_until']})")
                st.session_state['current_tweets'] = result['tweets']
                st.session_state['data_source'] = 'Кеш'
                st.session_state['last_updated'] = result['last_updated']

                # Аналіз кешованих твітів
                analysis = analyzer.analyze_text_content(result['tweets'], max_results)
            else:
                # Якщо кеш невалідний, робимо новий запит
                tweets = collector.search_tweets(query, max_results)
                
                if tweets:
                    # Аналізуємо твіти
                    analysis = analyzer.analyze_text_content(tweets, max_results)
                    
                    st.subheader("🔑 Топ-5 ключових слів")
                    for keyword_data in analysis.get('trending_keywords', [])[:5]:
                        st.write(f"- {keyword_data['keyword']}")
                        st.caption(keyword_data.get('context', 'Trend in crypto domain'))
                    
                    # Зберігаємо твіти в сесію
                    st.session_state['current_tweets'] = tweets
                    st.session_state['data_source'] = 'API'
                    st.session_state['last_updated'] = datetime.now().isoformat()
        else:
            st.error("Введіть пошуковий запит")
    
    # Основні вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Аналіз тексту", 
        "🔍 Пошукові запити",
        "📊 Статистика",
        "🧠 Sentiment Аналіз"
    ])
        
    # Вкладка 1: Аналіз тексту
    with tab1:
        st.header("Аналіз текстового контенту твітів")
        if 'current_tweets' in st.session_state:
            tweets = st.session_state['current_tweets']
            
            # Комплексний аналіз
            analysis = analyzer.analyze_text_content(tweets, max_results)
            
            # Секція 1: Популярні теми
            st.subheader("📈 Топ-5 популярних тем")
            for topic in analysis['popular_phrases'][:5]:
                st.write(f"#{topic['topic']} (Важливість: {topic['significance']})")
            
            # Секція 2: Тренди та обговорення
            st.subheader("💬 Топ-5 ключових слів та активних обговорень")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("Топ-5 ключових слів:")
                for word, increase in analysis['trending_topics'][:5]:
                    st.write(f"- {word}: +{increase} згадувань")
            
            with col2:
                st.write("Топ-5 активних обговорень:")
                for disc in analysis['active_discussions'][:5]:
                    with st.expander(f"Твіт з {disc['replies']} відповідями"):
                        st.write(disc['tweet'])
                        st.caption(f"Створено: {disc['created_at']}")
            
            # Секція 3: Пошук по тексту
            st.subheader("🔍 Пошук по текстовим даним")
            search_col1, search_col2 = st.columns([3, 1])
            with search_col1:
                search_text = st.text_input("Введіть текст для пошуку", key="text_search")
            with search_col2:
                search_type = st.selectbox(
                    "Тип пошуку",
                    ["Точний збіг", "Частковий збіг", "За фразою"]
                )
            
            if search_text:
                search_results = analyzer.search_in_tweets(tweets, search_text, search_type)
                if search_results:
                    st.write(f"Знайдено {len(search_results)} твітів:")
                    for tweet in search_results:
                        with st.expander(f"Твіт від {tweet['created_at']}"):
                            st.write(tweet['text'])
                            st.caption(f"Автор: {tweet['author_id']}")
                else:
                    st.warning("За вашим запитом нічого не знайдено")
            
        else:
            st.info("Спочатку виконайте пошук твітів")
    
    # Вкладка 2: Пошукові запити
    with tab2:
        st.header("Пошукові запити")
        if 'current_tweets' in st.session_state:
            tweets = st.session_state['current_tweets']
            
            # Вибір типу пошуку
            search_type = st.radio(
                "Оберіть тип пошуку:",
                ["Пошук твітів", "Пошук авторів"]
            )
            
            # Пошук твітів
            if search_type == "Пошук твітів":
                st.subheader("🔍 Пошук твітів за темою або словом")
                search_query = st.text_input("Введіть тему або слово для пошуку")
                if search_query:
                    matching_tweets = analyzer.search_by_keyword(tweets, search_query)
                    st.write(f"Знайдено {len(matching_tweets)} твітів")
                    for tweet in matching_tweets:
                        with st.expander(f"Твіт від {tweet['created_at']}"):
                            st.write(tweet['text'])
                            st.caption(f"Автор: {tweet['author_id']}")
                            metrics = tweet['metrics']
                            st.caption(
                                f"Взаємодії: "
                                f"👍 {metrics.get('like_count', 0)} лайків, "
                                f"🔄 {metrics.get('retweet_count', 0)} ретвітів, "
                                f"💬 {metrics.get('reply_count', 0)} відповідей"
                            )
            
            # Пошук авторів
            else:
                st.subheader("👥 Пошук авторів за темою")
                topic = st.text_input("Введіть тему або фразу")
                if topic:
                    authors = analyzer.find_users_by_topic(tweets, topic)
                    st.write(f"Знайдено {len(authors)} авторів")
                    
                    # Для кожного автора показуємо його твіти на цю тему
                    for author in authors:
                        with st.expander(f"Автор: {author}"):
                            author_tweets = [t for t in tweets if t['author_id'] == author and topic.lower() in t['text'].lower()]
                            st.write(f"Кількість твітів на цю тему: {len(author_tweets)}")
                            for tweet in author_tweets:
                                st.write(f"- {tweet['text']}")
                                st.caption(f"Створено: {tweet['created_at']}")
                            
        else:
            st.info("Спочатку виконайте пошук твітів")
    
    # Вкладка 3: Статистика
    with tab3:
        st.header("Статистичний аналіз")
        if 'current_tweets' in st.session_state:
            tweets = st.session_state['current_tweets']
            
            # Секція 1: Аналіз по користувачу
            st.subheader("👤 Аналіз твітів користувача")
            # Отримуємо унікальних авторів
            authors = list(set(tweet['author_id'] for tweet in tweets))
            selected_author = st.selectbox(
                "Виберіть користувача",
                authors
            )
            
            if selected_author:
                metric = st.selectbox(
                    "Виберіть метрику",
                    ['retweet_count', 'reply_count', 'like_count', 'quote_count'],
                    format_func=lambda x: {
                        'retweet_count': 'Ретвіти',
                        'reply_count': 'Відповіді',
                        'like_count': 'Лайки',
                        'quote_count': 'Цитування'
                    }[x]
                )
                
                # Показуємо топ твіти користувача
                user_tweets = [t for t in tweets if t['author_id'] == selected_author]
                sorted_tweets = sorted(
                    user_tweets,
                    key=lambda x: x['metrics'].get(metric, 0),
                    reverse=True
                )
                
                st.write(f"Топ твіти користувача за кількістю {metric}:")
                for tweet in sorted_tweets[:5]:
                    with st.expander(f"{metric}: {tweet['metrics'].get(metric, 0)}"):
                        st.write(tweet['text'])
                        st.caption(f"Створено: {tweet['created_at']}")
            
            # Секція 2: Найпопулярніші твіти
            st.subheader("🔥 Твіти з найбільшим інтересом")
            
            interest_metric = st.radio(
                "Оберіть показник інтересу",
                ["Загальні взаємодії", "Ретвіти", "Відповіді", "Лайки"]
            )
            
            if interest_metric == "Загальні взаємодії":
                # Рахуємо сумарну кількість всіх взаємодій
                for tweet in tweets:
                    tweet['total_interactions'] = sum(
                        tweet['metrics'].get(m, 0) 
                        for m in ['retweet_count', 'reply_count', 'like_count', 'quote_count']
                    )
                sorted_tweets = sorted(
                    tweets,
                    key=lambda x: x['total_interactions'],
                    reverse=True
                )
                metric_name = 'total_interactions'
            else:
                metric_map = {
                    "Ретвіти": "retweet_count",
                    "Відповіді": "reply_count",
                    "Лайки": "like_count"
                }
                sorted_tweets = sorted(
                    tweets,
                    key=lambda x: x['metrics'].get(metric_map[interest_metric], 0),
                    reverse=True
                )
                metric_name = metric_map[interest_metric]
            
            # Показуємо топ-10 твітів
            st.write("Топ-10 твітів за обраним показником:")
            for tweet in sorted_tweets[:10]:
                metric_value = (tweet['total_interactions'] 
                              if interest_metric == "Загальні взаємодії"
                              else tweet['metrics'].get(metric_map[interest_metric], 0))
                with st.expander(f"Кількість взаємодій: {metric_value}"):
                    st.write(tweet['text'])
                    st.caption(f"Автор: {tweet['author_id']}")
                    st.caption(f"Створено: {tweet['created_at']}")
                    st.caption(
                        f"Детальна статистика: "
                        f"🔄 {tweet['metrics'].get('retweet_count', 0)} ретвітів, "
                        f"💬 {tweet['metrics'].get('reply_count', 0)} відповідей, "
                        f"👍 {tweet['metrics'].get('like_count', 0)} лайків, "
                        f"📝 {tweet['metrics'].get('quote_count', 0)} цитувань"
                    )
            
        else:
            st.info("Спочатку виконайте пошук твітів")

    # Вкладка 4: Поглиблений аналіз твітів
    with tab4:
        st.header("Поглиблений аналіз твітів")
        if 'current_tweets' in st.session_state:
            tweets = st.session_state['current_tweets']
            
            # Виконуємо розширений аналіз
            advanced_analysis = analyzer.advanced_tweet_analysis(tweets)
            
            # Показуємо статистику sentiment
            st.subheader("📊 Статистика Sentiment")
            stats = advanced_analysis['sentiment_stats']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Позитивні", stats['positive_count'])
            with col2:
                st.metric("Нейтральні", stats['neutral_count'])
            with col3:
                st.metric("Негативні", stats['negative_count'])
            
            # Топ емоцій
            st.subheader("😀 Топ емоцій")
            for emotion, count in advanced_analysis['top_emotions']:
                st.write(f"{emotion}: {count}")
            
            # Детальний аналіз трендів
            st.subheader("🔍 Ключові тренди")
            for trend in analysis.get('significant_trends', []):
                st.markdown(f"**{trend['title']}**")
                st.write(f"*Контекст*: {trend['context']}")
                st.caption(f"*Потенційний вплив*: {trend['potential_impact']}")
        else:
            st.info("Спочатку виконайте пошук твітів")

if __name__ == "__main__":
    st.set_page_config(
        page_title="Twitter Analyzer",
        page_icon="📊",
        layout="wide"
    )
    main()