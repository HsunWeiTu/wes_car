#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

class OledDisplay(Node):
    def __init__(self):
        super().__init__('oled_display')
        self.get_logger().info('Initializing OLED display...')
        self.serial = None
        self.device = None

        # Initialize I2C interface and OLED device
        try:
            self.serial = i2c(port=7, address=0x3C)
            self.device = ssd1306(self.serial, width=128, height=32)
            self.get_logger().info('OLED display initialized successfully.')
        except Exception as e:
            self.get_logger().error(f"Error initializing I2C interface: {e}")
            return
        
        self.display_text("Wes Car")
        # Load a font
        self.font = ImageFont.load_default()     
        
    def display_text(self, text):
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="white", fill="black")
            draw.text((35, 10), text, fill="white")

def main(args=None):
    rclpy.init(args=args)
    node = OledDisplay()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
