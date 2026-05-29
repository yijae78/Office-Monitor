"""녹화 영상에서 감지 오버레이를 그린 데모 캡처 생성"""

import sys
import os

# 프로젝트 루트를 path에 추가
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from insightface.app import FaceAnalysis
from ultralytics import YOLO
import database
from paths import DATA_DIR

# ── 설정 ──
RECORDINGS_DIR = os.path.join(DATA_DIR, "recordings")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "assets", "demo")
SIMILARITY_THRESHOLD = 0.65
SCORE_THRESHOLD = 0.35
SAMPLE_INTERVAL = 60       # N프레임마다 1회 분석
MIN_PEOPLE = 1              # 최소 감지 인원수
MAX_CAPTURES = 2            # 총 캡처 수


def load_known_faces():
    """DB에서 등록된 얼굴 임베딩 로드 → 행렬 + 메타"""
    rows = database.get_all_embeddings()
    all_embs = []
    meta = []
    for row in (rows or []):
        emb = np.frombuffer(row["embedding"], dtype=np.float32).copy()
        all_embs.append(emb)
        meta.append((row["visitor_id"], row["name"]))
    if all_embs:
        matrix = np.vstack(all_embs).astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1)
        return matrix, norms, meta
    return None, None, []


def match_face(embedding, matrix, norms, meta):
    """임베딩 매칭"""
    if embedding is None or matrix is None:
        return "미등록", None, 0.0, False
    emb_norm = np.linalg.norm(embedding)
    if emb_norm == 0:
        return "미등록", None, 0.0, False
    sims = (matrix @ embedding) / (norms * emb_norm)
    best_idx = int(np.argmax(sims))
    best_sim = float(sims[best_idx])
    if best_sim >= SIMILARITY_THRESHOLD:
        vid, name = meta[best_idx]
        return name, vid, best_sim, True
    return "미등록", None, best_sim, False


def draw_overlay(frame, detections):
    """감지 결과를 프레임 위에 그리기 (앱과 동일한 스타일)"""
    for det in detections:
        bbox = det["bbox"]
        name = det["name"]
        is_registered = det["is_registered"]
        is_body = det.get("type") == "body"
        x1, y1, x2, y2 = bbox

        if is_registered:
            color = (94, 197, 34)  # BGR: #22C55E 초록
            if is_body:
                # 점선
                dash_len = 12
                for i in range(x1, x2, dash_len * 2):
                    cv2.line(frame, (i, y1), (min(i + dash_len, x2), y1), color, 1)
                    cv2.line(frame, (i, y2), (min(i + dash_len, x2), y2), color, 1)
                for i in range(y1, y2, dash_len * 2):
                    cv2.line(frame, (x1, i), (x1, min(i + dash_len, y2)), color, 1)
                    cv2.line(frame, (x2, i), (x2, min(i + dash_len, y2)), color, 1)
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = name
        else:
            color = (68, 68, 239)  # BGR: #EF4444 빨강
            if is_body:
                label = "미인식"
                dash_len = 10
                for i in range(x1, x2, dash_len * 2):
                    cv2.line(frame, (i, y1), (min(i + dash_len, x2), y1), color, 1)
                    cv2.line(frame, (i, y2), (min(i + dash_len, x2), y2), color, 1)
                for i in range(y1, y2, dash_len * 2):
                    cv2.line(frame, (x1, i), (x1, min(i + dash_len, y2)), color, 1)
                    cv2.line(frame, (x2, i), (x2, min(i + dash_len, y2)), color, 1)
            else:
                label = "미등록"
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    # Pillow로 한글 라벨 렌더링
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)

    try:
        pil_font = ImageFont.truetype("malgun.ttf", 18)
    except OSError:
        pil_font = ImageFont.load_default()

    for det in detections:
        bbox = det["bbox"]
        name = det["name"]
        is_registered = det["is_registered"]
        x1, y1, x2, y2 = bbox

        pil_color = (34, 197, 94) if is_registered else (239, 68, 68)  # RGB
        label = name

        tb = draw.textbbox((0, 0), label, font=pil_font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        lx, ly = x1, y1 - th - 10
        if ly < 0:
            ly = y2 + 4

        draw.rectangle([lx, ly, lx + tw + 10, ly + th + 6], fill=(0, 0, 0))
        draw.text((lx + 5, ly + 2), label, font=pil_font, fill=pil_color)

    frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return frame


def process_video(video_path, face_app, yolo, matrix, norms, meta, candidates):
    """영상 프레임 샘플링 → 감지 → 후보 수집"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  열기 실패: {video_path}")
        return candidates

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    fname = os.path.basename(video_path)
    print(f"  {fname}: {total_frames}프레임, {fps:.0f}fps, {total_frames/fps:.0f}초")

    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % SAMPLE_INTERVAL != 0:
            continue

        # YOLO 사람 감지 (tracking 없이 detect만)
        try:
            det_results = yolo(frame, classes=[0], verbose=False, conf=0.4)
        except Exception:
            continue

        tracks = []
        if det_results and det_results[0].boxes is not None and len(det_results[0].boxes):
            boxes = det_results[0].boxes
            for i in range(len(boxes)):
                bbox = boxes.xyxy[i].cpu().numpy().astype(int).tolist()
                conf = float(boxes.conf[i].cpu())
                tid = i  # 추적 없이 인덱스 사용
                tracks.append((tid, bbox, conf))

        if len(tracks) < MIN_PEOPLE:
            continue

        # InsightFace 얼굴 감지
        all_faces = []
        try:
            all_faces = face_app.get(frame)
        except Exception:
            pass

        # 얼굴 → track 매칭
        track_face = {}
        for face in all_faces:
            if face.det_score < SCORE_THRESHOLD:
                continue
            fb = face.bbox.astype(int)
            fcx = (fb[0] + fb[2]) / 2
            fcy = (fb[1] + fb[3]) / 2
            best_tid = None
            best_dist = float('inf')
            for tid, pbbox, _ in tracks:
                if pbbox[0] <= fcx <= pbbox[2] and pbbox[1] <= fcy <= pbbox[3]:
                    pcx = (pbbox[0] + pbbox[2]) / 2
                    pcy = (pbbox[1] + pbbox[3]) / 2
                    dist = ((fcx - pcx) ** 2 + (fcy - pcy) ** 2) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        best_tid = tid
            if best_tid is not None:
                if best_tid not in track_face or track_face[best_tid].det_score < face.det_score:
                    track_face[best_tid] = face

        # 결과 생성
        detections = []
        face_count = 0
        registered_count = 0

        for tid, person_bbox, person_conf in tracks:
            face = track_face.get(tid)
            if face is not None and face.embedding is not None:
                name, vid, sim, is_reg = match_face(face.embedding, matrix, norms, meta)
                face_count += 1
                if is_reg:
                    registered_count += 1
                detections.append({
                    "bbox": face.bbox.astype(int).tolist(),
                    "name": name,
                    "is_registered": is_reg,
                    "type": "face",
                })
                # person bbox도 추가 (얼굴 박스와 다를 때)
                detections.append({
                    "bbox": person_bbox,
                    "name": name,
                    "is_registered": is_reg,
                    "type": "body",
                })
            else:
                # 얼굴 없음
                name, is_reg = "미인식", False
                detections.append({
                    "bbox": person_bbox,
                    "name": name,
                    "is_registered": is_reg,
                    "type": "body",
                })

        if face_count == 0:
            continue

        # 점수 산정: 등록자 있으면 우선, 사람 많으면 가산
        score = registered_count * 10 + face_count * 3 + len(tracks)

        # 후보에 추가 (나중에 상위 N개 선택)
        sec = frame_idx / fps
        timestamp = f"{int(sec//60):02d}:{int(sec%60):02d}"
        candidates.append({
            "frame": frame.copy(),
            "detections": detections,
            "score": score,
            "timestamp": timestamp,
            "n_people": len(tracks),
            "n_faces": face_count,
            "n_registered": registered_count,
            "video": os.path.basename(video_path),
        })

    cap.release()
    return candidates


def main():
    print("=== 데모 캡처 생성 ===\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # DB 초기화
    database.init_db()

    # 모델 로드
    print("[1/3] 모델 로드 중...")
    face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    face_app.prepare(ctx_id=-1, det_size=(640, 640))
    yolo = YOLO("yolo11n.pt")
    print("  완료\n")

    # 알려진 얼굴 로드
    print("[2/3] 등록된 얼굴 로드 중...")
    matrix, norms, meta = load_known_faces()
    n_visitors = len(set(m[0] for m in meta)) if meta else 0
    n_embs = len(meta)
    print(f"  등록자 {n_visitors}명, 임베딩 {n_embs}개\n")

    # 녹화 파일 처리 (큰 파일 우선)
    print("[3/3] 영상 분석 중...")
    videos = []
    for f in os.listdir(RECORDINGS_DIR):
        if f.endswith(".avi"):
            fp = os.path.join(RECORDINGS_DIR, f)
            videos.append((os.path.getsize(fp), fp))
    videos.sort(reverse=True)  # 큰 파일 먼저

    candidates = []
    for _, vpath in videos:
        candidates = process_video(vpath, face_app, yolo, matrix, norms, meta, candidates)
        print(f"    → 후보 {len(candidates)}개 수집")

    if not candidates:
        print("\n감지된 프레임이 없습니다.")
        return

    # 점수 상위 N개 선택
    candidates.sort(key=lambda c: c["score"], reverse=True)
    top = candidates[:MAX_CAPTURES]

    print(f"\n상위 {len(top)}개 선택:")
    for i, c in enumerate(top):
        overlay = draw_overlay(c["frame"], c["detections"])
        out_path = os.path.join(OUTPUT_DIR, f"demo_{i+1:02d}.jpg")
        cv2.imwrite(out_path, overlay, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"  #{i+1}: {c['video']} {c['timestamp']} — "
              f"사람 {c['n_people']}명, 얼굴 {c['n_faces']}개, "
              f"등록 {c['n_registered']}명 (점수 {c['score']})")

    print(f"\n완료! {len(top)}개 캡처 저장됨: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
