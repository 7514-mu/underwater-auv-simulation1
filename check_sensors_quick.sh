#!/bin/bash
# 快速检查传感器话题是否存在

echo "=================================================="
echo "🔍 RexROV 传感器话题快速检查"
echo "=================================================="
echo ""

# 传感器话题列表
declare -A sensors=(
    ["IMU"]="/rexrov/imu"
    ["磁力计"]="/rexrov/magnetometer"
    ["GPS"]="/rexrov/gps"
    ["压力传感器"]="/rexrov/pressure"
    ["DVL"]="/rexrov/dvl"
    ["Pose_GT"]="/rexrov/pose_gt"
    ["Camera"]="/rexrov/camera"
)

echo "💡 正在检查传感器话题..."
echo ""

all_ok=true

for sensor in "${!sensors[@]}"; do
    topic="${sensors[$sensor]}"
    if ros2 topic list 2>/dev/null | grep -q "$topic"; then
        echo "✅ $sensor: $topic"
        # 尝试获取话题信息
        type=$(ros2 topic info $topic 2>/dev/null | grep "Type:" | awk '{print $2}')
        if [ -n "$type" ]; then
            echo "   类型: $type"
        fi
    else
        echo "❌ $sensor: $topic (未找到)"
        all_ok=false
    fi
    echo ""
done

echo "=================================================="
if [ "$all_ok" = true ]; then
    echo "✅ 所有传感器话题都存在！"
    echo ""
    echo "💡 下一步："
    echo "   运行完整测试: python3 ~/ros2_ws/test_all_sensors.py"
else
    echo "⚠️  部分传感器话题缺失"
    echo ""
    echo "💡 可能原因："
    echo "   1. Gazebo 未启动"
    echo "   2. 机器人未加载"
    echo "   3. 传感器插件未正确加载"
fi
echo "=================================================="
