from dagster import repository
from sensors import summarization_timeout_killer

from dagster_jobs import (
    abc_news_job,
    aljazeera_news_job,
    bbc_news_job,
    fox_news_job,
    guardian_news_job,
    nyt_news_job,
    reuters_news_job,
    cnn_news_job,
    summarization_update_job,      
    summarization_update_sensor,  
)

from sync_jobs import (
    sync_pt_abc_articles,
    sync_pt_aljazeera_articles, 
    sync_pt_bbc_articles,
    sync_pt_fox_articles,
    sync_pt_guardian_articles,
    sync_pt_nyt_articles, 
    sync_pt_reuters_articles,
    sync_pt_cnn_articles,
    sync_all_schema_articles
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

from sensors import (
    abc_sync_sensor,
    aljazeera_sync_sensor,
    bbc_sync_sensor,
    cnn_sync_sensor,
    fox_sync_sensor,
    guardian_sync_sensor,
    nyt_sync_sensor,
    reuters_sync_sensor
)

@repository
def news_aggregator_repository():
    return [
        # Jobs
        abc_news_job,
        aljazeera_news_job,
        bbc_news_job,
        fox_news_job,
        guardian_news_job,
        nyt_news_job,
        reuters_news_job,
        cnn_news_job,
        summarization_update_job,
        
        # Sync jobs
        sync_pt_abc_articles,
        sync_pt_aljazeera_articles,
        sync_pt_bbc_articles,
        sync_pt_fox_articles,
        sync_pt_guardian_articles,
        sync_pt_nyt_articles,
        sync_pt_reuters_articles,
        sync_pt_cnn_articles,
        sync_all_schema_articles,
        
        # Schedules
        abc_news_schedule,
        aljazeera_news_schedule,
        bbc_news_schedule,
        fox_news_schedule,
        guardian_news_schedule,
        nyt_news_schedule,
        reuters_news_schedule,
        cnn_news_schedule,
        
        # Sensors
        abc_sync_sensor,
        aljazeera_sync_sensor,
        bbc_sync_sensor,
        cnn_sync_sensor,
        fox_sync_sensor,
        guardian_sync_sensor,
        nyt_sync_sensor,
        reuters_sync_sensor,
        summarization_update_sensor,
        summarization_timeout_killer
    ]
