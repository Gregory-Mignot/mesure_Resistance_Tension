# main.py

import pyvisa
import time
import numpy as np
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import configparser
import traceback
import importlib

# Variables globales
delais = 0.1  # Délai par défaut entre les mesures (secondes)
titre_graph = "Résistance en fonction de la tension"
abcisse = "Tension (V)"
ordonnee = "Résistance (Ω)"
interrupt_event = threading.Event()  # Événement pour interrompre les mesures
data_res = np.array([])  # Données de résistance
data_tension = np.array([])  # Données de tension mesurée
data_consigne = np.array([])  # Données de tension de consigne
data_delai = np.array([])  # Données de délai appliqué
data_complete = None  # Stockage complet des données pour l'exportation
first_measurement_point = True  # Premier point de mesure du cycle complet

# Chargement de la configuration depuis config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Paramètres de l'alimentation électrique
alim_class_name = config['Alimentation']['classe']
alim_address = config['Alimentation']['address']
volt_max = float(config['Alimentation']['volt_max'])
curr_max = float(config['Alimentation']['curr_max'])
curr_prot_lev = float(config['Alimentation']['curr_prot_lev'])

# Paramètres du multimètre
meter_class_name = config['Meter']['classe']
meter_gpib = config['Meter']['gpib_address']

# Paramètres de formatage des données
decimal_separator = config['General']['decimal_separator']
column_separator = config['General']['column_separator']

# Importation dynamique des classes
alim_module = importlib.import_module('alimentation')
meter_module = importlib.import_module('appareil_mesure')
alim_class = getattr(alim_module, alim_class_name)
meter_class = getattr(meter_module, meter_class_name)

# Initialisation des instruments
power_supply = alim_class(alim_address, volt_max, curr_max, curr_prot_lev)
meter = meter_class(meter_gpib)

def load_config():
    """
    Charge les valeurs des champs de saisie depuis le fichier config.ini.
    Remplit les champs de l'interface utilisateur avec les valeurs configurées.

    Si certaines clés sont manquantes, laisse les champs vides.
    """
    try:
        entry_v1.insert(0, config['Mesure']['v1'])  # Tension initiale
        entry_v2.insert(0, config['Mesure']['v2'])  # Tension finale
        entry_step.insert(0, config['Mesure']['step'])  # Pas de tension
        entry_delay.insert(0, config['Mesure']['delay'])  # Délai standard
        entry_final_delay.insert(0, config['Mesure']['final_delay'])  # Délai aux points extrêmes
        hysteresis_var.set(config.getboolean('Mesure', 'hysteresis'))  # Hystérésis
    except KeyError:
        pass  # Si les clés n'existent pas, ne rien faire


def save_config():
    """
    Sauvegarde les valeurs des champs de saisie dans le fichier config.ini.
    Stocke les paramètres actuels pour une utilisation future.
    """
    config['Mesure'] = {
        'v1': entry_v1.get(),  # Tension initiale
        'v2': entry_v2.get(),  # Tension finale
        'step': entry_step.get(),  # Pas de tension
        'delay': entry_delay.get(),  # Délai standard
        'final_delay': entry_final_delay.get(),  # Délai aux points extrêmes
        'hysteresis': str(hysteresis_var.get())  # Hystérésis
    }
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def start():
    """
    Gère le démarrage et l'arrêt des mesures.

    Comportements:
    - Si le bouton indique "Démarrer les mesures" ou "Lancer une nouvelle mesure":
      * Initialise l'alimentation
      * Réinitialise le graphique et les données si nécessaire
      * Démarre les mesures dans un thread séparé
      * Change le texte du bouton en "Arrêter les mesures"

    - Si le bouton indique "Arrêter les mesures":
      * Interrompt les mesures en cours
      * Sécurise l'alimentation
      * Change le texte du bouton en "Lancer une nouvelle mesure"
    """
    global data_res, data_tension, data_consigne, data_delai, interrupt_event, first_measurement_point

    current_text = btn_start.cget("text")

    if current_text == "   Démarrer les mesures   " or current_text == "   Lancer une nouvelle mesure   ":
        try:
            # Réinitialisation de l'alimentation
            power_supply.initialize()

            # Réinitialisation pour nouvelle mesure
            if current_text == "   Lancer une nouvelle mesure   ":
                reset_graph()  # Réinitialiser le graphique et les données

            # Préparation pour la mesure
            interrupt_event.clear()  # Réinitialiser l'événement d'interruption
            first_measurement_point = True  # Premier point de mesure
            save_config()  # Sauvegarder la configuration

            # Lancement des mesures dans un thread séparé
            measurement_thread = threading.Thread(target=measure_resistance)
            measurement_thread.start()

            # Mise à jour du bouton
            btn_start.config(text="   Arrêter les mesures   ")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du démarrage de la mesure: {e}")

    elif current_text == "   Arrêter les mesures   ":
        # Arrêt des mesures
        interrupt_event.set()  # Signaler l'interruption
        secure_power_supply()  # Sécuriser l'alimentation
        btn_start.config(text="   Lancer une nouvelle mesure   ")  # Mise à jour du bouton

def reset_graph():
    """
    Réinitialise le graphique et les tableaux de données.

    Opérations:
    - Vide tous les tableaux de données
    - Efface le graphique
    - Redéfinit les titres et labels
    - Redessine le canevas vide
    """
    global data_res, data_tension, data_consigne, data_delai

    # Réinitialisation des tableaux de données
    data_res = np.array([])
    data_tension = np.array([])
    data_consigne = np.array([])
    data_delai = np.array([])

    # Réinitialisation du graphique
    ax.clear()
    ax.set_title(titre_graph)
    ax.set_xlabel(abcisse)
    ax.set_ylabel(ordonnee)
    canvas.draw()  # Redessiner le canevas

def secure_power_supply():
    """
    Remet l'alimentation électrique en état sécurisé.

    Opérations:
    - Désactivation de la sortie
    - Remise à zéro de la tension
    - Effacement des erreurs
    - Retour au mode local

    Gère les erreurs éventuelles et affiche un message si nécessaire.
    """
    power_supply.securiser()

def clean_response(response):
    """
    Nettoie une réponse d'instrument pour obtenir une valeur exploitable.

    Opérations:
    - Suppression des espaces en début et fin
    - Remplacement des séparateurs décimaux selon la configuration
    - Extraction de la première ligne si plusieurs lignes

    Args:
        response (str): La réponse brute de l'instrument

    Returns:
        str: La réponse nettoyée
    """
    response = response.strip()  # Suppression des espaces et caractères de fin de ligne
    response = response.replace(',', decimal_separator)  # Adaptation du séparateur décimal
    response = response.split('\n')[0]  # Première ligne uniquement
    return response

def generate_sequence(v1, v2, step):
    """
    Génère une séquence de tensions entre v1 et v2 avec un pas donné.

    Gère à la fois les rampes croissantes et décroissantes.
    Respecte la précision décimale du pas spécifié.

    Args:
        v1 (float): Tension de départ
        v2 (float): Tension finale
        step (float): Pas de tension (valeur absolue utilisée)

    Returns:
        list: Séquence de tensions avec le pas spécifié
    """
    sequence = []
    # Détermination du nombre de décimales pour les arrondis
    decimal_places = len(str(step).split('.')[1]) if '.' in str(step) else 0

    # Initialisation avec la tension de départ (arrondie)
    current_voltage = round(v1, decimal_places)

    # Génération de la séquence selon le sens (croissant ou décroissant)
    if v1 <= v2:  # Séquence croissante
        while current_voltage <= v2:
            sequence.append(current_voltage)
            current_voltage = round(current_voltage + abs(step), decimal_places)
    else:  # Séquence décroissante
        while current_voltage >= v2:
            sequence.append(current_voltage)
            current_voltage = round(current_voltage - abs(step), decimal_places)

    # Ajout de la tension finale si elle n'est pas déjà dans la séquence
    if sequence and sequence[-1] != v2:
        sequence.append(round(v2, decimal_places))

    return sequence

def insert_zero_at_polarity_changes(sequence):
    """
    Insère des points à 0V lors des changements de polarité dans la séquence.

    Cette fonction est cruciale pour permettre à l'utilisateur d'inverser les
    connexions lors du passage de tensions positives à négatives ou vice-versa.

    Args:
        sequence (list): Séquence de tensions originale

    Returns:
        list: Séquence avec points 0V insérés aux changements de polarité
    """
    result = []

    for i in range(len(sequence)):
        # Ajout du point courant
        result.append(sequence[i])

        # Vérification du changement de signe au point suivant
        if i < len(sequence) - 1:
            current = sequence[i]
            next_val = sequence[i+1]

            # S'il y a un changement de signe et que le point actuel n'est pas déjà 0
            if (current > 0 and next_val < 0) or (current < 0 and next_val > 0):
                if current != 0 and next_val != 0:  # Éviter les doublons de 0
                    # Insérer un point à 0V
                    result.append(0.0)

    return result

def measure_resistance():
    """
    Fonction principale qui effectue les mesures de résistance en fonction de la tension.

    Processus:
    1. Récupère les paramètres des champs de saisie
    2. Génère la séquence de tensions appropriée (avec/sans hystérésis)
    3. Insère des points à 0V aux changements de polarité
    4. Parcourt la séquence et pour chaque point:
       - Applique la tension
       - Attend le délai de stabilisation
       - Effectue les mesures (tension, courant, résistance)
       - Met à jour l'interface et le graphique
    5. Sécurise l'alimentation à la fin

    Gère les cas spéciaux:
    - Points à 0V pour permettre l'inversion des connexions
    - Délais différents aux points extrêmes
    - Interruption des mesures

    Les données sont stockées pour l'analyse et l'exportation.
    """
    global delais, data_res, data_tension, data_consigne, data_delai, data_complete, first_measurement_point
    try:
        # Récupération des paramètres
        v1 = float(entry_v1.get())
        v2 = float(entry_v2.get())
        step = float(entry_step.get())
        delay = float(entry_delay.get())
        final_delay = float(entry_final_delay.get())

        # Génération des séquences selon le mode (simple ou hystérésis)
        if hysteresis_var.get():
            if v1 >= v2:
                messagebox.showerror("Erreur", "Pour l'hystérésis, v1 doit être inférieur à v2.")
                return

            # Génération du cycle d'hystérésis complet (quadrants I, II, III, IV)
            sequence = generate_sequence(v1, v2, step)  # Quadrant I: v1 → v2
            sequence += generate_sequence(v2, v1, -step)[1:]  # Quadrant II: v2 → v1 (sans doublon)
            sequence += generate_sequence(v1, -v2, -step)[1:]  # Quadrant III: v1 → -v2 (sans doublon)
            sequence += generate_sequence(-v2, v1, step)[1:]  # Quadrant IV: -v2 → v1 (sans doublon)
        else:
            # Séquence simple de v1 à v2
            sequence = generate_sequence(v1, v2, step)

        # Insertion des points à 0V aux changements de polarité
        sequence = insert_zero_at_polarity_changes(sequence)
        print("Séquence avec points 0V aux changements de polarité:", sequence)

        # Réinitialisation des tableaux de données
        data_res = np.array([])  # Résistance mesurée
        data_tension = np.array([])  # Tension mesurée
        data_consigne = np.array([])  # Tension de consigne
        data_delai = np.array([])  # Délai appliqué

        # Initialisation: tension à 0V et activation de la sortie
        power_supply.power_supply.write('VOLT 0')
        power_supply.power_supply.write('OUTP ON')
        time.sleep(delay)  # Stabilisation initiale

        # Parcours de la séquence
        for i in range(len(sequence)):
            # Vérification d'interruption demandée
            if interrupt_event.is_set():
                break

            current_voltage = sequence[i]

            # Détermination du délai approprié (délai spécial pour les points extrêmes)
            if current_voltage in {v1, v2, -v2}:
                current_delay = final_delay
            else:
                current_delay = delay

            # Traitement spécial des points à 0V lors des changements de polarité
            if (current_voltage == 0 and i > 0 and i < len(sequence) - 1 and
                ((sequence[i-1] > 0 and sequence[i+1] < 0) or (sequence[i-1] < 0 and sequence[i+1] > 0))):
                # Désactivation de la sortie par sécurité
                power_supply.power_supply.write('OUTP OFF')

                # Demande à l'utilisateur d'inverser les connexions
                messagebox.showinfo("Changement de signe",
                                  f"Changement de signe détecté: {sequence[i-1]}V → {sequence[i+1]}V.\n"
                                  f"Veuillez inverser manuellement les connexions puis cliquer sur OK.")

                # Réactivation sécurisée
                power_supply.power_supply.write('VOLT 0')
                power_supply.power_supply.write('OUTP ON')

                # Délai de stabilisation
                time.sleep(current_delay)

                # Mesure au point 0V
                measured_voltage = clean_response(power_supply.power_supply.query('MEAS:VOLT?'))
                measured_current = clean_response(power_supply.power_supply.query('MEAS:CURR?'))
                resistance_value = clean_response(meter.mesurer())

                # Conversion des valeurs mesurées
                try:
                    measured_voltage = float(measured_voltage)
                    measured_current = float(measured_current)
                    resistance_value = float(resistance_value)
                except ValueError as e:
                    messagebox.showerror("Erreur de mesure", f"Erreur lors de la conversion des valeurs mesurées: {e}")
                    interrupt_event.set()
                    return

                # Mise à jour de l'interface
                update_measurement_labels(measured_voltage, measured_current, resistance_value, current_voltage)

                # Stockage des données
                data_res = np.append(data_res, resistance_value)
                data_tension = np.append(data_tension, measured_voltage)
                data_consigne = np.append(data_consigne, current_voltage)
                data_delai = np.append(data_delai, current_delay)

                # Mise à jour du graphique
                update_graph(data_res, data_tension)

                # Passer au point suivant
                continue

            # Application de la tension (toujours en valeur absolue)
            power_supply.power_supply.write(f'VOLT {abs(current_voltage)}')
            time.sleep(current_delay)  # Délai de stabilisation

            # Mesures
            measured_voltage = clean_response(power_supply.power_supply.query('MEAS:VOLT?'))
            measured_current = clean_response(power_supply.power_supply.query('MEAS:CURR?'))
            resistance_value = clean_response(meter.mesurer())

            # Conversion des valeurs mesurées
            try:
                measured_voltage = float(measured_voltage)
                measured_current = float(measured_current)
                resistance_value = float(resistance_value)
            except ValueError as e:
                messagebox.showerror("Erreur de mesure", f"Erreur lors de la conversion des valeurs mesurées: {e}")
                interrupt_event.set()
                return

            # Ajustement du signe de la tension mesurée
            if (current_voltage < 0 and measured_voltage > 0):
                measured_voltage = -measured_voltage

            # Mise à jour de l'interface
            update_measurement_labels(measured_voltage, measured_current, resistance_value, current_voltage)

            # Stockage des données
            data_res = np.append(data_res, resistance_value)
            data_tension = np.append(data_tension, measured_voltage)
            data_consigne = np.append(data_consigne, current_voltage)
            data_delai = np.append(data_delai, current_delay)

            # Mise à jour du graphique
            update_graph(data_res, data_tension)

        # Fin des mesures
        secure_power_supply()

    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la mesure: {e}\n{traceback.format_exc()}")
    finally:
        # Nettoyage final
        if not interrupt_event.is_set():
            btn_start.config(text="   Lancer une nouvelle mesure   ")
        secure_power_supply()
        first_measurement_point = True

        # Préparation des données pour l'exportation
        if len(data_tension) > 0 and len(data_res) > 0 and len(data_consigne) > 0 and len(data_delai) > 0:
            data_complete = np.column_stack((data_tension, data_res, data_consigne, data_delai))

def update_measurement_labels(voltage, current, resistance, setpoint=None):
    """
    Met à jour les labels d'affichage des valeurs mesurées.

    Args:
        voltage (float): Tension mesurée
        current (float): Courant mesuré
        resistance (float): Résistance mesurée
        setpoint (float, optional): Tension de consigne
    """
    if setpoint is not None:
        lbl_setpoint.config(text=f"Consigne: {setpoint:.4f} V")
    lbl_voltage.config(text=f"Tension: {voltage:.4f} V")
    lbl_current.config(text=f"Courant: {current:.4f} A")
    lbl_resistance.config(text=f"Résistance: {resistance:.4f} Ω")

def update_graph(data_res, data_tension):
    """
    Met à jour le graphique avec les nouvelles données.

    Args:
        data_res (numpy.ndarray): Données de résistance
        data_tension (numpy.ndarray): Données de tension
    """
    global ax, titre_graph, abcisse, ordonnee

    # Effacement et redéfinition du graphique
    ax.clear()
    ax.set_title(titre_graph)
    ax.set_xlabel(abcisse)
    ax.set_ylabel(ordonnee)

    # Tracé des données
    ax.plot(data_tension, data_res)

    # Mise à jour du canevas
    canvas.draw_idle()

def stop():
    """
    Arrête le programme proprement et sécurise les instruments.

    Opérations:
    - Sécurisation de l'alimentation
    - Signalement de l'interruption
    - Fermeture de la fenêtre principale
    """
    secure_power_supply()
    power_supply.close()
    meter.close()
    interrupt_event.set()
    time.sleep(1)  # Attendre que les opérations en cours se terminent
    root.destroy()

def save():
    """
    Sauvegarde les données de mesure dans un fichier texte ou CSV.

    Opérations:
    - Vérification de la disponibilité des données
    - Ouverture d'une boîte de dialogue pour le choix du fichier
    - Écriture des données formatées avec les séparateurs configurés
    - Notification à l'utilisateur
    """
    global data_complete

    # Vérification de la disponibilité des données
    if data_complete is None or len(data_complete) == 0:
        messagebox.showinfo("Information", "Aucune donnée à enregistrer.")
        return

    # Lecture du nombre de décimales depuis config.ini
    decimal_places = int(config['General']['decimales'])

    # Détermination du type de fichier par défaut
    default_extension = config['General']['file_format']
    if default_extension == ".txt":
        file_types = [('Text files', '*.txt'), ('CSV files', '*.csv')]
    else:
        file_types = [('CSV files', '*.csv'), ('Text files', '*.txt')]

    # Boîte de dialogue pour l'enregistrement
    file_path = filedialog.asksaveasfilename(defaultextension=default_extension, filetypes=file_types)
    if file_path:
        with open(file_path, 'w', encoding='utf-8') as file:
            # En-tête avec séparateurs configurés
            header = f'Tension mesurée (V){column_separator}Résistance (Ω){column_separator}Tension de consigne (V){column_separator}Délai (s)'
            np.savetxt(file, data_complete, delimiter=column_separator, header=header, comments='', fmt=f'%.{decimal_places}f')
        messagebox.showinfo("Sauvegarde", f"Données sauvegardées avec succès dans {file_path}")


def save_png():
    """
    Sauvegarde le graphique en tant qu'image PNG.

    Opérations:
    - Ouverture d'une boîte de dialogue pour le choix du fichier
    - Enregistrement du graphique en haute résolution (300 DPI)
    - Notification à l'utilisateur
    """
    file = filedialog.asksaveasfile(mode='wb', defaultextension=".png")
    if file:
        fig.savefig(file, dpi=300)  # Haute résolution
        file.close()
        messagebox.showinfo("Sauvegarde", "Image sauvegardée avec succès")

def close_program():
    """
    Gestionnaire de fermeture du programme.

    Cette fonction est appelée lorsque l'utilisateur ferme la fenêtre principale.
    Elle assure une fermeture propre du programme et la sécurisation des instruments.
    """
    stop()  # Appel de la fonction stop qui sécurise et ferme tout

# Point d'entrée du programme
if __name__ == '__main__':
    """
    Point d'entrée principal du programme.

    Initialise le matériel, configure l'interface graphique et lance la boucle principale.
    L'ensemble de l'application est structuré autour d'une interface Tkinter.
    """
    # Configuration de la fenêtre principale
    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", close_program)  # Gestionnaire de fermeture
    root.title("Résistivité en fonction de la tension")
    root.state('zoomed')  # Plein écran fenêtré
    chemin_logo = "icone.ico"
    root.iconbitmap(chemin_logo)  # Icône de l'application

    # Frame pour les champs de saisie
    input_frame = ttk.Frame(root)
    input_frame.pack(fill='x', padx=5, pady=5)

    # Configuration des champs de saisie
    ttk.Label(input_frame, text="V1 (V):").pack(side='left', padx=5, pady=5)
    entry_v1 = ttk.Entry(input_frame)  # Tension initiale
    entry_v1.pack(side='left', padx=5, pady=5)

    ttk.Label(input_frame, text="V2 (V):").pack(side='left', padx=5, pady=5)
    entry_v2 = ttk.Entry(input_frame)  # Tension finale
    entry_v2.pack(side='left', padx=5, pady=5)

    ttk.Label(input_frame, text="Pas (V):").pack(side='left', padx=5, pady=5)
    entry_step = ttk.Entry(input_frame)  # Pas de tension
    entry_step.pack(side='left', padx=5, pady=5)

    ttk.Label(input_frame, text="Délai (s):").pack(side='left', padx=5, pady=5)
    entry_delay = ttk.Entry(input_frame)  # Délai standard
    entry_delay.pack(side='left', padx=5, pady=5)

    ttk.Label(input_frame, text="Délai V1 / V2 (s):").pack(side='left', padx=5, pady=5)
    entry_final_delay = ttk.Entry(input_frame)  # Délai aux points extrêmes
    entry_final_delay.pack(side='left', padx=5, pady=5)

    # Case à cocher pour l'hystérésis
    hysteresis_var = tk.BooleanVar()
    hysteresis_check = ttk.Checkbutton(input_frame, text="Hystérésis", variable=hysteresis_var)
    hysteresis_check.pack(side='left', padx=5, pady=5)

    # Frame pour l'affichage des valeurs mesurées
    measurement_frame = ttk.Frame(root)
    measurement_frame.pack(side='right', fill='y', padx=5, pady=5)

    # Labels pour l'affichage des valeurs mesurées
    lbl_setpoint = ttk.Label(measurement_frame, text="Consigne: - V", font=('Courier', 12))
    lbl_voltage = ttk.Label(measurement_frame, text="Tension: - V", font=('Courier', 12))
    lbl_current = ttk.Label(measurement_frame, text="Courant: - A", font=('Courier', 12))
    lbl_resistance = ttk.Label(measurement_frame, text="Résistance: - Ω", font=('Courier', 12))

    # Placement des labels d'affichage
    lbl_setpoint.pack(anchor='w', padx=5, pady=5)
    lbl_voltage.pack(anchor='w', padx=5, pady=5)
    lbl_current.pack(anchor='w', padx=5, pady=5)
    lbl_resistance.pack(anchor='w', padx=5, pady=5)

    # Chargement des valeurs initiales depuis la configuration
    load_config()

    # Configuration du graphique
    fig, ax = plt.subplots()  # Création de la figure et des axes
    ax.set_title(titre_graph)
    ax.set_xlabel(abcisse)
    ax.set_ylabel(ordonnee)
    canvas = FigureCanvasTkAgg(fig, master=root)  # Intégration du graphique dans Tkinter
    canvas.draw()
    canvas.get_tk_widget().pack(side='top', fill='both', expand=True, padx=5, pady=5)

    # Frame pour les boutons de contrôle
    button_frame = ttk.Frame(root)
    button_frame.pack(fill='x', padx=5, pady=5)

    # Bouton Démarrer/Arrêter
    btn_start = ttk.Button(button_frame, text="   Démarrer les mesures   ", command=start, style='Start.TButton')
    btn_start.pack(side='left', expand=True, padx=25, pady=5)

    # Boutons pour l'enregistrement
    btn_save_data = ttk.Button(button_frame, text="   Enregistrer les données   ", command=save, style='SaveData.TButton')
    btn_save_data.pack(side='left', expand=True, padx=25, pady=5)
    btn_save_img = ttk.Button(button_frame, text="   Enregistrer image   ", command=save_png, style='SaveImg.TButton')
    btn_save_img.pack(side='left', expand=True, padx=25, pady=5)

    # Configuration des styles personnalisés pour les boutons
    style = ttk.Style()
    style.configure('SaveData.TButton', background='#c8e6c9', foreground='#1b5e20', font=('Arial', 26))
    style.configure('SaveImg.TButton', background='#ffccbc', foreground='#bf360c', font=('Arial', 26))
    style.configure('Start.TButton', background='#bbdefb', foreground='#0d47a1', font=('Arial', 26))

    # Frame pour les informations de crédit
    credits_frame = ttk.Frame(root)
    credits_frame.pack(side='bottom', fill='x', padx=5, pady=5)

    # Label de crédit
    lbl_credits = ttk.Label(credits_frame, text="Créé par Grégory Mignot, laboratoire OptiMag, https://github.com/Gregory-Mignot?tab=repositories", font=('Arial', 10), anchor='e')
    lbl_credits.pack(side='right', padx=5, pady=5)

    # Lancement de la boucle principale Tkinter
    root.mainloop()
