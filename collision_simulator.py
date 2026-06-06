#!/usr/bin/env python3
"""
碰撞模拟器 - 通过推进器模拟碰撞效果
不需要ApplyLinkWrench，直接控制推进器产生瞬间冲击
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import time
import threading

class CollisionSimulator(Node):
    def __init__(self):
        super().__init__('collision_simulator')

        self.namespace = 'rexrov'

        # 创建8个推进器的发布者
        self.thruster_pubs = []
        for i in range(8):
            topic = f'/{self.namespace}/thrusters/id_{i}/input'
            pub = self.create_publisher(Float64, topic, 10)
            self.thruster_pubs.append(pub)

        print("✅ 碰撞模拟器启动")
        print("="*70)
        print("通过推进器模拟碰撞效果（不需要外力）")
        print("="*70)

    def simulate_collision(self, direction, force, duration=0.5):
        """
        模拟碰撞
        direction: 'front', 'back', 'left', 'right', 'up', 'down'
        force: 0-10000
        duration: 持续时间（秒）
        """
        print(f"\n💥 模拟{direction}方向碰撞！")
        print(f"   强度：{force}N")
        print(f"   持续：{duration}秒")

        # 碰撞策略：瞬间反向推进器推力
        thrust_commands = [0.0] * 8

        if direction == 'front':
            # 前方碰撞 → 后退推进器推
            thrust_commands[4] = force  # thruster 4,5
            thrust_commands[5] = force
        elif direction == 'back':
            # 后方碰撞 → 前进推进器推
            thrust_commands[0] = force
            thrust_commands[1] = force
        elif direction == 'left':
            # 左侧碰撞 → 反向右推
            thrust_commands[6] = force
            thrust_commands[7] = force
        elif direction == 'right':
            # 右侧碰撞 → 反向左推
            thrust_commands[6] = -force
            thrust_commands[7] = -force
        elif direction == 'up':
            # 下方碰撞 → 反向浮力
            thrust_commands[2] = force
            thrust_commands[3] = force
        elif direction == 'down':
            # 上方碰撞 → 反向下压
            thrust_commands[2] = -force
            thrust_commands[3] = -force

        # 施加推力
        print(f"\n推进器指令:")
        for i, thrust in enumerate(thrust_commands):
            if abs(thrust) > 0:
                print(f"  推进器{i}: {thrust:.1f}N")

        start_time = time.time()
        while time.time() - start_time < duration:
            for i in range(8):
                msg = Float64()
                msg.data = float(thrust_commands[i])
                self.thruster_pubs[i].publish(msg)
            time.sleep(0.01)

        # 停止推进器
        for i in range(8):
            msg = Float64()
            msg.data = 0.0
            self.thruster_pubs[i].publish(msg)

        print(f"\n✅ 碰撞模拟完成！")

def main():
    rclpy.init()
    simulator = CollisionSimulator()

    print("\n使用方法:")
    print("1. front  - 前方碰撞（如撞击墙壁）")
    print("2. back   - 后方碰撞")
    print("3. left   - 左侧碰撞")
    print("4. right  - 右侧碰撞")
    print("5. up     - 上浮碰撞")
    print("6. down   - 下沉碰撞")
    print()

    try:
        while rclpy.ok():
            cmd = input("碰撞方向 (front/back/left/right/up/down) 或 'q'退出: ").strip().lower()

            if cmd == 'q':
                break

            force = input("碰撞强度 (0-10000N, 默认5000): ").strip()
            force = float(force) if force else 5000.0

            duration = input("持续时间 (秒, 默认0.5): ").strip()
            duration = float(duration) if duration else 0.5

            if cmd in ['front', 'back', 'left', 'right', 'up', 'down']:
                simulator.simulate_collision(cmd, force, duration)

    except KeyboardInterrupt:
        print("\n退出")
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
