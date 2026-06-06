#!/bin/bash
# 测试导弹AUV模型
# Test Missile AUV Model

echo "======================================"
echo "  Missile AUV Gazebo Test"
echo "======================================"

# Source ROS2 workspace
source /home/wei1367/ros2_ws/install/setup.bash

# 启动Gazebo水下世界（后台运行）
echo "Starting Gazebo with underwater world..."
ros2 launch uuv_gazebo_worlds ocean_waves.launch &
GAZEBO_PID=$!

# 等待Gazebo完全启动
echo "Waiting for Gazebo to start..."
sleep 10

# 检查Gazebo是否运行
if ! pgrep -x "gzserver" > /dev/null; then
    echo "ERROR: Gazebo failed to start!"
    exit 1
fi

echo "Gazebo is running. Spawning missile model..."

# 使用URDF直接生成模型
ros2 run gazebo_ros spawn_entity.py \
    -entity missile_auv \
    -x 0 \
    -y 0 \
    -z -10 \
    -topic /robot_description &

# 发布URDF到robot_description topic
ros2 run robot_state_publisher robot_state_publisher \
    --ros-args \
    -p robot_description:="$(cat /home/wei1367/ros2_ws/missile_final.urdf)" &
RSP_PID=$!

echo ""
echo "======================================"
echo "  Missile AUV spawned!"
echo "  - Gazebo PID: $GAZEBO_PID"
echo "  - RSP PID: $RSP_PID"
echo ""
echo "  Topics to check:"
echo "    /missile_auv/imu"
echo "    /missile_auv/pose_gt"
echo "    /missile_auv/thrusters/main/input"
echo ""
echo "  To stop: Ctrl+C or kill $GAZEBO_PID"
echo "======================================"

# 等待用户中断
wait $GAZEBO_PID
