from setuptools import setup, find_packages

setup(
    name="news_aggregator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'sqlalchemy>=1.4.0',
        'psycopg2-binary>=2.9.0',
        'requests>=2.25.0',
        'beautifulsoup4>=4.9.0',
    ],
    python_requires='>=3.8',
)