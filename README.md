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


### Table des matières

- [General](#general)
- [Alimentation](#alimentation)
- [Meter](#meter)
- [Mesure](#mesure)
- [Mesure_carre](#mesure_carre)

---

### <a name="general"></a> [General]

| Paramètre           | Type    | Description                                                        |
|:--------------------|:--------|:-------------------------------------------------------------------|
| `decimal_separator` | String  | Séparateur décimal utilisé dans les fichiers (`.` ou `,`)          |
| `file_format`       | String  | Extension des fichiers de données (`.txt`, `.csv`, etc.)           |
| `column_separator`  | String  | Séparateur de colonnes dans les fichiers (`;`, `,`, etc.)           |
| `decimales`         | Entier  | Nombre de chiffres après la virgule pour les mesures enregistrées  |

---

### <a name="alimentation"></a> [Alimentation]

| Paramètre         | Type    | Description                                                                  |
|:------------------|:--------|:----------------------------------------------------------------------------|
| `classe`          | String  | Modèle ou classe de l'alimentation utilisée (ex: `Itech6517D`)               |
| `address`         | String  | Adresse VISA de l'alimentation (`TCPIP0::192.168.0.200::inst0::INSTR`)        |
| `volt_max`        | Float   | Tension maximale autorisée (en Volts)                                        |
| `curr_max`        | Float   | Courant maximal autorisé sous tension (en Ampères)                          |
| `curr_prot_lev`   | Float   | Niveau de protection en courant (seuil de sécurité, en Ampères)             |

---

### <a name="meter"></a> [Meter]

| Paramètre         | Type    | Description                                                                  |
|:------------------|:--------|:----------------------------------------------------------------------------|
| `classe`          | String  | Modèle ou classe du multimètre utilisé (ex: `Keithley2000`)                  |
| `gpib_address`    | String  | Adresse GPIB du multimètre (`GPIB0::16::INSTR`)                               |

---

### <a name="mesure"></a> [Mesure]

| Paramètre         | Type    | Description                                                                   |
|:------------------|:--------|:----------------------------------------------------------------------------|
| `v1`              | Float   | Tension de départ pour la mesure (en Volts)                                   |
| `v2`              | Float   | Tension finale pour la mesure (en Volts)                                      |
| `step`            | Float   | Pas de tension entre deux mesures (en Volts)                                  |
| `delay`           | Float   | Temps d'attente après application de chaque niveau de tension (en secondes)   |
| `final_delay`     | Float   | Temps d'attente à la fin de la série de mesures (en secondes)                  |
| `hysteresis`      | Booléen | Active ou non un cycle aller-retour de tension (descente puis remontée)        |

---

### <a name="mesure_carre"></a> [Mesure_carre]

| Paramètre         | Type    | Description                                                               |
|:------------------|:--------|:-------------------------------------------------------------------------|
| `v1`              | Float   | Tension basse appliquée (en Volts)                                        |
| `v2`              | Float   | Tension haute appliquée (en Volts)                                        |
| `delay_v1`        | Float   | Durée de maintien de la tension `v1` avant changement (en secondes)      |
| `delay_v2`        | Float   | Durée de maintien de la tension `v2` avant changement (en secondes)      |
| `n`               | Entier  | Nombre de cycles complets (basse + haute tension) à réaliser              |
| `measure_delay`   | Float   | Temps entre deux mesures pendant les phases de stabilisation (en secondes) |

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

