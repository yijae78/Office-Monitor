"""오늘 방문자 타임라인 위젯"""

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
    QPushButton, QMessageBox, QDialog, QInputDialog,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor

from .design_tokens import Q_GREEN, Q_AMBER, Q_TEXT_SECONDARY, SPACE_2, SPACE_3

logger = logging.getLogger(__name__)


class ThumbnailPopup(QDialog):
    """방문자 썸네일 팝업 다이얼로그"""

    def __init__(self, name: str, time_str: str, thumb_path: str,
                 is_registered: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{name} — {time_str}")
        self.setStyleSheet("""
            QDialog { background: #0c111b; }
            QLabel { color: #f1f5f9; }
        """)
        self.setMinimumSize(240, 200)
        self._thumb_path = thumb_path
        self._registered_name = None  # 등록 완료 시 이름 저장

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 이미지
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if thumb_path and os.path.exists(thumb_path):
            pix = QPixmap(thumb_path)
            scaled = pix.scaled(
                320, 320,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            img_label.setPixmap(scaled)
        else:
            img_label.setText("사진 없음")
            img_label.setStyleSheet("color: #64748b; font-size: 14px;")
        layout.addWidget(img_label)

        # 이름 + 시간
        info = QLabel(f"{name}  ·  {time_str}")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(info)

        # 미등록자일 때만 등록/삭제 버튼 표시
        if not is_registered and thumb_path:
            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)

            register_btn = QPushButton("방문자로 등록")
            register_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #1d6aa5, stop:1 #3b82f6);
                    color: #fff; border: none; border-radius: 10px;
                    padding: 10px 20px; font-size: 14px; font-weight: bold;
                    min-height: 36px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #2563eb, stop:1 #60a5fa);
                }
            """)
            register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            register_btn.clicked.connect(self._do_register)
            btn_row.addWidget(register_btn)

            delete_btn = QPushButton("삭제")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(239,68,68,0.15);
                    color: #f87171; border: 1px solid rgba(239,68,68,0.30);
                    border-radius: 10px;
                    padding: 10px 16px; font-size: 14px; font-weight: bold;
                    min-height: 36px;
                }
                QPushButton:hover {
                    background: rgba(239,68,68,0.30);
                    color: #fca5a5;
                }
            """)
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(self._do_delete)
            btn_row.addWidget(delete_btn)

            layout.addLayout(btn_row)

        self.adjustSize()
        self._deleted = False

    def _do_register(self):
        """미등록 얼굴을 방문자로 등록"""
        dlg = QInputDialog(self)
        dlg.setWindowTitle("방문자 등록")
        dlg.setLabelText("이름을 입력하세요:")
        dlg.setStyleSheet("""
            QInputDialog { background: #ffffff; }
            QLabel { color: #0f172a; font-size: 14px; }
            QLineEdit {
                background: #ffffff; border: 1px solid #cbd5e1;
                border-radius: 8px; padding: 8px 12px;
                font-size: 14px; color: #0f172a; min-height: 32px;
            }
            QLineEdit:focus { border-color: #00A8FF; }
            QPushButton {
                background: #3b82f6; color: white; border: none;
                border-radius: 6px; padding: 8px 20px; font-size: 13px;
            }
            QPushButton:hover { background: #2563eb; }
        """)
        if not dlg.exec() or not dlg.textValue().strip():
            return

        name = dlg.textValue().strip()

        # 감지 엔진 접근 (parent → VisitorTimelineItem → window() → MainWindow)
        main_win = self.parent().window() if self.parent() else None
        det = getattr(main_win, '_detection_thread', None) if main_win else None

        if not det or not getattr(det, '_app', None):
            QMessageBox.warning(self, "오류", "감지 엔진이 준비되지 않았습니다")
            return

        import cv2
        img = cv2.imread(self._thumb_path)
        if img is None:
            QMessageBox.warning(self, "오류", "이미지를 읽을 수 없습니다")
            return

        try:
            faces = det._app.get(img)
        except Exception as e:
            logger.warning("얼굴 재감지 실패: %s", e)
            faces = None

        if not faces:
            QMessageBox.warning(self, "오류", "이미지에서 얼굴을 찾을 수 없습니다")
            return

        import database
        visitor_id = det.register_face(name, faces[0].embedding)
        database.update_visitor_thumbnail(visitor_id, self._thumb_path)

        self._registered_name = name
        self.accept()

    def _do_delete(self):
        """타임라인에서 이 미등록 방문 기록 삭제"""
        self._deleted = True
        self.accept()


class VisitorTimelineItem(QWidget):
    """타임라인 개별 항목"""

    def __init__(self, time_str: str, name: str, thumbnail: QPixmap = None,
                 is_registered: bool = True, thumbnail_path: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("timelineItem")
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._name = name
        self._time_str = time_str
        self._thumbnail_path = thumbnail_path
        self._is_registered = is_registered

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # 시간
        time_label = QLabel(time_str)
        time_label.setObjectName("subtitleLabel")
        time_label.setFixedWidth(44)
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(time_label)

        # 아바타 (원형, 이름 이니셜)
        self._avatar = AvatarLabel(36, thumbnail, Q_GREEN if is_registered else Q_AMBER, initial=name[:1] if name else "?")
        layout.addWidget(self._avatar)

        # 이름
        self._name_label = QLabel(name)
        self._name_label.setStyleSheet(
            f"color: {'#f1f5f9' if is_registered else '#fbbf24'}; font-size: 13px; font-weight: bold;"
        )
        layout.addWidget(self._name_label, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._thumbnail_path:
            popup = ThumbnailPopup(
                self._name, self._time_str, self._thumbnail_path,
                is_registered=self._is_registered, parent=self,
            )
            popup.exec()

            # 등록이 완료됐으면 타임라인 아이템 UI 업데이트
            if popup._registered_name:
                self._mark_as_registered(popup._registered_name)
                from .toast_widget import ToastWidget
                ToastWidget.show_toast(self.window(), f"'{popup._registered_name}' 등록 완료", True)

            # 삭제 요청 시 타임라인에서 제거
            elif getattr(popup, '_deleted', False):
                self._remove_from_timeline()

        super().mousePressEvent(event)

    def _mark_as_registered(self, name: str):
        """등록 완료 후 아이템 외관을 등록자 스타일로 변경"""
        self._name = name
        self._is_registered = True
        self._name_label.setText(name)
        self._name_label.setStyleSheet(
            "color: #f1f5f9; font-size: 13px; font-weight: bold;"
        )
        self._avatar._border_color = Q_GREEN
        self._avatar._initial = name[:1] if name else "?"
        self._avatar.update()

    def _remove_from_timeline(self):
        """타임라인에서 이 아이템 제거 + DB 방문 기록 삭제"""
        import database
        # 썸네일 경로로 해당 visit_log 삭제
        if self._thumbnail_path:
            database.execute(
                "DELETE FROM visit_logs WHERE thumbnail_path=?",
                (self._thumbnail_path,),
            )
        self.setParent(None)
        self.deleteLater()
        from .toast_widget import ToastWidget
        ToastWidget.show_toast(self.window() if self.window() else None,
                               "방문 기록 삭제됨", True)


class AvatarLabel(QWidget):
    """원형 아바타"""

    def __init__(self, size: int = 36, pixmap: QPixmap = None,
                 border_color: QColor = Q_GREEN, initial: str = "?", parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap = pixmap
        self._border_color = border_color
        self._initial = initial
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 보더
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._border_color)
        painter.drawEllipse(0, 0, self._size, self._size)

        # 내부
        if self._pixmap and not self._pixmap.isNull():
            path = QPainterPath()
            path.addEllipse(2, 2, self._size - 4, self._size - 4)
            painter.setClipPath(path)
            scaled = self._pixmap.scaled(
                self._size - 4, self._size - 4,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(2, 2, scaled)
        else:
            # 이니셜 표시
            painter.setBrush(QColor(30, 40, 60))
            painter.drawEllipse(2, 2, self._size - 4, self._size - 4)
            painter.setPen(QColor(200, 210, 220))
            from PyQt6.QtGui import QFont
            font = QFont("Pretendard Variable", 12)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initial)

        painter.end()


class VisitorTimeline(QWidget):
    """오늘 방문자 타임라인 (스크롤 가능, 글래스 카드)"""

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 글래스 카드 프레임
        from PyQt6.QtWidgets import QFrame
        self._card = QFrame()
        self._card.setObjectName("glassCard")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 헤더 (토글 + 리셋 버튼)
        from PyQt6.QtWidgets import QFrame as _QFrame
        header_widget = _QFrame()
        header_widget.setStyleSheet("background: transparent; border: none;")
        header_row = QHBoxLayout(header_widget)
        header_row.setContentsMargins(8, 6, 8, 4)
        header_row.setSpacing(8)

        self._toggle_btn = QPushButton("  ▼  오늘 방문자")
        self._toggle_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #f1f5f9;
                font-size: 13px; font-weight: bold; text-align: left; padding: 4px 4px; }
            QPushButton:hover { color: #00A8FF; }
        """)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)
        header_row.addWidget(self._toggle_btn, 1)

        self._reset_btn = QPushButton("초기화")
        self._reset_btn.setObjectName("resetBtn")
        self._reset_btn.setFixedSize(64, 30)
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.setStyleSheet("""
            QPushButton#resetBtn {
                background: rgba(239,68,68,0.15);
                color: #f87171;
                border: 1px solid rgba(239,68,68,0.30);
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 0px 4px;
            }
            QPushButton#resetBtn:hover {
                background: rgba(239,68,68,0.25);
                color: #fca5a5;
            }
        """)
        self._reset_btn.clicked.connect(self._reset_today)
        header_row.addWidget(self._reset_btn)

        card_layout.addWidget(header_widget)

        # 스크롤 영역
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                width: 8px; background: rgba(255,255,255,0.06);
                border-radius: 4px; margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.25);
                border-radius: 3px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0,168,255,0.45);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0; background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(8, 0, 8, 8)
        self._container_layout.setSpacing(2)
        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        self._collapsed = False
        card_layout.addWidget(self._scroll, 1)

        # 펼침: stretch로 공간 채움 / 접힘: 헤더만 남도록
        self._card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        outer.addWidget(self._card, 1)

        # 빈 상태
        self._empty_label = QLabel("방문자가 없습니다")
        self._empty_label.setObjectName("emptyStateDesc")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._container_layout.insertWidget(0, self._empty_label)

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._scroll.setVisible(not self._collapsed)
        if self._collapsed:
            # 접힘: 헤더 높이만 차지
            h = 42
            self._card.setFixedHeight(h)
            self._card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            self.setFixedHeight(h)
        else:
            # 펼침: 남은 공간 채움
            self._card.setMaximumHeight(16777215)
            self._card.setMinimumHeight(0)
            self._card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            self.setMaximumHeight(16777215)
            self.setMinimumHeight(0)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._update_title()

    def _update_title(self):
        # 방문자 수 카운트 (stretch, empty_label 제외)
        count = 0
        for i in range(self._container_layout.count()):
            item = self._container_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), VisitorTimelineItem):
                count += 1
        arrow = "▶" if self._collapsed else "▼"
        suffix = f" ({count})" if count > 0 else ""
        self._toggle_btn.setText(f"  {arrow}  오늘 방문자{suffix}")

    def _reset_today(self):
        """오늘 방문 기록 초기화"""
        reply = QMessageBox.question(
            self, "오늘 방문자 초기화",
            "오늘 방문 기록을 모두 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        import database
        database.clear_today_visits()
        self.clear()
        # 감지 엔진 추적 캐시도 리셋 (안 하면 쿨다운 때문에 재인식 안 됨)
        main_win = self.window()
        if hasattr(main_win, '_detection_thread') and main_win._detection_thread:
            main_win._detection_thread.reset_tracking()
        if hasattr(main_win, 'camera_widget'):
            main_win.camera_widget._detections = []
        if hasattr(main_win, '_update_kpi'):
            main_win._update_kpi()
        from .toast_widget import ToastWidget
        ToastWidget.show_toast(main_win, "오늘 방문 기록 초기화됨", True)

    def add_visitor(self, time_str: str, name: str, thumbnail: QPixmap = None,
                    is_registered: bool = True, thumbnail_path: str = None):
        """방문자 추가 (최신이 위에)"""
        self._empty_label.hide()
        item = VisitorTimelineItem(time_str, name, thumbnail, is_registered, thumbnail_path)
        self._container_layout.insertWidget(
            self._container_layout.count() - 1, item
        )
        self._update_title()

    def clear(self):
        """타임라인 초기화"""
        while self._container_layout.count() > 1:  # stretch 유지
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._empty_label.show()
        self._update_title()

    def add_demo_data(self):
        """데모 데이터 추가"""
        demos = [
            ("15:32", "김철수", True),
            ("14:15", "미등록 방문자", False),
            ("13:02", "박영희", True),
            ("11:45", "이민수", True),
            ("10:30", "미등록 방문자", False),
            ("09:15", "최지영", True),
        ]
        for time_str, name, reg in demos:
            self.add_visitor(time_str, name, is_registered=reg)
