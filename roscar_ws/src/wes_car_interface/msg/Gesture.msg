# Gesture.msg
std_msgs/Header header

# 手腕 (WRIST: 0)，作為判斷手指彎曲與拇指方向的穩定參考點
geometry_msgs/Point wrist

# 掌心位置 (取第 9 號點 MCP)
geometry_msgs/Point palm_center

# 指尖座標 (Tip: 4, 8, 12, 16, 20)
geometry_msgs/Point thumb_tip
geometry_msgs/Point index_tip
geometry_msgs/Point middle_tip
geometry_msgs/Point ring_tip
geometry_msgs/Point pinky_tip

# 指根座標 (MCP: 2, 5, 9, 13, 17)
# 註：拇指是用 MCP (2)，其餘四指也是 MCP
geometry_msgs/Point thumb_mcp
geometry_msgs/Point index_mcp
geometry_msgs/Point middle_mcp
geometry_msgs/Point ring_mcp
geometry_msgs/Point pinky_mcp

# 近端指節座標 (PIP: 6, 10, 14, 18)
# 用於判斷四指是否握起來 (指尖比 PIP 更靠近手腕代表彎曲)
geometry_msgs/Point index_pip
geometry_msgs/Point middle_pip
geometry_msgs/Point ring_pip
geometry_msgs/Point pinky_pip
