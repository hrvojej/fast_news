import os
import sys
import subprocess
from dagster import op, job, schedule

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
