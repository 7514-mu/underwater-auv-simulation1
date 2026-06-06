"""
Launch file for underwater bubble simulation.

Starts Gazebo (headless) with bubble world, spawns rexrov robot,
and launches bubble generator, image processor, and dynamics nodes.

Usage:
  ros2 launch underwater_bubble_sim ocean_bubbles.launch.py
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python import get_package_share_directory
import os


def generate_launch_description():
    uuv_worlds_dir = get_package_share_directory('uuv_gazebo_worlds')
    bubble_dir = get_package_share_directory('underwater_bubble_sim')

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

    robot_spawn = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('uuv_descriptions'),
                'launch', 'upload_rexrov_default.launch.py')),
        launch_arguments={
            'gazebo_namespace': "''",
        }.items())

    bubble_generator = Node(
        package='underwater_bubble_sim',
        executable='bubble_generator.py',
        name='bubble_generator',
        output='screen',
        parameters=[os.path.join(bubble_dir, 'config', 'bubble_params.yaml')],
    )

    bubble_image_processor = Node(
        package='underwater_bubble_sim',
        executable='bubble_image_processor.py',
        name='bubble_image_processor',
        output='screen',
        parameters=[os.path.join(bubble_dir, 'config', 'bubble_params.yaml')],
    )

    bubble_dynamics = Node(
        package='underwater_bubble_sim',
        executable='bubble_dynamics.py',
        name='bubble_dynamics',
        output='screen',
        parameters=[os.path.join(bubble_dir, 'config', 'bubble_params.yaml')],
    )

    return LaunchDescription([
        gazebo_launch,
        robot_spawn,
        bubble_generator,
        bubble_image_processor,
        bubble_dynamics,
    ])
