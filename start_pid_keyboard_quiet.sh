#!/bin/zsh
# 安静的PID+键盘控制启动（全后台）

source ~/.zshrc
export RCUTILS_LOGGING_SEVERITY=ERROR
export RCUTILS_COLORIZED_OUTPUT=0

echo "正在启动PID控制系统+键盘控制（后台）..."

# 启动launch文件（后台，无输出）
ros2 launch uuv_control_cascaded_pid key_board_velocity.launch \
  model_name:=rexrov \
  uuv_name:=rexrov > /dev/null 2>&1 &

# 等待launch完成
sleep 8

echo "✅ PID控制系统+键盘控制已启动（后台模式）"
echo "=============================================="
echo "现在你可以直接按键控制机器人了！"
echo "控制说明："
echo "  W/S: 前进/后退"
echo "  A/D: 左移/右移"
echo "  Q/E: 左转/右转"
echo "  X/Z: 下潜/上浮"
echo "  1/2: 慢速/快速切换"
echo "=============================================="
