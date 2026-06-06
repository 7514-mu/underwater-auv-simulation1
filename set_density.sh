#!/bin/bash
# 快速设置流体密度

if [ -z "$1" ]; then
    echo "🌊 水体密度设置工具"
    echo "=================="
    echo ""
    echo "用法: ./set_density.sh <密度值>"
    echo ""
    echo "【常见密度值】"
    echo "  999.8  - 冰水 (0°C)"
    echo "  999.7  - 冷水 (10°C)"
    echo "  998.2  - 常温 (20°C) ← 默认"
    echo "  995.7  - 温水 (30°C)"
    echo "  992.2  - 热水 (40°C)"
    echo ""
    echo "例子:"
    echo "  ./set_density.sh 995.7   # 设置为30°C水温"
    echo "  ./set_density.sh 998.2   # 恢复默认"
    exit 1
fi

DENSITY=$1

echo "💡 正在设置水体密度为: $DENSITY kg/m³"

# 使用ros2 service call
ros2 service call /rexrov/set_fluid_density uuv_gazebo_ros_plugins_msgs/srv/SetFloat "{data: $DENSITY}"

echo ""
echo "✅ 密度设置完成"
echo "💡 观察机器人浮力变化"
