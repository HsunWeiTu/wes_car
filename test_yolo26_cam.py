import cv2
from ultralytics import YOLO
import time

# 1. 載入 YOLO26 奈米版 (最適合 Orin Nano 的即時模型)
model = YOLO("yolo26n.pt") 

# 2. 開啟相機並強制使用 V4L2 引擎
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

# 3. 根據 hp60c.launch.py 設定精準參數
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 25)  # 關鍵：這是你 Launch 檔設定的數值

# 4. 檢查是否成功開啟
if not cap.isOpened():
    print("無法開啟 Nuwa-HP60C，請檢查 USB 連線")
    exit()

print("Nuwa-HP60C 啟動成功 (640x480 @ 25FPS)")
print("正在執行 YOLO26 推理... 按 'q' 結束")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 5. YOLO26 推理：device=0 (GPU), half=True (FP16 加速)
    # 這裡我們用 predict 模式，它在 YOLO26 中已經移除了 NMS 延遲
    results = model.predict(frame, device=0, half=True, verbose=False)
    
    # 取得渲染後的影像
    annotated_frame = results[0].plot()
    
    # 顯示 FPS
    cv2.imshow("Wes Jetson - YOLO26 Gesture Lab", annotated_frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()