"""Gazebo Sim（gz-sim / Fortress）模擬啟動 —— ROS2 原生路線。

流程：
  1. 設定資源路徑，讓 gz 找得到 world 與 mesh
  2. 啟動 gz-sim（載入 wes_world.sdf）；gui:=false 時走無頭伺服器
  3. xacro → /robot_description → robot_state_publisher（發布 TF）
  4. ros_gz_sim create：從注入過 expressed_in 的 SDF 把車 spawn 進 gz
  5. ros_gz_bridge：把 gz topic 橋接成 ROS2 topic

啟動參數：
  gui:=true   （預設）開 gz GUI，需要可用的 GPU/OpenGL
  gui:=false  無頭伺服器（無畫面），適合無 GPU 環境；用 RViz2 或 teleop 操作

遙控（含 linear.y 橫移，麥輪全向）：
    ros2 run decision keyboard_to_car_control_node
  # 或 ros2 run teleop_twist_keyboard teleop_twist_keyboard
"""
import os
import subprocess
import tempfile
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

WORLD_NAME = 'wes_world'
ROBOT_NAME = 'wes_car'


def _build_gz_sdf(xacro_file, resource_path):
    """xacro → URDF → SDF，並重新注入 URDF→SDF 會移除的 ignition:expressed_in。

    麥輪滾柱靠輪子的非等向摩擦 fdir1 模擬，而 fdir1 必須表達在車體座標，
    否則會隨輪子自轉而方向錯亂、橫移失效。URDF→SDF 轉換會吃掉這個屬性，故在此補回。
    注意：URDF 的 base_link 因 fixed joint 會被合併(lump)進 base_footprint 這個
    canonical link，因此參考 frame 用 base_footprint（方向與 base_link 相同）。
    回傳可直接 spawn 的 SDF 檔路徑。
    """
    env = dict(os.environ, IGN_GAZEBO_RESOURCE_PATH=resource_path)
    urdf = subprocess.check_output(['xacro', xacro_file], env=env).decode()
    with tempfile.NamedTemporaryFile('w', suffix='.urdf', delete=False) as f:
        f.write(urdf)
        urdf_path = f.name
    sdf = subprocess.check_output(['ign', 'sdf', '-p', urdf_path], env=env).decode()
    sdf = sdf.replace('<fdir1>', '<fdir1 ignition:expressed_in="base_footprint">')
    sdf_path = os.path.join(tempfile.gettempdir(), 'wes_car_gz.sdf')
    with open(sdf_path, 'w') as f:
        f.write(sdf)
    return sdf_path


def _launch_setup(context):
    pkg = get_package_share_directory('simulation')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    xacro_file = os.path.join(pkg, 'urdf', 'wes_car.urdf.xacro')
    resource_path = os.path.dirname(pkg)

    gui = context.launch_configurations.get('gui', 'true').lower() == 'true'
    world = context.launch_configurations.get('world', 'wes_world')
    # gui 只控制要不要開 GUI；world 控制世界：
    #   wes_world = 含 Sensors 系統（光達/相機有資料，需 GPU）
    #   driving   = 純驅動（無感測器，無 GPU 也能跑）
    gz_flags = '-r' if gui else '-s -r'
    world_file = os.path.join(pkg, 'worlds', f'{world}.sdf')

    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)
    gz_sdf_file = _build_gz_sdf(xacro_file, resource_path)

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': f'{gz_flags} {world_file}'}.items(),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
        output='screen',
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-file', gz_sdf_file, '-name', ROBOT_NAME, '-z', '0.1'],
        output='screen',
    )

    # gz topic ↔ ROS2 topic 橋接（@ 雙向, [ gz→ROS, ] ROS→gz）
    joint_state_gz = f'/world/{WORLD_NAME}/model/{ROBOT_NAME}/joint_state'
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
            f'{joint_state_gz}@sensor_msgs/msg/JointState[ignition.msgs.Model',
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            '/camera/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camera/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camera/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        ],
        remappings=[(joint_state_gz, '/joint_states')],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return [gz_sim, robot_state_publisher, spawn, bridge]


def generate_launch_description():
    pkg = get_package_share_directory('simulation')
    resource_path = os.path.dirname(pkg)

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true',
                              description='true=開 gz GUI；false=無頭伺服器'),
        DeclareLaunchArgument('world', default_value='wes_world',
                              description='wes_world=含感測器(需GPU)；driving=純驅動(免GPU)'),
        SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', resource_path),
        OpaqueFunction(function=_launch_setup),
    ])
