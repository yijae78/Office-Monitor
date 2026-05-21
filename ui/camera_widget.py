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
        """새 프레임 + 감지 결과 업데이트"""
        self._frame = frame
        self._detections = detections or []
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
            delta = event.angleDelta().y() / 1200.0
            self.set_zoom(self._zoom + delta)
            event.accept()
        else:
            super().wheelEvent(event)

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
        """프레임을 위젯 크기에 맞춰 그리기"""
        h, w, ch = self._frame.shape
        bytes_per_line = ch * w
        img = QImage(self._frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(img)

        # 줌 적용한 크기 계산
        scaled_w = int(pixmap.width() * self._zoom)
        scaled_h = int(pixmap.height() * self._zoom)

        # 위젯 크기에 맞추되 비율 유지
        widget_rect = self.rect()
        scaled = pixmap.scaled(
            QSize(scaled_w, scaled_h),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 위젯보다 크면 위젯 크기에 맞춤
        if scaled.width() > widget_rect.width() or scaled.height() > widget_rect.height():
            scaled = pixmap.scaled(
                widget_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        # 중앙 배치
        x = (widget_rect.width() - scaled.width()) // 2
        y = (widget_rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # 감지 결과 오버레이
        if self._detections:
            scale_x = scaled.width() / w
            scale_y = scaled.height() / h
            for det in self._detections:
                bbox = det.get("bbox", [])
                name = det.get("name", "")
                if len(bbox) == 4:
                    bx = int(bbox[0] * scale_x) + x
                    by = int(bbox[1] * scale_y) + y
                    bw = int((bbox[2] - bbox[0]) * scale_x)
                    bh = int((bbox[3] - bbox[1]) * scale_y)

                    pen = QPen(QColor(34, 197, 94), 2)
                    painter.setPen(pen)
                    painter.drawRect(bx, by, bw, bh)

                    if name:
                        font = QFont("Pretendard Variable", 11)
                        font.setWeight(QFont.Weight.Bold)
                        painter.setFont(font)
                        painter.setPen(QColor(34, 197, 94))
                        painter.drawText(bx, by - 6, name)

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
