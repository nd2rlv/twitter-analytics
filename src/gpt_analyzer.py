# src/gpt_analyzer.py

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from config import (
    async_client,
    GPT_MODEL, 
    MAX_TOKENS, 
    TEMPERATURE,
    MAX_TWEETS_FOR_GPT,
    MIN_RELEVANCE_SCORE
)
from search_prompts import (
    SYSTEM_ANALYSIS_PROMPT,
    SEMANTIC_SEARCH_PROMPT,
    SENTIMENT_ANALYSIS_PROMPT
)
from query_parser import QueryParser, TweetMatcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPTAnalyzer:
    def __init__(self):
        """Initialize GPT analyzer components."""
        self.query_parser = QueryParser()
        self.tweet_matcher = TweetMatcher()

    async def _gpt_request(self, 
                        prompt: str, 
                        content: str, 
                        temp: Optional[float] = None) -> Dict:
        try:
            response = await async_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content}
                ],
                temperature=temp if temp is not None else TEMPERATURE,
                max_tokens=MAX_TOKENS
            )
            
            # Логуємо повний Raw Response
            raw_content = response.choices[0].message.content
            logger.info(f"Raw GPT response: {raw_content}")
            
            # Видаляємо markdown-синтаксис
            clean_content = re.sub(r'^```json\n|```$', '', raw_content.strip(), flags=re.MULTILINE)
            
            try:
                # Пробуємо розпарсити напряму
                parsed_json = json.loads(clean_content)
                
                # НОВИЙ БЛОК: Додаткова перевірка sentiment_distribution
                if 'sentiment' in parsed_json and 'sentiment_distribution' not in parsed_json:
                    # Якщо немає distribution, але є key_sentiments
                    sentiments = parsed_json.get('key_sentiments', [])
                    distribution = {
                        'positive': sum(1 for s in sentiments if s.get('sentiment') == 'positive'),
                        'negative': sum(1 for s in sentiments if s.get('sentiment') == 'negative'),
                        'neutral': sum(1 for s in sentiments if s.get('sentiment') == 'neutral')
                    }
                    parsed_json['sentiment_distribution'] = distribution
                
                return parsed_json
            
            except json.JSONDecodeError:
                # Решта коду без змін
                pass
        
        except Exception as e:
            logger.error(f"Помилка GPT API: {e}")
            return {
                "matches": [],
                "search_metadata": {
                    "error": str(e)
                }
            }

    def _clean_json_content(self, content: str) -> str:
        """
        Clean and prepare JSON content for parsing.
        
        Args:
            content: Raw JSON-like content
        
        Returns:
            Cleaned JSON string
        """
        try:
            # Close unclosed strings
            content = re.sub(r'(?<!\\)"(?=\s*[}\],]|$)', '\\"', content)
            
            # Remove incomplete or problematic lines
            lines = [
                line.strip() for line in content.split('\n') 
                if line.strip() 
                and not line.strip().startswith('"tweet_text":')
                and not line.strip().startswith('"relevance_explanation":')
            ]
            
            # Rejoin cleaned lines
            cleaned_content = '\n'.join(lines)
            
            return cleaned_content
        except Exception as e:
            logger.error(f"JSON cleaning error: {e}")
            return content

    def _extract_json(self, content: str) -> str:
        """
        Extract JSON-like structure using regex.
        
        Args:
            content: Raw content potentially containing JSON
        
        Returns:
            Extracted JSON string
        """
        try:
            # Look for JSON structure with matches array
            json_match = re.search(r'\{.*?"matches":\s*\[.*?\].*?\}', content, re.DOTALL)
            
            if json_match:
                return json_match.group(0)
            
            # Fallback to first JSON-like object
            json_match = re.search(r'\{.*?\}', content, re.DOTALL)
            
            if json_match:
                return json_match.group(0)
            
            raise ValueError("No JSON-like structure found")
        
        except Exception as e:
            logger.error(f"JSON extraction error: {e}")
            raise

    def _basic_search(self, tweets: List[Dict], query: str) -> List[Dict]:
        """
        Perform initial filtering of tweets using QueryParser and TweetMatcher.
        
        Args:
            tweets: List of tweets to search
            query: Raw search query string
            
        Returns:
            List of potentially relevant tweets
        """
        try:
            # Parse the query
            parsed_query = self.query_parser.parse(query)
            conditions = self.query_parser.generate_search_conditions(parsed_query)
            
            # Find matching tweets
            matching_tweets = [
                tweet for tweet in tweets 
                if self.tweet_matcher.matches_conditions(tweet, conditions)
            ]
            
            # Sort by basic relevance and limit number of tweets
            for tweet in matching_tweets:
                text = tweet['text'].lower()
                matches = sum(1 for keyword in conditions['must_match_any'] 
                            if keyword.lower() in text)
                tweet['initial_relevance'] = matches
            
            matching_tweets.sort(key=lambda x: x['initial_relevance'], reverse=True)
            return matching_tweets[:MAX_TWEETS_FOR_GPT]
            
        except Exception as e:
            logger.error(f"Basic search error: {e}")
            return []

    async def search_tweets(self, 
                          tweets: List[Dict], 
                          query: str,
                          filters: Dict = None) -> Dict[str, Any]:
        """
        Search tweets using combination of basic filtering and GPT analysis.
        """
        try:
            # First, apply basic filtering
            filtered_tweets = self._basic_search(tweets, query)
            logger.info(f"Found {len(filtered_tweets)} tweets in basic search")
            
            if not filtered_tweets:
                return {
                    "matches": [],
                    "search_metadata": {
                        "total_tweets": 0,
                        "query": query,
                        "message": "No tweets found matching your criteria"
                    }
                }
            
            # Prepare context for GPT
            search_context = {
                "query": query,
                "tweets": filtered_tweets,
                "filters": filters
            }
            
            # Use GPT for semantic analysis
            gpt_results = await self._gpt_request(
                prompt=SEMANTIC_SEARCH_PROMPT,
                content=json.dumps(search_context),
                temp=0.3  # Lower temperature for more focused search
            )
            logger.info(f"GPT results: {json.dumps(gpt_results, indent=2)}")
            
            # Ensure matches array exists
            if 'matches' not in gpt_results:
                gpt_results['matches'] = []
            
            # Map GPT results back to original tweets
            enhanced_matches = []
            for match in gpt_results.get('matches', []):
                for original_tweet in filtered_tweets:
                    if original_tweet['text'] == match.get('tweet_text', ''):
                        enhanced_match = {
                            **original_tweet,
                            'relevance_score': match.get('relevance_score', 0),
                            'relevance_explanation': match.get('relevance_explanation', ''),
                            'matched_concepts': match.get('matched_concepts', [])
                        }
                        enhanced_matches.append(enhanced_match)
                        break
            
            gpt_results['matches'] = enhanced_matches
            
            # Filter results by minimum relevance score
            gpt_results['matches'] = [
                match for match in gpt_results['matches']
                if match.get('relevance_score', 0) >= MIN_RELEVANCE_SCORE
            ]
            
            # Add metadata
            gpt_results['search_metadata'] = {
                "total_tweets": len(filtered_tweets),
                "processed_tweets": len(gpt_results['matches']),
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "filters_applied": bool(filters)
            }
            
            return gpt_results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "error": str(e),
                "matches": [],
                "search_metadata": {
                    "error": True,
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            }

    async def analyze_content(self, tweets: List[Dict]) -> Dict[str, Any]:
        try:
            # Додаємо логування початку аналізу
            logger.info(f"Starting content analysis for {len(tweets)} tweets")

            # Додаємо інформацію про автора до кожного твіту перед аналізом
            enhanced_tweets = [
                {**tweet, 'author': tweet.get('author_id', 'Unknown')} 
                for tweet in tweets
            ]
            
            content_analysis = await self._gpt_request(
                prompt=SYSTEM_ANALYSIS_PROMPT,
                content=json.dumps(enhanced_tweets)
            )
            
            # Додаткова перевірка та виправлення
            if 'key_discussions' in content_analysis:
                for discussion in content_analysis['key_discussions']:
                    if 'author' not in discussion:
                        # Намагаємось витягти автора з оригінального твіту
                        matching_tweet = next(
                            (tweet for tweet in tweets if tweet['text'] == discussion.get('tweet_text')), 
                            None
                        )
                        discussion['author'] = matching_tweet.get('author_id', 'Unknown') if matching_tweet else 'Unknown'
            
            # Додаємо метадані
            content_analysis['metadata'] = {
                "analyzed_tweets": len(tweets),
                "timestamp": datetime.now().isoformat()
            }

            # Логування завершення аналізу
            logger.info(f"Content analysis complete. Topics found: {len(content_analysis.get('topics', []))}")
            
            return content_analysis
            
        except Exception as e:
            logger.error(f"Content analysis error: {e}")
            return {
                "error": str(e),
                "topics": [],
                "key_discussions": [],
                "trends": {"rising": [], "keywords": []},
                "metadata": {
                    "error": True,
                    "timestamp": datetime.now().isoformat()
                }
            }

    async def analyze_sentiment(self, tweets: List[Dict]) -> Dict[str, Any]:
        try:
            # Додаємо логування початку аналізу sentiment
            logger.info(f"Starting sentiment analysis for {len(tweets)} tweets")

            sentiment_analysis = await self._gpt_request(
                prompt=SENTIMENT_ANALYSIS_PROMPT,
                content=json.dumps(tweets)
            )
            
            # ВАЖЛИВО: явно додаємо sentiment_distribution, якщо її немає
            if 'sentiment_distribution' not in sentiment_analysis:
                key_sentiments = sentiment_analysis.get('key_sentiments', [])
                sentiment_analysis['sentiment_distribution'] = {
                    'positive': sum(1 for s in key_sentiments if s.get('sentiment') == 'positive'),
                    'negative': sum(1 for s in key_sentiments if s.get('sentiment') == 'negative'),
                    'neutral': sum(1 for s in key_sentiments if s.get('sentiment') == 'neutral')
                }
            
            # Додаємо метадані
            sentiment_analysis['metadata'] = {
                "analyzed_tweets": len(tweets),
                "timestamp": datetime.now().isoformat()
            }

            # Логування завершення аналізу
            logger.info(f"Sentiment analysis complete. Sentiment score: {sentiment_analysis.get('overall_sentiment', {}).get('score', 'N/A')}")
            
            return sentiment_analysis
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {
                "error": str(e),
                "overall_sentiment": {"score": 0, "summary": "", "confidence": 0},
                "key_sentiments": [],
                "sentiment_distribution": {
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0
                },
                "emotional_patterns": {"primary_emotions": [], "notable_shifts": []},
                "metadata": {
                    "error": True,
                    "timestamp": datetime.now().isoformat()
                }
            }