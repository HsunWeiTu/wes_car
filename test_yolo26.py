import torch
from ultralytics import YOLO

# 檢查 CUDA
print(f"CUDA Available: {torch.cuda.is_available()}")

# 載入 YOLO26 模型並強制指定到 GPU (device=0)
try:
    model = YOLO("yolo26n.pt")
    print("YOLO26 Model Loaded Successfully!")
    # 測試一個空矩陣推理，看會不會噴 CUDA 錯誤
    dummy_input = torch.zeros((1, 3, 640, 640)).cuda()
    model.to('cuda')
    print("GPU Memory Handshake: Success!")
except Exception as e:
    print(f"Error: {e}")