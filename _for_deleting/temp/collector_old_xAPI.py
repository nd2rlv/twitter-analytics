# src/collector.py
import requests
import time
from typing import List, Dict, Any
from src.config import TWITTER_BEARER_TOKEN

class TwitterCollector:
    def __init__(self):
        """Ініціалізація колектора з базовими налаштуваннями"""
        self.base_url = "https://api.twitter.com/2"
        self.headers = {
            "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
            "Content-Type": "application/json"
        }

    def search_tweets(self, query: str, max_results: int = 100) -> List[Dict[Any, Any]]:
        """
        Пошук твітів за заданим запитом
        
        Args:
            query (str): Пошуковий запит
            max_results (int): Максимальна кількість результатів
            
        Returns:
            List[Dict]: Список твітів
        """
        tweets = []
        try:
            endpoint = f"{self.base_url}/tweets/search/recent"
            params = {
                'query': query,
                'max_results': max_results,
                'tweet.fields': 'created_at,public_metrics,author_id'
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()  # Перевіряємо на помилки
            
            data = response.json()
            
            if 'data' in data:
                for tweet in data['data']:
                    tweet_data = {
                        'id': tweet['id'],
                        'text': tweet['text'],
                        'created_at': tweet['created_at'],
                        'author_id': tweet['author_id'],
                        'metrics': tweet.get('public_metrics', {})
                    }
                    tweets.append(tweet_data)
                    
        except requests.exceptions.RequestException as e:
            print(f"Помилка API запиту: {str(e)}")
        except Exception as e:
            print(f"Неочікувана помилка: {str(e)}")
            
        return tweets

    def get_user_tweets(self, user_id: str, max_results: int = 100) -> List[Dict[Any, Any]]:
        """
        Отримання твітів конкретного користувача
        
        Args:
            user_id (str): ID користувача
            max_results (int): Максимальна кількість результатів
            
        Returns:
            List[Dict]: Список твітів
        """
        endpoint = f"{self.base_url}/users/{user_id}/tweets"
        params = {
            'max_results': max_results,
            'tweet.fields': 'created_at,public_metrics'
        }
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            print(f"Помилка при отриманні твітів користувача: {str(e)}")
            return []