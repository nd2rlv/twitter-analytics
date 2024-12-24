# test_integration.py
from src.collector import TwitterCollector
from src.analyzer import TweetAnalyzer
from src.database import TweetDatabase
import os
import json
from datetime import datetime

def ensure_data_directory():
    """Перевірка та створення директорії для даних"""
    if not os.path.exists('data'):
        os.makedirs('data')

def test_full_pipeline():
    print("Початок комплексного тестування...")
    
    # Ініціалізація компонентів
    collector = TwitterCollector()
    analyzer = TweetAnalyzer()
    db = TweetDatabase()
    
    # Крок 1: Збір даних
    print("\n1. Збір твітів...")
    search_query = "python programming"
    tweets = collector.search_tweets(search_query, max_results=10)
    
    if not tweets:
        print("Не вдалося отримати твіти. Перевіряємо наявні дані в БД...")
        tweets = db.get_tweets_by_query(search_query)
        if not tweets:
            print("Дані відсутні в БД. Тестування неможливе.")
            return
    else:
        print(f"Отримано {len(tweets)} твітів")
        # Зберігаємо в БД
        print("\n2. Збереження твітів в базу даних...")
        db.save_tweets(tweets, search_query)
    
    # Крок 3: Аналіз даних
    print("\n3. Аналіз даних:")
    
    print("\nа) Популярні теми:")
    trending_topics = analyzer.find_trending_topics(tweets, top_n=5)
    for topic, count in trending_topics:
        print(f"   - {topic}: {count} згадувань")
    
    print("\nб) Топ твітів за лайками:")
    top_liked = analyzer.get_top_tweets_by_metric(tweets, 'like_count', top_n=3)
    for tweet in top_liked:
        print(f"   - Лайки: {tweet['metrics'].get('like_count', 0)}")
        print(f"     Текст: {tweet['text'][:100]}...")
    
    # Крок 4: Перевірка пошуку в БД
    print("\n4. Перевірка пошуку в базі даних:")
    db_tweets = db.get_tweets_by_query(search_query)
    print(f"   Знайдено {len(db_tweets)} твітів в БД")
    
    if db_tweets:
        print("   Приклад збереженого твіту:")
        sample_tweet = db_tweets[0]
        print(f"   - ID: {sample_tweet['id']}")
        print(f"   - Текст: {sample_tweet['text'][:100]}...")
        print(f"   - Створено: {sample_tweet['created_at']}")

if __name__ == "__main__":
    ensure_data_directory()
    test_full_pipeline()