#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont
from sensor_msgs.msg import BatteryState

class FrontOledDisplayNode(Node):
    def __init__(self):
        super().__init__('front_oled_display_node')
        self.get_logger().info('Initializing OLED display...')
        self.declare_parameter('battery_state_topic', 'battery_state')
        self.declare_parameter('battery_stale_timeout', 3.0)

        battery_state_topic = self.get_parameter('battery_state_topic').value
        self.battery_stale_timeout = float(self.get_parameter('battery_stale_timeout').value)
        self.serial = None
        self.device = None
        self.font = ImageFont.load_default()
        self.battery_voltage = None
        self.battery_percentage = float('nan')
        self.last_battery_time = None

        # Initialize I2C interface and OLED device
        try:
            self.serial = i2c(port=7, address=0x3C)
            self.device = ssd1306(self.serial, width=128, height=32)
            self.get_logger().info('OLED display initialized successfully.')
        except Exception as e:
            self.get_logger().error(f"Error initializing I2C interface: {e}")
            return

        self.battery_sub = self.create_subscription(
            BatteryState, battery_state_topic, self.battery_callback, 10)
        self.display_timer = self.create_timer(1.0, self.update_display)
        self.update_display()

    def battery_callback(self, msg):
        self.battery_voltage = msg.voltage
        self.battery_percentage = msg.percentage
        self.last_battery_time = self.get_clock().now()
        self.update_display()

    def update_display(self):
        if self.device is None:
            return

        lines = ['Wes Car']
        if self.is_battery_fresh():
            lines.append(f'BAT {self.battery_voltage:.1f}V')
            if not math.isnan(self.battery_percentage):
                lines.append(f'{self.battery_percentage * 100:.0f}%')
        else:
            lines.append('BAT waiting')

        self.display_lines(lines)

    def is_battery_fresh(self):
        if self.battery_voltage is None or self.last_battery_time is None:
            return False
        if self.battery_stale_timeout <= 0.0:
            return True

        elapsed = self.get_clock().now() - self.last_battery_time
        return elapsed.nanoseconds <= self.battery_stale_timeout * 1_000_000_000

    def display_lines(self, lines):
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="white", fill="black")
            for index, line in enumerate(lines[:3]):
                draw.text((0, index * 11), line, font=self.font, fill="white")

def main(args=None):
    rclpy.init(args=args)
    node = FrontOledDisplayNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
