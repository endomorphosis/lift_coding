#!/usr/bin/env python3
"""Dev helper script demonstrating TTS integration with the dev loop.

This script shows how to:
1. Submit a command to /v1/command
2. Extract the spoken_text from the response
3. Call /v1/tts to convert it to audio
4. Save the audio file locally

Usage:
    python dev/tts_demo.py "inbox"
    python dev/tts_demo.py "summarize pr 123"
    python dev/tts_demo.py --text "Custom text to synthesize"
"""

import argparse
import sys
from pathlib import Path

import httpx


def submit_command(base_url: str, command_text: str) -> dict:
    """Submit a command to the API and return the response.

    Args:
        base_url: Base URL of the API (e.g., http://localhost:8080)
        command_text: Command text to send

    Returns:
        Command response as a dict
    """
    url = f"{base_url}/v1/command"
    payload = {
        "input": {"type": "text", "text": command_text},
        "profile": "default",
        "client_context": {
            "device": "simulator",
            "locale": "en-US",
            "timezone": "America/Los_Angeles",
            "app_version": "0.1.0",
            "noise_mode": False,
        },
        "idempotency_key": f"tts-demo-{hash(command_text)}",
    }

    response = httpx.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def synthesize_speech(base_url: str, text: str, format: str = "wav") -> bytes:
    """Convert text to speech using the TTS API.

    Args:
        base_url: Base URL of the API
        text: Text to synthesize
        format: Audio format (wav or mp3)

    Returns:
        Audio bytes
    """
    url = f"{base_url}/v1/tts"
    payload = {
        "text": text,
        "format": format,
    }

    response = httpx.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.content


def save_audio(audio_bytes: bytes, filename: str) -> None:
    """Save audio bytes to a file.

    Args:
        audio_bytes: Audio data to save
        filename: Output filename
    """
    output_path = Path(filename)
    output_path.write_bytes(audio_bytes)
    print(f"✅ Audio saved to: {output_path.absolute()}")


def play_audio(filename: str) -> None:
    """Attempt to play the audio file using system tools.

    Args:
        filename: Path to audio file

    Note:
        This is best-effort and may not work on all systems.
        On macOS: uses 'afplay'
        On Linux: tries 'aplay', 'paplay', or 'ffplay'
        On Windows: tries 'start'
    """
    import platform
    import shutil
    import subprocess

    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            if shutil.which("afplay"):
                subprocess.run(["afplay", filename], check=True)
                print("🔊 Playing audio...")
                return
        elif system == "Linux":
            for player in ["aplay", "paplay", "ffplay"]:
                if shutil.which(player):
                    subprocess.run([player, filename], check=True)
                    print("🔊 Playing audio...")
                    return
        elif system == "Windows":
            subprocess.run(["start", filename], shell=True, check=True)
            print("🔊 Opening audio...")
            return

        print("⚠️  No audio player found. File saved but cannot auto-play.")
    except Exception as e:
        print(f"⚠️  Could not play audio: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="TTS Demo - Convert command responses to speech")
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to submit (e.g., 'inbox', 'summarize pr 123')",
    )
    parser.add_argument(
        "--text",
        help="Custom text to synthesize (skip command submission)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080",
        help="Base URL of the API (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--format",
        choices=["wav", "mp3"],
        default="wav",
        help="Audio format (default: wav)",
    )
    parser.add_argument(
        "--output",
        help="Output filename (default: auto-generated)",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Attempt to play the audio after saving",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save the audio file (only useful with --play)",
    )

    args = parser.parse_args()

    if not args.command and not args.text:
        parser.error("Either provide a command or use --text")

    try:
        # Step 1: Get text to synthesize
        if args.text:
            print(f"📝 Synthesizing custom text: {args.text[:50]}...")
            text_to_speak = args.text
        else:
            print(f"🚀 Submitting command: {args.command}")
            response = submit_command(args.base_url, args.command)

            print("✅ Command response:")
            print(f"   Status: {response.get('status')}")
            print(f"   Intent: {response.get('intent', {}).get('name')}")

            text_to_speak = response.get("spoken_text", "")
            if not text_to_speak:
                print("❌ No spoken_text in response")
                sys.exit(1)

            print(f"   Spoken text: {text_to_speak[:100]}...")

        # Step 2: Convert to speech
        print(f"\n🎙️  Converting to speech ({args.format} format)...")
        audio_bytes = synthesize_speech(args.base_url, text_to_speak, args.format)
        print(f"✅ Generated {len(audio_bytes)} bytes of audio")

        # Step 3: Save or play
        if not args.no_save:
            if args.output:
                output_file = args.output
            else:
                output_file = f"/tmp/tts_output_{hash(text_to_speak)}.{args.format}"

            save_audio(audio_bytes, output_file)

            if args.play:
                play_audio(output_file)
        elif args.play:
            # Save to temp file for playing
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=f".{args.format}", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name

            play_audio(tmp_path)

        print("\n✨ Done!")

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        try:
            error_detail = e.response.json()
            print(f"   Error: {error_detail.get('error', 'unknown')}")
            print(f"   Message: {error_detail.get('message', 'No message')}")
        except Exception:
            print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
