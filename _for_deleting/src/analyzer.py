# src/analyzer.py
from typing import List, Dict, Any
from collections import Counter, defaultdict
import re
from datetime import datetime
import os
import json
import openai
from openai import OpenAI
import logging
from src import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TweetAnalyzer:
    def __init__(self):
        self.stop_words = set([
        'rt', 'the', 'to', 'and', 'is', 'in', 'it', 'you', 'that', 'for',
        'a', 'of', 'or', 'on', 'with', 'by', 'from', 'up', 'about', 'into',
        'over', 'after', 'at', 'as', 'i', 'we', 'our', 'will', 'be', 'all',
        'have', 'has', 'had', 'what', 'when', 'where', 'who', 'which', 'why',
        'can', 'could', 'this', 'these', 'those', 'am', 'are', 'was', 'were'
    ])
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        Analyze the sentiment and emotional tone of the following tweet.
                        Return a JSON with the following structure:
                        {
                            "sentiment": "positive"/"negative"/"neutral",
                            "emotions": ["excited", "worried", "curious", ...],
                            "confidence": 0-100
                        }
                        Focus on nuanced emotional analysis of crypto/tech content.
                        """
                    },
                    {
                        "role": "user", 
                        "content": text
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        
        except Exception as e:
            logger.error(f"Sentiment analysis error for text '{text[:50]}...': {e}")
            return {
                "sentiment": "neutral", 
                "emotions": [], 
                "confidence": 50
            }
        
    def get_trending_insights(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            tweets_text = "\n".join([t['text'] for t in tweets[:10]])
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        You are an expert crypto and tech trend analyst. Perform a deep, nuanced analysis of these tweets.

                        CRITICAL ANALYSIS REQUIREMENTS:
                        1. Extract SUBSTANTIVE, MEANINGFUL trends in cryptocurrency, blockchain, and web3
                        2. IGNORE generic words like 'more', 'today', 'thread', 'announced'
                        3. Focus on SIGNIFICANT technological, economic, or regulatory developments

                        For EACH identified trend, provide:
                        - A PRECISE, DESCRIPTIVE title
                        - CONTEXT explaining the trend's importance
                        - POTENTIAL IMPACT on the crypto/blockchain ecosystem

                        UNACCEPTABLE TRENDS:
                        - Single generic words
                        - Vague statements
                        - Repetitive or non-informative observations

                        JSON FORMAT:
                        {
                            "significant_trends": [
                                {
                                    "title": "Advanced AI Integration in Blockchain Governance",
                                    "context": "Emerging decentralized autonomous organizations using AI for decision-making",
                                    "potential_impact": "High - could revolutionize organizational structures in web3"
                                }
                            ]
                        }
                        """
                    },
                    {
                        "role": "user",
                        "content": tweets_text
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Резервний механізм з більш жорстким фільтруванням
            if not result.get('significant_trends'):
                logger.warning("GPT failed to extract meaningful trends")
                return {
                    "significant_trends": [
                        {
                            "title": "Emerging Crypto Technological Trends",
                            "context": "No specific trends identified. Requires manual review.",
                            "potential_impact": "Undetermined"
                        }
                    ]
                }
            
            return result
        
        except Exception as e:
            logger.error(f"Trending insights error: {e}")
            return {
                "significant_trends": [
                    {
                        "title": "Analysis Error",
                        "context": f"Failed to process trends: {str(e)}",
                        "potential_impact": "Unknown"
                    }
                ]
            }

    def _clean_text(self, text: str) -> str:
        """Очищення тексту твіту"""
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#(\w+)', r'\1', text)
        text = re.sub(r'[^\w\s]', '', text)
        return text.lower()

    def _basic_analysis(self, tweets: List[Dict[Any, Any]]) -> Dict[str, Any]:
        # Знаходимо популярні фрази
        all_text = ' '.join([tweet['text'].lower() for tweet in tweets])
        hashtags = re.findall(r'#(\w+)', all_text)
        topics = Counter(hashtags).most_common(5)
        
        # Знаходимо активні обговорення
        discussions = sorted(
            tweets,
            key=lambda x: (x['metrics']['reply_count'] + x['metrics']['retweet_count']),
            reverse=True
        )[:5]

        # Тренди
        trending = self._analyze_trends_in_time(tweets)[:5]
        
        return {
            'popular_phrases': [{'topic': topic, 'count': count} for topic, count in topics],
            'active_discussions': [{
                'tweet': t['text'],
                'replies': t['metrics']['reply_count'],
                'created_at': t['created_at']
            } for t in discussions],
            'trending_topics': trending
        }
    
    def analyze_text_content(self, tweets: List[Dict[Any, Any]], max_tweets: int = 10) -> Dict[str, Any]:
        try:
            # Беремо задану кількість твітів для GPT аналізу
            sample_tweets = tweets[:max_tweets]
            
            try:
                gpt_analysis = self.get_trending_insights(sample_tweets)
                logger.info(f"GPT Analysis Raw Response: {gpt_analysis}")
            except Exception as e:
                logger.error(f"Error in GPT analysis: {e}")
                gpt_analysis = {}
            
            popular_phrases = gpt_analysis.get('main_topics', 
                [{'topic': topic, 'significance': 'medium'} for topic, count in self.find_trending_topics(tweets, top_n=5)]
            )
            
            trending_topics = self.find_trending_keywords(tweets)[:5]
            
            # Підготовка активних обговорень
            discussions = sorted(
                tweets,
                key=lambda x: (x['metrics']['reply_count'] + x['metrics']['retweet_count']),
                reverse=True
            )[:max_tweets]
            
            return {
                'popular_phrases': popular_phrases,
                'active_discussions': [{
                    'tweet': t['text'],
                    'replies': t['metrics']['reply_count'],
                    'created_at': t['created_at']
                } for t in discussions],
                'trending_topics': trending_topics
            }
        except Exception as e:
            logger.error(f"Comprehensive analysis error: {e}")
            # Fallback до базового аналізу
            return self._basic_analysis(tweets)

    def find_trending_topics(self, tweets: List[Dict[Any, Any]], top_n: int = 10) -> List[tuple]:
        # Додаткові специфічні стоп-слова для криптовалютної тематики
        crypto_stop_words = self.stop_words.union({
            'more', 'today', 'new', 'now', 'like', 'just', 'get', 'one', 
            'blockchain', 'crypto', 'web3', 'nft', 'thread'  # Запобігаємо занадто загальним термінам
        })
        
        # Розширений список релевантних криптовалютних термінів
        crypto_keywords = {
            'bitcoin', 'ethereum', 'defi', 'dao', 'nft', 'metaverse', 
            'smart contract', 'altcoin', 'token', 'mining', 'staking', 
            'governance', 'layer2', 'zk-rollup', 'ai', 'machine learning'
        }
        
        words = []
        for tweet in tweets:
            # Глибше очищення тексту
            text = re.sub(r'https?://\S+|@\w+|[^\w\s]', '', tweet['text'].lower())
            
            # Розбиваємо на слова та біграми
            tweet_words = text.split()
            tweet_bigrams = [' '.join(tweet_words[i:i+2]) for i in range(len(tweet_words)-1)]
            
            # Фільтрація слів
            filtered_words = [
                w for w in (tweet_words + tweet_bigrams) 
                if w not in crypto_stop_words 
                and (w in crypto_keywords or any(keyword in w for keyword in crypto_keywords))
            ]
            
            words.extend(filtered_words)
        
        # Підрахунок та фільтрація
        word_counts = Counter(words)
        
        # Фільтруємо, залишаючи лише релевантні та значущі терміни
        trending_topics = [
            (word, count) for word, count in word_counts.most_common(top_n * 2)
            if count > 1  # Принаймні два входження
        ][:top_n]
        
        return trending_topics
    
    def find_trending_keywords(self, tweets: List[Dict[Any, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        # Розширений список криптовалютних доменних термінів
        crypto_domains = {
            'blockchain': ['decentralization', 'smart contracts', 'consensus', 'distributed ledger'],
            'defi': ['liquidity', 'yield farming', 'staking', 'lending', 'borrowing'],
            'nft': ['digital art', 'collectibles', 'royalties', 'ownership'],
            'ai': ['machine learning', 'prediction', 'analytics', 'automation'],
            'web3': ['decentralized', 'user-owned', 'permissionless', 'trustless']
        }
        
        # Додаткові стоп-слова
        extended_stop_words = self.stop_words.union({
            'more', 'new', 'just', 'now', 'today', 
            'blockchain', 'crypto', 'web3', 'thread'
        })
        
        # Функція для семантичного аналізу ключового слова
        def keyword_semantic_score(word: str) -> float:
            """Оцінка семантичної релевантності ключового слова"""
            domain_scores = {
                domain: sum(1 for term in terms if term in word.lower())
                for domain, terms in crypto_domains.items()
            }
            return sum(domain_scores.values())
        
        # Збір та аналіз слів
        keywords = []
        for tweet in tweets:
            # Очищення тексту
            text = re.sub(r'https?://\S+|@\w+|[^\w\s]', '', tweet['text'].lower())
            
            # Створення слів та біграм
            words = text.split()
            bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
            
            # Фільтрація та оцінка
            filtered_keywords = [
                word for word in (words + bigrams) 
                if (len(word) > 2 and  # Більше 2 символів
                    word not in extended_stop_words and  # Не стоп-слово
                    keyword_semantic_score(word) > 0)  # Має semantic value
            ]
            
            keywords.extend(filtered_keywords)
        
        # Підрахунок та ранжування
        keyword_counts = Counter(keywords)
        trending_keywords = [
            {
                'keyword': word, 
                'count': count,
                'semantic_score': keyword_semantic_score(word),
                'context': next((
                    domain for domain, terms in crypto_domains.items() 
                    if any(term in word.lower() for term in terms)
                ), 'General Crypto')
            } 
            for word, count in keyword_counts.most_common(top_n * 2)
            if count > 1  # Принаймні два входження
        ]
        
        # Сортування за семантичним scores та кількістю
        trending_keywords.sort(
            key=lambda x: (x['semantic_score'], x['count']), 
            reverse=True
        )
        
        return trending_keywords[:top_n]

    def _analyze_trends_in_time(self, tweets: List[Dict[Any, Any]]) -> List[tuple]:
        sorted_tweets = sorted(tweets, key=lambda x: x['created_at'])
        mid = len(sorted_tweets) // 2
        
        early_words = Counter()
        late_words = Counter()
        
        for tweet in sorted_tweets[:mid]:
            words = [w for w in self._clean_text(tweet['text']).split() 
                    if w not in self.stop_words and len(w) > 3]
            early_words.update(words)
            
        for tweet in sorted_tweets[mid:]:
            words = [w for w in self._clean_text(tweet['text']).split() 
                    if w not in self.stop_words and len(w) > 3]
            late_words.update(words)
        
        trending = [(word, late_words[word] - early_words.get(word, 0))
                    for word in late_words
                    if len(word) > 3 and not any(c.isdigit() for c in word)]
                    
        return sorted(
            [t for t in trending if t[1] > 0],
            key=lambda x: x[1],
            reverse=True
        )

    def search_in_tweets(self, tweets: List[Dict[Any, Any]], search_text: str, search_type: str) -> List[Dict[Any, Any]]:
        search_text = search_text.lower()
        results = []
        
        for tweet in tweets:
            tweet_text = tweet['text'].lower()
            
            if search_type == "Точний збіг":
                if f" {search_text} " in f" {tweet_text} ":
                    results.append(tweet)
            
            elif search_type == "Частковий збіг":
                if search_text in tweet_text:
                    results.append(tweet)
            
            elif search_type == "За фразою":
                search_words = search_text.split()
                tweet_words = tweet_text.split()
                for i in range(len(tweet_words) - len(search_words) + 1):
                    if tweet_words[i:i+len(search_words)] == search_words:
                        results.append(tweet)
                        break
        
        return results
    
    def search_by_keyword(self, tweets: List[Dict[Any, Any]], search_query: str) -> List[Dict[Any, Any]]:
        """
        Пошук твітів за ключовим словом з використанням часткового збігу
        """
        return [
            tweet for tweet in tweets 
            if search_query.lower() in tweet['text'].lower()
        ]
    
    def advanced_tweet_analysis(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Комплексний аналіз твітів з sentiment, трендами та додатковими insights
        """
        try:
            # Аналіз sentiment для кожного твіту
            sentiments = []
            for tweet in tweets:
                sentiment_result = self.analyze_sentiment(tweet['text'])
                sentiments.append({
                    'text': tweet['text'],
                    'sentiment': sentiment_result.get('sentiment', 'neutral'),
                    'emotions': sentiment_result.get('emotions', []),
                    'created_at': tweet['created_at'],
                    'author': tweet['author_id']
                })
            
            # Глибший аналіз трендів
            trends_insights = self.get_trending_insights(tweets)
            
            # Статистика sentiment
            sentiment_stats = {
                'positive_count': len([s for s in sentiments if s['sentiment'] == 'positive']),
                'negative_count': len([s for s in sentiments if s['sentiment'] == 'negative']),
                'neutral_count': len([s for s in sentiments if s['sentiment'] == 'neutral']),
                'total_tweets': len(sentiments)
            }
            
            # Топ емоцій
            all_emotions = [emotion for s in sentiments for emotion in s.get('emotions', [])]
            top_emotions = Counter(all_emotions).most_common(5)
            
            return {
                'sentiment_details': sentiments,
                'sentiment_stats': sentiment_stats,
                'top_emotions': top_emotions,
                'trending_insights': trends_insights
            }
        
        except Exception as e:
            logger.error(f"Advanced tweet analysis error: {e}")
            return {
                'sentiment_details': [],
                'sentiment_stats': {},
                'top_emotions': [],
                'trending_insights': {}
            }