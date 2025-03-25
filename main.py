import json
from datetime import datetime
import statistics
import argparse
import requests

# Configuration API
API_KEY = "8ca5b7ba84282bf3c7a90ef9155f6ddf" #royer.oscar
API_KEY = "1a31f587893f36107eef4cc74960d0f2" #royer.oscar2
parser = argparse.ArgumentParser(description='Détecteur d\'opportunités d\'arbitrage de paris sportifs')
parser.add_argument('--api-key', type=str, default=API_KEY, help='API key pour The Odds API')
parser.add_argument('--regions', type=str, default='eu', help='Régions des bookmakers')
parser.add_argument('--markets', type=str, default='totals', help='Marchés à analyser')
parser.add_argument('--min-profit', type=float, default=1.0, help='Gain minimal en pourcentage')
parser.add_argument('--investment', type=float, default=100, help='Montant d\'investissement en dollars')
args = parser.parse_args()

def get_all_sports():
    """Récupère la liste des sports disponibles depuis l'API"""
    response = requests.get(f'https://api.the-odds-api.com/v4/sports', params={'apiKey': API_KEY})
    
    if response.status_code != 200:
        print(f"Erreur lors de la récupération des sports : {response.status_code} - {response.text}")
        return []
    
    sports_data = response.json()
    return [sport['key'] for sport in sports_data]  # On extrait uniquement les clés des sports


# Liste des sports à analyser
# SPORTS = ["boxing_boxing", "mma_mixed_martial_arts", "americanfootball_nfl", "icehockey_nhl"]
SPORTS = ['americanfootball_nfl', 'americanfootball_cfl', 'baseball_mlb', 'basketball_nba', 'boxing_boxing', 'icehockey_nhl', 'icehockey_ahl', 'mma_mixed_martial_arts', 'rugbyleague_nrl']
# Configuration des paramètres
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
            print("\najoute un sport\n")
            match_id = match['id']
            home_team = match['home_team']
            away_team = match['away_team']
            commence_time = match['commence_time']
            
            # Pour les marchés h2h
            if 'h2h' in MARKETS:
                # Collecter toutes les cotes disponibles pour home et away
                home_odds = []
                away_odds = []
                
                for bookmaker in match['bookmakers']:
                    bookmaker_name = bookmaker['title']
                    
                    for market in bookmaker['markets']:
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home_team:
                                    home_odds.append({
                                        'bookmaker': bookmaker_name,
                                        'price': outcome['price']
                                    })
                                elif outcome['name'] == away_team:
                                    away_odds.append({
                                        'bookmaker': bookmaker_name,
                                        'price': outcome['price']
                                    })
                
                # Trouver les meilleures combinaisons de cotes entre bookmakers différents
                for home in home_odds:
                    for away in away_odds:
                        # Vérifier que les bookmakers sont différents
                        if home['bookmaker'] != away['bookmaker']:
                            arb = calculate_arbitrage(
                                [home['price'], away['price']],
                                [home['bookmaker'], away['bookmaker']]
                            )
                            
                            if arb:
                                opportunities.append({
                                    'sport': sport_title,
                                    'match': f"{home_team} vs {away_team}",
                                    'commence_time': commence_time,
                                    'market': 'h2h',
                                    'outcomes': [
                                        {'name': home_team, 'bookmaker': home['bookmaker'], 'price': home['price'], 'stake': arb['optimal_bets'][0]},
                                        {'name': away_team, 'bookmaker': away['bookmaker'], 'price': away['price'], 'stake': arb['optimal_bets'][1]}
                                    ],
                                    'profit_percentage': arb['profit_percentage'],
                                    'expected_return': arb['expected_return']
                                })
            
            # Pour les marchés totals
            if 'totals' in MARKETS:
                # Collecter toutes les cotes disponibles pour over et under par point
                totals_odds = {}
                
                for bookmaker in match['bookmakers']:
                    bookmaker_name = bookmaker['title']
                    
                    for market in bookmaker['markets']:
                        if market['key'] == 'totals':
                            for outcome in market['outcomes']:
                                if 'point' in outcome:
                                    point = outcome['point']
                                    if point not in totals_odds:
                                        totals_odds[point] = {'over': [], 'under': []}
                                    
                                    if outcome['name'] == 'Over':
                                        totals_odds[point]['over'].append({
                                            'bookmaker': bookmaker_name,
                                            'price': outcome['price']
                                        })
                                    elif outcome['name'] == 'Under':
                                        totals_odds[point]['under'].append({
                                            'bookmaker': bookmaker_name,
                                            'price': outcome['price']
                                        })
                
                # Vérifier chaque point pour des opportunités d'arbitrage
                for point, odds in totals_odds.items():
                    for over in odds['over']:
                        for under in odds['under']:
                            # Vérifier que les bookmakers sont différents
                            if over['bookmaker'] != under['bookmaker']:
                                arb = calculate_arbitrage(
                                    [over['price'], under['price']],
                                    [over['bookmaker'], under['bookmaker']]
                                )
                                
                                if arb:
                                    opportunities.append({
                                        'sport': sport_title,
                                        'match': f"{home_team} vs {away_team}",
                                        'commence_time': commence_time,
                                        'market': 'totals',
                                        'point': point,
                                        'outcomes': [
                                            {'name': 'Over', 'bookmaker': over['bookmaker'], 'price': over['price'], 'stake': arb['optimal_bets'][0]},
                                            {'name': 'Under', 'bookmaker': under['bookmaker'], 'price': under['price'], 'stake': arb['optimal_bets'][1]}
                                        ],
                                        'profit_percentage': arb['profit_percentage'],
                                        'expected_return': arb['expected_return']
                                    })
    
    # Trier les opportunités par pourcentage de profit décroissant
    opportunities.sort(key=lambda x: x['profit_percentage'], reverse=True)
    return opportunities

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