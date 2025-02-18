
Based on:
# dagster_jobs.py
import os
import sys
import subprocess
from dagster import op, job

def get_script_path(relative_path: str) -> str:
    """
    Given a relative path (from the repository root), compute the absolute path.
    Assumes that this file is located in the 'dagster_orchestration' folder,
    and the repository root is one level up.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(current_dir, ".."))
    return os.path.join(base_dir, relative_path)

def get_log_file_path(filename: str) -> str:
    """
    Compute the absolute path for a log file.
    Assumes that logs are stored in the 'log' directory under the repository root.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(current_dir, ".."))
    log_dir = os.path.join(base_dir, "log")
    # Create the log directory if it doesn't exist.
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, filename)

def stream_subprocess_output(context, process, log_file_path: str):
    """
    Stream subprocess output line by line to Dagster's logger and also to a file.
    """
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        for line in iter(process.stdout.readline, ""):
            stripped_line = line.strip()
            context.log.info(stripped_line)
            log_file.write(line)
            log_file.flush()  # Ensure each line is written immediately.
    process.stdout.close()
    return process.wait()

# ## ABC News Job

@op
def abc_category_parser_op(context):
    context.log.info("Starting ABC Category Parser...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_abc/abc_category_rss_parser.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("abc_category_rss_parser.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"ABC Category Parser failed with return code {retcode}")
        context.log.warning("Continuing to article parser despite category parser failure.")
    return retcode

@op
def abc_article_parser_op(context, category_status):
    context.log.info("Starting ABC Article Parser...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_abc/abc_article_rss_parser.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("abc_article_rss_parser.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"ABC Article Parser failed with return code {retcode}")
        raise Exception("ABC Article Parser failed. Aborting job.")
    context.log.info("ABC Article Parser completed successfully.")
    return "articles_parsed"

@op
def abc_article_updater_op(context, articles_status):
    context.log.info("Starting ABC Article Content Updater...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_abc/abc_article_content_updater.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("abc_article_content_updater.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"ABC Article Updater failed with return code {retcode}")
        raise Exception("ABC Article Updater failed. Aborting job.")
    context.log.info("ABC Article Updater completed successfully.")
    return "update_completed"

@job
def abc_news_job():
    cat_status = abc_category_parser_op()
    articles_status = abc_article_parser_op(cat_status)
    abc_article_updater_op(articles_status)
    
    
# ## Al Jazeera Category Parser Op

@op
def aljazeera_category_parser_op(context):
    context.log.info("Starting Al Jazeera Category Parser...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_aljazeera/aljazeera_category_html_parser.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("aljazeera_category_html_parser.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Al Jazeera Category Parser failed with return code {retcode}")
        context.log.warning("Continuing to article parser despite category parser failure.")
    return retcode

# ## Al Jazeera Article Parser Op

@op
def aljazeera_article_parser_op(context, category_status):
    context.log.info("Starting Al Jazeera Article Parser...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_aljazeera/aljazeera_article_rss_parser.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("aljazeera_article_rss_parser.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Al Jazeera Article Parser failed with return code {retcode}")
        raise Exception("Al Jazeera Article Parser failed. Aborting job.")
    context.log.info("Al Jazeera Article Parser completed successfully.")
    return "articles_parsed"

# ## Al Jazeera Article Updater Op

@op
def aljazeera_article_updater_op(context, articles_status):
    context.log.info("Starting Al Jazeera Article Content Updater...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_aljazeera/aljazeera_article_content_updater.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("aljazeera_article_content_updater.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Al Jazeera Article Updater failed with return code {retcode}")
        raise Exception("Al Jazeera Article Updater failed. Aborting job.")
    context.log.info("Al Jazeera Article Updater completed successfully.")
    return "update_completed"

# ## Compose the Al Jazeera Job

@job
def aljazeera_news_job():
    cat_status = aljazeera_category_parser_op()
    articles_status = aljazeera_article_parser_op(cat_status)
    aljazeera_article_updater_op(articles_status)


# repository.py
from dagster import repository
from dagster_jobs import abc_news_job, aljazeera_news_job
from schedules import abc_news_schedule, aljazeera_news_schedule  # adjust the import if schedules are split

@repository
def news_aggregator_repository():
    return [
        abc_news_job,
        abc_news_schedule,
        aljazeera_news_job,
        aljazeera_news_schedule,  # add this if you created a schedule
    ]


And:
# schedules.py
from dagster import schedule
from dagster_jobs import abc_news_job, aljazeera_news_job

@schedule(cron_schedule="0 * * * *", job=abc_news_job, execution_timezone="UTC")
def abc_news_schedule(_context):
    # Return run config here if needed; an empty dict uses defaults.
    return {}


@schedule(cron_schedule="7 * * * *", job=aljazeera_news_job, execution_timezone="UTC")
def aljazeera_news_schedule(_context):
    # Run config (if needed)
    return {}


Now I need to add all other jobs to dagster:
├───pt_bbc
├───pt_fox
├───pt_guardian
├───pt_nyt
├───pt_reuters
└───py_cnn




(venv) C:\Users\Korisnik\Desktop\TLDR\news_dagster-etl\news_aggregator\portals>tree /f
Folder PATH listing
Volume serial number is ACEF-BB81
C:.
│   cache_models.py
│   
├───archive
│   └───pt_bloomberg
│           bloomberg_html_category_parser.py
│           bloomberg_rss_article_parser.py
│
├───modules
│   │   article_updater_utils.py
│   │   base_parser.py
│   │   keyword_extractor.py
│   │   logging_config.py
│   │   portal_db.py
│   │   rss_parser_utils.py
│   │   __init__.py
│   │   
│   └───__pycache__
│           article_updater_utils.cpython-313.pyc
│           base_parser.cpython-313.pyc
│           keyword_extractor.cpython-313.pyc
│           logging_config.cpython-313.pyc
│           portal_db.cpython-313.pyc
│           rss_parser_utils.cpython-313.pyc
│           __init__.cpython-313.pyc
│
├───pt_abc
│       abc_article_content_updater.py
│       abc_article_rss_parser.py
│       abc_category_rss_parser.py
│
├───pt_aljazeera
│       aljazeera_article_content_updater.py
│       aljazeera_article_rss_parser.py
│       aljazeera_category_html_parser.py
│       test_rss_feed.py
│
├───pt_bbc
│       bbc_article_content_updater.py
│       bbc_article_rss_parser.py
│       bbc_category_html_parser.py
│
├───pt_fox
│       fox_article_content_updater.py
│       fox_article_rss_parser.py
│       fox_category_rss_parser.py
│       fox_keyword_updater.py
│
├───pt_guardian
│       guardian_article_content_updater.py
│       guard_html_category_parser.py
│       guard_rss_article_parser.py
│       test_articles.py
│
├───pt_nyt
│       nyt_article_content_updater.py
│       nyt_rss_article_parser.py
│       nyt_rss_categories_parser.py
│       __init__.py
│
├───pt_reuters
│       reuters_article_content_updater.py
│       reuters_keyword_updater.py
│       reuters_rss_articles_parser.py
│       reuters_rss_categories_parser.py
│
└───py_cnn
        cnn_article_content_updater.py
        cnn_html_articles_parser.py
        cnn_html_categories_parser.py



Important!
Following scripts require pychrome:

news_dagster-etl\news_aggregator\portals\pt_nyt\nyt_article_content_updater.py:
  28  from bs4 import BeautifulSoup
  29: import pychrome
  30  

news_dagster-etl\news_aggregator\portals\pt_reuters\reuters_article_content_updater.py:
  31  import time
  32: import pychrome
  33  

news_dagster-etl\news_aggregator\portals\pt_reuters\reuters_rss_articles_parser.py:
  19  
  20: import pychrome
  21  from lxml import html

news_dagster-etl\news_aggregator\portals\pt_reuters\reuters_rss_categories_parser.py:
  119          try:
  120:             import pychrome
  121  


So, before scripts starts pychrome must be launched. 
Its important that we have some kind of check if pychrome is already launched (because another job could have started it and we can reuse it).
In case its started - we do not need to start it in current script.
If its not started - we need to start it.

Power Shell command for starting pychrome:

Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList `
 "--remote-debugging-port=9222",
 "--user-data-dir=""C:\Users\Korisnik\AppData\Local\Google\Chrome\User Data""",
 "--profile-directory=""Profile 1""",
 "--disable-gpu",
 "--disable-popup-blocking",
 "--disable-extensions",
 "--disable-sync",
 "--disable-translate",
 "--disable-notifications",
 "--mute-audio"

 If something is not clear- ask, do not assume. 

 # ##### Questions answers

 I have a few clarifying questions before proceeding:

Job Pipeline Structure:
Should each new portal (pt_bbc, pt_fox, pt_guardian, pt_nyt, pt_reuters, py_cnn) follow the same pipeline pattern as the existing jobs (i.e. a category parser op → article parser op → article updater op)? 
Yes.

For pt_fox, there’s an extra script (fox_keyword_updater.py). Would you like this to run as an additional step after the article updater, or should it be incorporated differently?
Ignore this file.

Pychrome Integration:
For the portals that require pychrome (pt_nyt and pt_reuters), I plan to add a helper function that:

Checks if Chrome’s remote debugging port (9222) is open.
If not, launches Chrome using the provided PowerShell command.
Does that approach work for you?
Yes.

Scheduling:
Do you have specific cron schedules in mind for these new jobs? If not, would you like me to propose default schedules (for example, spacing them out at different minutes within the hour)?

Here is current scheduler:

# schedules.py
from dagster import schedule
from dagster_jobs import abc_news_job, aljazeera_news_job

@schedule(cron_schedule="0 * * * *", job=abc_news_job, execution_timezone="UTC")
def abc_news_schedule(_context):
    # Return run config here if needed; an empty dict uses defaults.
    return {}


@schedule(cron_schedule="7 * * * *", job=aljazeera_news_job, execution_timezone="UTC")
def aljazeera_news_schedule(_context):
    # Run config (if needed)
    return {}

I want to keep spacing new jobs in same way with 7 minutes spacing - for example next job should be at 
"14 * * * *"

