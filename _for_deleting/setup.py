# setup.py
from setuptools import setup, find_packages

setup(
    name="twitter_analyzer",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'requests',
        'pandas',
        'streamlit',
        'python-dotenv',
        'nltk'
    ]
)