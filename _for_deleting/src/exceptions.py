# src/exceptions.py
class TwitterScraperError(Exception):
    """Базовий клас для помилок скрапера"""
    pass

class NetworkError(TwitterScraperError):
    """Помилки мережі"""
    pass

class RateLimitError(TwitterScraperError):
    """Перевищення ліміту запитів"""
    pass

class ParsingError(TwitterScraperError):
    """Помилки парсингу даних"""
    pass