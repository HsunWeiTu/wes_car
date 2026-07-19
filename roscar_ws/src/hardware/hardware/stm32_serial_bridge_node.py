#!/usr/bin/env python3
import rclpy
import serial
import struct
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import BatteryState

class Stm32SerialBridgeNode(Node):
    TX_HEADER = bytes([0xFF, 0xFC])
    RX_HEADER = bytes([0xFF, 0xFB])
    FUNC_SET_AUTO_SEND = 0x01
    FUNC_REQUEST_DATA = 0x50
    FUNC_MOTION_DATA = 0x0A

    def __init__(self):
        super().__init__('stm32_serial_bridge_node')
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('serial_timeout', 1.0)
        self.declare_parameter('cmd_vel_topic', 'cmd_vel')
        self.declare_parameter('battery_state_topic', 'battery_state')
        # 將 /cmd_vel 的真實物理單位轉成 STM32 協議的整數原始值 (依協議縮放倍率)
        self.declare_parameter('vx_scale', 1000.0)  # [m/s]   -> raw (×1000)
        self.declare_parameter('vy_scale', 1000.0)  # [m/s]   -> raw (×1000)
        self.declare_parameter('wz_scale', 5000.0)  # [rad/s] -> raw (×5000)
        self.declare_parameter('battery_min_voltage', 9.6)
        self.declare_parameter('battery_max_voltage', 12.6)

        serial_port = self.get_parameter('serial_port').value
        baudrate = int(self.get_parameter('baudrate').value)
        serial_timeout = float(self.get_parameter('serial_timeout').value)
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        battery_state_topic = self.get_parameter('battery_state_topic').value
        self.vx_scale = float(self.get_parameter('vx_scale').value)
        self.vy_scale = float(self.get_parameter('vy_scale').value)
        self.wz_scale = float(self.get_parameter('wz_scale').value)
        self.battery_min_voltage = float(self.get_parameter('battery_min_voltage').value)
        self.battery_max_voltage = float(self.get_parameter('battery_max_voltage').value)
        self.rx_buffer = bytearray()

        try:
            self.serial_port = serial.Serial(serial_port, baudrate, timeout=serial_timeout)
            self.get_logger().info(f'Serial port opened successfully: {serial_port}')
            self.buzzer(0x00) # 啟動時先關閉蜂鳴器
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open serial port: {e}')
            raise e
        
        self.subscription = self.create_subscription(Twist, cmd_vel_topic, self.cmd_vel_callback, 10)
        self.battery_pub = self.create_publisher(BatteryState, battery_state_topic, 10)
        self.read_timer = self.create_timer(0.02, self.read_serial_data)
        self.battery_request_timer = self.create_timer(1.0, self.request_motion_data)
        self.set_auto_send_data(True)

    def cmd_vel_callback(self, msg):
        # /cmd_vel 為真實物理單位：linear [m/s]、angular [rad/s]
        vx_raw = self.clamp_int16(msg.linear.x * self.vx_scale)
        vy_raw = self.clamp_int16(msg.linear.y * self.vy_scale)
        wz_raw = self.clamp_int16(msg.angular.z * self.wz_scale)
        # 呼叫你原本寫好的發送函式
        self.send_motion_control_command(vx_raw, vy_raw, wz_raw)

    @staticmethod
    def clamp_int16(value):
        return max(min(int(value), 32767), -32768)

    def set_auto_send_data(self, enabled):
        self.send_packet(bytes([
            0x05,
            self.FUNC_SET_AUTO_SEND,
            0x01 if enabled else 0x00,
            0x00,
        ]))

    def request_motion_data(self):
        self.send_packet(bytes([
            0x05,
            self.FUNC_REQUEST_DATA,
            self.FUNC_MOTION_DATA,
            0x00,
        ]))

    def send_packet(self, payload):
        checksum = sum(payload) % 256
        self.serial_port.write(self.TX_HEADER + payload + bytes([checksum]))

    def read_serial_data(self):
        try:
            waiting = self.serial_port.in_waiting
            if waiting <= 0:
                return

            self.rx_buffer.extend(self.serial_port.read(waiting))
            self.parse_rx_buffer()
        except serial.SerialException as e:
            self.get_logger().error(f'Error reading serial data: {e}')

    def parse_rx_buffer(self):
        while len(self.rx_buffer) >= 3:
            header_index = self.rx_buffer.find(self.RX_HEADER)
            if header_index < 0:
                del self.rx_buffer[:-1]
                return

            if header_index > 0:
                del self.rx_buffer[:header_index]

            if len(self.rx_buffer) < 3:
                return

            length = self.rx_buffer[2]
            packet_length = length + 2
            if len(self.rx_buffer) < packet_length:
                return

            packet = bytes(self.rx_buffer[:packet_length])
            del self.rx_buffer[:packet_length]

            if not self.is_valid_packet(packet):
                self.get_logger().warn('Received STM32 packet with invalid checksum.')
                continue

            self.handle_packet(packet)

    @staticmethod
    def is_valid_packet(packet):
        if len(packet) < 4:
            return False

        checksum = sum(packet[2:-1]) % 256
        return checksum == packet[-1]

    def handle_packet(self, packet):
        function_id = packet[3]
        if function_id == self.FUNC_MOTION_DATA and len(packet) >= 12:
            self.publish_battery_state(packet[10] / 10.0)

    def publish_battery_state(self, voltage):
        msg = BatteryState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.voltage = voltage
        msg.present = True
        # 硬體僅提供電壓量測，無法得知是否充電
        msg.power_supply_status = BatteryState.POWER_SUPPLY_STATUS_UNKNOWN
        msg.power_supply_health = BatteryState.POWER_SUPPLY_HEALTH_UNKNOWN
        msg.power_supply_technology = BatteryState.POWER_SUPPLY_TECHNOLOGY_UNKNOWN
        msg.percentage = self.voltage_to_percentage(voltage)
        self.battery_pub.publish(msg)

    def voltage_to_percentage(self, voltage):
        voltage_range = self.battery_max_voltage - self.battery_min_voltage
        if voltage_range <= 0.0:
            return float('nan')

        percentage = (voltage - self.battery_min_voltage) / voltage_range
        return max(min(percentage, 1.0), 0.0)

    def buzzer(self, state): #state: 0x00 for off, 0x01 for always on, 0x10 for 10ms on then off.
        header = [0xFF, 0xFC]
        length = 0x05
        function_id = 0x02
        command = struct.pack('<BBB', length, function_id, state)
        checksum = (sum(command) % 256)
        full_command = bytes(header) + command + bytes([checksum])
        self.serial_port.write(full_command)
        self.get_logger().info(f'Buzzer command sent: {full_command.hex()}')

    def send_move_command(self, speed, direction):
        #
        header = [0xFF, 0xFC]
        length = 0x06
        founction_id = 0x11
        car_type = 0x0A
        try:
            command = struct.pack('<BBBBB', length, founction_id, car_type, direction, speed)
        except struct.error as e:
            self.get_logger().error(f'Error packing move command: {e}')
            return
        checksum = (sum(command) % 256)
        full_commend = bytes(header) + command + bytes([checksum])
        self.serial_port.write(full_commend)
        self.get_logger().info(f'Move command sent: {full_commend.hex()}')
        #self.get_logger().info(f'Vx = {Vx}, Vy = {Vy}, Wz = {Wz}')

    def send_motion_control_command(self, Vx, Vy, Wz):
        # 
        header = [0xFF, 0xFC]
        length = 0x0A
        function_id = 0x12
        car_type = 0x0A
        try:
            command = struct.pack('<BBBhhh', length, function_id, car_type, Vx, Vy, Wz)
        except struct.error as e:
            self.get_logger().error(f'Error packing motion control command: {e}')
            return
        checksum = (sum(command) % 256)
        full_command = bytes(header) + command + bytes([checksum])
        self.serial_port.write(full_command)
        self.get_logger().info(f'Motion control command sent: {full_command.hex()}')

def main(args=None):
    rclpy.init(args=args)
    node = Stm32SerialBridgeNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()