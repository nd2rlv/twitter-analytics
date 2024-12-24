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
    filename='twitter_analyzer.log'
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

    # Додаємо секцію пошуку перед вкладками
    st.header("🔍 Пошук твітів")
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Введіть пошуковий запит",
            value=selected_query if 'selected_query' in locals() and selected_query else "",
            help="Введіть ключові слова для пошуку твітів"
        )
    with col2:
        max_results = st.slider(
            "Максимальна кількість твітів",
            min_value=5,
            max_value=25,
            value=10
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
                st.session_state['current_analysis'] = analyzer.analyze_text_content(result['tweets'])
            else:
                try:
                    # Якщо кеш невалідний, робимо новий запит
                    with st.spinner("Отримуємо нові твіти..."):
                        tweets = collector.search_tweets(query, max_results)
                        if tweets:
                            # Зберігаємо твіти
                            db.save_tweets(tweets, query)
                            st.success(f"Знайдено {len(tweets)} нових твітів")
                            
                            # Аналізуємо твіти
                            analysis = analyzer.analyze_text_content(tweets)
                            
                            # Зберігаємо в session state
                            st.session_state['current_tweets'] = tweets
                            st.session_state['current_analysis'] = analysis
                            st.session_state['data_source'] = 'API'
                            st.session_state['last_updated'] = datetime.now().isoformat()
                except Exception as e:
                    st.error(f"Помилка при отриманні даних: {str(e)}")
                    # Спробуємо отримати старі дані з бази
                    result = db.get_tweets_by_query(query)
                    if result['tweets']:
                        st.warning("Використовуємо старі дані з бази")
                        st.session_state['current_tweets'] = result['tweets']
                        st.session_state['current_analysis'] = analyzer.analyze_text_content(result['tweets'])
                        st.session_state['data_source'] = 'База даних'
                        st.session_state['last_updated'] = result['last_updated']
                    else:
                        st.error("Дані не знайдені")
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
        if 'current_tweets' in st.session_state and 'current_analysis' in st.session_state:
            analysis = st.session_state['current_analysis']
            tweets = st.session_state['current_tweets']
            
            # Секція 1: Популярні теми
            st.subheader("📈 Популярні теми")
            if 'popular_phrases' in analysis and analysis['popular_phrases']:
                for topic_data in analysis['popular_phrases']:
                    if isinstance(topic_data, dict):
                        topic = topic_data.get('topic', '')
                        count = topic_data.get('count', 0)
                        st.write(f"#{topic}: {count} згадувань")
                    elif isinstance(topic_data, tuple):
                        topic, count = topic_data
                        st.write(f"#{topic}: {count} згадувань")
            
            # Секція 2: Тренди та обговорення
            st.subheader("💬 Ключові слова та активні обговорення")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("Ключові слова, що набирають популярність:")
                for word, increase in analysis['trending_topics']:
                    st.write(f"- {word}: +{increase} згадувань")
            
            with col2:
                st.write("Активні обговорення:")
                for disc in analysis['active_discussions']:
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
                    matching_tweets = [t for t in tweets if search_query.lower() in t['text'].lower()]
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
                    authors = list(set(t['author_id'] for t in tweets if topic.lower() in t['text'].lower()))
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
                    key=lambda x: x.get('total_interactions', 0),
                    reverse=True
                )
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
            
            # Показуємо топ-10 твітів
            st.write("Топ-10 твітів за обраним показником:")
            for tweet in sorted_tweets[:10]:
                metric_value = (tweet.get('total_interactions', 0) 
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

    # Вкладка 4: Sentiment Аналіз
    with tab4:
        st.header("Поглиблений аналіз твітів")
        if 'current_tweets' in st.session_state and 'current_analysis' in st.session_state:
            tweets = st.session_state['current_tweets']
            analysis = st.session_state['current_analysis']
            
            # Показуємо статистику sentiment
            st.subheader("📊 Статистика по темах")
            if 'sentiment_stats' in analysis:
                stats = analysis['sentiment_stats']
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Позитивні", stats.get('positive_count', 0))
                with col2:
                    st.metric("Нейтральні", stats.get('neutral_count', 0))
                with col3:
                    st.metric("Негативні", stats.get('negative_count', 0))
            
            # Топ обговорюваних тем
            st.subheader("🔝 Топ обговорюваних тем")
            if 'top_topics' in analysis:
                for topic in analysis['top_topics']:
                    with st.expander(f"{topic['name']} ({topic['count']} згадувань)"):
                        st.write(f"Контекст: {topic['context']}")
                        if 'examples' in topic:
                            st.write("Приклади твітів:")
                            for example in topic['examples']:
                                st.markdown(f"- {example}")
            
            # Трендовий аналіз
            st.subheader("📈 Аналіз трендів")
            if 'trends' in analysis:
                col1, col2 = st.columns(2)
                with col1:
                    st.write("🔥 Зростаючі тренди:")
                    for trend in analysis['trends'].get('rising', []):
                        st.write(f"- {trend['topic']} (+{trend['growth']}%)")
                
                with col2:
                    st.write("📉 Спадаючі тренди:")
                    for trend in analysis['trends'].get('falling', []):
                        st.write(f"- {trend['topic']} ({trend['growth']}%)")

        else:
            st.info("Спочатку виконайте пошук твітів")

if __name__ == "__main__":
    st.set_page_config(
        page_title="Twitter Analyzer",
        page_icon="📊",
        layout="wide"
    )
    main()