import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy
from std_msgs.msg import Bool
from wes_car_interface.msg import Gesture, CarControl


class GestureToCarControlNode(Node):
    def __init__(self):
        super().__init__('gesture_to_car_control_node')
        self.declare_parameter('input_gesture_topic', 'raw_gesture_data')
        self.declare_parameter('output_control_topic', '/car_movement_control')
        self.declare_parameter('enabled_topic', 'gesture_control_enabled')
        # 拇指方向的判斷門檻 (拇指指尖相對指根的位移量)
        self.declare_parameter('thumb_threshold', 0.06)
        # 四指握拳判斷的容忍係數：指尖到手腕距離 < PIP 到手腕距離 * ratio 視為彎曲
        self.declare_parameter('curl_ratio', 1.0)
        # 拇指是否伸出的判斷係數：拇指指尖到手腕距離 > 拇指指根到手腕距離 * ratio 視為伸出
        self.declare_parameter('thumb_extend_ratio', 1.1)
        # 手勢觸發時的行駛線速度 (真實物理單位)
        self.declare_parameter('command_linear_speed', 0.3)  # [m/s]
        self.declare_parameter('default_enabled', False)

        input_gesture_topic = self.get_parameter('input_gesture_topic').value
        output_control_topic = self.get_parameter('output_control_topic').value
        enabled_topic = self.get_parameter('enabled_topic').value
        self.thumb_threshold = float(self.get_parameter('thumb_threshold').value)
        self.curl_ratio = float(self.get_parameter('curl_ratio').value)
        self.thumb_extend_ratio = float(self.get_parameter('thumb_extend_ratio').value)
        self.command_linear_speed = float(self.get_parameter('command_linear_speed').value)
        self.enabled = bool(self.get_parameter('default_enabled').value)
        self.last_command_label = None

        self.subscription = self.create_subscription(
            Gesture, input_gesture_topic, self.listener_callback, 10)
        self.publisher_ = self.create_publisher(CarControl, output_control_topic, 10)

        # 手勢開關狀態使用 latched QoS，讓後啟動的節點也能收到最新狀態
        latched_qos = QoSProfile(depth=1)
        latched_qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        latched_qos.history = QoSHistoryPolicy.KEEP_LAST
        self.enabled_sub = self.create_subscription(
            Bool, enabled_topic, self.enabled_callback, latched_qos)

        self.get_logger().info(
            f'手勢決策層已啟動 (拇指比讚模式)，初始狀態: {"開啟" if self.enabled else "關閉"}')

    def enabled_callback(self, msg):
        if msg.data != self.enabled:
            self.enabled = msg.data
            self.get_logger().info(f'手勢控車 -> {"開啟" if self.enabled else "關閉"}')
            if not self.enabled:
                self.publish_stop()

    def listener_callback(self, msg):
        # 開關關閉時完全不送動作，並持續維持停止
        if not self.enabled:
            self.publish_stop()
            return

        # 防呆：landmarks 必須是完整 21 點
        if len(msg.landmarks) < 21:
            self.publish_stop(label='手部關鍵點不完整')
            return

        # 先確認是「四指握拳 + 拇指伸出」的比讚手勢，否則視為無效手勢
        if not self.is_thumb_gesture(msg):
            self.publish_stop(label='無效手勢 (需四指握拳+拇指伸出)')
            return

        control_msg = CarControl()
        control_msg.header.stamp = self.get_clock().now().to_msg()
        control_msg.mode = CarControl.MODE_GESTURE

        # 拇指方向向量 (指尖 - 指根)
        thumb_tip = msg.landmarks[Gesture.THUMB_TIP]
        thumb_mcp = msg.landmarks[Gesture.THUMB_MCP]
        thumb_vx = thumb_tip.x - thumb_mcp.x
        thumb_vy = thumb_tip.y - thumb_mcp.y

        threshold = self.thumb_threshold

        # 判斷拇指主要指向：比較水平與垂直位移，取較大者
        if abs(thumb_vy) >= abs(thumb_vx):
            # 垂直方向為主
            if thumb_vy < -threshold:
                # 讚 (拇指朝上) -> 前進
                control_msg.speed_x = self.command_linear_speed
                command_label = '前進 (THUMB UP)'
            elif thumb_vy > threshold:
                # 倒讚 (拇指朝下) -> 倒車
                control_msg.speed_x = -self.command_linear_speed
                command_label = '倒車 (THUMB DOWN)'
            else:
                command_label = '停止'
        else:
            # 水平方向為主 (鏡像：使用者指左 -> 車右)
            if thumb_vx < -threshold:
                control_msg.speed_y = self.command_linear_speed
                command_label = '右移 (USER LEFT -> CAR RIGHT)'
            elif thumb_vx > threshold:
                control_msg.speed_y = -self.command_linear_speed
                command_label = '左移 (USER RIGHT -> CAR LEFT)'
            else:
                command_label = '停止'

        self.log_once(command_label)
        self.publisher_.publish(control_msg)

    def is_thumb_gesture(self, msg):
        wrist = msg.landmarks[Gesture.WRIST]

        # 四指 (食指/中指/無名指/小指) 都要握起來
        fingers = [
            (Gesture.INDEX_TIP, Gesture.INDEX_PIP),
            (Gesture.MIDDLE_TIP, Gesture.MIDDLE_PIP),
            (Gesture.RING_TIP, Gesture.RING_PIP),
            (Gesture.PINKY_TIP, Gesture.PINKY_PIP),
        ]
        for tip_idx, pip_idx in fingers:
            if not self.is_finger_curled(msg.landmarks[tip_idx], msg.landmarks[pip_idx], wrist):
                return False

        # 拇指要伸出來 (指尖離手腕比指根離手腕更遠)
        return self.is_thumb_extended(
            msg.landmarks[Gesture.THUMB_TIP], msg.landmarks[Gesture.THUMB_MCP], wrist)

    def is_finger_curled(self, tip, pip, wrist):
        # 彎曲：指尖到手腕的距離 <= PIP 到手腕的距離 * curl_ratio
        # 伸直時指尖遠離手腕，彎曲時指尖收回靠近手腕
        return self.dist(tip, wrist) <= self.dist(pip, wrist) * self.curl_ratio

    def is_thumb_extended(self, thumb_tip, thumb_mcp, wrist):
        return self.dist(thumb_tip, wrist) >= self.dist(thumb_mcp, wrist) * self.thumb_extend_ratio

    @staticmethod
    def dist(a, b):
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)

    def publish_stop(self, label='停止'):
        control_msg = CarControl()
        control_msg.header.stamp = self.get_clock().now().to_msg()
        control_msg.mode = 1
        control_msg.speed_x = 0.0
        control_msg.speed_y = 0.0
        control_msg.rotate_z = 0.0
        self.log_once(label)
        self.publisher_.publish(control_msg)

    def log_once(self, label):
        if label != self.last_command_label:
            self.get_logger().info(label)
            self.last_command_label = label


def main(args=None):
    rclpy.init(args=args)
    node = GestureToCarControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()