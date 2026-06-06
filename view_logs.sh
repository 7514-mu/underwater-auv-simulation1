#!/bin/bash
# 日志查看器 - 查看所有测试记录

LOG_DIR=~/ros2_ws/fault_logs

echo "📊 AUV故障测试日志查看器"
echo "=" * 60
echo ""

# 检查日志目录是否存在
if [ ! -d "$LOG_DIR" ]; then
    echo "❌ 日志目录不存在: $LOG_DIR"
    echo "   请先运行 auto_logger.py 记录数据"
    exit 1
fi

# 列出所有日志文件
LOG_FILES=($(ls -t "$LOG_DIR"/test_*.log 2>/dev/null))

if [ ${#LOG_FILES[@]} -eq 0 ]; then
    echo "❌ 没有找到日志文件"
    echo "   请先运行 auto_logger.py 记录数据"
    exit 1
fi

echo "📁 找到 ${#LOG_FILES[@]} 个日志文件:"
echo ""

# 显示日志文件列表
for i in "${!LOG_FILES[@]}"; do
    LOG_FILE="${LOG_FILES[$i]}"
    BASENAME=$(basename "$LOG_FILE")
    FILE_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    MOD_TIME=$(stat -c %y "$LOG_FILE" | cut -d'.' -f1)
    LINE_COUNT=$(wc -l < "$LOG_FILE")

    printf "%2d) %s\\n" $((i+1)) "$BASENAME"
    printf "    大小: %s | 行数: %s | 修改时间: %s\\n\\n" "$FILE_SIZE" "$LINE_COUNT" "$MOD_TIME"
done

echo "=" * 60
echo ""

# 如果只有一个日志文件，直接显示
if [ ${#LOG_FILES[@]} -eq 1 ]; then
    echo "📄 显示最新的日志文件:"
    echo "===================="
    echo ""
    tail -50 "${LOG_FILES[0]}"
    exit 0
fi

# 多个文件时让用户选择
echo "💡 选择要查看的日志文件 (输入编号，或按Enter查看最新的):"
read -r choice

if [ -z "$choice" ]; then
    choice=1
fi

# 验证输入
if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt ${#LOG_FILES[@]} ]; then
    echo "❌ 无效的选择"
    exit 1
fi

SELECTED_FILE="${LOG_FILES[$((choice-1))]}"

echo ""
echo "📄 文件: $(basename "$SELECTED_FILE")"
echo "===================="
echo ""

# 询问显示方式
echo "请选择显示方式:"
echo "1) 显示全部内容"
echo "2) 显示最后50行"
echo "3) 显示前50行"
echo "4) 搜索特定内容"
echo ""
read -r display_choice

case $display_choice in
    1)
        cat "$SELECTED_FILE"
        ;;
    2)
        tail -50 "$SELECTED_FILE"
        ;;
    3)
        head -50 "$SELECTED_FILE"
        ;;
    4)
        echo "请输入搜索关键词:"
        read -r keyword
        grep -i "$keyword" "$SELECTED_FILE" || echo "未找到匹配内容"
        ;;
    *)
        echo "无效选择，显示最后50行"
        tail -50 "$SELECTED_FILE"
        ;;
esac
