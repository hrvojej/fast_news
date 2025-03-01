from dagster import job, op
import psycopg2
from sshtunnel import SSHTunnelForwarder

@op(config_schema={"schema_name": str})
def sync_schema_articles(context):
  """Syncs articles from source to target database for a specific schema"""
  schema_name = context.op_config["schema_name"]
  context.log.info(f"Syncing articles from {schema_name}")
  
  # SSH tunnel configuration
  ssh_tunnel = SSHTunnelForwarder(
      ('150.136.244.218', 22),
      ssh_username='opc',
      ssh_pkey='C:/Users/Korisnik/.ssh/pg_prod_ssh-key-2025-02-28.pem',
      remote_bind_address=('localhost', 5432),
      local_bind_address=('localhost', 6543)  # Use any free local port
  )
  
  # Start the tunnel
  ssh_tunnel.start()
  
  # Connection parameters
  source_conn_params = {
      "dbname": "news_aggregator_dev",
      "user": "news_admin_dev",
      "password": "fasldkflk423mkj4k24jk242",
      "host": "localhost",
      "port": "5432"
  }
  
  target_conn_params = {
      "dbname": "news_aggregator_prod",
      "user": "news_admin_dev", 
      "password": "fasldkflk423mkj4k24jk242",
      "host": "localhost",
      "port": str(ssh_tunnel.local_bind_port)  # Use the local port from the tunnel
  }
  
  try:
      # Connect to source database
      source_conn = psycopg2.connect(**source_conn_params)
      source_cursor = source_conn.cursor()
      
      # Connect to target database
      target_conn = psycopg2.connect(**target_conn_params)
      target_cursor = target_conn.cursor()
      
      # Get all columns except 'content'
      source_cursor.execute(f"""
          SELECT column_name
          FROM information_schema.columns
          WHERE table_schema = '{schema_name}'
          AND table_name = 'articles'
          AND column_name != 'content'
      """)
      
      columns = [col[0] for col in source_cursor.fetchall()]
      columns_str = ", ".join(columns)
      placeholders = ", ".join(["%s"] * len(columns))
      update_set = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns])
      
      # Get data from source (excluding content)
      source_cursor.execute(f"""
          SELECT {columns_str}
          FROM {schema_name}.articles
      """)
      
      batch_size = 1000
      rows = source_cursor.fetchmany(batch_size)
      
      while rows:
          # Begin transaction
          target_cursor.execute("BEGIN")
          
          # Prepare the INSERT ON CONFLICT statement
          insert_query = f"""
              INSERT INTO {schema_name}.articles ({columns_str})
              VALUES ({placeholders})
              ON CONFLICT (article_id) 
              DO UPDATE SET {update_set}
          """
          
          # Execute batch insert
          target_cursor.executemany(insert_query, rows)
          
          # Commit transaction
          target_conn.commit()
          
          context.log.info(f"Inserted/updated {len(rows)} records for {schema_name}")
          
          # Get next batch
          rows = source_cursor.fetchmany(batch_size)
      
      context.log.info(f"Successfully synced {schema_name}.articles")
      
  except Exception as e:
      context.log.error(f"Error syncing {schema_name}.articles: {str(e)}")
      if 'target_conn' in locals() and target_conn:
          target_conn.rollback()
      raise
  
  finally:
      # Close connections
      if 'source_cursor' in locals() and source_cursor:
          source_cursor.close()
      if 'source_conn' in locals() and source_conn:
          source_conn.close()
      if 'target_cursor' in locals() and target_cursor:
          target_cursor.close()
      if 'target_conn' in locals() and target_conn:
          target_conn.close()
      
      # Stop the SSH tunnel
      ssh_tunnel.stop()

@job(name="sync_pt_abc_articles")
def sync_pt_abc_articles():
   sync_schema_articles.configured({"schema_name": "pt_abc"}, name="abc_sync")()

@job(name="sync_pt_bbc_articles")
def sync_pt_bbc_articles():
   sync_schema_articles.configured({"schema_name": "pt_bbc"}, name="bbc_sync")()

@job(name="sync_pt_cnn_articles")
def sync_pt_cnn_articles():
   sync_schema_articles.configured({"schema_name": "pt_cnn"}, name="cnn_sync")()

@job(name="sync_pt_fox_articles")
def sync_pt_fox_articles():
   sync_schema_articles.configured({"schema_name": "pt_fox"}, name="fox_sync")()

@job(name="sync_pt_nyt_articles")
def sync_pt_nyt_articles():
   sync_schema_articles.configured({"schema_name": "pt_nyt"}, name="nyt_sync")()

@job(name="sync_pt_reuters_articles")
def sync_pt_reuters_articles():
   sync_schema_articles.configured({"schema_name": "pt_reuters"}, name="reuters_sync")()

@job(name="sync_pt_guardian_articles")
def sync_pt_guardian_articles():
   sync_schema_articles.configured({"schema_name": "pt_guardian"}, name="guardian_sync")()

@job(name="sync_pt_aljazeera_articles")
def sync_pt_aljazeera_articles():
   sync_schema_articles.configured({"schema_name": "pt_aljazeera"}, name="aljazeera_sync")()

@job(name="sync_all_schema_articles")
def sync_all_schema_articles():
   sync_schema_articles.configured({"schema_name": "pt_abc"}, name="abc_sync_all")()
   sync_schema_articles.configured({"schema_name": "pt_bbc"}, name="bbc_sync_all")()
   sync_schema_articles.configured({"schema_name": "pt_cnn"}, name="cnn_sync_all")()
   sync_schema_articles.configured({"schema_name": "pt_fox"}, name="fox_sync_all")()
   sync_schema_articles.configured({"schema_name": "pt_nyt"}, name="nyt_sync_all")()
   sync_schema_articles.configured({"schema_name": "pt_reuters"}, name="reuters_sync_all")()
   sync_schema_articles.configured({"schema_name": "pt_guardian"}, name="guardian_sync_all")()
   sync_schema_articles.configured({"schema_name": "pt_aljazeera"}, name="aljazeera_sync_all")()