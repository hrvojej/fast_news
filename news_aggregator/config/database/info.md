# #########################################  DROP CREATE databases ######################################
sudo -u postgres psql
DROP DATABASE news_aggregator_dev;

## Create DB DEV
DROP DATABASE news_aggregator_dev;

DROP USER news_admin_dev;

CREATE DATABASE news_aggregator_dev;

CREATE USER news_admin_dev WITH PASSWORD 'fasldkflk423mkj4k24jk242';

GRANT ALL PRIVILEGES ON DATABASE news_aggregator_dev TO news_admin_dev;

ALTER DATABASE news_aggregator_dev OWNER TO news_admin_dev;


## Create DB PROD
CREATE DATABASE news_aggregator_prod;
CREATE USER news_admin_prod WITH PASSWORD 'fasldkflk423mkj4k24jk242';
GRANT ALL PRIVILEGES ON DATABASE news_aggregator_prod TO news_admin_prod;
ALTER DATABASE news_aggregator_prod OWNER TO news_admin_prod;

# ########################### Create the Initial Migration (Code First) ###############################
- in alembic.ini we have sqlalchemy.url = postgresql+psycopg2://news_admin_dev:fasldkflk423mkj4k24jk242@localhost:5432/news_aggregator_dev -> so this will initialize dev database

alembic revision --autogenerate -m "Initial migration" 
- DELETE PREVIOUS MIGRATIONS IF GOING FROM STRACH

- model.py is upgraded so it creates schemas in start
alembic upgrade head



