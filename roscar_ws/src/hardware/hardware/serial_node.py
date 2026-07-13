#!/usr/bin/env python3
import rclpy
import serial
import struct
from geometry_msgs.msg import Twist
from rclpy.node import Node

class SerialNode(Node):
    def __init__(self):
        super().__init__('serial_node')
        try:
            self.serial_port = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
            self.get_logger().info('Serial port opened successfully')
            self.buzzer(0x01) # 啟動時先關閉蜂鳴器
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open serial port: {e}')
            raise e
        
        self.subscription = self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)

    def cmd_vel_callback(self, msg):
        vx_raw = int(msg.linear.x * 1000) # 0 ~ 1000
        vy_raw = int(msg.linear.y * 1000) # 0 ~ 1000
        wz_raw = int(msg.angular.z * 5000) # 0 ~ 5000
        # 呼叫你原本寫好的發送函式
        self.send_motion_control_command(vx_raw, vy_raw, wz_raw)

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
    serial_node = SerialNode()
    rclpy.spin(serial_node)
    serial_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()