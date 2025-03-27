import json
from datetime import datetime
import statistics
import argparse
import requests
import itertools

# Configuration API
API_KEY = "8ca5b7ba84282bf3c7a90ef9155f6ddf" #oscar.ai 
API_KEY = "1a31f587893f36107eef4cc74960d0f2" #royer.oscar2
API_KEY = "a3426a5c3481393d3f4fb725f1b517d2" #royer.oscar

parser = argparse.ArgumentParser(description='Détecteur d\'opportunités d\'arbitrage de paris sportifs')
parser.add_argument('--api-key', type=str, default=API_KEY, help='API key pour The Odds API')
parser.add_argument('--regions', type=str, default='eu', help='Régions des bookmakers')
parser.add_argument('--markets', type=str, default='totals,h2h,spreads', help='Marchés à analyser')
parser.add_argument('--min-profit', type=float, default=1.0, help='Gain minimal en pourcentage')
parser.add_argument('--investment', type=float, default=100, help='Montant d\'investissement en dollars')
args = parser.parse_args()

# Liste des sports à analyser
SPORTS = ['mma_mixed_martial_arts','boxing_boxing', 'americanfootball_nfl','icehockey_nhl']
SPORTS = [
'americanfootball_nfl',
'americanfootball_cfl',
'americanfootball_ncaaf',
'basketball_nba',
'basketball_euroleague',
'basketball_wnba',
'basketball_ncaab',
'baseball_mlb',
'icehockey_nhl',
'soccer_epl',
'soccer_spain_la_liga',
'soccer_germany_bundesliga',
'soccer_italy_serie_a',
'soccer_france_ligue_one',
'soccer_uefa_champs_league',
'soccer_uefa_europa_league',
'soccer_fifa_world_cup',
'soccer_conmebol_copa_america',
'soccer_usa_mls',
'soccer_brazil_campeonato',
'soccer_mexico_ligamx',
'tennis_atp_aus_open_singles',
'tennis_atp_french_open',
'tennis_atp_us_open',
'tennis_atp_wimbledon',
'tennis_wta_aus_open_singles',
'tennis_wta_french_open',
'tennis_wta_us_open',
'tennis_wta_wimbledon',
'mma_mixed_martial_arts',
'boxing_boxing'
]
SPORTS = ['icehockey_sweden_hockey_league']
REGIONS = args.regions
MARKETS = args.markets
ODDS_FORMAT = 'decimal'
DATE_FORMAT = 'iso'
MIN_PROFIT = args.min_profit / 100  # Convertir en décimal
INVESTMENT = args.investment

def calculate_arbitrage(odds_list, bookmakers):
    """
    Calcule si un arbitrage est possible et les mises optimales
    
    Args:
        odds_list: Liste des cotes
        bookmakers: Liste des bookmakers correspondants
    
    Returns:
        Dictionnaire contenant les informations de l'arbitrage ou None si pas d'opportunité
    """
    if not odds_list or len(odds_list) < 2:
        return None
    
    # Vérifier que les bookmakers sont différents
    if len(set(bookmakers)) != len(bookmakers):
        return None
    
    # Calculer la somme des inverses des cotes
    sum_inverse_odds = sum(1/odds for odds in odds_list)
    
    # Si la somme est inférieure à 1, il y a une opportunité d'arbitrage
    if sum_inverse_odds < 1:
        profit_percentage = (1/sum_inverse_odds - 1) * 100
        
        # Vérifier si le profit est supérieur au seuil minimal
        if profit_percentage/100 >= MIN_PROFIT:
            # Calculer les mises optimales pour chaque bookmaker
            optimal_bets = []
            for odds in odds_list:
                stake = INVESTMENT * (1/odds) / sum_inverse_odds
                optimal_bets.append(round(stake, 2))
            
            return {
                'profit_percentage': round(profit_percentage, 2),
                'optimal_bets': optimal_bets,
                'expected_return': round(INVESTMENT * (1/sum_inverse_odds), 2)
            }
    
    return None

def find_arbitrage_opportunities(sports_data):
    """Trouve les opportunités d'arbitrage dans les données des sports"""
    opportunities = []
    
    for sport in sports_data:
        sport_key = sport['sport_key']
        sport_title = sport['sport_title']
        
        for match in sport['matches']:
            match_id = match['id']
            home_team = match['home_team']
            away_team = match['away_team']
            commence_time = match['commence_time']
            
            if 'h2h' in MARKETS:
                h2h_odds = {}
                for bookmaker in match['bookmakers']:
                    for match_par_marche in bookmaker['markets']:
                        outcomes = match_par_marche['outcomes']
                        if len(outcomes) == 2:
                            #c'est un match a 2 issues
                            nom1 = outcome[0]["name"]
                            cote1 = outcome[0]["price"]
                            nom2 = outcome[1]["name"]
                            cote2 = outcome[1]["price"]

                        if len(outcomes) == 3:
                            #c'est un match à 3 issues
                            nom1 = outcome[0]["name"]
                            cote1 = outcome[0]["price"]
                            nom2 = outcome[1]["name"]
                            cote2 = outcome[1]["price"]
                            nom2 = outcome[2]["name"]
                            cote2 = outcome[2]["price"]
                    



            # Pour les marchés spreads
            if 'spreads' in MARKETS:
                # Collecter toutes les cotes disponibles pour spreads
                spreads_odds = {}
                
                for bookmaker in match['bookmakers']:
                    bookmaker_name = bookmaker['title']
                    
                    for market in bookmaker['markets']:
                        if market['key'] == 'spreads':
                            for outcome in market['outcomes']:
                                if 'point' in outcome:
                                    point = outcome['point']
                                    team = outcome['name']
                                    
                                    if point not in spreads_odds:
                                        spreads_odds[point] = {}
                                    
                                    spreads_odds[point][team] = spreads_odds[point].get(team, []) + [{
                                        'bookmaker': bookmaker_name,
                                        'price': outcome['price']
                                    }]
                
                # Vérifier chaque point de spread pour des opportunités d'arbitrage
                for point, teams in spreads_odds.items():
                    # Générer des combinaisons pour tous les outcomes disponibles
                    team_names = list(teams.keys())
                    
                    for num_teams in range(2, len(team_names) + 1):
                        for team_combo in itertools.combinations(range(len(team_names)), num_teams):
                            # Collecter les cotes pour ces équipes
                            combo_odds = []
                            combo_outcomes = []
                            combo_bookmakers = []
                            
                            # Générer toutes les combinaisons de bookmakers pour ces équipes
                            for i in team_combo:
                                for odds in teams[team_names[i]]:
                                    combo_odds.append(odds['price'])
                                    combo_outcomes.append(team_names[i])
                                    combo_bookmakers.append(odds['bookmaker'])
                            
                            # Vérifier que les bookmakers sont tous différents
                            if len(set(combo_bookmakers)) == len(combo_bookmakers):
                                # Calculer l'arbitrage
                                arb = calculate_arbitrage(combo_odds, combo_bookmakers)
                                
                                if arb and len(combo_outcomes) >= 2:
                                    # Préparer les détails de l'opportunité
                                    outcomes_details = [
                                        {
                                            'name': combo_outcomes[j], 
                                            'bookmaker': combo_bookmakers[j], 
                                            'price': combo_odds[j], 
                                            'stake': arb['optimal_bets'][j]
                                        } for j in range(len(combo_outcomes))
                                    ]
                                    
                                    opportunities.append({
                                        'sport': sport_title,
                                        'match': f"{home_team} vs {away_team}",
                                        'commence_time': commence_time,
                                        'market': 'spreads',
                                        'point': point,
                                        'outcomes': outcomes_details,
                                        'profit_percentage': arb['profit_percentage'],
                                        'expected_return': arb['expected_return']
                                    })
    
    # Trier les opportunités par pourcentage de profit décroissant
    opportunities.sort(key=lambda x: x['profit_percentage'], reverse=True)
    return opportunities

def get_all_sports():
    """Récupère la liste des sports disponibles depuis l'API"""
    response = requests.get(f'https://api.the-odds-api.com/v4/sports', params={'apiKey': API_KEY})
    
    if response.status_code != 200:
        print(f"Erreur lors de la récupération des sports : {response.status_code} - {response.text}")
        return []
    
    sports_data = response.json()
    return [sport['key'] for sport in sports_data]

def main():
    all_sports_data = []
    
    for sport in SPORTS:
        print(f"Récupération des données pour {sport}...")
        
        # Requête API pour obtenir les cotes
        response = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/odds', params={
            'api_key': args.api_key,
            'regions': REGIONS,
            'markets': MARKETS,
            'oddsFormat': ODDS_FORMAT,
            'dateFormat': DATE_FORMAT
        })
        
        print('Remaining requests', response.headers['x-requests-remaining'])
        print('Used requests', response.headers['x-requests-used'])
        
        if response.status_code != 200:
            print(f'Échec de récupération des cotes pour {sport}: status_code {response.status_code}, réponse {response.text}')
            continue
        
        data = response.json()
        # print(data)
        
        if data:
            all_sports_data.append({
                'sport_key': sport,
                'sport_title': data[0]['sport_title'] if data else sport,
                'matches': data
            })
            
            print(f'Requêtes restantes: {response.headers.get("x-requests-remaining", "N/A")}')
            print(f'Requêtes utilisées: {response.headers.get("x-requests-used", "N/A")}')
        else:
            print(f"Aucune donnée disponible pour {sport}")
    
    # Rechercher les opportunités d'arbitrage
    opportunities = find_arbitrage_opportunities(all_sports_data)
    
    # Afficher les résultats
    if opportunities:
        print("\n=== OPPORTUNITÉS D'ARBITRAGE DÉTECTÉES ===")
        for i, opp in enumerate(opportunities, 1):
            print(f"\nOpportunité #{i} - {opp['sport']} - Profit: {opp['profit_percentage']}%")
            print(f"Match: {opp['match']} - {opp['commence_time']}")
            print(f"Marché: {opp['market']}" + (f" (Point: {opp['point']})" if 'point' in opp else ""))
            print("Mises recommandées:")
            for outcome in opp['outcomes']:
                print(f"  Miser {outcome['stake']}$ sur {outcome['name']} avec {outcome['bookmaker']} (cote: {outcome['price']})")
            print(f"Investissement total: {sum(o['stake'] for o in opp['outcomes'])}$")
            print(f"Retour attendu: {opp['expected_return']}$ ({opp['profit_percentage']}% de profit)")
    else:
        print("\nAucune opportunité d'arbitrage détectée avec un profit minimum de", MIN_PROFIT * 100, "%")

if __name__ == "__main__":
    main()