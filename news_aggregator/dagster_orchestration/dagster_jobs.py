# dagster_jobs.py
import os
import sys
import socket
import subprocess
from dagster import op, job
import time
import random

##############################################
# Helper Functions
##############################################

def add_random_delay(context, min_delay=0, max_delay=10):
    """
    Adds a random delay (in minutes) before proceeding.
    You can adjust min_delay and max_delay as needed.
    """
    delay_minutes = random.randint(min_delay, max_delay)
    context.log.info(f"Random delay: waiting for {delay_minutes} minutes before starting.")
    time.sleep(delay_minutes * 60)

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

##############################################
# Pychrome Integration Helper
##############################################


def is_chrome_running() -> bool:
    """Check if Chrome’s remote debugging port (9222) is open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect(("localhost", 9222))
            return True
        except socket.error:
            return False

def ensure_pychrome_running(context):
    """Ensure that Chrome is running with remote debugging enabled."""
    if not is_chrome_running():
        context.log.info("Chrome remote debugging (port 9222) not detected. Launching Chrome with pychrome...")
        powershell_command = [
            "powershell",
            "-Command",
            (
                'Start-Process -FilePath "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" '
                '-ArgumentList \'--remote-debugging-port=9222\','
                '\'--user-data-dir=C:\\Users\\Korisnik\\AppData\\Local\\Google\\Chrome\\User Data\','
                '\'--profile-directory=Profile 1\','
                '\'--disable-gpu\','
                '\'--disable-popup-blocking\','
                '\'--disable-extensions\','
                '\'--disable-sync\','
                '\'--disable-translate\','
                '\'--disable-notifications\','
                '\'--mute-audio\' '
                '-WindowStyle Hidden'
            )
        ]
        subprocess.Popen(powershell_command)

##############################################
# Existing ABC and Al Jazeera Ops & Jobs
##############################################

@op
def abc_category_parser_op(context):
    add_random_delay(context)
    context.log.info("Starting ABC Category Parser...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_abc/abc_category_rss_parser.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("abc_category_rss_parser.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
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
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
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
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
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

@op
def aljazeera_category_parser_op(context):
    add_random_delay(context)
    context.log.info("Starting Al Jazeera Category Parser...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_aljazeera/aljazeera_category_html_parser.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("aljazeera_category_html_parser.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Al Jazeera Category Parser failed with return code {retcode}")
        context.log.warning("Continuing to article parser despite category parser failure.")
    return retcode

@op
def aljazeera_article_parser_op(context, category_status):
    context.log.info("Starting Al Jazeera Article Parser...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_aljazeera/aljazeera_article_rss_parser.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("aljazeera_article_rss_parser.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Al Jazeera Article Parser failed with return code {retcode}")
        raise Exception("Al Jazeera Article Parser failed. Aborting job.")
    context.log.info("Al Jazeera Article Parser completed successfully.")
    return "articles_parsed"

@op
def aljazeera_article_updater_op(context, articles_status):
    context.log.info("Starting Al Jazeera Article Content Updater...")
    context.log.info(f"Current working directory: {os.getcwd()}")
    script_path = get_script_path("portals/pt_aljazeera/aljazeera_article_content_updater.py")
    context.log.info(f"Using script path: {script_path}")
    log_file = get_log_file_path("aljazeera_article_content_updater.log")
    context.log.info(f"Logging to file: {log_file}")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Al Jazeera Article Updater failed with return code {retcode}")
        raise Exception("Al Jazeera Article Updater failed. Aborting job.")
    context.log.info("Al Jazeera Article Updater completed successfully.")
    return "update_completed"

@job
def aljazeera_news_job():
    cat_status = aljazeera_category_parser_op()
    articles_status = aljazeera_article_parser_op(cat_status)
    aljazeera_article_updater_op(articles_status)

##############################################
# New Portal Jobs
##############################################

# --- pt_bbc Job ---
@op
def bbc_category_parser_op(context):
    add_random_delay(context)
    context.log.info("Starting BBC Category Parser...")
    script_path = get_script_path("portals/pt_bbc/bbc_category_html_parser.py")
    log_file = get_log_file_path("bbc_category_html_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"BBC Category Parser failed with return code {retcode}")
        context.log.warning("Continuing to article parser despite category parser failure.")
    return retcode

@op
def bbc_article_parser_op(context, category_status):
    context.log.info("Starting BBC Article Parser...")
    script_path = get_script_path("portals/pt_bbc/bbc_article_rss_parser.py")
    log_file = get_log_file_path("bbc_article_rss_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"BBC Article Parser failed with return code {retcode}")
        raise Exception("BBC Article Parser failed. Aborting job.")
    context.log.info("BBC Article Parser completed successfully.")
    return "articles_parsed"

@op
def bbc_article_updater_op(context, articles_status):
    context.log.info("Starting BBC Article Content Updater...")
    script_path = get_script_path("portals/pt_bbc/bbc_article_content_updater.py")
    log_file = get_log_file_path("bbc_article_content_updater.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"BBC Article Updater failed with return code {retcode}")
        raise Exception("BBC Article Updater failed. Aborting job.")
    context.log.info("BBC Article Updater completed successfully.")
    return "update_completed"

@job
def bbc_news_job():
    cat_status = bbc_category_parser_op()
    articles_status = bbc_article_parser_op(cat_status)
    bbc_article_updater_op(articles_status)

# --- pt_fox Job ---
@op
def fox_category_parser_op(context):
    add_random_delay(context)
    context.log.info("Starting FOX Category Parser...")
    script_path = get_script_path("portals/pt_fox/fox_category_rss_parser.py")
    log_file = get_log_file_path("fox_category_rss_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"FOX Category Parser failed with return code {retcode}")
        context.log.warning("Continuing to article parser despite category parser failure.")
    return retcode

@op
def fox_article_parser_op(context, category_status):
    context.log.info("Starting FOX Article Parser...")
    script_path = get_script_path("portals/pt_fox/fox_article_rss_parser.py")
    log_file = get_log_file_path("fox_article_rss_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"FOX Article Parser failed with return code {retcode}")
        raise Exception("FOX Article Parser failed. Aborting job.")
    context.log.info("FOX Article Parser completed successfully.")
    return "articles_parsed"

@op
def fox_article_updater_op(context, articles_status):
    context.log.info("Starting FOX Article Content Updater...")
    script_path = get_script_path("portals/pt_fox/fox_article_content_updater.py")
    log_file = get_log_file_path("fox_article_content_updater.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"FOX Article Updater failed with return code {retcode}")
        raise Exception("FOX Article Updater failed. Aborting job.")
    context.log.info("FOX Article Updater completed successfully.")
    return "update_completed"

@job
def fox_news_job():
    cat_status = fox_category_parser_op()
    articles_status = fox_article_parser_op(cat_status)
    fox_article_updater_op(articles_status)

# --- pt_guardian Job ---
@op
def guardian_category_parser_op(context):
    add_random_delay(context)
    context.log.info("Starting Guardian Category Parser...")
    script_path = get_script_path("portals/pt_guardian/guard_html_category_parser.py")
    log_file = get_log_file_path("guardian_category_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Guardian Category Parser failed with return code {retcode}")
        context.log.warning("Continuing to article parser despite category parser failure.")
    return retcode

@op
def guardian_article_parser_op(context, category_status):
    context.log.info("Starting Guardian Article Parser...")
    script_path = get_script_path("portals/pt_guardian/guard_rss_article_parser.py")
    log_file = get_log_file_path("guardian_article_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Guardian Article Parser failed with return code {retcode}")
        raise Exception("Guardian Article Parser failed. Aborting job.")
    context.log.info("Guardian Article Parser completed successfully.")
    return "articles_parsed"

@op
def guardian_article_updater_op(context, articles_status):
    context.log.info("Starting Guardian Article Content Updater...")
    script_path = get_script_path("portals/pt_guardian/guardian_article_content_updater.py")
    log_file = get_log_file_path("guardian_article_content_updater.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Guardian Article Updater failed with return code {retcode}")
        raise Exception("Guardian Article Updater failed. Aborting job.")
    context.log.info("Guardian Article Updater completed successfully.")
    return "update_completed"

@job
def guardian_news_job():
    cat_status = guardian_category_parser_op()
    articles_status = guardian_article_parser_op(cat_status)
    guardian_article_updater_op(articles_status)

# --- pt_nyt Job (requires pychrome) ---
@op
def nyt_category_parser_op(context):
    add_random_delay(context)
    context.log.info("Starting NYT Category Parser...")
    ensure_pychrome_running(context)
    script_path = get_script_path("portals/pt_nyt/nyt_rss_categories_parser.py")
    log_file = get_log_file_path("nyt_rss_categories_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"NYT Category Parser failed with return code {retcode}")
        context.log.warning("Continuing to article parser despite category parser failure.")
    return retcode

@op
def nyt_article_parser_op(context, category_status):
    context.log.info("Starting NYT Article Parser...")
    ensure_pychrome_running(context)
    script_path = get_script_path("portals/pt_nyt/nyt_rss_article_parser.py")
    log_file = get_log_file_path("nyt_rss_article_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"NYT Article Parser failed with return code {retcode}")
        raise Exception("NYT Article Parser failed. Aborting job.")
    context.log.info("NYT Article Parser completed successfully.")
    return "articles_parsed"

@op
def nyt_article_updater_op(context, articles_status):
    context.log.info("Starting NYT Article Content Updater...")
    ensure_pychrome_running(context)
    script_path = get_script_path("portals/pt_nyt/nyt_article_content_updater.py")
    log_file = get_log_file_path("nyt_article_content_updater.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"NYT Article Updater failed with return code {retcode}")
        raise Exception("NYT Article Updater failed. Aborting job.")
    context.log.info("NYT Article Updater completed successfully.")
    return "update_completed"

@job
def nyt_news_job():
    cat_status = nyt_category_parser_op()
    articles_status = nyt_article_parser_op(cat_status)
    nyt_article_updater_op(articles_status)

# --- pt_reuters Job (requires pychrome) ---
@op
def reuters_category_parser_op(context):
    add_random_delay(context)
    context.log.info("Starting Reuters Category Parser...")
    ensure_pychrome_running(context)
    script_path = get_script_path("portals/pt_reuters/reuters_rss_categories_parser.py")
    log_file = get_log_file_path("reuters_rss_categories_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Reuters Category Parser failed with return code {retcode}")
        context.log.warning("Continuing to article parser despite category parser failure.")
    return retcode

@op
def reuters_article_parser_op(context, category_status):
    context.log.info("Starting Reuters Article Parser...")
    ensure_pychrome_running(context)
    script_path = get_script_path("portals/pt_reuters/reuters_rss_articles_parser.py")
    log_file = get_log_file_path("reuters_rss_articles_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Reuters Article Parser failed with return code {retcode}")
        raise Exception("Reuters Article Parser failed. Aborting job.")
    context.log.info("Reuters Article Parser completed successfully.")
    return "articles_parsed"

@op
def reuters_article_updater_op(context, articles_status):
    context.log.info("Starting Reuters Article Content Updater...")
    ensure_pychrome_running(context)
    script_path = get_script_path("portals/pt_reuters/reuters_article_content_updater.py")
    log_file = get_log_file_path("reuters_article_content_updater.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"Reuters Article Updater failed with return code {retcode}")
        raise Exception("Reuters Article Updater failed. Aborting job.")
    context.log.info("Reuters Article Updater completed successfully.")
    return "update_completed"

@job
def reuters_news_job():
    cat_status = reuters_category_parser_op()
    articles_status = reuters_article_parser_op(cat_status)
    reuters_article_updater_op(articles_status)

# --- py_cnn Job ---
@op
def cnn_category_parser_op(context):
    add_random_delay(context)
    context.log.info("Starting CNN Category Parser...")
    script_path = get_script_path("portals/py_cnn/cnn_html_categories_parser.py")
    log_file = get_log_file_path("cnn_html_categories_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"CNN Category Parser failed with return code {retcode}")
        context.log.warning("Continuing to article parser despite category parser failure.")
    return retcode

@op
def cnn_article_parser_op(context, category_status):
    context.log.info("Starting CNN Article Parser...")
    script_path = get_script_path("portals/py_cnn/cnn_html_articles_parser.py")
    log_file = get_log_file_path("cnn_html_articles_parser.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"CNN Article Parser failed with return code {retcode}")
        raise Exception("CNN Article Parser failed. Aborting job.")
    context.log.info("CNN Article Parser completed successfully.")
    return "articles_parsed"

@op
def cnn_article_updater_op(context, articles_status):
    context.log.info("Starting CNN Article Content Updater...")
    script_path = get_script_path("portals/py_cnn/cnn_article_content_updater.py")
    log_file = get_log_file_path("cnn_article_content_updater.log")
    cmd = [sys.executable, script_path, "--env", "dev"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8")
    retcode = stream_subprocess_output(context, process, log_file)
    if retcode != 0:
        context.log.error(f"CNN Article Updater failed with return code {retcode}")
        raise Exception("CNN Article Updater failed. Aborting job.")
    context.log.info("CNN Article Updater completed successfully.")
    return "update_completed"

@job
def cnn_news_job():
    cat_status = cnn_category_parser_op()
    articles_status = cnn_article_parser_op(cat_status)
    cnn_article_updater_op(articles_status)
