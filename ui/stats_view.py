"""통계 뷰 — 방문자 통계 차트 + 달력 + CSV 내보내기"""

import os
import csv
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QFileDialog, QComboBox, QCalendarWidget,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QRectF, QDate
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient, QTextCharFormat

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
        self._selected_date = None  # None = 범위 모드, str = 날짜 모드

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # 헤더
        header = QHBoxLayout()
        title = QLabel("방문 통계")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1f5f9;")
        header.addWidget(title)
        header.addStretch()

        self.combo_range = QComboBox()
        self.combo_range.addItems(["최근 7일", "최근 14일", "최근 30일"])
        self.combo_range.currentIndexChanged.connect(self._on_range_changed)
        header.addWidget(self.combo_range)

        btn_export = QPushButton("📥 CSV 내보내기")
        btn_export.clicked.connect(self._export_csv)
        header.addWidget(btn_export)

        btn_refresh = QPushButton("🔄 새로고침")
        btn_refresh.clicked.connect(self._refresh)
        header.addWidget(btn_refresh)

        layout.addLayout(header)

        # ── 메인 영역: 달력(왼쪽) + 통계(오른쪽) ──
        main_area = QHBoxLayout()
        main_area.setSpacing(16)

        # 달력
        cal_card = QFrame()
        cal_card.setObjectName("glassCard")
        cal_layout = QVBoxLayout(cal_card)
        cal_layout.setContentsMargins(12, 12, 12, 12)
        cal_layout.setSpacing(8)

        cal_title = QLabel("날짜 선택")
        cal_title.setObjectName("titleLabel")
        cal_layout.addWidget(cal_title)

        self._selected_date_label = QLabel("")
        self._selected_date_label.setStyleSheet("font-size: 12px; color: #00A8FF; font-weight: bold;")
        cal_layout.addWidget(self._selected_date_label)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setFixedSize(300, 240)
        self.calendar.setStyleSheet(self._calendar_style())
        self.calendar.clicked.connect(self._on_date_clicked)
        cal_layout.addWidget(self.calendar)

        btn_clear_date = QPushButton("날짜 선택 해제")
        btn_clear_date.setFixedHeight(30)
        btn_clear_date.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.06); color: #94a3b8;
                border: 1px solid rgba(255,255,255,0.12); border-radius: 6px;
                font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(255,255,255,0.10); color: #f1f5f9; }
        """)
        btn_clear_date.clicked.connect(self._clear_date_selection)
        cal_layout.addWidget(btn_clear_date)

        cal_layout.addStretch()
        cal_card.setFixedWidth(324)
        main_area.addWidget(cal_card)

        # 오른쪽: 통계 콘텐츠
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        # 요약 카드
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        self._lbl_total = self._make_summary_card("총 방문", "0")
        self._lbl_registered = self._make_summary_card("등록 방문자", "0")
        self._lbl_unregistered = self._make_summary_card("미등록 방문자", "0")
        summary_row.addWidget(self._lbl_total)
        summary_row.addWidget(self._lbl_registered)
        summary_row.addWidget(self._lbl_unregistered)
        right_panel.addLayout(summary_row)

        # 차트
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)
        self.daily_chart = BarChart()
        charts_layout.addWidget(self.daily_chart, 1)
        self.hourly_chart = BarChart()
        charts_layout.addWidget(self.hourly_chart, 1)
        right_panel.addLayout(charts_layout, 1)

        # 자주 오는 방문자 / 선택 날짜 방문 기록
        top_card = QFrame()
        top_card.setObjectName("glassCard")
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(16, 12, 16, 12)
        self._top_title = QLabel("자주 오는 방문자 TOP 5")
        self._top_title.setObjectName("titleLabel")
        top_layout.addWidget(self._top_title)
        self._top_list = QLabel("데이터 없음")
        self._top_list.setObjectName("subtitleLabel")
        self._top_list.setWordWrap(True)
        top_layout.addWidget(self._top_list)
        right_panel.addWidget(top_card)

        main_area.addLayout(right_panel, 1)
        layout.addLayout(main_area, 1)

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

    def _on_date_clicked(self, date: QDate):
        """달력 날짜 클릭 → 해당 날짜 통계 표시"""
        self._selected_date = date.toString("yyyy-MM-dd")
        self._selected_date_label.setText(f"선택: {self._selected_date}")
        self._refresh()

    def _clear_date_selection(self):
        """날짜 선택 해제 → 범위 모드로 복귀"""
        self._selected_date = None
        self._selected_date_label.setText("")
        self._refresh()

    def _on_range_changed(self):
        """콤보박스 변경 → 날짜 선택 해제 + 범위 모드"""
        self._selected_date = None
        self._selected_date_label.setText("")
        self._refresh()

    def _refresh(self):
        if self._selected_date:
            self._refresh_date(self._selected_date)
        else:
            self._refresh_range()

    def _refresh_range(self):
        """범위 모드 (최근 N일)"""
        days_map = {0: 7, 1: 14, 2: 30}
        days = days_map.get(self.combo_range.currentIndex(), 7)

        stats = database.get_visit_stats(days)

        total = sum(r["cnt"] for r in stats) if stats else 0
        reg = sum(r["registered"] for r in stats) if stats else 0
        unreg = sum(r["unregistered"] for r in stats) if stats else 0
        self._lbl_total._val_label.setText(str(total))
        self._lbl_registered._val_label.setText(str(reg))
        self._lbl_unregistered._val_label.setText(str(unreg))

        daily_data = []
        for r in (stats or []):
            day_str = r["day"][5:]
            daily_data.append((day_str, r["cnt"], Q_CYAN))
        self.daily_chart.set_data(daily_data, "일별 방문자 수")

        hourly = database.get_hourly_stats()
        hourly_data = []
        for r in (hourly or []):
            hourly_data.append((f"{r['hour']}시", r["cnt"], Q_GREEN))
        self.hourly_chart.set_data(hourly_data, "오늘 시간대별")

        self._top_title.setText("자주 오는 방문자 TOP 5")
        top = database.get_top_visitors(5)
        if top:
            lines = []
            for i, r in enumerate(top):
                lines.append(f"{i+1}. {r['visitor_name']}  —  {r['visit_count']}회  (최근: {r['last_visit'][:10]})")
            self._top_list.setText("\n".join(lines))
        else:
            self._top_list.setText("데이터 없음")

    def _refresh_date(self, date_str: str):
        """날짜 모드 (선택한 날짜 하루)"""
        # 해당 날짜 방문 로그
        rows = database.execute(
            "SELECT * FROM visit_logs WHERE timestamp LIKE ? ORDER BY timestamp",
            (f"{date_str}%",), fetch="all") or []

        total = len(rows)
        reg = sum(1 for r in rows if r["is_registered"])
        unreg = total - reg
        self._lbl_total._val_label.setText(str(total))
        self._lbl_registered._val_label.setText(str(reg))
        self._lbl_unregistered._val_label.setText(str(unreg))

        # 일별 차트 → 해당 날짜 하루만
        self.daily_chart.set_data(
            [(date_str[5:], total, Q_CYAN)], f"{date_str} 방문자")

        # 시간대 차트
        hourly = database.get_hourly_stats(date_str)
        hourly_data = []
        for r in (hourly or []):
            hourly_data.append((f"{r['hour']}시", r["cnt"], Q_GREEN))
        self.hourly_chart.set_data(hourly_data, f"{date_str} 시간대별")

        # 해당 날짜 방문 기록 목록
        self._top_title.setText(f"{date_str} 방문 기록")
        if rows:
            lines = []
            for r in rows:
                t = r["timestamp"][11:16] if len(r["timestamp"]) >= 16 else r["timestamp"]
                tag = "등록" if r["is_registered"] else "미등록"
                lines.append(f"{t}  {r['visitor_name']}  [{tag}]")
            self._top_list.setText("\n".join(lines))
        else:
            self._top_list.setText("방문 기록 없음")

    @staticmethod
    def _calendar_style() -> str:
        return """
        QCalendarWidget {
            background: transparent;
        }
        QCalendarWidget QToolButton {
            background: rgba(255,255,255,0.06);
            color: #f1f5f9;
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            font-weight: bold;
        }
        QCalendarWidget QToolButton:hover {
            background: rgba(0,168,255,0.15);
            color: #00A8FF;
        }
        QCalendarWidget QToolButton#qt_calendar_prevmonth,
        QCalendarWidget QToolButton#qt_calendar_nextmonth {
            min-width: 28px; min-height: 28px;
            qproperty-icon: none;
        }
        QCalendarWidget QToolButton#qt_calendar_prevmonth { qproperty-text: "<"; }
        QCalendarWidget QToolButton#qt_calendar_nextmonth { qproperty-text: ">"; }
        QCalendarWidget QMenu {
            background: #111827; color: #f1f5f9;
            border: 1px solid rgba(255,255,255,0.10);
        }
        QCalendarWidget QSpinBox {
            background: rgba(255,255,255,0.06); color: #f1f5f9;
            border: 1px solid rgba(255,255,255,0.10); border-radius: 4px;
            font-size: 12px; padding: 2px;
        }
        QCalendarWidget QAbstractItemView {
            background: rgba(255,255,255,0.03);
            color: #f1f5f9;
            selection-background-color: rgba(0,168,255,0.30);
            selection-color: #00A8FF;
            font-size: 12px;
            outline: none;
        }
        QCalendarWidget QAbstractItemView:enabled {
            color: #f1f5f9;
        }
        QCalendarWidget QAbstractItemView:disabled {
            color: #475569;
        }
        QCalendarWidget QWidget#qt_calendar_navigationbar {
            background: rgba(255,255,255,0.04);
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding: 4px;
        }
        """

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV 내보내기", "visit_logs.csv", "CSV (*.csv)")
        if not path:
            return

        if self._selected_date:
            rows = database.execute(
                "SELECT * FROM visit_logs WHERE timestamp LIKE ? ORDER BY timestamp",
                (f"{self._selected_date}%",), fetch="all") or []
        else:
            days_map = {0: 7, 1: 14, 2: 30}
            days = days_map.get(self.combo_range.currentIndex(), 7)
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            rows = database.execute(
                "SELECT * FROM visit_logs WHERE timestamp >= ? ORDER BY timestamp",
                (start,), fetch="all") or []

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "방문자ID", "이름", "시간", "신뢰도", "등록여부"])
            for r in rows:
                writer.writerow([r["id"], r["visitor_id"], r["visitor_name"],
                                 r["timestamp"], f"{r['confidence']:.2f}",
                                 "등록" if r["is_registered"] else "미등록"])

        from .toast_widget import ToastWidget
        ToastWidget.show_toast(self.window(), f"CSV 저장: {os.path.basename(path)}", True)
