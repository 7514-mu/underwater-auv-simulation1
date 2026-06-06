#!/usr/bin/env python3
"""
真正的物理故障注入 - 直接对机器人本体施加外力
不通过推进器模拟，而是使用ApplyLinkWrench直接作用于机器人
"""

import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import ApplyLinkWrench
from geometry_msgs.msg import Wrench, Vector3
import time
import threading
import random
import math

class RealPhysicsFaultInjector(Node):
    def __init__(self):
        super().__init__('real_physics_fault_injector')

        self.namespace = 'rexrov'
        self.wrench_client = self.create_client(
            ApplyLinkWrench, '/apply_link_wrench')
        self.active_faults = []

        print("✅ 真正物理故障注入器启动")
        print("   所有外力直接作用于机器人本体")
        print("   不通过推进器模拟")

    def apply_force(self, force, torque, duration_sec=0.5):
        """施加外力"""
        req = ApplyLinkWrench.Request()
        req.link_name = f'{self.namespace}/base_link'
        req.reference_frame = 'world'
        req.reference_point.x = 0.0
        req.reference_point.y = 0.0
        req.reference_point.z = 0.0

        req.wrench.force.x = float(force[0])
        req.wrench.force.y = float(force[1])
        req.wrench.force.z = float(force[2])
        req.wrench.torque.x = float(torque[0])
        req.wrench.torque.y = float(torque[1])
        req.wrench.torque.z = float(torque[2])

        req.start_time.sec = 0
        req.start_time.nanosec = 0
        req.duration.sec = int(duration_sec)
        req.duration.nanosec = 0

        future = self.wrench_client.call_async(req)
        rclpy.spin_until_future_complete(future, timeout_sec=1.0)

    def inject_turbulence_real(self, intensity='medium'):
        """湍流 - 真正的随机扰动力"""
        fault_name = f"湍流({intensity})"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  故障 '{fault_name}' 已在运行")
            return

        if intensity == 'low':
            magnitude = 300.0
        elif intensity == 'medium':
            magnitude = 800.0
        else:  # high
            magnitude = 1500.0

        print(f"🌊 注入湍流故障（强度：{intensity}）")
        print("   直接对机器人施加随机扰动力")

        stop_event = threading.Event()

        def turbulence_task():
            count = 0
            while not stop_event.is_set():
                fx = random.gauss(0, magnitude)
                fy = random.gauss(0, magnitude)
                fz = random.gauss(0, magnitude * 0.3)

                self.apply_force([fx, fy, fz], [0, 0, 0], 0.1)

                count += 1
                if count % 10 == 0:
                    print(f"   湍流施加中... (count={count})")

                time.sleep(0.1)

            # 清除
            if fault_name in [f['name'] for f in self.active_faults]:
                self.active_faults = [f for f in self.active_faults if f['name'] != fault_name]

        thread = threading.Thread(target=turbulence_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'stop': stop_event,
            'thread': thread
        })

        print("✅ 湍流故障已启动（使用选项0停止）")

    def inject_magnetic_real(self, intensity='medium'):
        """磁场干扰 - 真正的随机扰动力"""
        fault_name = f"磁场({intensity})"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  故障 '{fault_name}' 已在运行")
            return

        if intensity == 'low':
            magnitude = 50.0
        elif intensity == 'medium':
            magnitude = 100.0
        else:  # high
            magnitude = 200.0

        print(f"🧲 注入磁场干扰（强度：{intensity}）")
        print("   直接对机器人施加小幅随机扰动力")

        stop_event = threading.Event()

        def magnetic_task():
            count = 0
            while not stop_event.is_set():
                # 磁场干扰产生小幅随机力
                fx = random.gauss(0, magnitude)
                fy = random.gauss(0, magnitude)
                fz = random.gauss(0, magnitude * 0.5)

                self.apply_force([fx, fy, fz], [0, 0, 0], 0.2)

                count += 1
                if count % 10 == 0:
                    print(f"   磁场干扰中... (count={count})")

                time.sleep(0.2)

            # 清除
            if fault_name in [f['name'] for f in self.active_faults]:
                self.active_faults = [f for f in self.active_faults if f['name'] != fault_name]

        thread = threading.Thread(target=magnetic_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'stop': stop_event,
            'thread': thread
        })

        print("✅ 磁场干扰已启动（使用选项0停止）")

    def inject_collision(self, direction, force=10000, duration=2.0):
        """碰撞 - 真正的冲击力"""
        direction_map = {
            'front': [1, 0, 0],
            'back': [-1, 0, 0],
            'left': [0, -1, 0],
            'right': [0, 1, 0],
            'up': [0, 0, -1],
            'down': [0, 0, 1]
        }

        if direction not in direction_map:
            print(f"❌ 未知方向: {direction}")
            return

        vec = direction_map[direction]
        force_vec = [vec[0] * force, vec[1] * force, vec[2] * force]

        print(f"💥 注入碰撞：{direction}方向，{force}N，{duration}秒")

        self.apply_force(force_vec, [0, 0, 0], duration)

        print(f"✅ 碰撞已施加")

    def stop_all(self):
        """停止所有故障"""
        print("🔧 停止所有故障...")
        for fault in self.active_faults:
            fault['stop'].set()
        for fault in self.active_faults:
            fault['thread'].join(timeout=1.0)
        self.active_faults.clear()
        print("✅ 所有故障已停止")

    def show_menu(self):
        print("\n" + "="*70)
        print("💉 真正物理故障注入系统")
        print("="*70)
        print("【直接对机器人本体施加外力】")
        print("  1. 碰撞 - 前方")
        print("  2. 碰撞 - 后方")
        print("  3. 碰撞 - 左侧")
        print("  4. 碰撞 - 右侧")
        print("  5. 碰撞 - 上方")
        print("  6. 碰撞 - 下方")
        print("  t. 湍流 - 随机扰动力")
        print("  m. 磁场干扰 - 小幅随机力")
        print("  0. 停止所有故障")
        print("  q. 退出")
        print("="*70)

    def run_interactive(self):
        self.show_menu()

        while rclpy.ok():
            try:
                choice = input("\n请选择: ").strip().lower()

                if choice == '0':
                    self.stop_all()

                elif choice == '1':
                    self.inject_collision('front', 10000, 2.0)

                elif choice == '2':
                    self.inject_collision('back', 10000, 2.0)

                elif choice == '3':
                    self.inject_collision('left', 10000, 2.0)

                elif choice == '4':
                    self.inject_collision('right', 10000, 2.0)

                elif choice == '5':
                    self.inject_collision('up', 8000, 2.0)

                elif choice == '6':
                    self.inject_collision('down', 12000, 2.0)

                elif choice == 't':
                    level = input("湍流强度 (low/medium/high, 默认medium): ").strip() or 'medium'
                    self.inject_turbulence_real(level)

                elif choice == 'm':
                    level = input("磁场强度 (low/medium/high, 默认medium): ").strip() or 'medium'
                    self.inject_magnetic_real(level)

                elif choice == 'q':
                    print("\n退出")
                    self.stop_all()
                    break

                else:
                    print("❌ 无效选择")

            except Exception as e:
                print(f"❌ 错误: {e}")

def main():
    rclpy.init()
    try:
        injector = RealPhysicsFaultInjector()
        injector.run_interactive()
    except KeyboardInterrupt:
        print("\n退出")
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
