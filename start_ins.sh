#!/bin/bash
# 一键启动INS系统

echo "=================================================="
echo "🧭 惯性导航系统（INS）快速启动"
echo "=================================================="
echo ""

# 检查ROS 2环境
if [ -z "$ROS_DOMAIN_ID" ]; then
    echo "⚠️  ROS 2环境未设置，正在设置..."
    source /opt/ros/humble/setup.bash
    cd ~/ros2_ws
    source install/setup.bash
fi

echo "💡 启动步骤："
echo "   1. 确保Gazebo和机器人已启动"
echo "   2. 启动INS节点"
echo "   3. 可选：启动精度测试"
echo ""

# 检查Gazebo是否运行
if ros2 node list 2>/dev/null | grep -q gazebo; then
    echo "✅ Gazebo正在运行"
else
    echo "❌ Gazebo未运行，请先启动："
    echo "   ros2 launch uuv_gazebo_worlds ocean_waves.launch"
    exit 1
fi

# 检查机器人是否加载
if ros2 topic list 2>/dev/null | grep -q rexrov/imu; then
    echo "✅ 机器人传感器正常"
else
    echo "❌ 机器人未加载，请先启动："
    echo "   ros2 launch uuv_descriptions upload_rexrov_default.launch.py"
    exit 1
fi

echo ""
echo "=================================================="
echo "🚀 正在启动INS节点..."
echo "=================================================="
echo ""

# 启动INS节点
cd ~/ros2_ws
python3 simple_ins_node.py
