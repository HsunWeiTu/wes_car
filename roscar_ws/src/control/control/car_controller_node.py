import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from wes_car_interface.msg import CarControl

class WesCarController(Node):
    def __init__(self):
        super().__init__('car_controller_node')
        
        # 訂閱決策層指令
        self.subscription = self.create_subscription(
            CarControl, '/car_movement_control', self.command_callback, 10)
        
        # 發布底盤速度指令
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.get_logger().info('處理層 (Controller) 已啟動：等待接收 CarControl 指令...')

    def command_callback(self, msg):
        twist = Twist()

        # --- 根據指令碼進行映射 ---
        twist.linear.x = msg.speed_x           
        twist.linear.y = msg.speed_y
        twist.angular.z = msg.rotate_z

        # 發布到 ROS2 標準底盤接口
        self.cmd_vel_pub.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = WesCarController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()