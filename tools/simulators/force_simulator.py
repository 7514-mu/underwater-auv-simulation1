#!/usr/bin/env python3
"""
外力仿真器 - 通过推进器模拟真实的力
用于仿真碰撞、涡流等场景
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from gazebo_msgs.srv import GetEntityState
import numpy as np
import time
import threading
import math


class ForceSimulator(Node):
    """通过推进器模拟外力效果"""

    def __init__(self):
        super().__init__('force_simulator')

        self.namespace = 'rexrov'

        # 推进器发布者
        self.thruster_pubs = []
        for i in range(8):
            topic = f'/{self.namespace}/thrusters/id_{i}/input'
            pub = self.create_publisher(Float64, topic, 10)
            self.thruster_pubs.append(pub)

        # 状态订阅
        self.current_position = None
        self.state_client = self.create_client(GetEntityState, '/gazebo/get_entity_state')

        # 推进器分配矩阵（TAM）- 将力分配到各个推进器
        # RexROV有8个推进器：
        # 0,1: 前进(Surge)
        # 2,3: 悬浮(Heave，但实际上是侧向Sway)
        # 4,5: 后退(Surge)
        # 6,7: 侧向(Sway)和旋转(Yaw)

        self.force_active = False
        self.force_thread = None
        self.stop_flag = threading.Event()

        print("✅ 外力仿真器启动（通过推进器）")

    def get_current_position(self):
        """获取当前位置"""
        req = GetEntityState.Request()
        req.name = 'rexrov'
        req.reference_frame = 'world'

        future = self.state_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)

        if future.result() is not None:
            return future.result().state.pose.position
        return None

    def apply_impulse_force(self, force_x, force_y, force_z, duration=1.0):
        """
        施加瞬时力（碰撞）
        force_x, force_y, force_z: 力的分量（牛顿）
        duration: 持续时间（秒）
        """
        print(f"\n💥 碰撞仿真！")
        print(f"   力：Fx={force_x:.1f}N, Fy={force_y:.1f}N, Fz={force_z:.1f}N")
        print(f"   持续时间：{duration}秒")
        print(f"   通过推进器模拟...")

        # 将力分配到推进器
        # 简化分配策略：
        # X轴力 → 推进器0,1,4,5
        # Y轴力 → 推进器6,7
        # Z轴力 → 推进器2,3（如果有垂直推进器）

        thrust_commands = [0.0] * 8

        # X轴力分配
        if force_x != 0:
            surge_thrust = force_x / 4.0  # 分配到4个surge推进器
            if surge_thrust > 0:
                # 向前
                thrust_commands[0] = abs(surge_thrust)
                thrust_commands[1] = abs(surge_thrust)
            else:
                # 向后
                thrust_commands[4] = abs(surge_thrust)
                thrust_commands[5] = abs(surge_thrust)

        # Y轴力分配
        if force_y != 0:
            sway_thrust = force_y / 2.0  # 分配到2个sway推进器
            thrust_commands[6] = max(0.0, sway_thrust)
            thrust_commands[7] = max(0.0, sway_thrust)

        # Z轴力分配（如果有垂直推进器）
        if force_z != 0:
            heave_thrust = force_z / 4.0
            for i in range(4):
                thrust_commands[i] += max(0.0, heave_thrust)

        # 施加推力
        print(f"\n   推进器指令：")
        for i, thrust in enumerate(thrust_commands):
            if thrust > 0:
                print(f"     推进器{i}: {thrust:.1f}N")

        start_time = time.time()
        while time.time() - start_time < duration:
            for i in range(8):
                msg = Float64()
                msg.data = float(thrust_commands[i])
                self.thruster_pubs[i].publish(msg)
            time.sleep(0.01)

        print(f"\n   ✅ 碰撞仿真完成！")

    def apply_vortex_force(self, strength, duration=10.0):
        """
        施加涡流力（旋转力场）
        strength: 涡流强度（牛顿）
        duration: 持续时间（秒）
        """
        print(f"\n🌀 涡流仿真！")
        print(f"   强度：{strength}N")
        print(f"   持续时间：{duration}秒")
        print(f"   通过旋转力场模拟...")

        self.stop_flag.clear()
        self.force_active = True

        def vortex_task():
            start_time = time.time()
            count = 0

            while not self.stop_flag.is_set() and (time.time() - start_time) < duration:
                t = time.time() - start_time

                # 旋转的力场（涡流）
                # 力的方向随时间旋转
                angle = 2 * math.pi * t * 0.5  # 0.5 Hz旋转

                force_x = strength * math.cos(angle)
                force_y = strength * math.sin(angle)

                # 分配到推进器
                thrust_commands = [0.0] * 8

                # X分量
                if force_x > 0:
                    thrust_commands[0] = force_x / 2.0
                    thrust_commands[1] = force_x / 2.0
                else:
                    thrust_commands[4] = abs(force_x) / 2.0
                    thrust_commands[5] = abs(force_x) / 2.0

                # Y分量
                thrust_commands[6] = max(0.0, force_y)
                thrust_commands[7] = max(0.0, force_y)

                # 发布推力
                for i in range(8):
                    msg = Float64()
                    msg.data = float(thrust_commands[i])
                    self.thruster_pubs[i].publish(msg)

                count += 1
                if count % 10 == 0:  # 每0.1秒
                    print(f"   🌀 涡流中... t={t:.1f}s, Fx={force_x:.1f}N, Fy={force_y:.1f}N")

                time.sleep(0.01)

            self.force_active = False
            print(f"\n   ✅ 涡流仿真完成！")

        self.force_thread = threading.Thread(target=vortex_task)
        self.force_thread.start()

        print(f"   ✅ 涡流已启动（将持续{duration}秒）")

    def apply_turbulence_force(self, intensity, duration=10.0):
        """
        施加湍流力（随机扰动）
        intensity: 湍流强度（牛顿）
        duration: 持续时间（秒）
        """
        print(f"\n⚡ 湍流仿真！")
        print(f"   强度：{intensity}N")
        print(f"   持续时间：{duration}秒")
        print(f"   通过随机扰动模拟...")

        self.stop_flag.clear()
        self.force_active = True

        def turbulence_task():
            start_time = time.time()
            count = 0

            while not self.stop_flag.is_set() and (time.time() - start_time) < duration:
                # 随机力
                force_x = np.random.uniform(-intensity, intensity)
                force_y = np.random.uniform(-intensity, intensity)
                force_z = np.random.uniform(-intensity/2, intensity/2)

                # 分配到推进器
                thrust_commands = [0.0] * 8

                if force_x > 0:
                    thrust_commands[0] = max(0.0, force_x / 2.0)
                    thrust_commands[1] = max(0.0, force_x / 2.0)
                else:
                    thrust_commands[4] = max(0.0, abs(force_x) / 2.0)
                    thrust_commands[5] = max(0.0, abs(force_x) / 2.0)

                thrust_commands[6] = max(0.0, force_y)
                thrust_commands[7] = max(0.0, force_y)

                # 发布推力
                for i in range(8):
                    msg = Float64()
                    msg.data = float(thrust_commands[i])
                    self.thruster_pubs[i].publish(msg)

                count += 1
                if count % 20 == 0:  # 每0.2秒
                    print(f"   ⚡ 湍流中... t={time.time()-start_time:.1f}s")

                time.sleep(0.01)

            self.force_active = False
            print(f"\n   ✅ 湍流仿真完成！")

        self.force_thread = threading.Thread(target=turbulence_task)
        self.force_thread.start()

        print(f"   ✅ 湍流已启动（将持续{duration}秒）")

    def stop_all_forces(self):
        """停止所有外力仿真"""
        print("\n🛑 停止所有外力仿真...")

        self.stop_flag.set()
        if self.force_thread:
            self.force_thread.join(timeout=2.0)

        # 停止所有推进器
        for i in range(8):
            msg = Float64()
            msg.data = 0.0
            self.thruster_pubs[i].publish(msg)

        self.force_active = False
        print("✅ 已停止")


def main():
    rclpy.init()

    simulator = ForceSimulator()

    print("\n" + "="*70)
    print("🎯 外力仿真系统 - 碰撞、涡流、湍流")
    print("="*70)
    print("\n说明：")
    print("  由于ApplyLinkWrench被UUV插件覆盖，我们通过推进器模拟外力")
    print("  这是在这个仿真环境中仿真外力的唯一方法")
    print()
    print("命令：")
    print("  1. 碰撞仿真：")
    print("     impulse <Fx> <Fy> <Fz> [duration]")
    print("     示例：impulse 5000 0 0       - X方向5000N碰撞")
    print("           impulse 0 3000 0 0.5   - Y方向3000N碰撞，持续0.5秒")
    print()
    print("  2. 涡流仿真：")
    print("     vortex <strength> [duration]")
    print("     示例：vortex 2000           - 强度2000N的涡流")
    print("           vortex 5000 15         - 强度5000N，持续15秒")
    print()
    print("  3. 湍流仿真：")
    print("     turbulence <intensity> [duration]")
    print("     示例：turbulence 1000        - 强度1000N的湍流")
    print()
    print("  4. 其他：")
    print("     stop                      - 停止所有外力")
    print("     pos                       - 查看当前位置")
    print("     q                         - 退出")
    print()
    print("="*70)

    try:
        while rclpy.ok():
            try:
                cmd = input("\n外力仿真> ").strip().lower()

                if not cmd:
                    continue

                if cmd == 'q':
                    simulator.stop_all_forces()
                    print("退出")
                    break

                elif cmd == 'stop':
                    simulator.stop_all_forces()

                elif cmd == 'pos':
                    pos = simulator.get_current_position()
                    if pos:
                        print(f"当前位置：X={pos.x:.3f}, Y={pos.y:.3f}, Z={pos.z:.3f}")

                elif cmd.startswith('impulse '):
                    parts = cmd.split()
                    try:
                        fx = float(parts[1])
                        fy = float(parts[2])
                        fz = float(parts[3]) if len(parts) > 3 else 0.0
                        duration = float(parts[4]) if len(parts) > 4 else 1.0

                        simulator.apply_impulse_force(fx, fy, fz, duration)
                    except (ValueError, IndexError):
                        print("❌ 命令格式错误")
                        print("   正确格式：impulse <Fx> <Fy> <Fz> [duration]")

                elif cmd.startswith('vortex '):
                    parts = cmd.split()
                    try:
                        strength = float(parts[1])
                        duration = float(parts[2]) if len(parts) > 2 else 10.0
                        simulator.apply_vortex_force(strength, duration)
                    except (ValueError, IndexError):
                        print("❌ 命令格式错误")
                        print("   正确格式：vortex <strength> [duration]")

                elif cmd.startswith('turbulence '):
                    parts = cmd.split()
                    try:
                        intensity = float(parts[1])
                        duration = float(parts[2]) if len(parts) > 2 else 10.0
                        simulator.apply_turbulence_force(intensity, duration)
                    except (ValueError, IndexError):
                        print("❌ 命令格式错误")
                        print("   正确格式：turbulence <intensity> [duration]")

                else:
                    print("❌ 未知命令")

            except KeyboardInterrupt:
                print("\n退出")
                simulator.stop_all_forces()
                break
            except Exception as e:
                print(f"❌ 错误：{e}")

    finally:
        simulator.stop_all_forces()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
