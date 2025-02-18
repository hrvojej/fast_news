# repository.py
from dagster import repository
from dagster_jobs import abc_news_job
from schedules import abc_news_schedule
# Import additional jobs and schedules as needed.

@repository
def news_aggregator_repository():
    return [
        abc_news_job,
        abc_news_schedule,
        # Add other jobs and schedule definitions here.
    ]
