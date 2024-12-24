# Twitter Analytics Tool

AI-powered tool for analyzing Twitter content, detecting trends, and generating insights using GPT models.

## Features

🔍 **Search**
- Complex query parsing with AND/OR operators
- Semantic search with GPT
- Filters by date, metrics, authors

📊 **Analytics**
- Topic detection
- Sentiment analysis
- Engagement metrics

📈 **Visualization**
- Interactive dashboards
- Trend analysis
- Author statistics

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/twitter-analytics.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your OpenAI API key to .env
```

## Usage

Launch the application:
```bash
streamlit run src/app.py
```

## Tech Stack

- Python 3.8+
- OpenAI GPT
- Streamlit
- Pandas
- AsyncIO
- python-dotenv
- JSON

## Project Structure

```
├── src/
│   ├── __init__.py       # Package initialization
│   ├── app.py            # Streamlit UI
│   ├── config.py         # Configuration settings
│   ├── gpt_analyzer.py   # GPT integration
│   ├── query_parser.py   # Search logic
│   └── search_prompts.py # GPT prompts
├── data/
│   └── mock_tweets.json  # Sample data
├── .env                  # OpenAI API key
├── .gitignore           # Git ignore rules
├── README.md            # Project documentation
└── requirements.txt     # Dependencies
```