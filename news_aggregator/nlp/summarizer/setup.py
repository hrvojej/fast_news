# setup.py
"""
Setup script for the article summarization system.
"""

from setuptools import setup, find_packages

setup(
    name="article-summarizer",
    version="1.0.0",
    description="Article summarization system using Gemini API",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy>=1.4.0",
        "beautifulsoup4>=4.9.0",
        "google-generativeai>=0.3.0",
        "python-dotenv>=0.19.0",
        "requests>=2.25.0"
    ],
    entry_points={
        "console_scripts": [
            "article-summarizer=main:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)