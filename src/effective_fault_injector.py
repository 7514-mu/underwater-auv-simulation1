#!/usr/bin/env python3
"""
有效的故障注入系统 - 将外力转换为推进器指令修改
原理：通过修改推进器管理器的输入指令来模拟外力干扰效果
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist
import time
import random
import math
import threading


class EffectiveFaultInjector(Node):
    """通过修改推进器指令来模拟各种故障"""

    def __init__(self):
        super().__init__('effective_fault_injector')

        self.namespace = 'rexrov'

        # 订阅来自控制器的指令（如果有）
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            f'/{self.namespace}/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        # 创建推进器指令发布者
        self.thruster_pubs = []
        for i in range(8):
            topic = f'/{self.namespace}/thrusters/id_{i}/input'
            pub = self.create_publisher(Float64, topic, 10)
            self.thruster_pubs.append(pub)

        self.fault_active = False
        self.current_fault = None

        # 存储当前控制指令
        self.current_cmd_vel = Twist()

        print("=== 有效故障注入系统启动 ===")
        print("原理：修改推进器指令来模拟外力干扰")
        print("这样故障效果会非常明显！")
        print()

    def cmd_vel_callback(self, msg):
        """接收速度指令"""
        self.current_cmd_vel = msg

    def get_thruster_outputs(self, surge, sway, heave, roll, pitch, yaw):
        """
        根据6自由度输出，计算8个推进器的推力
        使用简化的TAM矩阵（逆变换）
        """
        # RexROV 8推进器TAM矩阵（简化版）
        # 这是一个6x8矩阵，将[Fx, Fy, Fz, Mx, My, Mz]转换为8个推进器推力
        # 这里使用近似计算

        # 简化：只考虑主要的推进器
        # T0-T3: 垂直推进器
        # T4-T7: 水平推进器

        thrusters = [0.0] * 8

        # 垂直推进器 (T0-T3) 主要负责heave (z)
        # 假设每个推力贡献0.24倍的heave力
        if heave != 0:
            for i in range(4):
                thrusters[i] += heave * 0.24

        # 水平推进器 (T4-T7) 负责surge (x) 和 sway (y)
        # T4, T5: 主要负责surge
        # T6, T7: 主要负责sway
        # 根据TAM矩阵的系数
        if surge != 0:
            thrusters[4] += surge * 0.707
            thrusters[5] += surge * 0.707

        if sway != 0:
            thrusters[6] += sway * 0.707
            thrusters[7] += sway * 0.707

        return thrusters

    def inject_turbulence_fault(self, intensity, duration=10):
        """
        湍流干扰 - 通过添加随机噪声到推进器指令
        """
        print(f"\n[湍流干扰] 强度: {intensity}, 持续: {duration}秒")
        print("  效果: 推进器指令会随机变化，机器人会摇摆")

        if intensity == "low":
            magnitude = 20.0
        elif intensity == "medium":
            magnitude = 50.0
        else:  # high
            magnitude = 100.0

        start_time = time.time()

        while time.time() - start_time < duration:
            # 获取当前基本推力（假设静止状态为0）
            base_thrusts = [0.0] * 8

            # 添加湍流噪声
            noisy_thrusts = []
            for i in range(8):
                noise = random.uniform(-magnitude, magnitude)
                noisy_thrusts.append(max(0, base_thrusts[i] + noise))

            # 发布修改后的指令
            for i in range(8):
                self.thruster_pubs[i].publish(Float64(data=noisy_thrusts[i]))

            time.sleep(0.5)

            if int(time.time() - start_time) % 2 == 0:
                print(f"  湍流进行中... ({int(time.time() - start_time)}/{duration}秒)")

        print("  ✓ 湍流干扰完成")

    def inject_magnetic_fault(self, intensity, duration=10):
        """
        磁场干扰 - 通过周期性修改推进器指令模拟
        """
        print(f"\n[磁场干扰] 强度: {intensity}, 持续: {duration}秒")
        print("  效果: 推进器指令会周期性变化，机器人会摆动")

        if intensity == "low":
            force_mag = 30.0
            freq = 0.5
        elif intensity == "medium":
            force_mag = 60.0
            freq = 1.0
        else:  # high
            force_mag = 100.0
            freq = 2.0

        start_time = time.time()

        while time.time() - start_time < duration:
            t = time.time() - start_time

            # 正弦波变化的力
            surge = force_mag * math.sin(2 * math.pi * freq * t)
            sway = force_mag * math.cos(2 * math.pi * freq * t)

            # 计算推进器推力
            thrusters = self.get_thruster_outputs(surge, sway, 0, 0, 0, 0)

            # 发布指令
            for i in range(8):
                self.thruster_pubs[i].publish(Float64(data=thrusters[i]))

            time.sleep(0.1)

            if int(time.time() - start_time) % 2 == 0:
                print(f"  磁场干扰中... ({int(time.time() - start_time)}/{duration}秒)")

        print("  ✓ 磁场干扰完成")

    def inject_pressure_fault(self, leak_depth, duration=15):
        """
        压力舱进水 - 通过增加垂直推力来模拟重量增加
        """
        print(f"\n[压力舱进水] 深度: {leak_depth}m, 持续: {duration}秒")
        print("  效果: 垂直推进器自动增大推力，机器人下沉")

        # 计算额外重量
        if leak_depth == "shallow":
            extra_mass_kg = 50
        elif leak_depth == "medium":
            extra_mass_kg = 250
        else:  # deep
            extra_mass_kg = 500

        # 额外重力 (N)
        extra_gravity = extra_mass_kg * 9.81

        print(f"  额外质量: {extra_mass_kg}kg")
        print(f"  补偿重力: {extra_gravity:.1f}N")

        # 通过增大垂直推力来补偿（模拟控制器响应）
        start_time = time.time()

        while time.time() - start_time < duration:
            # 向下的额外重力需要额外的向上推力
            extra_heave = -extra_gravity / 4.0  # 分配到4个垂直推进器

            # 发布补偿推力
            for i in range(4):
                base_thrust = 0.0
                compensated_thrust = base_thrust + extra_heave
                self.thruster_pubs[i].publish(Float64(data=compensated_thrust))

            time.sleep(0.5)

            if int(time.time() - start_time) % 3 == 0:
                print(f"  补偿中... ({int(time.time() - start_time)}/{duration}秒)")

        print("  ✓ 压力舱干扰完成")

    def inject_sensor_drift(self, drift_type, duration=10):
        """
        传感器漂移 - 通过修改控制指令来模拟
        """
        print(f"\n[传感器漂移] 类型: {drift_type}, 持续: {duration}秒")
        print("  效果: 机器人会向一侧漂移")

        start_time = time.time()

        while time.time() - start_time < duration:
            # 添加偏置到控制指令
            if "forward" in drift_type:
                # 向前漂移：总是添加向前的指令
                drift_thrust = 30.0
                # 分配到水平推进器
                self.thruster_pubs[4].publish(Float64(data=drift_thrust))
                self.thruster_pubs[5].publish(Float64(data=-drift_thrust))
            elif "lateral" in drift_type:
                # 侧向漂移
                drift_thrust = 30.0
                self.thruster_pubs[6].publish(Float64(data=drift_thrust))
                self.thruster_pubs[7].publish(Float64(data=-drift_thrust))

            time.sleep(0.5)

            if int(time.time() - start_time) % 3 == 0:
                print(f"  漂移中... ({int(time.time() - start_time)}/{duration}秒)")

        print("  ✓ 传感器漂移完成")

    def show_menu(self):
        print("\n" + "="*50)
        print("    有效故障注入系统（能看到明显效果）")
        print("="*50)
        print("1. 水下湍流干扰")
        print("   - low: 轻度湍流")
        print("   - medium: 中度湍流")
        print("   - high: 强湍流")
        print("2. 磁场干扰")
        print("   - low: 弱磁场")
        print("   - medium: 中等磁场")
        print("   - high: 强磁场")
        print("3. 压力舱进水干扰")
        print("   - shallow: 浅层进水")
        print("   - medium: 中层进水")
        print("   - deep: 深层进水")
        print("4. 传感器漂移干扰")
        print("   - forward_0.1: 向前漂移")
        print("   - lateral_0.1: 侧向漂移")
        print("5. 显示菜单")
        print("6. 退出")
        print("="*50)

    def run_interactive(self):
        self.show_menu()

        while rclpy.ok():
            choice = input("\n请选择故障类型 (1-6): ").strip()

            if choice == '1':
                level = input("  选择湍流强度 (low/medium/high): ").strip()
                self.inject_turbulence_fault(level, duration=15)

            elif choice == '2':
                level = input("  选择磁场强度 (low/medium/high): ").strip()
                self.inject_magnetic_fault(level, duration=15)

            elif choice == '3':
                depth = input("  选择进水深度 (shallow/medium/deep): ").strip()
                self.inject_pressure_fault(depth, duration=20)

            elif choice == '4':
                drift = input("  选择漂移类型 (forward_0.1/lateral_0.1): ").strip()
                self.inject_sensor_drift(drift, duration=15)

            elif choice == '5':
                self.show_menu()

            elif choice == '6':
                print("退出故障注入器")
                break

            else:
                print("无效选择，请重试")


def main(args=None):
    rclpy.init()
    injector = EffectiveFaultInjector()

    try:
        injector.run_interactive()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        injector.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
