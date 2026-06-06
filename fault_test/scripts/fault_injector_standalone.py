#!/usr/bin/env python3
"""
AUV Fault Injection System - Standalone Version
No compilation required - just run it directly!
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Wrench
import random
import time
from threading import Thread

class FaultInjector(Node):
    """Injects faults into AUV thruster system"""

    def __init__(self):
        super().__init__('fault_injector')

        # Robot namespace
        self.namespace = 'rexrov'
        self.num_thrusters = 8  # RexROV has 8 thrusters

        # Fault state
        self.fault_active = False
        self.fault_type = None
        self.affected_thrusters = []
        self.fault_start_time = 0
        self.fault_duration = 0

        # Original thruster commands (for stuck fault)
        self.stuck_thrust_values = {}

        # Publishers to override thruster commands
        self.thruster_pubs = []
        for i in range(self.num_thrusters):
            topic = f'/{self.namespace}/thrusters/id_{i}/input'
            pub = self.create_publisher(Float64, topic, 10)
            self.thruster_pubs.append(pub)

        # Subscribe to original thrust commands
        self.thruster_subs = []
        for i in range(self.num_thrusters):
            topic = f'/{self.namespace}/thrusters/id_{i}/input'
            sub = self.create_subscription(
                Float64,
                topic,
                lambda msg, idx=i: self.thruster_callback(msg, idx),
                10
            )
            self.thruster_subs.append(sub)

        # Store current commands
        self.current_commands = [0.0] * self.num_thrusters

        # Fault injection loop
        self.create_timer(0.1, self.fault_loop)

        self.get_logger().info('=' * 60)
        self.get_logger().info('🔧 AUV Fault Injection System Initialized')
        self.get_logger().info('=' * 60)
        self.print_menu()

    def print_menu(self):
        """Print fault injection menu"""
        menu = """
╔════════════════════════════════════════════════════════════╗
║           🔧 AUV 故障注入系统 (Fault Injection)             ║
╠════════════════════════════════════════════════════════════╣
║  故障类型 / Fault Types:                                   ║
║                                                              ║
║  1️⃣  COMPLETE FAILURE    - 推进器完全停止                  ║
║  2️⃣  PARTIAL FAILURE     - 效率降至50% / 50% efficiency    ║
║  3️⃣  STUCK THRUSTER      - 推进器卡死 / Stuck at current   ║
║  4️⃣  REVERSE THRUST      - 推力反向 / Reversed direction   ║
║  5️⃣  OSCILLATING         - 随机波动 / Random fluctuations  ║
║  6️⃣  PROGRESSIVE         - 渐进退化 / Gradual degradation  ║
║                                                              ║
║  控制命令 / Commands:                                       ║
║  inject <类型> <推进器> <持续时间>                          ║
║  Example: inject 1 0,3,5 10  (thrusters 0,3,5 fail 10s)    ║
║                                                              ║
║  clear  - 清除故障 / Clear all faults                      ║
║  status - 查看状态 / Show fault status                     ║
║  menu   - 帮助菜单 / Show this menu                        ║
║                                                              ║
║  推进器索引 / Thruster Index (RexROV):                      ║
║  0,1: 前/Surge  2,3: 中/Sway  4,5: 后/Surge                ║
║  6: 垂直/Heave  7: 偏航/Yaw                                 ║
╚════════════════════════════════════════════════════════════╝
        """
        print(menu)

    def thruster_callback(self, msg, thruster_idx):
        """Store original thruster commands"""
        if not self.fault_active:
            self.current_commands[thruster_idx] = msg.value

    def inject_fault(self, fault_type, thrusters, duration):
        """Inject a fault into specified thrusters"""
        self.fault_active = True
        self.fault_type = fault_type
        self.affected_thrusters = thrusters
        self.fault_start_time = time.time()
        self.fault_duration = duration

        # Store current values for stuck fault
        if fault_type == 3:  # STUCK
            for idx in thrusters:
                self.stuck_thrust_values[idx] = self.current_commands[idx]

        fault_names = {
            1: "完全失效 / COMPLETE FAILURE",
            2: "部分失效(50%) / PARTIAL FAILURE",
            3: "推进器卡死 / STUCK THRUSTER",
            4: "推力反向 / REVERSE THRUST",
            5: "推力振荡 / OSCILLATING",
            6: "渐进退化 / PROGRESSIVE DEGRADATION"
        }

        print('=' * 60)
        print(f'⚠️  故障注入 / FAULT INJECTED: {fault_names[fault_type]}')
        print(f'📍 影响推进器 / Affected Thrusters: {thrusters}')
        print(f'⏱️  持续时间 / Duration: {duration}s')
        print('=' * 60)

    def clear_fault(self):
        """Clear all faults"""
        self.fault_active = False
        self.fault_type = None
        self.affected_thrusters = []
        self.stuck_thrust_values = {}
        print('✅ 故障已清除 / All faults cleared')

    def fault_loop(self):
        """Main fault injection loop - overrides thruster commands"""

        if not self.fault_active:
            return

        # Check if fault duration expired
        elapsed = time.time() - self.fault_start_time
        if elapsed >= self.fault_duration:
            print('⏰ 故障时间到期，清除故障 / Fault duration expired')
            self.clear_fault()
            return

        # Apply fault to affected thrusters
        for i in range(self.num_thrusters):
            if i not in self.affected_thrusters:
                # Publish normal command
                msg = Float64()
                msg.data = self.current_commands[i]
                self.thruster_pubs[i].publish(msg)
            else:
                # Apply fault
                msg = Float64()

                if self.fault_type == 1:  # COMPLETE FAILURE
                    msg.data = 0.0

                elif self.fault_type == 2:  # PARTIAL FAILURE (50%)
                    msg.data = self.current_commands[i] * 0.5

                elif self.fault_type == 3:  # STUCK THRUSTER
                    msg.data = self.stuck_thrust_values[i]

                elif self.fault_type == 4:  # REVERSE THRUST
                    msg.data = -self.current_commands[i]

                elif self.fault_type == 5:  # OSCILLATING
                    noise = random.uniform(-0.3, 0.3)
                    msg.data = self.current_commands[i] + noise
                    msg.data = max(-1.0, min(1.0, msg.data))

                elif self.fault_type == 6:  # PROGRESSIVE DEGRADATION
                    progress = elapsed / self.fault_duration
                    efficiency = 1.0 - (0.8 * progress)  # Down to 20%
                    msg.data = self.current_commands[i] * efficiency

                self.thruster_pubs[i].publish(msg)

def main():
    rclpy.init()

    fault_injector = FaultInjector()

    # Start in a separate thread
    spin_thread = Thread(target=rclpy.spin, args=(fault_injector,), daemon=True)
    spin_thread.start()

    print("\n🔧 故障注入系统就绪 / Fault Injection System - Ready!")
    print("输入 'menu' 查看命令 / Type 'menu' for commands")

    try:
        while rclpy.ok():
            cmd = input("\nfault_injector> ").strip().lower()

            if not cmd:
                continue

            parts = cmd.split()

            if cmd == 'menu':
                fault_injector.print_menu()

            elif cmd == 'clear':
                fault_injector.clear_fault()

            elif cmd == 'status':
                if fault_injector.fault_active:
                    remaining = fault_injector.fault_duration - (time.time() - fault_injector.fault_start_time)
                    print(f"故障活跃 / Fault Active: 类型/Type={fault_injector.fault_type}, "
                          f"推进器/Thrusters={fault_injector.affected_thrusters}, "
                          f"剩余/Remaining={remaining:.1f}s")
                else:
                    print("无活跃故障 / No active faults")

            elif parts[0] == 'inject':
                try:
                    fault_type = int(parts[1])
                    thrusters = [int(x) for x in parts[2].split(',')]
                    duration = float(parts[3])

                    if not (1 <= fault_type <= 6):
                        print("❌ 无效故障类型 / Invalid fault type (1-6)")
                        continue

                    if any(t < 0 or t >= fault_injector.num_thrusters for t in thrusters):
                        print(f"❌ 无效推进器索引 / Invalid thruster index (0-{fault_injector.num_thrusters-1})")
                        continue

                    fault_injector.inject_fault(fault_type, thrusters, duration)

                except (IndexError, ValueError):
                    print("❌ 命令格式错误 / Invalid command format")
                    print("用法 / Usage: inject <type> <thrusters> <duration>")
                    print("示例 / Example: inject 1 0,3,5 10")

            else:
                print("❌ 未知命令 / Unknown command. 输入 'menu' 查看帮助 / Type 'menu' for help")

    except KeyboardInterrupt:
        pass
    finally:
        fault_injector.clear_fault()
        fault_injector.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
