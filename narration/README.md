Put a video script at narration/<slug>/script.txt (blank line between scenes).
Optional narration/<slug>/voice.txt with a Google voice name (default en-US-Chirp3-HD-Aoede).
Pushing it runs the "Narrate video scripts" action, which commits narration/<slug>/vo/01.mp3, 02.mp3, ...
Needs the repository secret GOOGLE_TTS_API_KEY.
