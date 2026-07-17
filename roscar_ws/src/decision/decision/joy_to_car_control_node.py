#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
#from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from wes_car_interface.msg import CarControl

class JoyToCarControlNode(Node):
    def __init__(self):
        super().__init__('joy_to_car_control_node')
        self.declare_parameter('joy_topic', 'joy')
        self.declare_parameter('output_control_topic', '/car_movement_control')
        self.declare_parameter('axis_linear_x', 1)
        self.declare_parameter('axis_linear_y', 0)
        self.declare_parameter('axis_angular_z', 3)
        self.declare_parameter('deadzone', 0.01)

        joy_topic = self.get_parameter('joy_topic').value
        output_control_topic = self.get_parameter('output_control_topic').value
        self.axis_linear_x = int(self.get_parameter('axis_linear_x').value)
        self.axis_linear_y = int(self.get_parameter('axis_linear_y').value)
        self.axis_angular_z = int(self.get_parameter('axis_angular_z').value)
        self.deadzone = float(self.get_parameter('deadzone').value)
        
        # 建立訂閱者：接收搖桿訊號
        self.sub_joy = self.create_subscription(
            Joy, 
            joy_topic,
            self.joy_callback, 
            10
        )

        # 建立發布者：改為發布 CarControl 自定義訊息
        self.pub_control = self.create_publisher(
            CarControl, 
            output_control_topic,
            10
        )

        # 設定優先權常數 (可以根據需求調整)
        self.PRIORITY_LEVEL = 10 

    def joy_callback(self, msg):
        control_msg = CarControl()
        control_msg.header.stamp = self.get_clock().now().to_msg()
        control_msg.mode = 0

        if len(msg.axes) <= max(self.axis_linear_x, self.axis_linear_y, self.axis_angular_z):
            self.get_logger().warn('Joy message does not contain enough axes for configured mapping.')
            return

        # 讀取搖桿數值 (假設 Axes[1] 是前後, Axes[0] 是左右)
        forward_backward = msg.axes[self.axis_linear_x]  # 1.0 為前, -1.0 為後
        left_right = msg.axes[self.axis_linear_y]        # 1.0 為左, -1.0 為右
        cw_ccw = msg.axes[self.axis_angular_z]           # 1.0 為順時針, -1.0 為逆時針

        # 邏輯判斷：決定 command 與 speed
        # 我們設定一個死區 (Deadzone) 避免搖桿過於靈敏
        threshold = self.deadzone
        
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
    node = JoyToCarControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

