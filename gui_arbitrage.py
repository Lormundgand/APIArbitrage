import tkinter as tk
from tkinter import ttk
import subprocess
import json
import os
import sys

class ArbitrageDetectorApp:
    def __init__(self, master):
        self.master = master
        master.title("Détecteur d'Opportunités d'Arbitrage")
        master.geometry("800x600")

        # Configuration initiale
        self.sports_list = ['mma_mixed_martial_arts', 'boxing', 'soccer_uefa_champions_league', 'basketball_nba', 'tennis_atp']
        self.regions_list = ['eu', 'us', 'uk', 'au']
        self.markets_list = ['h2h', 'totals']

        # Créer les frames principales
        self.create_filter_frame()
        self.create_results_frame()

    def create_filter_frame(self):
        filter_frame = ttk.LabelFrame(self.master, text="Filtres")
        filter_frame.pack(padx=10, pady=10, fill='x')

        # Sport
        ttk.Label(filter_frame, text="Sports:").grid(row=0, column=0, sticky='w')
        self.sports_var = tk.StringVar(value=self.sports_list)
        self.sports_listbox = tk.Listbox(filter_frame, selectmode=tk.MULTIPLE, height=5)
        for sport in self.sports_list:
            self.sports_listbox.insert(tk.END, sport)
        self.sports_listbox.grid(row=0, column=1, padx=5, pady=5)

        # Regions
        ttk.Label(filter_frame, text="Régions:").grid(row=1, column=0, sticky='w')
        self.regions_var = tk.StringVar(value='eu')
        regions_dropdown = ttk.Combobox(filter_frame, textvariable=self.regions_var, values=self.regions_list)
        regions_dropdown.grid(row=1, column=1, padx=5, pady=5)

        # Marchés
        ttk.Label(filter_frame, text="Marchés:").grid(row=2, column=0, sticky='w')
        self.markets_var = tk.StringVar(value=','.join(self.markets_list))
        markets_entry = ttk.Entry(filter_frame, textvariable=self.markets_var)
        markets_entry.grid(row=2, column=1, padx=5, pady=5)

        # Paramètres supplémentaires
        ttk.Label(filter_frame, text="Min Profit (%):").grid(row=3, column=0, sticky='w')
        self.min_profit_var = tk.DoubleVar(value=1.0)
        min_profit_entry = ttk.Entry(filter_frame, textvariable=self.min_profit_var)
        min_profit_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(filter_frame, text="Investissement ($):").grid(row=4, column=0, sticky='w')
        self.investment_var = tk.DoubleVar(value=100)
        investment_entry = ttk.Entry(filter_frame, textvariable=self.investment_var)
        investment_entry.grid(row=4, column=1, padx=5, pady=5)

        # Bouton de recherche
        search_button = ttk.Button(filter_frame, text="Rechercher Opportunités", command=self.search_opportunities)
        search_button.grid(row=5, column=0, columnspan=2, pady=10)

    def create_results_frame(self):
        self.results_frame = ttk.LabelFrame(self.master, text="Opportunités d'Arbitrage")
        self.results_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.results_tree = ttk.Treeview(self.results_frame, columns=('Sport', 'Match', 'Profit', 'Retour', 'Détails'), show='headings')
        self.results_tree.heading('Sport', text='Sport')
        self.results_tree.heading('Match', text='Match')
        self.results_tree.heading('Profit', text='Profit (%)')
        self.results_tree.heading('Retour', text='Retour ($)')
        self.results_tree.heading('Détails', text='Détails')
        
        self.results_tree.pack(fill='both', expand=True)
        self.results_tree.bind('<Double-1>', self.show_opportunity_details)

    def search_opportunities(self):
        # Effacer résultats précédents
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Préparer les arguments
        selected_sports = list(map(self.sports_listbox.get, self.sports_listbox.curselection())) or self.sports_list
        
        # Construction des arguments pour le script original
        cmd = [
            sys.executable,  # Utiliser le même interpréteur Python
            'mian.py',  # Nom du script original
            '--sport', ','.join(selected_sports),
            '--regions', self.regions_var.get(),
            '--markets', self.markets_var.get(),
            '--min-profit', str(self.min_profit_var.get()),
            '--investment', str(self.investment_var.get())
        ]

        try:
            # Exécuter le script et capturer la sortie
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Chercher les opportunités dans la sortie
            opportunities = self.parse_opportunities(result.stdout)
            
            # Afficher les résultats
            for opp in opportunities:
                self.results_tree.insert('', 'end', values=(
                    opp['sport'], 
                    opp['match'], 
                    f"{opp['profit_percentage']:.2f}", 
                    f"{opp['expected_return']:.2f}",
                    f"{len(opp['outcomes'])} bookmakers"
                ), tags=('opportunity',))
            
            # Colorier les lignes selon le profit
            self.results_tree.tag_configure('opportunity', background='#e6f2e6')
            
        except Exception as e:
            tk.messagebox.showerror("Erreur", str(e))

    def parse_opportunities(self, output):
        # Trouver le bloc des opportunités
        start_marker = '=== OPPORTUNITÉS D\'ARBITRAGE DÉTECTÉES ==='
        start_index = output.find(start_marker)
        
        if start_index == -1:
            return []
        
        # Extraire le texte après le marker
        opportunities_text = output[start_index + len(start_marker):].strip()
        
        # Parser manuellement (simplification)
        opportunities = []
        current_opp = None
        
        for line in opportunities_text.split('\n'):
            line = line.strip()
            if line.startswith('Opportunité #'):
                if current_opp:
                    opportunities.append(current_opp)
                current_opp = self.parse_opportunity_header(line)
            elif current_opp and line.startswith('Miser'):
                self.parse_opportunity_bet(current_opp, line)
        
        # Ajouter la dernière opportunité
        if current_opp:
            opportunities.append(current_opp)
        
        return opportunities

    def parse_opportunity_header(self, line):
        # Exemple: "Opportunité #1 - MMA - Profit: 3.5%"
        parts = line.split(' - ')
        return {
            'sport': parts[1],
            'profit_percentage': float(parts[2].split(': ')[1].rstrip('%')),
            'outcomes': []
        }

    def parse_opportunity_bet(self, opportunity, line):
        # Exemple: "Miser 97.56$ sur Team1 avec Bookmaker1 (cote: 2.1)"
        opportunity['outcomes'].append(line)

    def show_opportunity_details(self, event):
        # Afficher les détails complets de l'opportunité sélectionnée
        selected_item = self.results_tree.selection()[0]
        details = self.results_tree.item(selected_item)['values']
        
        details_window = tk.Toplevel(self.master)
        details_window.title(f"Détails de l'opportunité - {details[1]}")
        details_window.geometry("500x300")
        
        details_text = tk.Text(details_window, wrap=tk.WORD)
        details_text.pack(fill='both', expand=True)
        
        # TODO: Implémenter l'affichage des détails complets

def main():
    root = tk.Tk()
    app = ArbitrageDetectorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()