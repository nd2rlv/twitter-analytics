# src/database.py
import sqlite3
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('TwitterDatabase')

class TweetDatabase:
    def __init__(self, db_path: str = "data/tweets.db"):
        """Ініціалізація бази даних"""
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        """Створення необхідних таблиць"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Оновлюємо таблицю твітів, додаємо cached_until
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tweets (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    retweet_count INTEGER DEFAULT 0,
                    reply_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    quote_count INTEGER DEFAULT 0,
                    collected_at TEXT NOT NULL,
                    cached_until TEXT NOT NULL
                )
            ''')
            
            # Таблиця для пошукових запитів з кешуванням
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS searches (
                    query TEXT NOT NULL,
                    tweet_id TEXT NOT NULL,
                    searched_at TEXT NOT NULL,
                    cached_until TEXT NOT NULL,
                    FOREIGN KEY(tweet_id) REFERENCES tweets(id),
                    PRIMARY KEY(query, tweet_id)
                )
            ''')
            
            conn.commit()

    def save_tweets(self, tweets: List[Dict[Any, Any]], search_query: str = None):
        """Збереження твітів з кешуванням"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            collected_at = datetime.utcnow().isoformat()
            # Кешуємо на 1 годину
            cached_until = (datetime.utcnow() + timedelta(hours=1)).isoformat()
            
            for tweet in tweets:
                cursor.execute('''
                    INSERT OR REPLACE INTO tweets (
                        id, text, created_at, author_id,
                        retweet_count, reply_count, like_count, quote_count,
                        collected_at, cached_until
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tweet['id'],
                    tweet['text'],
                    tweet['created_at'],
                    tweet['author_id'],
                    tweet['metrics'].get('retweet_count', 0),
                    tweet['metrics'].get('reply_count', 0),
                    tweet['metrics'].get('like_count', 0),
                    tweet['metrics'].get('quote_count', 0),
                    collected_at,
                    cached_until
                ))
                
                if search_query:
                    cursor.execute('''
                        INSERT OR REPLACE INTO searches (
                            query, tweet_id, searched_at, cached_until
                        ) VALUES (?, ?, ?, ?)
                    ''', (search_query, tweet['id'], collected_at, cached_until))
            
            conn.commit()
            logger.info(f"Збережено {len(tweets)} твітів з кешуванням до {cached_until}")

    def get_tweets_by_query(self, query: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            current_time = datetime.utcnow().isoformat()
            cursor.execute('''
                SELECT t.*, s.searched_at, s.cached_until 
                FROM tweets t
                JOIN searches s ON t.id = s.tweet_id
                WHERE s.query = ? AND s.cached_until > ?
                ORDER BY t.created_at DESC
            ''', (query, current_time))
            
            rows = cursor.fetchall()
            
            if not rows:
                return {
                    'tweets': [],
                    'source': None,
                    'last_updated': None,
                    'cached_until': None
                }
            
            tweets = []
            for row in rows:
                tweet_dict = dict(row)
                tweet_dict['metrics'] = {
                    'retweet_count': tweet_dict.pop('retweet_count', 0),
                    'reply_count': tweet_dict.pop('reply_count', 0),
                    'like_count': tweet_dict.pop('like_count', 0),
                    'quote_count': tweet_dict.pop('quote_count', 0)
                }
                tweets.append(tweet_dict)

            return {
                'tweets': tweets,
                'source': 'cache',
                'last_updated': tweets[0]['collected_at'] if tweets else None,
                'cached_until': tweets[0]['cached_until'] if tweets else None
            }

    def is_cache_valid(self, query: str) -> bool:
        """Перевірка валідності кешу"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            current_time = datetime.utcnow().isoformat()
            
            cursor.execute('''
                SELECT COUNT(*) FROM searches 
                WHERE query = ? AND cached_until > ?
            ''', (query, current_time))
            
            count = cursor.fetchone()[0]
            return count > 0
        
    def get_all_queries(self) -> List[str]:
        """Отримання всіх унікальних пошукових запитів"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT query 
                FROM searches 
                ORDER BY searched_at DESC
            ''')
            return [row[0] for row in cursor.fetchall()]