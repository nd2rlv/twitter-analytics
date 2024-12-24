# src/gpt_analyzer.py
import openai
from typing import List, Dict, Any
import logging

logger = logging.getLogger('GPTAnalyzer')

class GPTAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "Analyze the sentiment and key topics of the following tweet. Return JSON with sentiment (positive/negative/neutral) and main topics."
                }, {
                    "role": "user",
                    "content": text
                }]
            )
            return response.choices[0].message['content']
        except Exception as e:
            logger.error(f"GPT API error: {str(e)}")
            return {"sentiment": "neutral", "topics": []}

    def get_trending_insights(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            tweets_text = "\n".join([t['text'] for t in tweets[:5]])
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "Analyze these tweets and identify main trends, discussions and user interests. Return JSON."
                }, {
                    "role": "user",
                    "content": tweets_text
                }]
            )
            return response.choices[0].message['content']
        except Exception as e:
            logger.error(f"GPT API error: {str(e)}")
            return {"trends": [], "insights": []}