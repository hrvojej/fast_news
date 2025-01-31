# venv and sys
conda activate pytorch_env
Public IPv4 address:  
129.213.125.118
Private IPv4 address: 
10.0.0.182

# dagster vm
ocid1.instance.oc1.iad.anuwcljt62g7x7ycs2ahtlwnqxbyu22ap4zlfsosnt2thb7k43a6dbvbea5q
ocid1.tenancy.oc1..aaaaaaaazwnzfsshem5h3phaphasftvjdtnqwwly6nd2jwekakr4vdp7s34q
ocid1.user.oc1..aaaaaaaaxuuxwp42n366bedbjmmfsjwpnt6cralaie5sk5dzod5p4skwxmxq

fingerprint: 24:13:1a:df:44:7a:db:e6:5e:d9:82:56:00:e7:34:d4

[DEFAULT]
user=ocid1.user.oc1..aaaaaaaaxuuxwp42n366bedbjmmfsjwpnt6cralaie5sk5dzod5p4skwxmxq
fingerprint=24:13:1a:df:44:7a:db:e6:5e:d9:82:56:00:e7:34:d4
tenancy=ocid1.tenancy.oc1..aaaaaaaazwnzfsshem5h3phaphasftvjdtnqwwly6nd2jwekakr4vdp7s34q
region=us-ashburn-1
key_file=~/.oci/keys/oci_api_key.pem

# pg
CREATE DATABASE news_aggregator;
CREATE USER news_admin WITH PASSWORD 'fasldkflk423mkj4k24jk242';
sudo -u postgres psql
\c news_aggregator
PGPASSWORD='fasldkflk423mkj4k24jk242' psql -U news_admin -d news_aggregator -h localhost

\dn - list schemas


# Image details
Image details
Operating system:
Oracle Linux
Version:8
Image:
Oracle-Linux-8.10-aarch64-2024.10.31-0
Shape configuration
Shape: VM.Standard.A2.Flex
OCPU count:2
Memory (GB):12


# db
## db setup:
sudo -u postgres /home/opc/miniforge3/envs/pytorch_env/bin/python \
    /home/opc/news_dagster-etl/news_aggregator/db_scripts/setup_database.py dev

ALTER USER news_admin_prod WITH PASSWORD 'fasldkflk423mkj4k24jk242';



Dosljedni tipovi ID-jeva: Trenutačno se miješaju tipovi (neke tablice imaju INT, neke TEXT, neke SERIAL). U većim sustavima korisno je preći na UUID ili bar dosljedno BIGINT.
Normalizacija: Za polja poput event_type, content_type, relationship_type i slično moglo bi se razmisliti o posebnim lookup tablicama radi veće fleksibilnosti i održavanja.

