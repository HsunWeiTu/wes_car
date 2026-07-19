# CarControl.msg
# 各控制來源 (joy / 手勢 / 導航) 統一發布的抽象控制指令
std_msgs/Header header

# 指令來源模式 (mode)：供下游做多來源優先權仲裁
int32 MODE_MANUAL=0
int32 MODE_GESTURE=1
int32 MODE_NAVIGATE=2
int32 mode

# 速度指令，使用真實物理單位 (與 ROS 標準 geometry_msgs/Twist 一致)
# speed_x:  前後線速度   [m/s]   (+前 / -後)
# speed_y:  左右平移線速度 [m/s]   (+左 / -右)
# rotate_z: 旋轉角速度   [rad/s] (+逆時針 / -順時針)
float32 speed_x
float32 speed_y
float32 rotate_z