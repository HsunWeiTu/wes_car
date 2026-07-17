import rclpy
from rclpy.node import Node
from wes_car_interface.msg import Gesture, CarControl

class GestureToCarControlNode(Node):
    def __init__(self):
        super().__init__('gesture_to_car_control_node')
        self.declare_parameter('input_gesture_topic', 'raw_gesture_data')
        self.declare_parameter('output_control_topic', '/car_movement_control')
        self.declare_parameter('xy_threshold', 0.1)
        self.declare_parameter('z_threshold', -0.07)
        self.declare_parameter('command_speed', 1.0)

        input_gesture_topic = self.get_parameter('input_gesture_topic').value
        output_control_topic = self.get_parameter('output_control_topic').value
        self.xy_threshold = float(self.get_parameter('xy_threshold').value)
        self.z_threshold = float(self.get_parameter('z_threshold').value)
        self.command_speed = float(self.get_parameter('command_speed').value)
        self.last_command_label = None

        self.subscription = self.create_subscription(
            Gesture, input_gesture_topic, self.listener_callback, 10)
        self.publisher_ = self.create_publisher(CarControl, output_control_topic, 10)

        self.get_logger().info('決策層已啟動：鏡像模式 (指右->左移, 指左->右移)')

    def listener_callback(self, msg):
        control_msg = CarControl()
        control_msg.header.stamp = self.get_clock().now().to_msg()
        control_msg.mode = 1

        # --- 向量計算：指尖 - 指根 (V = Tip - MCP) ---
        # 食指向量 (x, y, z)
        idx_vx = msg.index_tip.x - msg.index_mcp.x
        idx_vy = msg.index_tip.y - msg.index_mcp.y
        idx_vz = msg.index_tip.z - msg.index_mcp.z
        
        # 中指向量 (x, y, z)
        mid_vx = msg.middle_tip.x - msg.middle_mcp.x
        mid_vy = msg.middle_tip.y - msg.middle_mcp.y
        mid_vz = msg.middle_tip.z - msg.middle_mcp.z

        # --- 門檻值設定 ---
        threshold = self.xy_threshold
        z_threshold = self.z_threshold # Z 軸負值代表指尖比指根更靠近鏡頭

        # --- 判斷邏輯 ---
        
        # 1. 向上指 -> 前進 (1)
        if idx_vy < -threshold and mid_vy < -threshold:
            control_msg.speed_x = self.command_speed
            command_label = '前進 (UP)'

        # 2. 指向鏡頭 -> 後退 (2) 
        # 這裡判斷 Z 軸的深度差，指尖明顯突出到掌心前面
        elif idx_vz < z_threshold and mid_vz < z_threshold:
            control_msg.speed_x = -self.command_speed
            command_label = '後退 (POINTING AT CAMERA)'

        # 3. 指向左手邊 -> 車子右移 (4) [鏡像]
        elif idx_vx < -threshold and mid_vx < -threshold:
            control_msg.speed_y = self.command_speed
            command_label = '右移 (USER LEFT -> CAR RIGHT)'

        # 4. 指向右手邊 -> 車子左移 (3) [鏡像]
        elif idx_vx > threshold and mid_vx > threshold:
            control_msg.speed_y = -self.command_speed
            command_label = '左移 (USER RIGHT -> CAR LEFT)'

        

        else:
            control_msg.speed_x = 0.0
            control_msg.speed_y = 0.0
            control_msg.rotate_z = 0.0
            command_label = '停止'

        if command_label != self.last_command_label:
            self.get_logger().info(command_label)
            self.last_command_label = command_label

        self.publisher_.publish(control_msg)

def main(args=None):
    rclpy.init(args=args)
    node = GestureToCarControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()