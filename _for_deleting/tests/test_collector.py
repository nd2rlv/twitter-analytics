# test_collector.py
from src.collector import TwitterCollector
import json

def test_search():
    collector = TwitterCollector()
    tweets = collector.search_tweets("python", max_results=10)
    
    print(f"Знайдено {len(tweets)} твітів")
    
    # Красиво виводимо перші 3 твіти
    for tweet in tweets[:3]:
        print("\nТвіт:")
        print(json.dumps(tweet, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_search()