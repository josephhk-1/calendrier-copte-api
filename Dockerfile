# Utiliser une image Python officielle comme base
FROM python:3.12-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Empêcher Python de créer des fichiers .pyc et s'assurer que les logs s'affichent directement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copier le fichier des dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier tous les dossiers du projet dans le conteneur
COPY app ./app
COPY data ./data
COPY schemas ./schemas
COPY scripts ./scripts

# Exposer le port sur lequel l'application va tourner
EXPOSE 8000

# Définir la commande pour lancer l'application

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
