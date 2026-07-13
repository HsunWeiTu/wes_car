
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    
    # 1. Joy Node: �t�dŪ���n��w��T��
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
    )

    # 2. Teleop Node: �t�d�N�n��T�� (sensor_msgs/Joy) �ର�t�׫��O (geometry_msgs/Twist)
    # �o�̰��]�A�� teleop_node �w�]���� /joy ���D�A�o�� /cmd_vel ���D
    teleop_node = Node(
        package='decision',
        executable='teleop_node',
        name='joy_teleop_node', 
    )

    # 3. STM32 Serial Node: �t�d�N�t�׫��O (/cmd_vel) �z�L��f�o�� STM32
    hardware_node = Node(
        package='hardware',
        executable='serial_node',
        name='serial_node',
        arguments=['--ros-args', '--log-level', 'warn'], 
        output='screen',
    )

    # 4. Camera Launch: �t�d�N�t�׫��O (鏡頭) �A�i�H�� camera_launch.py
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ascamera'), 
            'launch', 
            'ascamera.launch.py'
        ))
    )

    # 5. Gesture Perception Node:tdNt׫O (鏡頭影像)AiH gesture_perception_node.py
    gesture_decision_node = Node(
        package='decision',
        executable='gesture_decision_node',
        name='gesture_decision_node'
    )

    gesture_recognition_node = Node(
    package='perception',
    executable='gesture_recognition_node',
    name='gesture_recognition_node',
    remappings=[
        # 將輸入對接到相機發布的真實話題
        ('/image', '/ascamera/camera_publisher/rgb0/image'),
        # 輸出則對接到決策層正在監聽的話題
        ('/gesture', '/wes_car/raw_gesture')
    ])

    car_controller_node = Node(
        package='control',
        executable='car_controller',
        name='car_controller_node',
        output='screen'
    )

    oled_node = Node(
        package='control',
        executable='oled_display',
        name='oled_display_node'
    )

    return LaunchDescription([
        joy_node,
        teleop_node,
        hardware_node,
        camera_launch,
        gesture_decision_node,
        gesture_recognition_node,
        car_controller_node,
        oled_node
    ])