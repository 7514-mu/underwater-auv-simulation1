#!/bin/bash
# 清洁启动PID控制系统（单实例）

source ~/.zshrc 2>/dev/null

echo "=========================================="
echo "PID控制系统清洁启动"
echo "=========================================="

# 第一步：彻底清理
echo ""
echo "步骤1: 清理旧进程..."
killall -9 acceleration_control.py velocity_control.py position_control.py 2>/dev/null
sleep 3

# 验证清理完成
if ps aux | grep -E "acceleration_control|velocity_control|position_control" | grep -v grep | grep -q .; then
    echo "✗ 警告：仍有旧进程在运行！"
    echo "剩余进程："
    ps aux | grep -E "acceleration_control|velocity_control|position_control" | grep -v grep
    echo ""
    echo "请手动清理进程"
    exit 1
fi

echo "✓ 清理完成"

# 第二步：启动推进器管理器
echo ""
echo "步骤2: 启动推进器管理器..."
ros2 launch uuv_thruster_manager thruster_manager.launch \
  model_name:=rexrov \
  uuv_name:=rexrov > /dev/null 2>&1 &
echo "PID: $!"
sleep 5

# 第三步：启动加速度控制器
echo ""
echo "步骤3: 启动加速度控制器..."
ros2 run uuv_control_cascaded_pid acceleration_control.py \
  --ros-args \
  -r cmd_accel:=/rexrov/cmd_accel \
  -r thruster_manager/input:=/rexrov/thruster_manager/input \
  --params-file ~/ros2_ws/src/uuv_control/uuv_control_cascaded_pids/config/rexrov/inertial.yaml > /dev/null 2>&1 &
echo "PID: $!"
sleep 5

# 第四步：启动速度控制器
echo ""
echo "步骤4: 启动速度控制器（机体坐标系）..."
ros2 run uuv_control_cascaded_pid velocity_control.py \
  --ros-args \
  -r cmd_vel:=/rexrov/cmd_vel \
  -r odom:=/rexrov/pose_gt \
  -r cmd_accel:=/rexrov/cmd_accel \
  --params-file ~/ros2_ws/vel_pid_body_fixed.yaml > /dev/null 2>&1 &
echo "PID: $!"
sleep 3

# 第五步：验证
echo ""
echo "=========================================="
echo "步骤5: 验证启动"
echo "=========================================="

sleep 2

# 检查节点数量
VC_COUNT=$(ros2 node list 2>/dev/null | grep -c "/velocity_control" || echo "0")
AC_COUNT=$(ros2 node list 2>/dev/null | grep -c "/acceleration_control" || echo "0")

echo ""
echo "速度控制器实例数: $VC_COUNT"
echo "加速度控制器实例数: $AC_COUNT"

if [ "$VC_COUNT" -eq 1 ] && [ "$AC_COUNT" -eq 1 ]; then
    echo "✓ 控制器启动正常（单实例）"
elif [ "$VC_COUNT" -gt 1 ] || [ "$AC_COUNT" -gt 1 ]; then
    echo "✗ 警告：检测到多个控制器实例！"
    echo "这会导致控制冲突和漂移！"
    exit 1
else
    echo "✗ 控制器启动失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ 启动完成！"
echo "=========================================="
echo ""
echo "已启动2层控制系统："
echo "  1. 速度控制器（机体坐标系）"
echo "  2. 加速度控制器"
echo "  3. 推进器管理器"
echo ""
echo "注意：前进时可能需要手动按Z键轻微上浮以补偿下沉效应"
echo ""
echo "控制机器人："
echo "  ros2 run uuv_teleop vehicle_keyboard_teleop.py \\"
echo "    --ros-args -r output:=/rexrov/cmd_vel"
echo ""
