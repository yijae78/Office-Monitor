"""설정 다이얼로그 — config.yaml 편집 UI"""

import os
import yaml

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QFrame, QScrollArea, QWidget, QFileDialog,
)
from PyQt6.QtCore import Qt


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


class SettingsDialog(QDialog):
    """앱 설정 다이얼로그"""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setFixedSize(480, 560)
        self.setStyleSheet(self._style())
        self._config = config
        self._changed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목
        header = QWidget()
        header.setStyleSheet("background: rgba(255,255,255,0.03); padding: 16px;")
        hl = QHBoxLayout(header)
        title = QLabel("설정")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1f5f9; background: transparent;")
        hl.addWidget(title)
        hl.addStretch()
        layout.addWidget(header)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        self._form = QVBoxLayout(content)
        self._form.setContentsMargins(24, 16, 24, 16)
        self._form.setSpacing(16)

        # ── 카메라 ──
        self._add_section("카메라")
        cam = config.get("camera", {})
        self.cam_id = self._add_spin("카메라 ID", cam.get("id", 0), 0, 10)
        self.cam_w = self._add_spin("해상도 (가로)", cam.get("resolution", [1280, 720])[0], 320, 3840)
        self.cam_h = self._add_spin("해상도 (세로)", cam.get("resolution", [1280, 720])[1], 240, 2160)

        # ── 감지 ──
        self._add_section("얼굴 감지")
        det = config.get("detection", {})
        self.det_interval = self._add_spin("감지 간격 (ms)", det.get("interval_ms", 200), 50, 2000)
        self.det_score = self._add_double("감지 임계값", det.get("score_threshold", 0.35), 0.1, 1.0, 0.05)
        self.det_sim = self._add_double("유사도 임계값", det.get("similarity_threshold", 0.4), 0.1, 1.0, 0.05)
        self.det_cooldown = self._add_spin("쿨다운 (초)", det.get("cooldown_seconds", 300), 10, 3600)
        self.det_augment = self._add_check("자동 임베딩 보강", det.get("auto_augment_embeddings", True))

        # ── 녹화 ──
        self._add_section("녹화")
        rec = config.get("recording", {})
        self.rec_fps = self._add_spin("FPS", rec.get("fps", 15), 5, 60)
        self.rec_segment = self._add_spin("분할 단위 (분)", rec.get("segment_minutes", 30), 1, 120)
        self.rec_auto = self._add_check("자동 녹화 시작", rec.get("auto_start", True))

        # ── 저장 ──
        self._add_section("저장")
        stor = config.get("storage", {})
        self.stor_retention = self._add_spin("데이터 보존 (일)", stor.get("retention_days", 3), 1, 365)
        self.stor_cleanup = self._add_spin("정리 주기 (시간)", stor.get("cleanup_interval_hours", 1), 1, 24)

        # ── 데모 데이터 ──
        self._add_section("데모 모드")
        demo_row = QHBoxLayout()
        demo_desc = QLabel("샘플 데이터를 생성하여 각 기능을 미리 확인합니다")
        demo_desc.setStyleSheet("font-size: 12px; color: #64748b;")
        demo_desc.setWordWrap(True)
        demo_row.addWidget(demo_desc, 1)

        btn_demo = QPushButton("데모 생성")
        btn_demo.setFixedSize(100, 32)
        btn_demo.setStyleSheet("""
            QPushButton { background: rgba(34,197,94,0.12); color: #34d399;
                border: 1px solid rgba(34,197,94,0.25); border-radius: 8px;
                font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(34,197,94,0.22); }
        """)
        btn_demo.clicked.connect(self._generate_demo)
        demo_row.addWidget(btn_demo)

        btn_clear = QPushButton("데모 삭제")
        btn_clear.setFixedSize(100, 32)
        btn_clear.setStyleSheet("""
            QPushButton { background: rgba(239,68,68,0.10); color: #f87171;
                border: 1px solid rgba(239,68,68,0.25); border-radius: 8px;
                font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(239,68,68,0.20); }
        """)
        btn_clear.clicked.connect(self._clear_demo)
        demo_row.addWidget(btn_clear)

        self._form.addLayout(demo_row)

        self._form.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # 하단 버튼
        footer = QWidget()
        footer.setStyleSheet("background: rgba(255,255,255,0.03); padding: 12px 24px;")
        fl = QHBoxLayout(footer)
        fl.addStretch()

        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setFixedSize(80, 36)
        btn_cancel.clicked.connect(self.reject)
        fl.addWidget(btn_cancel)

        btn_save = QPushButton("저장")
        btn_save.setObjectName("btnSave")
        btn_save.setFixedSize(80, 36)
        btn_save.clicked.connect(self._save)
        fl.addWidget(btn_save)

        layout.addWidget(footer)

    def _add_section(self, title: str):
        lbl = QLabel(title)
        lbl.setStyleSheet("""
            font-size: 14px; font-weight: bold; color: #00A8FF;
            padding-top: 8px; padding-bottom: 4px;
            border-bottom: 1px solid rgba(0,168,255,0.2);
        """)
        self._form.addWidget(lbl)

    def _add_spin(self, label: str, value: int, min_v: int, max_v: int) -> QSpinBox:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 13px; color: #94a3b8; min-width: 160px;")
        row.addWidget(lbl)
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(value)
        spin.setFixedWidth(120)
        row.addWidget(spin)
        row.addStretch()
        self._form.addLayout(row)
        return spin

    def _add_double(self, label: str, value: float, min_v: float, max_v: float, step: float) -> QDoubleSpinBox:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 13px; color: #94a3b8; min-width: 160px;")
        row.addWidget(lbl)
        spin = QDoubleSpinBox()
        spin.setRange(min_v, max_v)
        spin.setSingleStep(step)
        spin.setDecimals(2)
        spin.setValue(value)
        spin.setFixedWidth(120)
        row.addWidget(spin)
        row.addStretch()
        self._form.addLayout(row)
        return spin

    def _add_check(self, label: str, checked: bool) -> QCheckBox:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 13px; color: #94a3b8; min-width: 160px;")
        row.addWidget(lbl)
        cb = QCheckBox()
        cb.setChecked(checked)
        row.addWidget(cb)
        row.addStretch()
        self._form.addLayout(row)
        return cb

    def _generate_demo(self):
        from demo_data import generate_demo_data
        result = generate_demo_data()
        from PyQt6.QtWidgets import QMessageBox
        if result:
            QMessageBox.information(self, "데모 데이터", "데모 데이터가 생성되었습니다.\n방문자관리, 통계 탭에서 확인하세요.")
        else:
            QMessageBox.information(self, "데모 데이터", "이미 데이터가 존재합니다.")
        self._changed = True

    def _clear_demo(self):
        from demo_data import clear_demo_data
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "데모 삭제", "모든 데모 데이터를 삭제하시겠습니까?\n(실제 데이터도 함께 삭제됩니다)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            clear_demo_data()
            QMessageBox.information(self, "완료", "데이터가 삭제되었습니다.")
            self._changed = True

    def _save(self):
        """UI 값 → config dict → config.yaml 저장"""
        self._config["camera"]["id"] = self.cam_id.value()
        self._config["camera"]["resolution"] = [self.cam_w.value(), self.cam_h.value()]

        det = self._config.setdefault("detection", {})
        det["interval_ms"] = self.det_interval.value()
        det["score_threshold"] = round(self.det_score.value(), 2)
        det["similarity_threshold"] = round(self.det_sim.value(), 2)
        det["cooldown_seconds"] = self.det_cooldown.value()
        det["auto_augment_embeddings"] = self.det_augment.isChecked()

        rec = self._config.setdefault("recording", {})
        rec["fps"] = self.rec_fps.value()
        rec["segment_minutes"] = self.rec_segment.value()
        rec["auto_start"] = self.rec_auto.isChecked()

        stor = self._config.setdefault("storage", {})
        stor["retention_days"] = self.stor_retention.value()
        stor["cleanup_interval_hours"] = self.stor_cleanup.value()

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

        self._changed = True
        self.accept()

    @property
    def changed(self) -> bool:
        return self._changed

    @staticmethod
    def _style() -> str:
        return """
        QDialog { background: #0c111b; }
        QWidget { background: transparent; color: #f1f5f9; }
        QScrollArea { background: #0c111b; border: none; }
        QLabel { background: transparent; }
        QSpinBox, QDoubleSpinBox {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 8px; padding: 6px 10px;
            color: #f1f5f9; font-size: 13px;
        }
        QSpinBox:focus, QDoubleSpinBox:focus { border-color: #00A8FF; }
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            width: 20px; border: none;
            background: rgba(255,255,255,0.04);
        }
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            image: none; border: none;
            border-left: 4px solid transparent; border-right: 4px solid transparent;
            border-bottom: 5px solid #94a3b8;
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            image: none; border: none;
            border-left: 4px solid transparent; border-right: 4px solid transparent;
            border-top: 5px solid #94a3b8;
        }
        QCheckBox { background: transparent; }
        QCheckBox::indicator {
            width: 18px; height: 18px; border-radius: 4px;
            border: 2px solid rgba(255,255,255,0.15);
            background: rgba(255,255,255,0.04);
        }
        QCheckBox::indicator:checked {
            background: #00A8FF; border-color: #00A8FF;
        }
        QPushButton#btnSave {
            background: rgba(0,168,255,0.15); color: #00A8FF;
            border: 1px solid rgba(0,168,255,0.3); border-radius: 10px;
            font-size: 13px; font-weight: bold;
        }
        QPushButton#btnSave:hover { background: rgba(0,168,255,0.25); }
        QPushButton#btnCancel {
            background: rgba(255,255,255,0.06); color: #94a3b8;
            border: 1px solid rgba(255,255,255,0.10); border-radius: 10px;
            font-size: 13px;
        }
        QPushButton#btnCancel:hover { background: rgba(255,255,255,0.10); color: #f1f5f9; }
        """
