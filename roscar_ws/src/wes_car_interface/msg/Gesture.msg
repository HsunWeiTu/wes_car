# Gesture.msg
std_msgs/Header header

# 掌心位置 (取第 9 號點 MCP 或第 0 號點 WRIST)
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
