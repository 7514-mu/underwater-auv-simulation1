#!/bin/bash
# RexROV 完整系统启动脚本
# 自动处理URDF生成并启动所有5个终端

echo "=== 🚀 RexROV 仿真系统启动 ==="
echo ""

# 检查URDF文件
URDF_FILE="$HOME/ros2_ws/install/uuv_descriptions/share/uuv_descriptions/robots/generated/rexrov/robot_description"

if [ ! -f "$URDF_FILE" ]; then
    echo "📝 URDF文件不存在，正在生成..."
    mkdir -p "$(dirname "$URDF_FILE")"
    cd ~/ros2_ws/install/uuv_descriptions/share/uuv_descriptions/robots
    xacro rexrov_default.xacro > generated/rexrov/robot_description
    if [ $? -eq 0 ]; then
        echo "✅ URDF生成成功"
    else
        echo "❌ URDF生成失败"
        exit 1
    fi
else
    echo "✅ URDF文件已存在"
fi

echo ""
echo "=== 请在新终端中执行以下命令 ==="
echo ""

# 终端1: Gazebo
echo "🖥️  终端1: Gazebo 仿真环境"
echo "source ~/.zshrc"
echo "ros2 launch uuv_gazebo_worlds ocean_waves.launch"
echo ""
echo "⏳ 等待20秒让Gazebo完全启动..."
echo ""

# 终端2: 机器人
echo "🤖 终端2: RexROV 机器人"
echo "source ~/.zshrc"
echo "ros2 launch uuv_descriptions upload_rexrov_default.launch.py mode:=default x:=0 y:=0 z:=-20 namespace:=rexrov gazebo_namespace:=\"''\""
echo ""

# 终端3: 推进器
echo "⚙️  终端3: 推进器管理器"
echo "source ~/.zshrc"
echo "ros2 launch uuv_thruster_manager thruster_manager.launch model_name:=rexrov"
echo ""

# 终端4: 命令转换
echo "🔄 终端4: 命令转换器"
echo "source ~/.zshrc"
echo "python3 ~/ros2_ws/cmd_vel_to_wrench_simple.py"
echo ""

# 终端5: 键盘控制
echo "🎮 终端5: 键盘控制"
echo "source ~/.zshrc"
echo "ros2 run uuv_teleop vehicle_keyboard_teleop.py --ros-args -r output:=/rexrov/cmd_vel"
echo ""

echo "=== 启动顺序 ==="
echo "1️⃣  先启动 终端1 (Gazebo)"
echo "2️⃣  等待20秒"
echo "3️⃣  启动 终端2 (机器人)"
echo "4️⃣  启动 终端3 (推进器)"
echo "5️⃣  启动 终端4 (命令转换)"
echo "6️⃣  启动 终端5 (键盘控制)"
echo ""
echo "✅ 准备完成！请按照顺序启动各终端。"
