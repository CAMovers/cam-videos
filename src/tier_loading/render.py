"""Render 'How Pro Movers Load a Box Truck (Tier Loading)'.

Canva AI scene images (1920x1080) + ElevenLabs Melanie narration (one clip per
scene) + Colorado Apartment Movers branding (logo bug, caption bar, title and
end cards). One encoded file per scene, joined with the concat demuxer.
Usage: python render.py <images_dir> <vo_dir> <out.mp4>
"""
import os, subprocess, sys, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
NAVY = (18, 38, 66)
ORANGE = (242, 140, 40)
WHITE = (255, 255, 255)
FONT = "/usr/share/fonts/truetype/google-fonts/ofl/montserrat/Montserrat[wght].ttf"

CAPTIONS = [
    ("TIER LOADING", "How pro movers load a box truck"),
    ("TIP 1", "Build tiers floor to ceiling, wall to wall"),
    ("TIP 2", "Heaviest pieces first, at the cab end"),
    ("TIP 3", "Mattresses bagged and upright along the walls"),
    ("TIP 4", "Heavy bottom  •  medium middle  •  light top"),
    ("TIP 5", "Couches on end, fully wrapped. Protect glass and screens"),
    ("TIP 6", "Fill the gaps with soft items"),
    ("TIP 7", "Strap every tier before starting the next"),
    ("THE RULE", "Protected. Supported. Secured."),
    None,  # end card
]


def font(size, weight=700):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def logo_disc(path, d):
    im = Image.open(path).convert("RGBA").resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
    out = Image.new("RGBA", (d + 12, d + 12), (0, 0, 0, 0))
    ring = ImageDraw.Draw(out)
    ring.ellipse((0, 0, d + 11, d + 11), fill=WHITE + (255,))
    out.paste(im, (6, 6), mask)
    return out


def overlay(i, logo_path):
    """Transparent PNG drawn over the moving image."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    cap = CAPTIONS[i]
    if cap is None:
        # End card: dark gradient, big logo, name, promise, website.
        grad = Image.new("L", (1, H))
        for y in range(H):
            grad.putpixel((0, y), int(120 + 110 * y / H))
        shade = Image.new("RGBA", (W, H), NAVY + (0,))
        shade.putalpha(grad.resize((W, H)))
        ov.alpha_composite(shade)
        lg = logo_disc(logo_path, 300)
        ov.alpha_composite(lg, ((W - lg.width) // 2, 150))
        lines = [
            ("Colorado Apartment Movers", font(78, 800), WHITE, 500),
            ("Blankets, dollies and ratchet straps included", font(42, 600), WHITE, 610),
            ("Every charge in your estimate before you book", font(42, 600), WHITE, 668),
            ("coloradoapartmentmovers.com", font(64, 800), ORANGE, 780),
        ]
        for text, f, col, y in lines:
            w = dr.textlength(text, font=f)
            dr.text(((W - w) / 2, y), text, font=f, fill=col)
        return ov
    kicker, line = cap
    if i == 0:
        # Title card: centered panel.
        f1, f2 = font(120, 900), font(56, 600)
        pw = max(dr.textlength(kicker, font=f1), dr.textlength(line, font=f2)) + 140
        x0, y0 = (W - pw) / 2, 330
        dr.rounded_rectangle((x0, y0, x0 + pw, y0 + 330), 28, fill=NAVY + (225,))
        dr.rectangle((x0, y0 + 318, x0 + pw, y0 + 330), fill=ORANGE + (255,))
        w = dr.textlength(kicker, font=f1)
        dr.text(((W - w) / 2, y0 + 50), kicker, font=f1, fill=WHITE)
        w = dr.textlength(line, font=f2)
        dr.text(((W - w) / 2, y0 + 205), line, font=f2, fill=ORANGE)
    else:
        # Lower-third caption bar.
        fk, fl = font(34, 800), font(54, 700)
        tw = dr.textlength(line, font=fl)
        x0, y0 = 90, H - 250
        dr.rounded_rectangle((x0, y0, x0 + tw + 90, y0 + 150), 22, fill=NAVY + (230,))
        dr.rounded_rectangle((x0, y0, x0 + 14, y0 + 150), 7, fill=ORANGE + (255,))
        dr.text((x0 + 48, y0 + 18), kicker, font=fk, fill=ORANGE)
        dr.text((x0 + 48, y0 + 62), line, font=fl, fill=WHITE)
    # Logo bug + name, top right, on every scene but the end card.
    lg = logo_disc(logo_path, 110)
    ov.alpha_composite(lg, (W - lg.width - 50, 40))
    f = font(30, 800)
    name = "Colorado Apartment Movers"
    w = dr.textlength(name, font=f)
    dr.rounded_rectangle((W - lg.width - 70 - w - 40, 70, W - lg.width - 60, 130), 30, fill=NAVY + (210,))
    dr.text((W - lg.width - 70 - w - 20, 82), name, font=f, fill=WHITE)
    return ov


def dur(p):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", p])
    return float(out)


def main(img_dir, vo_dir, out):
    work = os.path.join(os.path.dirname(os.path.abspath(out)), "parts")
    os.makedirs(work, exist_ok=True)
    logo = os.path.join(img_dir, "logo.png")
    parts = []
    for i in range(10):
        img = os.path.join(img_dir, f"s{i+1:02d}.jpg")
        vo = os.path.join(vo_dir, f"{i+1:02d}.mp3")
        lead = 0.5 if i == 0 else 0.25
        tail = 1.2 if i == 9 else 0.45
        D = round(lead + dur(vo) + tail, 2)
        ovp = os.path.join(work, f"ov{i+1:02d}.png")
        overlay(i, logo).save(ovp)
        zin = i % 2 == 0  # alternate slow push-in / pull-out
        N = int(D * FPS)
        z = f"(1+0.08*n/{N})" if zin else f"(1.08-0.08*n/{N})"
        vf = (f"[0:v]fps={FPS},scale=w='trunc({W}*{z}/2)*2':h='trunc({H}*{z}/2)*2':eval=frame:flags=bicubic,"
              f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2,setsar=1[bg];"
              f"[bg][1:v]overlay=0:0,format=yuv420p,"
              f"fade=t=in:st=0:d=0.35,fade=t=out:st={D-0.35}:d=0.35[v];"
              f"[2:a]adelay={int(lead*1000)}|{int(lead*1000)},apad,atrim=0:{D},"
              f"aformat=sample_rates=44100:channel_layouts=stereo[a]")
        tmp = os.path.join(work, f"p{i+1:02d}.tmp.mp4")
        final = os.path.join(work, f"p{i+1:02d}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS),
                        "-t", str(D), "-i", img, "-loop", "1", "-t", str(D), "-i", ovp, "-i", vo,
                        "-filter_complex", vf, "-map", "[v]", "-map", "[a]", "-t", str(D),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", tmp], check=True)
        os.replace(tmp, final)
        parts.append(final)
        print(f"scene {i+1}: {D}s")
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    joined = os.path.join(work, "joined.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", joined], check=True)
    # One loudness pass on the audio only, video copied.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", joined, "-c:v", "copy",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", out + ".tmp.mp4"], check=True)
    os.replace(out + ".tmp.mp4", out)
    print("done", out, dur(out))


if __name__ == "__main__":
    main(*sys.argv[1:])
