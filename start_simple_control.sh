#!/bin/zsh
# 简单直接控制（只用加速度控制，更稳定）

source ~/.zshrc

export RCUTILS_LOGGING_SEVERITY=WARN
export RCUTILS_COLORIZED_OUTPUT=0

echo "启动简单控制系统（加速度直接控制）..."

# 只启动加速度控制器（不带级联）
ros2 run uuv_control_cascaded_pid acceleration_control.py \
  --ros-args \
  -r cmd_accel:=/rexrov/cmd_accel \
  -r thruster_manager/input:=/rexrov/thruster_manager/input \
  --params-file ~/ros2_ws/src/uuv_control/uuv_control_cascaded_pids/config/rexrov/inertial.yaml > /dev/null 2>&1 &

echo "✅ 简单控制系统已启动"
echo "键盘控制需要输出到 /rexrov/cmd_accel"
