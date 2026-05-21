"""얼굴 감지/인식 스레드 — InsightFace buffalo_sc"""

import time
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from insightface.app import FaceAnalysis
import database


class DetectionThread(QThread):
    """별도 스레드에서 얼굴 감지/인식 수행"""

    faces_detected = pyqtSignal(list)  # [{bbox, name, confidence, is_registered, embedding}]
    visit_logged = pyqtSignal(str, bool)  # name, is_registered

    def __init__(self, config: dict):
        super().__init__()
        self._running = False
        self._frame = None
        self._frame_lock = __import__("threading").Lock()

        det_cfg = config.get("detection", {})
        self._interval = det_cfg.get("interval_ms", 200) / 1000.0
        self._score_threshold = det_cfg.get("score_threshold", 0.5)
        self._similarity_threshold = det_cfg.get("similarity_threshold", 0.4)
        self._cooldown = det_cfg.get("cooldown_seconds", 300)

        self._app = None
        self._known_embeddings = []  # [(visitor_id, name, embedding_np)]
        self._cooldown_map = {}  # visitor_id -> last_seen_time

    def set_frame(self, frame: np.ndarray):
        """카메라 스레드에서 프레임 전달 (복사 없이 참조)"""
        with self._frame_lock:
            self._frame = frame

    def run(self):
        self._running = True

        # InsightFace 초기화
        self._app = FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
        self._app.prepare(ctx_id=-1, det_size=(640, 480))

        # 등록된 얼굴 로드
        self._load_known_faces()

        while self._running:
            with self._frame_lock:
                frame = self._frame

            if frame is not None:
                self._detect(frame)

            time.sleep(self._interval)

    def _load_known_faces(self):
        """DB에서 등록된 얼굴 임베딩 로드"""
        self._known_embeddings = []
        try:
            rows = database.get_all_embeddings()
            for row in rows:
                emb = np.frombuffer(row["embedding"], dtype=np.float32)
                self._known_embeddings.append((row["visitor_id"], row["name"], emb))
        except Exception:
            pass

    def reload_known_faces(self):
        """외부에서 호출: 등록된 얼굴 다시 로드"""
        self._load_known_faces()

    def _detect(self, frame: np.ndarray):
        """프레임에서 얼굴 감지 + 인식"""
        try:
            faces = self._app.get(frame)
        except Exception:
            return

        results = []
        now = time.time()

        for face in faces:
            if face.det_score < self._score_threshold:
                continue

            bbox = face.bbox.astype(int).tolist()
            embedding = face.embedding
            name = "미등록"
            visitor_id = None
            is_registered = False
            best_sim = 0.0

            # 등록된 얼굴과 비교
            if embedding is not None and len(self._known_embeddings) > 0:
                for vid, vname, known_emb in self._known_embeddings:
                    sim = self._cosine_sim(embedding, known_emb)
                    if sim > best_sim:
                        best_sim = sim
                        if sim >= self._similarity_threshold:
                            name = vname
                            visitor_id = vid
                            is_registered = True

            results.append({
                "bbox": bbox,
                "name": name,
                "confidence": float(face.det_score),
                "similarity": float(best_sim),
                "is_registered": is_registered,
                "visitor_id": visitor_id,
                "embedding": embedding,
            })

            # 쿨다운 체크 후 방문 로그
            cooldown_key = visitor_id if visitor_id else f"unknown_{bbox[0]}_{bbox[1]}"
            last_seen = self._cooldown_map.get(cooldown_key, 0)

            if now - last_seen > self._cooldown:
                self._cooldown_map[cooldown_key] = now

                # 썸네일 저장
                thumb_path = self._save_thumbnail(frame, bbox)

                database.add_visit_log(
                    visitor_id=visitor_id,
                    visitor_name=name,
                    confidence=float(face.det_score),
                    thumbnail_path=thumb_path,
                    is_registered=is_registered,
                )
                self.visit_logged.emit(name, is_registered)

        self.faces_detected.emit(results)

    def _save_thumbnail(self, frame: np.ndarray, bbox: list) -> str:
        """얼굴 영역 썸네일 저장"""
        import cv2
        import os
        h, w = frame.shape[:2]
        x1 = max(0, bbox[0] - 20)
        y1 = max(0, bbox[1] - 20)
        x2 = min(w, bbox[2] + 20)
        y2 = min(h, bbox[3] + 20)
        crop = frame[y1:y2, x1:x2]

        ts = time.strftime("%Y%m%d_%H%M%S")
        thumb_dir = r"C:\OfficeMonitor\data\thumbnails"
        os.makedirs(thumb_dir, exist_ok=True)
        path = os.path.join(thumb_dir, f"thumb_{ts}_{bbox[0]}.jpg")
        cv2.imwrite(path, crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return path

    @staticmethod
    def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        return float(dot / norm) if norm > 0 else 0.0

    def register_face(self, name: str, embedding: np.ndarray) -> int:
        """새 얼굴 등록"""
        visitor_id = database.add_visitor(name)
        emb_bytes = embedding.astype(np.float32).tobytes()
        database.add_embedding(visitor_id, emb_bytes)
        self._load_known_faces()
        return visitor_id

    def stop(self):
        self._running = False
        self.wait(3000)
