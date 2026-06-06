#!/bin/bash
# 验证服务状态的脚本

source ~/.zshrc

echo "🔍 检查推进器服务状态"
echo "================================"
echo ""

# 检查推进器状态
for i in {0..7}; do
    echo "推进器${i}状态:"
    
    # 获取输入值
    input=$(ros2 topic echo /rexrov/thrusters/id_${i}/input --once 2>/dev/null | grep "data:" | awk '{print $2}')
    
    if [ -z "$input" ]; then
        echo "   ❌ 无数据"
    else
        echo "   📊 输入值: $input"
        
        # 判断是否故障
        if (( $(echo "$input == 0" | bc -l) )); then
            echo "   ⚠️  状态: 可能故障"
        else
            echo "   ✅ 状态: 正常工作"
        fi
    fi
    echo ""
done

echo "================================"
echo "💡 在终端4按W键可以看到推进器输入变化"
