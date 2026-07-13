# CarControl.msg
std_msgs/Header header
#int32 command    # 0:停止, 1:左移, 2:右移, 3:前進, 4:後退, 5:順時針旋轉, 6:逆時針旋轉
int32 mode       # 0:manual 1:gesture 2:navigate
float32 speed_x
float32 speed_y
float32 rotate_z