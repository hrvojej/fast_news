Here is direcotry structure of my python data engineering project for fetching and scrapping RSS and HTML pages of categories and articles of 20 most popular portals:
run tree -f on /home/opc/news_dagster-etl/news_aggregator
 folder to see it.

Lets focus on 
/home/opc/news_dagster-etl/news_aggregator/db_scripts

Task at hand:
check
/home/opc/news_dagster-etl/news_aggregator/db_scripts/schemas/create_complete_schema.sql

I want to simplify Event management and keep it in single table. 
Events have to have connection to one or more articles. 
Idea is that each portal report on news but those news could be covering same event. 
I will implement latter on functionalitiy that will connect event with all articles that are talking about that event.

