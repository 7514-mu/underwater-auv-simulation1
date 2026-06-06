#!/bin/bash
# 简单启动10推进器RexROV（无海洋环境）

echo "启动RexROV（10推进器）..."

# Source环境
source ~/.zshrc

# 启动robot_state_publisher和spawn
ros2 launch uuv_descriptions rexrov_default \
  x:=0 y:=0 z:=0.5 \
  namespace:=rexrov \
  gazebo_namespace:=""
