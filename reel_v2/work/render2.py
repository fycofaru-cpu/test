"""Reel v2 (full length): camera + clean audio + subtitles + synced logos + animated screen demos + CTA.
All times are absolute seconds in the original base video; the clip starts at T0."""
import subprocess, math, glob, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
T0, DUR = 0.32, 31.33
NF = int(round(DUR * FPS))
UP = "/root/.claude/uploads/e67b4a67-bc95-5241-bcc2-fee4c64bb19b/"
BASE = glob.glob(UP + "b29b525c-*.mp4")[0]
CLAUDE = glob.glob(UP + "efc0938d-*.mov")[0]
GPT_C = glob.glob(UP + "ab1cffff-*.mov")[0]
GPT_I = glob.glob(UP + "38ac0768-*.mov")[0]
OUT = sys.argv[1] if len(sys.argv) > 1 else "../reel_v2.mp4"
LAST = int(sys.argv[2]) if len(sys.argv) > 2 else NF  # limit frames for quick tests

BLUE, ORANGE, WHITE = (1, 117, 253), (255, 74, 54), (255, 255, 255)


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = min(max(x, 0.0), 1.0)
    return x ** 3


# ---------------- screen-demo definitions ----------------
# card: source file, crop (x,y,w,h) of the 2420x1680 recording, size on screen, abs time its content starts,
# optional list of source segments [(src_start, n_frames)], optional highlight box (crop coords, secs after start)
def card(src, crop, size, abs0, segs, hl=None, cy=790):
    return dict(src=src, crop=crop, size=size, abs0=abs0, segs=segs, hl=hl, cy=cy, frames=[])


MODES = [
    dict(t0=3.76, t1=6.00, tr=0.28, cards=[
        card(CLAUDE, (420, 640, 960, 800), (1000, 833), 3.76, [(44.9, 75)], hl=((24, 90, 936, 524), 1.27), cy=770)]),
    dict(t0=15.76, t1=21.45, tr=0.28, cards=[
        card(GPT_C, (1340, 330, 990, 1256), (820, 1040), 15.76, [(1.5, 60)]),
        card(GPT_I, (500, 0, 1380, 1680), (820, 998), 17.35, [(2.55, 22), (4.17, 45)]),
        card(CLAUDE, (420, 725, 960, 700), (1000, 729), 19.09, [(68.1, 75)], hl=((16, 205, 940, 420), 1.30)),
    ]),
]
SWITCH = 0.30  # slide duration between cards

# ---------------- logos / badges ----------------
CHIP = 190


def make_chip(logo, glyph=112, sz_chip=CHIP):
    sz = sz_chip + 80
    ch = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    sh = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([40, 52, 40 + sz_chip, 52 + sz_chip], int(sz_chip * .26), fill=(0, 0, 0, 90))
    ch = Image.alpha_composite(ch, sh.filter(ImageFilter.GaussianBlur(14)))
    big = Image.new("RGBA", (sz * 3, sz * 3), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle([120, 120, 120 + sz_chip * 3, 120 + sz_chip * 3], int(sz_chip * .26 * 3), fill=(255, 255, 255, 255))
    ch = Image.alpha_composite(ch, big.resize((sz, sz), Image.LANCZOS))
    lg = Image.open(logo).convert("RGBA").resize((glyph, glyph), Image.LANCZOS)
    ch.alpha_composite(lg, ((sz - glyph) // 2, (sz - glyph) // 2))
    return ch


chip_claude, chip_meta = make_chip("logo_claude.png"), make_chip("logo_meta.png")
chip_gpt = make_chip("logo_chatgpt.png")
badge_claude = make_chip("logo_claude.png", 84, 140)
CHIP_Y = 540


def paste_pop(frame, chip, cx, cy, t, t_on, t_off_a, t_off_b, dur=0.34, rise=26):
    p = ease_out((t - t_on) / dur)
    ex = ease_in((t - t_off_a) / (t_off_b - t_off_a))
    if p <= 0 or ex >= 1:
        return
    al = p * (1 - ex)
    s = 0.82 + 0.18 * p
    sz = int(chip.width * s)
    c2 = chip.resize((sz, sz), Image.LANCZOS)
    c2.putalpha(c2.getchannel("A").point(lambda v: int(v * al)))
    frame.alpha_composite(c2, (int(cx - sz / 2), int(cy - sz / 2 - rise * ex)))


# ---------------- strokes ----------------
def rr_points(x0, y0, x1, y1, r, n=10):
    pts = [((x0 + x1) / 2, y0), (x1 - r, y0)]
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append(((x0 + x1) / 2, y0))
    return pts


def partial(pts, p):
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    goal, out, acc = sum(seg) * min(max(p, 0), 1), [pts[0]], 0
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
    lw, lh = size
    L = Image.new("RGBA", (lw * ss, lh * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for (x0, y0, x1, y1), r, p, col, wd, al in items:
        if p <= 0 or al <= 0:
            continue
        pp = partial([(a * ss, b * ss) for a, b in rr_points(x0, y0, x1, y1, r)], p)
        c = col + (int(255 * min(al, 1)),)
        d.line(pp, fill=c, width=int(wd * ss), joint="curve")
        for q in (pp[0], pp[-1]):
            d.ellipse([q[0] - wd * ss / 2, q[1] - wd * ss / 2, q[0] + wd * ss / 2, q[1] + wd * ss / 2], fill=c)
    return L.resize((lw, lh), Image.LANCZOS)


# ---------------- text assets ----------------
FONT = "font_sub.ttf"


def text_img(text, size, fill=WHITE, shadow=True, pad=40, maxw=None):
    f = ImageFont.truetype(FONT, size)
    bb = f.getbbox(text)
    while maxw and bb[2] - bb[0] > maxw and size > 36:
        size -= 2
        f = ImageFont.truetype(FONT, size)
        bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    im = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - bb[0], pad - bb[1] + 4), text, font=f, fill=(0, 0, 0, 150))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(7)))
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=f, fill=fill + (255,))
    return im


# subtitles: (text, start[, end]); end defaults to next start - 0.03
SUBS = [("Es una locura", 0.48), ("Ahora puedes conectar", 1.36), ("tu cuenta de Claude", 2.16), ("con Meta", 2.80),
        ("y hacer anuncios", 3.36), ("de forma automática", 4.00), ("Vas a poder optimizar,", 4.80),
        ("mejorar y escalar", 5.98), ("tus campañas", 7.12), ("con muy simples prompts", 7.76, 9.08),
        ("Y además de eso", 9.12), ("vas a poder conectar", 9.84), ("tu cuenta de ChatGPT", 10.64),
        ("para hacer anuncios", 11.68), ("totalmente ganadores", 12.40), ("copiando y pegando", 13.28),
        ("de tu competencia", 14.48, 15.25), ("Literalmente vas a poder", 15.36), ("ver los mejores anuncios,", 16.24, 17.40),
        ("crearlos con", 17.52), ("inteligencia artificial,", 18.24, 19.20), ("colocarlos en Claude", 19.28),
        ("para que los suba", 20.08), ("automáticamente", 20.80, 21.40), ("y de esa forma de escalar", 21.44),
        ("mucho más rápido", 22.72, 23.30), ("Acabo de crear una clase", 23.44), ("totalmente gratuita", 24.48),
        ("a la que te enseño", 25.20), ("paso a paso", 26.08), ("cómo hacer esto", 26.48),
        ("para tu tienda online", 27.04), ("en menos de 15 minutos", 28.00, 28.90)]
SUB_Y = 1440
sub_imgs = [text_img(s[0], 66, maxw=940) for s in SUBS]
sub_t = []
for j, s in enumerate(SUBS):
    en = s[2] if len(s) > 2 else SUBS[j + 1][1] - 0.03
    sub_t.append((s[1] - 0.04, en))

# "Clase gratuita" pill
pill_txt = text_img("Clase gratuita", 58, pad=0, shadow=False)
PW, PH = pill_txt.width + 90, 104
pill = Image.new("RGBA", (PW + 80, PH + 80), (0, 0, 0, 0))
ps = Image.new("RGBA", pill.size, (0, 0, 0, 0))
ImageDraw.Draw(ps).rounded_rectangle([40, 50, 40 + PW, 50 + PH], PH // 2, fill=(0, 0, 0, 90))
pill = Image.alpha_composite(pill, ps.filter(ImageFilter.GaussianBlur(12)))
big = Image.new("RGBA", ((PW) * 3, PH * 3), (0, 0, 0, 0))
ImageDraw.Draw(big).rounded_rectangle([0, 0, PW * 3 - 1, PH * 3 - 1], PH * 3 // 2, fill=BLUE + (255,))
pill.alpha_composite(big.resize((PW, PH), Image.LANCZOS), (40, 40))
pill.alpha_composite(pill_txt, (40 + (PW - pill_txt.width) // 2, 40 + (PH - pill_txt.height) // 2))

# CTA
cta_a = text_img("Comentá", 112, pad=30)
clase_t = text_img("CLASE", 112, pad=0, shadow=False)
CBW, CBH = clase_t.width + 70, 150
cta_box = Image.new("RGBA", (CBW + 60, CBH + 60), (0, 0, 0, 0))
cs = Image.new("RGBA", cta_box.size, (0, 0, 0, 0))
ImageDraw.Draw(cs).rounded_rectangle([30, 40, 30 + CBW, 40 + CBH], 36, fill=(0, 0, 0, 100))
cta_box = Image.alpha_composite(cta_box, cs.filter(ImageFilter.GaussianBlur(10)))
bigb = Image.new("RGBA", (CBW * 3, CBH * 3), (0, 0, 0, 0))
ImageDraw.Draw(bigb).rounded_rectangle([0, 0, CBW * 3 - 1, CBH * 3 - 1], 108, fill=BLUE + (255,))
cta_box.alpha_composite(bigb.resize((CBW, CBH), Image.LANCZOS), (30, 30))
cta_box.alpha_composite(clase_t, (30 + (CBW - clase_t.width) // 2, 30 + (CBH - clase_t.height) // 2))
cta_b = text_img("y te lo doy totalmente gratis", 62, pad=30, maxw=940)
CTA_Y = 1330
cta_gap = 20
cta_total_w = (cta_a.width - 60) + cta_gap + CBW
cta_x0 = (W - cta_total_w) // 2

# ---------------- video IO ----------------
grade = ("scale=1080:1920:flags=lanczos,eq=contrast=1.04:saturation=1.07:gamma=1.13:brightness=0.025,"
         "colorbalance=rs=.035:gs=.012:bs=-.04:rm=.03:gm=.008:bm=-.03,unsharp=5:5:0.55:5:5:0.0")


def read_frames(path, ss, n, crop):
    x, y, w, h = crop
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(ss), "-i", path, "-frames:v", str(n), "-vf",
                        f"fps={FPS},crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    sz = w * h * 3
    return [Image.frombytes("RGB", (w, h), p.stdout[i * sz:(i + 1) * sz]) for i in range(len(p.stdout) // sz)]


for md in MODES:
    for c in md["cards"]:
        for (ss, n) in c["segs"]:
            c["frames"] += read_frames(c["src"], ss, n, c["crop"])
        w_, h_ = c["size"]
        mk = Image.new("L", (w_ * 3, h_ * 3), 0)
        ImageDraw.Draw(mk).rounded_rectangle([0, 0, w_ * 3 - 1, h_ * 3 - 1], 36 * 3, fill=255)
        c["mask"] = mk.resize((w_, h_), Image.LANCZOS)
        sh = Image.new("RGBA", (w_ + 160, h_ + 160), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([80, 98, 80 + w_, 98 + h_], 36, fill=(0, 0, 0, 120))
        c["shadow"] = sh.filter(ImageFilter.GaussianBlur(26))
        print("card frames", len(c["frames"]), flush=True)

cam = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(T0), "-t", str(DUR), "-i", BASE, "-vf", f"fps={FPS},{grade}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-i", "audio_mix.wav", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-colorspace", "bt709",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)


def cam_scale(t):
    if 6.0 <= t <= 15.76:
        return 1.0 + 0.04 * ease_io((t - 6.0) / 9.76)
    if 23.44 <= t:
        return 1.0 + 0.04 * ease_io((t - 23.44) / 8.2)
    if 15.76 < t < 21.45:
        return 1.04
    if 21.45 <= t < 23.44:
        return 1.04 - 0.04 * ease_io((t - 21.45) / 1.99)
    return 1.0


def draw_modes(frame, t):
    for md in MODES:
        if not (md["t0"] <= t <= md["t1"]):
            continue
        tr = md["tr"]
        m = min(ease_io((t - md["t0"]) / tr), ease_io((md["t1"] - t) / tr))
        if m <= 0:
            continue
        small = frame.resize((135, 240), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BICUBIC)
        frame = Image.blend(frame, Image.eval(small, lambda v: int(v * 0.68)), m)
        base = frame.convert("RGBA")
        cards = md["cards"]
        for i, c in enumerate(cards):
            st = c["abs0"] if i > 0 else md["t0"]
            e_in = 1.0 if i == 0 else ease_io((t - (st - SWITCH / 2)) / SWITCH)
            e_out = 0.0 if i == len(cards) - 1 else ease_io((t - (cards[i + 1]["abs0"] - SWITCH / 2)) / SWITCH)
            if e_in <= 0 or e_out >= 1:
                continue
            w_, h_ = c["size"]
            x_off = (1 - e_in) * W * 0.9 * (1 if i > 0 else 0) - e_out * W * 0.9
            al_slide = e_in * (1 - e_out)
            amode = ease_out(m)
            al = (al_slide if i > 0 else (1 - e_out)) * amode
            td = t - c["abs0"]
            z = 1.0 + 0.04 * ease_io((t - (st - SWITCH / 2)) / max(0.5, (md["t1"] - st)))
            fi = min(max(int(td * FPS), 0), len(c["frames"]) - 1)
            cx_, cy_, cw_, ch_ = c["crop"]
            win = c["frames"][fi].crop((0, 0, int(cw_ / z), int(ch_ / z))).resize((w_, h_), Image.LANCZOS)
            sc = 0.94 + 0.06 * amode
            cw, chh = int(w_ * sc), int(h_ * sc)
            cardimg = win.resize((cw, chh), Image.LANCZOS).convert("RGBA")
            cardimg.putalpha(c["mask"].resize((cw, chh), Image.LANCZOS).point(lambda v: int(v * al)))
            px, py = int((W - cw) // 2 + x_off), int(c["cy"] - chh // 2)
            sh = c["shadow"].copy()
            sh.putalpha(sh.getchannel("A").point(lambda v: int(v * al)))
            base.alpha_composite(sh, (int((W - w_) // 2 + x_off + (w_ - cw) // 2) - 80, int(c["cy"] - h_ // 2 + (h_ - chh) // 2) - 80))
            base.alpha_composite(cardimg, (px, py))
            # drawn outline + highlight box
            lw_, lh_ = w_ + 60, h_ + 60
            ox, oy = (w_ - cw) // 2, (h_ - chh) // 2
            prog = ease_io(((t - (st - SWITCH / 2)) if i > 0 else (t - md["t0"])) / 0.5)
            items = [((30 + ox, 30 + oy, 30 + ox + cw - 1, 30 + oy + chh - 1), int(36 * sc), prog, BLUE, 5, min(1.0, al * 1.2))]
            if c["hl"]:
                (hx0, hy0, hx1, hy1), hoff = c["hl"]
                hp = ease_io((td - hoff) / 0.55)
                if hp > 0:
                    k = w_ / (cw_ / z)
                    items.append(((30 + hx0 * k, 30 + hy0 * k, 30 + hx1 * k, 30 + hy1 * k), 22, hp, ORANGE, 7, min(1.0, al * 1.3)))
            ly = stroke_layer((lw_, lh_), items)
            base.alpha_composite(ly, (int((W - w_) // 2 - 30 + x_off), int(c["cy"] - h_ // 2 - 30)))
        frame = base.convert("RGB")
    return frame


QA = (30, 105, 170, 235, 300, 370, 480, 500, 540, 600, 700, 760, 800, 880, 905, 925)
for i in range(min(NF, LAST)):
    raw = cam.stdout.read(W * H * 3)
    if len(raw) < W * H * 3:
        break
    t = T0 + i / FPS
    frame = Image.frombytes("RGB", (W, H), raw)
    s = cam_scale(t)
    if s > 1.0005:
        cw, ch = int(W / s), int(H / s)
        frame = frame.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.LANCZOS)
    frame = draw_modes(frame, t).convert("RGBA")

    # logos synced with the words
    exit1 = (3.54, 3.74)
    paste_pop(frame, chip_claude, 350, CHIP_Y, t, 2.48, *exit1)
    paste_pop(frame, chip_meta, 730, CHIP_Y, t, 3.04, *exit1)
    lp = ease_io((t - 3.14) / 0.34)
    ex = ease_in((t - exit1[0]) / (exit1[1] - exit1[0]))
    if lp > 0 and ex < 1:
        xa, xb = 350 + CHIP // 2 + 18, 730 - CHIP // 2 - 18
        lw, lh, ss = xb - xa + 60, 60, 2
        L = Image.new("RGBA", (lw * ss, lh * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        xe, a = 30 + (xb - xa) * lp, int(255 * (1 - ex))
        d.line([(30 * ss, 30 * ss), (xe * ss, 30 * ss)], fill=BLUE + (a,), width=8 * ss)
        for q in (30, xe):
            d.ellipse([(q - 4) * ss, 26 * ss, (q + 4) * ss, 34 * ss], fill=BLUE + (a,))
        if lp >= 1:
            d.ellipse([(xe - 11) * ss, 19 * ss, (xe + 11) * ss, 41 * ss], fill=ORANGE + (a,))
        frame.alpha_composite(L.resize((lw, lh), Image.LANCZOS), (xa - 30, CHIP_Y - 30 - int(26 * ex)))
    paste_pop(frame, chip_gpt, 540, CHIP_Y, t, 11.04, 12.35, 12.58)
    # Claude badge on the demo card (word "Claude" at 19.84)
    paste_pop(frame, badge_claude, 82, 405, t, 19.84, 21.12, 21.30, rise=14)

    # "Clase gratuita" pill with a drawn frame
    if 24.16 <= t <= 26.30:
        p = ease_out((t - 24.16) / 0.34)
        ex2 = ease_in((t - 26.05) / 0.25)
        al = p * (1 - ex2)
        s_ = 0.86 + 0.14 * p
        pw, ph = int(pill.width * s_), int(pill.height * s_)
        pp = pill.resize((pw, ph), Image.LANCZOS)
        pp.putalpha(pp.getchannel("A").point(lambda v: int(v * al)))
        frame.alpha_composite(pp, (W // 2 - pw // 2, CHIP_Y - ph // 2 - int(20 * ex2)))
        sp = ease_io((t - 24.50) / 0.55)
        if sp > 0:
            lay = stroke_layer((PW + 60, PH + 60), [((30 - 14, 30 - 14, 30 + PW + 14, 30 + PH + 14), PH // 2 + 14, sp, ORANGE, 6, 1 - ex2)])
            frame.alpha_composite(lay, (W // 2 - (PW + 60) // 2, CHIP_Y - (PH + 60) // 2 - int(20 * ex2) + 0))

    # subtitles (stop before the CTA)
    for j, (a0, a1) in enumerate(sub_t):
        if a0 <= t <= a1:
            a_in = ease_out((t - a0) / 0.10)
            a_out = min(1.0, (a1 - t) / 0.06 + 0.0) if a1 - t < 0.06 and (j + 1 == len(sub_t) or sub_t[j + 1][0] - a1 > 0.1) else 1.0
            al = max(0.0, min(a_in, a_out))
            im = sub_imgs[j]
            if al < 1:
                im = im.copy()
                im.putalpha(im.getchannel("A").point(lambda v: int(v * al)))
            rise = int(8 * (1 - ease_out((t - a0) / 0.12)))
            frame.alpha_composite(im, ((W - im.width) // 2, SUB_Y - im.height // 2 + rise))
            break

    # CTA: «Comentá CLASE» then «y te lo doy totalmente gratis»
    if t >= 29.12:
        p1 = ease_out((t - 29.12) / 0.30)
        im = cta_a.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * p1)))
        frame.alpha_composite(im, (cta_x0 - 30, CTA_Y - im.height // 2 + int(14 * (1 - p1))))
        p2 = ease_out((t - 29.58) / 0.30)
        if p2 > 0:
            s_ = 0.85 + 0.15 * p2
            bw, bh = int(cta_box.width * s_), int(cta_box.height * s_)
            bx = cta_box.resize((bw, bh), Image.LANCZOS)
            bx.putalpha(bx.getchannel("A").point(lambda v: int(v * p2)))
            bcx = cta_x0 + (cta_a.width - 60) + cta_gap + CBW // 2
            frame.alpha_composite(bx, (bcx - bw // 2, CTA_Y - bh // 2))
            sp = ease_io((t - 29.72) / 0.55)
            if sp > 0:
                lay = stroke_layer((CBW + 80, CBH + 80), [((40 - 12, 40 - 12, 40 + CBW + 12, 40 + CBH + 12), 48, sp, ORANGE, 7, 1.0)])
                frame.alpha_composite(lay, (bcx - (CBW + 80) // 2, CTA_Y - (CBH + 80) // 2))
        p3 = ease_out((t - 29.94) / 0.30)
        if p3 > 0:
            im = cta_b.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * p3)))
            frame.alpha_composite(im, ((W - im.width) // 2, CTA_Y + 135 - im.height // 2 + int(12 * (1 - p3))))

    frame = frame.convert("RGB")
    if i in QA:
        frame.save(f"qa2_{i:03d}.png")
    enc.stdin.write(frame.tobytes())
    if i % 100 == 0:
        print("frame", i, "/", NF, flush=True)

enc.stdin.close()
enc.wait()
cam.stdout.close()
print("done")
