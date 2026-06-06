#!/bin/bash
# 导弹AUV完整控制系统启动脚本
# Usage:
#   1. ros2 launch uuv_gazebo_worlds ocean_waves.launch
#   2. ros2 launch uuv_descriptions upload_missile_auv.launch.py
#   3. ./start_missile_pid.sh

source /home/wei1367/ros2_ws/install/setup.bash

echo "=========================================="
echo "导弹AUV PID控制系统启动"
echo "=========================================="

NAMESPACE="missile_auv"

# 清理旧进程
killall -9 velocity_control.py acceleration_control.py 2>/dev/null
sleep 1

# 第一步：启动推进器管理器
echo "步骤1: 启动推进器管理器..."
ros2 launch uuv_thruster_manager thruster_manager.launch \
  model_name:=$NAMESPACE \
  uuv_name:=$NAMESPACE > /dev/null 2>&1 &
sleep 5

# 第二步：加速度控制器（在 namespace 下运行）
echo "步骤2: 启动加速度控制器..."
ros2 run uuv_control_cascaded_pid acceleration_control.py \
  --ros-args \
  -r __ns:=/$NAMESPACE \
  -p tf_prefix:="$NAMESPACE/" \
  --params-file /home/wei1367/ros2_ws/src/uuv_control/uuv_control_cascaded_pids/config/missile_auv/inertial.yaml \
  > /dev/null 2>&1 &
sleep 3

# 第三步：速度控制器（在 namespace 下运行）
echo "步骤3: 启动速度控制器..."
ros2 run uuv_control_cascaded_pid velocity_control.py \
  --ros-args \
  -r __ns:=/$NAMESPACE \
  -r odom:=/$NAMESPACE/pose_gt \
  --params-file /home/wei1367/ros2_ws/src/uuv_control/uuv_control_cascaded_pids/config/missile_auv/vel_pid_control.yaml \
  > /dev/null 2>&1 &
sleep 3

# 验证
echo ""
echo "=========================================="
echo "验证"
echo "=========================================="

VC=$(ros2 node list 2>/dev/null | grep -c "velocity_control")
AC=$(ros2 node list 2>/dev/null | grep -c "acceleration_control")
TM=$(ros2 node list 2>/dev/null | grep -c "thruster_allocator")
echo "推进器管理器: $TM | 加速度控制器: $AC | 速度控制器: $VC"

if [ "$VC" -ge 1 ] && [ "$AC" -ge 1 ] && [ "$TM" -ge 1 ]; then
    echo "✓ 全部启动成功"
else
    echo "✗ 部分启动失败"
fi

echo ""
echo "键盘控制:"
echo "  ros2 run uuv_teleop vehicle_keyboard_teleop.py \\"
echo "    --ros-args -r cmd_vel:=/$NAMESPACE/cmd_vel -r output:=/$NAMESPACE/cmd_vel"
echo ""
echo "直接测试推进:"
echo "  ros2 topic pub /$NAMESPACE/cmd_vel geometry_msgs/msg/Twist \\"
echo "    '{linear: {x: 1.0}}' --once"
echo "=========================================="

wait
