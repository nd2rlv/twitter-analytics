# src/collector.py
from ntscraper import Nitter
from typing import List, Dict, Any
from datetime import datetime, timedelta
import time
import json
import random
import functools
import logging
from src.exceptions import NetworkError, RateLimitError, ParsingError
import requests.exceptions

# Налаштування логування
logging.basicConfig(
    filename='twitter_scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TwitterScraper')

def rate_limit(min_delay: int, max_delay: int):
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.info(f"Rate limiting: waiting for {min_delay} to {max_delay} seconds")
            time.sleep(random.uniform(min_delay, max_delay))
            return func(*args, **kwargs)
        return wrapper
    return decorator

def retry_on_error(max_retries: int = 3, delay: int = 5):
    """
    Декоратор для повторних спроб при помилках
    
    Args:
        max_retries: Максимальна кількість спроб
        delay: Затримка між спробами в секундах
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.ConnectionError as e:
                    retries += 1
                    logger.warning(f"Помилка мережі (спроба {retries}/{max_retries}): {str(e)}")
                    if retries == max_retries:
                        raise NetworkError(f"Не вдалося підключитися після {max_retries} спроб")
                    time.sleep(delay * retries)
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        logger.error(f"Перевищено ліміт запитів: {str(e)}")
                        raise RateLimitError("Перевищено ліміт запитів. Спробуйте пізніше.")
                    else:
                        logger.error(f"Неочікувана помилка: {str(e)}")
                        raise
            return None
        return wrapper
    return decorator

class TwitterCollector:
    def __init__(self):
        self.scraper = Nitter()
        self._user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Mozilla/5.0 (X11; Linux x86_64)'
        ]

    @retry_on_error(max_retries=3, delay=5)
    @rate_limit(min_delay=3, max_delay=7)

    def search_tweets(self, query: str, max_results: int = 100) -> List[Dict[Any, Any]]:
        try:
            with open('mock_tweets.json', 'r') as f:
                all_tweets = json.load(f)
            
            # Фільтруємо твіти за пошуковим запитом
            query_terms = query.lower().split()
            matching_tweets = [
                tweet for tweet in all_tweets 
                if any(term in tweet['text'].lower() for term in query_terms)
            ]
            
            return sorted(
                matching_tweets[:max_results],
                key=lambda x: x['created_at'],
                reverse=True
            )
        except Exception as e:
            logger.error(f"Error reading mock tweets: {e}")
            return []

    def _format_tweet(self, tweet):
        return {
            'id': tweet.get('link', '').split('/')[-1],
            'text': tweet.get('text', ''),
            'created_at': tweet.get('date', ''),
            'author_id': tweet.get('user', {}).get('username', ''),
            'metrics': {
                'retweet_count': tweet.get('retweets', 0),
                'reply_count': tweet.get('replies', 0),
                'like_count': tweet.get('likes', 0),
                'quote_count': 0
            }
        }