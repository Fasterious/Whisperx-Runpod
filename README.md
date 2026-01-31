# WhisperX sur RunPod - Guide Complet

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

### 2.1 Ouvrir un terminal dans le dossier du projet

```bash
cd /Users/arnaudcrepieux/Cursor/Whisperx-Runpod-2
```

### 2.2 Se connecter à Docker Hub

```bash
docker login
```

### 2.3 Construire l'image Docker

**Option A : Sans pré-téléchargement des modèles de diarisation** (plus petit, modèles téléchargés au premier lancement)

```bash
docker build -t VOTRE_USERNAME_DOCKER/whisperx-runpod:latest .
```

**Option B : Avec pré-téléchargement des modèles** (recommandé, démarrage plus rapide)

```bash
docker build --build-arg HF_TOKEN=hf_votre_token_ici -t VOTRE_USERNAME_DOCKER/whisperx-runpod:latest .
```

> ⚠️ Remplacez `VOTRE_USERNAME_DOCKER` par votre nom d'utilisateur Docker Hub
> ⚠️ Remplacez `hf_votre_token_ici` par votre token Hugging Face

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

## Coûts estimés

- **Construction Docker** : Gratuit (sur votre machine)
- **RunPod Serverless** :
  - RTX 4090 : ~$0.00044/seconde
  - RTX 3090 : ~$0.00031/seconde
  - Transcription d'un audio de 10 min : ~$0.02-0.05

## Support

- WhisperX : [github.com/m-bain/whisperX](https://github.com/m-bain/whisperX)
- RunPod : [docs.runpod.io](https://docs.runpod.io)
