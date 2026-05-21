"""신규 방문자 등록 다이얼로그 — 얼굴 사진 + 이름 입력"""

import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap


class NewFaceDialog(QDialog):
    """미등록 얼굴 감지 시 표시되는 등록 요청 다이얼로그"""

    def __init__(self, face_crop: np.ndarray, parent=None):
        super().__init__(parent)
        self.setWindowTitle("새로운 방문자 감지")
        self.setFixedSize(360, 320)
        self.setStyleSheet(self._dialog_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 제목
        title = QLabel("새로운 방문자가 감지되었습니다")
        title.setObjectName("dialogTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("이 방문자를 등록하시겠습니까?")
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # 얼굴 이미지
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(120, 120)
        img_label.setStyleSheet("""
            border: 2px solid rgba(0,168,255,0.4);
            border-radius: 60px;
            background: rgba(0,0,0,0.3);
        """)

        if face_crop is not None and face_crop.size > 0:
            rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(
                116, 116,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            img_label.setPixmap(pixmap)

        img_container = QHBoxLayout()
        img_container.addStretch()
        img_container.addWidget(img_label)
        img_container.addStretch()
        layout.addLayout(img_container)

        # 이름 입력
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("이름을 입력하세요...")
        self._name_input.setMinimumHeight(40)
        layout.addWidget(self._name_input)

        # 버튼
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_ignore = QPushButton("무시")
        btn_ignore.setObjectName("btnIgnore")
        btn_ignore.setMinimumHeight(40)
        btn_ignore.clicked.connect(self.reject)
        btn_row.addWidget(btn_ignore)

        btn_register = QPushButton("등록")
        btn_register.setObjectName("btnRegister")
        btn_register.setMinimumHeight(40)
        btn_register.clicked.connect(self._on_register)
        btn_row.addWidget(btn_register)

        layout.addLayout(btn_row)

        # Enter 키로 등록
        self._name_input.returnPressed.connect(self._on_register)

    def _on_register(self):
        if self._name_input.text().strip():
            self.accept()

    def get_name(self) -> str:
        return self._name_input.text().strip()

    @staticmethod
    def _dialog_style() -> str:
        return """
        QDialog {
            background: #111827;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 20px;
        }
        QLabel#dialogTitle {
            font-size: 16px;
            font-weight: bold;
            color: #f1f5f9;
        }
        QLabel#dialogSubtitle {
            font-size: 13px;
            color: #94a3b8;
        }
        QLineEdit {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 14px;
            color: #f1f5f9;
        }
        QLineEdit:focus {
            border-color: #00A8FF;
        }
        QLineEdit::placeholder {
            color: #64748b;
        }
        QPushButton#btnRegister {
            background: rgba(0,168,255,0.15);
            color: #00A8FF;
            border: 1px solid rgba(0,168,255,0.3);
            border-radius: 10px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton#btnRegister:hover {
            background: rgba(0,168,255,0.25);
        }
        QPushButton#btnIgnore {
            background: rgba(255,255,255,0.04);
            color: #94a3b8;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            font-size: 14px;
        }
        QPushButton#btnIgnore:hover {
            background: rgba(255,255,255,0.08);
            color: #f1f5f9;
        }
        """
