# schedules.py
from dagster import schedule
from dagster_jobs import abc_news_job

@schedule(cron_schedule="0 * * * *", job=abc_news_job, execution_timezone="UTC")
def abc_news_schedule(_context):
    # Return run config here if needed; an empty dict uses defaults.
    return {}
