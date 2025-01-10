#!/bin/bash

# Install PostgreSQL repository
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# Disable built-in PostgreSQL module
sudo dnf -qy module disable postgresql

# Install PostgreSQL 16
sudo dnf install -y postgresql16-server postgresql16-contrib

# Initialize the database
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb

# Start PostgreSQL service
sudo systemctl start postgresql-16
sudo systemctl enable postgresql-16

# Configure PostgreSQL to accept remote connections
# Backup original config
sudo cp /var/lib/pgsql/16/data/postgresql.conf /var/lib/pgsql/16/data/postgresql.conf.bak
sudo cp /var/lib/pgsql/16/data/pg_hba.conf /var/lib/pgsql/16/data/pg_hba.conf.bak

# Update postgresql.conf to listen on all interfaces
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /var/lib/pgsql/16/data/postgresql.conf

# Add firewall rule
sudo firewall-cmd --permanent --add-port=5432/tcp
sudo firewall-cmd --reload

# Create RSS database and user
sudo -u postgres psql -c "CREATE DATABASE rss_feeds;"
sudo -u postgres psql -c "CREATE USER rss_admin WITH ENCRYPTED PASSWORD 'mJN0f864j23zWWDr';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE rss_feeds TO rss_admin;"

# Restart PostgreSQL
sudo systemctl restart postgresql-16

echo "PostgreSQL installation and configuration completed."