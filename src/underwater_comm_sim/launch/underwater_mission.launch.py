"""
水下任务仿真统一启动文件

启动 Gazebo + 两台 RexROV + 气泡仿真 + 通信/探测/识别/跟踪节点。

使用方法:
  ros2 launch underwater_mission_sim underwater_mission.launch.py
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python import get_package_share_directory
import os


def generate_launch_description():
    uuv_worlds_dir = get_package_share_directory('uuv_gazebo_worlds')
    bubble_dir = get_package_share_directory('underwater_bubble_sim')
    comm_dir = get_package_share_directory('underwater_comm_sim')
    uuv_desc_dir = get_package_share_directory('uuv_descriptions')

    comm_yaml = os.path.join(comm_dir, 'config', 'comm_params.yaml')
    bubble_yaml = os.path.join(bubble_dir, 'config', 'bubble_params.yaml')

    gui_arg = DeclareLaunchArgument('gui', default_value='true')

    # 1. Gazebo + 海洋世界
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('gazebo_ros'),
                'launch', 'gazebo.launch.py')),
        launch_arguments={
            'world': os.path.join(uuv_worlds_dir, 'worlds', 'ocean_waves_bubbles.world'),
            'verbose': 'true',
            'gui': 'true',
        }.items())

    # 2. 生成 auv_1 (RexROV sonar 变体)
    # gazebo_namespace 设为空, 使 spawn_entity 使用 /spawn_entity 服务而非 /gazebo/spawn_entity
    auv_1_spawn = TimerAction(
        period=8.0,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(uuv_desc_dir, 'launch', 'upload_rexrov_default.launch.py')),
            launch_arguments={
                'namespace': 'auv_1',
                'mode': 'sonar',
                'x': '0.0',
                'y': '0.0',
                'z': '-40.0',
                'gazebo_namespace': "''",
            }.items())])

    # 3. 生成 auv_2 (RexROV default, 在auv_1前方15m)
    auv_2_spawn = TimerAction(
        period=12.0,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(uuv_desc_dir, 'launch', 'upload_rexrov_default.launch.py')),
            launch_arguments={
                'namespace': 'auv_2',
                'mode': 'default',
                'x': '15.0',
                'y': '0.0',
                'z': '-40.0',
                'gazebo_namespace': "''",
            }.items())])

    # 4. 气泡仿真节点 (延迟启动, 等航行器生成)
    bubble_generator = TimerAction(
        period=5.0,
        actions=[Node(
            package='underwater_bubble_sim',
            executable='bubble_generator.py',
            name='bubble_generator',
            output='screen',
            parameters=[bubble_yaml],
        )])

    bubble_image_processor = TimerAction(
        period=18.0,
        actions=[Node(
            package='underwater_bubble_sim',
            executable='bubble_image_processor.py',
            name='bubble_image_processor',
            output='screen',
            parameters=[bubble_yaml],
        )])

    bubble_dynamics_1 = TimerAction(
        period=18.0,
        actions=[Node(
            package='underwater_bubble_sim',
            executable='bubble_dynamics.py',
            name='bubble_dynamics_auv1',
            output='screen',
            parameters=[bubble_yaml, {'link_name': 'auv_1/base_link'}],
        )])

    bubble_dynamics_2 = TimerAction(
        period=18.0,
        actions=[Node(
            package='underwater_bubble_sim',
            executable='bubble_dynamics.py',
            name='bubble_dynamics_auv2',
            output='screen',
            parameters=[bubble_yaml, {'link_name': 'auv_2/base_link'}],
        )])

    # 任务仿真节点 (延迟启动, 等航行器和传感器就绪)
    mission_nodes = TimerAction(
        period=22.0,
        actions=[
            Node(
                package='underwater_comm_sim',
                executable='acoustic_comm_simulator.py',
                name='acoustic_comm_simulator',
                output='screen',
                parameters=[comm_yaml],
            ),
            Node(
                package='underwater_comm_sim',
                executable='underwater_detector.py',
                name='underwater_detector',
                output='screen',
            ),
            Node(
                package='underwater_comm_sim',
                executable='underwater_identifier.py',
                name='underwater_identifier',
                output='screen',
            ),
            Node(
                package='underwater_comm_sim',
                executable='underwater_tracker.py',
                name='underwater_tracker',
                output='screen',
            ),
        ])

    return LaunchDescription([
        gui_arg,
        gazebo_launch,
        auv_1_spawn,
        auv_2_spawn,
        bubble_generator,
        bubble_image_processor,
        bubble_dynamics_1,
        bubble_dynamics_2,
        mission_nodes,
    ])
