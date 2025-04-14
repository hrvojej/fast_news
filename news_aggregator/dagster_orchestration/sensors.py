from dagster import RunRequest, sensor, RunsFilter, DagsterRunStatus
from datetime import datetime, timedelta, timezone
from sync_jobs import (
   sync_pt_abc_articles,
   sync_pt_aljazeera_articles, 
   sync_pt_bbc_articles,
   sync_pt_fox_articles,
   sync_pt_guardian_articles,
   sync_pt_nyt_articles, 
   sync_pt_reuters_articles,
   sync_pt_cnn_articles
)

@sensor(job=sync_pt_abc_articles)
def abc_sync_sensor(context):
   """Sensor that triggers sync_pt_abc_articles when abc_news_job completes successfully"""
   runs = context.instance.get_runs(
       filters=RunsFilter(job_name="abc_news_job"),
       limit=1
   )
   last_run = runs[0] if runs else None

   if last_run and last_run.status == DagsterRunStatus.SUCCESS:
       cursor = context.cursor or ""
       if last_run.run_id != cursor:
           context.update_cursor(last_run.run_id)
           yield RunRequest(run_key=f"sync_after_{last_run.run_id}")

@sensor(job=sync_pt_bbc_articles)
def bbc_sync_sensor(context):
   """Sensor that triggers sync_pt_bbc_articles when bbc_news_job completes successfully"""
   runs = context.instance.get_runs(
       filters=RunsFilter(job_name="bbc_news_job"),
       limit=1
   )
   last_run = runs[0] if runs else None

   if last_run and last_run.status == DagsterRunStatus.SUCCESS:
       cursor = context.cursor or ""
       if last_run.run_id != cursor:
           context.update_cursor(last_run.run_id)
           yield RunRequest(run_key=f"sync_after_{last_run.run_id}")

@sensor(job=sync_pt_cnn_articles)
def cnn_sync_sensor(context):
   """Sensor that triggers sync_pt_cnn_articles when cnn_news_job completes successfully"""
   runs = context.instance.get_runs(
       filters=RunsFilter(job_name="cnn_news_job"),
       limit=1
   )
   last_run = runs[0] if runs else None

   if last_run and last_run.status == DagsterRunStatus.SUCCESS:
       cursor = context.cursor or ""
       if last_run.run_id != cursor:
           context.update_cursor(last_run.run_id)
           yield RunRequest(run_key=f"sync_after_{last_run.run_id}")

@sensor(job=sync_pt_fox_articles)
def fox_sync_sensor(context):
   """Sensor that triggers sync_pt_fox_articles when fox_news_job completes successfully"""
   runs = context.instance.get_runs(
       filters=RunsFilter(job_name="fox_news_job"),
       limit=1
   )
   last_run = runs[0] if runs else None

   if last_run and last_run.status == DagsterRunStatus.SUCCESS:
       cursor = context.cursor or ""
       if last_run.run_id != cursor:
           context.update_cursor(last_run.run_id)
           yield RunRequest(run_key=f"sync_after_{last_run.run_id}")

@sensor(job=sync_pt_nyt_articles)
def nyt_sync_sensor(context):
   """Sensor that triggers sync_pt_nyt_articles when nyt_news_job completes successfully"""
   runs = context.instance.get_runs(
       filters=RunsFilter(job_name="nyt_news_job"),
       limit=1
   )
   last_run = runs[0] if runs else None

   if last_run and last_run.status == DagsterRunStatus.SUCCESS:
       cursor = context.cursor or ""
       if last_run.run_id != cursor:
           context.update_cursor(last_run.run_id)
           yield RunRequest(run_key=f"sync_after_{last_run.run_id}")

@sensor(job=sync_pt_reuters_articles)
def reuters_sync_sensor(context):
   """Sensor that triggers sync_pt_reuters_articles when reuters_news_job completes successfully"""
   runs = context.instance.get_runs(
       filters=RunsFilter(job_name="reuters_news_job"),
       limit=1
   )
   last_run = runs[0] if runs else None

   if last_run and last_run.status == DagsterRunStatus.SUCCESS:
       cursor = context.cursor or ""
       if last_run.run_id != cursor:
           context.update_cursor(last_run.run_id)
           yield RunRequest(run_key=f"sync_after_{last_run.run_id}")

@sensor(job=sync_pt_guardian_articles)
def guardian_sync_sensor(context):
   """Sensor that triggers sync_pt_guardian_articles when guardian_news_job completes successfully"""
   runs = context.instance.get_runs(
       filters=RunsFilter(job_name="guardian_news_job"),
       limit=1
   )
   last_run = runs[0] if runs else None

   if last_run and last_run.status == DagsterRunStatus.SUCCESS:
       cursor = context.cursor or ""
       if last_run.run_id != cursor:
           context.update_cursor(last_run.run_id)
           yield RunRequest(run_key=f"sync_after_{last_run.run_id}")

@sensor(job=sync_pt_aljazeera_articles)
def aljazeera_sync_sensor(context):
   """Sensor that triggers sync_pt_aljazeera_articles when aljazeera_news_job completes successfully"""
   runs = context.instance.get_runs(
       filters=RunsFilter(job_name="aljazeera_news_job"),
       limit=1
   )
   last_run = runs[0] if runs else None

   if last_run and last_run.status == DagsterRunStatus.SUCCESS:
       cursor = context.cursor or ""
       if last_run.run_id != cursor:
           context.update_cursor(last_run.run_id)
           yield RunRequest(run_key=f"sync_after_{last_run.run_id}")
           
           

# Define maximum run duration in minutes
MAX_DURATION_MINUTES = 20

@sensor(name="summarization_timeout_killer", minimum_interval_seconds=60)
def summarization_timeout_killer(context):
    instance = context.instance
    now = datetime.now(timezone.utc)

    # Get all currently running runs for this job
    running_runs = instance.get_runs(
        filters=RunsFilter(job_name="summarization_update_job", statuses=["STARTED"])
    )

    for run in running_runs:
        start_ts = run.start_time
        if not start_ts:
            continue  # skip if no start time

        started_at = datetime.fromtimestamp(start_ts, tz=timezone.utc)
        elapsed = now - started_at

        if elapsed > timedelta(minutes=MAX_DURATION_MINUTES):
            context.log.warn(f"Run {run.run_id} for summarization_update_job running too long ({elapsed}), cancelling it.")
            instance.report_run_canceled(run)
