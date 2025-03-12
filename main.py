import json
from datetime import datetime
import statistics

#import pour les requetes API
import argparse
import requests

API_KEY = "8ca5b7ba84282bf3c7a90ef9155f6ddf"
# Obtain the api key that was passed in from the command line
parser = argparse.ArgumentParser(description='Sample V4')
parser.add_argument('--api-key', type=str, default='')
args = parser.parse_args()

# Sport key
# Find sport keys from the /sports endpoint below, or from https://the-odds-api.com/sports-odds-data/sports-apis.html
# Alternatively use 'upcoming' to see the next 8 games across all sports
SPORT = 'mma_mixed_martial_arts'

# Bookmaker regions
# uk | us | us2 | eu | au. Multiple can be specified if comma delimited.
# More info at https://the-odds-api.com/sports-odds-data/bookmaker-apis.html
REGIONS = 'eu'

# Odds markets
# h2h | spreads | totals. Multiple can be specified if comma delimited
# More info at https://the-odds-api.com/sports-odds-data/betting-markets.html
# Note only featured markets (h2h, spreads, totals) are available with the odds endpoint.
MARKETS = 'totals'

# Odds format
# decimal | american
ODDS_FORMAT = 'decimal'

# Date format
# iso | unix
DATE_FORMAT = 'iso'

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
# Now get a list of live & upcoming games for the sport you want, along with odds for different bookmakers
# This will deduct from the usage quota
# The usage quota cost = [number of markets specified] x [number of regions specified]
# For examples of usage quota costs, see https://the-odds-api.com/liveapi/guides/v4/#usage-quota-costs
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

paris = requests.get(f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds', params={
    'api_key': API_KEY,
    'regions': REGIONS,
    'markets': MARKETS,
    'oddsFormat': ODDS_FORMAT
})

if paris.status_code != 200:
    print(f'Failed to get odds: status_code {paris.status_code}, response body {paris.text}')
else:
    paris_json = paris.json()

    for match in paris_json:
        home_team = match["home_team"]  # Fix: Access from each match object in the list
        away_team = match["away_team"]
        print(home_team, "vs", away_team)

        for bookmaker in match["bookmakers"]:
            nom_bookmaker = bookmaker["key"]
            print("Bookmaker:", nom_bookmaker)

            for market in bookmaker["markets"]:  # Fix: Iterate over the markets list
                market_key = market["key"]
                


    print('Remaining requests:', paris.headers.get('x-requests-remaining', 'N/A'))
    print('Used requests:', paris.headers.get('x-requests-used', 'N/A'))







