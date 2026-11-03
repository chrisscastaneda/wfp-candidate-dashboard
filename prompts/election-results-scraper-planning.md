# Election Results Scraper Planning

Let's develop an implementation plan for building out the election results scrapers to power the next stage of this dashboard.  For now, we don't have the resources for an AP or DDHQ license so we'll need to rely on scraping the data and pulling from free resources where we can.

I want to prioritize collecting data is this order:
1. Federal level races for U.S. House and U.S. Senate
2. State level races, for both state houses and state senates as well as state wide offices like Governors, Attorney Generals, etc
3. State level ballot initiatives
4. Local races
    - Focus on NY and CA first
5. We can de-prioritize anything that is difficult to get data for, like sites that block scripts or are otherwise hard to verify.
6. If it's easy enough to pull lower priority results data for local races along with the scrapes for higher offices, let's just grab that info too with the scrapes for higher offices.

It seems like we'll need to develop a scraper for each state and county level data source.  As such, I want to prioritize developing the state level scrapers first.  

I want to be able to easily call the scrapers from the command line and pass along flags to indicate my scraping preferences. Some initial thoughts about my preferences are: running everything (perhaps this is the default behavior); running the scrapers just for a specific state by including the two letter state abbreviation in the flag, or a set of states by including a comma separated list of states as a parameter; a flag/parameter to call the county level scrapers for a state; etc.

I imagine that it might be useful to develop a primary election results driver script that serves as the primary interface to the various state and county level scripts.  Having separate scripts for each data source will also help with maintainability.  

I also want to be sure to keep a logs for each scrape, regardless of the scope of the scrape.  So let's add a `logs/` directory (if its not there already) and keep a scraper log for each data pull the scrapers commit.

Let's not write any code yet, but feel free to produce some exploratory scripts to test out ideas and concepts for this set of scrapers.

I want a detailed plan outlining each scraper script we're going to develop.  I want to see a plan for how the driver script will orchestrate everything and the API it will expose via command line flags and parameters.  When planning and ultimately when writing code, it's important to design things well, I like to lean on the best practices outlined in the book "A Philosophy of Software Design" by John Ousterhout.

