"""Narrate a video script, one MP3 per scene.

Usage: python tools/narrate.py narration/<slug>
Reads narration/<slug>/script.txt (blank line between scenes) and optional
narration/<slug>/voice.txt. Writes narration/<slug>/vo/01.mp3, 02.mp3, ...

Voices (voice.txt):
  (empty or missing)      ElevenLabs "Melanie" (h2OBoQqre8SPfGehinER), the
                          same voice as Casey on the phones. Default since
                          Nov 25, 2026 (Musa: "switch to the ElevenLabs voice").
  elevenlabs:<voice_id>   any other ElevenLabs voice
  elevenlabs:<voice_id>:<model>   e.g. ...:eleven_v3 (expressive; supports [tags])
  en-US-Chirp3-HD-Aoede   (any Google voice name) Google Cloud Text-to-Speech

Env:
  ELEVENLABS_API_KEY   for ElevenLabs voices (repo secret)
  GOOGLE_TTS_API_KEY   for Google voices, and the fallback if the ElevenLabs
                       key is missing
"""
import base64, json, os, pathlib, sys, urllib.request

MELANIE = "h2OBoQqre8SPfGehinER"
ELEVEN_MODEL = "eleven_multilingual_v2"
GOOGLE_DEFAULT = "en-US-Chirp3-HD-Aoede"


def eleven(scene, voice_id, prev_text, next_text, key, model=ELEVEN_MODEL):
    body = {
        "text": scene,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75,
                           "style": 0.15, "use_speaker_boost": True},
    }
    if model in ("eleven_v3", "eleven_v4"):
        # Expressive models: looser settings, no context stitching.
        body["voice_settings"] = {"stability": 0.5, "similarity_boost": 0.75}
        prev_text = next_text = ""
    # Neighbouring scenes keep the tone and pacing even across clips.
    if prev_text:
        body["previous_text"] = prev_text
    if next_text:
        body["next_text"] = next_text
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        "?output_format=mp3_44100_128",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "xi-api-key": key,
                 "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def google(scene, voice, key):
    body = json.dumps({
        "input": {"text": scene},
        "voice": {"languageCode": voice[:5], "name": voice},
        "audioConfig": {"audioEncoding": "MP3", "sampleRateHertz": 24000},
    }).encode()
    req = urllib.request.Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize?key=" + key,
        data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return base64.b64decode(json.load(r)["audioContent"])


def pick_voice(d):
    raw = ""
    if (d / "voice.txt").exists():
        raw = (d / "voice.txt").read_text().strip()
    if raw.startswith("elevenlabs:"):
        return "eleven", raw.split(":", 1)[1].strip() or MELANIE
    if raw:
        return "google", raw
    return "eleven", MELANIE


def main(folder):
    d = pathlib.Path(folder)
    text = (d / "script.txt").read_text(encoding="utf-8")
    scenes = [p.strip() for p in text.split("\n\n") if p.strip()]
    engine, voice = pick_voice(d)
    model = ELEVEN_MODEL
    if engine == "eleven" and ":" in voice:  # elevenlabs:<voice_id>:<model>
        voice, model = voice.split(":", 1)
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if engine == "eleven" and not eleven_key:
        print("ELEVENLABS_API_KEY not set: falling back to Google " + GOOGLE_DEFAULT)
        engine, voice = "google", GOOGLE_DEFAULT
    out = d / "vo"
    out.mkdir(exist_ok=True)
    for i, scene in enumerate(scenes, 1):
        if engine == "eleven":
            prev_text = scenes[i - 2] if i > 1 else ""
            next_text = scenes[i] if i < len(scenes) else ""
            audio = eleven(scene, voice, prev_text, next_text, eleven_key, model)
        else:
            audio = google(scene, voice, os.environ["GOOGLE_TTS_API_KEY"])
        (out / f"{i:02d}.mp3").write_bytes(audio)
        print(f"scene {i}: {len(scene)} chars")
    print(f"done: {len(scenes)} clips, {engine} voice {voice}")


if __name__ == "__main__":
    main(sys.argv[1])
