#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
#from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from wes_car_interface.msg import CarControl

class Teleop(Node):
    def __init__(self):
        super().__init__('joy_to_car_control_node')
        
        # 建立訂閱者：接收搖桿訊號
        self.sub_joy = self.create_subscription(
            Joy, 
            'joy', 
            self.joy_callback, 
            10
        )

        # 建立發布者：改為發布 CarControl 自定義訊息
        self.pub_control = self.create_publisher(
            CarControl, 
            '/car_movement_control', 
            10
        )

        # 設定優先權常數 (可以根據需求調整)
        self.PRIORITY_LEVEL = 10 

    def joy_callback(self, msg):
        control_msg = CarControl()
        control_msg.header.stamp = self.get_clock().now().to_msg()

        # 讀取搖桿數值 (假設 Axes[1] 是前後, Axes[0] 是左右)
        forward_backward = msg.axes[1]  # 1.0 為前, -1.0 為後
        left_right = msg.axes[0]        # 1.0 為左, -1.0 為右
        cw_ccw = msg.axes[3]           # 1.0 為順時針, -1.0 為逆時針

        # 邏輯判斷：決定 command 與 speed
        # 我們設定一個死區 (Deadzone) 避免搖桿過於靈敏
        threshold = 0.01
        
        # 優先判斷前後，再判斷左右 (你也可以根據需求修改判斷優先級)
        if abs(forward_backward) > threshold:
            control_msg.speed_x = forward_backward
        if abs(left_right) > threshold:
            control_msg.speed_y = left_right
        if abs(cw_ccw) > threshold:
            control_msg.rotate_z = cw_ccw

        # 發布訊息
        self.pub_control.publish(control_msg)

def main(args=None):
    rclpy.init(args=args)
    node = Teleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

