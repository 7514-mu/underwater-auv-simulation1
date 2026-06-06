#!/bin/zsh
# 超安静键盘控制启动（修复版）

# 正确source ROS环境（zsh）
source /opt/ros/humble/setup.zsh
source ~/ros2_ws/install/setup.zsh

# 设置日志级别为ERROR（只显示错误）
export RCUTILS_LOGGING_SEVERITY=ERROR
export RCUTILS_COLORIZED_OUTPUT=0

# 启动键盘控制（安静模式）
ros2 run uuv_teleop vehicle_keyboard_teleop.py \
  --ros-args \
  -r output:=/rexrov/cmd_vel \
  --remap __name:=keyboard_teleop \
  --log-level error
