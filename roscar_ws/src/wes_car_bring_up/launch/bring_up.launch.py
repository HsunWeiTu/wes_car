from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    use_joy = LaunchConfiguration('use_joy')
    use_camera = LaunchConfiguration('use_camera')
    use_gesture = LaunchConfiguration('use_gesture')
    use_hardware = LaunchConfiguration('use_hardware')
    use_oled = LaunchConfiguration('use_oled')
    image_topic = LaunchConfiguration('image_topic')
    gesture_topic = LaunchConfiguration('gesture_topic')
    control_topic = LaunchConfiguration('control_topic')
    cmd_vel_topic = LaunchConfiguration('cmd_vel_topic')
    serial_port = LaunchConfiguration('serial_port')

    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        condition=IfCondition(use_joy),
    )

    joy_to_car_control_node = Node(
        package='decision',
        executable='joy_to_car_control_node',
        name='joy_to_car_control_node', 
        parameters=[{
            'output_control_topic': control_topic,
        }],
        condition=IfCondition(use_joy),
    )

    stm32_serial_bridge_node = Node(
        package='hardware',
        executable='stm32_serial_bridge_node',
        name='stm32_serial_bridge_node',
        parameters=[{
            'serial_port': serial_port,
            'cmd_vel_topic': cmd_vel_topic,
        }],
        arguments=['--ros-args', '--log-level', 'warn'], 
        output='screen',
        condition=IfCondition(use_hardware),
    )

    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ascamera'), 
            'launch', 
            'ascamera.launch.py'
        )),
        condition=IfCondition(use_camera),
    )

    gesture_to_car_control_node = Node(
        package='decision',
        executable='gesture_to_car_control_node',
        name='gesture_to_car_control_node',
        parameters=[{
            'input_gesture_topic': gesture_topic,
            'output_control_topic': control_topic,
        }],
        condition=IfCondition(use_gesture),
    )

    hand_gesture_recognition_node = Node(
        package='perception',
        executable='hand_gesture_recognition_node',
        name='hand_gesture_recognition_node',
        parameters=[{
            'image_topic': image_topic,
            'gesture_topic': gesture_topic,
        }],
        condition=IfCondition(use_gesture),
    )

    car_control_to_cmd_vel_node = Node(
        package='control',
        executable='car_control_to_cmd_vel_node',
        name='car_control_to_cmd_vel_node',
        output='screen',
        parameters=[{
            'input_control_topic': control_topic,
            'output_cmd_vel_topic': cmd_vel_topic,
        }],
    )

    front_oled_display_node = Node(
        package='control',
        executable='front_oled_display_node',
        name='front_oled_display_node',
        condition=IfCondition(use_oled),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_joy', default_value='true'),
        DeclareLaunchArgument('use_camera', default_value='true'),
        DeclareLaunchArgument('use_gesture', default_value='true'),
        DeclareLaunchArgument('use_hardware', default_value='true'),
        DeclareLaunchArgument('use_oled', default_value='true'),
        DeclareLaunchArgument('image_topic', default_value='/ascamera/camera_publisher/rgb0/image'),
        DeclareLaunchArgument('gesture_topic', default_value='raw_gesture_data'),
        DeclareLaunchArgument('control_topic', default_value='/car_movement_control'),
        DeclareLaunchArgument('cmd_vel_topic', default_value='/cmd_vel'),
        DeclareLaunchArgument('serial_port', default_value='/dev/ttyUSB0'),
        joy_node,
        joy_to_car_control_node,
        stm32_serial_bridge_node,
        camera_launch,
        gesture_to_car_control_node,
        hand_gesture_recognition_node,
        car_control_to_cmd_vel_node,
        front_oled_display_node
    ])