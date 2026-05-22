"""OfficeMonitor QSS 스타일시트 — 신교수님 디자인 시스템 완전 적용"""

MAIN_STYLE = """
/* ══════════════════════════════════════════
   전역
   ══════════════════════════════════════════ */
* {
    font-family: 'Pretendard Variable', 'Inter', 'Segoe UI', 'Malgun Gothic', 'Noto Sans KR', sans-serif;
    color: #f1f5f9;
    outline: none;
}

QMainWindow, QWidget#centralWidget {
    background: #0c111b;
}

/* ══════════════════════════════════════════
   헤더바
   ══════════════════════════════════════════ */
QWidget#headerBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(12,17,27,0.98), stop:1 rgba(17,24,39,0.98));
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

QLabel#appTitle {
    font-size: 16px;
    font-weight: bold;
    color: #f1f5f9;
    padding-left: 4px;
}

QLabel#appDot {
    font-size: 20px;
    color: #00A8FF;
}

QLabel#clockLabel {
    font-size: 12px;
    color: #94a3b8;
    font-family: 'JetBrains Mono', 'D2Coding', monospace;
}

QLabel#dateLabel {
    font-size: 12px;
    color: #64748b;
    font-family: 'Pretendard Variable', 'Segoe UI', sans-serif;
}

/* ── 세그먼트 컨트롤 ── */
QWidget#segmentGroup {
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    padding: 3px;
}

QPushButton.segmentBtn {
    background: transparent;
    color: #64748b;
    border: none;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
    font-weight: bold;
    min-width: 40px;
}
QPushButton.segmentBtn:hover {
    color: #94a3b8;
    background: rgba(255,255,255,0.04);
}
QPushButton.segmentBtn[active="true"] {
    background: rgba(255,255,255,0.09);
    color: #00A8FF;
}

/* ── 설정 버튼 ── */
QPushButton#settingsBtn {
    background: transparent;
    color: #64748b;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 6px 10px;
    font-size: 14px;
}
QPushButton#settingsBtn:hover {
    color: #f1f5f9;
    border-color: rgba(0,168,255,0.3);
    background: rgba(0,168,255,0.06);
}

/* ══════════════════════════════════════════
   상태바
   ══════════════════════════════════════════ */
QStatusBar {
    background: #111827;
    border-top: 1px solid rgba(255,255,255,0.06);
    font-size: 12px;
    padding: 4px 12px;
    min-height: 28px;
}
QStatusBar::item { border: none; }
QStatusBar QLabel {
    font-size: 12px;
    color: #94a3b8;
    padding: 0 6px;
}

/* ══════════════════════════════════════════
   서브 툴바 (모니터링 뷰 상단)
   ══════════════════════════════════════════ */
QWidget#subToolbar {
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    border-radius: 0;
}

/* ══════════════════════════════════════════
   버튼
   ══════════════════════════════════════════ */
QPushButton {
    background: rgba(59,130,246,0.10);
    color: #60a5fa;
    border: 1px solid rgba(59,130,246,0.25);
    border-radius: 10px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton:hover {
    background: rgba(59,130,246,0.18);
}
QPushButton:pressed {
    background: rgba(59,130,246,0.25);
}
QPushButton:disabled {
    color: rgba(255,255,255,0.25);
    background: rgba(255,255,255,0.03);
    border-color: rgba(255,255,255,0.05);
}

/* 녹화 버튼 */
QPushButton#btnRecord {
    background: rgba(239,68,68,0.10);
    color: #f87171;
    border: 1px solid rgba(239,68,68,0.25);
}
QPushButton#btnRecord:hover {
    background: rgba(239,68,68,0.18);
}
QPushButton#btnRecord[recording="true"] {
    background: rgba(239,68,68,0.25);
    color: #ff5252;
    border: 1px solid rgba(239,68,68,0.5);
}

/* 캡처 버튼 */
QPushButton#btnCapture {
    background: rgba(34,197,94,0.10);
    color: #34d399;
    border: 1px solid rgba(34,197,94,0.25);
}
QPushButton#btnCapture:hover {
    background: rgba(34,197,94,0.18);
}

/* 줌 버튼 */
QPushButton#zoomBtn {
    background: rgba(255,255,255,0.08);
    color: #f1f5f9;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px;
    padding: 2px 6px;
    font-size: 15px;
    font-weight: bold;
}
QPushButton#zoomBtn:hover {
    background: rgba(0,168,255,0.20);
    color: #38bdf8;
    border-color: rgba(0,168,255,0.4);
}

/* 일시정지 버튼 */
QPushButton#btnPause {
    background: rgba(245,158,11,0.10);
    color: #fbbf24;
    border: 1px solid rgba(245,158,11,0.25);
}
QPushButton#btnPause:hover {
    background: rgba(245,158,11,0.18);
}

/* ══════════════════════════════════════════
   패널 토글 버튼
   ══════════════════════════════════════════ */
QPushButton#panelToggle {
    background: rgba(255,255,255,0.04);
    border: none;
    border-left: 1px solid rgba(255,255,255,0.08);
    border-right: 1px solid rgba(255,255,255,0.08);
    color: #64748b;
    font-size: 10px;
    padding: 0;
    border-radius: 0;
}
QPushButton#panelToggle:hover {
    background: rgba(0,168,255,0.10);
    color: #00A8FF;
}

/* ── 상단 패널 토글 ── */
QPushButton#topPanelToggle {
    background: rgba(255,255,255,0.04);
    border: none;
    border-top: 1px solid rgba(255,255,255,0.08);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    color: #64748b;
    font-size: 9px;
    padding: 0;
    border-radius: 0;
}
QPushButton#topPanelToggle:hover {
    background: rgba(0,168,255,0.10);
    color: #00A8FF;
}

/* ══════════════════════════════════════════
   글래스 카드
   ══════════════════════════════════════════ */
QFrame#glassCard {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 12px;
}
QFrame#glassCard:hover {
    background: rgba(255,255,255,0.07);
    border-color: rgba(255,255,255,0.20);
}

/* ── 접기/펼치기 카드 헤더 ── */
QPushButton#cardHeader {
    background: transparent;
    border: none;
    border-radius: 12px;
    color: #f1f5f9;
    font-size: 13px;
    font-weight: bold;
    text-align: left;
    padding: 10px 12px;
}
QPushButton#cardHeader:hover {
    background: rgba(255,255,255,0.04);
}

/* ══════════════════════════════════════════
   라벨
   ══════════════════════════════════════════ */
QLabel#titleLabel {
    font-size: 14px;
    font-weight: bold;
    color: #f1f5f9;
    padding-bottom: 2px;
}
QLabel#subtitleLabel {
    font-size: 12px;
    color: #94a3b8;
}
QLabel#kpiValue {
    font-size: 28px;
    font-weight: bold;
    color: #f1f5f9;
}
QLabel#kpiLabel {
    font-size: 10px;
    font-weight: bold;
    color: #94a3b8;
}
QLabel#statusOK {
    color: #34d399;
    font-weight: bold;
    font-size: 12px;
}
QLabel#statusError {
    color: #f87171;
    font-weight: bold;
    font-size: 12px;
}
QLabel#statusWarning {
    color: #fbbf24;
    font-weight: bold;
    font-size: 12px;
}

/* ══════════════════════════════════════════
   스플리터
   ══════════════════════════════════════════ */
QSplitter::handle {
    background: rgba(255,255,255,0.04);
    width: 3px;
}
QSplitter::handle:hover {
    background: rgba(0,168,255,0.3);
}

/* ══════════════════════════════════════════
   스크롤 영역 / 스크롤바
   ══════════════════════════════════════════ */
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    width: 10px;
    background: rgba(255,255,255,0.06);
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.20);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(0,168,255,0.40);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: transparent;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    height: 6px;
    background: transparent;
}
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,0.10);
    border-radius: 3px;
    min-width: 30px;
}

/* ══════════════════════════════════════════
   콤보박스
   ══════════════════════════════════════════ */
QComboBox {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 6px 12px;
    font-size: 13px;
    color: #f1f5f9;
    min-width: 100px;
}
QComboBox:hover {
    border-color: rgba(0,168,255,0.4);
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background: #111827;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    selection-background-color: rgba(0,168,255,0.15);
    selection-color: #00A8FF;
    padding: 4px;
}

/* ══════════════════════════════════════════
   라인에딧 (검색바 등)
   ══════════════════════════════════════════ */
QLineEdit {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    color: #f1f5f9;
    selection-background-color: rgba(0,168,255,0.3);
}
QLineEdit:focus {
    border-color: #00A8FF;
}
QLineEdit::placeholder {
    color: #64748b;
}

/* ══════════════════════════════════════════
   방문자 타임라인 아이템
   ══════════════════════════════════════════ */
QWidget#timelineItem {
    background: rgba(255,255,255,0.02);
    border-radius: 8px;
    padding: 4px;
}
QWidget#timelineItem:hover {
    background: rgba(255,255,255,0.06);
}

/* ══════════════════════════════════════════
   뱃지
   ══════════════════════════════════════════ */
QLabel#badgeGreen {
    background: rgba(34,197,94,0.15);
    color: #34d399;
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}
QLabel#badgeCyan {
    background: rgba(0,168,255,0.15);
    color: #00A8FF;
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}
QLabel#badgeAmber {
    background: rgba(245,158,11,0.15);
    color: #fbbf24;
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}
QLabel#badgeRed {
    background: rgba(239,68,68,0.15);
    color: #f87171;
    border-radius: 9999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

/* ══════════════════════════════════════════
   디바이더
   ══════════════════════════════════════════ */
QFrame#divider {
    background: rgba(255,255,255,0.08);
    max-height: 1px;
    min-height: 1px;
}

/* ══════════════════════════════════════════
   빈 상태 (Empty State)
   ══════════════════════════════════════════ */
QLabel#emptyStateIcon {
    font-size: 48px;
    color: rgba(255,255,255,0.15);
}
QLabel#emptyStateTitle {
    font-size: 16px;
    font-weight: bold;
    color: #94a3b8;
}
QLabel#emptyStateDesc {
    font-size: 13px;
    color: #64748b;
}
"""
