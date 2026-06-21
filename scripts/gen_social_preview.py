"""One-off generator for the GitHub social preview image (assets/image/social-preview.png)."""

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 640
BG = (26, 27, 38)
GLOW = (90, 60, 160)
WHITE = (245, 245, 250)
VIOLET = (179, 146, 240)
FONT_DIR = "C:/Windows/Fonts/"
wordmark_font = ImageFont.truetype(FONT_DIR + "seguibl.ttf", 88)
tagline_font = ImageFont.truetype(FONT_DIR + "seguisb.ttf", 32)

img = Image.new("RGB", (WIDTH, HEIGHT), BG)

# Soft radial glow behind the logo
glow = Image.new("RGB", (WIDTH, HEIGHT), BG)
glow_draw = ImageDraw.Draw(glow)
cx, cy = 300, HEIGHT // 2
max_r = 380
for r in range(max_r, 0, -4):
    t = r / max_r
    color = tuple(int(BG[i] + (GLOW[i] - BG[i]) * (1 - t) * 0.55) for i in range(3))
    glow_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
img = glow

# Logo, left-aligned
logo = Image.open("assets/image/memcord_1024.png").convert("RGBA")
logo_size = 460
logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
logo_x = 70
logo_y = (HEIGHT - logo_size) // 2
img.paste(logo, (logo_x, logo_y), logo)

draw = ImageDraw.Draw(img)

text_x = logo_x + logo_size + 60
y = 250
draw.text((text_x, y), "memcord", font=wordmark_font, fill=WHITE)
bbox = draw.textbbox((text_x, y), "memcord", font=wordmark_font)
y = bbox[3] + 24
draw.text((text_x, y), "MCP server for long-term AI memory", font=tagline_font, fill=VIOLET)
img.save("assets/image/social-preview.png")
print("saved assets/image/social-preview.png")
