#!/usr/bin/env python3
import select
import sys
import termios
import tty

import rclpy
from rclpy.node import Node

from interface.msg import CarControl


DEFAULT_LINEAR_SPEED = 0.4
DEFAULT_ANGULAR_SPEED = 1.0


class KeyboardToCarControlNode(Node):
    def __init__(self):
        super().__init__('keyboard_to_car_control_node')
        self.declare_parameter('output_control_topic', '/car_movement_control')
        self.declare_parameter('linear_speed', DEFAULT_LINEAR_SPEED)
        self.declare_parameter('angular_speed', DEFAULT_ANGULAR_SPEED)
        self.declare_parameter('publish_rate', 20.0)

        output_control_topic = self.get_parameter('output_control_topic').value
        self.linear_speed = float(self.get_parameter('linear_speed').value)
        self.angular_speed = float(self.get_parameter('angular_speed').value)
        publish_rate = max(float(self.get_parameter('publish_rate').value), 1.0)
        self.key_timeout = 1.0 / publish_rate

        self.bindings = {
            'w': (self.linear_speed, 0.0, 0.0),
            's': (-self.linear_speed, 0.0, 0.0),
            'a': (0.0, self.linear_speed, 0.0),
            'd': (0.0, -self.linear_speed, 0.0),
            'q': (0.0, 0.0, self.angular_speed),
            'e': (0.0, 0.0, -self.angular_speed),
        }
        self.stop_keys = (' ', 'k')
        self.instructions = self.build_instructions()

        self.speed_x = 0.0
        self.speed_y = 0.0
        self.rotate_z = 0.0
        self.publisher_ = self.create_publisher(CarControl, output_control_topic, 10)
        self.terminal_settings = termios.tcgetattr(sys.stdin)
        self.timer = self.create_timer(self.key_timeout, self.poll_keyboard_and_publish)

        self.get_logger().info('鍵盤控制已啟動，屬於手動控制優先層。')
        print(self.instructions)

    def build_instructions(self):
        return """\
============================================
 Wes Car 鍵盤控制（手動優先）
--------------------------------------------
        W 前進
   A 左移   S 後退   D 右移
        Q 逆時針   E 順時針
   空白 / K = 停止      Ctrl-C = 離開
--------------------------------------------
 線速度 %.2f m/s   角速度 %.2f rad/s
============================================""" % (self.linear_speed, self.angular_speed)

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        ready, _, _ = select.select([sys.stdin], [], [], self.key_timeout)
        key = sys.stdin.read(1) if ready else ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.terminal_settings)
        return key

    def poll_keyboard_and_publish(self):
        key = self.get_key()
        if key:
            lower = key.lower()
            if lower in self.bindings:
                self.speed_x, self.speed_y, self.rotate_z = self.bindings[lower]
            elif key in self.stop_keys:
                self.stop_motion()
            elif key == '\x03':
                raise KeyboardInterrupt

        control_msg = CarControl()
        control_msg.header.stamp = self.get_clock().now().to_msg()
        control_msg.mode = CarControl.MODE_MANUAL
        control_msg.speed_x = self.speed_x
        control_msg.speed_y = self.speed_y
        control_msg.rotate_z = self.rotate_z
        self.publisher_.publish(control_msg)

    def stop_motion(self):
        self.speed_x = 0.0
        self.speed_y = 0.0
        self.rotate_z = 0.0

    def destroy_node(self):
        self.stop_motion()
        stop_msg = CarControl()
        stop_msg.header.stamp = self.get_clock().now().to_msg()
        stop_msg.mode = CarControl.MODE_MANUAL
        self.publisher_.publish(stop_msg)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.terminal_settings)
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardToCarControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()