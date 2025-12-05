import os
import zipfile

EXCLUDES = {'.env', 'tmp.py', 'zipage.py', 'audity_web.zip', 'cis_benchmarks.db'}
EXCLUDED_DIRS = {'vendor', 'venv', '__pycache__', '.git', '.idea', '.vscode'}

def should_exclude(path: str) -> bool:
    base = os.path.basename(path)
    # Fichiers à exclure
    if base in EXCLUDES:
        return True
    # Dossiers à exclure
    parts = path.split(os.sep)
    if any(p in EXCLUDED_DIRS for p in parts):
        return True
    return False

def make_zip(zip_name: str = "audity_web.zip"):
    root = os.path.dirname(os.path.abspath(__file__))
    zpath = os.path.join(root, zip_name)

    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder, dirs, files in os.walk(root):
            # filtrer les dossiers exclus pour ne pas descendre dedans
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(folder, d))]
            for f in files:
                full_path = os.path.join(folder, f)
                rel_path = os.path.relpath(full_path, root)
                if should_exclude(full_path):
                    continue
                zf.write(full_path, rel_path)
    print(f"Archive créée: {zpath}")

if __name__ == "__main__":
    make_zip()
