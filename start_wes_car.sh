#!/bin/bash

# 1. 優先進入最強 AI 虛擬環境
# 這樣後續啟動的 Python 節點都會使用 mp_env 裡的 MediaPipe + CUDA OpenCV
echo "🚀 載入 mp_env 虛擬環境..."
source /home/wes/mp_env/bin/activate

# 2. 載入 ROS 2 核心與所有工作空間
echo "📦 載入 ROS 2 與工作空間環境..."
source /opt/ros/humble/setup.bash
source /home/wes/ascam_ros2_ws/install/setup.bash
source /home/wes/roscar_ws/install/setup.bash

# 3. 自動給串口權限 (STM32 Bridge 需要)
echo "🔒 設定串口 /dev/ttyUSB0 權限..."
sudo chmod 666 /dev/ttyUSB0 || true

# 4. (選配) 開啟風扇與噴發效能
# 既然要跑 CUDA，建議把 Jetson 效能拉滿
# sudo jetson_clocks

# 5. 一鍵啟動 Bringup
echo "🏎️  小車出動！啟動整合啟動檔..."
ros2 launch wes_car_bring_up bring_up.launch.py