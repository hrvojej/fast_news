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
    cron_schedule="0 */2 * * *",  # Runs at minute 0 every 2 hours
    job=abc_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def abc_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="7 */2 * * *",  # Runs at minute 7 every 2 hours
    job=aljazeera_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def aljazeera_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="14 */2 * * *",  # Runs at minute 14 every 2 hours
    job=bbc_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def bbc_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="21 */2 * * *",  # Runs at minute 21 every 2 hours
    job=fox_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def fox_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="28 */2 * * *",  # Runs at minute 28 every 2 hours
    job=guardian_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def guardian_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="35 */2 * * *",  # Runs at minute 35 every 2 hours
    job=nyt_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def nyt_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="42 */2 * * *",  # Runs at minute 42 every 2 hours
    job=reuters_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def reuters_news_schedule(_context):
    return {}

@schedule(
    cron_schedule="49 */2 * * *",  # Runs at minute 49 every 2 hours
    job=cnn_news_job,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)
def cnn_news_schedule(_context):
    return {}
