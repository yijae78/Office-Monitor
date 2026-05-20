"""OfficeMonitor — 사무실 출입자 모니터링 시스템"""

import sys
import os
import yaml

# 프로젝트 루트를 path에 추가
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
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
    ensure_directories()
    config = load_config()

    app = QApplication(sys.argv)
    app.setApplicationName("OfficeMonitor")

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
