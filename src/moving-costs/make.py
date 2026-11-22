"""Rebuild "What Movers Really Cost in Denver" with current prices (quarterly task, from Mar 2, 2027).

Steps (run from the repo root, CAMovers/cam-videos):
  1. Edit src/moving-costs/prices.json with the live /pricing numbers (totals per home size, as_of date).
  2. python3 src/moving-costs/make.py script <slug>
       writes narration/<slug>/script.txt (the totals scene only). Commit + push it; the GitHub Action
       "Narrate video scripts" adds narration/<slug>/vo/01.mp3 in ~30 s (gh run list -R CAMovers/cam-videos; git pull).
  3. python3 src/moving-costs/make.py render <slug>
       uses that mp3 as the totals voice-over, keeps the other 8 scenes' voice-over (src/moving-costs/audio),
       renders all scenes, and writes src/moving-costs/out/<slug>.mp4 plus out/check_totals.jpg to look at.
  4. Copy the mp4 to videos/<slug>.mp4, commit with [skip ci], push, upload with Zapier YouTube upload_video
     using https://raw.githubusercontent.com/CAMovers/cam-videos/main/videos/<slug>.mp4

If the hourly rate, truck, service fee or wrap price changed, the 4-hour comparison scene ($470 in the
voice-over, scene 06) and the rates scene (03) are out of date too: stop and tell Musa instead of rendering.
"""
import json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ORDER = ['hook', 'how', 'ours', 'totals', 'time', 'compare', 'why', 'tips', 'cta']
PAD = 0.9

ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = 'zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()


def two(n):
    if n < 20:
        return ONES[n]
    return TENS[n // 10] + ('' if n % 10 == 0 else ' ' + ONES[n % 10])


def say(n):
    """Prices the way people say them: 350 'three fifty', 1250 'twelve fifty', 2020 'two thousand twenty'."""
    if n >= 2000 and n % 1000 < 100:
        return two(n // 1000) + ' thousand' + ('' if n % 1000 == 0 else ' ' + two(n % 1000))
    hi, lo = divmod(n, 100)
    if lo == 0:
        return two(hi) + ' hundred'
    return two(hi) + ' ' + (('oh ' + ONES[lo]) if lo < 10 else two(lo))


def totals_line(p):
    t = {r['key']: r for r in p['totals']}
    r = lambda k: f"{say(t[k]['low'])} to {say(t[k]['high'])}"
    return ("So what does that add up to? Based on what our moves actually took, a studio or one bedroom runs about "
            f"{r('1br')}. A two bedroom, about {r('2br')}. Three bedrooms, about {r('3br')}. "
            f"And four bedrooms, about {r('4br')}.")


def dur(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]).decode().strip())


def main():
    cmd, slug = sys.argv[1], sys.argv[2]
    p = json.load(open(os.path.join(HERE, 'prices.json')))
    if cmd == 'script':
        d = os.path.join(ROOT, 'narration', slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'script.txt'), 'w').write(totals_line(p) + '\n')
        print(totals_line(p))
        return
    if cmd != 'render':
        sys.exit('usage: make.py script|render <slug>')
    vo = os.path.join(ROOT, 'narration', slug, 'vo', '01.mp3')
    if not os.path.exists(vo):
        sys.exit(f'missing {vo}: push the script and git pull after the narration Action')
    out = os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    audio = [os.path.join(HERE, 'audio', f'{i:02d}.mp3') for i in range(1, 10)]
    audio[3] = vo
    durations = {s: round(dur(a), 2) for s, a in zip(ORDER, audio)}
    json.dump(durations, open(os.path.join(out, 'durations.json'), 'w'))
    subprocess.run([sys.executable, os.path.join(HERE, 'render.py')], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, 'render.py'), 'stills'], check=True)
    shutil.copy(os.path.join(out, 'still_totals.jpg'), os.path.join(out, 'check_totals.jpg'))
    parts = []
    for s, a in zip(ORDER, audio):
        w = os.path.join(out, f'a_{s}.wav')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', a, '-af', f'apad,atrim=0:{durations[s] + PAD:.3f}', '-ar', '48000', '-ac', '2', w], check=True)
        parts.append(w)
    open(os.path.join(out, 'vlist.txt'), 'w').write(''.join(f"file '{s}.mp4'\n" for s in ORDER))
    open(os.path.join(out, 'alist.txt'), 'w').write(''.join(f"file '{os.path.basename(w)}'\n" for w in parts))
    os.chdir(out)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'vlist.txt', '-c', 'copy', 'video.mp4'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'alist.txt', '-c:a', 'pcm_s16le', 'audio.wav'], check=True)
    final = f'{slug}.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', 'video.mp4', '-i', 'audio.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-af', 'loudnorm=I=-16:TP=-1.5', '-shortest', final], check=True)
    starts, t = {}, 0.0
    for s in ORDER:
        starts[s] = t
        t += durations[s] + PAD
    chapters = [('hook', 'What movers cost in Denver'), ('how', 'How Denver moves are priced'), ('ours', 'Our rates: $40 per mover per hour'),
                ('totals', 'Typical totals by home size'), ('time', 'What changes your price: stairs, elevators, long walks'),
                ('compare', '4-hour move: big company vs us'), ('why', 'Why it costs less'), ('tips', '4 ways to pay less'), ('cta', 'See your estimate')]
    print(os.path.join(out, final), round(dur(final), 1), 's')
    print('Chapters')
    for s, name in chapters:
        m, sec = divmod(int(starts[s]), 60)
        print(f'{m}:{sec:02d} {name}')


if __name__ == '__main__':
    main()
