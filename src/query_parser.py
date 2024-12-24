# src/query_parser.py

from dataclasses import dataclass
from typing import List, Dict, Optional
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchQuery:
    """Structure to hold parsed search query components."""
    keywords: List[str]          # basic keywords
    phrases: List[str]           # quoted phrases
    operators: List[str]         # OR, AND
    exclude_terms: List[str]     # terms with minus
    filters: Dict[str, str]      # filters like lang:en
    year: Optional[int]          # year if specified
    
class QueryParser:
    """Parser for Twitter-like search queries."""
    
    def parse(self, query: str) -> SearchQuery:
        """
        Parse complex Twitter-like search query.
        
        Args:
            query: Raw search query string
            
        Returns:
            SearchQuery object with parsed components
        """
        try:
            # Initialize empty query object
            search_query = SearchQuery(
                keywords=[],
                phrases=[],
                operators=[],
                exclude_terms=[],
                filters={},
                year=None
            )
            
            # Clean query
            query = query.strip()
            
            # Handle empty query
            if not query:
                return search_query
                
            # Find quoted phrases first
            phrases = re.findall(r'"([^"]*)"', query)
            search_query.phrases = phrases
            
            # Remove processed phrases from query
            for phrase in phrases:
                query = query.replace(f'"{phrase}"', '')
            
            # Find year
            year_match = re.search(r'\((\d{4})\)', query)
            if year_match:
                search_query.year = int(year_match.group(1))
                query = query.replace(year_match.group(0), '')
            
            # Find filters (pattern: word:value)
            filters = re.findall(r'([a-zA-Z]+):([a-zA-Z]+)', query)
            for filter_name, filter_value in filters:
                search_query.filters[filter_name] = filter_value
                query = query.replace(f'{filter_name}:{filter_value}', '')
            
            # Find exclusions (words with minus)
            exclude_terms = re.findall(r'-(\w+)', query)
            search_query.exclude_terms = exclude_terms
            for term in exclude_terms:
                query = query.replace(f'-{term}', '')
            
            # Process operators and keywords
            query = query.replace(' AND ', ' ')  # Normalize AND
            if 'OR' in query:
                # Handle OR operator
                search_query.operators.append('OR')
                terms = [term.strip() for term in query.split('OR')]
                search_query.keywords = [term for term in terms if term]
            else:
                # If no OR, split into individual words
                search_query.keywords = [
                    word.strip() for word in query.split() 
                    if word.strip() and word.strip() not in ['AND', '(', ')', 'OR']
                ]
            
            # Remove any remaining empty strings
            search_query.keywords = [k for k in search_query.keywords if k]
            
            logger.debug(f"Parsed query: {search_query}")
            return search_query
            
        except Exception as e:
            logger.error(f"Error parsing query: {e}")
            # Return empty query object in case of error
            return SearchQuery([], [], [], [], {}, None)
    
    def generate_search_conditions(self, query: SearchQuery) -> Dict:
        """
        Generate search conditions from parsed query.
        
        Args:
            query: Parsed SearchQuery object
            
        Returns:
            Dictionary with search conditions
        """
        return {
            "must_match_any": query.keywords,    # match any of these words
            "must_match_all": query.phrases,     # match all these phrases
            "must_not_match": query.exclude_terms,  # exclude these words
            "filters": {
                "year": query.year,
                **query.filters
            }
        }

class TweetMatcher:
    """Class for matching tweets against search conditions."""
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        return text.lower().strip()
    
    def matches_conditions(self, tweet: Dict, conditions: Dict) -> bool:
        """
        Check if tweet matches search conditions.
        
        Args:
            tweet: Tweet dictionary
            conditions: Search conditions dictionary
            
        Returns:
            Boolean indicating if tweet matches conditions
        """
        try:
            # Normalize tweet text
            text = self._normalize_text(tweet['text'])
            
            # Check exclusions first
            if any(self._normalize_text(term) in text for term in conditions['must_not_match']):
                return False
            
            # Check required phrases
            if conditions['must_match_all']:
                if not all(self._normalize_text(phrase) in text for phrase in conditions['must_match_all']):
                    return False
            
            # Check keywords (at least one match)
            keywords_match = not conditions['must_match_any'] or \
                             any(self._normalize_text(keyword) in text for keyword in conditions['must_match_any'])
            
            if not keywords_match:
                return False
            
            # Check filters
            filters = conditions['filters']
            
            # Check year filter
            if filters.get('year'):
                tweet_year = int(tweet['created_at'].split('-')[0])
                if tweet_year != filters['year']:
                    return False
            
            # Check language filter
            if filters.get('lang'):
                # Note: Our mock data doesn't have a language field, 
                # so this check would need to be adjusted with real data
                tweet_lang = tweet.get('lang', 'en')  # Default to English
                if tweet_lang != filters['lang']:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error matching tweet: {e}")
            return False