#!/usr/bin/env python3
"""
水温控制器 - 利用公式推断实现水温控制
原理：温度 → 公式计算密度 → 修改流体密度 → 物理效果
"""

import rclpy
from rclpy.node import Node
from uuv_gazebo_ros_plugins_msgs.srv import SetFloat

class WaterTemperatureController(Node):
    def __init__(self):
        super().__init__('water_temperature_controller')

        # 创建服务客户端
        self.density_client = self.create_client(
            SetFloat, '/rexrov/set_fluid_density')

        print("="*70)
        print("🌊 水温控制器（公式推断法）")
        print("="*70)
        print()
        print("💡 原理：温度 → 公式计算密度 → 修改仿真参数")
        print("   公式：ρ = 1000 - 0.2 × (T - 4)²")
        print()

        if not self.density_client.wait_for_service(timeout_sec=5.0):
            print("❌ set_fluid_density服务未就绪")
            print("💡 请确保Gazebo和机器人已启动")
            return

        print("✅ 服务已就绪")
        print()

    def temperature_to_density(self, temp_c):
        """
        温度 → 密度（公式推断）

        使用简化公式：
        ρ = 1000 - 0.2 × (T - 4)²

        其中：
        ρ = 密度 (kg/m³)
        T = 温度 (°C)

        注意：4°C时纯水密度最大（1000 kg/m³）
        """
        # 纯水密度公式
        if temp_c < 0:
            # 冰点以下，使用冰的密度
            rho = 917.0
        else:
            # 液态水
            rho = 1000.0 - 0.2 * (temp_c - 4)**2

        # 限制范围（物理合理性）
        rho = max(950.0, min(rho, 1000.0))

        return rho

    def set_temperature(self, temp_c):
        """
        设置水温（通过修改密度实现）

        步骤：
        1. 温度 → 密度（公式计算）
        2. 密度 → 仿真器（服务调用）
        """
        print(f"🎯 设置水温: {temp_c}°C")

        # 步骤1：温度 → 密度（公式推断）
        rho = self.temperature_to_density(temp_c)
        print(f"   📐 公式计算: ρ = 1000 - 0.2×({temp_c}-4)² = {rho:.2f} kg/m³")

        # 步骤2：密度 → 仿真器
        req = SetFloat.Request()
        req.data = float(rho)

        future = self.density_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result() is not None:
            response = future.result()
            if response.success:
                print(f"   ✅ 水温设置成功: {temp_c}°C (密度{rho:.2f} kg/m³)")

                # 显示预期效果
                self.show_temperature_effects(temp_c, rho)
            else:
                print(f"   ❌ 设置失败: {response.message}")
        else:
            print("   ❌ 设置超时")

        print()

    def show_temperature_effects(self, temp_c, rho):
        """显示温度变化的预期效果"""
        print(f"   💡 预期物理效果:")

        # 与标准温度（20°C）对比
        rho_std = 998.2
        diff_percent = (rho - rho_std) / rho_std * 100

        if abs(diff_percent) < 0.1:
            print(f"      • 浮力变化: < 0.1%（几乎无影响）")
        elif abs(diff_percent) < 0.5:
            print(f"      • 浮力变化: {diff_percent:+.1f}%（轻微影响）")
        elif abs(diff_percent) < 1.0:
            print(f"      • 浮力变化: {diff_percent:+.1f}%（明显影响）")
        else:
            print(f"      • 浮力变化: {diff_percent:+.1f}%（显著影响）")

        # 声速变化（信息）
        sound_speed_20 = 1521.0  # 20°C时的声速
        sound_speed = 1449.2 + 4.6*temp_c - 0.055*temp_c**2 + 0.0003*temp_c**3
        sound_diff = sound_speed - sound_speed_20

        print(f"      • 声速变化: {sound_diff:+.1f} m/s（仅信息，不影响仿真）")
        print(f"        → 20°C时声速约{sound_speed_20:.0f} m/s")
        print(f"        → {temp_c}°C时声速约{sound_speed:.0f} m/s")

def main():
    rclpy.init()

    try:
        controller = WaterTemperatureController()

        if not controller.density_client.wait_for_service(timeout_sec=1.0):
            return

        print("="*70)
        print("📊 水温与密度对照表")
        print("="*70)
        print(f"{'温度':<10} {'密度':<15} {'与标准差异'}")
        print("-"*70)

        for temp in [0, 10, 20, 30, 40]:
            rho = controller.temperature_to_density(temp)
            rho_std = 998.2
            diff = rho - rho_std
            print(f"{temp:<10} {rho:<15.2f} {diff:+.2f} kg/m³")

        print()
        print("="*70)
        print("🎮 交互式水温控制")
        print("="*70)
        print()
        print("【预设温度】")
        print("  1 - 0°C  (冰水)")
        print("  2 - 10°C (冷水)")
        print("  3 - 20°C (常温，默认)")
        print("  4 - 30°C (温水)")
        print("  5 - 40°C (热水)")
        print()
        print("【自定义温度】")
        print("  6 - 输入任意温度 (-10 ~ 100°C)")
        print()
        print("【其他】")
        print("  0 - 恢复默认温度 (20°C)")
        print("  q - 退出")
        print()

        # 预设温度
        preset_temps = {
            '1': 0,
            '2': 10,
            '3': 20,
            '4': 30,
            '5': 40
        }

        while rclpy.ok():
            try:
                choice = input("请选择: ").strip()

                if choice.lower() == 'q':
                    print("👋 退出水温控制器")
                    break

                if choice == '0':
                    controller.set_temperature(20)
                    print("   💡 已恢复默认温度")

                elif choice in preset_temps:
                    temp = preset_temps[choice]
                    controller.set_temperature(temp)

                elif choice == '6':
                    try:
                        temp = float(input("  输入温度 (°C): "))
                        if -10 <= temp <= 100:
                            controller.set_temperature(temp)
                        else:
                            print("   ❌ 温度超出范围 (-10 ~ 100°C)")
                    except ValueError:
                        print("   ❌ 无效输入")

                else:
                    print("   ❌ 无效选择")

            except ValueError:
                print("   ❌ 无效输入")
            except KeyboardInterrupt:
                print("\n👋 退出水温控制器")
                break

    except KeyboardInterrupt:
        print("\n👋 用户中断")
    finally:
        controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
