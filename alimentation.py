# alimentation.py

import pyvisa
from pyvisa.errors import VisaIOError
from tkinter import messagebox

class Itech6517D:
    """
    Classe pour contrôler l'alimentation ITECH 6517D via VISA.

    Attributes:
        power_supply (pyvisa.Resource): Ressource VISA pour l'alimentation.
        volt_max (float): Tension maximale.
        curr_max (float): Courant maximal.
        curr_prot_lev (float): Niveau de protection en courant.
    """

    def __init__(self, address, volt_max, curr_max, curr_prot_lev):
        """
        Initialise l'alimentation avec les paramètres spécifiés.

        Args:
            address (str): Adresse de l'alimentation.
            volt_max (float): Tension maximale.
            curr_max (float): Courant maximal.
            curr_prot_lev (float): Niveau de protection en courant.
        """
        try:
            self.power_supply = pyvisa.ResourceManager().open_resource(address)
            self.volt_max = volt_max
            self.curr_max = curr_max
            self.curr_prot_lev = curr_prot_lev
            self.initialize()
        except VisaIOError as e:
            messagebox.showerror("Erreur VISA", f"Erreur lors de l'ouverture de la ressource : {e}")
            raise

    def initialize(self):
        """
        Initialise l'alimentation avec les paramètres de sécurité.
        """
        try:
            self.power_supply.write('*RST')  # Reset de l'instrument
            self.power_supply.write('*CLS')  # Clear status
            self.power_supply.write('SYST:REM')  # Mode remote
            self.power_supply.write('VOLT:MIN 0')  # Tension minimale
            self.power_supply.write(f'VOLT:MAX {self.volt_max}')  # Tension maximale
            self.power_supply.write('CURR:MIN 0')  # Courant minimal
            self.power_supply.write(f'CURR:MAX {self.curr_max}')  # Courant maximal
            self.power_supply.write('VOLT:PROT:STAT 0')  # Désactivation de la protection en tension
            self.power_supply.write('CURR:PROT:STAT 1')  # Activation de la protection en courant
            self.power_supply.write(f'CURR:PROT:LEV {self.curr_prot_lev}')  # Niveau de protection en courant

            error_query = self.power_supply.query('SYST:ERR?')
            if "No error" not in error_query:
                raise Exception(f"Erreur lors de l'initialisation de l'alimentation: {error_query}")
        except VisaIOError as e:
            messagebox.showerror("Erreur VISA", f"Erreur lors de l'initialisation de l'alimentation : {e}")
            raise

    def securiser(self):
        """
        Remet l'alimentation en état sécurisé.
        """
        try:
            self.power_supply.write('OUTP OFF')  # Désactiver la sortie
            self.power_supply.write('VOLT 0')    # Tension à 0V
            self.power_supply.write('*CLS')      # Effacer les erreurs
            self.power_supply.write('SYST:LOC')  # Mode local
        except VisaIOError as e:
            messagebox.showerror("Erreur VISA", f"Erreur lors de la sécurisation de l'alimentation : {e}")
            raise

    def close(self):
        """
        Ferme la ressource VISA.
        """
        try:
            self.power_supply.close()
        except VisaIOError as e:
            messagebox.showerror("Erreur VISA", f"Erreur lors de la fermeture de la ressource : {e}")
            raise
