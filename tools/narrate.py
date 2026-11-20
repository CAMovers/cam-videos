"""Narrate a video script with Google Cloud Text-to-Speech (Chirp 3 HD).

Usage: python tools/narrate.py narration/<slug>
Reads narration/<slug>/script.txt (blank line between scenes) and optional
narration/<slug>/voice.txt (voice name, default en-US-Chirp3-HD-Aoede).
Writes narration/<slug>/vo/01.mp3, 02.mp3, ...
Needs env GOOGLE_TTS_API_KEY (a Google Cloud API key restricted to Text-to-Speech).
"""
import base64, json, os, pathlib, sys, urllib.request

def main(folder):
    d = pathlib.Path(folder)
    text = (d / "script.txt").read_text(encoding="utf-8")
    voice = "en-US-Chirp3-HD-Aoede"
    if (d / "voice.txt").exists():
        voice = (d / "voice.txt").read_text().strip() or voice
    scenes = [p.strip() for p in text.split("\n\n") if p.strip()]
    key = os.environ["GOOGLE_TTS_API_KEY"]
    out = d / "vo"
    out.mkdir(exist_ok=True)
    for i, scene in enumerate(scenes, 1):
        body = json.dumps({
            "input": {"text": scene},
            "voice": {"languageCode": voice[:5], "name": voice},
            "audioConfig": {"audioEncoding": "MP3", "sampleRateHertz": 24000},
        }).encode()
        req = urllib.request.Request(
            "https://texttospeech.googleapis.com/v1/text:synthesize?key=" + key,
            data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            audio = json.load(r)["audioContent"]
        (out / f"{i:02d}.mp3").write_bytes(base64.b64decode(audio))
        print(f"scene {i}: {len(scene)} chars")
    print(f"done: {len(scenes)} clips, voice {voice}")

if __name__ == "__main__":
    main(sys.argv[1])
