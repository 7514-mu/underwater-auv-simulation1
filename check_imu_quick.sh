#!/bin/bash
# 快速查看IMU数据

echo "=================================================="
echo "📡 IMU传感器快速检查"
echo "=================================================="
echo ""
echo "💡 正在查看IMU数据（按Ctrl+C停止）"
echo ""

# 检查话题是否存在
if ! ros2 topic list 2>/dev/null | grep -q "/rexrov/imu"; then
    echo "❌ IMU话题不存在：/rexrov/imu"
    echo ""
    echo "💡 可能原因："
    echo "   1. Gazebo未启动"
    echo "   2. 机器人未加载"
    echo "   3. IMU插件未加载"
    echo ""
    echo "💡 请先启动："
    echo "   ros2 launch uuv_gazebo_worlds ocean_waves.launch"
    echo "   ros2 launch uuv_descriptions upload_rexrov_default.launch.py"
    exit 1
fi

echo "✅ IMU话题存在"
echo ""
echo "=================================================="
echo "📊 IMU实时数据"
echo "=================================================="
echo ""
echo "【数据说明】"
echo "  加速度 (m/s²):"
echo "    X轴 - 前向加速度"
echo "    Y轴 - 侧向加速度"
echo "    Z轴 - 垂向加速度"
echo ""
echo "  角速度 (rad/s):"
echo "    X轴 - 横滚角速度"
echo "    Y轴 - 俯仰角速度"
echo "    Z轴 - 偏航角速度"
echo ""
echo "=================================================="
echo ""

# 显示IMU数据（使用grep过滤关键信息）
ros2 topic echo /rexrov/imu | grep -A 3 "linear_acceleration:\|angular_velocity:"
