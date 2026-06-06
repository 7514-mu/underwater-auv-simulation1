#!/bin/bash
# 故障注入系统启动脚本

echo "=========================================================================="
echo "💉 水下机器人故障注入系统"
echo "=========================================================================="
echo ""
echo "使用ApplyLinkWrench进行真实的物理故障注入"
echo ""

# Source ROS 2环境
source ~/.zshrc

# 运行故障注入系统
python3 ~/ros2_ws/fault_injector_complete.py
