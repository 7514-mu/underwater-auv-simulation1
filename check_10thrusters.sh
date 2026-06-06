#!/bin/bash
# 10推进器诊断和启动脚本

echo "=========================================="
echo "10推进器RexROV诊断"
echo "=========================================="

# 1. 检查当前配置
echo ""
echo "【1】检查当前配置文件..."
CONFIG_FILE="/home/wei1367/ros2_ws/src/uuv_descriptions/urdf/rexrov_actuators.xacro"
THRUSTER_COUNT=$(grep -c "thruster_id=" "$CONFIG_FILE")
echo "   当前推进器数量: $THRUSTER_COUNT"

if [ "$THRUSTER_COUNT" -eq 10 ]; then
    echo "   ✅ 配置文件正确（10推进器）"
else
    echo "   ❌ 配置文件错误（期望10，实际$THRUSTER_COUNT）"
fi

# 2. 检查是否编译
echo ""
echo "【2】检查编译状态..."
if [ -f "/home/wei1367/ros2_ws/install/uuv_descriptions/share/uuv_descriptions/urdf/rexrov_actuators.xacro" ];then
    INSTALLED_COUNT=$(grep -c "thruster_id=" "/home/wei1367/ros2_ws/install/uuv_descriptions/share/uuv_descriptions/urdf/rexrov_actuators.xacro")
    echo "   已安装版本: $INSTALLED_COUNT 个推进器"
    if [ "$INSTALLED_COUNT" -eq 10 ]; then
        echo "   ✅ 已编译10推进器版本"
    else
        echo "   ⚠️  已编译版本不是10推进器，需要重新编译"
    fi
else
    echo "   ❌ 未找到编译后的文件"
fi

# 3. 检查Gazebo是否运行
echo ""
echo "【3】检查Gazebo状态..."
if pgrep -x "gzserver" > /dev/null; then
    echo "   ✅ Gazebo正在运行"
else
    echo "   ❌ Gazebo未运行！请先启动："
    echo "      ros2 launch uuv_gazebo_worlds ocean_waves.launch"
fi

# 4. 检查RexROV是否加载
echo ""
echo "【4】检查RexROV是否加载..."
if ros2 node list 2>/dev/null | grep -q "rexrov"; then
    echo "   ✅ RexROV节点正在运行"
else
    echo "   ❌ RexROV未加载"
fi

# 5. 检查推进器话题
echo ""
echo "【5】检查推进器话题..."
THRUSTER_TOPICS=$(ros2 topic list 2>/dev/null | grep -c "rexrov/thrusters/id_")
if [ "$THRUSTER_TOPICS" -gt 0 ]; then
    echo "   发现 $THRUSTER_TOPICS 个推进器话题"
    echo "   推进器列表:"
    ros2 topic list 2>/dev/null | grep "rexrov/thrusters/id_" | sort
else
    echo "   ⚠️  未发现推进器话题"
fi

echo ""
echo "=========================================="
echo "诊断完成"
echo "=========================================="

# 6. 提供启动建议
echo ""
echo "如果所有检查都通过，但机器人仍未出现，请："
echo "1. 在Gazebo中检查模型列表：按Ctrl+T或查看Models面板"
echo "2. 查看Gazebo输出是否有错误信息"
echo "3. 尝试手动生成spawn命令"
