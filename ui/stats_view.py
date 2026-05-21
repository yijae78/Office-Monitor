"""통계 뷰 — 방문자 통계 차트 + CSV 내보내기"""

import os
import csv
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QFileDialog, QComboBox,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient

import database
from .design_tokens import (
    Q_CYAN, Q_GREEN, Q_AMBER, Q_RED, Q_TEXT_PRIMARY, Q_TEXT_SECONDARY,
    Q_TEXT_MUTED, Q_BORDER, Q_SURFACE_1, FONT_UI, RADIUS_MD,
)


class BarChart(QWidget):
    """간단한 바 차트 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # [(label, value, color)]
        self._title = ""
        self.setMinimumHeight(220)

    def set_data(self, data: list, title: str = ""):
        self._data = data
        self._title = title
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(16, 12, -16, -12)

        # 배경
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 10))
        painter.drawRoundedRect(rect, RADIUS_MD, RADIUS_MD)

        # 제목
        if self._title:
            painter.setPen(Q_TEXT_PRIMARY)
            font = QFont(FONT_UI, 14)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(rect.x() + 12, rect.y() + 8, rect.width(), 24),
                             Qt.AlignmentFlag.AlignLeft, self._title)

        max_val = max((d[1] for d in self._data), default=1) or 1
        chart_top = rect.y() + 44
        chart_h = rect.height() - 72
        bar_w = min(40, (rect.width() - 40) / max(len(self._data), 1) - 8)
        spacing = (rect.width() - 40 - bar_w * len(self._data)) / max(len(self._data), 1)

        font_sm = QFont(FONT_UI, 9)
        painter.setFont(font_sm)

        for i, (label, value, color) in enumerate(self._data):
            x = rect.x() + 20 + i * (bar_w + spacing)
            bar_h = (value / max_val) * chart_h if max_val > 0 else 0
            y = chart_top + chart_h - bar_h

            # 바
            grad = QLinearGradient(x, y, x, chart_top + chart_h)
            grad.setColorAt(0, color)
            c2 = QColor(color)
            c2.setAlphaF(0.3)
            grad.setColorAt(1, c2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 4, 4)

            # 값
            painter.setPen(Q_TEXT_PRIMARY)
            painter.drawText(QRectF(x - 4, y - 18, bar_w + 8, 16),
                             Qt.AlignmentFlag.AlignCenter, str(value))

            # 라벨
            painter.setPen(Q_TEXT_MUTED)
            painter.drawText(QRectF(x - 8, chart_top + chart_h + 4, bar_w + 16, 16),
                             Qt.AlignmentFlag.AlignCenter, label)

        painter.end()


class StatsView(QWidget):
    """통계 탭"""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # 헤더
        header = QHBoxLayout()
        title = QLabel("방문 통계")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1f5f9;")
        header.addWidget(title)
        header.addStretch()

        self.combo_range = QComboBox()
        self.combo_range.addItems(["최근 7일", "최근 14일", "최근 30일"])
        self.combo_range.currentIndexChanged.connect(self._refresh)
        header.addWidget(self.combo_range)

        btn_export = QPushButton("📥 CSV 내보내기")
        btn_export.clicked.connect(self._export_csv)
        header.addWidget(btn_export)

        btn_refresh = QPushButton("🔄 새로고침")
        btn_refresh.clicked.connect(self._refresh)
        header.addWidget(btn_refresh)

        layout.addLayout(header)

        # 요약 카드
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        self._lbl_total = self._make_summary_card("총 방문", "0")
        self._lbl_registered = self._make_summary_card("등록 방문자", "0")
        self._lbl_unregistered = self._make_summary_card("미등록 방문자", "0")
        summary_row.addWidget(self._lbl_total)
        summary_row.addWidget(self._lbl_registered)
        summary_row.addWidget(self._lbl_unregistered)
        layout.addLayout(summary_row)

        # 차트
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)

        self.daily_chart = BarChart()
        charts_layout.addWidget(self.daily_chart, 1)

        self.hourly_chart = BarChart()
        charts_layout.addWidget(self.hourly_chart, 1)

        layout.addLayout(charts_layout, 1)

        # 자주 오는 방문자
        top_card = QFrame()
        top_card.setObjectName("glassCard")
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(16, 12, 16, 12)
        top_title = QLabel("자주 오는 방문자 TOP 5")
        top_title.setObjectName("titleLabel")
        top_layout.addWidget(top_title)
        self._top_list = QLabel("데이터 없음")
        self._top_list.setObjectName("subtitleLabel")
        self._top_list.setWordWrap(True)
        top_layout.addWidget(self._top_list)
        layout.addWidget(top_card)

        self._refresh()

    def _make_summary_card(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("glassCard")
        card.setFixedHeight(80)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)

        val = QLabel(value)
        val.setObjectName("kpiValue")
        val.setStyleSheet("font-size: 24px; font-weight: bold; color: #f1f5f9;")
        cl.addWidget(val)

        lbl = QLabel(label)
        lbl.setObjectName("kpiLabel")
        lbl.setStyleSheet("font-size: 10px; color: #94a3b8; text-transform: uppercase;")
        cl.addWidget(lbl)

        card._val_label = val
        return card

    def _refresh(self):
        days_map = {0: 7, 1: 14, 2: 30}
        days = days_map.get(self.combo_range.currentIndex(), 7)

        stats = database.get_visit_stats(days)

        # 요약
        total = sum(r["cnt"] for r in stats) if stats else 0
        reg = sum(r["registered"] for r in stats) if stats else 0
        unreg = sum(r["unregistered"] for r in stats) if stats else 0
        self._lbl_total._val_label.setText(str(total))
        self._lbl_registered._val_label.setText(str(reg))
        self._lbl_unregistered._val_label.setText(str(unreg))

        # 일별 차트
        daily_data = []
        for r in (stats or []):
            day_str = r["day"][5:]  # MM-DD
            daily_data.append((day_str, r["cnt"], Q_CYAN))
        self.daily_chart.set_data(daily_data, "일별 방문자 수")

        # 시간대 차트
        hourly = database.get_hourly_stats()
        hourly_data = []
        for r in (hourly or []):
            hourly_data.append((f"{r['hour']}시", r["cnt"], Q_GREEN))
        self.hourly_chart.set_data(hourly_data, "오늘 시간대별")

        # TOP 방문자
        top = database.get_top_visitors(5)
        if top:
            lines = []
            for i, r in enumerate(top):
                lines.append(f"{i+1}. {r['visitor_name']}  —  {r['visit_count']}회  (최근: {r['last_visit'][:10]})")
            self._top_list.setText("\n".join(lines))
        else:
            self._top_list.setText("데이터 없음")

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV 내보내기", "visit_logs.csv", "CSV (*.csv)")
        if not path:
            return

        days_map = {0: 7, 1: 14, 2: 30}
        days = days_map.get(self.combo_range.currentIndex(), 7)

        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = database.execute(
            "SELECT * FROM visit_logs WHERE timestamp >= ? ORDER BY timestamp",
            (start,), fetch="all"
        )

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "방문자ID", "이름", "시간", "신뢰도", "등록여부"])
            for r in rows:
                writer.writerow([r["id"], r["visitor_id"], r["visitor_name"],
                                 r["timestamp"], f"{r['confidence']:.2f}",
                                 "등록" if r["is_registered"] else "미등록"])

        from .toast_widget import ToastWidget
        ToastWidget.show_toast(self.window(), f"CSV 저장: {os.path.basename(path)}", True)
