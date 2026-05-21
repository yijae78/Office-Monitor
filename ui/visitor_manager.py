"""방문자 관리 뷰 — 자동 캡처 + 등록 + 휴지통 통합"""

import os
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QInputDialog, QFileDialog,
    QSizePolicy, QMessageBox, QStackedWidget, QCheckBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage

import database
from .flow_layout import FlowLayout


# ═══════════════════════════════════════
# 카드 위젯들
# ═══════════════════════════════════════

class PendingFaceCard(QFrame):
    """미등록 캡처 카드 — 자동 캡처된 얼굴"""

    def __init__(self, face_data: dict, parent_view, parent=None):
        super().__init__(parent)
        self.face_id = face_data["id"]
        self.face_data = face_data
        self._parent_view = parent_view
        self.setObjectName("glassCard")
        self.setFixedSize(160, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 얼굴 이미지
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(144, 120)
        img_label.setStyleSheet("""
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            background: rgba(0,0,0,0.3);
        """)

        img_path = face_data["image_path"]
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path).scaled(
                140, 116,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            img_label.setPixmap(pixmap)
        else:
            img_label.setText("?")
            img_label.setStyleSheet(img_label.styleSheet() + "font-size: 36px; color: #64748b;")

        layout.addWidget(img_label)

        # 캡처 시간
        time_str = face_data["captured_at"][11:16] if face_data["captured_at"] else ""
        date_str = face_data["captured_at"][:10] if face_data["captured_at"] else ""
        time_label = QLabel(f"{date_str}  {time_str}")
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label.setStyleSheet("font-size: 10px; color: #64748b;")
        layout.addWidget(time_label)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_register = QPushButton("등록")
        btn_register.setFixedHeight(30)
        btn_register.setStyleSheet("""
            QPushButton { background: rgba(0,168,255,0.12); color: #00A8FF;
                border: 1px solid rgba(0,168,255,0.25); border-radius: 6px;
                font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,168,255,0.22); }
        """)
        btn_register.clicked.connect(self._register)
        btn_row.addWidget(btn_register)

        btn_delete = QPushButton("삭제")
        btn_delete.setFixedHeight(30)
        btn_delete.setStyleSheet("""
            QPushButton { background: rgba(239,68,68,0.10); color: #f87171;
                border: 1px solid rgba(239,68,68,0.25); border-radius: 6px;
                font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(239,68,68,0.20); }
        """)
        btn_delete.clicked.connect(self._delete)
        btn_row.addWidget(btn_delete)

        layout.addLayout(btn_row)

    def _register(self):
        name, ok = QInputDialog.getText(self, "방문자 등록", "이름을 입력하세요:")
        if not ok or not name.strip():
            return

        # 임베딩 복원 → 등록
        emb = np.frombuffer(self.face_data["embedding"], dtype=np.float32).copy()
        det = self._parent_view._main_window._detection_thread
        if det:
            det.register_face(name.strip(), emb)
            database.remove_pending_face(self.face_id)
            self._parent_view.refresh()
            from .toast_widget import ToastWidget
            ToastWidget.show_toast(self._parent_view.window(), f"'{name.strip()}' 등록 완료", True)

    def _delete(self):
        database.soft_delete_pending_face(self.face_id)
        self._parent_view.refresh()


class DeletedFaceCard(QFrame):
    """휴지통 카드 — 체크박스 선택 + 복구/삭제"""

    def __init__(self, face_data: dict, parent_view, parent=None):
        super().__init__(parent)
        self.face_id = face_data["id"]
        self.face_data = face_data
        self._parent_view = parent_view
        self.setObjectName("glassCard")
        self.setFixedSize(160, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        # 체크박스 (선택 삭제용)
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px;
                border: 2px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.04); }
            QCheckBox::indicator:checked { background: #ef4444; border-color: #ef4444; }
        """)
        layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignRight)

        # 얼굴 이미지
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(144, 120)
        img_label.setStyleSheet("""
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 10px;
            background: rgba(0,0,0,0.3);
        """)

        img_path = face_data["image_path"]
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path).scaled(
                140, 116,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            img_label.setPixmap(pixmap)

        layout.addWidget(img_label)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_restore = QPushButton("복구")
        btn_restore.setFixedHeight(28)
        btn_restore.setStyleSheet("""
            QPushButton { background: rgba(34,197,94,0.10); color: #34d399;
                border: 1px solid rgba(34,197,94,0.25); border-radius: 6px;
                font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(34,197,94,0.20); }
        """)
        btn_restore.clicked.connect(self._restore)
        btn_row.addWidget(btn_restore)

        btn_hard = QPushButton("삭제")
        btn_hard.setFixedHeight(28)
        btn_hard.setStyleSheet("""
            QPushButton { background: rgba(239,68,68,0.10); color: #f87171;
                border: 1px solid rgba(239,68,68,0.25); border-radius: 6px;
                font-size: 12px; }
            QPushButton:hover { background: rgba(239,68,68,0.20); }
        """)
        btn_hard.clicked.connect(self._hard_delete)
        btn_row.addWidget(btn_hard)

        layout.addLayout(btn_row)

    def _restore(self):
        database.restore_pending_face(self.face_id)
        self._parent_view.refresh()

    def _hard_delete(self):
        face = database.get_pending_face(self.face_id)
        if face and os.path.exists(face["image_path"]):
            os.remove(face["image_path"])
        database.hard_delete_pending_face(self.face_id)
        self._parent_view.refresh()


class RegisteredCard(QFrame):
    """등록된 방문자 카드"""

    def __init__(self, visitor_id: int, name: str, thumb_path: str, emb_count: int, parent_view, parent=None):
        super().__init__(parent)
        self.visitor_id = visitor_id
        self.visitor_name = name
        self._parent_view = parent_view
        self.setObjectName("glassCard")
        self.setFixedSize(160, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 썸네일 또는 기본 아이콘
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(144, 120)
        img_label.setStyleSheet("""
            border: 1px solid rgba(0,168,255,0.15);
            border-radius: 10px;
            background: rgba(0,0,0,0.3);
        """)

        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path).scaled(
                140, 116,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            img_label.setPixmap(pixmap)
        else:
            img_label.setText("👤")
            img_label.setStyleSheet(img_label.styleSheet() + "font-size: 42px; color: rgba(255,255,255,0.2);")

        layout.addWidget(img_label)

        # 이름
        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #f1f5f9;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # 임베딩 수 뱃지
        info = QLabel(f"임베딩 {emb_count}개")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("font-size: 10px; color: #64748b;")
        layout.addWidget(info)

        # 버튼 행
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(6)

        btn_edit = QPushButton("편집")
        btn_edit.setFixedHeight(28)
        btn_edit.setStyleSheet("""
            QPushButton { background: rgba(59,130,246,0.10); color: #60a5fa;
                border: 1px solid rgba(59,130,246,0.25); border-radius: 6px;
                font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(59,130,246,0.20); }
        """)
        btn_edit.clicked.connect(self._edit)
        btn_row2.addWidget(btn_edit)

        btn_del = QPushButton("삭제")
        btn_del.setFixedHeight(28)
        btn_del.setStyleSheet("""
            QPushButton { background: rgba(239,68,68,0.10); color: #f87171;
                border: 1px solid rgba(239,68,68,0.25); border-radius: 6px;
                font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(239,68,68,0.20); }
        """)
        btn_del.clicked.connect(self._delete)
        btn_row2.addWidget(btn_del)

        layout.addLayout(btn_row2)

    def _edit(self):
        name, ok = QInputDialog.getText(
            self, "이름 편집", "새 이름을 입력하세요:", text=self.visitor_name)
        if ok and name.strip() and name.strip() != self.visitor_name:
            database.update_visitor_name(self.visitor_id, name.strip())
            det = self._parent_view._main_window._detection_thread
            if det:
                det.reload_known_faces()
            self._parent_view.refresh()

    def _delete(self):
        reply = QMessageBox.question(
            self, "삭제 확인", f"'{self.visitor_name}' 방문자를 삭제하시겠습니까?\n(모든 임베딩이 함께 삭제됩니다)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_visitor(self.visitor_id)
            det = self._parent_view._main_window._detection_thread
            if det:
                det.reload_known_faces()
            self._parent_view.refresh()


# ═══════════════════════════════════════
# 메인 뷰
# ═══════════════════════════════════════

class VisitorManagerView(QWidget):
    """방문자 관리 탭 — 미등록 캡처 / 등록된 방문자 / 휴지통"""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main_window = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # ── 상단 탭 (세그먼트 컨트롤) ──
        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(0)

        self._tab_btns = []
        tab_names = ["미등록 캡처", "등록된 방문자", "휴지통"]
        tab_group = QWidget()
        tab_group.setStyleSheet("""
            QWidget { background: rgba(255,255,255,0.04); border-radius: 10px; }
        """)
        tab_layout = QHBoxLayout(tab_group)
        tab_layout.setContentsMargins(3, 3, 3, 3)
        tab_layout.setSpacing(2)

        for i, name in enumerate(tab_names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet(self._tab_style())
            btn.clicked.connect(lambda checked, idx=i: self._switch_tab(idx))
            tab_layout.addWidget(btn)
            self._tab_btns.append(btn)

        self._tab_btns[0].setChecked(True)
        tab_bar.addWidget(tab_group)
        tab_bar.addStretch()

        # 이미지에서 등록 (fallback)
        btn_add_file = QPushButton("+ 이미지에서 등록")
        btn_add_file.setStyleSheet("""
            QPushButton { background: rgba(59,130,246,0.10); color: #60a5fa;
                border: 1px solid rgba(59,130,246,0.25); border-radius: 10px;
                padding: 6px 16px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(59,130,246,0.18); }
        """)
        btn_add_file.clicked.connect(self._add_from_image)
        tab_bar.addWidget(btn_add_file)

        layout.addLayout(tab_bar)

        # 검색
        self.search = QLineEdit()
        self.search.setPlaceholderText("이름 검색...")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        # ── 스택 (3개 탭) ──
        self._stack = QStackedWidget()

        # 탭 0: 미등록 캡처
        self._pending_scroll, self._pending_gallery, self._pending_layout = self._make_gallery()
        self._pending_empty = self._make_empty_label(
            "자동 캡처된 얼굴이 없습니다\n카메라가 미등록 얼굴을 감지하면 자동으로 캡처됩니다")
        pending_page = QWidget()
        pl = QVBoxLayout(pending_page)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.addWidget(self._pending_empty)
        pl.addWidget(self._pending_scroll, 1)
        self._stack.addWidget(pending_page)

        # 탭 1: 등록된 방문자
        self._reg_scroll, self._reg_gallery, self._reg_layout = self._make_gallery()
        self._reg_empty = self._make_empty_label("등록된 방문자가 없습니다")
        reg_page = QWidget()
        rl = QVBoxLayout(reg_page)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(self._reg_empty)
        rl.addWidget(self._reg_scroll, 1)
        self._stack.addWidget(reg_page)

        # 탭 2: 휴지통
        self._trash_scroll, self._trash_gallery, self._trash_layout = self._make_gallery()
        self._trash_empty = self._make_empty_label("휴지통이 비어있습니다")
        trash_page = QWidget()
        tl = QVBoxLayout(trash_page)
        tl.setContentsMargins(0, 0, 0, 0)

        # 휴지통 액션 바
        trash_header = QHBoxLayout()
        trash_header.setSpacing(8)

        self._btn_select_all = QPushButton("전체선택")
        self._btn_select_all.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.04); color: #94a3b8;
                border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
                padding: 6px 12px; font-size: 12px; }
            QPushButton:hover { background: rgba(255,255,255,0.08); color: #f1f5f9; }
        """)
        self._btn_select_all.clicked.connect(self._toggle_select_all)
        trash_header.addWidget(self._btn_select_all)

        self._btn_delete_selected = QPushButton("선택 삭제")
        self._btn_delete_selected.setStyleSheet("""
            QPushButton { background: rgba(239,68,68,0.10); color: #f87171;
                border: 1px solid rgba(239,68,68,0.25); border-radius: 8px;
                padding: 6px 12px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(239,68,68,0.22); }
        """)
        self._btn_delete_selected.clicked.connect(self._delete_selected)
        trash_header.addWidget(self._btn_delete_selected)

        trash_header.addStretch()

        self._btn_empty_trash = QPushButton("전체 비우기")
        self._btn_empty_trash.setStyleSheet("""
            QPushButton { background: rgba(239,68,68,0.15); color: #f87171;
                border: 1px solid rgba(239,68,68,0.30); border-radius: 8px;
                padding: 6px 16px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(239,68,68,0.25); }
        """)
        self._btn_empty_trash.clicked.connect(self._empty_trash)
        trash_header.addWidget(self._btn_empty_trash)

        tl.addLayout(trash_header)

        tl.addWidget(self._trash_empty)
        tl.addWidget(self._trash_scroll, 1)
        self._stack.addWidget(trash_page)

        layout.addWidget(self._stack, 1)

        self.refresh()

    def _make_gallery(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        gallery = QWidget()
        flow = FlowLayout(gallery, h_spacing=12, v_spacing=12)
        scroll.setWidget(gallery)
        return scroll, gallery, flow

    def _make_empty_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 14px; color: #64748b; padding: 60px;")
        return lbl

    def _tab_style(self) -> str:
        return """
            QPushButton {
                background: transparent; color: #64748b; border: none;
                border-radius: 8px; padding: 6px 16px;
                font-size: 13px; font-weight: bold; min-width: 60px;
            }
            QPushButton:hover { color: #94a3b8; background: rgba(255,255,255,0.04); }
            QPushButton:checked { background: rgba(255,255,255,0.09); color: #00A8FF; }
        """

    def _switch_tab(self, idx: int):
        for i, btn in enumerate(self._tab_btns):
            btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)

    def refresh(self):
        """3개 탭 모두 갱신"""
        self._refresh_pending()
        self._refresh_registered()
        self._refresh_trash()

        # 미등록 캡처 수 뱃지
        pending_count = len(database.get_pending_faces("pending") or [])
        if pending_count > 0:
            self._tab_btns[0].setText(f"미등록 캡처 ({pending_count})")
        else:
            self._tab_btns[0].setText("미등록 캡처")

        trash_count = len(database.get_pending_faces("deleted") or [])
        if trash_count > 0:
            self._tab_btns[2].setText(f"휴지통 ({trash_count})")
        else:
            self._tab_btns[2].setText("휴지통")

    def _clear_layout(self, flow_layout):
        while flow_layout.count():
            item = flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _refresh_pending(self):
        self._clear_layout(self._pending_layout)
        faces = database.get_pending_faces("pending") or []
        self._pending_empty.setVisible(len(faces) == 0)
        self._pending_scroll.setVisible(len(faces) > 0)
        for f in faces:
            card = PendingFaceCard(dict(f), self)
            self._pending_layout.addWidget(card)

    def _refresh_registered(self):
        self._clear_layout(self._reg_layout)
        visitors = database.get_all_visitors() or []
        self._reg_empty.setVisible(len(visitors) == 0)
        self._reg_scroll.setVisible(len(visitors) > 0)

        for v in visitors:
            vid = v["id"]
            # 최신 썸네일 가져오기
            thumb = database.execute(
                "SELECT thumbnail_path FROM visit_logs WHERE visitor_id=? AND thumbnail_path IS NOT NULL ORDER BY timestamp DESC LIMIT 1",
                (vid,), fetch="one")
            thumb_path = thumb["thumbnail_path"] if thumb else None

            # 임베딩 수
            embs = database.get_embeddings_for_visitor(vid) or []
            card = RegisteredCard(vid, v["name"], thumb_path, len(embs), self)
            self._reg_layout.addWidget(card)

    def _refresh_trash(self):
        self._clear_layout(self._trash_layout)
        faces = database.get_pending_faces("deleted") or []
        has_items = len(faces) > 0
        self._trash_empty.setVisible(not has_items)
        self._trash_scroll.setVisible(has_items)
        self._btn_empty_trash.setVisible(has_items)
        self._btn_select_all.setVisible(has_items)
        self._btn_delete_selected.setVisible(has_items)
        if has_items:
            self._btn_select_all.setText("전체선택")
        for f in faces:
            card = DeletedFaceCard(dict(f), self)
            self._trash_layout.addWidget(card)

    def _toggle_select_all(self):
        """휴지통 전체선택 토글"""
        # 현재 체크 상태 파악
        cards = self._get_trash_cards()
        all_checked = all(c.checkbox.isChecked() for c in cards) if cards else False
        for card in cards:
            card.checkbox.setChecked(not all_checked)
        self._btn_select_all.setText("선택해제" if not all_checked else "전체선택")

    def _delete_selected(self):
        """선택된 휴지통 항목만 완전삭제"""
        cards = [c for c in self._get_trash_cards() if c.checkbox.isChecked()]
        if not cards:
            return
        reply = QMessageBox.question(
            self, "선택 삭제",
            f"선택한 {len(cards)}개 항목을 완전 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for card in cards:
            face = database.get_pending_face(card.face_id)
            if face and os.path.exists(face["image_path"]):
                os.remove(face["image_path"])
            database.hard_delete_pending_face(card.face_id)
        self.refresh()
        from .toast_widget import ToastWidget
        ToastWidget.show_toast(self.window(), f"{len(cards)}개 완전 삭제됨", True)

    def _get_trash_cards(self) -> list:
        """휴지통 카드 목록 반환"""
        cards = []
        for i in range(self._trash_layout.count()):
            item = self._trash_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), DeletedFaceCard):
                cards.append(item.widget())
        return cards

    def _empty_trash(self):
        """휴지통 전체 비우기 — 완전삭제"""
        faces = database.get_pending_faces("deleted") or []
        if not faces:
            return
        reply = QMessageBox.question(
            self, "휴지통 비우기",
            f"휴지통의 {len(faces)}개 항목을 완전 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for f in faces:
            img_path = f["image_path"]
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
            database.hard_delete_pending_face(f["id"])
        self.refresh()
        from .toast_widget import ToastWidget
        ToastWidget.show_toast(self.window(), f"휴지통 {len(faces)}개 완전 삭제됨", True)

    def _filter(self, text: str):
        """현재 탭에서 검색 (등록된 방문자만)"""
        if self._stack.currentIndex() != 1:
            return
        for i in range(self._reg_layout.count()):
            item = self._reg_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if hasattr(card, 'visitor_name'):
                    card.setVisible(text.lower() in card.visitor_name.lower() if text else True)

    def _add_from_image(self):
        """이미지 파일에서 얼굴 등록"""
        path, _ = QFileDialog.getOpenFileName(
            self, "얼굴 이미지 선택", "", "Images (*.jpg *.jpeg *.png *.bmp)")
        if not path:
            return

        name, ok = QInputDialog.getText(self, "방문자 등록", "이름을 입력하세요:")
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
            from .toast_widget import ToastWidget
            ToastWidget.show_toast(self.window(), f"'{name.strip()}' 등록 완료", True)
        else:
            QMessageBox.warning(self, "오류", "감지 엔진이 준비되지 않았습니다")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
