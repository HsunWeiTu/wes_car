import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from wes_car_interface.msg import CarControl

class CarControlToCmdVelNode(Node):
    def __init__(self):
        super().__init__('car_control_to_cmd_vel_node')
        self.declare_parameter('input_control_topic', '/car_movement_control')
        self.declare_parameter('output_cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('max_speed_x', 1.0)
        self.declare_parameter('max_speed_y', 1.0)
        self.declare_parameter('max_rotate_z', 1.0)
        self.declare_parameter('command_timeout', 0.5)
        self.declare_parameter('publish_rate', 20.0)

        input_control_topic = self.get_parameter('input_control_topic').value
        output_cmd_vel_topic = self.get_parameter('output_cmd_vel_topic').value
        self.max_speed_x = float(self.get_parameter('max_speed_x').value)
        self.max_speed_y = float(self.get_parameter('max_speed_y').value)
        self.max_rotate_z = float(self.get_parameter('max_rotate_z').value)
        self.command_timeout = float(self.get_parameter('command_timeout').value)
        publish_rate = max(float(self.get_parameter('publish_rate').value), 1.0)
        self.last_command_time = None
        self.last_twist = Twist()
        
        # 訂閱決策層指令
        self.subscription = self.create_subscription(
            CarControl, input_control_topic, self.command_callback, 10)
        
        # 發布底盤速度指令
        self.cmd_vel_pub = self.create_publisher(Twist, output_cmd_vel_topic, 10)
        self.timer = self.create_timer(1.0 / publish_rate, self.publish_cmd_vel)
        
        self.get_logger().info('處理層 (Controller) 已啟動：等待接收 CarControl 指令...')

    def command_callback(self, msg):
        twist = Twist()

        # --- 根據指令碼進行映射 ---
        twist.linear.x = self.clamp(msg.speed_x, -self.max_speed_x, self.max_speed_x)
        twist.linear.y = self.clamp(msg.speed_y, -self.max_speed_y, self.max_speed_y)
        twist.angular.z = self.clamp(msg.rotate_z, -self.max_rotate_z, self.max_rotate_z)
        self.last_twist = twist
        self.last_command_time = self.get_clock().now()

    def publish_cmd_vel(self):
        twist = self.last_twist
        if self.last_command_time is None or self.is_command_timed_out():
            twist = Twist()

        self.cmd_vel_pub.publish(twist)

    def is_command_timed_out(self):
        if self.command_timeout <= 0.0:
            return False

        elapsed = self.get_clock().now() - self.last_command_time
        return elapsed.nanoseconds > self.command_timeout * 1_000_000_000

    @staticmethod
    def clamp(value, min_value, max_value):
        return max(min(value, max_value), min_value)

def main(args=None):
    rclpy.init(args=args)
    node = CarControlToCmdVelNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()