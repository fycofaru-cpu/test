"""Reel sample v1: camera + clean audio + subtitles + logo sync + animated screen demo.
All times below are absolute seconds in the original base video (clip starts at T0)."""
import subprocess, math, glob, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
T0, DUR = 0.32, 8.86
NF = int(round(DUR * FPS))
UP = "/root/.claude/uploads/e67b4a67-bc95-5241-bcc2-fee4c64bb19b/"
BASE = glob.glob(UP + "b29b525c-*.mp4")[0]
CLAUDE = glob.glob(UP + "efc0938d-*.mov")[0]
OUT = sys.argv[1] if len(sys.argv) > 1 else "../sample_v1.mp4"

BLUE, ORANGE = (1, 117, 253), (255, 74, 54)

# demo window (abs seconds), source of the screen recording starts at 44.9 s
D_IN, D_OUT, D_TR = 3.76, 6.00, 0.28
SRC_START, SRC_W, SRC_H = 44.9, 960, 800
CW = 1000
CH = round(CW * SRC_H / SRC_W)
CX0, CY0 = (W - CW) // 2, 350

# logos
L_CLAUDE, L_META = 2.48, 3.04
L_EXIT = (3.54, 3.74)

# subtitles: (text, start); end = next start - 0.03; last ends at SUB_END
SUBS = [("Es una locura", 0.48), ("Ahora puedes conectar", 1.36), ("tu cuenta de Claude", 2.16),
        ("con Meta", 2.80), ("y hacer anuncios", 3.36), ("de forma automática", 4.00),
        ("Vas a poder optimizar,", 4.80), ("mejorar y escalar", 5.98), ("tus campañas", 7.12),
        ("con muy simples prompts", 7.76)]
SUB_END = 9.12
SUB_Y = 1440


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = min(max(x, 0.0), 1.0)
    return x ** 3


def rr_points(x0, y0, x1, y1, r, n=10):
    """closed rounded-rect path, clockwise from top-centre"""
    pts = [((x0 + x1) / 2, y0), (x1 - r, y0)]
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        if (cx, cy, a0) == (x1 - r, y0 + r, -90):
            pass
    pts.append(((x0 + x1) / 2, y0))
    return pts


def partial(pts, p):
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    tot, goal, out, acc = sum(seg), sum(seg) * min(max(p, 0), 1), [pts[0]], 0
    for i, s in enumerate(seg):
        if acc + s >= goal:
            f = (goal - acc) / s if s else 0
            a, b = pts[i], pts[i + 1]
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            return out
        acc += s
        out.append(pts[i + 1])
    return out


def stroke_layer(size, items, ss=2):
    """items: list of (rect(x0,y0,x1,y1), radius, progress, colour, width, alpha) in layer px; anti-aliased via supersample"""
    lw, lh = size
    L = Image.new("RGBA", (lw * ss, lh * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for (x0, y0, x1, y1), r, p, col, wd, al in items:
        if p <= 0 or al <= 0:
            continue
        pts = [(a * ss, b * ss) for a, b in rr_points(x0, y0, x1, y1, r)]
        pp = partial(pts, p)
        d.line(pp, fill=col + (int(255 * al),), width=int(wd * ss), joint="curve")
        for q in (pp[0], pp[-1]):
            d.ellipse([q[0] - wd * ss / 2, q[1] - wd * ss / 2, q[0] + wd * ss / 2, q[1] + wd * ss / 2],
                      fill=col + (int(255 * al),))
    return L.resize((lw, lh), Image.LANCZOS)


# ---------- assets ----------
font = ImageFont.truetype("font_sub.ttf", 66)
sub_imgs = []
for text, st in SUBS:
    bb = font.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = 40
    im = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - bb[0], pad - bb[1] + 4), text, font=font, fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    im = Image.alpha_composite(im, sh)
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=font, fill=(255, 255, 255, 255))
    sub_imgs.append(im)

CHIP = 190


def make_chip(logo):
    sz = CHIP + 80
    ch = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    sh = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([40, 52, 40 + CHIP, 52 + CHIP], 50, fill=(0, 0, 0, 90))
    ch = Image.alpha_composite(ch, sh.filter(ImageFilter.GaussianBlur(14)))
    big = Image.new("RGBA", (sz * 3, sz * 3), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle([120, 120, 120 + CHIP * 3, 120 + CHIP * 3], 150, fill=(255, 255, 255, 255))
    ch = Image.alpha_composite(ch, big.resize((sz, sz), Image.LANCZOS))
    lg = Image.open(logo).convert("RGBA").resize((112, 112), Image.LANCZOS)
    ch.alpha_composite(lg, ((sz - 112) // 2, (sz - 112) // 2))
    return ch


chip_claude, chip_meta = make_chip("logo_claude.png"), make_chip("logo_meta.png")
CHIP_Y = 540
CX_CLAUDE, CX_META = 350, 730

# card shadow + mask
card_mask = Image.new("L", (CW * 3, CH * 3), 0)
ImageDraw.Draw(card_mask).rounded_rectangle([0, 0, CW * 3 - 1, CH * 3 - 1], 36 * 3, fill=255)
card_mask = card_mask.resize((CW, CH), Image.LANCZOS)
shadow = Image.new("RGBA", (CW + 160, CH + 160), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rounded_rectangle([80, 98, 80 + CW, 98 + CH], 36, fill=(0, 0, 0, 120))
shadow = shadow.filter(ImageFilter.GaussianBlur(26))

# ---------- readers / writer ----------
grade = ("scale=1080:1920:flags=lanczos,eq=contrast=1.04:saturation=1.07:gamma=1.13:brightness=0.025,"
         "colorbalance=rs=.035:gs=.012:bs=-.04:rm=.03:gm=.008:bm=-.03,unsharp=5:5:0.55:5:5:0.0")
cam = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(T0), "-t", str(DUR), "-i", BASE, "-vf", f"fps={FPS},{grade}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
dm = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(SRC_START), "-t", "2.5", "-i", CLAUDE, "-vf",
                       f"fps={FPS},crop={SRC_W}:{SRC_H}:420:640", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                      stdout=subprocess.PIPE)
demo_frames = []
while True:
    b = dm.stdout.read(SRC_W * SRC_H * 3)
    if len(b) < SRC_W * SRC_H * 3:
        break
    demo_frames.append(Image.frombytes("RGB", (SRC_W, SRC_H), b))
print("demo frames", len(demo_frames), flush=True)

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-i", "audio_mix.wav", "-vf",
                        "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-colorspace", "bt709",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)

HL = (24, 90, 936, 524)  # highlight rect in crop coords (options list of step 2/4)
HL_T = 1.17 + 0.10  # seconds after demo start when the 2/4 question appears
snap = {}

for i in range(NF):
    raw = cam.stdout.read(W * H * 3)
    if len(raw) < W * H * 3:
        break
    t = T0 + i / FPS
    frame = Image.frombytes("RGB", (W, H), raw)

    # ---- demo window ----
    m_in = ease_io((t - D_IN) / D_TR)
    m_out = ease_io((D_OUT - t) / D_TR)
    m = min(m_in, m_out) if D_IN <= t <= D_OUT else 0.0
    if m > 0:
        small = frame.resize((135, 240), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BICUBIC)
        dim = Image.eval(small, lambda v: int(v * 0.68))
        frame = Image.blend(frame, dim, m)
        td = t - D_IN
        z = 1.0 + 0.04 * ease_io(td / (D_OUT - D_IN))
        fi = min(int(td * FPS), len(demo_frames) - 1)
        win = demo_frames[fi].crop((0, 0, int(SRC_W / z), int(SRC_H / z))).resize((CW, CH), Image.LANCZOS)
        sc = 0.94 + 0.06 * ease_out(m)
        cw, ch = int(CW * sc), int(CH * sc)
        card = win.resize((cw, ch), Image.LANCZOS).convert("RGBA")
        mk = card_mask.resize((cw, ch), Image.LANCZOS).point(lambda v: int(v * ease_out(m)))
        card.putalpha(mk)
        cx, cy = (W - cw) // 2, CY0 + (CH - ch) // 2
        sh = shadow.copy()
        sh.putalpha(sh.getchannel("A").point(lambda v: int(v * ease_out(m))))
        base = frame.convert("RGBA")
        base.alpha_composite(sh, (CX0 - 80, CY0 - 80))
        base.alpha_composite(card, (cx, cy))
        # drawn frame + highlight (blue outline draws in, orange box draws around the options)
        lay_w, lay_h = CW + 60, CH + 60
        items = [((30 + 1, 30 + 1, 30 + cw - 1 + (CW - cw) // 2 * 0, 30 + ch - 1), 36, ease_io(td / 0.5), BLUE, 5,
                  1.0 if t < D_OUT - D_TR else ease_io((D_OUT - t) / D_TR))]
        # centre the outline on the (scaled) card
        ox, oy = (CW - cw) // 2, (CH - ch) // 2
        items = [((30 + ox, 30 + oy, 30 + ox + cw - 1, 30 + oy + ch - 1), int(36 * sc), ease_io(td / 0.5), BLUE, 5,
                  min(1.0, m * 1.2))]
        hp = ease_io((td - HL_T) / 0.55)
        if hp > 0:
            k = CW / (SRC_W / z)
            x0, y0, x1, y1 = [v * k for v in HL]
            fade = 1.0 if t < D_OUT - D_TR - 0.05 else max(0.0, (D_OUT - D_TR - t) / D_TR + 1)
            items.append(((30 + x0, 30 + y0, 30 + x1, 30 + y1), 22, hp, ORANGE, 7, min(1.0, m * 1.3) * fade))
        ly = stroke_layer((lay_w, lay_h), items)
        base.alpha_composite(ly, (CX0 - 30, CY0 - 30))
        frame = base.convert("RGB")

    frame = frame.convert("RGBA")

    # ---- logos (word-synced) ----
    exit_p = ease_in((t - L_EXIT[0]) / (L_EXIT[1] - L_EXIT[0]))
    for chip, cxl, t_on in ((chip_claude, CX_CLAUDE, L_CLAUDE), (chip_meta, CX_META, L_META)):
        p = ease_out((t - t_on) / 0.34)
        if p <= 0 or exit_p >= 1:
            continue
        al = p * (1 - exit_p)
        s = 0.82 + 0.18 * p
        sz = int(chip.width * s)
        c2 = chip.resize((sz, sz), Image.LANCZOS)
        c2.putalpha(c2.getchannel("A").point(lambda v: int(v * al)))
        frame.alpha_composite(c2, (cxl - sz // 2, CHIP_Y - sz // 2 - int(26 * exit_p)))
    lp = ease_io((t - (L_META + 0.10)) / 0.34)
    if lp > 0 and exit_p < 1:
        x_a, x_b = CX_CLAUDE + CHIP // 2 + 18, CX_META - CHIP // 2 - 18
        lw, lh = x_b - x_a + 60, 60
        pts_items = []
        ss = 2
        L = Image.new("RGBA", (lw * ss, lh * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        xe = 30 + (x_b - x_a) * lp
        a = int(255 * (1 - exit_p))
        d.line([(30 * ss, 30 * ss), (xe * ss, 30 * ss)], fill=BLUE + (a,), width=8 * ss)
        for q in (30, xe):
            d.ellipse([(q - 4) * ss, 26 * ss, (q + 4) * ss + 0, 34 * ss], fill=BLUE + (a,))
        if lp >= 1:
            d.ellipse([(xe - 11) * ss, 19 * ss, (xe + 11) * ss, 41 * ss], fill=ORANGE + (a,))
        L = L.resize((lw, lh), Image.LANCZOS)
        frame.alpha_composite(L, (x_a - 30, CHIP_Y - 30 - int(26 * exit_p)))

    # ---- subtitles ----
    for j, (text, st) in enumerate(SUBS):
        en = (SUBS[j + 1][1] - 0.03) if j + 1 < len(SUBS) else SUB_END
        st0 = st - 0.04
        if st0 <= t <= en:
            a_in = ease_out((t - st0) / 0.10)
            a_out = 1.0 if j + 1 < len(SUBS) or t < SUB_END - 0.08 else (SUB_END - t) / 0.08
            al = max(0.0, min(a_in, a_out))
            im = sub_imgs[j]
            if al < 1:
                im = im.copy()
                im.putalpha(im.getchannel("A").point(lambda v: int(v * al)))
            rise = int(8 * (1 - ease_out((t - st0) / 0.12)))
            frame.alpha_composite(im, ((W - im.width) // 2, SUB_Y - im.height // 2 + rise))
            break

    frame = frame.convert("RGB")
    if i in (10, 60, 100, 110, 125, 150, 195, 245):
        frame.save(f"qa_{i:03d}.png")
    enc.stdin.write(frame.tobytes())
    if i % 40 == 0:
        print("frame", i, "/", NF, flush=True)

enc.stdin.close()
enc.wait()
cam.stdout.close()
print("done")
