# Mesure Résistance/Tension  , Readme.md à finir

Deux scripts Python (`main_rampe.py` et `main_carre.py`) pour réaliser des mesures de résistance ou de tension en fonction d'un signal généré (rampe ou carré), avec des paramètres entièrement configurables via un fichier `config.ini`.

---

## Table des matières

- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration (`config.ini`)](#configuration-configini)
  - [Description des paramètres](#description-des-paramètres)
- [Utilisation](#utilisation)
  - [main_rampe.py](#1-script-main_rampepy)
  - [main_carre.py](#2-script-main_carrepy)
- [Remarques](#remarques)
- [Auteurs](#auteurs)

---

## Prérequis

- Python 3.7 ou supérieur
- Modules Python suivants :
  - `numpy`
  - `matplotlib`
  - `pyvisa`
  - `configparser` (fourni avec Python)

Installation rapide :

```bash
pip install Requirements.txt
```

---

## Installation

1. Clonez ce dépôt :

```bash
git clone https://github.com/Gregory-Mignot/mesure_Resistance_Tension.git
cd mesure_Resistance_Tension
```

2. Vérifiez que le fichier `config.ini` est présent à la racine.  
   Sinon, copiez un modèle de base :

```bash
cp config_example.ini config.ini
```

---

## Configuration (`config.ini`)

Le fichier `config.ini` contient tous les paramètres nécessaires à l'exécution des scripts.

### Exemple :

```ini
[DEFAULT]
visa_address = GPIB0::22::INSTR
V_min = 0
V_max = 5
nb_points = 50
duree_point = 0.5
mesure = resistance
```

### Description des paramètres

| Paramètre     | Type    | Description                                                      | Utilisé dans |
|:--------------|:--------|:------------------------------------------------------------------|:-------------|
| `visa_address`| String  | Adresse VISA de l'appareil (ex: `GPIB0::22::INSTR`)               | Tous         |
| `V_min`       | Float   | Tension minimale appliquée (en Volts)                             | Tous         |
| `V_max`       | Float   | Tension maximale appliquée (en Volts)                             | Tous         |
| `nb_points`   | Entier  | Nombre de points dans la rampe de tension                         | `main_rampe.py` |
| `duree_point` | Float   | Temps (en secondes) d'attente à chaque niveau de tension          | Tous         |
| `mesure`      | String  | Type de mesure réalisée (`resistance` ou `tension`)               | Tous         |

---

## Utilisation

Les deux scripts utilisent **le même fichier `config.ini`** pour récupérer leurs paramètres.

### 1. Script `main_rampe.py`

**But** : Appliquer une rampe de tension continue entre `V_min` et `V_max`, avec `nb_points` valeurs intermédiaires.

**Lancement** :

```bash
python main_rampe.py
```

**Fonctionnement** :
- Crée une rampe linéaire de `nb_points` entre `V_min` et `V_max`.
- À chaque point :
  - Applique la tension correspondante.
  - Attend `duree_point` secondes.
  - Mesure soit la résistance, soit la tension selon `mesure`.
- Trace automatiquement la courbe de la mesure en fonction de la tension appliquée.

**Paramètres utilisés** :
- `visa_address`
- `V_min`
- `V_max`
- `nb_points`
- `duree_point`
- `mesure`

---

### 2. Script `main_carre.py`

**But** : Appliquer un signal carré alternant entre `V_min` et `V_max`.

**Lancement** :

```bash
python main_carre.py
```

**Fonctionnement** :
- Bascule alternativement entre `V_min` et `V_max`.
- À chaque palier :
  - Attend `duree_point` secondes.
  - Réalise la mesure.
- Trace automatiquement la mesure en fonction du temps.

**Paramètres utilisés** :
- `visa_address`
- `V_min`
- `V_max`
- `duree_point`
- `mesure`

*(Pas besoin de `nb_points` dans `main_carre.py` car le signal est simplement alterné.)*

---

## Remarques

- **Appareil non détecté** : vérifiez la bonne adresse `visa_address` avec un explorateur VISA (ex: `NI MAX` ou `pyvisa`).
- **Sécurité** : assurez-vous que les tensions appliquées sont compatibles avec votre matériel et dispositif sous test (DUT).
- Les figures générées peuvent être sauvegardées en adaptant le code (`plt.savefig()`).

---

## Auteurs

Projet développé par [Grégory Mignot](https://github.com/Gregory-Mignot).

