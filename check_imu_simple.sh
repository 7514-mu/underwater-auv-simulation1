#!/bin/bash
# 简单查看IMU数据

echo "=================================================="
echo "📡 IMU传感器实时数据"
echo "=================================================="
echo ""
echo "💡 按Ctrl+C停止"
echo ""

# 检查话题是否存在
if ! ros2 topic list 2>/dev/null | grep -q "/rexrov/imu"; then
    echo "❌ IMU话题不存在：/rexrov/imu"
    echo ""
    echo "💡 请先启动Gazebo和机器人"
    exit 1
fi

echo "✅ IMU话题正常"
echo ""
echo "=================================================="
echo ""

# 直接显示IMU数据
ros2 topic echo /rexrov/imu
