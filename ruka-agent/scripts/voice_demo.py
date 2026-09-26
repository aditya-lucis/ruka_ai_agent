# -*- coding: utf-8 -*-
"""Demo Interaktif Suara Ruka (TTS & Voice Response)
Jalankan: python scripts/voice_demo.py
"""
from __future__ import annotations
import sys
import winsound
from pathlib import Path

# Pastikan akar proyek masuk ke sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google import genai
from src.config import load_config
from src.multimodal.voice_out import VoiceOut
from src.application.ruka_app import RukaApp

def main():
    print("=" * 60)
    print("  RUKA VOICE INTERACTION — THE AWAKENED MARQUIS")
    print("  Model TTS: gemini-3.1-flash-tts-preview | Voice: Sulafat")
    print("=" * 60 + "\n")

    cfg = load_config()
    raw_client = genai.Client(api_key=cfg.api_key)
    voice_out = VoiceOut(raw_client, cfg)
    app = RukaApp()

    out_dir = Path("data/voice")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Ketik pertanyaan/sapaan ke Ruka (ketik 'exit' untuk keluar):")
    while True:
        try:
            text = input("\nMy Lord > ").strip()
            if not text:
                continue
            if text.lower() in ("exit", "keluar", "quit", "q"):
                farewell = "Selamat beristirahat, My Lord. Istana tetap terjaga."
                print(f"\nRuka: '{farewell}'")
                wav = voice_out.speak(farewell, tone_hint="warm, calm", out_path=out_dir / "farewell.wav")
                winsound.PlaySound(str(wav), winsound.SND_FILENAME)
                break

            print("[1/2] Ruka sedang memproses tanggapan kognitif...")
            answer = app.handle("user-voice", text)
            print(f"\n[Ruka]: {answer}\n")

            print("[2/2] Menggenerasi suara (TTS - Sulafat)...")
            wav_path = voice_out.speak(answer, tone_hint="calm, aristocratic", out_path=out_dir / "ruka_response.wav")
            print(f"-> Audio tersimpan di: {wav_path}")
            
            print("-> Memutar audio Ruka...")
            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)

        except (KeyboardInterrupt, EOFError):
            print("\nSesi diakhiri.")
            break
        except Exception as e:
            print(f"\n[Error Voice]: {e}")

if __name__ == "__main__":
    main()
