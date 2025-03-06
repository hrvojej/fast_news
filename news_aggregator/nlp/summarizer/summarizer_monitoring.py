# summarizer_monitoring.py
"""
Module for monitoring and tracking the article summarization process.
Provides metrics, progress tracking, and performance analysis.
"""

import os
import json
import time
from datetime import datetime, timedelta
import uuid

from summarizer_logging import get_logger
from summarizer_config import get_config_value

# Initialize logger
logger = get_logger(__name__)

class ProcessMetrics:
    """Class to track process metrics for the summarization system."""
    
    def __init__(self, metrics_file=None):
        """
        Initialize process metrics.
        
        Args:
            metrics_file (str, optional): Path to the metrics file
        """
        # Set metrics file path
        self.metrics_file = metrics_file or os.path.join("logs", "process_metrics.json")
        
        # Create metrics directory if it doesn't exist
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
        
        # Initialize metrics
        self.reset()
        
        # Load existing metrics if available
        self.load_metrics()
    
    def reset(self):
        """Reset metrics to initial values."""
        self.run_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.end_time = None
        self.total_articles = 0
        self.processed_articles = 0
        self.successful_articles = 0
        self.failed_articles = 0
        self.skipped_articles = 0
        self.api_calls = 0
        self.api_errors = 0
        self.total_api_time = 0
        self.total_process_time = 0
        self.article_metrics = {}
    
    def load_metrics(self):
        """Load metrics from file if available."""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    
                # Load historical runs
                self.historical_runs = data.get('historical_runs', [])
                
                # Load current run if it exists and is not completed
                current_run = data.get('current_run')
                if current_run and not current_run.get('end_time'):
                    # Convert string timestamps to datetime
                    current_run['start_time'] = datetime.fromisoformat(current_run['start_time'])
                    if current_run.get('end_time'):
                        current_run['end_time'] = datetime.fromisoformat(current_run['end_time'])
                    
                    # Set attributes
                    self.run_id = current_run.get('run_id', self.run_id)
                    self.start_time = current_run.get('start_time', self.start_time)
                    self.end_time = current_run.get('end_time')
                    self.total_articles = current_run.get('total_articles', 0)
                    self.processed_articles = current_run.get('processed_articles', 0)
                    self.successful_articles = current_run.get('successful_articles', 0)
                    self.failed_articles = current_run.get('failed_articles', 0)
                    self.skipped_articles = current_run.get('skipped_articles', 0)
                    self.api_calls = current_run.get('api_calls', 0)
                    self.api_errors = current_run.get('api_errors', 0)
                    self.total_api_time = current_run.get('total_api_time', 0)
                    self.total_process_time = current_run.get('total_process_time', 0)
                    self.article_metrics = current_run.get('article_metrics', {})
                
                logger.info(f"Loaded metrics from {self.metrics_file}")
                
            except Exception as e:
                logger.error(f"Error loading metrics: {e}", exc_info=True)
                self.historical_runs = []
        else:
            self.historical_runs = []
    
    def save_metrics(self):
        """Save metrics to file."""
        try:
            # Prepare current run data
            current_run = {
                'run_id': self.run_id,
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'total_articles': self.total_articles,
                'processed_articles': self.processed_articles,
                'successful_articles': self.successful_articles,
                'failed_articles': self.failed_articles,
                'skipped_articles': self.skipped_articles,
                'api_calls': self.api_calls,
                'api_errors': self.api_errors,
                'total_api_time': self.total_api_time,
                'total_process_time': self.total_process_time,
                'article_metrics': self.article_metrics
            }
            
            # Combine with historical runs
            data = {
                'current_run': current_run,
                'historical_runs': self.historical_runs
            }
            
            # Write to file
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved metrics to {self.metrics_file}")
            
        except Exception as e:
            logger.error(f"Error saving metrics: {e}", exc_info=True)
    
    def start_run(self, total_articles=0):
        """
        Start a new run.
        
        Args:
            total_articles (int): Total number of articles to process
        """
        # Archive current run if it exists and is not already archived
        if hasattr(self, 'run_id') and not self.end_time:
            self.complete_run()
        
        # Reset metrics
        self.reset()
        self.total_articles = total_articles
        
        logger.info(f"Started new run {self.run_id} with {total_articles} articles")
        
        # Save initial metrics
        self.save_metrics()
    
    def complete_run(self):
        """Complete the current run."""
        if not self.end_time:
            self.end_time = datetime.now()
            self.total_process_time = (self.end_time - self.start_time).total_seconds()
            
            # Archive current run
            current_run = {
                'run_id': self.run_id,
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'total_articles': self.total_articles,
                'processed_articles': self.processed_articles,
                'successful_articles': self.successful_articles,
                'failed_articles': self.failed_articles,
                'skipped_articles': self.skipped_articles,
                'api_calls': self.api_calls,
                'api_errors': self.api_errors,
                'total_api_time': self.total_api_time,
                'total_process_time': self.total_process_time,
                'success_rate': self.get_success_rate(),
                'average_processing_time': self.get_average_processing_time()
            }
            
            # Add to historical runs
            self.historical_runs.append(current_run)
            
            # Limit historical runs to most recent 20
            if len(self.historical_runs) > 20:
                self.historical_runs = self.historical_runs[-20:]
            
            logger.info(f"Completed run {self.run_id} with {self.processed_articles} articles processed")
            
            # Save final metrics
            self.save_metrics()
    
    def log_article_start(self, article_id):
        """
        Log the start of article processing.
        
        Args:
            article_id (str): The article ID
            
        Returns:
            str: A tracking ID for this processing attempt
        """
        tracking_id = f"{article_id}_{int(time.time())}"
        
        self.article_metrics[tracking_id] = {
            'article_id': article_id,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'status': 'processing',
            'api_calls': 0,
            'api_time': 0,
            'total_time': 0
        }
        
        self.processed_articles += 1
        
        # Periodically save metrics (every 10 articles)+
        if self.processed_articles % 10 == 0:
            self.save_metrics()
        
        return tracking_id
    
    def log_article_end(self, tracking_id, success=True, api_calls=0, api_time=0):
        """
        Log the end of article processing.
        
        Args:
            tracking_id (str): The tracking ID from log_article_start
            success (bool): Whether processing was successful
            api_calls (int): Number of API calls made
            api_time (float): Total time spent on API calls
        """
        if tracking_id not in self.article_metrics:
            logger.warning(f"Tracking ID {tracking_id} not found in article metrics")
            return
        
        article_metric = self.article_metrics[tracking_id]
        
        # Update metrics
        end_time = datetime.now()
        start_time = datetime.fromisoformat(article_metric['start_time'])
        total_time = (end_time - start_time).total_seconds()
        
        article_metric['end_time'] = end_time.isoformat()
        article_metric['status'] = 'success' if success else 'failed'
        article_metric['api_calls'] = api_calls
        article_metric['api_time'] = api_time
        article_metric['total_time'] = total_time
        
        # Update overall metrics
        if success:
            self.successful_articles += 1
        else:
            self.failed_articles += 1
        
        self.api_calls += api_calls
        self.total_api_time += api_time
        
        # Periodically save metrics (every 10 completed articles)
        completed = self.successful_articles + self.failed_articles
        if completed % 10 == 0:
            self.save_metrics()
    
    def log_api_call(self, success=True, duration=0):
        """
        Log an API call.
        
        Args:
            success (bool): Whether the API call was successful
            duration (float): Duration of the API call in seconds
        """
        self.api_calls += 1
        self.total_api_time += duration
        
        if not success:
            self.api_errors += 1
    
    def get_progress(self):
        """
        Get progress information.
        
        Returns:
            dict: Progress information
        """
        if self.total_articles > 0:
            completion_percentage = (self.processed_articles / self.total_articles) * 100
        else:
            completion_percentage = 0
        
        current_time = datetime.now()
        elapsed_time = (current_time - self.start_time).total_seconds()
        
        # Calculate estimated time remaining
        if self.processed_articles > 0 and self.total_articles > 0:
            avg_time_per_article = elapsed_time / self.processed_articles
            remaining_articles = self.total_articles - self.processed_articles
            estimated_time_remaining = avg_time_per_article * remaining_articles
            
            # Format as HH:MM:SS
            eta = str(timedelta(seconds=int(estimated_time_remaining)))
        else:
            eta = "Unknown"
        
        return {
            'run_id': self.run_id,
            'start_time': self.start_time.isoformat(),
            'current_time': current_time.isoformat(),
            'elapsed_time': elapsed_time,
            'elapsed_time_formatted': str(timedelta(seconds=int(elapsed_time))),
            'total_articles': self.total_articles,
            'processed_articles': self.processed_articles,
            'successful_articles': self.successful_articles,
            'failed_articles': self.failed_articles,
            'skipped_articles': self.skipped_articles,
            'completion_percentage': round(completion_percentage, 2),
            'remaining_articles': self.total_articles - self.processed_articles,
            'estimated_time_remaining': eta,
            'success_rate': self.get_success_rate(),
            'average_processing_time': self.get_average_processing_time()
        }
    
    def get_success_rate(self):
        """
        Get the success rate.
        
        Returns:
            float: Success rate as a percentage
        """
        if self.processed_articles > 0:
            return round((self.successful_articles / self.processed_articles) * 100, 2)
        else:
            return 0
    
    def get_average_processing_time(self):
        """
        Get the average processing time per article.
        
        Returns:
            float: Average processing time in seconds
        """
        completed_articles = [m for m in self.article_metrics.values() 
                             if m.get('status') in ['success', 'failed']]
        
        if completed_articles:
            total_time = sum(m.get('total_time', 0) for m in completed_articles)
            return round(total_time / len(completed_articles), 2)
        else:
            return 0
    
    def get_api_performance(self):
        """
        Get API performance metrics.
        
        Returns:
            dict: API performance metrics
        """
        if self.api_calls > 0:
            error_rate = (self.api_errors / self.api_calls) * 100
            avg_api_time = self.total_api_time / self.api_calls
        else:
            error_rate = 0
            avg_api_time = 0
        
        return {
            'total_api_calls': self.api_calls,
            'api_errors': self.api_errors,
            'error_rate': round(error_rate, 2),
            'total_api_time': round(self.total_api_time, 2),
            'average_api_time': round(avg_api_time, 2)
        }
    
    def get_historical_summary(self):
        """
        Get a summary of historical runs.
        
        Returns:
            dict: Summary of historical runs
        """
        if not self.historical_runs:
            return {
                'total_runs': 0,
                'total_articles_processed': 0,
                'average_success_rate': 0,
                'average_processing_time': 0
            }
        
        total_articles = sum(run.get('processed_articles', 0) for run in self.historical_runs)
        success_rates = [run.get('success_rate', 0) for run in self.historical_runs]
        processing_times = [run.get('average_processing_time', 0) for run in self.historical_runs]
        
        return {
            'total_runs': len(self.historical_runs),
            'total_articles_processed': total_articles,
            'average_success_rate': round(sum(success_rates) / len(success_rates), 2),
            'average_processing_time': round(sum(processing_times) / len(processing_times), 2),
            'last_run_date': self.historical_runs[-1].get('end_time') if self.historical_runs else None
        }

# Global metrics instance
process_metrics = ProcessMetrics()

def with_tracking(func):
    """
    Decorator to track article processing.
    
    Args:
        func: The function to track
        
    Returns:
        function: Wrapped function with tracking
    """
    def wrapper(self, article_info, *args, **kwargs):
        article_id = article_info.get('article_id')
        
        # Start tracking
        tracking_id = process_metrics.log_article_start(article_id)
        
        api_calls = 0
        api_time = 0
        start_time = time.time()
        
        try:
            # Call the original function
            result = func(self, article_info, *args, **kwargs)
            
            # Log completion
            end_time = time.time()
            process_metrics.log_article_end(
                tracking_id,
                success=result,
                api_calls=api_calls,
                api_time=api_time
            )
            
            return result
            
        except Exception as e:
            # Log failure
            process_metrics.log_article_end(
                tracking_id,
                success=False,
                api_calls=api_calls,
                api_time=api_time
            )
            
            # Re-raise the exception
            raise e
    
    return wrapper

# Function to print progress to console
def print_progress(metrics=None):
    """
    Print progress information to the console.
    
    Args:
        metrics (ProcessMetrics, optional): Metrics instance
    """
    if metrics is None:
        metrics = process_metrics
    
    progress = metrics.get_progress()
    
    print("\n=== Summarization Progress ===")
    print(f"Run ID: {progress['run_id']}")
    print(f"Elapsed Time: {progress['elapsed_time_formatted']}")
    print(f"Articles: {progress['processed_articles']}/{progress['total_articles']} "
          f"({progress['completion_percentage']}%)")
    print(f"Success: {progress['successful_articles']} | "
          f"Failed: {progress['failed_articles']} | "
          f"Skipped: {progress['skipped_articles']}")
    print(f"Success Rate: {progress['success_rate']}%")
    print(f"Avg. Processing Time: {metrics.get_average_processing_time()} seconds")
    print(f"ETA: {progress['estimated_time_remaining']}")
    print("=============================\n")

# Test function
def test_metrics():
    """Test the metrics functionality."""
    metrics = ProcessMetrics("test_metrics.json")
    metrics.start_run(100)
    
    for i in range(10):
        article_id = f"test_article_{i}"
        tracking_id = metrics.log_article_start(article_id)
        
        # Simulate processing
        time.sleep(0.1)
        
        # Simulate API calls
        api_calls = 1
        api_time = 0.05
        
        # Simulate success/failure
        success = i % 3 != 0  # Every 3rd article fails
        
        metrics.log_article_end(tracking_id, success, api_calls, api_time)
    
    # Print progress
    print_progress(metrics)
    
    # Complete run
    metrics.complete_run()
    
    # Clean up
    if os.path.exists("test_metrics.json"):
        os.remove("test_metrics.json")
    
    return True

if __name__ == "__main__":
    test_metrics()