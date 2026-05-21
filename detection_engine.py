"""얼굴 감지/인식 + 사람 추적 스레드
— InsightFace (다중 임베딩) + YOLO11n + ByteTrack"""

import time
import os
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from insightface.app import FaceAnalysis
import database


class DetectionThread(QThread):
    """얼굴 인식 + 사람 추적 통합 스레드

    파이프라인:
    1. YOLO11n → 사람 바운딩박스 (모든 각도)
    2. ByteTrack → track_id 부여/유지
    3. InsightFace → 얼굴 검출 시 임베딩 매칭 → track_id에 이름 바인딩
    4. 얼굴 미검출 → track_id의 기존 이름 유지 (뒷모습도 OK)
    """

    faces_detected = pyqtSignal(list)   # [{bbox, name, confidence, track_id, ...}]
    visit_logged = pyqtSignal(str, bool)  # name, is_registered
    face_captured = pyqtSignal(int)  # pending_face_id

    MAX_EMBEDDINGS_PER_VISITOR = 10
    MIN_FACE_SIZE = 60          # 최소 얼굴 크기 (px)
    MIN_BLUR_SCORE = 25.0       # 최소 선명도 (라플라시안 분산)
    MIN_CAPTURE_DET_SCORE = 0.40  # 수집 최소 감지 점수
    DUPLICATE_SIM_THRESHOLD = 0.55  # 같은 사람 판정 임계값
    CROP_PAD_RATIO = 0.7       # 얼굴 크기 대비 여백 비율
    MIN_SAVE_SIZE = 200         # 최종 저장 이미지 최소 크기 (px)
    CAPTURE_DURATION = 3.0      # 최고 프레임 수집 시간 (초)
    MIN_QUALITY_SCORE = 25.0    # 최소 품질 점수 (완전 불량만 차단)

    def __init__(self, config: dict):
        super().__init__()
        self._running = False
        self._frame = None
        self._frame_lock = __import__("threading").Lock()

        det_cfg = config.get("detection", {})
        self._model_name = det_cfg.get("model", "buffalo_l")
        self._det_size = tuple(det_cfg.get("det_size", [640, 640]))
        self._interval = det_cfg.get("interval_ms", 200) / 1000.0
        self._score_threshold = det_cfg.get("score_threshold", 0.35)
        self._similarity_threshold = det_cfg.get("similarity_threshold", 0.4)
        self._cooldown = det_cfg.get("cooldown_seconds", 300)
        self._auto_augment = det_cfg.get("auto_augment_embeddings", True)

        self._app = None        # InsightFace
        self._yolo = None       # YOLO11n
        self._known_faces = {}  # {visitor_id: {"name", "embeddings": [...]}}
        self._cooldown_map = {}
        self._new_face_cooldown = {}

        # pending_faces 임베딩 캐시 (중복 방지용)
        self._pending_embeddings = []  # [(pending_id, embedding)]

        # 최고 프레임 수집 후보 (3초간 프레임 비교 후 최고만 저장)
        # {candidate_key: {"start": float, "score": float,
        #                   "frame": ndarray, "bbox": list,
        #                   "embedding": ndarray, "det_score": float,
        #                   "count": int}}
        self._capture_candidates = {}

        # track_id → visitor 이름 매핑 (ByteTrack 추적용)
        self._track_names = {}       # {track_id: name}
        self._track_visitors = {}    # {track_id: visitor_id or None}
        self._track_registered = {}  # {track_id: bool}

    def set_frame(self, frame: np.ndarray):
        with self._frame_lock:
            self._frame = frame

    def run(self):
        self._running = True

        # InsightFace 초기화
        self._app = FaceAnalysis(name=self._model_name, providers=["CPUExecutionProvider"])
        self._app.prepare(ctx_id=-1, det_size=self._det_size)

        # YOLO 초기화
        try:
            from ultralytics import YOLO
            self._yolo = YOLO("yolo11n.pt")
        except Exception:
            self._yolo = None

        self._load_known_faces()
        self._load_pending_embeddings()

        while self._running:
            with self._frame_lock:
                frame = self._frame

            if frame is not None:
                self._detect(frame)

            time.sleep(self._interval)

    def _load_known_faces(self):
        self._known_faces = {}
        try:
            rows = database.get_all_embeddings()
            for row in rows:
                vid = row["visitor_id"]
                emb = np.frombuffer(row["embedding"], dtype=np.float32).copy()
                if vid not in self._known_faces:
                    self._known_faces[vid] = {"name": row["name"], "embeddings": []}
                self._known_faces[vid]["embeddings"].append(emb)
        except Exception:
            pass

    def reload_known_faces(self):
        self._load_known_faces()
        self._load_pending_embeddings()

    def _detect(self, frame: np.ndarray):
        """통합 감지 파이프라인"""
        now = time.time()

        if self._yolo is not None:
            self._detect_with_tracking(frame, now)
        else:
            self._detect_face_only(frame, now)

        # 수집 시간이 지난 후보를 확정하여 저장
        self._finalize_candidates(now)

    def _detect_with_tracking(self, frame: np.ndarray, now: float):
        """YOLO + ByteTrack + InsightFace 통합 파이프라인"""
        # 1단계: YOLO 사람 감지 + ByteTrack 추적
        try:
            track_results = self._yolo.track(
                frame, classes=[0], persist=True,
                tracker="bytetrack.yaml", verbose=False,
                conf=0.4, iou=0.5,
            )
        except Exception:
            self._detect_face_only(frame, now)
            return

        results = []
        active_track_ids = set()

        if track_results and track_results[0].boxes is not None and len(track_results[0].boxes):
            boxes = track_results[0].boxes

            for i in range(len(boxes)):
                bbox = boxes.xyxy[i].cpu().numpy().astype(int).tolist()
                conf = float(boxes.conf[i].cpu())
                track_id = int(boxes.id[i].cpu()) if boxes.id is not None else -1

                active_track_ids.add(track_id)

                # 2단계: 사람 영역 내에서 InsightFace 얼굴 감지
                h, w = frame.shape[:2]
                px1 = max(0, bbox[0])
                py1 = max(0, bbox[1])
                px2 = min(w, bbox[2])
                py2 = min(h, bbox[3])
                person_crop = frame[py1:py2, px1:px2]

                name = self._track_names.get(track_id, "미등록")
                visitor_id = self._track_visitors.get(track_id)
                is_registered = self._track_registered.get(track_id, False)
                embedding = None
                best_sim = 0.0

                if person_crop.size > 0:
                    try:
                        faces = self._app.get(person_crop)
                        if faces:
                            face = max(faces, key=lambda f: f.det_score)
                            if face.det_score >= self._score_threshold and face.embedding is not None:
                                embedding = face.embedding
                                # 얼굴 매칭
                                matched_name, matched_vid, matched_sim, matched_reg = self._match_face(embedding)
                                best_sim = matched_sim

                                if matched_reg:
                                    name = matched_name
                                    visitor_id = matched_vid
                                    is_registered = True

                                    # track_id에 이름 바인딩
                                    self._track_names[track_id] = name
                                    self._track_visitors[track_id] = visitor_id
                                    self._track_registered[track_id] = True

                                    if self._auto_augment:
                                        self._try_augment_embedding(visitor_id, embedding)
                                else:
                                    # 미등록이지만 이전에 바인딩된 이름이 있으면 유지
                                    if track_id not in self._track_names:
                                        self._track_names[track_id] = "미등록"
                                        self._track_visitors[track_id] = None
                                        self._track_registered[track_id] = False

                                    # 미등록 얼굴 → 최고 프레임 수집
                                    if not is_registered:
                                        face_bbox = face.bbox.astype(int)
                                        abs_bbox = [
                                            face_bbox[0] + px1, face_bbox[1] + py1,
                                            face_bbox[2] + px1, face_bbox[3] + py1,
                                        ]
                                        self._notify_new_face(
                                            frame, abs_bbox, embedding, now,
                                            det_score=float(face.det_score),
                                            track_id=track_id, face=face)
                    except Exception:
                        pass

                results.append({
                    "bbox": bbox,
                    "name": name,
                    "confidence": conf,
                    "similarity": float(best_sim),
                    "is_registered": is_registered,
                    "visitor_id": visitor_id,
                    "track_id": track_id,
                    "embedding": embedding,
                    "type": "person",
                })

                # 쿨다운 체크 후 방문 로그
                cooldown_key = visitor_id if visitor_id else f"track_{track_id}"
                last_seen = self._cooldown_map.get(cooldown_key, 0)
                if now - last_seen > self._cooldown:
                    self._cooldown_map[cooldown_key] = now
                    thumb_path = self._save_thumbnail(frame, bbox)
                    database.add_visit_log(
                        visitor_id=visitor_id,
                        visitor_name=name,
                        confidence=conf,
                        thumbnail_path=thumb_path,
                        is_registered=is_registered,
                    )
                    self.visit_logged.emit(name, is_registered)

        # 사라진 track_id 정리 (30초 후)
        for tid in list(self._track_names.keys()):
            if tid not in active_track_ids:
                # 나중에 같은 ID가 재사용될 수 있으므로 바로 삭제하지 않음
                pass

        self.faces_detected.emit(results)

    def _detect_face_only(self, frame: np.ndarray, now: float):
        """YOLO 없이 InsightFace만 사용하는 폴백 모드"""
        try:
            faces = self._app.get(frame)
        except Exception:
            return

        results = []
        for face in faces:
            if face.det_score < self._score_threshold:
                continue

            bbox = face.bbox.astype(int).tolist()
            embedding = face.embedding
            name, visitor_id, best_sim, is_registered = self._match_face(embedding)

            results.append({
                "bbox": bbox,
                "name": name,
                "confidence": float(face.det_score),
                "similarity": float(best_sim),
                "is_registered": is_registered,
                "visitor_id": visitor_id,
                "track_id": -1,
                "embedding": embedding,
                "type": "face",
            })

            if is_registered and self._auto_augment and embedding is not None:
                self._try_augment_embedding(visitor_id, embedding)

            cooldown_key = visitor_id if visitor_id else f"unknown_{bbox[0]}_{bbox[1]}"
            last_seen = self._cooldown_map.get(cooldown_key, 0)
            if now - last_seen > self._cooldown:
                self._cooldown_map[cooldown_key] = now
                thumb_path = self._save_thumbnail(frame, bbox)
                database.add_visit_log(
                    visitor_id=visitor_id, visitor_name=name,
                    confidence=float(face.det_score),
                    thumbnail_path=thumb_path, is_registered=is_registered,
                )
                self.visit_logged.emit(name, is_registered)

            if not is_registered and embedding is not None:
                self._notify_new_face(frame, bbox, embedding, now,
                                      det_score=float(face.det_score),
                                      track_id=-1, face=face)

        self.faces_detected.emit(results)

    def _match_face(self, embedding: np.ndarray):
        """임베딩 매칭 → (name, visitor_id, best_sim, is_registered)"""
        name = "미등록"
        visitor_id = None
        is_registered = False
        best_sim = 0.0

        if embedding is not None and len(self._known_faces) > 0:
            for vid, info in self._known_faces.items():
                for known_emb in info["embeddings"]:
                    sim = self._cosine_sim(embedding, known_emb)
                    if sim > best_sim:
                        best_sim = sim
                        if sim >= self._similarity_threshold:
                            name = info["name"]
                            visitor_id = vid
                            is_registered = True

        return name, visitor_id, best_sim, is_registered

    def _try_augment_embedding(self, visitor_id: int, embedding: np.ndarray):
        info = self._known_faces.get(visitor_id)
        if not info or len(info["embeddings"]) >= self.MAX_EMBEDDINGS_PER_VISITOR:
            return
        max_sim = max(self._cosine_sim(embedding, e) for e in info["embeddings"])
        if max_sim < 0.8:
            emb_bytes = embedding.astype(np.float32).tobytes()
            database.add_embedding(visitor_id, emb_bytes)
            info["embeddings"].append(embedding.copy())

    def _load_pending_embeddings(self):
        """DB의 pending_faces 임베딩을 캐시로 로드 (중복 방지용)"""
        self._pending_embeddings = []
        try:
            rows = database.get_pending_faces("pending")
            for row in rows:
                emb = np.frombuffer(row["embedding"], dtype=np.float32).copy()
                self._pending_embeddings.append((row["id"], emb))
        except Exception:
            pass

    # ═══════════════════════════════════════════
    # 최고 프레임 선별 시스템 (3초 수집 → 최고 1장 저장)
    # ═══════════════════════════════════════════

    def _compute_quality_score(self, frame: np.ndarray, bbox: list,
                               det_score: float, face=None) -> float:
        """얼굴 품질 종합 점수 (0~100)

        - 감지 점수 (30%) — InsightFace det_score
        - 얼굴 크기 (25%) — 클수록 좋음 (최대 200px에서 만점)
        - 선명도   (25%) — 라플라시안 분산
        - 정면도   (20%) — 좌우 눈 수평 대칭
        """
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
        face_w = x2 - x1
        face_h = y2 - y1

        # 1. 감지 점수 (0~30)
        score_det = min(det_score / 1.0, 1.0) * 30

        # 2. 얼굴 크기 (0~25) — 200px 이상이면 만점
        face_size = max(face_w, face_h)
        score_size = min(face_size / 200.0, 1.0) * 25

        # 3. 선명도 (0~25)
        face_region = frame[max(0,y1):min(h,y2), max(0,x1):min(w,x2)]
        score_blur = 0.0
        if face_region.size > 0:
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            blur_val = cv2.Laplacian(gray, cv2.CV_64F).var()
            score_blur = min(blur_val / 200.0, 1.0) * 25

        # 4. 정면도 (0~20) — 좌우 기울기 + 상하 각도(코 위치)
        score_front = 5.0  # 기본 낮은 점수
        if face is not None and hasattr(face, 'kps') and face.kps is not None:
            kps = face.kps
            if len(kps) >= 3:
                left_eye, right_eye, nose = kps[0], kps[1], kps[2]
                eye_center_x = (left_eye[0] + right_eye[0]) / 2
                eye_center_y = (left_eye[1] + right_eye[1]) / 2
                eye_dist_x = abs(left_eye[0] - right_eye[0])

                if eye_dist_x > 0:
                    # 좌우 기울기 (0~10)
                    tilt_ratio = abs(left_eye[1] - right_eye[1]) / eye_dist_x
                    tilt_score = max(0, 1.0 - tilt_ratio * 5) * 10

                    # 상하 각도: 코가 눈 중심 바로 아래에 있어야 정면 (0~10)
                    nose_offset_x = abs(nose[0] - eye_center_x) / eye_dist_x
                    nose_below = (nose[1] - eye_center_y) / eye_dist_x
                    # 코가 눈 아래 0.3~0.8 범위에 있고, 좌우 편차 적으면 정면
                    if 0.2 < nose_below < 1.0 and nose_offset_x < 0.3:
                        vert_score = max(0, 1.0 - nose_offset_x * 3) * 10
                    else:
                        vert_score = 0.0

                    score_front = tilt_score + vert_score

        elif face is not None and hasattr(face, 'landmark_2d_106'):
            lm = face.landmark_2d_106
            if lm is not None and len(lm) >= 106:
                left_eye_y = np.mean(lm[33:42, 1])
                right_eye_y = np.mean(lm[87:96, 1])
                eye_diff = abs(left_eye_y - right_eye_y)
                eye_dist = abs(np.mean(lm[33:42, 0]) - np.mean(lm[87:96, 0]))
                if eye_dist > 0:
                    tilt_ratio = eye_diff / eye_dist
                    score_front = max(0, 1.0 - tilt_ratio * 5) * 20

        return score_det + score_size + score_blur + score_front

    def _is_duplicate_face(self, embedding: np.ndarray, now: float) -> bool:
        """이미 캡처된 얼굴인지 확인 (메모리 쿨다운 + DB pending_faces + 수집중 후보)"""
        # 1. 메모리 쿨다운
        for key, (last_time, prev_emb) in list(self._new_face_cooldown.items()):
            if now - last_time > self._cooldown:
                del self._new_face_cooldown[key]
                continue
            if self._cosine_sim(embedding, prev_emb) >= self.DUPLICATE_SIM_THRESHOLD:
                return True

        # 2. DB pending_faces 캐시
        for pid, prev_emb in self._pending_embeddings:
            if self._cosine_sim(embedding, prev_emb) >= self.DUPLICATE_SIM_THRESHOLD:
                return True

        return False

    def _find_candidate_key(self, embedding: np.ndarray, track_id: int) -> str:
        """현재 얼굴에 해당하는 수집 후보 키 찾기"""
        # track_id가 있으면 track 기반
        if track_id >= 0:
            return f"track_{track_id}"
        # track_id 없으면 임베딩 유사도로 기존 후보 매칭
        for key, cand in self._capture_candidates.items():
            if self._cosine_sim(embedding, cand["embedding"]) >= self.DUPLICATE_SIM_THRESHOLD:
                return key
        return f"emb_{id(embedding)}_{int(time.time()*1000)}"

    def _notify_new_face(self, frame: np.ndarray, bbox: list, embedding: np.ndarray,
                         now: float, det_score: float = 0.6,
                         track_id: int = -1, face=None):
        """미등록 얼굴 → 3초간 프레임 수집, 최고 품질만 저장"""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
        face_w = x2 - x1
        face_h = y2 - y1

        # 기본 필터 (최소 크기, 가장자리 잘림)
        if face_w < self.MIN_FACE_SIZE or face_h < self.MIN_FACE_SIZE:
            return
        margin = min(face_w, face_h) * 0.1
        if x1 < margin or y1 < margin or x2 > w - margin or y2 > h - margin:
            return

        # 이미 저장 완료된 얼굴인지 확인
        if self._is_duplicate_face(embedding, now):
            return

        # 품질 점수 계산
        score = self._compute_quality_score(frame, bbox, det_score, face)

        # 후보 키 찾기/생성
        cand_key = self._find_candidate_key(embedding, track_id)

        if cand_key in self._capture_candidates:
            # 기존 후보 — 더 좋은 프레임이면 교체
            cand = self._capture_candidates[cand_key]
            cand["count"] += 1
            if score > cand["score"]:
                cand["score"] = score
                cand["frame"] = frame.copy()
                cand["bbox"] = bbox
                cand["embedding"] = embedding.copy()
                cand["det_score"] = det_score
        else:
            # 새 후보 시작
            self._capture_candidates[cand_key] = {
                "start": now,
                "score": score,
                "frame": frame.copy(),
                "bbox": bbox,
                "embedding": embedding.copy(),
                "det_score": det_score,
                "count": 1,
            }

    def _finalize_candidates(self, now: float):
        """수집 시간이 지난 후보를 확정하여 저장 (최소 품질 미달 시 폐기)"""
        done_keys = []
        for key, cand in self._capture_candidates.items():
            if now - cand["start"] < self.CAPTURE_DURATION:
                continue
            done_keys.append(key)

            # 최소 품질 점수 미달 → 폐기
            if cand["score"] < self.MIN_QUALITY_SCORE:
                continue

            # 최종 저장
            self._save_best_capture(cand, now)

        for key in done_keys:
            del self._capture_candidates[key]

    def _make_quality_crop(self, frame: np.ndarray, bbox: list) -> np.ndarray:
        """얼굴 bbox → 머리~어깨 포함 고품질 크롭"""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
        face_w = x2 - x1
        face_h = y2 - y1

        pad_x = int(face_w * self.CROP_PAD_RATIO)
        pad_y_top = int(face_h * 0.8)
        pad_y_bot = int(face_h * 0.9)
        cx1 = max(0, x1 - pad_x)
        cy1 = max(0, y1 - pad_y_top)
        cx2 = min(w, x2 + pad_x)
        cy2 = min(h, y2 + pad_y_bot)
        crop = frame[cy1:cy2, cx1:cx2]

        if crop.size == 0:
            return None

        # 최소 크기 보장
        ch, cw = crop.shape[:2]
        if cw < self.MIN_SAVE_SIZE or ch < self.MIN_SAVE_SIZE:
            scale = max(self.MIN_SAVE_SIZE / cw, self.MIN_SAVE_SIZE / ch)
            crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)),
                              interpolation=cv2.INTER_LANCZOS4)
        return crop

    def _save_best_capture(self, cand: dict, now: float):
        """후보의 최고 프레임을 파일로 저장"""
        frame = cand["frame"]
        bbox = cand["bbox"]
        embedding = cand["embedding"]

        face_crop = self._make_quality_crop(frame, bbox)
        if face_crop is None:
            return

        # 선명도 최종 체크 (크롭 이미지 기준, 완전 블러만 차단)
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        if cv2.Laplacian(gray, cv2.CV_64F).var() < self.MIN_BLUR_SCORE * 0.5:
            return

        pending_dir = r"C:\OfficeMonitor\data\pending_faces"
        os.makedirs(pending_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        img_path = os.path.join(pending_dir, f"face_{ts}_{bbox[0]}.jpg")
        cv2.imwrite(img_path, face_crop, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # 저장된 이미지 재검증
        if not self._verify_saved_face(img_path):
            try:
                os.remove(img_path)
            except OSError:
                pass
            return

        emb_bytes = embedding.astype(np.float32).tobytes()
        pending_id = database.add_pending_face(img_path, emb_bytes)

        # 캐시 업데이트
        emb_copy = embedding.astype(np.float32).copy()
        self._pending_embeddings.append((pending_id, emb_copy))
        self._new_face_cooldown[f"saved_{int(now*1000)}"] = (now, emb_copy)

        self.face_captured.emit(pending_id)

    def _verify_saved_face(self, img_path: str) -> bool:
        """저장된 이미지에서 얼굴 재감지 — 완전 불량만 거부"""
        try:
            img = cv2.imread(img_path)
            if img is None:
                return False
            h, w = img.shape[:2]
            if h < 50 or w < 50:
                return False
            # InsightFace로 얼굴 재감지 — 크롭 이미지에서 얼굴이 아예 안 잡히면 불량
            faces = self._app.get(img)
            if not faces:
                return False
            best = max(faces, key=lambda f: f.det_score)
            if best.det_score < 0.3:
                return False
            return True
        except Exception:
            return False

    def cleanup_bad_pending_faces(self):
        """기존 pending_faces 중 불량 이미지 자동 삭제"""
        try:
            rows = database.get_pending_faces("pending")
        except Exception:
            return 0
        removed = 0
        for row in (rows or []):
            img_path = row["image_path"]
            # 파일 없음 → 삭제
            if not os.path.exists(img_path):
                database.hard_delete_pending_face(row["id"])
                self._pending_embeddings = [
                    (pid, e) for pid, e in self._pending_embeddings if pid != row["id"]
                ]
                removed += 1
                continue
            # 품질 재검사
            if not self._verify_saved_face(img_path):
                try:
                    os.remove(img_path)
                except OSError:
                    pass
                database.hard_delete_pending_face(row["id"])
                self._pending_embeddings = [
                    (pid, e) for pid, e in self._pending_embeddings if pid != row["id"]
                ]
                removed += 1
        return removed

    def _save_thumbnail(self, frame: np.ndarray, bbox: list) -> str:
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
        """방문자 등록 — 같은 이름이 이미 있으면 임베딩만 추가"""
        emb_copy = embedding.astype(np.float32).copy()
        emb_bytes = emb_copy.tobytes()

        # 같은 이름의 기존 방문자가 있는지 확인
        existing = database.find_visitor_by_name(name.strip())
        if existing:
            visitor_id = existing["id"]
            # 기존 방문자에 임베딩 추가 (최대 개수 체크)
            current_embs = database.get_embeddings_for_visitor(visitor_id)
            if current_embs and len(current_embs) >= self.MAX_EMBEDDINGS_PER_VISITOR:
                # 가장 오래된 임베딩 삭제
                oldest_id = current_embs[0]["id"]
                database.execute("DELETE FROM face_embeddings WHERE id=?", (oldest_id,))
            database.add_embedding(visitor_id, emb_bytes)
            # 메모리 캐시 업데이트
            if visitor_id in self._known_faces:
                self._known_faces[visitor_id]["embeddings"].append(emb_copy)
                # 최대 개수 유지
                if len(self._known_faces[visitor_id]["embeddings"]) > self.MAX_EMBEDDINGS_PER_VISITOR:
                    self._known_faces[visitor_id]["embeddings"].pop(0)
            else:
                self._known_faces[visitor_id] = {
                    "name": name,
                    "embeddings": [emb_copy],
                }
        else:
            # 새 방문자 생성
            visitor_id = database.add_visitor(name)
            database.add_embedding(visitor_id, emb_bytes)
            self._known_faces[visitor_id] = {
                "name": name,
                "embeddings": [emb_copy],
            }
        return visitor_id

    def stop(self):
        self._running = False
        self.wait(3000)
