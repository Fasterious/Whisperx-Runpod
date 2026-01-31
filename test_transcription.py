#!/usr/bin/env python3
"""
Script pour tester la transcription WhisperX sur RunPod.
Usage: python3 test_transcription.py <URL_AUDIO>

Configuration:
  Créez un fichier .env avec:
    RUNPOD_API_KEY=votre_clé_api
    RUNPOD_ENDPOINT_ID=votre_endpoint_id
"""

import os
import sys
import time
import json
import requests
import argparse
from pathlib import Path


def load_env():
    """Charge les variables depuis le fichier .env"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


# Charger le fichier .env
load_env()

# ============================================
# CONFIGURATION (depuis .env ou variables d'environnement)
# ============================================
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "")
# ============================================


def run_transcription(audio_url: str, options: dict = None) -> dict:
    """Lance une transcription sur RunPod et attend le résultat."""
    options = options or {}
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }
    
    data = {
        "input": {
            "audio": audio_url,
            **options
        }
    }
    
    # Lancer le job
    print(f"🚀 Lancement de la transcription...")
    response = requests.post(
        f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run",
        headers=headers,
        json=data
    )
    
    if response.status_code != 200:
        raise Exception(f"Erreur API: {response.status_code} - {response.text}")
    
    result = response.json()
    job_id = result.get('id')
    print(f"📋 Job ID: {job_id}")
    
    # Attendre le résultat
    print("⏳ En attente du résultat...")
    while True:
        status_response = requests.get(
            f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status/{job_id}",
            headers=headers
        )
        
        status_result = status_response.json()
        status = status_result.get('status')
        
        if status == 'COMPLETED':
            print("✅ Transcription terminée!")
            return status_result.get('output', {})
        elif status == 'FAILED':
            print("❌ Échec de la transcription")
            print(json.dumps(status_result, indent=2))
            return status_result
        elif status == 'IN_QUEUE':
            print("  ⏳ En file d'attente...")
        elif status == 'IN_PROGRESS':
            print("  🔄 En cours de traitement...")
        
        time.sleep(5)


def main():
    parser = argparse.ArgumentParser(
        description="Transcription audio avec WhisperX sur RunPod",
        epilog="Exemple: python3 test_transcription.py https://example.com/audio.mp3"
    )
    parser.add_argument("audio_url", help="URL de l'audio à transcrire")
    parser.add_argument("--language", "-l", help="Code langue (ex: fr, en)")
    parser.add_argument("--no-diarize", action="store_true", help="Désactiver la diarisation")
    parser.add_argument("--min-speakers", type=int, help="Nombre minimum de locuteurs")
    parser.add_argument("--max-speakers", type=int, help="Nombre maximum de locuteurs")
    parser.add_argument("--output", "-o", help="Fichier de sortie JSON")
    
    args = parser.parse_args()
    
    # Vérifier la configuration
    if not RUNPOD_API_KEY:
        print("❌ Erreur: RUNPOD_API_KEY non configuré!")
        print("   Créez un fichier .env avec: RUNPOD_API_KEY=votre_clé")
        sys.exit(1)
    if not RUNPOD_ENDPOINT_ID:
        print("❌ Erreur: RUNPOD_ENDPOINT_ID non configuré!")
        print("   Créez un fichier .env avec: RUNPOD_ENDPOINT_ID=votre_endpoint")
        sys.exit(1)
    
    print(f"🔗 URL audio: {args.audio_url}\n")
    
    # Options
    options = {}
    if args.language:
        options["language"] = args.language
    if args.no_diarize:
        options["diarize"] = False
    if args.min_speakers:
        options["min_speakers"] = args.min_speakers
    if args.max_speakers:
        options["max_speakers"] = args.max_speakers
    
    # Lancer la transcription
    try:
        result = run_transcription(args.audio_url, options)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
    
    # Afficher le résultat
    print("\n" + "="*60)
    print("📝 RÉSULTAT DE LA TRANSCRIPTION")
    print("="*60)
    
    output = result.get("output", result) if isinstance(result, dict) else result
    
    if isinstance(output, dict):
        if "speaker_text" in output:
            print("\n🗣️  Transcription avec locuteurs:\n")
            print(output["speaker_text"])
        elif "text" in output:
            print("\n📄 Transcription:\n")
            print(output["text"])
        
        if "language" in output:
            print(f"\n🌍 Langue détectée: {output['language']}")
    else:
        print(output)
    
    # Sauvegarder en JSON
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Résultat sauvegardé: {args.output}")
    
    print("\n✅ Terminé!")


if __name__ == "__main__":
    main()
