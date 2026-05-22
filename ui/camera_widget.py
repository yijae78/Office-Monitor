"""리사이즈/확대축소 가능한 카메라 뷰어 위젯"""

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QPen, QBrush, QCursor


class CameraWidget(QWidget):
    """카메라 영상을 표시하는 위젯. 확대/축소, 자유 리사이즈, 영역 캡처 지원."""

    region_captured = pyqtSignal(np.ndarray)  # 영역 캡처 완료 시그널

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._frame = None
        self._detections = []
        self._status_text = "카메라 연결 대기 중..."
        self._status_ok = False

        # 영역 선택 상태
        self._selecting = False       # 영역 선택 모드 여부
        self._sel_start = QPoint()    # 드래그 시작점
        self._sel_end = QPoint()      # 드래그 끝점
        self._sel_dragging = False    # 드래그 진행 중

        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    def update_frame(self, frame: np.ndarray, detections: list = None):
        """새 프레임 + 감지 결과 업데이트. detections=None이면 이전 결과 유지."""
        self._frame = frame
        if detections is not None:
            self._detections = detections
        self._status_ok = True
        self._status_text = ""
        self.update()

    def set_status(self, text: str, ok: bool = False):
        """상태 텍스트 설정 (카메라 미연결 등)"""
        self._status_text = text
        self._status_ok = ok
        self.update()

    def set_zoom(self, factor: float):
        self._zoom = max(0.5, min(3.0, factor))
        self.update()

    def wheelEvent(self, event):
        """Ctrl+휠로 확대/축소"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y() / 600.0
            self.set_zoom(self._zoom + delta)
            event.accept()
        else:
            super().wheelEvent(event)

    def zoom_in(self):
        self.set_zoom(self._zoom + 0.25)

    def zoom_out(self):
        self.set_zoom(self._zoom - 0.25)

    def zoom_reset(self):
        self.set_zoom(1.0)

    # ── 영역 캡처 ──

    def start_region_select(self):
        """영역 선택 모드 시작"""
        self._selecting = True
        self._sel_dragging = False
        self._sel_start = QPoint()
        self._sel_end = QPoint()
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.update()

    def cancel_region_select(self):
        """영역 선택 모드 취소"""
        self._selecting = False
        self._sel_dragging = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.update()

    def _get_frame_rect(self):
        """현재 위젯에서 프레임이 그려지는 영역 반환"""
        if self._frame is None:
            return QRect()
        h, w, ch = self._frame.shape
        if self._zoom > 1.0:
            fw = int(w / self._zoom)
            fh = int(h / self._zoom)
        else:
            fw, fh = w, h
        pixmap_size = QSize(fw, fh).scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        x = (self.width() - pixmap_size.width()) // 2
        y = (self.height() - pixmap_size.height()) // 2
        return QRect(x, y, pixmap_size.width(), pixmap_size.height())

    def _widget_to_frame(self, pt: QPoint):
        """위젯 좌표 → 원본 프레임 좌표 변환"""
        if self._frame is None:
            return (0, 0)
        h, w, ch = self._frame.shape
        fr = self._get_frame_rect()
        if fr.width() == 0 or fr.height() == 0:
            return (0, 0)

        # 줌 크롭 영역
        if self._zoom > 1.0:
            crop_w = int(w / self._zoom)
            crop_h = int(h / self._zoom)
            ox = (w - crop_w) // 2
            oy = (h - crop_h) // 2
        else:
            crop_w, crop_h = w, h
            ox, oy = 0, 0

        # 위젯 → 크롭 프레임 좌표
        fx = int((pt.x() - fr.x()) / fr.width() * crop_w) + ox
        fy = int((pt.y() - fr.y()) / fr.height() * crop_h) + oy
        fx = max(0, min(w, fx))
        fy = max(0, min(h, fy))
        return (fx, fy)

    def mousePressEvent(self, event):
        if self._selecting and event.button() == Qt.MouseButton.LeftButton:
            self._sel_start = event.pos()
            self._sel_end = event.pos()
            self._sel_dragging = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._sel_dragging:
            self._sel_end = event.pos()
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._sel_dragging and event.button() == Qt.MouseButton.LeftButton:
            self._sel_end = event.pos()
            self._sel_dragging = False
            self._selecting = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

            # 선택 영역 → 프레임 좌표
            x1, y1 = self._widget_to_frame(self._sel_start)
            x2, y2 = self._widget_to_frame(self._sel_end)
            left, right = min(x1, x2), max(x1, x2)
            top, bottom = min(y1, y2), max(y1, y2)

            if right - left > 5 and bottom - top > 5 and self._frame is not None:
                cropped = self._frame[top:bottom, left:right].copy()
                self.region_captured.emit(cropped)
            else:
                # 너무 작으면 전체 프레임 캡처
                if self._frame is not None:
                    self.region_captured.emit(self._frame.copy())

            self._sel_start = QPoint()
            self._sel_end = QPoint()
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self._selecting and event.key() == Qt.Key.Key_Escape:
            self.cancel_region_select()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 배경
        painter.fillRect(self.rect(), QColor(10, 10, 10))

        if self._frame is not None:
            self._paint_frame(painter)
        else:
            self._paint_placeholder(painter)

        # 영역 선택 오버레이
        if self._selecting or self._sel_dragging:
            self._paint_selection_overlay(painter)

        painter.end()

    def _paint_selection_overlay(self, painter: QPainter):
        """영역 선택 모드 오버레이"""
        # 반투명 어둡게
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._sel_dragging and not self._sel_start.isNull() and not self._sel_end.isNull():
            # 선택 영역
            sel = QRect(self._sel_start, self._sel_end).normalized()

            # 선택 영역은 밝게 (어둠 제거)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(sel, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # 다시 프레임 그리기 (선택 영역만)
            if self._frame is not None:
                painter.save()
                painter.setClipRect(sel)
                self._paint_frame(painter)
                painter.restore()

            # 선택 영역 테두리
            pen = QPen(QColor(0, 168, 255), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(sel)

            # 크기 표시
            x1, y1 = self._widget_to_frame(self._sel_start)
            x2, y2 = self._widget_to_frame(self._sel_end)
            pw = abs(x2 - x1)
            ph = abs(y2 - y1)
            size_text = f"{pw}×{ph}"
            font = QFont("Pretendard Variable", 10)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(0, 168, 255))
            painter.drawText(sel.x() + 4, sel.y() - 6, size_text)
        else:
            # 선택 전: 안내 텍스트
            painter.setPen(QColor(255, 255, 255, 200))
            font = QFont("Pretendard Variable", 14)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "캡처할 영역을 드래그하세요\nESC: 취소")

    def _paint_frame(self, painter: QPainter):
        """프레임을 위젯 크기에 맞춰 그리기 (줌 시 중앙 크롭)"""
        h, w, ch = self._frame.shape

        # 줌 > 1이면 프레임의 중앙 부분만 크롭
        if self._zoom > 1.0:
            crop_w = int(w / self._zoom)
            crop_h = int(h / self._zoom)
            x1 = (w - crop_w) // 2
            y1 = (h - crop_h) // 2
            cropped = self._frame[y1:y1+crop_h, x1:x1+crop_w].copy()
            frame_to_draw = cropped
            fh, fw = crop_h, crop_w
        else:
            frame_to_draw = self._frame
            fh, fw = h, w

        bytes_per_line = ch * fw
        img = QImage(frame_to_draw.data, fw, fh, bytes_per_line, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(img)

        # 위젯 크기에 맞추되 비율 유지
        widget_rect = self.rect()
        scaled = pixmap.scaled(
            widget_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 중앙 배치
        x = (widget_rect.width() - scaled.width()) // 2
        y = (widget_rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # 줌 표시 (1배 이외일 때)
        if abs(self._zoom - 1.0) > 0.05:
            painter.setPen(QColor(0, 168, 255))
            font = QFont("Pretendard Variable", 10)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(x + 8, y + 18, f"×{self._zoom:.1f}")

        # 감지 결과 오버레이
        if self._detections:
            # 줌 크롭 오프셋 계산
            if self._zoom > 1.0:
                crop_x1 = (w - int(w / self._zoom)) // 2
                crop_y1 = (h - int(h / self._zoom)) // 2
                crop_fw = int(w / self._zoom)
                crop_fh = int(h / self._zoom)
            else:
                crop_x1, crop_y1 = 0, 0
                crop_fw, crop_fh = w, h

            scale_x = scaled.width() / crop_fw
            scale_y = scaled.height() / crop_fh
            for det in self._detections:
                bbox = det.get("bbox", [])
                name = det.get("name", "")
                is_reg = det.get("is_registered", False)
                sim = det.get("similarity", 0.0)
                if len(bbox) != 4:
                    continue

                # 정확히 확인된 등록자만 표시 (유사도 0.55 이상)
                if not (is_reg and sim >= 0.55):
                    continue

                bx = int((bbox[0] - crop_x1) * scale_x) + x
                by = int((bbox[1] - crop_y1) * scale_y) + y
                bw = int((bbox[2] - bbox[0]) * scale_x)
                bh = int((bbox[3] - bbox[1]) * scale_y)

                color = QColor(34, 197, 94)
                pen = QPen(color, 2)
                painter.setPen(pen)
                painter.drawRect(bx, by, bw, bh)

                font = QFont("Pretendard Variable", 12)
                font.setWeight(QFont.Weight.Bold)
                painter.setFont(font)
                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(name) + 8
                th = fm.height() + 4
                label_y = by - th - 2
                painter.fillRect(bx, label_y, tw, th, QColor(0, 0, 0, 180))
                painter.setPen(color)
                painter.drawText(bx + 4, by - 6, name)

    def _paint_placeholder(self, painter: QPainter):
        """카메라 미연결 시 플레이스홀더"""
        painter.fillRect(self.rect(), QColor(10, 14, 26))

        # 상태 텍스트
        color = QColor(100, 116, 139) if not self._status_ok else QColor(34, 197, 94)
        painter.setPen(color)
        font = QFont("Pretendard Variable", 14)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._status_text)
