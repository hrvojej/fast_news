from dagster import schedule, DefaultScheduleStatus
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

@schedule(
    cron_schedule="0 * * * *",
    job=abc_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def abc_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="7 * * * *",
    job=aljazeera_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def aljazeera_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="14 * * * *",
    job=bbc_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def bbc_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="21 * * * *",
    job=fox_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def fox_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="28 * * * *",
    job=guardian_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def guardian_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="35 * * * *",
    job=nyt_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def nyt_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="42 * * * *",
    job=reuters_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def reuters_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="49 * * * *",
    job=cnn_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def cnn_news_schedule(_context):
    return {}
