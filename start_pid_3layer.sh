#!/bin/bash
# 3层完整级联PID控制系统（位置+速度+加速度）

source ~/.zshrc 2>/dev/null

echo "=========================================="
echo "3层级联PID控制系统启动"
echo "=========================================="

# 第一步：彻底清理
echo ""
echo "步骤1: 清理旧进程..."
killall -9 acceleration_control.py velocity_control.py position_control.py 2>/dev/null
sleep 3

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

# 第五步：启动位置控制器 ⭐ 新增！
echo ""
echo "步骤5: 启动位置控制器..."
ros2 run uuv_control_cascaded_pid position_control.py \
  --ros-args \
  -r cmd_pose:=/rexrov/cmd_pose \
  -r odom:=/rexrov/pose_gt \
  -r cmd_vel:=/rexrov/cmd_vel \
  --params-file ~/ros2_ws/src/uuv_control/uuv_control_cascaded_pids/config/rexrov/pos_pid_control.yaml > /dev/null 2>&1 &
echo "PID: $!"
sleep 5

# 第六步：验证
echo ""
echo "=========================================="
echo "步骤6: 验证启动"
echo "=========================================="

sleep 2

# 检查节点数量
PC_COUNT=$(ros2 node list 2>/dev/null | grep -c "/position_control" || echo "0")
VC_COUNT=$(ros2 node list 2>/dev/null | grep -c "/velocity_control" || echo "0")
AC_COUNT=$(ros2 node list 2>/dev/null | grep -c "/acceleration_control" || echo "0")

echo ""
echo "位置控制器实例数: $PC_COUNT"
echo "速度控制器实例数: $VC_COUNT"
echo "加速度控制器实例数: $AC_COUNT"

if [ "$PC_COUNT" -eq 1 ] && [ "$VC_COUNT" -eq 1 ] && [ "$AC_COUNT" -eq 1 ]; then
    echo "✓ 控制器启动正常（单实例）"
elif [ "$PC_COUNT" -gt 1 ] || [ "$VC_COUNT" -gt 1 ] || [ "$AC_COUNT" -gt 1 ]; then
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
echo "已启动3层控制系统："
echo "  1. 位置控制器 ⭐ 新增"
	echo "  2. 速度控制器"
	echo "  3. 加速度控制器"
	echo "  4. 推进器管理器"
echo ""
echo "⚠️ 重要：位置控制器需要持续接收目标消息！"
echo ""
echo "在新终端发送目标位置："
echo "  source ~/.zshrc"
echo "  python3 ~/ros2_ws/send_goal_continuous_pose.py 5 0 -20"
echo ""
echo "或发送其他目标："
echo "  python3 ~/ros2_ws/send_goal_continuous_pose.py <x> <y> <z>"
echo ""
