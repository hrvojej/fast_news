from news_dagster_etl.news_aggregator.db_scripts.db_utils import get_db_connection

class DatabaseContext:
    def __init__(self, env='dev'):
        self.conn = get_db_connection(env)
        if not self.conn:
            raise Exception("Failed to initialize database context due to connection error.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def get_connection(self):
        return self.conn

# Example usage (can be removed later):
if __name__ == '__main__':
    try:
        with DatabaseContext() as db_context:
            conn = db_context.get_connection()
            if conn:
                print("Database context initialized and connection obtained successfully.")
            else:
                print("Failed to get database connection from context.")
    except Exception as e:
        print(f"Exception during database context initialization: {e}")
