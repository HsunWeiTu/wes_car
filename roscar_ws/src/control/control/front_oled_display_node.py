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
    LOW_BATTERY_THRESHOLD = 0.20  # 20% 以下視為低電量，需閃爍提醒充電

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
        self.gesture_enabled = False
        self.last_battery_time = None
        self.blink_on = True

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

        # 0.5s 週期讓低電量電池 icon 能閃爍提醒
        self.display_timer = self.create_timer(0.5, self.on_timer)
        self.update_display()

    def load_font(self):
        # 嘗試載入較大的 TrueType 字型讓電量趴數明顯，失敗則退回預設字型
        candidates = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, 14)
            except Exception:
                continue
        return ImageFont.load_default()

    def battery_callback(self, msg):
        self.battery_percentage = msg.percentage
        self.last_battery_time = self.get_clock().now()
        self.update_display()

    def gesture_callback(self, msg):
        self.gesture_enabled = msg.data
        self.update_display()

    def on_timer(self):
        # 低電量時切換閃爍狀態，其餘情況維持常亮
        if self.is_low_battery():
            self.blink_on = not self.blink_on
        else:
            self.blink_on = True
        self.update_display()

    def update_display(self):
        if self.device is None:
            return

        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")

            # 上排：Wes Car 字樣
            draw.text((2, 0), 'Wes Car', font=self.font, fill="white")

            # 手勢控車開啟 -> 右側顯示讚手勢 icon
            if self.gesture_enabled:
                self.draw_thumbs_up(draw, 112, 6)

            # 下排：四格電池 icon (低電量時整顆閃爍)
            self.draw_battery(draw, 2, 18, 40, 12)

    def draw_battery(self, draw, x, y, w, h):
        # 低電量閃爍：blink_on 為 False 的半個週期整顆電池不畫
        if self.is_low_battery() and not self.blink_on:
            return

        # 電池外框
        draw.rectangle([x, y, x + w, y + h], outline="white", fill="black")
        # 正極凸點
        nub_h = max(h // 2, 4)
        draw.rectangle(
            [x + w + 1, y + (h - nub_h) // 2, x + w + 3, y + (h + nub_h) // 2],
            outline="white", fill="white")

        # 內部四格，依電量填滿；低電量 (<=20%) 或無資料時為空白
        bars = self.battery_bar_count()
        if bars <= 0:
            return

        segments = 4
        gap = 1
        inner_x = x + 2
        inner_y = y + 2
        inner_w = w - 4
        inner_h = h - 4
        seg_w = (inner_w - gap * (segments - 1)) / segments
        for i in range(bars):
            bx = inner_x + i * (seg_w + gap)
            draw.rectangle(
                [bx, inner_y, bx + seg_w, inner_y + inner_h],
                fill="white")

    def battery_bar_count(self):
        # 回傳應點亮的格數 (0~4)；資料失效或低電量回傳 0
        if not self.is_battery_fresh() or math.isnan(self.battery_percentage):
            return 0
        pct = self.battery_percentage
        if pct <= self.LOW_BATTERY_THRESHOLD:
            return 0
        if pct >= 0.75:
            return 4
        if pct >= 0.50:
            return 3
        if pct >= 0.25:
            return 2
        return 1

    def is_low_battery(self):
        if not self.is_battery_fresh() or math.isnan(self.battery_percentage):
            return False
        return self.battery_percentage <= self.LOW_BATTERY_THRESHOLD

    def draw_thumbs_up(self, draw, x, y):
        # 簡易讚手勢 icon：拳頭 (方框) + 向上豎起的拇指
        draw.rectangle([x, y + 10, x + 12, y + 22], outline="white", fill="black")
        draw.rectangle([x + 2, y, x + 7, y + 11], outline="white", fill="black")
        draw.line([x, y + 22, x + 12, y + 22], fill="white")

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
