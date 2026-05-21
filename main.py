"""OfficeMonitor — 사무실 출입자 모니터링 시스템"""

import sys
import os
import yaml
import ctypes

# 프로젝트 루트를 path에 추가
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow


DATA_DIR = r"C:\OfficeMonitor"


def ensure_directories():
    """데이터 디렉토리 구조 확인/생성"""
    dirs = [
        os.path.join(DATA_DIR, "snapshots"),
        os.path.join(DATA_DIR, "recordings"),
        os.path.join(DATA_DIR, "known_faces"),
        os.path.join(DATA_DIR, "saved", "snapshots"),
        os.path.join(DATA_DIR, "saved", "recordings"),
        os.path.join(DATA_DIR, "data"),
        os.path.join(DATA_DIR, "data", "thumbnails"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def load_config() -> dict:
    """config.yaml 로드"""
    config_path = os.path.join(PROJECT_DIR, "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def main():
    # Windows 작업표시줄 아이콘 표시를 위한 AppUserModelID
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OfficeMonitor.App")

    ensure_directories()
    config = load_config()

    app = QApplication(sys.argv)
    app.setApplicationName("OfficeMonitor")

    # 앱 아이콘 (작업표시줄 + 타이틀바) — 다중 사이즈 PNG 로드
    icon = QIcon()
    for size in [16, 32, 48, 64, 128, 256, 512]:
        png_path = os.path.join(PROJECT_DIR, "assets", f"icon-{size}.png")
        if os.path.exists(png_path):
            icon.addFile(png_path)
    ico_path = os.path.join(PROJECT_DIR, "icon.ico")
    if os.path.exists(ico_path):
        icon.addFile(ico_path)

    app.setWindowIcon(icon)

    window = MainWindow(config)
    window.setWindowIcon(icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
