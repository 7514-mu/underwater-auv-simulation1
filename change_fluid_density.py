#!/usr/bin/env python3
"""
真实修改水体密度脚本
模拟水温变化对浮力和阻力的影响
"""

import rclpy
from rclpy.node import Node
from uuv_gazebo_ros_plugins_msgs.srv import SetFloat

class FluidDensityChanger(Node):
    def __init__(self):
        super().__init__('fluid_density_changer')

        # 创建服务客户端
        self.density_client = self.create_client(
            SetFloat, '/rexrov/set_fluid_density')

        if not self.density_client.wait_for_service(timeout_sec=5.0):
            print("❌ set_fluid_density服务未就绪")
            print("💡 请确保Gazebo和机器人已启动")
            return

        print("="*70)
        print("🌊 水体密度修改器 - 真实物理仿真")
        print("="*70)
        print()
        print("💡 水温与密度关系：")
        print("   温度↑ → 密度↓ → 浮力↓ → 机器人下沉")
        print("   温度↓ → 密度↑ → 浮力↑ → 机器人上浮")
        print()
        print("【典型密度值】")
        print("  1) 冰水 (0°C):     999.8 kg/m³")
        print("  2) 冷水 (10°C):    999.7 kg/m³")
        print("  3) 常温 (20°C):    998.2 kg/m³ ← 默认")
        print("  4) 温水 (30°C):    995.7 kg/m³")
        print("  5) 热水 (40°C):    992.2 kg/m³")
        print()

        # 测试不同密度
        print("🧪 测试不同密度的效果...")
        print()

        # 默认密度
        print("1️⃣  设置为默认密度 (20°C)")
        self.set_density(998.2)
        input("按Enter继续...")

        # 温水
        print("\n2️⃣  设置为温水密度 (30°C)")
        print("   预期：浮力减小，机器人微沉")
        self.set_density(995.7)
        input("按Enter继续...")

        # 热水
        print("\n3️⃣  设置为热水密度 (40°C)")
        print("   预期：浮力明显减小，机器人下沉")
        self.set_density(992.2)
        input("按Enter继续...")

        # 恢复默认
        print("\n4️⃣  恢复默认密度")
        self.set_density(998.2)

        print("\n✅ 测试完成")

    def set_density(self, density):
        """设置流体密度"""
        print(f"   🎯 正在设置密度为: {density} kg/m³")

        req = SetFloat.Request()
        req.data = float(density)

        future = self.density_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result() is not None:
            response = future.result()
            if response.success:
                print(f"   ✅ 密度设置成功: {density} kg/m³")
            else:
                print(f"   ❌ 设置失败: {response.message}")
        else:
            print("   ❌ 设置超时")

def main():
    rclpy.init()

    try:
        changer = FluidDensityChanger()
    except KeyboardInterrupt:
        print("\n\n👋 退出")
    finally:
        if rclpy.ok():
            changer.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()
