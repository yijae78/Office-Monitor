"""방문자 관리 뷰 — 등록된 얼굴 갤러리 + 추가/삭제"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QFileDialog, QInputDialog,
    QSizePolicy, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont

import database
from .flow_layout import FlowLayout
from .design_tokens import Q_CYAN, Q_TEXT_SECONDARY


class FaceCard(QFrame):
    """개별 얼굴 카드"""

    def __init__(self, visitor_id: int, name: str, parent_view, parent=None):
        super().__init__(parent)
        self.visitor_id = visitor_id
        self._parent_view = parent_view
        self.setObjectName("glassCard")
        self.setFixedSize(150, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 아바타
        avatar = QLabel("👤")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("font-size: 48px; color: rgba(255,255,255,0.3);")
        layout.addWidget(avatar)

        # 이름
        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #f1f5f9;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # 삭제 버튼
        btn_del = QPushButton("삭제")
        btn_del.setFixedHeight(28)
        btn_del.setStyleSheet("""
            QPushButton { background: rgba(239,68,68,0.10); color: #f87171;
                border: 1px solid rgba(239,68,68,0.25); border-radius: 6px;
                font-size: 11px; font-weight: bold; padding: 2px 8px; }
            QPushButton:hover { background: rgba(239,68,68,0.20); }
        """)
        btn_del.clicked.connect(self._delete)
        layout.addWidget(btn_del)

    def _delete(self):
        reply = QMessageBox.question(
            self, "삭제 확인", f"이 얼굴을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_visitor(self.visitor_id)
            self._parent_view.refresh()


class VisitorManagerView(QWidget):
    """방문자 관리 탭"""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main_window = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # 헤더
        header = QHBoxLayout()
        title = QLabel("등록된 얼굴")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1f5f9;")
        header.addWidget(title)
        header.addStretch()

        self.btn_add = QPushButton("+ 이미지에서 등록")
        self.btn_add.clicked.connect(self._add_from_image)
        header.addWidget(self.btn_add)

        layout.addLayout(header)

        # 검색
        self.search = QLineEdit()
        self.search.setPlaceholderText("이름 검색...")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        # 갤러리 (FlowLayout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._gallery = QWidget()
        self._gallery_layout = FlowLayout(self._gallery, h_spacing=12, v_spacing=12)
        scroll.setWidget(self._gallery)
        layout.addWidget(scroll, 1)

        # 빈 상태
        self._empty = QLabel("등록된 얼굴이 없습니다\n카메라에서 '👤 얼굴등록' 버튼으로 등록하세요")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("font-size: 14px; color: #64748b; padding: 60px;")
        layout.addWidget(self._empty)

        self.refresh()

    def refresh(self):
        # 기존 카드 제거
        while self._gallery_layout.count():
            item = self._gallery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        visitors = database.get_all_visitors()
        self._empty.setVisible(len(visitors) == 0)
        self._gallery.setVisible(len(visitors) > 0)

        for v in visitors:
            card = FaceCard(v["id"], v["name"], self)
            self._gallery_layout.addWidget(card)

    def _filter(self, text: str):
        for i in range(self._gallery_layout.count()):
            item = self._gallery_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                visible = text.lower() in card.findChild(QLabel).text().lower() if text else True
                card.setVisible(visible)

    def _add_from_image(self):
        """이미지 파일에서 얼굴 등록"""
        path, _ = QFileDialog.getOpenFileName(self, "얼굴 이미지 선택", "", "Images (*.jpg *.jpeg *.png *.bmp)")
        if not path:
            return

        name, ok = QInputDialog.getText(self, "얼굴 등록", "이름을 입력하세요:")
        if not ok or not name.strip():
            return

        import cv2
        img = cv2.imread(path)
        if img is None:
            QMessageBox.warning(self, "오류", "이미지를 읽을 수 없습니다")
            return

        det = self._main_window._detection_thread
        if det and det._app:
            faces = det._app.get(img)
            if not faces:
                QMessageBox.warning(self, "오류", "이미지에서 얼굴을 찾을 수 없습니다")
                return
            det.register_face(name.strip(), faces[0].embedding)
            self.refresh()
            QMessageBox.information(self, "완료", f"'{name.strip()}' 등록 완료")
        else:
            QMessageBox.warning(self, "오류", "감지 엔진이 준비되지 않았습니다")
