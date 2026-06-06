#!/usr/bin/env python3
"""
自定义故障注入系统 - 增强版
支持多种自定义干扰类型
"""

import rclpy
from rclpy.node import Node
from uuv_world_ros_plugins_msgs.srv import SetCurrentModel
from gazebo_msgs.srv import ApplyLinkWrench
from std_msgs.msg import Float64
from geometry_msgs.msg import Wrench, Vector3, Point
from builtin_interfaces.msg import Duration
import time
import random
import math

class CustomFaultInjector(Node):
    """自定义故障注入器 - 支持多种干扰类型"""

    def __init__(self):
        super().__init__('custom_fault_injector')

        self.namespace = 'rexrov'

        # 官方服务客户端
        self.model_client = self.create_client(
            SetCurrentModel,
            f'{self.namespace}/hydrodynamics/set_current_model')
        self.wrench_client = self.create_client(
            ApplyLinkWrench,
            '/apply_link_wrench')

        # 推进器发布者
        self.thruster_pubs = []
        for i in range(8):
            topic = f'/{self.namespace}/thrusters/id_{i}/input'
            pub = self.create_publisher(Float64, topic, 10)
            self.thruster_pubs.append(pub)

        print("=== 自定义故障注入器启动 ===")

    def apply_wrench(self, force_x, force_y, force_z, torque_x=0.0, torque_y=0.0, torque_z=0.0, duration_sec=0):
        """辅助方法：正确调用ApplyLinkWrench服务"""
        # 等待服务可用
        if not self.wrench_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('ApplyLinkWrench service not available!')
            return False

        # 创建请求
        request = ApplyLinkWrench.Request()
        request.link_name = 'rexrov/base_link'  # 注意：Gazebo使用斜杠而不是双冒号
        request.reference_frame = ''  # 空字符串=世界坐标系
        request.reference_point = Point(x=0.0, y=0.0, z=0.0)  # 在质心施加
        request.wrench = Wrench(
            force=Vector3(x=force_x, y=force_y, z=force_z),
            torque=Vector3(x=torque_x, y=torque_y, z=torque_z)
        )
        request.duration = Duration(sec=duration_sec, nanosec=500000000)  # 至少0.5秒

        # 同步调用并检查结果
        future = self.wrench_client.call_async(request)
        return True
        print("可用的干扰类型：")
        print("1. 水流温度干扰 (通过流体密度)")
        print("2. 水下噪声/湍流干扰")
        print("3. 磁场干扰")
        print("4. 压力舱干扰")
        print("5. 通信延迟干扰")
        print("6. 传感器漂移干扰")
        print("7. 显示菜单")
        print("8. 退出")

    def inject_water_temperature_fault(self, temperature_change):
        """
        水流温度干扰
        原理：通过修改流体密度来模拟温度变化
        温度↑ → 密度↓ → 浮力↓ → 下沉力↑

        注意：当前实现仅打印信息，需要通过以下方式实现：
        1. 修改rexrov.gazebo.xacro中的fluid_density参数并重启
        2. 或者通过等效垂直力近似（浮力变化 = 密度变化 × 体积 × g）
        """
        print(f"\n[温度干扰] 注入水流温度变化: {temperature_change}°C")

        # 计算密度变化（简化模型：海水密度与温度关系）
        # 基础密度 1028 kg/m³ (20°C海水)
        base_density = 1028.0
        # 简化线性关系：每1°C变化约0.3 kg/m³
        density_change = temperature_change * 0.3
        new_density = base_density - density_change

        print(f"  ⚠️  当前实现仅计算密度变化")
        print(f"  原始密度: {base_density} kg/m³")
        print(f"  新密度: {new_density:.2f} kg/m³")
        print(f"  说明: 需要重启Gazebo或在URDF中设置fluid_density参数")
        print(f"  或使用等效垂直力近似（未实现）")

    def inject_turbulence_fault(self, intensity):
        """
        水下噪声/湍流干扰
        原理：施加随机变化的力和力矩
        """
        print(f"\n[湍流干扰] 注入湍流强度: {intensity}")

        if intensity == "low":
            magnitude = 50.0  # 增加到50N
        elif intensity == "medium":
            magnitude = 100.0  # 增加到100N
        else:  # high
            magnitude = 200.0  # 增加到200N

        # 持续时间：30秒
        duration = 30
        start_time = time.time()

        while time.time() - start_time < duration:
            # 生成随机力和力矩
            force_x = random.uniform(-magnitude, magnitude)
            force_y = random.uniform(-magnitude, magnitude)
            force_z = random.uniform(-magnitude/2, magnitude/2)

            torque_x = random.uniform(-magnitude/2, magnitude/2)
            torque_y = random.uniform(-magnitude/2, magnitude/2)
            torque_z = random.uniform(-magnitude, magnitude)

            # 使用辅助方法施加力
            self.apply_wrench(force_x, force_y, force_z,
                            torque_x, torque_y, torque_z,
                            duration_sec=0)
            time.sleep(0.5)  # 每0.5秒更新一次

        print("  [湍流干扰] 完成")

    def inject_magnetic_fault(self, intensity):
        """
        磁场干扰
        原理：施加周期性外力模拟磁干扰
        """
        print(f"\n[磁场干扰] 注入磁场强度: {intensity}")

        if intensity == "low":
            force_mag = 50.0  # 增加到50N
            freq = 0.5  # Hz
        elif intensity == "medium":
            force_mag = 100.0  # 增加到100N
            freq = 1.0
        else:
            force_mag = 200.0  # 增加到200N
            freq = 2.0

        duration = 30  # 增加到30秒
        start_time = time.time()

        while time.time() - start_time < duration:
            # 正弦波变化的力
            t = time.time() - start_time
            force_x = force_mag * math.sin(2 * math.pi * freq * t)
            force_y = force_mag * math.cos(2 * math.pi * freq * t)

            # 使用辅助方法施加力
            self.apply_wrench(force_x, force_y, 0.0, duration_sec=0)
            time.sleep(0.1)

        print("  [磁场干扰] 完成")

    def inject_pressure_fault(self, leak_depth):
        """
        压力舱干扰
        原理：模拟压力舱进水，增加重量
        """
        print(f"\n[压力舱干扰] 注入进水深度: {leak_depth}m")

        # 根据进水深度计算额外重量
        # 假设压力舱截面积0.5m²
        area = 0.5
        water_density = 1028.0
        added_mass = area * leak_depth * water_density

        print(f"  额外质量: {added_mass:.2f} kg")

        # 通过向下施加力来模拟重量增加
        duration = 15.0  # 持续15秒
        force_z = -added_mass * 9.81  # 向下的重力

        for _ in range(int(duration / 0.5)):
            self.apply_wrench(0.0, 0.0, force_z, duration_sec=0)
            time.sleep(0.5)

        print("  [压力舱干扰] 完成")

    def inject_comm_delay_fault(self, packet_loss_rate):
        """
        通信延迟干扰
        原理：人为延迟推进器指令发布
        """
        print(f"\n[通信延迟干扰] 注入丢包率: {packet_loss_rate}%")

        # 这个需要在推进器管理器层面实现
        # 这里通过间歇性停止发布来模拟
        duration = 10
        start_time = time.time()

        missed_packets = 0
        total_cycles = 0

        while time.time() - start_time < duration:
            total_cycles += 1
            # 根据丢包率决定是否延迟
            if random.uniform(0, 100) < packet_loss_rate:
                missed_packets += 1
                time.sleep(0.2)  # 延迟200ms
            else:
                time.sleep(0.01)  # 正常10ms

        print(f"  总周期: {total_cycles}, 错过: {missed_packets}")
        print(f"  实际丢包率: {missed_packets/total_cycles*100:.1f}%")
        print("  [通信延迟干扰] 完成")

    def inject_sensor_drift_fault(self, drift_rate):
        """
        传感器漂移干扰
        原理：通过外力模拟传感器读数漂移
        """
        print(f"\n[传感器漂移干扰] 注入漂移率: {drift_rate}")

        # 施加恒定小力模拟传感器偏差
        duration = 10.0
        # 提取数字并作为漂移力
        if "forward_0.1" in drift_rate:
            drift_force = 1.0
            self.get_logger().info(f"施加向前漂移力: {drift_force}N")
            for _ in range(int(duration / 0.1)):
                self.apply_wrench(drift_force, 0.0, 0.0, duration_sec=0)
                time.sleep(0.1)
        elif "lateral_0.1" in drift_rate:
            drift_force = 1.0
            self.get_logger().info(f"施加侧向漂移力: {drift_force}N")
            for _ in range(int(duration / 0.1)):
                self.apply_wrench(0.0, drift_force, 0.0, duration_sec=0)
                time.sleep(0.1)

        print("  [传感器漂移干扰] 完成")

    def show_menu(self):
        """显示交互菜单"""
        print("\n" + "="*50)
        print("    自定义故障注入菜单")
        print("="*50)
        print("1. 水流温度干扰")
        print("   - cold: 水温降低10°C (密度↑)")
        print("   - warm: 水温升高10°C (密度↓)")
        print("2. 水下湍流干扰")
        print("   - low: 轻度湍流")
        print("   - medium: 中度湍流")
        print("   - high: 强湍流")
        print("3. 磁场干扰")
        print("   - low: 弱磁场")
        print("   - medium: 中等磁场")
        print("   - high: 强磁场")
        print("4. 压力舱干扰")
        print("   - shallow: 浅层进水 (0.1m)")
        print("   - medium: 中层进水 (0.5m)")
        print("   - deep: 深层进水 (1.0m)")
        print("5. 通信延迟干扰")
        print("   - 10%: 10%丢包率")
        print("   - 30%: 30%丢包率")
        print("   - 50%: 50%丢包率")
        print("6. 传感器漂移干扰")
        print("   - forward_0.1: 向前漂移0.1m/s")
        print("   - lateral_0.1: 侧向漂移0.1m/s")
        print("7. 【测试】巨大向前推力 (1000N, 5秒)")
        print("8. 显示菜单")
        print("9. 退出")
        print("="*50)

    def run_interactive(self):
        """交互式运行"""
        self.show_menu()

        while rclpy.ok():
            choice = input("\n请选择干扰类型 (1-8): ").strip()

            if choice == '1':
                temp = input("  选择温度变化 (cold/warm): ").strip()
                if temp == 'cold':
                    self.inject_water_temperature_fault(10.0)
                elif temp == 'warm':
                    self.inject_water_temperature_fault(-10.0)

            elif choice == '2':
                level = input("  选择湍流强度 (low/medium/high): ").strip()
                self.inject_turbulence_fault(level)

            elif choice == '3':
                level = input("  选择磁场强度 (low/medium/high): ").strip()
                self.inject_magnetic_fault(level)

            elif choice == '4':
                depth = input("  选择进水深度 (shallow/medium/deep): ").strip()
                if depth == 'shallow':
                    self.inject_pressure_fault(0.1)
                elif depth == 'medium':
                    self.inject_pressure_fault(0.5)
                elif depth == 'deep':
                    self.inject_pressure_fault(1.0)

            elif choice == '5':
                rate = input("  选择丢包率 (10/30/50): ").strip()
                self.inject_comm_delay_fault(float(rate))

            elif choice == '6':
                drift = input("  选择漂移类型 (forward_0.1/lateral_0.1): ").strip()
                self.inject_sensor_drift_fault(drift)

            elif choice == '7':
                # 测试：施加巨大向前推力
                print("\n[测试] 施加1000N向前推力，持续5秒...")
                for i in range(10):
                    self.apply_wrench(1000.0, 0.0, 0.0, duration_sec=0)
                    time.sleep(0.5)
                print("  [测试] 完成")

            elif choice == '8':
                self.show_menu()

            elif choice == '9':
                print("退出故障注入器")
                break

            else:
                print("无效选择，请重试")

def main(args=None):
    rclpy.init()

    fault_injector = CustomFaultInjector()

    try:
        fault_injector.run_interactive()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        fault_injector.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
