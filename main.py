import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import sys
import time
import csv
import cv2
from ultralytics import YOLO
from collections import defaultdict

# ========= 設定（必要に応じて変更） =========
SOURCE = "./videos/test video_2.mp4"   # カメラなら 0 / ファイルパス / RTSP など
CLASSES = [2,5,7]   # COCO:人=0, 自転車=1, 車=2, バイク=3, バス=5, トラック=7
MODEL = "./models/yolo11n.pt"        # 初回実行で自動DL
USE_GPU = True             # RTXがあれば True（Torch+CUDA必須）
IMG_SIZE = 960              # CPU時は 960→832→640 で調整
CONF = 0.25                 # 昼:0.25 / 夜:0.15 まで下げて拾い増し
IOU = 0.45                  # NMS閾値
TTL_SEC = 2.0               # 見失ってからID破棄までの秒数
WRITE_CSV = True
CSV_PATH = "gate_counts.csv"
# ==========================================

def put(img, s, org, scale=0.7, color=(220,220,220), th=1):
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0,0,0), th+2, cv2.LINE_AA)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, th, cv2.LINE_AA)

def main():
    global IMG_SIZE
    model = YOLO(MODEL)
    # device = 0 if USE_GPU else "cpu"
    device = "cpu"

    cap = cv2.VideoCapture(SOURCE if isinstance(SOURCE, (str,int)) else 0)
    if not cap.isOpened():
        print(f"[ERROR] ソースを開けませんでした: {SOURCE}", file=sys.stderr); sys.exit(1)

    ok, frame = cap.read()
    if not ok:
        print("[ERROR] 先頭フレームが読み取れませんでした。", file=sys.stderr); sys.exit(1)

    h, w = frame.shape[:2]
    # 左右 10% 内側に寄せた幅、縦方向は高さの45〜55%（中央バンド）
    #gate = [int(w*0.1), int(h*0.45), int(w*0.9), int(h*0.55)]  # x1,y1,x2,y2
    # 「横いっぱいの水平ゲート」が初期状態
    # gate = [0, int(h*0.4), w, int(h*0.6)]
    # 任意の幅の水平ゲート
    gate = [int(w*0.5), int(h*0.6), int(w*0.8), int(h*0.8)]

    # ID毎の状態
    counted = set()                # 既にカウントしたID
    last_seen = defaultdict(lambda: 0.0)  # 最終検出時刻
    inside_prev = defaultdict(lambda: False)  # 前フレームでゲート内だったか
    total = 0

    # CSV
    csvw = None
    if WRITE_CSV:
        f = open(CSV_PATH, "w", newline="", encoding="utf-8")
        csvw = csv.writer(f)
        csvw.writerow(["ts","id","cls","x","y","crossed"])

    t_prev = time.time(); fps = 0.0
    conf = CONF

    help_lines = [
        "[Q] Quit   [W/A/S/D] Move gate   [H/L] Thin/Thick   [R] Reset",
        "[N] Night mode (lower conf)   [G] GPU toggle   [Z] Size toggle",
        f"Classes: {CLASSES} (COCO)"
    ]


    while True:
        ok, frame = cap.read()
        if not ok: break

        # 推論（追跡）
        results = model.track(
            source=frame,
            imgsz=IMG_SIZE,
            device=device,
            conf=conf,
            iou=IOU,
            classes=CLASSES,
            tracker="bytetrack.yaml",
            persist=True,
            verbose=False,
            stream=False
        )

        now = time.time()
        dt = now - t_prev
        fps = 0.9*fps + 0.1*(1.0/max(dt,1e-6))
        t_prev = now

        # ゲート描画
        x1,y1,x2,y2 = gate
        cv2.rectangle(frame, (x1,y1), (x2,y2), (0,0,255), 2)
        put(frame, f"GATE y:{y1}-{y2}", (10, max(20,y1-8)), 0.7, (70,200,255))

        # 検出結果処理
        dets = []
        try:
            r = results[0]
            if r.boxes is not None and r.boxes.id is not None:
                for b in r.boxes:
                    xyxy = b.xyxy[0].tolist()    # [x1,y1,x2,y2]
                    tid  = int(b.id.item())      # Track ID
                    cls  = int(b.cls.item())
                    confb= float(b.conf.item())
                    dets.append((tid, cls, confb, xyxy))
        except Exception as e:
            # まれに追跡が返らないフレームがある
            dets = []

        # IDごとにゲート通過判定
        for (tid, cls, confb, (bx1,by1,bx2,by2)) in dets:
            cx = int((bx1+bx2)/2); cy = int((by1+by2)/2)
            last_seen[tid] = now

            inside = (y1 <= cy <= y2) and (x1 <= cx <= x2)
            was_inside = inside_prev[tid]

            # 外→内→外 を 1カウントとみなすシンプル判定
            crossed = False
            if was_inside and not inside and tid not in counted:
                crossed = True
                counted.add(tid)
                total += 1

            inside_prev[tid] = inside

            # 可視化
            color = (0,255,0) if not tid in counted else (128,128,128)
            cv2.rectangle(frame, (int(bx1),int(by1)), (int(bx2),int(by2)), color, 2)
            put(frame, f"ID:{tid} C{cls} {confb:.2f}", (int(bx1), max(15,int(by1)-6)), 0.55, (200,255,200))
            cv2.circle(frame, (cx,cy), 3, (255,255,255), -1)

            if csvw:
                csvw.writerow([f"{now:.3f}", tid, cls, cx, cy, int(crossed)])

        # TTLで古いIDを破棄
        to_del = [tid for tid,t in last_seen.items() if now - t > TTL_SEC]
        for tid in to_del:
            last_seen.pop(tid, None)
            inside_prev.pop(tid, None)
            # counted は保持（重複カウント防止）

        # HUD
        put(frame, f"TOTAL: {total}", (10, 24), 0.9, (50,255,50), 2)
        put(frame, f"FPS: {fps:5.1f}  size:{IMG_SIZE}  conf:{conf:.2f}  device:{'cuda' if device==0 else 'cpu'}",
            (10, 50), 0.7, (200,200,255))

        for i, line in enumerate(help_lines):
            put(frame, line, (10, h-10 - 20*(len(help_lines)-1-i)), 0.55, (220,220,220))

        cv2.imshow("YOLO11n Gate Counter", frame)
        k = cv2.waitKey(1) & 0xFF

        if k in (ord('q'), 27):
            break
        elif k == ord('n'):   # 夜モード：confを下げる/戻す
            conf = 0.15 if abs(conf-0.25)<1e-6 else 0.25
        elif k == ord('g'):   # GPUトグル（次フレームから反映）
            device = 0 if device=="cpu" else "cpu"
        elif k == ord('z'):   # 画像サイズトグル
            IMG_SEQ = [640, 832, 960, 1280]
            try:
                idx = IMG_SEQ.index(IMG_SIZE)
                IMG_SIZE = IMG_SEQ[(idx+1)%len(IMG_SEQ)]
            except ValueError:
                IMG_SIZE = 960
        elif k == ord('r'):   # カウンタ/状態リセット
            total = 0; counted.clear(); inside_prev.clear(); last_seen.clear()
        elif k == ord('w'):  # ↑
            gate[1] = max(0, gate[1]-5); gate[3] = max(gate[1]+10, gate[3]-5)
        elif k == ord('s'):  # ↓
            gate[3] = min(h-1, gate[3]+5); gate[1] = min(gate[3]-10, gate[1]+5)
        elif k == ord('a'):  # ←
            gate[0] = max(0, gate[0]-5); gate[2] = max(gate[0]+10, gate[2]-5)
        elif k == ord('d'):  # →
            gate[2] = min(w-1, gate[2]+5); gate[0] = min(gate[2]-10, gate[0]+5)
        elif k == ord('h'):  # 厚み薄く
            if gate[3]-gate[1] > 12: gate[3] -= 3
        elif k == ord('l'):  # 厚み厚く
            if gate[3] < h-1: gate[3] += 3

    if csvw: csvw.__self__.close()  # file close
    cap.release()
    cv2.destroyAllWindows()



    

if __name__ == "__main__":
    if len(os.sys.argv) >= 2:
        SOURCE = os.sys.argv[1]
    main()