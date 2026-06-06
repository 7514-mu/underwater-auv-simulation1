#!/usr/bin/env python3
"""
ROS 2 Humble - RexROV完整演示启动脚本
包括：Gazebo、机器人、PID控制器、键盘控制
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch import LaunchDescription
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # 声明launch参数
    use_ned_frame_arg = DeclareLaunchArgument(
        'use_ned_frame',
        default_value='false',
        description='Use NED frame'
    )

    record_arg = DeclareLaunchArgument(
        'record',
        default_value='false',
        description='Record simulation'
    )

    # 获取包路径
    uuv_gazebo_worlds_share = get_package_share_directory('uuv_gazebo_worlds')
    uuv_descriptions_share = get_package_share_directory('uuv_descriptions')

    # 启动Gazebo世界
    gazebo_world = os.path.join(uuv_gazebo_worlds_share, 'launch', 'ocean_waves.launch')

    return LaunchDescription([
        # 注意：这里需要手动启动各个组件，因为ROS 2的复杂依赖
        # 建议使用分步启动方式，参见 ~/ros2_ws/启动指南_5终端.md
        use_ned_frame_arg,
        record_arg,
    ])

def main(args=None):
    from launch import LaunchService
    from ament_index_python.packages import get_package_share_directory

    # 这里只是占位，实际上应该使用分步启动
    ld = generate_launch_description()
    ls = LaunchService()
    ls.include_launch_description(ld)
    return ls.run(ld)

if __name__ == '__main__':
    main()
