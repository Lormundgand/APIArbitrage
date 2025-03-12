import numpy as np
import matplotlib.pyplot as plt

# Paramètres de l'ADC
n_bits = 8  # Résolution de l'ADC (8 bits -> 256 niveaux)
V_ref_min = 0  # Tension de référence basse
V_ref_max = 5  # Tension de référence haute
levels = 2**n_bits  # Nombre de niveaux de quantification
LSB = (V_ref_max - V_ref_min) / levels  # Poids du LSB

# Générer les points de la courbe en escalier
V_in = np.linspace(V_ref_min, V_ref_max, 1000)  # Signal analogique d'entrée
V_out = np.floor((V_in - V_ref_min) / LSB) * LSB + V_ref_min  # Quantification

# Tracé de la fonction de transfert
plt.figure(figsize=(8, 6))
plt.step(V_in, V_out, where='post', linewidth=2, label="Transfert ADC (8 bits)")
plt.xlabel("Tension d'entrée (V)")
plt.ylabel("Sortie numérique quantifiée (V)")
plt.title("Fonction de transfert d'un ADC en escalier")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.show()
