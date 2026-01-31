# WhisperX sur RunPod - Guide Complet

[![GitHub](https://img.shields.io/github/stars/Fasterious/Whisperx-Runpod?style=social)](https://github.com/Fasterious/Whisperx-Runpod)

Ce guide vous permet de déployer WhisperX avec diarisation (identification des locuteurs) sur RunPod Serverless.

## Prérequis

1. **Compte RunPod** : [runpod.io](https://runpod.io)
2. **Compte Docker Hub** : [hub.docker.com](https://hub.docker.com)
3. **Token Hugging Face** (pour la diarisation) : [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
4. **Docker Desktop** installé sur votre machine

## Étape 1 : Configuration Hugging Face (Obligatoire pour la diarisation)

### 1.1 Créer un token Hugging Face

1. Allez sur [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Cliquez sur "New token"
3. Nom : `whisperx-runpod`
4. Type : `Read`
5. Copiez le token (format : `hf_xxxxxxxxxxxx`)

### 1.2 Accepter les conditions d'utilisation des modèles

Vous devez accepter les conditions pour ces deux modèles :

1. **Segmentation** : [huggingface.co/pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
   - Cliquez sur "Agree and access repository"

2. **Speaker Diarization** : [huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - Cliquez sur "Agree and access repository"

## Étape 2 : Construction de l'image Docker

### 2.1 Cloner le repository

```bash
git clone https://github.com/Fasterious/Whisperx-Runpod.git
cd Whisperx-Runpod
```

### 2.2 Se connecter à Docker Hub

```bash
docker login
```

### 2.3 Construire l'image Docker

> **Note pour les utilisateurs Mac (Apple Silicon)** : L'option `--platform linux/amd64` est obligatoire car RunPod utilise des GPUs NVIDIA sur architecture x86_64.

**Option A : Image légère** (modèles téléchargés au premier lancement sur RunPod)

```bash
docker build --platform linux/amd64 -t VOTRE_USERNAME_DOCKER/whisperx-runpod:latest .
```

- Image ~8-10 GB
- Premier lancement : ~5-10 min (téléchargement des modèles)
- Lancements suivants : rapides (modèles en cache sur le worker)

**Option B : Image complète avec modèles pré-intégrés** (recommandé)

```bash
docker build --platform linux/amd64 --build-arg HF_TOKEN=hf_votre_token_ici -t VOTRE_USERNAME_DOCKER/whisperx-runpod:latest .
```

- Image ~15-18 GB (modèles Whisper + alignement + diarisation inclus)
- **Tous les modèles sont dans l'image Docker** → pas de téléchargement sur RunPod
- Démarrage immédiat, même sur un nouveau worker (cold start minimal)
- Build plus long (~15-25 min) mais déploiement instantané

> Remplacez `VOTRE_USERNAME_DOCKER` par votre nom d'utilisateur Docker Hub  
> Remplacez `hf_votre_token_ici` par votre token Hugging Face

### 2.4 Pousser l'image sur Docker Hub

```bash
docker push VOTRE_USERNAME_DOCKER/whisperx-runpod:latest
```

## Étape 3 : Configuration sur RunPod

### 3.1 Créer un Template

1. Allez sur [runpod.io/console/serverless](https://runpod.io/console/serverless)
2. Cliquez sur **"Custom Templates"** dans le menu de gauche
3. Cliquez sur **"New Template"**
4. Remplissez :
   - **Template Name** : `WhisperX Transcription`
   - **Container Image** : `VOTRE_USERNAME_DOCKER/whisperx-runpod:latest`
   - **Container Disk** : `20 GB` (pour stocker les modèles)
5. Dans **Environment Variables**, ajoutez :
   - `HF_TOKEN` = `hf_votre_token_ici`
   - `WHISPER_MODEL` = `large-v2` (optionnel, c'est la valeur par défaut)
6. Cliquez sur **"Save Template"**

### 3.2 Créer un Endpoint Serverless

1. Cliquez sur **"Endpoints"** dans le menu de gauche
2. Cliquez sur **"New Endpoint"**
3. Configurez :
   - **Endpoint Name** : `whisperx`
   - **Select Template** : Choisissez `WhisperX Transcription`
   - **GPU Type** : `NVIDIA RTX 4090` ou `NVIDIA RTX 3090` (recommandé)
   - **Active Workers** : `0` (scale to zero quand inactif)
   - **Max Workers** : `1` ou plus selon vos besoins
   - **Idle Timeout** : `60` secondes
   - **Execution Timeout** : `600` secondes (10 minutes max par requête)
4. Cliquez sur **"Create Endpoint"**

### 3.3 Récupérer l'API Key et l'Endpoint ID

1. Dans la page de l'endpoint, notez :
   - **Endpoint ID** : `xxxxxxxxxxxxxxxx`
   - **API Key** : Allez dans Settings > API Keys

## Étape 4 : Tester la transcription

### 4.1 Test via l'interface RunPod

1. Dans la page de votre endpoint, cliquez sur **"Requests"**
2. Entrez ce JSON dans le champ de test :

```json
{
  "input": {
    "audio": "https://www.uclass.psychol.ucl.ac.uk/Release2/Conversation/AudioOnly/mp3/F_0811_10y6m_1.mp3"
  }
}
```

3. Cliquez sur **"Run"**
4. Attendez le résultat (le premier lancement peut prendre quelques minutes pour charger les modèles)

### 4.2 Test via cURL

```bash
# Lancer une transcription (mode asynchrone)
curl -X POST "https://api.runpod.ai/v2/VOTRE_ENDPOINT_ID/run" \
  -H "Authorization: Bearer VOTRE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "audio": "https://www.uclass.psychol.ucl.ac.uk/Release2/Conversation/AudioOnly/mp3/F_0811_10y6m_1.mp3"
    }
  }'
```

Réponse :
```json
{
  "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "IN_QUEUE"
}
```

```bash
# Récupérer le résultat
curl "https://api.runpod.ai/v2/VOTRE_ENDPOINT_ID/status/JOB_ID" \
  -H "Authorization: Bearer VOTRE_API_KEY"
```

### 4.3 Test synchrone (attend le résultat)

```bash
curl -X POST "https://api.runpod.ai/v2/VOTRE_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer VOTRE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "audio": "https://www.uclass.psychol.ucl.ac.uk/Release2/Conversation/AudioOnly/mp3/F_0811_10y6m_1.mp3"
    }
  }'
```

## Format de la requête

```json
{
  "input": {
    "audio": "https://example.com/audio.mp3",  // URL de l'audio (obligatoire)
    "language": "fr",                           // Langue (optionnel, auto-détection par défaut)
    "diarize": true,                            // Activer la diarisation (optionnel, true par défaut)
    "min_speakers": 2,                          // Nombre min de locuteurs (optionnel)
    "max_speakers": 4,                          // Nombre max de locuteurs (optionnel)
    "batch_size": 16                            // Taille du batch (optionnel, 16 par défaut)
  }
}
```

## Format de la réponse

```json
{
  "status": "success",
  "output": {
    "language": "en",
    "text": "The complete transcription as plain text...",
    "speaker_text": "[SPEAKER_00]: First speaker text...\n[SPEAKER_01]: Second speaker text...",
    "segments": [
      {
        "start": 0.0,
        "end": 2.5,
        "text": " Hello, how are you?",
        "speaker": "SPEAKER_00",
        "words": [
          {"word": "Hello", "start": 0.0, "end": 0.5, "score": 0.99},
          {"word": "how", "start": 0.6, "end": 0.8, "score": 0.98}
        ]
      }
    ],
    "word_segments": [...]
  }
}
```

## Modèles Whisper disponibles

| Modèle | VRAM requise | Vitesse | Qualité |
|--------|--------------|---------|---------|
| `tiny` | ~1 GB | Très rapide | Basse |
| `base` | ~1 GB | Rapide | Moyenne |
| `small` | ~2 GB | Moyen | Bonne |
| `medium` | ~5 GB | Lent | Très bonne |
| `large-v2` | ~10 GB | Lent | Excellente |
| `large-v3` | ~10 GB | Lent | Excellente |

Pour changer de modèle, modifiez la variable d'environnement `WHISPER_MODEL` dans RunPod.

## Dépannage

### Erreur : "No HF_TOKEN provided"

- Vérifiez que vous avez bien ajouté `HF_TOKEN` dans les variables d'environnement de votre template RunPod.
- Vérifiez que votre token est valide sur huggingface.co.

### Erreur : "Failed to download audio"

- Vérifiez que l'URL de l'audio est accessible publiquement.
- Vérifiez que le format audio est supporté (mp3, wav, m4a, etc.).

### Erreur : "CUDA out of memory"

- Réduisez `batch_size` dans votre requête (ex: `"batch_size": 4`).
- Utilisez un modèle plus petit (ex: `medium` au lieu de `large-v2`).
- Utilisez un GPU avec plus de VRAM.

### Premier lancement très lent

- C'est normal ! Les modèles sont téléchargés au premier lancement.
- Pour accélérer, reconstruisez l'image Docker avec `--build-arg HF_TOKEN=...`.

### Erreur : "pull access denied" sur RunPod

- L'image Docker n'a pas été poussée ou le repository est privé.
- Vérifiez que vous avez fait `docker push` après le build.
- Vérifiez que le repository est **public** sur Docker Hub (Settings → Visibility → Public).

### Erreur SSL lors du build Docker

- Si vous avez des erreurs SSL avec `download.pytorch.org`, le Dockerfile inclut déjà les corrections nécessaires (`trusted-host`, `certifi`).
- Si le problème persiste, vérifiez votre connexion internet et réessayez.

### Erreur "xet" ou téléchargement Hugging Face qui échoue

- Le Dockerfile désactive automatiquement le téléchargeur expérimental `xet` de Hugging Face qui peut causer des problèmes dans Docker.
- Les variables `HF_HUB_ENABLE_HF_TRANSFER=0` et `HF_HUB_DISABLE_XET=1` sont déjà configurées.

## Notes techniques

### Architecture

Le projet utilise :
- **Base image** : `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04`
- **Python** : 3.10
- **WhisperX** : Dernière version stable
- **PyTorch** : Version CUDA 12.1 (réinstallée après WhisperX pour garantir le support GPU)

### Temps de build

- **Sans modèles pré-téléchargés** : ~5-10 minutes
- **Avec modèles pré-téléchargés** : ~15-25 minutes (selon la connexion)

### Taille de l'image Docker

- **Sans modèles** : ~8-10 GB
- **Avec modèles large-v2** : ~15-18 GB

### Sécurité du token Hugging Face

- Le token HF passé avec `--build-arg` est **uniquement utilisé pendant le build** pour télécharger les modèles
- Le token n'est **PAS stocké dans l'image Docker** finale
- Au runtime, le token est fourni via les variables d'environnement RunPod (sécurisées)
- Vous pouvez vérifier avec `docker history` ou `docker inspect` que le token n'apparaît pas

### Langues supportées

WhisperX supporte de nombreuses langues avec alignement automatique :
- **Alignement natif** : `en`, `fr`, `de`, `es`, `it`
- **Via Hugging Face** : Nombreuses autres langues (voir [alignment.py](https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py))

### Formats audio supportés

Tous les formats supportés par FFmpeg : `mp3`, `wav`, `m4a`, `flac`, `ogg`, `webm`, etc.

## Coûts estimés

- **Construction Docker** : Gratuit (sur votre machine)
- **RunPod Serverless** :
  - RTX 4090 : ~$0.00044/seconde
  - RTX 3090 : ~$0.00031/seconde
  - Transcription d'un audio de 10 min : ~$0.02-0.05

## Support

- **Ce projet** : [github.com/Fasterious/Whisperx-Runpod](https://github.com/Fasterious/Whisperx-Runpod)
- **WhisperX** : [github.com/m-bain/whisperX](https://github.com/m-bain/whisperX)
- **RunPod** : [docs.runpod.io](https://docs.runpod.io)

## Licence

MIT License - Libre d'utilisation et de modification.
