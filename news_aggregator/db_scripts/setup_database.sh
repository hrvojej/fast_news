#!/bin/bash
set -euo pipefail

# 1. Terminiranje aktivnih sesija za dev/prod
sudo -u postgres psql <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'news_aggregator_dev'
  AND pid <> pg_backend_pid();

SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'news_aggregator_prod'
  AND pid <> pg_backend_pid();
EOF

# 2. Brisanje baza i rola (ako postoje)
sudo -u postgres psql <<EOF
DROP DATABASE IF EXISTS news_aggregator_dev;
DROP DATABASE IF EXISTS news_aggregator_prod;

DROP ROLE IF EXISTS news_admin_dev;
DROP ROLE IF EXISTS news_admin_prod;
EOF

# 3. Kreiranje novih rola i baza
sudo -u postgres psql <<EOF
CREATE ROLE news_admin_dev WITH LOGIN PASSWORD 'SOME_STRONG_PASSWORD_DEV';
CREATE ROLE news_admin_prod WITH LOGIN PASSWORD 'SOME_STRONG_PASSWORD_PROD';

CREATE DATABASE news_aggregator_dev OWNER news_admin_dev;
CREATE DATABASE news_aggregator_prod OWNER news_admin_prod;

-- Postavljanje vlasnika i privilegija za dev bazu
ALTER DATABASE news_aggregator_dev OWNER TO news_admin_dev;
GRANT CONNECT ON DATABASE news_aggregator_dev TO news_admin_dev;
GRANT ALL PRIVILEGES ON DATABASE news_aggregator_dev TO news_admin_dev;

\c news_aggregator_dev
CREATE EXTENSION IF NOT EXISTS ltree;

ALTER SCHEMA public OWNER TO news_admin_dev;
GRANT USAGE ON SCHEMA public TO news_admin_dev;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO news_admin_dev;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO news_admin_dev;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO news_admin_dev;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON TABLES TO news_admin_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON SEQUENCES TO news_admin_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON FUNCTIONS TO news_admin_dev;

-- Postavljanje vlasnika i privilegija za prod bazu
ALTER DATABASE news_aggregator_prod OWNER TO news_admin_prod;
GRANT CONNECT ON DATABASE news_aggregator_prod TO news_admin_prod;
GRANT ALL PRIVILEGES ON DATABASE news_aggregator_prod TO news_admin_prod;

\c news_aggregator_prod
CREATE EXTENSION IF NOT EXISTS ltree;

ALTER SCHEMA public OWNER TO news_admin_prod;
GRANT USAGE ON SCHEMA public TO news_admin_prod;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO news_admin_prod;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO news_admin_prod;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO news_admin_prod;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON TABLES TO news_admin_prod;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON SEQUENCES TO news_admin_prod;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON FUNCTIONS TO news_admin_prod;
EOF

# 4. Pozivanje setup_database.py za dev i prod (conda Python)
sudo -u postgres /home/opc/miniforge3/envs/pytorch_env/bin/python \
  /home/opc/news_dagster-etl/news_aggregator/db_scripts/setup_database.py dev

sudo -u postgres /home/opc/miniforge3/envs/pytorch_env/bin/python \
  /home/opc/news_dagster-etl/news_aggregator/db_scripts/setup_database.py prod

echo "Database setup completed."
