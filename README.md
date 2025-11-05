# 🔒 Audity - CIS Benchmark Security Scanner

**Audity** est un outil de scan de sécurité automatisé pour serveurs Linux basé sur les benchmarks CIS (Center for Internet Security). Il détecte automatiquement le système d'exploitation et les packages installés, applique les règles CIS pertinentes et génère des rapports détaillés avec possibilité de correction automatique.

---

## ✨ Caractéristiques

- ✅ **Détection automatique** de l'OS et des packages installés
- ✅ **Chargement intelligent** des règles CIS pertinentes
- ✅ **Scan multi-thread** pour performances optimales
- ✅ **Rapports XML et HTML** avec graphiques et statistiques
- ✅ **Correction automatique** avec backup des fichiers
- ✅ **Vérification des privilèges** admin/root
- ✅ **Logs détaillés** avec codes couleurs
- ✅ **Support multi-technologies** :
  - Debian/Ubuntu
  - Apache HTTP Server
  - Apache Tomcat 10.1
  - Nginx
  - MariaDB
  - PostgreSQL
  - MongoDB
  - SQL Server (Linux)

---

## 📦 Prérequis

- **Python 3.8+**
- **Privilèges root/admin** (pour lire les fichiers de configuration système)
- **Système d'exploitation supporté** : Linux (Debian, Ubuntu, etc.)

---

## 🚀 Installation

### Méthode 1 : Installation via pip (recommandé)

```bash
# Cloner le dépôt ou extraire l'archive
cd audity

# Installer avec pip
pip install -e .

# OU installer les dépendances uniquement
pip install -r requirements.txt
```

### Méthode 2 : Installation manuelle

```bash
# Installer les dépendances
pip install lxml jinja2 colorama psutil packaging python-dateutil
```

### Vérification de l'installation

```bash
python main.py --help
```

---

## 📂 Structure du projet

```
audity/
├── main.py                      # Point d'entrée CLI
├── config.ini                   # Configuration par défaut
├── requirements.txt             # Dépendances Python
├── setup.py                     # Installation via pip
├── README.md                    # Documentation
│
├── scanner/                     # Module de scan
│   ├── __init__.py
│   ├── system_detector.py       # Détection OS + packages
│   ├── rules_loader.py          # Chargement règles XML
│   └── vulnerability_checker.py # Exécution des checks
│
├── reports/                     # Module de rapports
│   ├── __init__.py
│   ├── xml_generator.py         # Génération rapport XML
│   └── html_generator.py        # Génération rapport HTML
│
├── remediation/                 # Module de correction
│   ├── __init__.py
│   └── auto_fix.py              # Correction automatique
│
├── utils/                       # Utilitaires
│   ├── __init__.py
│   ├── logger.py                # Système de logs
│   └── privilege_checker.py     # Vérification privilèges
│
├── rules/                       # Règles CIS (à fournir)
│   ├── debian/
│   │   └── *.xml
│   ├── apache_http/
│   │   └── *.xml
│   ├── mariadb/
│   │   └── *.xml
│   └── ...
│
├── reports/                     # Rapports générés
│   └── scan_YYYYMMDD_HHMMSS.*
│
├── backups/                     # Backups des fichiers modifiés
│   └── *.backup.*
│
└── logs/                        # Logs d'exécution
    └── audity.log
```

---

## ⚙️ Configuration

Le fichier `config.ini` contient la configuration par défaut :

```ini
[scanner]
# Répertoire des règles CIS
rules_dir = ./rules

# Répertoire de sortie des rapports
output_dir = ./reports

# Niveau de log : DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = INFO

# Fichier de log
log_file = ./logs/audity.log

# Nombre de threads pour le scan parallèle
max_threads = 4

[reports]
# Générer rapport HTML
generate_html = true

# Générer rapport XML
generate_xml = true

# Version du format
format_version = 1.0

[remediation]
# Créer backup avant correction
create_backup = true

# Répertoire des backups
backup_dir = ./backups

# Mode interactif (demander confirmation)
interactive = true
```

Vous pouvez surcharger ces valeurs via les arguments CLI.

---

## 🔧 Utilisation

### Commande de base : Scan

```bash
sudo python main.py scan --rules ./rules --output ./reports
```

### Options disponibles

```bash
# Aide générale
python main.py --help

# Aide pour la commande scan
python main.py scan --help
```

### Exemples d'utilisation

**1. Scan simple**
```bash
sudo python main.py scan --rules ./rules --output ./reports
```

**2. Scan avec correction automatique**
```bash
sudo python main.py scan --rules ./rules --output ./reports --fix
```

**3. Scan sans interaction (applique tous les fix)**
```bash
sudo python main.py scan --rules ./rules --output ./reports --fix --no-interactive
```

**4. Scan avec plus de threads**
```bash
sudo python main.py scan --rules ./rules --output ./reports --threads 8
```

**5. Scan en mode verbose (debug)**
```bash
sudo python main.py scan --rules ./rules --output ./reports --verbose
```

**6. Visualiser un rapport existant**
```bash
python main.py report --input ./reports/scan_20241104_120000.xml
```

---

## 📝 Format des règles CIS

### Structure des dossiers

Les règles doivent être organisées par technologie :

```
rules/
├── debian/
│   ├── 1.1-1.xml      # Filesystem rules
│   ├── 1.2-1.xml      # Package management
│   └── ...
├── apache_http/
│   └── apache-2.4.xml
├── nginx/
│   └── nginx-1.18.xml
└── ...
```

### Format XML des règles

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Benchmark>
    <Group id="1">
        <title>Initial Setup</title>

        <Rule id="1.1.1.1" severity="high">
            <title>Ensure mounting of cramfs filesystems is disabled</title>
            <description>
                The cramfs filesystem type is a compressed read-only 
                Linux filesystem embedded in small footprint systems.
            </description>
            <rationale>
                Removing support for unneeded filesystem types reduces 
                the local attack surface.
            </rationale>

            <check test-type="pattern_not_match">
                <file>/proc/modules</file>
                <pattern>cramfs</pattern>
            </check>

            <fix type="command">
                <command>modprobe -r cramfs</command>
                <description>Disable cramfs kernel module</description>
            </fix>
        </Rule>
    </Group>
</Benchmark>
```

### Types de tests supportés

- **pattern_match** : Le fichier doit contenir le pattern
- **pattern_not_match** : Le fichier ne doit PAS contenir le pattern
- **file_exists** : Le fichier doit exister
- **command_output** : Sortie de commande doit correspondre
- **permission_check** : Permissions fichier doivent correspondre

---

## 📊 Rapports générés

### Rapport HTML

Rapport interactif avec :
- Score de conformité global (%)
- Statistiques (passed/failed/errors/notchecked)
- Tableau filtrable par statut
- Design moderne et responsive

Ouvrir dans un navigateur : `firefox ./reports/scan_YYYYMMDD_HHMMSS.html`

### Rapport XML

Format structuré pour intégration dans d'autres outils :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ScanReport version="1.0">
    <Metadata>
        <ScanDate>2024-11-04T12:00:00</ScanDate>
        <Hostname>debian-server</Hostname>
        <OperatingSystem>Debian 11</OperatingSystem>
    </Metadata>
    <Statistics>
        <Total>150</Total>
        <Passed>120</Passed>
        <Failed>20</Failed>
        <Errors>5</Errors>
        <NotChecked>5</NotChecked>
        <CompliancePercentage>85.71</CompliancePercentage>
    </Statistics>
    <Results>
        <Rule id="1.1.1.1" status="pass" severity="high">
            <Title>Ensure mounting of cramfs filesystems is disabled</Title>
            <Details>Pattern not found in /proc/modules (as expected)</Details>
            <Timestamp>2024-11-04T12:00:05</Timestamp>
        </Rule>
        <!-- ... -->
    </Results>
</ScanReport>
```

---

## 🔧 Correction automatique

### Fonctionnement

1. Le scan identifie les règles en échec (status=fail)
2. Avec l'option `--fix`, le système propose des corrections
3. Mode **interactif** (défaut) : demande confirmation pour chaque fix
4. Mode **automatique** (`--no-interactive`) : applique tous les fix

### Backups automatiques

Avant chaque modification :
- Backup créé dans `./backups/`
- Nom : `fichier.backup.YYYYMMDD_HHMMSS`
- Permet restauration manuelle si nécessaire

### Log de remediation

Un fichier `remediation_YYYYMMDD_HHMMSS.log` est créé avec :
- Liste des fix appliqués avec succès
- Liste des fix échoués
- Timestamp de chaque action

---

## 🔍 Exemples de workflows

### Workflow 1 : Scan initial

```bash
# 1. Lancer le scan
sudo python main.py scan --rules ./rules --output ./reports

# 2. Ouvrir le rapport HTML
firefox ./reports/scan_20241104_120000.html

# 3. Analyser les résultats
```

### Workflow 2 : Scan + Correction

```bash
# 1. Scan avec correction interactive
sudo python main.py scan --rules ./rules --output ./reports --fix

# 2. Confirmer chaque fix proposé (y/n)

# 3. Vérifier les backups
ls -la ./backups/

# 4. Consulter le log de remediation
cat ./reports/remediation_20241104_120000.log
```

### Workflow 3 : Automatisation complète

```bash
# Mode non-interactif pour scripts automatisés
sudo python main.py scan \
    --rules ./rules \
    --output ./reports \
    --fix \
    --no-interactive \
    --threads 8
```

---

## 🐛 Dépannage

### Erreur : "Must be run with administrator/root privileges"

```bash
# Solution : Utiliser sudo
sudo python main.py scan --rules ./rules
```

### Erreur : "No applicable rules found"

Vérifier la structure du dossier `rules/` :
```bash
ls -R ./rules/
# Doit afficher : debian/, apache_http/, etc.
```

### Erreur : "No rules loaded"

Les fichiers XML sont-ils valides ?
```bash
# Tester manuellement
python -c "from lxml import etree; etree.parse('./rules/debian/1.1-1.xml')"
```

### Logs détaillés

Activer le mode verbose :
```bash
sudo python main.py scan --rules ./rules --verbose
```

Consulter les logs :
```bash
tail -f ./logs/audity.log
```

---

## 🚀 Développement

### Ajouter un nouveau type de test

Éditer `scanner/vulnerability_checker.py` :

```python
def _check_custom_test(self, rule) -> CheckResult:
    # Votre logique ici
    pass
```

### Personnaliser le rapport HTML

Éditer `reports/html_generator.py`, méthode `_get_html_template()`.

---

## 📄 Licence

MIT License

---

## 👥 Auteurs

**Dylan CARBON** & **Clément LAVALLÉE**  
ESGI - Projet Annuel 4SI3

---

## 📞 Support

Pour toute question ou problème :
- Créer une issue sur GitHub
- Contact : dylan.carbon@example.com

---

## 🎯 Roadmap

- [ ] Support Windows Server
- [ ] Interface web (dashboard)
- [ ] Export PDF des rapports
- [ ] Intégration CI/CD (Jenkins, GitLab CI)
- [ ] API REST
- [ ] Comparaison de scans (évolution temporelle)

---

**Happy Scanning! 🔒**
