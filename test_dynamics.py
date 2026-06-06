#!/usr/bin/env python3
"""
独立测试脚本：验证气泡动力学效应的数学计算
"""

import math

# ==============================================
# 测试参数配置
# ==============================================
BUBBLE_DENSITY = 0.3  # 气泡密度 (0~1)
ROBOT_VELOCITY = 1.0  # 机器人速度 (m/s)
ROBOT_VOLUME = 0.5    # 机器人体积 (m³)
ROBOT_CROSS_SECTION = 0.3  # 机器人横截面积 (m²)

# 物理常数
WATER_DENSITY = 998.2      # 水密度 (kg/m³)
GRAVITY = 9.81             # 重力加速度 (m/s²)
VISCOSITY = 1.002e-3       # 水的动力粘度 (Pa·s)
ALPHA_MAX = 0.15           # 气泡体积分数上限

# ==============================================
# 1. 阻力增加计算
# ==============================================
def compute_drag_force(bubble_density, velocity):
    """
    计算气泡引起的阻力增加
    
    公式：F_drag = 0.5 × ρ × Cd × A_eff × v²
    A_eff = A_base × (1 + K_AREA × α)
    α = bubble_density × α_max
    """
    Cd = 1.0        # 阻力系数 (方头ROV)
    K_AREA = 2.5    # Clift经验系数
    
    alpha = bubble_density * ALPHA_MAX
    A_eff = ROBOT_CROSS_SECTION * (1 + K_AREA * alpha)
    drag = 0.5 * WATER_DENSITY * Cd * A_eff * velocity**2
    
    return drag, alpha, A_eff

# ==============================================
# 2. 浮力变化计算
# ==============================================
def compute_buoyancy_change(bubble_density):
    """
    计算气泡引起的浮力变化
    
    公式：ΔF_buoyancy = ρ_water × g × V_bubble
    V_bubble = V_robot × α
    """
    alpha = bubble_density * ALPHA_MAX
    V_bubble = ROBOT_VOLUME * alpha
    buoyancy_change = WATER_DENSITY * GRAVITY * V_bubble
    
    return buoyancy_change, V_bubble

# ==============================================
# 3. 漂移力计算
# ==============================================
def compute_drift_force(bubble_density):
    """
    计算气泡上升引起的漂移力
    
    公式：F_drift = C_DRIFT × α × v_bubble × μ × A
    """
    C_DRIFT = 120.0      # 群体效应系数
    v_bubble = 0.35      # 气泡上升速度 (m/s)
    
    alpha = bubble_density * ALPHA_MAX
    drift = C_DRIFT * alpha * v_bubble * VISCOSITY * ROBOT_CROSS_SECTION
    
    return drift

# ==============================================
# 4. 振荡扰动计算
# ==============================================
def compute_perturbation(bubble_density):
    """
    计算气泡振荡引起的扰动力
    
    公式：F_perturb = k × bubble_density
    """
    k = 40.0  # 扰动强度系数
    perturbation = k * bubble_density
    
    return perturbation

# ==============================================
# 5. Minnaert振荡周期计算
# ==============================================
def compute_minnaert_frequency(bubble_radius=0.001):
    """
    计算气泡振荡频率
    
    公式：T_minnaert = 2πR × sqrt(ρ_water / (3γP₀))
    f_minnaert = 1 / T_minnaert
    """
    gamma = 1.4        # 空气绝热指数
    P0 = 101325        # 大气压 (Pa)
    
    T_minnaert = 2 * math.pi * bubble_radius * math.sqrt(WATER_DENSITY / (3 * gamma * P0))
    f_minnaert = 1 / T_minnaert
    
    return T_minnaert, f_minnaert

# ==============================================
# 主测试函数
# ==============================================
def main():
    print("=" * 60)
    print("          气泡动力学效应验证测试")
    print("=" * 60)
    print(f"测试参数：")
    print(f"  气泡密度 (bubble_density) = {BUBBLE_DENSITY}")
    print(f"  机器人速度 (v) = {ROBOT_VELOCITY} m/s")
    print(f"  机器人体积 (V_robot) = {ROBOT_VOLUME} m³")
    print(f"  机器人横截面积 (A) = {ROBOT_CROSS_SECTION} m²")
    print("-" * 60)
    
    # 1. 阻力计算
    drag, alpha, A_eff = compute_drag_force(BUBBLE_DENSITY, ROBOT_VELOCITY)
    print("\n【1】阻力增加")
    print(f"  气泡体积分数 α = {alpha:.4f}")
    print(f"  有效截面积 A_eff = {A_eff:.4f} m²")
    print(f"  阻力 F_drag = {drag:.4f} N")
    
    # 2. 浮力计算
    buoyancy_change, V_bubble = compute_buoyancy_change(BUBBLE_DENSITY)
    print("\n【2】浮力变化")
    print(f"  气泡体积 V_bubble = {V_bubble:.6f} m³")
    print(f"  浮力变化 ΔF_buoyancy = {buoyancy_change:.2f} N")
    
    # 3. 漂移力计算
    drift = compute_drift_force(BUBBLE_DENSITY)
    print("\n【3】漂移力")
    print(f"  漂移力 F_drift = {drift*1000:.4f} mN")  # 转换为mN
    
    # 4. 振荡扰动计算
    perturbation = compute_perturbation(BUBBLE_DENSITY)
    print("\n【4】振荡扰动")
    print(f"  扰动强度 F_perturb = {perturbation:.2f} N")
    
    # 5. 振荡频率计算
    T_1mm, f_1mm = compute_minnaert_frequency(0.001)  # 1mm气泡
    T_10mm, f_10mm = compute_minnaert_frequency(0.01)  # 10mm气泡
    print("\n【5】Minnaert振荡频率")
    print(f"  气泡半径 R = 1mm:")
    print(f"    振荡周期 T = {T_1mm*1000:.4f} ms")
    print(f"    振荡频率 f = {f_1mm:.1f} Hz")
    print(f"  气泡半径 R = 10mm:")
    print(f"    振荡周期 T = {T_10mm*1000:.4f} ms")
    print(f"    振荡频率 f = {f_10mm:.1f} Hz")
    
    # 汇总
    print("\n" + "-" * 60)
    print("【汇总】气泡密度=%.1f时的力学效应" % BUBBLE_DENSITY)
    print("-" * 60)
    print(f"  阻力增加:      {drag:.4f} N")
    print(f"  浮力变化:      {buoyancy_change:.2f} N (↑)")
    print(f"  漂移力:        {drift*1000:.4f} mN (↑)")
    print(f"  振荡扰动强度:  {perturbation:.2f} N")
    print("-" * 60)
    print("\n说明：")
    print("  - 阻力方向与速度相反")
    print("  - 浮力变化和漂移力方向向上")
    print("  - 振荡扰动方向随机但偏向上方")
    print("=" * 60)

if __name__ == "__main__":
    main()
