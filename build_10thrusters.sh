#!/bin/bash
# 构建10推进器RexROV配置

echo "=========================================="
echo "构建10推进器RexROV"
echo "=========================================="

cd ~/ros2_ws

# Source ROS环境
source /opt/ros/humble/setup.bash

# 清理旧的构建
echo "清理旧构建..."
rm -rf build/uuv_descriptions install/uuv_descriptions

# 构建新配置
echo "构建新配置..."
colcon build --packages-select uuv_descriptions

# Source新环境
source install/setup.bash

echo "✅ 构建完成！"
echo ""
echo "现在可以启动仿真："
echo "  ros2 launch uuv_gazebo_worlds ocean_waves.launch"
echo "  ros2 launch uuv_descriptions upload_rexrov_default.launch.py mode:=default"
echo ""
echo "检查推进器数量："
echo "  ros2 topic list | grep thruster"
