#!/usr/bin/env python3
"""
交互式故障注入系统 - 超强版
效果增强，故障更明显！
"""

import rclpy
from rclpy.node import Node
from uuv_world_ros_plugins_msgs.srv import SetCurrentVelocity
from std_msgs.msg import Float64
import time
import random
import math
import threading
from std_srvs.srv import SetBool
from uuv_gazebo_ros_plugins_msgs.srv import SetThrusterEfficiency


class EnhancedFaultInjector(Node):
    def __init__(self):
        super().__init__('enhanced_fault_injector')

        self.namespace = '/rexrov'

        # 洋流服务客户端
        self.current_client = self.create_client(
            SetCurrentVelocity, '/hydrodynamics/set_current_velocity')

        # 推进器效率服务
        self.thruster_eff_clients = {}
        for i in range(8):
            eff_srv = f'{self.namespace}/thrusters/id_{i}/set_thrust_force_efficiency'
            self.thruster_eff_clients[i] = self.create_client(
                SetThrusterEfficiency, eff_srv)

        # 推进器指令发布者
        self.thruster_pubs = []
        for i in range(8):
            topic = f'{self.namespace}/thrusters/id_{i}/input'
            pub = self.create_publisher(Float64, topic, 10)
            self.thruster_pubs.append(pub)

        self.active_faults = []
        print("✅ 超强故障注入系统已启动")
        time.sleep(2)

    def clear_all_faults(self):
        """清除所有故障"""
        print("🔧 正在清除所有故障...")

        # 停止所有环境故障
        for fault in self.active_faults:
            fault['stop'].set()
        for fault in self.active_faults:
            fault['thread'].join(timeout=1.0)
        self.active_faults.clear()

        # 恢复推进器效率
        for i in range(8):
            try:
                req = SetThrusterEfficiency.Request()
                req.efficiency = 1.0
                future = self.thruster_eff_clients[i].call_async(req)
                rclpy.spin_until_future_complete(self, future, timeout_sec=0.5)
            except:
                pass

        # 清除洋流
        try:
            req = SetCurrentVelocity.Request()
            req.velocity = 0.0
            req.horizontal_angle = 0.0
            req.vertical_angle = 0.0
            future = self.current_client.call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
            print("   ✓ 洋流已停止")
        except:
            pass

        print("✅ 所有故障已清除\n")

    def inject_super_current(self, velocity, angle_deg=0):
        """超强洋流干扰"""
        angle_rad = math.radians(angle_deg)
        print(f"🌊 注入超强洋流：{velocity}m/s，方向{angle_deg}度")
        print(f"   ⚠️  机器人将被推动！请观察Gazebo！")

        req = SetCurrentVelocity.Request()
        req.velocity = float(velocity)
        req.horizontal_angle = float(angle_rad)
        req.vertical_angle = 0.0

        future = self.current_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)

        if future.result() and future.result().success:
            print("   ✅ 洋流已启动（使用选项0停止）\n")
        else:
            print("   ❌ 洋流启动失败\n")

    def inject_super_turbulence(self):
        """超强湍流 - 剧烈摇摆"""
        fault_name = "超强湍流"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  '{fault_name}' 已在运行")
            return

        print("⚡ 注入超强湍流干扰！")
        print("   效果：机器人将剧烈摇摆，难以控制")
        print("   ⭐ 持续运行，直到手动停止")

        stop_flag = threading.Event()

        def turbulence_task():
            # 打开所有推进器
            print("   🔧 打开所有推进器...")
            for i in range(8):
                try:
                    client = self.create_client(SetBool,
                        f'{self.namespace}/thrusters/id_{i}/set_thruster_state')
                    if client.wait_for_service(timeout_sec=0.5):
                        req = SetBool.Request()
                        req.data = True
                        future = client.call_async(req)
                        rclpy.spin_until_future_complete(self, future, timeout_sec=0.5)
                except:
                    pass
            print("   ✓ 准备完成，开始湍流干扰！")

            count = 0
            while not stop_flag.is_set():
                # 超强随机力
                for i in range(8):
                    noise = random.uniform(-150, 150)  # 增大到150
                    thrust = float(max(0.0, noise))
                    self.thruster_pubs[i].publish(Float64(data=thrust))

                count += 1
                if count % 4 == 0:  # 每2秒
                    print(f"   ⚡⚡⚡ 湍流干扰中！... (已运行{count//2}秒)")

                time.sleep(0.5)

        thread = threading.Thread(target=turbulence_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'stop': stop_flag,
            'thread': thread
        })

        print("   ✅ 超强湍流已启动！\n")

    def inject_super_magnetic(self):
        """超强磁场 - 剧烈旋转"""
        fault_name = "超强磁场"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  '{fault_name}' 已在运行")
            return

        print("🧲 注入超强磁场干扰！")
        print("   效果：机器人将剧烈旋转摆动")
        print("   ⭐ 持续运行，直到手动停止")

        stop_flag = threading.Event()

        def magnetic_task():
            print("   🔧 打开水平推进器...")
            for i in range(4, 8):
                try:
                    client = self.create_client(SetBool,
                        f'{self.namespace}/thrusters/id_{i}/set_thruster_state')
                    if client.wait_for_service(timeout_sec=0.5):
                        req = SetBool.Request()
                        req.data = True
                        future = client.call_async(req)
                        rclpy.spin_until_future_complete(self, future, timeout_sec=0.5)
                except:
                    pass
            print("   ✓ 准备完成，开始磁场干扰！")

            count = 0
            while not stop_flag.is_set():
                t = time.time()

                # 超强正弦波 - 2Hz
                surge = 150 * math.sin(4 * math.pi * t)
                sway = 150 * math.cos(4 * math.pi * t)

                self.thruster_pubs[4].publish(Float64(data=float(max(0.0, surge))))
                self.thruster_pubs[5].publish(Float64(data=float(max(0.0, -surge))))
                self.thruster_pubs[6].publish(Float64(data=float(max(0.0, sway))))
                self.thruster_pubs[7].publish(Float64(data=float(max(0.0, -sway))))

                count += 1
                if count % 20 == 0:
                    print(f"   🧲🧲🧲 磁场干扰中！... (已运行{count//10}秒)")

                time.sleep(0.1)

        thread = threading.Thread(target=magnetic_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'stop': stop_flag,
            'thread': thread
        })

        print("   ✅ 超强磁场已启动！\n")

    def inject_super_pressure(self):
        """超强压力舱进水 - 快速下沉"""
        fault_name = "超强进水"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  '{fault_name}' 已在运行")
            return

        print("💥 注入超强压力舱进水！")
        print("   效果：机器人将快速下沉")
        print("   ⭐ 持续运行，直到手动停止")

        stop_flag = threading.Event()
        extra_mass = 500  # kg
        extra_gravity = extra_mass * 9.81

        def pressure_task():
            print("   🔧 打开垂直推进器...")
            for i in range(4):
                try:
                    client = self.create_client(SetBool,
                        f'{self.namespace}/thrusters/id_{i}/set_thruster_state')
                    if client.wait_for_service(timeout_sec=0.5):
                        req = SetBool.Request()
                        req.data = True
                        future = client.call_async(req)
                        rclpy.spin_until_future_complete(self, future, timeout_sec=0.5)
                except:
                    pass
            print("   ✓ 准备完成，开始进水模拟！")

            count = 0
            while not stop_flag.is_set():
                # 超大下沉力
                extra_heave = -extra_gravity / 4.0

                for i in range(4):
                    thrust = float(max(0.0, abs(extra_heave) * 1.5))  # 增大1.5倍
                    self.thruster_pubs[i].publish(Float64(data=thrust))

                count += 1
                if count % 4 == 0:
                    print(f"   💧💧💧 进水中！机器人下沉... (已运行{count//2}秒)")

                time.sleep(0.5)

        thread = threading.Thread(target=pressure_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'stop': stop_flag,
            'thread': thread
        })

        print("   ✅ 超强进水已启动！\n")

    def inject_super_drift(self):
        """超强漂移 - 快速侧向移动"""
        fault_name = "超强漂移"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  '{fault_name}' 已在运行")
            return

        print("📈 注入超强漂移！")
        print("   效果：机器人将快速向Y轴方向漂移")
        print("   ⭐ 持续运行，直到手动停止")

        stop_flag = threading.Event()

        def drift_task():
            print("   🔧 打开侧向推进器...")
            for i in [6, 7]:
                try:
                    client = self.create_client(SetBool,
                        f'{self.namespace}/thrusters/id_{i}/set_thruster_state')
                    if client.wait_for_service(timeout_sec=0.5):
                        req = SetBool.Request()
                        req.data = True
                        future = client.call_async(req)
                        rclpy.spin_until_future_complete(self, future, timeout_sec=0.5)
                except:
                    pass
            print("   ✓ 准备完成，开始漂移！")

            count = 0
            while not stop_flag.is_set():
                # 超大漂移推力
                drift_thrust = 100.0  # 增大到100N
                self.thruster_pubs[6].publish(Float64(data=float(drift_thrust)))
                self.thruster_pubs[7].publish(Float64(data=float(drift_thrust)))

                count += 1
                if count % 4 == 0:
                    print(f"   📈📈📈 快速漂移中！... (已运行{count//2}秒)")

                time.sleep(0.5)

        thread = threading.Thread(target=drift_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'stop': stop_flag,
            'thread': thread
        })

        print("   ✅ 超强漂移已启动！\n")

    def show_active_faults(self):
        """显示活动故障"""
        if not self.active_faults:
            print("ℹ️  当前没有运行中的环境故障\n")
        else:
            print(f"📊 当前活动的故障 ({len(self.active_faults)}个)：")
            for i, fault in enumerate(self.active_faults, 1):
                print(f"   {i}. {fault['name']}")
            print()


def print_menu():
    print("\n" + "="*70)
    print("🔥 超强故障注入系统 - 效果增强版 🔥")
    print("="*70)
    print("【洋流干扰（官方方法，最有效）】")
    print("1 - 强洋流 X轴 2m/s")
    print("2 - 强洋流 Y轴 2m/s")
    print("3 - 超强洋流 X轴 5m/s")
    print("4 - 对角洋流 3m/s")
    print("\n【环境干扰（超强效果，持续运行）】")
    print("5 - ⚡ 超强湍流（剧烈摇摆）")
    print("6 - 🧲 超强磁场（剧烈旋转）")
    print("7 - 💥 超强进水（快速下沉）")
    print("8 - 📈 超强漂移（快速侧移）")
    print("\n【其他】")
    print("0 - 清除所有故障")
    print("9 - 查看当前活动故障")
    print("m - 显示菜单")
    print("q - 退出")
    print("="*70)
    print("\n💡 提示：")
    print("   - 洋流干扰（1-4）使用官方服务，效果最明显")
    print("   - 环境干扰（5-8）效果增强，可以清楚看到机器人运动")
    print("   - 所有环境故障持续运行，用选项0停止")
    print("   - 可以同时运行多个故障实现组合效果")
    print()


def main():
    rclpy.init()

    try:
        injector = EnhancedFaultInjector()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        rclpy.shutdown()
        return

    print_menu()

    try:
        while rclpy.ok():
            try:
                cmd = input("请选择: ").strip().lower()

                if not cmd:
                    continue

                elif cmd == '0':
                    injector.clear_all_faults()

                elif cmd == '1':
                    injector.inject_super_current(2.0, 0)  # X轴 2m/s

                elif cmd == '2':
                    injector.inject_super_current(2.0, 90)  # Y轴 2m/s

                elif cmd == '3':
                    injector.inject_super_current(5.0, 0)  # X轴 5m/s

                elif cmd == '4':
                    injector.inject_super_current(3.0, 45)  # 对角 3m/s

                elif cmd == '5':
                    injector.inject_super_turbulence()

                elif cmd == '6':
                    injector.inject_super_magnetic()

                elif cmd == '7':
                    injector.inject_super_pressure()

                elif cmd == '8':
                    injector.inject_super_drift()

                elif cmd == '9':
                    injector.show_active_faults()

                elif cmd == 'm':
                    print_menu()

                elif cmd == 'q':
                    print("\n👋 退出系统")
                    injector.clear_all_faults()
                    break

                else:
                    print("❌ 无效选项，输入m查看菜单\n")

            except KeyboardInterrupt:
                print("\n\n👋 用户中断")
                injector.clear_all_faults()
                break
            except Exception as e:
                print(f"❌ 错误: {e}\n")

    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
