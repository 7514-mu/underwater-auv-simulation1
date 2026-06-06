#!/usr/bin/env python3
"""
完整的水下机器人故障注入系统
使用正确的ApplyLinkWrench格式
"""

import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import ApplyLinkWrench, GetEntityState
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import Wrench, Vector3
import time
import threading
import math

class FaultInjector(Node):
    def __init__(self):
        super().__init__('fault_injector')

        self.namespace = 'rexrov'

        # 创建服务客户端
        self.wrench_client = self.create_client(
            ApplyLinkWrench, '/apply_link_wrench')
        self.state_client = self.create_client(
            GetEntityState, '/gazebo/get_entity_state')

        self.active_faults = []

        print("✅ 故障注入系统启动")
        print("="*70)
        print("使用正确的ApplyLinkWrench格式")
        print("="*70)

    def get_position(self):
        """获取机器人当前位置"""
        req = GetEntityState.Request()
        req.name = self.namespace
        req.reference_frame = 'world'

        future = self.state_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)

        if future.result() is not None:
            pos = future.result().state.pose.position
            return pos.x, pos.y, pos.z
        return None, None, None

    def apply_force(self, link_name, force, torque, duration_sec=-1):
        """
        施加外力（使用正确的格式）

        Args:
            link_name: link名称
            force: [x, y, z] 力（牛顿）
            torque: [x, y, z] 力矩（牛·米）
            duration_sec: 持续时间（秒），-1表示持续施加
        """
        if not self.wrench_client.wait_for_service(timeout_sec=1.0):
            print("❌ ApplyLinkWrench服务不可用")
            return False

        # 创建请求（使用正确的格式）
        request = ApplyLinkWrench.Request()
        request.link_name = f'{self.namespace}/{link_name}'
        request.reference_frame = 'world'

        # 正确格式：wrench: {force: {...}, torque: {...}}
        request.wrench.force.x = float(force[0])
        request.wrench.force.y = float(force[1])
        request.wrench.force.z = float(force[2])
        request.wrench.torque.x = float(torque[0])
        request.wrench.torque.y = float(torque[1])
        request.wrench.torque.z = float(torque[2])

        # 持续时间
        request.duration.sec = int(duration_sec)
        request.duration.nanosec = 0

        # 开始时间（0表示立即开始）
        request.start_time.sec = 0
        request.start_time.nanosec = 0

        # 调用服务
        future = self.wrench_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result() is not None:
            response = future.result()
            return response.success
        return False

    def clear_all_forces(self):
        """清除所有外力"""
        print("\n🔧 清除所有外力...")

        # 停止所有主动故障
        for fault in self.active_faults:
            fault['stop'].set()
        for fault in self.active_faults:
            fault['thread'].join(timeout=1.0)
        self.active_faults.clear()

        print("✅ 所有力已清除")

    def inject_collision(self, direction, force=10000, duration=2.0):
        """
        注入碰撞故障

        Args:
            direction: 'front', 'back', 'left', 'right', 'up', 'down'
            force: 碰撞力（牛顿）
            duration: 持续时间（秒）
        """
        direction_map = {
            'front': [1, 0, 0],    # 向前碰撞 → 向后的力
            'back': [-1, 0, 0],    # 向后碰撞 → 向前的力
            'left': [0, -1, 0],    # 向左碰撞 → 向右的力
            'right': [0, 1, 0],    # 向右碰撞 → 向左的力
            'up': [0, 0, -1],     # 向上碰撞 → 向下的力
            'down': [0, 0, 1]     # 向下碰撞 → 向上的力
        }

        if direction not in direction_map:
            print(f"❌ 未知方向: {direction}")
            return False

        vec = direction_map[direction]
        force_vec = [vec[0] * force, vec[1] * force, vec[2] * force]

        print(f"\n💥 注入碰撞：{direction}方向")
        print(f"   力：{force}N，持续{duration}秒")

        success = self.apply_force('base_link', force_vec, [0, 0, 0], duration)

        if success:
            print(f"   ✅ 碰撞已注入")
            if duration > 0:
                time.sleep(duration)
                print(f"   ✅ 碰撞结束")
        else:
            print(f"   ❌ 碰撞注入失败")

        return success

    def inject_vortex(self, strength=5000, duration=10.0):
        """
        注入涡流故障（旋转力场）

        Args:
            strength: 涡流强度（牛顿）
            duration: 持续时间（秒）
        """
        print(f"\n🌀 注入涡流故障")
        print(f"   强度：{strength}N·m，持续{duration}秒")

        # 涡流：施加旋转力矩
        success = self.apply_force('base_link', [0, 0, 0], [0, 0, strength], duration)

        if success:
            print(f"   ✅ 涡流已注入")
        else:
            print(f"   ❌ 涡流注入失败")

        return success

    def inject_turbulence(self, intensity=3000, duration=15.0):
        """
        注入湍流故障（随机扰动力）

        Args:
            intensity: 湍流强度（牛顿）
            duration: 持续时间（秒）
        """
        print(f"\n🌊 注入湍流故障")
        print(f"   强度：{intensity}N，持续{duration}秒")

        stop_event = threading.Event()

        def turbulence_task():
            start_time = time.time()
            while time.time() - start_time < duration and not stop_event.is_set():
                # 随机方向的力
                fx = (math.sin(time.time() * 5) * intensity * 0.5 +
                      (math.random() - 0.5) * intensity * 0.5)
                fy = (math.cos(time.time() * 3) * intensity * 0.5 +
                      (math.random() - 0.5) * intensity * 0.5)
                fz = (math.sin(time.time() * 7) * intensity * 0.3)

                self.apply_force('base_link', [fx, fy, fz], [0, 0, 0], 0.1)
                time.sleep(0.1)

        thread = threading.Thread(target=turbulence_task)
        thread.start()

        self.active_faults.append({
            'type': 'turbulence',
            'stop': stop_event,
            'thread': thread
        })

        print(f"   ✅ 湍流已启动（使用选项0停止）")
        return True

    def inject_magnetic_interference(self, sensor_type='magnetometer', duration=10.0):
        """
        注入磁场干扰（传感器噪声）

        Args:
            sensor_type: 传感器类型
            duration: 持续时间（秒）
        """
        print(f"\n🧲 注入磁场干扰")
        print(f"   传感器：{sensor_type}")
        print(f"   持续时间：{duration}秒")

        # 磁场干扰不是物理力，而是传感器噪声
        # 这里创建一个模拟的效果（轻微的随机力）
        stop_event = threading.Event()

        def magnetic_task():
            start_time = time.time()
            while time.time() - start_time < duration and not stop_event.is_set():
                # 磁场干扰导致的小幅随机力
                fx = (math.random() - 0.5) * 50  # ±25N
                fy = (math.random() - 0.5) * 50
                fz = (math.random() - 0.5) * 50

                self.apply_force('base_link', [fx, fy, fz], [0, 0, 0], 0.1)
                time.sleep(0.5)

        thread = threading.Thread(target=magnetic_task)
        thread.start()

        self.active_faults.append({
            'type': 'magnetic',
            'stop': stop_event,
            'thread': thread
        })

        print(f"   ✅ 磁场干扰已启动（使用选项0停止）")
        print(f"   注意：这是通过小扰动力模拟的效果")
        return True

    def show_menu(self):
        """显示菜单"""
        print("\n" + "="*70)
        print("💉 水下机器人故障注入系统")
        print("="*70)
        print("\n【物理故障】")
        print("  1. 碰撞 - 前方碰撞")
        print("  2. 碰撞 - 后方碰撞")
        print("  3. 碰撞 - 左侧碰撞")
        print("  4. 碰撞 - 右侧碰撞")
        print("  5. 碰撞 - 上浮碰撞")
        print("  6. 碰撞 - 下沉碰撞")
        print("  7. 涡流 - 旋转力场")
        print("  8. 湍流 - 随机扰动")
        print("\n【传感器/环境故障】")
        print("  9. 磁场干扰 - 影响导航")
        print("\n【控制】")
        print("  0. 停止所有故障")
        print("  q. 退出")
        print("="*70)

    def run_interactive(self):
        """交互式运行"""
        self.show_menu()

        while rclpy.ok():
            try:
                choice = input("\n请选择故障类型: ").strip()

                if not choice:
                    continue

                if choice == '0':
                    self.clear_all_forces()

                elif choice == '1':
                    self.inject_collision('front', force=10000, duration=2.0)

                elif choice == '2':
                    self.inject_collision('back', force=10000, duration=2.0)

                elif choice == '3':
                    self.inject_collision('left', force=10000, duration=2.0)

                elif choice == '4':
                    self.inject_collision('right', force=10000, duration=2.0)

                elif choice == '5':
                    self.inject_collision('up', force=8000, duration=2.0)

                elif choice == '6':
                    self.inject_collision('down', force=12000, duration=2.0)

                elif choice == '7':
                    strength = input("涡流强度 (N·m, 默认5000): ").strip()
                    strength = float(strength) if strength else 5000.0
                    duration = input("持续时间 (秒, 默认10): ").strip()
                    duration = float(duration) if duration else 10.0
                    self.inject_vortex(strength, duration)

                elif choice == '8':
                    intensity = input("湍流强度 (N, 默认3000): ").strip()
                    intensity = float(intensity) if intensity else 3000.0
                    duration = input("持续时间 (秒, 默认15): ").strip()
                    duration = float(duration) if duration else 15.0
                    self.inject_turbulence(intensity, duration)

                elif choice == '9':
                    sensor = input("传感器类型 (默认magnetometer): ").strip()
                    sensor = sensor if sensor else 'magnetometer'
                    duration = input("持续时间 (秒, 默认10): ").strip()
                    duration = float(duration) if duration else 10.0
                    self.inject_magnetic_interference(sensor, duration)

                elif choice == 'q':
                    print("\n退出系统")
                    self.clear_all_forces()
                    break

                else:
                    print("❌ 无效选择")

            except ValueError:
                print("❌ 输入格式错误")
            except Exception as e:
                print(f"❌ 错误: {e}")

def main():
    rclpy.init()

    try:
        injector = FaultInjector()
        injector.run_interactive()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
