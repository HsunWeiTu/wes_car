#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool

class FrontOledDisplayNode(Node):
    def __init__(self):
        super().__init__('front_oled_display_node')
        self.get_logger().info('Initializing OLED display...')
        self.declare_parameter('battery_state_topic', 'battery_state')
        self.declare_parameter('gesture_enabled_topic', 'gesture_control_enabled')
        self.declare_parameter('battery_stale_timeout', 3.0)

        battery_state_topic = self.get_parameter('battery_state_topic').value
        gesture_enabled_topic = self.get_parameter('gesture_enabled_topic').value
        self.battery_stale_timeout = float(self.get_parameter('battery_stale_timeout').value)
        self.serial = None
        self.device = None
        self.font = self.load_font()
        self.battery_percentage = float('nan')
        self.is_charging = False
        self.gesture_enabled = False
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

        # 手勢開關狀態使用 latched QoS，讓後啟動也能收到最新狀態
        latched_qos = QoSProfile(depth=1)
        latched_qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        latched_qos.history = QoSHistoryPolicy.KEEP_LAST
        self.gesture_sub = self.create_subscription(
            Bool, gesture_enabled_topic, self.gesture_callback, latched_qos)

        self.display_timer = self.create_timer(1.0, self.update_display)
        self.update_display()

    def load_font(self):
        # 嘗試載入較大的 TrueType 字型讓電量趴數明顯，失敗則退回預設字型
        candidates = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, 24)
            except Exception:
                continue
        return ImageFont.load_default()

    def battery_callback(self, msg):
        self.battery_percentage = msg.percentage
        self.is_charging = (msg.power_supply_status == BatteryState.POWER_SUPPLY_STATUS_CHARGING)
        self.last_battery_time = self.get_clock().now()
        self.update_display()

    def gesture_callback(self, msg):
        self.gesture_enabled = msg.data
        self.update_display()

    def update_display(self):
        if self.device is None:
            return

        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")

            # 中央：電量趴數 (只顯示趴數，不顯示電壓)
            if self.is_battery_fresh() and not math.isnan(self.battery_percentage):
                text = f'{self.battery_percentage * 100:.0f}%'
            else:
                text = '--%'
            self.draw_centered_text(draw, text)

            # 手勢控車開啟 -> 左邊顯示讚手勢 icon
            if self.gesture_enabled:
                self.draw_thumbs_up(draw, 2, 6)

            # 充電中 -> 最右邊顯示閃電符號
            if self.is_charging:
                self.draw_lightning(draw, 116, 4)

    def draw_centered_text(self, draw, text):
        try:
            bbox = draw.textbbox((0, 0), text, font=self.font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except Exception:
            w, h = draw.textsize(text, font=self.font)
        x = (128 - w) // 2
        y = (32 - h) // 2
        draw.text((x, y), text, font=self.font, fill="white")

    def draw_thumbs_up(self, draw, x, y):
        # 簡易讚手勢 icon：拳頭 (方框) + 向上豎起的拇指
        # 拳頭 (四指握起)
        draw.rectangle([x, y + 10, x + 12, y + 22], outline="white", fill="black")
        # 拇指 (向上豎起)
        draw.rectangle([x + 2, y, x + 7, y + 11], outline="white", fill="black")
        # 手臂底線
        draw.line([x, y + 22, x + 12, y + 22], fill="white")

    def draw_lightning(self, draw, x, y):
        # 閃電符號 (充電中)
        bolt = [
            (x + 6, y),
            (x + 1, y + 12),
            (x + 5, y + 12),
            (x + 2, y + 24),
            (x + 10, y + 9),
            (x + 6, y + 9),
            (x + 9, y),
        ]
        draw.polygon(bolt, fill="white")

    def is_battery_fresh(self):
        if self.last_battery_time is None:
            return False
        if self.battery_stale_timeout <= 0.0:
            return True

        elapsed = self.get_clock().now() - self.last_battery_time
        return elapsed.nanoseconds <= self.battery_stale_timeout * 1_000_000_000

def main(args=None):
    rclpy.init(args=args)
    node = FrontOledDisplayNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
