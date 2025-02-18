# repository.py
from dagster import repository
from dagster_jobs import (
    abc_news_job,
    aljazeera_news_job,
    bbc_news_job,
    fox_news_job,
    guardian_news_job,
    nyt_news_job,
    reuters_news_job,
    cnn_news_job,
)
from schedules import (
    abc_news_schedule,
    aljazeera_news_schedule,
    bbc_news_schedule,
    fox_news_schedule,
    guardian_news_schedule,
    nyt_news_schedule,
    reuters_news_schedule,
    cnn_news_schedule,
)

@repository
def news_aggregator_repository():
    return [
        abc_news_job,
        aljazeera_news_job,
        bbc_news_job,
        fox_news_job,
        guardian_news_job,
        nyt_news_job,
        reuters_news_job,
        cnn_news_job,
        abc_news_schedule,
        aljazeera_news_schedule,
        bbc_news_schedule,
        fox_news_schedule,
        guardian_news_schedule,
        nyt_news_schedule,
        reuters_news_schedule,
        cnn_news_schedule,
    ]
