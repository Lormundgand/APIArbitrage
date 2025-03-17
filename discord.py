import os
import time
import json
import hashlib
import requests
import subprocess
import argparse
from datetime import datetime

# Configuration par défaut
DEFAULT_INTERVAL = 120  # 60 sec
DEFAULT_DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1351188640826658858/fXYj1BQNiEVWJzyTwdcImNfBhnwMd8lSi50PwMtVdwEIhD2WO8U8AbzvGXHkfox5mm4r"
DEFAULT_SPORTS = ""
DEFAULT_MIN_PROFIT = 1.0
DEFAULT_INVESTMENT = 100
DEFAULT_BOOKMAKERS = "betclic,Betsson,unibet,winamax,williamhill,888sport,betvictor,matchbook,Betfair,pinnacle,marathonbet,BetOnline.ag,1xbet,coolbet,betanysports,gtbets,mybookieag,Nordic Bet,everygame,suprabets,tipico_de"

# Analyse des arguments
parser = argparse.ArgumentParser(description='Bot d\'arbitrage sportif avec notifications Discord')
parser.add_argument('--interval', type=int, default=DEFAULT_INTERVAL, help='Intervalle entre les scans (secondes)')
parser.add_argument('--webhook', type=str, default=DEFAULT_DISCORD_WEBHOOK, help='URL du webhook Discord')
parser.add_argument('--sports', type=str, default=DEFAULT_SPORTS, help='Sports à scanner (séparés par des virgules)')
parser.add_argument('--min-profit', type=float, default=DEFAULT_MIN_PROFIT, help='Profit minimum en pourcentage')
parser.add_argument('--investment', type=float, default=DEFAULT_INVESTMENT, help='Montant d\'investissement')
parser.add_argument('--bookmakers', type=str, default=DEFAULT_BOOKMAKERS, 
                    help='Bookmakers à considérer (séparés par des virgules, en minuscules)')
args = parser.parse_args()

# Convertir la chaîne de bookmakers en liste
ALLOWED_BOOKMAKERS = [bk.strip().lower() for bk in args.bookmakers.split(',')]

# Fichier de stockage des opportunités déjà trouvées
OPPORTUNITIES_FILE = "opportunities_sent.json"

def load_sent_opportunities():
    """Charge les opportunités déjà envoyées"""
    if os.path.exists(OPPORTUNITIES_FILE):
        try:
            with open(OPPORTUNITIES_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_sent_opportunities(opportunities):
    """Enregistre les opportunités déjà envoyées"""
    with open(OPPORTUNITIES_FILE, 'w') as f:
        json.dump(opportunities, f)

def generate_opportunity_hash(opportunity):
    """Génère un hash unique pour une opportunité"""
    key_data = f"{opportunity['match']}_{opportunity['market']}"
    if 'point' in opportunity:
        key_data += f"_{opportunity['point']}"
    for outcome in opportunity['outcomes']:
        key_data += f"_{outcome['name']}_{outcome['bookmaker']}_{outcome['price']}"
    return hashlib.md5(key_data.encode()).hexdigest()

def send_discord_notification(webhook_url, opportunity):
    """Envoie une notification Discord pour une opportunité"""
    if not webhook_url:
        print("Aucune URL de webhook Discord fournie. Notification non envoyée.")
        return False
    
    # Formater la date et l'heure
    commence_time = datetime.fromisoformat(opportunity['commence_time'].replace('Z', '+00:00'))
    formatted_time = commence_time.strftime("%d-%m-%Y %H:%M")
    
    # Créer le message Discord
    message = {
        "username": "Arbitrage Bot",
        "avatar_url": "https://i.imgur.com/4M34hi2.png",
        "embeds": [{
            "title": f"Nouvelle opportunité d'arbitrage! {opportunity['profit_percentage']}% de profit",
            "color": 3066993,  # Vert
            "fields": [
                {"name": "Sport", "value": opportunity['sport'], "inline": True},
                {"name": "Match", "value": opportunity['match'], "inline": True},
                {"name": "Date", "value": formatted_time, "inline": True},
                {"name": "Marché", "value": opportunity['market'] + (f" (Point: {opportunity['point']})" if 'point' in opportunity else ""), "inline": True},
                {"name": "Profit", "value": f"{opportunity['profit_percentage']}%", "inline": True},
                {"name": "Retour attendu", "value": f"{opportunity['expected_return']}$", "inline": True}
            ],
            "description": "**Mises recommandées:**\n" + "\n".join([
                f"• Miser {outcome['stake']}$ sur {outcome['name']} avec {outcome['bookmaker']} (cote: {outcome['price']})"
                for outcome in opportunity['outcomes']
            ])
        }]
    }
    
    # Envoyer la notification
    response = requests.post(webhook_url, json=message)
    if response.status_code == 204:
        print(f"Notification envoyée avec succès pour {opportunity['match']} ({opportunity['profit_percentage']}%)")
        return True
    else:
        print(f"Échec de l'envoi de la notification: {response.status_code} - {response.text}")
        return False

def parse_opportunities_from_output(output):
    """Extrait les opportunités d'arbitrage du texte de sortie"""
    opportunities = []
    lines = output.split("\n")
    
    current_opp = None
    outcomes = []
    matches_analyzed = 0
    
    for line in lines:
        # Capture le nombre de matchs analysés
        if "Récupération des données pour" in line:
            matches_analyzed += 1
        
        if line.startswith("Opportunité #"):
            # Nouvelle opportunité
            if current_opp:
                current_opp["outcomes"] = outcomes
                opportunities.append(current_opp)
            
            # Initialiser la nouvelle opportunité
            parts = line.split(" - ")
            if len(parts) >= 3:
                current_opp = {
                    "sport": parts[1],
                    "profit_percentage": float(parts[2].replace("Profit: ", "").replace("%", ""))
                }
                outcomes = []
        
        elif line.startswith("Match: "):
            if current_opp:
                match_parts = line.replace("Match: ", "").split(" - ")
                current_opp["match"] = match_parts[0]
                if len(match_parts) > 1:
                    current_opp["commence_time"] = match_parts[1]
        
        elif line.startswith("Marché: "):
            if current_opp:
                market_line = line.replace("Marché: ", "")
                if "Point:" in market_line:
                    market_parts = market_line.split(" (Point: ")
                    current_opp["market"] = market_parts[0]
                    current_opp["point"] = float(market_parts[1].replace(")", ""))
                else:
                    current_opp["market"] = market_line
        
        elif line.strip().startswith("Miser "):
            parts = line.strip().split(" sur ")
            if len(parts) >= 2:
                stake = float(parts[0].replace("Miser ", "").replace("$", ""))
                name_parts = parts[1].split(" avec ")
                if len(name_parts) >= 2:
                    name = name_parts[0]
                    bookmaker_parts = name_parts[1].split(" (cote: ")
                    if len(bookmaker_parts) >= 2:
                        bookmaker = bookmaker_parts[0]
                        price = float(bookmaker_parts[1].replace(")", ""))
                        outcomes.append({
                            "name": name,
                            "bookmaker": bookmaker,
                            "price": price,
                            "stake": stake
                        })
        
        elif line.startswith("Retour attendu: "):
            if current_opp:
                parts = line.replace("Retour attendu: ", "").split("$ (")
                if len(parts) >= 2:
                    current_opp["expected_return"] = float(parts[0])
    
    # Ajouter la dernière opportunité
    if current_opp:
        current_opp["outcomes"] = outcomes
        opportunities.append(current_opp)
    
    return opportunities, matches_analyzed

def is_valid_bookmaker_opportunity(opportunity):
    """Vérifie si l'opportunité utilise uniquement les bookmakers autorisés"""
    if not opportunity or 'outcomes' not in opportunity:
        return False
    
    for outcome in opportunity['outcomes']:
        if 'bookmaker' not in outcome:
            return False
        
        # Vérifier si le bookmaker est dans la liste des bookmakers autorisés
        bookmaker_name = outcome['bookmaker'].lower()
        
        # Vérifier les correspondances partielles pour gérer les variations de noms
        if not any(allowed_bk in bookmaker_name or bookmaker_name in allowed_bk for allowed_bk in ALLOWED_BOOKMAKERS):
            return False
    
    return True

def run_arbitrage_scan():
    """Lance le scan des opportunités d'arbitrage"""
    # Construire la commande pour main.py
    cmd = [
        "python", "main.py",
        "--sport", "all",
        "--min-profit", str(args.min_profit),
        "--investment", str(args.investment)
    ]
    
    try:
        # Exécuter la commande
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Analyser la sortie
        opportunities, matches_analyzed = parse_opportunities_from_output(result.stdout)
        
        # Afficher le nombre de matchs analysés
        print(f"Nombre de matchs analysés: {matches_analyzed}")
        
        # Filtrer les opportunités par bookmakers
        filtered_opportunities = [opp for opp in opportunities if is_valid_bookmaker_opportunity(opp)]
        
        print(f"Opportunités trouvées: {len(opportunities)}")
        print(f"Opportunités avec bookmakers autorisés: {len(filtered_opportunities)}")
        
        # Charger les opportunités déjà envoyées
        sent_opportunities = load_sent_opportunities()
        
        # Variables pour statistiques
        new_opportunities = 0
        
        # Traiter les nouvelles opportunités
        for opp in filtered_opportunities:
            opp_hash = generate_opportunity_hash(opp)
            
            # Vérifier si l'opportunité a déjà été envoyée
            if opp_hash not in sent_opportunities:
                # Envoyer une notification
                if send_discord_notification(args.webhook, opp):
                    # Marquer comme envoyée
                    sent_opportunities[opp_hash] = {
                        "timestamp": datetime.now().isoformat(),
                        "match": opp["match"],
                        "profit": opp["profit_percentage"]
                    }
                    new_opportunities += 1
        
        # Sauvegarder les opportunités envoyées
        save_sent_opportunities(sent_opportunities)
        
        # Afficher un résumé
        print(f"Nouvelles opportunités envoyées: {new_opportunities}")
        
    except Exception as e:
        print(f"Erreur lors du scan: {str(e)}")

def main():
    print(f"Bot d'arbitrage démarré avec un intervalle de {args.interval} secondes")
    print(f"Webhook Discord: {'Configuré' if args.webhook else 'Non configuré'}")
    print(f"Profit minimum: {args.min_profit}%")
    print(f"Investissement: {args.investment}$")
    print(f"Bookmakers autorisés: {', '.join(ALLOWED_BOOKMAKERS)}")
    
    while True:
        try:
            print(f"\n--- Scan démarré à {datetime.now().strftime('%H:%M:%S')} ---")
            run_arbitrage_scan()
            print(f"--- Scan terminé à {datetime.now().strftime('%H:%M:%S')} ---")
            print(f"Prochain scan dans {args.interval} secondes...")
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nBot d'arbitrage arrêté.")
            break
        except Exception as e:
            print(f"Erreur inattendue: {str(e)}")
            print("Nouvelle tentative dans 60 secondes...")
            time.sleep(60)

if __name__ == "__main__":
    main()