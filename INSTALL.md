# Guide d'installation rapide - Audity

## Prérequis

- Python 3.8+
- pip
- Linux (Debian/Ubuntu recommandé)
- Privilèges root/sudo

## Installation en 3 étapes

### 1. Extraire l'archive

```bash
cd /path/to/audity
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

OU avec installation complète :

```bash
pip install -e .
```

### 3. Préparer les règles CIS

Créer la structure des règles :

```bash
mkdir -p rules/debian
mkdir -p rules/apache_http
mkdir -p rules/nginx
# etc.
```

Copier vos fichiers XML de règles CIS dans les dossiers correspondants.

### 4. Premier scan

```bash
sudo python main.py scan --rules ./rules --output ./reports
```

## Vérification

```bash
# Tester l'installation
python main.py --help

# Voir la version
python -c "import sys; print(f'Python {sys.version}')"
```

## Problèmes courants

### Module non trouvé

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Permission denied

```bash
sudo python main.py scan --rules ./rules
```

### Pas de règles chargées

Vérifier que :
1. Le dossier `rules/` existe
2. Les sous-dossiers correspondent aux packages installés
3. Les fichiers .xml sont valides

## Support

Consulter README.md pour la documentation complète.
