"""Branded explainer: What movers really cost in Denver (2026). 1920x1080, 30 fps.
Each scene is drawn with PIL and piped to ffmpeg as one mp4; scenes are joined with the concat demuxer."""
import json, os, subprocess, sys, math
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
BG = (246, 247, 251); NAVY = (0, 40, 104); INK = (16, 33, 63); MUTED = (98, 112, 138)
ORANGE = (232, 121, 43); WHITE = (255, 255, 255); LINE = (221, 227, 238); GREEN = (16, 140, 90)
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts') + '/'
P = json.load(open(os.path.join(HERE, 'prices.json')))
def F(w, s): return ImageFont.truetype(FD + {'r': 'Inter-Regular', 'm': 'Inter-Medium', 's': 'Inter-SemiBold', 'b': 'Inter-Bold', 'x': 'Inter-ExtraBold', 'k': 'Inter-Black'}[w] + '.otf', s)
def M(s, wname='Bold'):
    f = ImageFont.truetype(FD + 'Montserrat[wght].ttf', s)
    try: f.set_variation_by_name(wname)
    except Exception: pass
    return f

DUR = json.load(open(os.path.join(HERE, 'out', 'durations.json')))
LOGO = Image.open(os.path.join(HERE, 'logo.png')).convert('RGBA')
def logo(h): return LOGO.resize((int(LOGO.width * h / LOGO.height), h), Image.LANCZOS)
PAD = 0.9

# ---------- element helpers: each returns (RGBA image, x, y) ----------
def text_img(txt, font, fill=INK, pad=4):
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    l, t, r, b = d.textbbox((0, 0), txt, font=font)
    im = Image.new('RGBA', (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), txt, font=font, fill=fill)
    return im
def rich(parts, gap=0):
    """parts: [(text, font, color)] on one baseline."""
    ims = [text_img(t, f, c, pad=0) for t, f, c in parts]
    h = max(i.height for i in ims); w = sum(i.width for i in ims) + gap * (len(ims) - 1)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0)); x = 0
    asc = max(f.getmetrics()[0] for _, f, _ in parts)
    for (t, f, c), im in zip(parts, ims):
        out.alpha_composite(im, (x, asc - f.getmetrics()[0])); x += im.width + gap
    return out
def card(w, h, fill=WHITE, radius=26, outline=LINE, shadow=True):
    im = Image.new('RGBA', (w + 24, h + 24), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if shadow: d.rounded_rectangle((12, 18, w + 12, h + 18), radius, fill=(16, 33, 63, 18))
    d.rounded_rectangle((12, 12, w + 12, h + 12), radius, fill=fill, outline=outline, width=2)
    return im
def pill(txt, font, fg=WHITE, bg=ORANGE, padx=26, pady=14):
    t = text_img(txt, font, fg); im = Image.new('RGBA', (t.width + padx * 2, t.height + pady * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, im.width - 1, im.height - 1), im.height // 2, fill=bg)
    im.alpha_composite(t, (padx, pady)); return im
def check(size=44, color=GREEN):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, size - 1, size - 1), fill=color)
    d.line([(size * .27, size * .52), (size * .44, size * .69), (size * .74, size * .34)], fill=WHITE, width=max(3, size // 9), joint='curve')
    return im

def ease(p): p = max(0.0, min(1.0, p)); return 1 - (1 - p) ** 3

class Scene:
    def __init__(self, sid):
        self.id = sid; self.dur = DUR[sid] + PAD; self.items = []
    def add(self, im, x, y, at, kind='rise', dur=0.55):
        self.items.append(dict(im=im, x=int(x), y=int(y), at=at, kind=kind, d=dur)); return im
    def frame(self, t, base):
        fr = base.copy()
        for it in self.items:
            p = (t - it['at']) / it['d']
            if p <= 0: continue
            e = ease(p); im = it['im']
            if it['kind'] == 'grow':  # bar grows left to right
                w = max(1, int(im.width * e)); fr.alpha_composite(im.crop((0, 0, w, im.height)), (it['x'], it['y'])); continue
            if it['kind'] == 'pop':
                s = 0.85 + 0.15 * e; im2 = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
                a = im2.getchannel('A').point(lambda v, e=e: int(v * e)); im2.putalpha(a)
                fr.alpha_composite(im2, (it['x'] + (im.width - im2.width) // 2, it['y'] + (im.height - im2.height) // 2)); continue
            dy = int((1 - e) * 36) if it['kind'] == 'rise' else 0
            if e < 1:
                im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v, e=e: int(v * e)))
            fr.alpha_composite(im, (it['x'], it['y'] + dy))
        return fr

def base_layer(idx, total, footnote=None):
    im = Image.new('RGBA', (W, H), BG + (255,)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 10), fill=NAVY)
    lg = LOGO.resize((int(LOGO.width * 84 / LOGO.height), 84), Image.LANCZOS); im.alpha_composite(lg, (88, 26))
    wm = rich([('Colorado ', M(30, 'ExtraBold'), NAVY), ('Apartment', M(30, 'ExtraBold'), NAVY), (' Movers', M(30, 'ExtraBold'), ORANGE)])
    im.alpha_composite(wm, (88 + lg.width + 16, 52))
    d.text((W - 96, 60), 'coloradoapartmentmovers.com', font=F('m', 24), fill=MUTED, anchor='ra')
    # progress
    d.rounded_rectangle((96, H - 46, W - 96, H - 40), 3, fill=LINE)
    d.rounded_rectangle((96, H - 46, 96 + int((W - 192) * (idx + 1) / total), H - 40), 3, fill=ORANGE)
    if footnote: d.text((96, H - 92), footnote, font=F('r', 22), fill=MUTED)
    return im

TOTAL = 9
def heading(sc, txt, at=0.15, y=150, size=72):
    return sc.add(text_img(txt, F('x', size), NAVY), 96, y, at)

def build():
    S = []
    # 1 hook
    sc = Scene('hook'); S.append((sc, '*Published hourly rates of established Denver moving companies, 2 movers + truck, Nov 2026'))
    sc.add(pill('DENVER  ·  2026', F('b', 26)), 96, 210, 0.1)
    sc.add(text_img('What movers', F('k', 132), NAVY), 90, 300, 0.3)
    sc.add(text_img('really cost.', F('k', 132), ORANGE), 90, 450, 0.6)
    c = card(820, 230); d = ImageDraw.Draw(c)
    d.text((52, 46), 'Big Denver movers*', font=F('s', 34), fill=MUTED)
    d.text((52, 100), '$170–$200/hr', font=F('x', 84), fill=INK)
    sc.add(c, 1000, 330, 2.2, 'pop')
    sc.add(text_img('for 2 movers and a truck', F('m', 34), MUTED), 1064, 590, 2.9)
    sc.add(text_img('Here’s what a move should cost — and how to pay less.', F('s', 44), INK), 96, 760, 9.4)
    # 2 how
    sc = Scene('how'); S.append((sc, None))
    heading(sc, 'How Denver moves are priced')
    labels = [('Hourly crew rate', 'Every minute runs on it', True), ('Truck', 'Flat or built into the rate', False), ('Travel', 'Miles and drive time', False)]
    for i, (a, b, hot) in enumerate(labels):
        c = card(520, 330, fill=NAVY if hot else WHITE, outline=NAVY if hot else LINE); d = ImageDraw.Draw(c)
        d.text((52, 54), f'0{i + 1}', font=F('b', 34), fill=ORANGE)
        d.text((52, 120), a, font=F('x', 48), fill=WHITE if hot else INK)
        d.text((52, 200), b, font=F('m', 30), fill=(200, 212, 235) if hot else MUTED)
        sc.add(c, 96 + i * 580, 360, 1.6 + i * 1.1, 'rise')
    sc.add(pill('The hourly rate matters most', F('b', 32)), 96, 790, 8.6)
    # 3 ours
    sc = Scene('ours'); S.append((sc, 'Prices from coloradoapartmentmovers.com/pricing, Nov 2026'))
    heading(sc, 'Our rates')
    c = card(640, 560, fill=NAVY, outline=NAVY); d = ImageDraw.Draw(c)
    d.text((60, 70), '$40', font=F('k', 220), fill=WHITE)
    d.text((66, 330), 'per mover, per hour', font=F('s', 40), fill=(200, 212, 235))
    d.rounded_rectangle((60, 420, 420, 500), 40, fill=ORANGE); d.text((240, 460), '2 movers = $80/hr', font=F('b', 34), fill=WHITE, anchor='mm')
    sc.add(c, 96, 270, 0.6, 'pop')
    rows = [('Truck', '$80  (15 ft)  ·  $130  (26 ft)', 7.2), ('Service fee', '$40 once', 12.9), ('Minimum', '1 hour, then 30-min steps', 14.7), ('Travel', '30 min free, then $5/mover per 7.5 min', 20.7), ('Included', 'Blankets, dollies, ratchet straps', 28.8)]
    for i, (a, b, at) in enumerate(rows):
        c = card(1000, 118); d = ImageDraw.Draw(c)
        d.text((44, 38), a, font=F('s', 34), fill=MUTED)
        fs = 40
        while d.textlength(b, font=F('b', fs)) > 640: fs -= 1
        d.text((330, 34 + (40 - fs) // 2), b, font=F('b', fs), fill=INK)
        sc.add(c, 790, 270 + i * 128, at)
    # 4 totals
    sc = Scene('totals'); S.append((sc, f"Typical totals: ground level, within a 30-minute drive of Littleton, with the recommended shrink wrap. Based on what our moves actually took. Prices as of {P['as_of']}."))
    heading(sc, 'Typical totals')
    T = DUR['totals']  # bar timings follow the narration (fractions measured on the Nov 22 voice-over)
    sizes = [(r['label'], r['low'], r['high'], r['crew'], T * f) for r, f in zip(P['totals'], (0.127, 0.392, 0.589, 0.796))]
    x0, x1 = 560, 1430; vmax = (max(r['high'] for r in P['totals']) // 100 + 1) * 100
    for i, (lab, lo, hi, crew, at) in enumerate(sizes):
        y = 300 + i * 165
        sc.add(text_img(lab, F('b', 42), INK), 96, y + 6, at)
        sc.add(text_img(crew, F('m', 28), MUTED), 98, y + 66, at + 0.1)
        ax = x0 + (x1 - x0) * lo / vmax; bx = x0 + (x1 - x0) * hi / vmax
        bar = Image.new('RGBA', (int(bx - ax), 70), (0, 0, 0, 0)); ImageDraw.Draw(bar).rounded_rectangle((0, 0, bar.width - 1, 69), 35, fill=ORANGE if i == 0 else NAVY)
        track = Image.new('RGBA', (x1 - x0, 70), (0, 0, 0, 0)); ImageDraw.Draw(track).rounded_rectangle((0, 0, x1 - x0 - 1, 69), 35, fill=LINE)
        sc.add(track, x0, y, at, 'fade', 0.3); sc.add(bar, ax, y, at + 0.2, 'grow', 0.9)
        lbl = text_img(f'${lo:,}–${hi:,}', F('x', 40), WHITE if (bx - ax) > 330 else INK)
        lx = ax + 26 if (bx - ax) > 330 else bx + 18
        sc.add(lbl, lx, y + 9, at + 0.8, 'fade', 0.4)
    # 5 time
    sc = Scene('time'); S.append((sc, None))
    heading(sc, 'What changes your number: time')
    items = [('Stairs', 'about +0.5 hr per flight (2 movers)', 3.0), ('Elevators', 'reserve yours ahead', 7.2), ('Long walks', 'from the truck to your door', 8.6)]
    for i, (a, b, at) in enumerate(items):
        c = card(520, 300); d = ImageDraw.Draw(c)
        d.ellipse((52, 50, 132, 130), fill=(255, 237, 224)); d.text((92, 90), str(i + 1), font=F('x', 40), fill=ORANGE, anchor='mm')
        d.text((52, 160), a, font=F('x', 50), fill=INK); d.text((52, 232), b, font=F('m', 28), fill=MUTED)
        sc.add(c, 96 + i * 580, 340, at)
    sc.add(pill('You enter it when you book, so it’s in your estimate', F('b', 32), WHITE, NAVY), 96, 760, 10.8)
    # 6 compare
    sc = Scene('compare'); S.append((sc, '*Big company: $170/hr published weekday rate for 2 movers (Saturday $200/hr), Nov 2026. Ours: 4 hr × $80 + $80 truck + $40 fee + $30 wrap.'))
    heading(sc, 'A 4-hour move, 2 movers, weekday')
    for i, (lab, val, at, col) in enumerate([('Big Denver mover*', 680, 1.2, (150, 160, 182)), ('Colorado Apartment Movers', P['compare_ours'], 8.0, ORANGE)]):
        y = 330 + i * 220
        sc.add(text_img(lab, F('b', 40), INK), 96, y, at)
        w = int(1250 * val / 700)
        bar = Image.new('RGBA', (w, 100), (0, 0, 0, 0)); ImageDraw.Draw(bar).rounded_rectangle((0, 0, w - 1, 99), 24, fill=col)
        sc.add(bar, 96, y + 64, at + 0.2, 'grow', 1.0)
        sc.add(text_img(f'${val}', F('k', 64), WHITE), 96 + w - 200, y + 72, at + 1.0, 'fade', 0.4)
    sc.add(pill(f"You save about ${680 - P['compare_ours']}", F('x', 40), WHITE, GREEN), 1420, 620, 10.4, 'pop')
    sc.add(text_img('Saturday at a big company: about $800', F('s', 34), MUTED), 96, 850, 14.2)
    # 7 why
    sc = Scene('why'); S.append((sc, None))
    heading(sc, 'Why it costs less')
    steps = ['Booking', 'Scheduling', 'Contracts', 'Billing']
    for i, s in enumerate(steps):
        c = card(380, 150); d = ImageDraw.Draw(c); d.text((202, 87), s, font=F('x', 44), fill=INK, anchor='mm')
        sc.add(c, 96 + i * 440, 380, 4.2 + i * 0.6, 'pop')
    sc.add(text_img('all online, not a big office', F('s', 44), MUTED), 96, 590, 6.8)
    sc.add(pill('You pay for movers, not overhead.', F('x', 52), WHITE, NAVY, 40, 22), 96, 740, 8.6, 'pop')
    # 8 tips
    sc = Scene('tips'); S.append((sc, None))
    heading(sc, 'Pay even less')
    tips = [('Be packed before the crew arrives', 1.6), ('Reserve your elevator', 4.2), ('Save a parking spot near the door', 5.9), ('Move mid-month on a weekday', 8.3)]
    for i, (t, at) in enumerate(tips):
        sc.add(check(64), 96, 320 + i * 150, at, 'pop'); sc.add(text_img(t, F('b', 50), INK), 190, 324 + i * 150, at + 0.1)
    # 9 cta
    sc = Scene('cta'); S.append((sc, None))
    sc.add(logo(560), 1260, 300, 1.0, 'pop')
    sc.add(text_img('See your estimate', F('k', 108), NAVY), 90, 250, 0.2)
    sc.add(text_img('in about 5 minutes.', F('k', 108), ORANGE), 90, 390, 0.6)
    sc.add(pill('coloradoapartmentmovers.com', F('x', 52), WHITE, NAVY, 44, 24), 96, 620, 2.0, 'pop')
    sc.add(text_img('Call or text (720) 253-6499', F('b', 54), INK), 96, 790, 5.6)
    sc.add(text_img('Moves from $350  ·  No deposit  ·  1-hour minimum', F('s', 34), MUTED), 96, 880, 6.4)
    return S

def render(only=None, stills=None):
    S = build(); os.chdir(HERE); os.makedirs('out', exist_ok=True)
    for i, (sc, foot) in enumerate(S):
        if only and sc.id not in only: continue
        base = base_layer(i, len(S), foot)
        if stills is not None:
            sc.frame(sc.dur - 0.5, base).convert('RGB').save(f'out/still_{sc.id}.jpg', quality=90); continue
        n = int(round(sc.dur * FPS)); tmp = f'out/{sc.id}.part.mp4'
        fade = f"fade=t=in:st=0:d=0.3:color=0xF6F7FB,fade=t=out:st={sc.dur - 0.3:.2f}:d=0.3:color=0xF6F7FB"
        p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                              '-vf', fade, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-f', 'mp4', tmp], stdin=subprocess.PIPE)
        for f in range(n):
            p.stdin.write(sc.frame(f / FPS, base).convert('RGB').tobytes())
        p.stdin.close(); assert p.wait() == 0; os.replace(tmp, f'out/{sc.id}.mp4'); print('scene', sc.id, round(sc.dur, 2), flush=True)
    return S

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'stills': render(stills=True)
    else: render(sys.argv[1:] or None)
