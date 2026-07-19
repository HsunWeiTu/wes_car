#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
#from geometry_msgs.msg import Twist
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool
from wes_car_interface.msg import CarControl

class JoyToCarControlNode(Node):
    def __init__(self):
        super().__init__('joy_to_car_control_node')
        self.declare_parameter('joy_topic', 'joy')
        self.declare_parameter('output_control_topic', '/car_movement_control')
        self.declare_parameter('gesture_enabled_topic', 'gesture_control_enabled')
        self.declare_parameter('axis_linear_x', 1)
        self.declare_parameter('axis_linear_y', 0)
        self.declare_parameter('axis_angular_z', 3)
        self.declare_parameter('deadzone', 0.01)
        # 搖桿推到底時對應的最大速度 (將正規化軸值 [-1,1] 轉成真實物理單位)
        self.declare_parameter('max_linear_speed', 0.5)   # [m/s]
        self.declare_parameter('max_angular_speed', 1.0)  # [rad/s]
        # 用哪一顆按鈕切換手勢控車 (buttons 陣列的索引)
        self.declare_parameter('gesture_toggle_button', 0)
        self.declare_parameter('gesture_control_default_enabled', False)

        joy_topic = self.get_parameter('joy_topic').value
        output_control_topic = self.get_parameter('output_control_topic').value
        gesture_enabled_topic = self.get_parameter('gesture_enabled_topic').value
        self.axis_linear_x = int(self.get_parameter('axis_linear_x').value)
        self.axis_linear_y = int(self.get_parameter('axis_linear_y').value)
        self.axis_angular_z = int(self.get_parameter('axis_angular_z').value)
        self.deadzone = float(self.get_parameter('deadzone').value)
        self.max_linear_speed = float(self.get_parameter('max_linear_speed').value)
        self.max_angular_speed = float(self.get_parameter('max_angular_speed').value)
        self.gesture_toggle_button = int(self.get_parameter('gesture_toggle_button').value)
        self.gesture_enabled = bool(self.get_parameter('gesture_control_default_enabled').value)
        self.prev_toggle_pressed = False
        
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

        # 手勢開關狀態：latched QoS，讓 OLED 與手勢節點後啟動也能收到
        latched_qos = QoSProfile(depth=1)
        latched_qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        latched_qos.history = QoSHistoryPolicy.KEEP_LAST
        self.pub_gesture_enabled = self.create_publisher(
            Bool, gesture_enabled_topic, latched_qos)
        self.publish_gesture_enabled()

        # 設定優先權常數 (可以根據需求調整)
        self.PRIORITY_LEVEL = 10 

    def handle_gesture_toggle(self, msg):
        # 邊緣觸發：按鈕從放開變成按下時切換一次
        if self.gesture_toggle_button >= len(msg.buttons):
            return
        pressed = msg.buttons[self.gesture_toggle_button] == 1
        if pressed and not self.prev_toggle_pressed:
            self.gesture_enabled = not self.gesture_enabled
            self.get_logger().info(
                f'手勢控車 -> {"開啟" if self.gesture_enabled else "關閉"}')
            self.publish_gesture_enabled()
        self.prev_toggle_pressed = pressed

    def publish_gesture_enabled(self):
        enabled_msg = Bool()
        enabled_msg.data = self.gesture_enabled
        self.pub_gesture_enabled.publish(enabled_msg)

    def joy_callback(self, msg):
        # 先處理手勢開關切換鈕
        self.handle_gesture_toggle(msg)

        control_msg = CarControl()
        control_msg.header.stamp = self.get_clock().now().to_msg()
        control_msg.mode = CarControl.MODE_MANUAL

        if len(msg.axes) <= max(self.axis_linear_x, self.axis_linear_y, self.axis_angular_z):
            self.get_logger().warn('Joy message does not contain enough axes for configured mapping.')
            return

        # 讀取搖桿正規化數值 [-1.0, 1.0] (假設 Axes[1] 是前後, Axes[0] 是左右)
        forward_backward = msg.axes[self.axis_linear_x]  # 1.0 為前, -1.0 為後
        left_right = msg.axes[self.axis_linear_y]        # 1.0 為左, -1.0 為右
        cw_ccw = msg.axes[self.axis_angular_z]           # 1.0 為逆時針, -1.0 為順時針

        # 死區 (Deadzone) 避免搖桿雜訊，超過門檻才乘上最大速度轉成真實物理單位
        threshold = self.deadzone

        # 正規化軸值 × 最大速度 -> speed_x/speed_y 為 [m/s]，rotate_z 為 [rad/s]
        if abs(forward_backward) > threshold:
            control_msg.speed_x = forward_backward * self.max_linear_speed
        if abs(left_right) > threshold:
            control_msg.speed_y = left_right * self.max_linear_speed
        if abs(cw_ccw) > threshold:
            control_msg.rotate_z = cw_ccw * self.max_angular_speed

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

