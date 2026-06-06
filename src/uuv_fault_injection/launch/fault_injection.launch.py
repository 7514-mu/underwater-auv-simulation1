"""
Fault Injection Launch File
Starts fault injection system with AUV simulation
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Declare launch arguments
    namespace_arg = DeclareLaunchArgument(
        'namespace',
        default_value='rexrov',
        description='Robot namespace'
    )

    # Fault injector node
    fault_injector_node = Node(
        package='uuv_fault_injection',
        executable='fault_injector',
        name='fault_injector',
        namespace=LaunchConfiguration('namespace'),
        output='screen',
        parameters=[{
            'namespace': LaunchConfiguration('namespace')
        }]
    )

    # Fault monitor node (optional)
    fault_monitor_node = Node(
        package='uuv_fault_injection',
        executable='fault_monitor',
        name='fault_monitor',
        namespace=LaunchConfiguration('namespace'),
        output='screen',
        condition=None  # Always start for now
    )

    return LaunchDescription([
        namespace_arg,
        fault_injector_node,
        # fault_monitor_node  # Uncomment to enable monitoring
    ])
