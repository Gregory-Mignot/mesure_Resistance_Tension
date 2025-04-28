# appareil_mesure.py

import pyvisa
from pyvisa.errors import VisaIOError
from tkinter import messagebox

class Keithley2000:
    """
    Classe pour contrôler le multimètre Keithley 2000 via VISA.

    Attributes:
        meter (pyvisa.Resource): Ressource VISA pour le multimètre.
    """

    def __init__(self, gpib_address):
        """
        Initialise le multimètre avec l'adresse GPIB spécifiée.

        Args:
            gpib_address (str): Adresse GPIB du multimètre.
        """
        try:
            self.meter = pyvisa.ResourceManager().open_resource(gpib_address)
            self.initialize()
        except VisaIOError as e:
            messagebox.showerror("Erreur VISA", f"Erreur lors de l'ouverture de la ressource : {e}")
            raise

    def initialize(self):
        """
        Initialise le multimètre avec les paramètres de mesure.
        """
        try:
            self.meter.write('*RST')  # Reset de l'instrument
            self.meter.write('CONF:RES')  # Configuration pour mesurer la résistance
            self.meter.write('RES:RANG:AUTO ON')  # Auto-range pour la résistance
            self.meter.write('TRIG:SOUR IMM')  # Source de déclenchement immédiate
            self.meter.write('TRIG:COUNT 1')  # Un seul déclenchement par mesure
        except VisaIOError as e:
            messagebox.showerror("Erreur VISA", f"Erreur lors de l'initialisation du multimètre : {e}")
            raise

    def mesurer(self):
        """
        Effectue une mesure de résistance.

        Returns:
            str: Valeur de résistance mesurée.
        """
        try:
            return self.meter.query('READ?')
        except VisaIOError as e:
            messagebox.showerror("Erreur VISA", f"Erreur lors de la mesure : {e}")
            raise

    def securiser(self):
        """
        Remet le multimètre en mode local.
        """
        try:
            self.meter.write('SYST:LOC')  # Mode local
            error_check = self.meter.query('SYST:ERR?')
            if "No error" not in error_check:
                messagebox.showwarning("Avertissement", f"Erreur après sécurisation du Keithley: {error_check}")
        except VisaIOError as e:
            messagebox.showerror("Erreur VISA", f"Erreur lors de la sécurisation du multimètre : {e}")
            raise

    def close(self):
        """
        Ferme la ressource VISA.
        """
        try:
            self.meter.close()
        except VisaIOError as e:
            messagebox.showerror("Erreur VISA", f"Erreur lors de la fermeture de la ressource : {e}")
            raise
