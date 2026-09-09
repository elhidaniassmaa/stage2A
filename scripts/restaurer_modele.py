import shutil, os

prod_path = "models/classification/"
backup_path = "models/classification_backup/"

if os.path.exists(prod_path):
    shutil.rmtree(prod_path)
shutil.copytree(backup_path, prod_path)
print("Modèle de production restauré à l'état pré-test.")