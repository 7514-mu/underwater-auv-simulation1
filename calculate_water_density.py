#!/usr/bin/env python3
"""
水密度与温度关系计算器
使用多种公式计算
"""

def density_pure_water_simple(temp_c):
    """
    纯水密度 - 简化公式
    ρ = ρ₀ × [1 - α(T - T₀)]
    """
    rho0 = 1000.0  # 4°C时的密度
    alpha = 0.000207  # 热膨胀系数
    t0 = 20.0  # 参考温度

    rho = rho0 * (1 - alpha * (temp_c - t0))
    return rho

def density_pure_water_precise(temp_c):
    """
    纯水密度 - 精确公式（0-100°C）
    标准大气压下
    """
    t = temp_c
    rho = (999.842594 +
           6.793952e-2 * t -
           9.095290e-3 * t**2 +
           1.001685e-4 * t**3 -
           1.120083e-6 * t**4 +
           6.536332e-9 * t**5)
    return rho

def density_sea_water(temp_c, salinity=35.0):
    """
    海水密度 - 简化UNESCO公式
    盐度35ppt，表面压力
    """
    t = temp_c
    s = salinity

    # 淡水部分
    rho_fresh = (999.842594 +
                 6.793952e-2 * t -
                 9.095290e-3 * t**2 +
                 1.001685e-4 * t**3 -
                 1.120083e-6 * t**4 +
                 6.536332e-9 * t**5)

    # 盐度修正
    rho = (rho_fresh +
           4.788 * s -
           1.117e-2 * s * t +
           2.717e-4 * s * t**2)

    return rho

def main():
    print("="*70)
    print("🌊 水密度与温度关系计算器")
    print("="*70)
    print()

    temperatures = [0, 5, 10, 15, 20, 25, 30, 35, 40]

    print("【纯水密度】")
    print(f"{'温度(°C)':<10} {'简化公式':<15} {'精确公式':<15} {'差异':<10}")
    print("-"*70)

    for temp in temperatures:
        rho_simple = density_pure_water_simple(temp)
        rho_precise = density_pure_water_precise(temp)
        diff = rho_precise - rho_simple

        print(f"{temp:<10} {rho_simple:<15.2f} {rho_precise:<15.2f} {diff:+.2f}")

    print()
    print("【海水密度】（盐度35ppt）")
    print(f"{'温度(°C)':<10} {'密度(kg/m³)':<15} {'与20°C差异':<15}")
    print("-"*70)

    rho_20 = density_sea_water(20)

    for temp in temperatures:
        rho = density_sea_water(temp)
        diff = rho - rho_20

        print(f"{temp:<10} {rho:<15.2f} {diff:+.2f}")

    print()
    print("【对水下机器人的影响】")
    print()
    print("假设机器人质量 = 1000kg, 体积 = 1m³")
    print()

    for temp in [20, 30, 40]:
        rho = density_sea_water(temp)
        buoyancy = rho * 9.81  # 浮力
        gravity = 1000 * 9.81  # 重力
        net_force = buoyancy - gravity  # 净力

        print(f"{temp}°C: 密度={rho:.1f} kg/m³")
        print(f"     浮力={buoyancy:.1f}N, 重力={gravity:.1f}N")
        print(f"     净力={net_force:.1f}N ", end="")

        if abs(net_force) < 1.0:
            print("(平衡)")
        elif net_force > 0:
            print("(上浮)")
        else:
            print("(下沉)")
        print()

if __name__ == '__main__':
    main()
