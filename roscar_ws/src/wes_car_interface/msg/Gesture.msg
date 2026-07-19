# Gesture.msg
# 單一隻手的 MediaPipe 手部關鍵點資料
std_msgs/Header header

# MediaPipe 21 點索引常數 (landmarks 陣列的 index)
uint8 WRIST=0
uint8 THUMB_CMC=1
uint8 THUMB_MCP=2
uint8 THUMB_IP=3
uint8 THUMB_TIP=4
uint8 INDEX_MCP=5
uint8 INDEX_PIP=6
uint8 INDEX_DIP=7
uint8 INDEX_TIP=8
uint8 MIDDLE_MCP=9
uint8 MIDDLE_PIP=10
uint8 MIDDLE_DIP=11
uint8 MIDDLE_TIP=12
uint8 RING_MCP=13
uint8 RING_PIP=14
uint8 RING_DIP=15
uint8 RING_TIP=16
uint8 PINKY_MCP=17
uint8 PINKY_PIP=18
uint8 PINKY_DIP=19
uint8 PINKY_TIP=20

# 完整 21 點手部關鍵點 (index 對應上方常數)，座標為 MediaPipe 正規化值 (0~1，z 為相對深度)
# 用陣列而非具名欄位，之後要用到任何新關節都不必修改訊息或重新編譯
geometry_msgs/Point[] landmarks

# 左右手 ("Left" / "Right") 與偵測信心分數 (0~1)
string handedness
float32 score
