# test_analyzer.py
from src.collector import TwitterCollector
from src.analyzer import TweetAnalyzer

def test_analysis():
    # Збираємо твіти
    collector = TwitterCollector()
    tweets = collector.search_tweets("python programming", max_results=100)
    
    # Створюємо аналізатор
    analyzer = TweetAnalyzer()
    
    # Тестуємо різні функції аналізу
    print("\nПопулярні теми:")
    trending_topics = analyzer.find_trending_topics(tweets, top_n=5)
    for topic, count in trending_topics:
        print(f"- {topic}: {count} згадувань")
    
    print("\nТоп твіти за лайками:")
    top_liked = analyzer.get_top_tweets_by_metric(tweets, 'like_count', top_n=3)
    for tweet in top_liked:
        print(f"- Лайки: {tweet['metrics']['like_count']}")
        print(f"  Текст: {tweet['text'][:100]}...")
    
    print("\nТвіти зі словом 'learn':")
    learn_tweets = analyzer.search_by_keyword(tweets, 'learn')
    for tweet in learn_tweets[:3]:  # Показуємо перші 3
        print(f"- {tweet['text'][:100]}...")

if __name__ == "__main__":
    test_analysis()