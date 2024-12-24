# src/app.py

import streamlit as st
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
from config import TWEETS_FILE
from gpt_analyzer import GPTAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TweetData:
    """Class to manage tweet data loading and basic operations."""
    
    def __init__(self, file_path: str):
        """Initialize with tweets data file."""
        self.tweets = self._load_tweets(file_path)
        self.authors = self._get_unique_authors()
        
    def _load_tweets(self, file_path: str) -> List[Dict]:
        """Load tweets from JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tweets: {e}")
            return []
            
    def _get_unique_authors(self) -> List[str]:
        """Get list of unique authors from tweets."""
        return sorted(list(set(tweet['author_id'] for tweet in self.tweets)))

    def get_author_tweets(self, author_id: str) -> List[Dict]:
        """Get all tweets from specific author."""
        return [tweet for tweet in self.tweets if tweet['author_id'] == author_id]

    def get_tweet_statistics(self, tweets: List[Dict]) -> Dict:
        """Calculate statistics for given tweets."""
        if not tweets:
            return {
                "total_tweets": 0,
                "total_engagement": 0,
                "avg_engagement": 0,
                "top_tweets": []
            }
            
        return {
            "total_tweets": len(tweets),
            "total_engagement": sum(
                tweet['metrics']['retweet_count'] + 
                tweet['metrics']['reply_count'] + 
                tweet['metrics']['like_count']
                for tweet in tweets
            ),
            "avg_engagement": sum(
                tweet['metrics']['retweet_count'] + 
                tweet['metrics']['reply_count'] + 
                tweet['metrics']['like_count']
                for tweet in tweets
            ) / len(tweets),
            "top_tweets": sorted(
                tweets,
                key=lambda x: (
                    x['metrics']['retweet_count'] + 
                    x['metrics']['reply_count'] + 
                    x['metrics']['like_count']
                ),
                reverse=True
            )[:5]
        }

def create_search_interface():
    """Create and return search interface elements."""
    st.markdown("### Search Tweets")
    
    # Main search input
    search_query = st.text_input(
        "Enter your search query:",
        placeholder="e.g., blockchain OR crypto OR 'Web3 development' -scam lang:en"
    )
    
    # Advanced search options
    with st.expander("Advanced Search Options"):
        col1, col2 = st.columns(2)
        
        with col1:
            date_from = st.date_input("From date", None)
            min_engagement = st.number_input(
                "Minimum engagement", 
                min_value=0, 
                value=0
            )
            
        with col2:
            date_to = st.date_input("To date", None)
            author = st.text_input("Author")
    
    # Create filters dictionary
    filters = {}
    if date_from:
        filters['date_from'] = date_from.strftime('%Y-%m-%d')
    if date_to:
        filters['date_to'] = date_to.strftime('%Y-%m-%d')
    if min_engagement > 0:
        filters['min_engagement'] = min_engagement
    if author:
        filters['author'] = author
        
    return search_query, filters

def show_search_results(matches: List[Dict]):
    """Display search results."""
    st.markdown(f"### Found {len(matches)} matching tweets")
    
    for match in matches:
        with st.container():
            st.markdown(f"**@{match['author_id']}**")
            st.markdown(match['text'])
            
            # Show relevance and explanation if available
            if 'relevance_score' in match:
                st.markdown(f"*Relevance Score:* {match['relevance_score']:.2f}")
            if 'relevance_explanation' in match:
                st.markdown(f"*Why relevant:* {match['relevance_explanation']}")
            
            # Show metrics
            st.markdown(f"""
                *Posted on: {match['created_at']}* | 
                💬 {match['metrics']['reply_count']} | 
                🔄 {match['metrics']['retweet_count']} | 
                ❤️ {match['metrics']['like_count']}
            """)
            st.markdown("---")

def show_content_analysis(analysis: Dict):
    col1, col2 = st.columns(2)
    
    with col1:
        # Popular Topics
        st.markdown("### Popular Topics")
        if analysis.get("topics"):
            topics_df = pd.DataFrame(analysis["topics"][:5])
            st.dataframe(topics_df[["name", "count", "importance"]])
        
        # Keywords
        st.markdown("### Top Keywords")
        if analysis.get("trends", {}).get("keywords"):
            st.markdown(", ".join(analysis["trends"]["keywords"][:5]))
        
        # Sentiment Overview
        st.markdown("### Sentiment Overview")
        if analysis.get("sentiment"):
            sentiment = analysis["sentiment"]["overall_sentiment"]
            st.markdown(f"**Score:** {sentiment['score']:.2f}")
            st.markdown(f"**Summary:** {sentiment['summary']}")
        
        # Sentiment Breakdown
        st.markdown("### Sentiment Breakdown")
        sentiment_stats = analysis.get("sentiment", {}).get('sentiment_distribution', {
            'positive': 0,
            'negative': 0,
            'neutral': 0
        })
        
        col_sent1, col_sent2, col_sent3 = st.columns(3)
        
        with col_sent1:
            st.metric("Positive Tweets", sentiment_stats.get('positive', 0))
        
        with col_sent2:
            st.metric("Negative Tweets", sentiment_stats.get('negative', 0))
        
        with col_sent3:
            st.metric("Neutral Tweets", sentiment_stats.get('neutral', 0))
    
    with col2:
        # Key Discussions
        st.markdown("### Active Discussions")
        if analysis.get("key_discussions"):
            for discussion in analysis["key_discussions"][:5]:
                # Перевірка автора з кількома fallback-варіантами
                author = (
                    discussion.get('author') or 
                    discussion.get('author_id') or 
                    'Unknown'
                )
                st.markdown(f"**Author:** @{author}")
                st.markdown(f"**Tweet:** {discussion['tweet_text']}")
                st.markdown(f"*Importance:* {discussion['importance']}/10")
                st.markdown("---")

def show_statistics(tweet_data: TweetData, tweets: List[Dict]):
    with st.sidebar:
        st.header("Author Statistics Filters")
        
        # Вибір автора з наявних у результатах пошуку
        selected_author = st.selectbox(
            "Select Author",
            options=tweet_data.authors,
            format_func=lambda x: f"@{x}"
        )
        
        # Фільтр по даті
        date_range = st.date_input(
            "Filter date range", 
            value=None,
            help="Select start and end date for tweets"
        )
        
        # Мінімальний поріг залученості
        min_engagement = st.number_input(
            "Minimum total engagement", 
            min_value=0, 
            value=0,
            help="Filter tweets with engagement above this threshold"
        )
        
        # Варіанти сортування
        sort_options = {
            "Total Engagement": lambda t: (t['metrics']['retweet_count'] + 
                                           t['metrics']['reply_count'] + 
                                           t['metrics']['like_count']),
            "Retweets": lambda t: t['metrics']['retweet_count'],
            "Likes": lambda t: t['metrics']['like_count'],
            "Replies": lambda t: t['metrics']['reply_count']
        }
        
        # Вибір сортування
        sort_by = st.selectbox(
            "Sort tweets by", 
            options=list(sort_options.keys())
        )
        
        # Кнопка застосування фільтрів
        apply_filters = st.button("Apply Filters")
    
    # Перевірка, чи обрано автора
    if not selected_author:
        st.warning("Please select an author to view statistics")
        return
    
    # Фільтрація твітів
    if apply_filters or selected_author:
        # Фільтр по автору
        author_tweets = [t for t in tweets if t['author_id'] == selected_author]
        
        # Фільтр по даті
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            author_tweets = [
                t for t in author_tweets 
                if start_date <= datetime.strptime(t['created_at'], '%Y-%m-%dT%H:%M:%S').date() <= end_date
            ]
        
        # Фільтр по залученості
        author_tweets = [
            t for t in author_tweets
            if (t['metrics']['retweet_count'] + 
                t['metrics']['reply_count'] + 
                t['metrics']['like_count']) >= min_engagement
        ]
        
        # Сортування
        author_tweets = sorted(
            author_tweets, 
            key=sort_options[sort_by], 
            reverse=True
        )
        
        # Розрахунок статистики
        stats = tweet_data.get_tweet_statistics(author_tweets)
        
        # Виведення статистики
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Author Metrics")
            st.markdown(f"**Total Tweets:** {stats['total_tweets']}")
            st.markdown(f"**Total Engagement:** {stats['total_engagement']}")
            st.markdown(f"**Average Engagement:** {stats['avg_engagement']:.2f}")
        
        with col2:
            st.markdown("### Top Tweets")
            for tweet in stats['top_tweets']:
                total_engagement = (
                    tweet['metrics']['retweet_count'] +
                    tweet['metrics']['reply_count'] +
                    tweet['metrics']['like_count']
                )
                st.markdown(f"**Tweet:** {tweet['text']}")
                st.markdown(f"*Total Engagement:* {total_engagement}")
                st.markdown("---")
        
        # Додаткова перевірка, якщо немає твітів після фільтрації
        if not author_tweets:
            st.info("No tweets found matching the selected filters")

async def main():
    st.set_page_config(page_title="Twitter Analysis Tool", layout="wide")
    st.title("Twitter Analysis Tool")
    
    # Initialize components
    tweet_data = TweetData(TWEETS_FILE)
    analyzer = GPTAnalyzer()
    
    # Search interface
    search_query, filters = create_search_interface()
    
    if search_query:
        # Створюємо порожній контейнер для статусу
        status_container = st.empty()
        
        # Створюємо прогрес-бар одразу
        progress_bar = st.progress(0)

        try:
            # Пошук твітів з прогресом відразу
            with st.spinner(f'Searching tweets...'):
                progress_bar.progress(10)  # Прогрес одразу після старту
                search_results = await analyzer.search_tweets(
                    tweet_data.tweets, 
                    search_query, 
                    filters
                )
            
            if search_results.get("error"):
                st.error(f"Search error: {search_results['error']}")
                progress_bar.empty()
                return
            
            matched_tweets = search_results.get("matches", [])
            
            if not matched_tweets:
                st.warning("No tweets found matching your criteria.")
                progress_bar.empty()
                return
            
            # Оновлюємо spinner з інформацією про кількість знайдених твітів
            with st.spinner(f'Searching tweets... Found {len(matched_tweets)} tweets. Analyzing content...'):
                progress_bar.progress(30)  # Повертаємо попередній рівень прогресу

            # Аналіз контенту
            with st.spinner('Performing content analysis...'):
                progress_bar.progress(50)
                content_analysis = await analyzer.analyze_content(matched_tweets)
                
                progress_bar.progress(70)
                sentiment_analysis = await analyzer.analyze_sentiment(matched_tweets)
                
                progress_bar.progress(90)
            
            # Очищаємо статус-контейнер
            status_container.empty()
            
            # Завершуємо прогрес-бар
            progress_bar.progress(100)
            
            # Combine analyses
            full_analysis = {
                "topics": content_analysis.get('topics', []),
                "key_discussions": content_analysis.get('key_discussions', []),
                "trends": content_analysis.get('trends', {}),
                "sentiment": {
                    **sentiment_analysis,
                    "sentiment_distribution": sentiment_analysis.get('sentiment_distribution', {
                        'positive': 0,
                        'negative': 0,
                        'neutral': 0
                    })
                }
            }
            
            # Display results in tabs
            tab1, tab2, tab3 = st.tabs(
                ["Search Results", "Content Analysis", "Statistics"]
            )
            
            with tab1:
                show_search_results(matched_tweets)
                
            with tab2:
                show_content_analysis(full_analysis)
                
            with tab3:
                matched_authors = list(set(tweet['author_id'] for tweet in matched_tweets))
                tweet_data = TweetData(TWEETS_FILE)
                tweet_data.authors = matched_authors
                show_statistics(tweet_data, matched_tweets)
            
            # Видаляємо прогрес-бар після завершення
            progress_bar.empty()
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            status_container.error("An error occurred during analysis. Please try again.")
            progress_bar.empty()

if __name__ == "__main__":
    asyncio.run(main())