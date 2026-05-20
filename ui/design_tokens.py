"""OfficeMonitor 디자인 토큰 — 신교수님 통합 디자인 시스템 기반"""

from PyQt6.QtGui import QColor, QFont

# ── 배경 계층 ──
BG_VOID = "#0a0e1a"
BG_PRIMARY = "#0c111b"
BG_RAISED = "#111827"
SURFACE_1 = "rgba(255,255,255,0.04)"
SURFACE_2 = "rgba(255,255,255,0.06)"
SURFACE_3 = "rgba(255,255,255,0.09)"

# ── 텍스트 계층 ──
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
TEXT_DISABLED = "rgba(255,255,255,0.25)"

# ── 시맨틱 악센트 ──
GREEN = "#22c55e"
GREEN_LIGHT = "#34d399"
BLUE = "#3b82f6"
BLUE_LIGHT = "#60a5fa"
AMBER = "#f59e0b"
AMBER_LIGHT = "#fbbf24"
RED = "#ef4444"
RED_LIGHT = "#f87171"

# ── 브랜드 악센트 (블루-시안, 기술/모니터링) ──
CYAN = "#00A8FF"
CYAN_LIGHT = "#00d4ff"
CYAN_PALE = "#38bdf8"

# ── 보더 ──
BORDER = "rgba(255,255,255,0.08)"
BORDER_HOVER = "rgba(255,255,255,0.15)"
BORDER_ACCENT = "rgba(0,168,255,0.25)"

# ── QColor 인스턴스 (QPainter용) ──
Q_BG_VOID = QColor(10, 14, 26)
Q_BG_PRIMARY = QColor(12, 17, 27)
Q_BG_RAISED = QColor(17, 24, 39)
Q_TEXT_PRIMARY = QColor(241, 245, 249)
Q_TEXT_SECONDARY = QColor(148, 163, 184)
Q_TEXT_MUTED = QColor(100, 116, 139)

Q_GREEN = QColor(34, 197, 94)
Q_BLUE = QColor(59, 130, 246)
Q_AMBER = QColor(245, 158, 11)
Q_RED = QColor(239, 68, 68)
Q_CYAN = QColor(0, 168, 255)
Q_CYAN_LIGHT = QColor(0, 212, 255)

Q_BORDER = QColor(255, 255, 255, 20)  # ~0.08
Q_SURFACE_1 = QColor(255, 255, 255, 10)  # ~0.04
Q_SURFACE_2 = QColor(255, 255, 255, 15)  # ~0.06
Q_SURFACE_3 = QColor(255, 255, 255, 23)  # ~0.09

# ── 스페이싱 (4px 기반) ──
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_8 = 32

# ── Border-radius ──
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 12
RADIUS_XL = 20
RADIUS_FULL = 9999

# ── 그림자 ──
SHADOW_SM = (0, 1, 3, 76)    # offset_x, offset_y, blur, alpha
SHADOW_MD = (0, 4, 16, 76)
SHADOW_LG = (0, 8, 32, 102)
SHADOW_GLOW_CYAN = (0, 0, 24, 51)  # 시안 글로우

# ── 타이포 ──
FONT_UI = "Pretendard Variable"
FONT_FALLBACK = "Segoe UI"
FONT_CODE = "JetBrains Mono"

def font_kpi() -> QFont:
    f = QFont(FONT_UI, 28)
    f.setWeight(QFont.Weight.Bold)
    return f

def font_title() -> QFont:
    f = QFont(FONT_UI, 16)
    f.setWeight(QFont.Weight.Bold)
    return f

def font_subtitle() -> QFont:
    f = QFont(FONT_UI, 12)
    f.setWeight(QFont.Weight.Normal)
    return f

def font_label() -> QFont:
    f = QFont(FONT_UI, 11)
    f.setWeight(QFont.Weight.DemiBold)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
    return f

def font_body() -> QFont:
    f = QFont(FONT_UI, 13)
    f.setWeight(QFont.Weight.Normal)
    return f
