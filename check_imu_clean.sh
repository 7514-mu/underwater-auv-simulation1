#!/bin/bash
# 超简洁版IMU查看器

echo "💡 IMU实时数据（每秒刷新一次，按Ctrl+C停止）"
echo "=================================="
echo ""

while true; do
    # 获取IMU数据
    DATA=$(ros2 topic echo /rexrov/imu --once 2>/dev/null)

    if [ -z "$DATA" ]; then
        echo "❌ 未接收到IMU数据"
        sleep 2
        continue
    fi

    # 提取关键数据（超简洁格式）
    ACC_X=$(echo "$DATA" | grep -A 3 "linear_acceleration:" | grep "x:" | awk '{print $2}')
    ACC_Y=$(echo "$DATA" | grep -A 3 "linear_acceleration:" | grep "y:" | awk '{print $2}')
    ACC_Z=$(echo "$DATA" | grep -A 3 "linear_acceleration:" | grep "z:" | awk '{print $2}')

    VEL_X=$(echo "$DATA" | grep -A 3 "angular_velocity:" | grep "x:" | awk '{print $2}')
    VEL_Y=$(echo "$DATA" | grep -A 3 "angular_velocity:" | grep "y:" | awk '{print $2}')
    VEL_Z=$(echo "$DATA" | grep -A 3 "angular_velocity:" | grep "z:" | awk '{print $2}')

    # 显示（一行搞定）
    printf "\r📊 加速度: X=%6.3f  Y=%6.3f  Z=%6.3f  |  🔄 角速度: X=%8.5f  Y=%8.5f  Z=%8.5f" \
        $ACC_X $ACC_Y $ACC_Z $VEL_X $VEL_Y $VEL_Z

    sleep 1
done
