import os
import re
import json
import random
import hashlib
import logging

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter,
    ImageEnhance,
)

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# =============================================================================
# LOGGER
# =============================================================================

logger = logging.getLogger("ThumbnailGenerator")

# =============================================================================
# OUTPUT
# =============================================================================

OUTPUT_DIR = "output/thumbnails"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# =============================================================================
# FONTS
# =============================================================================

FONT_BOLD = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]

FONT_REGULAR = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "/Library/Fonts/Arial.ttf",
]


def find_font(paths):

    for path in paths:

        if os.path.exists(path):

            return path

    return None


BOLD_FONT = find_font(FONT_BOLD)

REGULAR_FONT = find_font(FONT_REGULAR)


def font(size, bold=True):

    try:

        path = BOLD_FONT if bold else REGULAR_FONT

        if path:

            return ImageFont.truetype(
                path,
                size
            )

    except Exception:
        pass

    return ImageFont.load_default()


# =============================================================================
# LAYOUTS
# =============================================================================

LAYOUTS = [

    "shock_red",
    "neon_split",
    "ai_glow",
    "ev_vs_gas",
    "battery_alert",

    "future_city",
    "robot_takeover",
    "minimal_dark",
    "cinematic_blue",
    "data_explosion",

    "warning_theme",
    "hyper_future",
    "elon_style",
    "tesla_breakthrough",
    "red_vs_blue",

    "ultimate_ev",
    "viral_news",
    "world_change",
    "electric_revolution",
    "ai_future_war",
]

# =============================================================================
# COLORS
# =============================================================================

TOPIC_STYLES = {

    "electric_vehicle": {

        "bg1": (0, 0, 0),
        "bg2": (0, 20, 40),

        "accent": (0, 220, 255),
        "accent2": (255, 50, 0),

        "label": "EV TECH",

        "stats": [
            ("500MI", "NEW RANGE"),
            ("10MIN", "FAST CHARGE"),
            ("-45%", "WINTER LOSS"),
        ]
    },

    "battery_tech": {

        "bg1": (0, 0, 0),
        "bg2": (10, 30, 0),

        "accent": (0, 255, 140),
        "accent2": (255, 200, 0),

        "label": "BATTERY",

        "stats": [
            ("1M KM", "LIFESPAN"),
            ("5MIN", "CHARGE"),
            ("2030", "NEXT GEN"),
        ]
    },

    "artificial_intelligence": {

        "bg1": (0, 0, 0),
        "bg2": (15, 0, 30),

        "accent": (170, 0, 255),
        "accent2": (0, 220, 255),

        "label": "AI TECH",

        "stats": [
            ("10X", "FASTER"),
            ("2030", "AGI"),
            ("$1T", "MARKET"),
        ]
    },

    "robotics": {

        "bg1": (0, 0, 0),
        "bg2": (0, 20, 0),

        "accent": (0, 255, 120),
        "accent2": (255, 255, 255),

        "label": "ROBOTICS",

        "stats": [
            ("24/7", "UPTIME"),
            ("40%", "AUTOMATED"),
            ("$1.5T", "MARKET"),
        ]
    },

    "default": {

        "bg1": (0, 0, 0),
        "bg2": (0, 20, 40),

        "accent": (255, 50, 0),
        "accent2": (0, 220, 255),

        "label": "TECH",

        "stats": [
            ("300%", "GROWTH"),
            ("2030", "FUTURE"),
            ("NEW", "UPDATE"),
        ]
    }
}

# =============================================================================
# HELPERS
# =============================================================================


def mix(c1, c2, t):

    return tuple(
        int(c1[i] * (1 - t) + c2[i] * t)
        for i in range(3)
    )


def gradient(draw, W, H, c1, c2):

    for y in range(H):

        t = y / H

        draw.line(
            [(0, y), (W, y)],
            fill=mix(c1, c2, t)
        )


def add_glow(img, color, strength=0.35):

    overlay = Image.new(
        "RGB",
        img.size,
        (0, 0, 0)
    )

    od = ImageDraw.Draw(overlay)

    W, H = img.size

    for _ in range(10):

        x = random.randint(0, W)
        y = random.randint(0, H)

        r = random.randint(150, 500)

        od.ellipse(
            [x-r, y-r, x+r, y+r],
            fill=color
        )

    overlay = overlay.filter(
        ImageFilter.GaussianBlur(120)
    )

    return Image.blend(
        img,
        overlay,
        strength
    )


def add_noise(img):

    noise = Image.effect_noise(
        img.size,
        8
    )

    noise = noise.convert("L")

    noise = ImageEnhance.Contrast(
        noise
    ).enhance(2)

    noise = noise.filter(
        ImageFilter.GaussianBlur(0.5)
    )

    noise_rgb = Image.merge(
        "RGB",
        (noise, noise, noise)
    )

    return Image.blend(
        img,
        noise_rgb,
        0.05
    )


def split_title(title):

    words = title.upper().split()

    lines = []

    current = []

    for word in words:

        current.append(word)

        if len(current) >= 3:

            lines.append(
                " ".join(current)
            )

            current = []

    if current:

        lines.append(
            " ".join(current)
        )

    while len(lines) < 3:

        lines.append("")

    return lines[:3]


def auto_font(
    draw,
    text,
    max_width,
    start_size=110,
    bold=True
):

    size = start_size

    while size > 20:

        f = font(size, bold)

        w = draw.textlength(
            text,
            font=f
        )

        if w <= max_width:

            return f

        size -= 4

    return font(20, bold)


def draw_stroke_text(
    draw,
    pos,
    text,
    fnt,
    fill,
    stroke=(0, 0, 0)
):

    x, y = pos

    for ox in range(-4, 5):

        for oy in range(-4, 5):

            if ox == 0 and oy == 0:
                continue

            draw.text(
                (x + ox, y + oy),
                text,
                font=fnt,
                fill=stroke
            )

    draw.text(
        (x, y),
        text,
        font=fnt,
        fill=fill
    )


def safe_filename(text):

    return re.sub(
        r"[^\w]",
        "_",
        text[:40]
    )


def pick_layout(title):

    h = int(
        hashlib.md5(
            title.encode()
        ).hexdigest(),
        16
    )

    return LAYOUTS[
        h % len(LAYOUTS)
    ]


# =============================================================================
# LIGHTNING EFFECT
# =============================================================================

def draw_lightning(draw, W, H, color):

    for _ in range(12):

        x1 = random.randint(0, W)
        y1 = random.randint(0, H)

        x2 = x1 + random.randint(-250, 250)
        y2 = y1 + random.randint(60, 250)

        draw.line(
            [(x1, y1), (x2, y2)],
            fill=color,
            width=3
        )

# =============================================================================
# MAIN RENDER
# =============================================================================


def render_thumbnail(
    W,
    H,
    lines,
    style,
    layout
):

    img = Image.new(
        "RGB",
        (W, H),
        (0, 0, 0)
    )

    draw = ImageDraw.Draw(img)

    # BACKGROUND

    gradient(
        draw,
        W,
        H,
        style["bg1"],
        style["bg2"]
    )

    img = add_glow(
        img,
        style["accent"],
        0.35
    )

    img = add_glow(
        img,
        style["accent2"],
        0.18
    )

    img = add_noise(img)

    draw = ImageDraw.Draw(img)

    # LIGHTNING

    if layout in [
        "shock_red",
        "hyper_future",
        "warning_theme",
        "ai_future_war"
    ]:

        draw_lightning(
            draw,
            W,
            H,
            style["accent"]
        )

    # SIDE BAR

    draw.rectangle(
        [0, 0, 18, H],
        fill=style["accent"]
    )

    # TOP BAR

    draw.rectangle(
        [0, 0, W, 70],
        fill=(0, 0, 0)
    )

    draw.rectangle(
        [0, 66, W, 70],
        fill=style["accent"]
    )

    draw.text(
        (40, 16),
        f"{style['label']} REPORT",
        font=font(26),
        fill=(255, 255, 255)
    )

    # BIG RIGHT NUMBER

    stat = style["stats"][0][0]

    stat_font = auto_font(
        draw,
        stat,
        W // 2,
        210
    )

    sw = draw.textlength(
        stat,
        font=stat_font
    )

    sx = W - sw - 40
    sy = 110

    draw_stroke_text(
        draw,
        (sx, sy),
        stat,
        stat_font,
        style["accent"]
    )

    draw.text(
        (sx, sy + 170),
        style["stats"][0][1],
        font=font(28),
        fill=(220, 220, 220)
    )

    # TITLE

    y = 120

    colors = [
        style["accent"],
        (255, 255, 255),
        style["accent2"]
    ]

    sizes = [100, 72, 50]

    max_w = W // 2 - 60

    for i, line in enumerate(lines):

        if not line:
            continue

        f = auto_font(
            draw,
            line,
            max_w,
            sizes[i]
        )

        draw_stroke_text(
            draw,
            (40, y),
            line,
            f,
            colors[i]
        )

        h = f.size + 20

        if i == 0:

            tw = draw.textlength(
                line,
                font=f
            )

            draw.rectangle(
                [
                    40,
                    y + h - 12,
                    40 + tw,
                    y + h - 4
                ],
                fill=style["accent"]
            )

        y += h + 12

    # RIGHT BOXES

    bx = W - 320
    by = 350

    for value, label in style["stats"]:

        draw.rectangle(
            [
                bx,
                by,
                bx + 260,
                by + 74
            ],
            fill=(0, 0, 0)
        )

        draw.rectangle(
            [
                bx,
                by,
                bx + 10,
                by + 74
            ],
            fill=style["accent2"]
        )

        draw.text(
            (bx + 22, by + 4),
            value,
            font=font(38),
            fill=style["accent2"]
        )

        draw.text(
            (bx + 22, by + 42),
            label,
            font=font(18, False),
            fill=(180, 180, 180)
        )

        by += 92

    # CORNERS

    c = style["accent"]

    s = 60
    t = 6
    m = 20

    # TL

    draw.rectangle(
        [m, m, m+s, m+t],
        fill=c
    )

    draw.rectangle(
        [m, m, m+t, m+s],
        fill=c
    )

    # BR

    draw.rectangle(
        [W-m-s, H-m, W-m, H-m+t],
        fill=c
    )

    draw.rectangle(
        [W-m, H-m-s, W-m+t, H-m],
        fill=c
    )

    # FOOTER

    draw.rectangle(
        [0, H-70, W, H],
        fill=(0, 0, 0)
    )

    draw.rectangle(
        [0, H-70, W, H-66],
        fill=style["accent"]
    )

    draw.text(
        (40, H-50),
        "* EVCARIX",
        font=font(28),
        fill=(255,255,255)
    )

    draw.text(
        (W-240, H-50),
        "FUTURE TECH",
        font=font(24, False),
        fill=(120,120,120)
    )

    return img

# =============================================================================
# MAIN CLASS
# =============================================================================


class ThumbnailGenerator:

    def create(
        self,
        title: str,
        topic: str = "default",
        output_path: str = "",
        is_short: bool = False,
    ):

        # SHORTS = NO THUMBNAIL

        if is_short:

            logger.info(
                "[Thumbnail] Shorts skipped."
            )

            return ""

        W = 1280
        H = 720

        topic_key = topic.lower().replace(
            " ",
            "_"
        )

        style = TOPIC_STYLES.get(
            topic_key,
            TOPIC_STYLES["default"]
        )

        lines = split_title(title)

        layout = pick_layout(title)

        try:

            img = render_thumbnail(
                W,
                H,
                lines,
                style,
                layout
            )

            if not output_path:

                safe = safe_filename(title)

                output_path = os.path.join(
                    OUTPUT_DIR,
                    f"{safe}_{layout}.jpg"
                )

            img.save(
                output_path,
                "JPEG",
                quality=97
            )

            logger.info(
                f"[Thumbnail] OK → {output_path}"
            )

            return output_path

        except Exception as e:

            logger.error(
                f"[Thumbnail] ERROR → {e}"
            )

            return ""

    # =========================================================================

    def upload_thumbnail(
        self,
        video_id: str,
        thumbnail_path: str
    ):

        try:

            token_json = os.getenv(
                "YOUTUBE_TOKEN_JSON"
            )

            secret_json = os.getenv(
                "YOUTUBE_CLIENT_SECRET_JSON"
            )

            if not token_json or not secret_json:

                logger.warning(
                    "[Thumbnail] Missing YouTube credentials"
                )

                return False

            token_data = json.loads(token_json)

            secret_data = json.loads(secret_json)

            creds = Credentials(

                token=token_data.get("token"),

                refresh_token=token_data.get(
                    "refresh_token"
                ),

                token_uri="https://oauth2.googleapis.com/token",

                client_id=secret_data["installed"]["client_id"],

                client_secret=secret_data["installed"]["client_secret"],

                scopes=[
                    "https://www.googleapis.com/auth/youtube.force-ssl"
                ]
            )

            youtube = build(
                "youtube",
                "v3",
                credentials=creds
            )

            media = MediaFileUpload(
                thumbnail_path,
                mimetype="image/jpeg"
            )

            youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()

            logger.info(
                f"[Thumbnail] Uploaded → {video_id}"
            )

            return True

        except Exception as e:

            logger.error(
                f"[Thumbnail] Upload failed → {e}"
            )

            return False

# =============================================================================
# HELPER
# =============================================================================


def generate_and_upload(
    video_id,
    title,
    topic="default"
):

    gen = ThumbnailGenerator()

    path = gen.create(
        title=title,
        topic=topic
    )

    if path and os.path.exists(path):

        return gen.upload_thumbnail(
            video_id,
            path
        )

    return False

# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO
    )

    gen = ThumbnailGenerator()

    gen.create(
        title="Tesla Battery Breakthrough Changes EV Future",
        topic="electric_vehicle"
    )

    gen.create(
        title="AI Will Replace Millions Of Jobs",
        topic="artificial_intelligence"
    )

    gen.create(
        title="1 Million KM Battery Is Real",
        topic="battery_tech"
    )

    gen.create(
        title="Robots Are Taking Over Factories",
        topic="robotics"
    )
