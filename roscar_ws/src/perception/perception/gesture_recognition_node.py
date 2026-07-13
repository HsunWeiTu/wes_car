#!/home/wes/mp_env/bin/python3
# -*- coding: utf-8 -*-
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
from cv_bridge import CvBridge
import cv2
import sys
sys.path.insert(0, '/home/wes/mp_env/lib/python3.10/site-packages')
import mediapipe as mp

# 引入你的自定義訊息
from wes_car_interface.msg import Gesture

class GestureRecognitionNode(Node):
    def __init__(self):
        super().__init__('gesture_recognition_node')
        self.get_logger().warn('--- 偵測啟動：正在嘗試訂閱 /ascamera/camera_publisher/rgb0/image ---')
        # 1. 初始化訂閱與發布
        self.subscription = self.create_subscription(
            Image, '/ascamera/camera_publisher/rgb0/image', self.image_callback, 10)
        self.publisher_ = self.create_publisher(Gesture, 'raw_gesture_data', 10)
        
        # 2. 初始化工具
        self.bridge = CvBridge()
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1, # 先專注於一隻手，邏輯比較簡單
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.get_logger().info('Recognition Layer: MediaPipe node started.')

    def image_callback(self, msg):
        try:
            # 轉換影像
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_image)

            if results.multi_hand_landmarks:
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # 判斷左右手 (MediaPipe 的結果)
                    handedness = results.multi_handedness[idx].classification[0].label
                    
                    # 建立並填充訊息
                    gesture_msg = self.create_gesture_msg(hand_landmarks, handedness)
                    self.publisher_.publish(gesture_msg)

            # Debug 用畫圖 (選配，可以增加流暢度)
            #cv2.imshow('Recognition Debug', cv_image)
            #cv2.waitKey(1)

        except Exception as e:
            self.get_logger().error(f'Recognition Error: {e}')

    def create_gesture_msg(self, landmarks, handedness):
        msg = Gesture()
        msg.header.stamp = self.get_clock().now().to_msg()
        #msg.is_left_hand = (handedness == 'Left')

        # 輔助函數：將 MediaPipe 點轉為 ROS Point
        def to_p(idx):
            p = Point()
            lm = landmarks.landmark[idx]
            p.x = float(lm.x)
            p.y = float(lm.y)
            p.z = float(lm.z)
            return p

        # 賦值各關鍵點
        # 掌心
        msg.palm_center = to_p(9) # 中指根部作為參考中心

        # 指尖 (Tip: 4, 8, 12, 16, 20)
        msg.thumb_tip  = to_p(4)
        msg.index_tip  = to_p(8)
        msg.middle_tip = to_p(12)
        msg.ring_tip   = to_p(16)
        msg.pinky_tip  = to_p(20)

        # 指根 (MCP: 2, 5, 9, 13, 17)
        msg.thumb_mcp  = to_p(2)
        msg.index_mcp  = to_p(5)
        msg.middle_mcp = to_p(9)
        msg.ring_mcp   = to_p(13)
        msg.pinky_mcp  = to_p(17)

        return msg

def main(args=None):
    rclpy.init(args=args)
    node = GestureRecognitionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()