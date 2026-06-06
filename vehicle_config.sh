#!/bin/bash
# 车辆配置 - 只需修改这里就能切换任意模型
# 换模型？只改这3行

MODEL_NAME="missile_auv"           # 模型名称
URDF_FILE="$HOME/ros2_ws/missile_final.urdf"  # URDF文件路径
NAMESPACE="missile_auv"            # ROS命名空间

# 下面不用动
export VEHICLE_MODEL_NAME=$MODEL_NAME
export VEHICLE_URDF=$URDF_FILE
export VEHICLE_NAMESPACE=$NAMESPACE

echo "当前车辆配置:"
echo "  模型: $MODEL_NAME"
echo "  URDF: $URDF_FILE"
echo "  命名空间: $NAMESPACE"
