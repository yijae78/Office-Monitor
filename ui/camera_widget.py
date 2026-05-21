"""리사이즈/확대축소 가능한 카메라 뷰어 위젯"""

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QPen


class CameraWidget(QWidget):
    """카메라 영상을 표시하는 위젯. 확대/축소, 자유 리사이즈 지원."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._frame = None
        self._detections = []
        self._status_text = "카메라 연결 대기 중..."
        self._status_ok = False

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 배경
        painter.fillRect(self.rect(), QColor(10, 10, 10))

        if self._frame is not None:
            self._paint_frame(painter)
        else:
            self._paint_placeholder(painter)

        painter.end()

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
                if len(bbox) != 4:
                    continue

                # 등록된 사람만 표시
                if not is_reg:
                    continue

                bx = int((bbox[0] - crop_x1) * scale_x) + x
                by = int((bbox[1] - crop_y1) * scale_y) + y
                bw = int((bbox[2] - bbox[0]) * scale_x)
                bh = int((bbox[3] - bbox[1]) * scale_y)

                color = QColor(34, 197, 94)
                pen = QPen(color, 2)
                painter.setPen(pen)
                painter.drawRect(bx, by, bw, bh)

                if name:
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
