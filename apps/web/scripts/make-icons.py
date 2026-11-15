"""Render the FINN app icons. Run: uv run --project services/api python apps/web/scripts/make-icons.py"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "apps/web/public/icons"
AND = ROOT / "apps/android/assets"
SAGE = (94, 115, 97)  # --sage-600
SURFACE = (253, 251, 248)  # --surface
FONT = "/System/Library/Fonts/Helvetica.ttc"


def mark(size: int, *, rounded: bool, safe: float = 1.0, bg=SAGE, fg=SURFACE, glyph=True) -> Image.Image:
    """A square icon. `safe` shrinks the glyph for maskable/adaptive icons (keep inside the safe zone)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if bg is not None:
        if rounded:
            d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=bg)
        else:
            d.rectangle([0, 0, size, size], fill=bg)
    if glyph:
        f = ImageFont.truetype(FONT, int(size * 0.62 * safe), index=1)  # bold face
        w = d.textlength("F", font=f)
        asc, desc = f.getmetrics()
        d.text(((size - w) / 2, (size - (asc + desc)) / 2 - size * 0.01), "F", font=f, fill=fg)
    return img


WEB.mkdir(parents=True, exist_ok=True)
AND.mkdir(parents=True, exist_ok=True)
mark(192, rounded=True).save(WEB / "icon-192.png")
mark(512, rounded=True).save(WEB / "icon-512.png")
mark(512, rounded=False, safe=0.72).save(WEB / "icon-maskable-512.png")  # full bleed, glyph in the safe zone
mark(180, rounded=False, safe=0.85).convert("RGB").save(WEB / "apple-touch-icon.png")  # iOS rounds it itself
# Android launcher sources for @capacitor/assets
mark(1024, rounded=False, safe=0.85).convert("RGB").save(AND / "icon-only.png")
mark(1024, rounded=False, bg=SAGE, glyph=False).convert("RGB").save(AND / "icon-background.png")
mark(1024, rounded=False, bg=None, safe=0.62).save(AND / "icon-foreground.png")
print("icons written")
