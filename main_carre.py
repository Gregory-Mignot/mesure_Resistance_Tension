# main_carre.py

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
titre_graph = "Résistance et Tension en fonction du temps"
abcisse = "Temps (s)"
ordonnee_resistance = "Résistance (Ω)"
ordonnee_tension = "Tension (V)"
interrupt_event = threading.Event()  # Événement pour interrompre les mesures
data_res = np.array([])  # Données de résistance
data_tension = np.array([])  # Données de tension mesurée
data_consigne = np.array([])  # Données de tension de consigne
data_temps = np.array([])  # Données de temps
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
decimales = int(config['General']['decimales'])

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
        entry_v1.insert(0, config['Mesure_carre']['v1'])  # Tension initiale
        entry_v2.insert(0, config['Mesure_carre']['v2'])  # Tension finale
        entry_delay_v1.insert(0, config['Mesure_carre']['delay_V1'])  # Délai V1
        entry_delay_v2.insert(0, config['Mesure_carre']['delay_V2'])  # Délai V2
        entry_n.insert(0, config['Mesure_carre']['N'])  # Nombre d'occurrences
        entry_measure_delay.insert(0, config['Mesure_carre']['measure_delay'])  # Délai de mesure
    except KeyError:
        pass  # Si les clés n'existent pas, ne rien faire

def save_config():
    """
    Sauvegarde les valeurs des champs de saisie dans le fichier config.ini.
    Stocke les paramètres actuels pour une utilisation future.
    """
    config['Mesure_carre'] = {
        'v1': entry_v1.get(),  # Tension initiale
        'v2': entry_v2.get(),  # Tension finale
        'delay_V1': entry_delay_v1.get(),  # Délai V1
        'delay_V2': entry_delay_v2.get(),  # Délai V2
        'N': entry_n.get(),  # Nombre d'occurrences
        'measure_delay': entry_measure_delay.get()  # Délai de mesure
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
    global data_res, data_tension, data_consigne, data_temps, interrupt_event, first_measurement_point

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
    global data_res, data_tension, data_consigne, data_temps

    # Réinitialisation des tableaux de données
    data_res = np.array([])
    data_tension = np.array([])
    data_consigne = np.array([])
    data_temps = np.array([])

    # Réinitialisation du graphique
    ax.clear()
    ax.set_title(titre_graph)
    ax.set_xlabel(abcisse)
    ax.set_ylabel(ordonnee_resistance)
    ax2.set_ylabel(ordonnee_tension)
    canvas.draw()  # Redessiner le canevas

def secure_power_supply():
    """
    Remet l'alimentation électrique en état sécurisé et ferme les ressources VISA.

    Opérations:
    - Désactivation de la sortie
    - Remise à zéro de la tension
    - Effacement des erreurs
    - Retour au mode local
    - Fermeture des ressources VISA

    Gère les erreurs éventuelles et affiche un message si nécessaire.
    """
    try:
        power_supply.securiser()
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la sécurisation de l'alimentation: {e}")

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

def measure_resistance():
    """
    Fonction principale qui effectue les mesures de résistance et de tension en fonction du temps.

    Processus:
    1. Récupère les paramètres des champs de saisie
    2. Applique un signal carré de tension
    3. Mesure la tension, le courant et la résistance à intervalles réguliers (measure_delay secondes)
    4. Met à jour l'interface et le graphique
    5. Sécurise l'alimentation à la fin

    Gère les cas spéciaux:
    - Interruption des mesures
    - Arrêt après N cycles

    Les données sont stockées pour l'analyse et l'exportation.
    """
    global delais, data_res, data_tension, data_consigne, data_temps, data_complete, first_measurement_point
    try:
        # Récupération des paramètres
        v1 = float(entry_v1.get())
        v2 = float(entry_v2.get())
        delay_V1 = float(entry_delay_v1.get())
        delay_V2 = float(entry_delay_v2.get())
        N = int(entry_n.get())
        measure_delay = float(entry_measure_delay.get())

        # Réinitialisation des tableaux de données
        data_res = np.array([])  # Résistance mesurée
        data_tension = np.array([])  # Tension mesurée
        data_consigne = np.array([])  # Tension de consigne
        data_temps = np.array([])  # Temps écoulé
        data_current = np.array([])  # Courant mesuré

        # Initialisation: tension à 0V et activation de la sortie
        power_supply.power_supply.write(f'VOLT {v1}')
        power_supply.power_supply.write('OUTP ON')
        time.sleep(2) 
        start_time = time.time()

        # Variables pour suivre le temps écoulé et le nombre de cycles
        elapsed_time = 0
        current_voltage = v1
        next_voltage_change = delay_V1
        cycle_count = 0
        measure_event = threading.Event()

        # Boucle pour appliquer le signal carré
        while not interrupt_event.is_set() and (N == 0 or cycle_count < N):
            # Vérification du temps écoulé
            elapsed_time = time.time() - start_time

            # Changement de tension en fonction du temps écoulé
            if elapsed_time >= next_voltage_change:
                if current_voltage == v1:
                    current_voltage = v2
                    next_voltage_change += delay_V2
                else:
                    current_voltage = v1
                    next_voltage_change += delay_V1
                    cycle_count += 1  # Incrémenter le compteur de cycles

                # Application de la tension
                power_supply.power_supply.write(f'VOLT {current_voltage}')

            # Mesure de la tension, du courant et de la résistance
            if elapsed_time >= measure_delay:
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
                update_measurement_labels(current_voltage, measured_voltage, measured_current, resistance_value, elapsed_time)

                # Stockage des données
                data_res = np.append(data_res, resistance_value)
                data_tension = np.append(data_tension, measured_voltage)
                data_consigne = np.append(data_consigne, current_voltage)
                data_temps = np.append(data_temps, elapsed_time)
                data_current = np.append(data_current, measured_current)

                # Mise à jour du graphique
                update_graph(data_res, data_tension, data_temps)

                # Réinitialisation du temps de mesure
                measure_event.clear()
                measure_event.wait(measure_delay)

            # Vérification de l'interruption
            if interrupt_event.is_set():
                break

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
        if len(data_temps) > 0 and len(data_res) > 0 and len(data_tension) > 0 and len(data_consigne) > 0 and len(data_current) > 0:
            data_complete = np.column_stack((data_temps, data_tension, data_res, data_consigne, data_current))



def update_measurement_labels(setpoint, voltage, current, resistance, elapsed_time):
    """
    Met à jour les labels d'affichage des valeurs mesurées.

    Args:
        setpoint (float): Tension de consigne
        voltage (float): Tension mesurée
        current (float): Courant mesuré
        resistance (float): Résistance mesurée
        elapsed_time (float): Temps écoulé
    """
    lbl_setpoint.config(text=f"Consigne: {setpoint:.4f} V")
    lbl_voltage.config(text=f"Tension: {voltage:.4f} V")
    lbl_current.config(text=f"Courant: {current:.4f} A")
    lbl_resistance.config(text=f"Résistance: {resistance:.4f} Ω")
    lbl_time.config(text=f"Temps: {elapsed_time:.4f} s")


def update_graph(data_res, data_tension, data_temps): 
    """ 
    Met à jour le graphique avec les nouvelles données. 
 
    Args: 
        data_res (numpy.ndarray): Données de résistance 
        data_tension (numpy.ndarray): Données de tension 
        data_temps (numpy.ndarray): Données de temps 
    """ 
    global ax, ax2, fig, canvas, titre_graph, abcisse, ordonnee_resistance, ordonnee_tension 
 
    # Effacement complet de la figure
    fig.clear()
    
    # Recréation des axes comme au démarrage
    ax = fig.add_subplot(111)
    ax2 = ax.twinx()  # Ceci garantit que ax2 est bien positionné à droite
    
    # Configuration des axes
    ax.set_title(titre_graph) 
    ax.set_xlabel(abcisse) 
    ax.set_ylabel(ordonnee_resistance, color='blue') 
    ax.tick_params(axis='y', labelcolor='blue') 
    ax.plot(data_temps, data_res, color='blue', label='Résistance (Ω)') 
 
    ax2.set_ylabel(ordonnee_tension, color='red') 
    ax2.tick_params(axis='y', labelcolor='red') 
    ax2.plot(data_temps, data_tension, color='red', label='Tension (V)') 
 
    # Légende si nécessaire
    lines = ax.get_lines() + ax2.get_lines() 
    labels = [line.get_label() for line in lines] 
    ax.legend(lines, labels, loc='upper left') 
 
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
            header = f'Temps (s){column_separator}Tension mesurée (V){column_separator}Résistance (Ω){column_separator}Tension de consigne (V){column_separator}Courant Mesuré (A)'
            np.savetxt(file, data_complete, delimiter=column_separator, header=header, comments='', fmt=f'%.{decimales}f')
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
    root.title("Résistance et Tension en fonction du temps")
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

    ttk.Label(input_frame, text="Délai V1 (s):").pack(side='left', padx=5, pady=5)
    entry_delay_v1 = ttk.Entry(input_frame)  # Délai V1
    entry_delay_v1.pack(side='left', padx=5, pady=5)

    ttk.Label(input_frame, text="Délai V2 (s):").pack(side='left', padx=5, pady=5)
    entry_delay_v2 = ttk.Entry(input_frame)  # Délai V2
    entry_delay_v2.pack(side='left', padx=5, pady=5)

    ttk.Label(input_frame, text="N:").pack(side='left', padx=5, pady=5)
    entry_n = ttk.Entry(input_frame)  # Nombre d'occurrences
    entry_n.pack(side='left', padx=5, pady=5)

    ttk.Label(input_frame, text="Délai de mesure (s):").pack(side='left', padx=5, pady=5)
    entry_measure_delay = ttk.Entry(input_frame)  # Délai de mesure
    entry_measure_delay.pack(side='left', padx=5, pady=5)

    # Frame pour l'affichage des valeurs mesurées
    measurement_frame = ttk.Frame(root)
    measurement_frame.pack(side='right', fill='y', padx=5, pady=5)

    # Labels pour l'affichage des valeurs mesurées
    lbl_setpoint = ttk.Label(measurement_frame, text="Consigne: - V", font=('Courier', 12))
    lbl_voltage = ttk.Label(measurement_frame, text="Tension: - V", font=('Courier', 12))
    lbl_current = ttk.Label(measurement_frame, text="Courant: - A", font=('Courier', 12))
    lbl_resistance = ttk.Label(measurement_frame, text="Résistance: - Ω", font=('Courier', 12))
    lbl_time = ttk.Label(measurement_frame, text="Temps: - s", font=('Courier', 12))

    # Placement des labels d'affichage
    lbl_setpoint.pack(anchor='w', padx=5, pady=5)
    lbl_voltage.pack(anchor='w', padx=5, pady=5)
    lbl_current.pack(anchor='w', padx=5, pady=5)
    lbl_resistance.pack(anchor='w', padx=5, pady=5)
    lbl_time.pack(anchor='w', padx=5, pady=5)

    # Chargement des valeurs initiales depuis la configuration
    load_config()

    # Configuration du graphique
    fig, ax = plt.subplots()  # Création de la figure et des axes
    ax2 = ax.twinx()  # Création d'un deuxième axe y pour la tension
    ax.set_title(titre_graph)
    ax.set_xlabel(abcisse)
    ax.set_ylabel(ordonnee_resistance, color='blue')
    ax2.set_ylabel(ordonnee_tension,color='red')
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
