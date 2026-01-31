# WhisperX sur RunPod Serverless

Déployez WhisperX avec diarisation (identification des locuteurs) sur RunPod Serverless.

## Prérequis

1. **Compte RunPod** : [runpod.io](https://runpod.io)
2. **Compte Docker Hub** : [hub.docker.com](https://hub.docker.com)
3. **Token Hugging Face** : [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
4. **Docker Desktop** installé

## Configuration Hugging Face

Avant de commencer, acceptez les conditions d'utilisation de ces modèles :

1. [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) → "Agree and access repository"
2. [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) → "Agree and access repository"

## Construction de l'image Docker

```bash
# Cloner le repo
git clone https://github.com/Fasterious/Whisperx-Runpod.git
cd Whisperx-Runpod

# Se connecter à Docker Hub
docker login

# Construire l'image (avec modèles pré-téléchargés - recommandé)
docker build --platform linux/amd64 --build-arg HF_TOKEN=hf_votre_token -t VOTRE_USERNAME/whisperx-runpod:latest .

# Pousser sur Docker Hub
docker push VOTRE_USERNAME/whisperx-runpod:latest
```

> **Note Mac (Apple Silicon)** : L'option `--platform linux/amd64` est obligatoire.

## Déploiement sur RunPod

1. Allez sur [runpod.io/console/serverless](https://runpod.io/console/serverless)
2. Créez un **Endpoint** avec :
   - **Container Image** : `VOTRE_USERNAME/whisperx-runpod:latest`
   - **Container Disk** : `20 GB`
   - **GPU** : RTX 4090 ou RTX 3090

3. Ajoutez ces **variables d'environnement** :
   - `HF_TOKEN` = `hf_votre_token`
   - `WHISPER_MODEL` = `large-v3` *(recommandé pour de meilleurs résultats)*

> **Important** : Le modèle par défaut dans l'image est `large-v2`. Pour de meilleurs résultats (moins d'erreurs en fin d'audio), définissez `WHISPER_MODEL=large-v3` dans les variables d'environnement RunPod.

## Tester la transcription

### Via le script Python inclus

```bash
# Configurer les identifiants
cp .env.example .env
# Éditer .env avec RUNPOD_API_KEY et RUNPOD_ENDPOINT_ID

# Lancer un test
python3 test_transcription.py https://example.com/audio.mp3

# Options disponibles
python3 test_transcription.py URL --language fr
python3 test_transcription.py URL --no-diarize
python3 test_transcription.py URL --min-speakers 2 --max-speakers 4
python3 test_transcription.py URL -o resultat.json
```

### Via cURL

```bash
# Lancer une transcription
curl -X POST "https://api.runpod.ai/v2/ENDPOINT_ID/run" \
  -H "Authorization: Bearer API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"audio": "https://example.com/audio.mp3"}}'

# Récupérer le résultat
curl "https://api.runpod.ai/v2/ENDPOINT_ID/status/JOB_ID" \
  -H "Authorization: Bearer API_KEY"
```

## Format de la requête

```json
{
  "input": {
    "audio": "https://example.com/audio.mp3",
    "language": "fr",
    "diarize": true,
    "min_speakers": 2,
    "max_speakers": 4
  }
}
```

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `audio` | URL du fichier audio (obligatoire) | - |
| `language` | Code langue (`fr`, `en`, etc.) | Auto-détection |
| `diarize` | Activer la diarisation | `true` |
| `min_speakers` | Nombre min de locuteurs | Auto |
| `max_speakers` | Nombre max de locuteurs | Auto |

## Format de la réponse

```json
{
  "status": "success",
  "output": {
    "language": "fr",
    "text": "Transcription complète...",
    "speaker_text": "[SPEAKER_00]: Texte du premier locuteur...\n[SPEAKER_01]: Texte du second...",
    "segments": [...]
  }
}
```

## Structure du projet

```
├── handler.py           # Handler RunPod (point d'entrée)
├── download_models.py   # Pré-téléchargement des modèles
├── Dockerfile           # Image Docker
├── test_transcription.py # Script de test
├── .env.example         # Template de configuration
└── audio.mp3            # Fichier audio de test
```

## Modèles Whisper

| Modèle | VRAM | Recommandation |
|--------|------|----------------|
| `large-v3` | ~10 GB | **Recommandé** - Meilleure qualité |
| `large-v2` | ~10 GB | Défaut dans l'image |
| `medium` | ~5 GB | Bon compromis vitesse/qualité |
| `small` | ~2 GB | Rapide, qualité correcte |

## Dépannage

| Erreur | Solution |
|--------|----------|
| "No HF_TOKEN provided" | Ajoutez `HF_TOKEN` dans les variables d'environnement |
| "Failed to download audio" | Vérifiez que l'URL est accessible publiquement |
| "CUDA out of memory" | Réduisez `batch_size` ou utilisez un modèle plus petit |

## Liens utiles

- [WhisperX](https://github.com/m-bain/whisperX)
- [RunPod Documentation](https://docs.runpod.io)

## Licence

MIT License
