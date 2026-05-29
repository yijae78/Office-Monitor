"""OfficeMonitor 앱 아이콘 v5 — 투명 배경, 밝고 빛나는 렌즈"""

from PIL import Image, ImageDraw, ImageFilter
import math

SIZE = 512
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))  # 완전 투명
cx, cy = SIZE // 2, SIZE // 2

# ── 1. 외부 글로우 (투명 배경 위에 빛나는 효과) ──
glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for radius in range(250, 0, -1):
    t = 1 - radius / 250
    alpha = int(30 * t ** 2)
    gd.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
               fill=(0, 180, 255, alpha))
img = Image.alpha_composite(img, glow)

# ── 2. 외부 링 (매우 밝고 굵은 시안→화이트) ──
outer_r = 200
ring_w = 35

ring = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
rd = ImageDraw.Draw(ring)

# 링 베이스
for r in range(outer_r, outer_r - ring_w, -1):
    t = (r - (outer_r - ring_w)) / ring_w
    # 바깥=밝은 시안, 안쪽=더 밝은 시안
    red = int(40 + 80 * (1 - t))
    green = int(200 + 40 * (1 - t))
    blue = 255
    rd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(red, green, blue, 255))

# 상단 하이라이트 (거의 하얀색)
for angle_deg in range(-80, 80):
    angle = math.radians(angle_deg)
    for depth in range(ring_w):
        r = outer_r - depth
        x = cx + int(r * math.cos(angle - math.pi / 2))
        y = cy + int(r * math.sin(angle - math.pi / 2))
        t = (1 - abs(angle_deg) / 80) ** 1.2
        d = 1 - depth / ring_w
        boost = int(140 * t * d)
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px = ring.getpixel((x, y))
            if px[3] > 0:
                ring.putpixel((x, y), (
                    min(255, px[0] + boost),
                    min(255, px[1] + boost),
                    min(255, px[2] + int(boost * 0.6)),
                    255
                ))

# 하단 약간 어둡게 (입체)
for angle_deg in range(100, 260):
    angle = math.radians(angle_deg)
    for depth in range(ring_w):
        r = outer_r - depth
        x = cx + int(r * math.cos(angle - math.pi / 2))
        y = cy + int(r * math.sin(angle - math.pi / 2))
        t_a = 1 - min(abs(angle_deg - 180), 80) / 80
        d = 1 - depth / ring_w
        darken = int(40 * t_a * d)
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px = ring.getpixel((x, y))
            if px[3] > 0:
                ring.putpixel((x, y), (
                    max(0, px[0] - darken),
                    max(0, px[1] - int(darken * 0.5)),
                    max(0, px[2] - int(darken * 0.3)),
                    255
                ))

img = Image.alpha_composite(img, ring)

# ── 3. 링 외부 밝은 글로우 (빛 번짐) ──
ring_glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
rgd = ImageDraw.Draw(ring_glow)
for r in range(outer_r + 20, outer_r, -1):
    t = 1 - (r - outer_r) / 20
    rgd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(100, 220, 255, int(50 * t)))
img = Image.alpha_composite(img, ring_glow)

# ── 4. 내부 렌즈 (밝은 그라디언트 — 어둡지 않게) ──
inner = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
ind = ImageDraw.Draw(inner)
inner_r = outer_r - ring_w

# 렌즈 내부: 진한 남색이지만 밝은 편
for r in range(inner_r, 0, -1):
    t = r / inner_r
    red = int(15 + 60 * (1 - t))
    green = int(35 + 100 * (1 - t))
    blue = int(70 + 130 * (1 - t))
    ind.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(red, green, blue, 255))

img = Image.alpha_composite(img, inner)

# ── 5. 내부 링 ──
ir = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
ird = ImageDraw.Draw(ir)
ird.ellipse([cx - inner_r + 8, cy - inner_r + 8, cx + inner_r - 8, cy + inner_r - 8],
            outline=(80, 210, 255, 100), width=2)
ird.ellipse([cx - 95, cy - 95, cx + 95, cy + 95],
            outline=(80, 210, 255, 60), width=1)
img = Image.alpha_composite(img, ir)

# ── 6. 중앙 "M" 글자 (크고 밝게) ──
from PIL import ImageFont

m_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

# 글로우용 레이어
m_glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
mg = ImageDraw.Draw(m_glow)

# 본체용 레이어
md = ImageDraw.Draw(m_layer)

# 폰트 (굵은 폰트 시도)
font_size = 280
for fname in ["arialbd.ttf", "calibrib.ttf", "arial.ttf", "segoeui.ttf"]:
    try:
        m_font = ImageFont.truetype(fname, font_size)
        break
    except:
        continue
else:
    m_font = ImageFont.load_default()

letter = "M"
bbox = md.textbbox((0, 0), letter, font=m_font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
tx = cx - tw // 2
ty = cy - th // 2 - bbox[1]

# 글로우 (시안 번짐)
mg.text((tx, ty), letter, fill=(0, 200, 255, 120), font=m_font)
m_glow = m_glow.filter(ImageFilter.GaussianBlur(12))
img = Image.alpha_composite(img, m_glow)

# 2차 글로우 (더 강하게)
m_glow2 = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
ImageDraw.Draw(m_glow2).text((tx, ty), letter, fill=(0, 220, 255, 80), font=m_font)
m_glow2 = m_glow2.filter(ImageFilter.GaussianBlur(6))
img = Image.alpha_composite(img, m_glow2)

# 본체 (밝은 흰색)
md.text((tx, ty), letter, fill=(255, 255, 255, 255), font=m_font)
img = Image.alpha_composite(img, m_layer)

# ── 8. 녹화 LED (빨간 점, 밝게) ──
led = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
ld = ImageDraw.Draw(led)
lx, ly = cx + 152, cy - 152

for r in range(30, 0, -1):
    t = 1 - r / 30
    ld.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(255, 50, 30, int(50 * t)))
for r in range(13, 0, -1):
    t = 1 - r / 13
    ld.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(255, int(80 + 120 * t), int(60 + 80 * t), int(255 * t ** 0.5)))

img = Image.alpha_composite(img, led)

# ── 9. 저장 ──
img.save("icon_preview.png", "PNG")
print(f"아이콘 생성 완료: icon_preview.png ({SIZE}x{SIZE})")
