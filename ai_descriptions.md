# Create production based on dev
Works nice. 

Now based on this script lets create production script that will not drop create tables but use those existing tables. 

It should also not delete existing articles but update them if date is newer or insert new articles if they dont exist in articles table. 

This script will be run on every hour or so by Dagster to insert new articles from each category or to update existing ones. 

# 
Now modfy this nyt dev script to work like Guardian dev script; with single table and batch processing..I also want to have same output as in guardian and all other stuff too.


#
Great. Please now update nyt production script to equally resembles where applicable to guardian production script.