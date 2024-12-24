# src/config.py

import os
from openai import AsyncClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GPT_MODEL = "gpt-4o"

# Create async client
async_client = AsyncClient(api_key=OPENAI_API_KEY)

# API request parameters
MAX_TOKENS = 4000  # Збільшено для більшої кількості твітів
TEMPERATURE = 0.3  # Зменшено для більш точних результатів

# Search configuration
MAX_TWEETS_FOR_GPT = 25  # Максимальна кількість твітів для аналізу
MIN_RELEVANCE_SCORE = 0.3  # Мінімальний бал релевантності для результатів

# File paths
TWEETS_FILE = 'data/mock_tweets.json'