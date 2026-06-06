#!/usr/bin/env python3
"""
声速计算和模拟工具
虽然Gazebo不模拟声速，但可以计算理论值
"""

def calculate_sound_speed(temp_c=20, salinity=35, depth=0):
    """
    计算海水中的声速

    UNESCO公式（简化）：
    c = 1449.2 + 4.6T - 0.055T² + 0.0003T³
        + (1.2 - 0.01T)(S - 35) + 0.016z

    参数：
    temp_c: 温度 (°C)
    salinity: 盐度 (‰)
    depth: 深度 (m)

    返回：
    声速 (m/s)
    """
    t = temp_c
    s = salinity
    z = depth

    # UNESCO公式
    c = (1449.2 +
         4.6 * t -
         0.055 * t**2 +
         0.0003 * t**3 +
         (1.2 - 0.01 * t) * (s - 35) +
         0.016 * z)

    return c

def main():
    print("="*70)
    print("🔊 声速计算器")
    print("="*70)
    print()

    # 默认参数
    temp = 20
    salinity = 35
    depth = 0

    print(f"【当前参数】")
    print(f"  温度: {temp}°C")
    print(f"  盐度: {salinity}‰")
    print(f"  深度: {depth}m")
    print()

    speed = calculate_sound_speed(temp, salinity, depth)
    print(f"【计算结果】")
    print(f"  声速: {speed:.2f} m/s")
    print()

    # 对比不同温度
    print("="*70)
    print("【温度对声速的影响】")
    print("="*70)
    print(f"{'温度(°C)':<10} {'声速(m/s)':<15} {'与标准差':<15}")
    print("-"*70)

    standard_speed = calculate_sound_speed(20, salinity, depth)

    for t in [0, 10, 15, 20, 25, 30]:
        s = calculate_sound_speed(t, salinity, depth)
        diff = s - standard_speed
        print(f"{t:<10} {s:<15.2f} {diff:+.2f}")

    print()
    print("【对测距的影响】")
    print()
    print("假设测量100m距离的目标：")
    print()

    for temp_c in [10, 20, 30]:
        c = calculate_sound_speed(temp_c, salinity, depth)
        time_flight = 2 * 100 / c  # 往返时间
        distance_calc_std = 1500 * time_flight / 2  # 用标准声速计算的距离
        distance_calc_actual = c * time_flight / 2  # 用实际声速计算的距离
        error = distance_calc_std - 100  # 误差

        print(f"{temp_c}°C: 实际声速={c:.1f} m/s")
        print(f"     实际距离=100.0m")
        print(f"     如果用1500 m/s计算：测量距离={distance_calc_std:.2f}m")
        print(f"     测量误差={error:+.2f}m")
        print()

    print("💡 结论：")
    print("   温度变化10°C → 声速变化约30-40 m/s")
    print("   对100m目标的测量误差约2-3m")
    print()
    print("💡 在Gazebo中：")
    print("   ❌ 不直接模拟声速")
    print("   ✅ 可以用这个工具计算理论值")
    print("   ✅ 在后处理中修正数据")

if __name__ == '__main__':
    main()
