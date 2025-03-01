# venv
python -m venv venv
.\venv\Scripts\activate
pip install pychrome requests urllib3

reuters Medo#342

# Chrome DEv Tools with Profile 3
Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList `
  "--remote-debugging-port=9222",
  "--user-data-dir=""C:\Users\Korisnik\AppData\Local\Google\Chrome\User Data""",
  "--profile-directory=""Profile 3""",
  "--disable-gpu",
  "--blink-settings=imagesEnabled=false",
  "--disable-popup-blocking",
  "--disable-extensions",
  "--disable-sync",
  "--disable-translate",
  "--disable-notifications",
  "--mute-audio"

# Chrome - use this
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

# pg
user: postgres 
pss: fasldkflk423mkj4k24jk242
psql -U postgres -W
DROP DATABASE news_aggregator_dev;
DROP ROLE news_admin_dev;
CREATE DATABASE news_aggregator_dev;
CREATE ROLE news_admin_dev WITH LOGIN PASSWORD 'fasldkflk423mkj4k24jk242';
ALTER DATABASE news_aggregator_dev OWNER TO news_admin_dev;

# pg-oci
IP: 150.136.244.218
sudo systemctl status postgresql-16
CREATE DATABASE news_aggregator_prod; 
CREATE ROLE news_admin_prod WITH LOGIN PASSWORD 'fasldkflk423mkj4k24jk242'; 
ALTER DATABASE news_aggregator_prod OWNER TO news_admin_prod;


# alembic
alembic upgrade head
