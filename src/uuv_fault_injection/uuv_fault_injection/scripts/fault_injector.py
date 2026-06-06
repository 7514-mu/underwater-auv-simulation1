#!/usr/bin/env python3
"""
AUV Fault Injection System
Injects various thruster faults for testing AUV robustness
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Wrench
import yaml
import random
import time
from threading import Thread
import os

class FaultInjector(Node):
    """Injects faults into AUV thruster system"""

    def __init__(self):
        super().__init__('fault_injector')

        # Robot namespace
        self.namespace = self.declare_parameter('namespace', 'rexrov').value
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

        # Subscribe to thruster manager input
        self.wrench_sub = self.create_subscription(
            Wrench,
            f'/{self.namespace}/thruster_manager/input',
            self.wrench_callback,
            10
        )

        # Fault injection service (simple keyboard trigger)
        self.create_timer(0.1, self.fault_loop)

        self.get_logger().info('=' * 60)
        self.get_logger().info('🔧 AUV Fault Injection System Initialized')
        self.get_logger().info('=' * 60)
        self.print_menu()

    def print_menu(self):
        """Print fault injection menu"""
        menu = """
╔════════════════════════════════════════════════════════════╗
║           🔧 AUV FAULT INJECTION SYSTEM                     ║
╠════════════════════════════════════════════════════════════╣
║  Fault Types:                                               ║
║                                                              ║
║  1️⃣  COMPLETE FAILURE    - Selected thrusters stop        ║
║  2️⃣  PARTIAL FAILURE     - Reduced efficiency (50%)       ║
║  3️⃣  STUCK THRUSTER      - Locked at current thrust       ║
║  4️⃣  REVERSE THRUST      - Thrust direction reversed      ║
║  5️⃣  OSCILLATING         - Random thrust fluctuations     ║
║  6️⃣  PROGRESSIVE         - Gradual efficiency degradation  ║
║                                                              ║
║  Control Commands:                                          ║
║  - inject <type> <thrusters> <duration>                    ║
║    Example: inject 1 0,3,5 10  (thrusters 0,3,5 fail 10s)  ║
║  - clear                      - Clear all faults           ║
║  - status                     - Show fault status          ║
║  - menu                       - Show this menu             ║
║                                                              ║
║  Thruster Index (RexROV 8 thrusters):                       ║
║  0,1: Front/Surge  2,3: Middle/Sway   4,5: Rear/Surge     ║
║  6: Heave (Z)      7: Yaw                                   ║
╚════════════════════════════════════════════════════════════╝
        """
        self.get_logger().info(menu)

    def thruster_callback(self, msg, thruster_idx):
        """Store original thruster commands"""
        if not self.fault_active:
            self.current_commands[thruster_idx] = msg.value

    def wrench_callback(self, msg):
        """Monitor wrench commands (for debugging)"""
        pass

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
            1: "COMPLETE FAILURE",
            2: "PARTIAL FAILURE (50%)",
            3: "STUCK THRUSTER",
            4: "REVERSE THRUST",
            5: "OSCILLATING",
            6: "PROGRESSIVE DEGRADATION"
        }

        self.get_logger().warning('=' * 60)
        self.get_logger().warning(f'⚠️  FAULT INJECTED: {fault_names[fault_type]}')
        self.get_logger().warning(f'📍 Affected Thrusters: {thrusters}')
        self.get_logger().warning(f'⏱️  Duration: {duration}s')
        self.get_logger().warning('=' * 60)

    def clear_fault(self):
        """Clear all faults"""
        self.fault_active = False
        self.fault_type = None
        self.affected_thrusters = []
        self.stuck_thrust_values = {}
        self.get_logger().info('✅ All faults cleared')

    def fault_loop(self):
        """Main fault injection loop - overrides thruster commands"""

        if not self.fault_active:
            return

        # Check if fault duration expired
        elapsed = time.time() - self.fault_start_time
        if elapsed >= self.fault_duration:
            self.get_logger().info('⏰ Fault duration expired, clearing fault')
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

    print("\n🔧 AUV Fault Injection System - Ready!")
    print("Type 'menu' for commands, 'inject <type> <thrusters> <duration>' to inject fault")

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
                    print(f"Fault Active: Type={fault_injector.fault_type}, "
                          f"Thrusters={fault_injector.affected_thrusters}, "
                          f"Remaining={remaining:.1f}s")
                else:
                    print("No active faults")

            elif parts[0] == 'inject':
                try:
                    fault_type = int(parts[1])
                    thrusters = [int(x) for x in parts[2].split(',')]
                    duration = float(parts[3])

                    if not (1 <= fault_type <= 6):
                        print("❌ Invalid fault type (1-6)")
                        continue

                    if any(t < 0 or t >= fault_injector.num_thrusters for t in thrusters):
                        print(f"❌ Invalid thruster index (0-{fault_injector.num_thrusters-1})")
                        continue

                    fault_injector.inject_fault(fault_type, thrusters, duration)

                except (IndexError, ValueError):
                    print("❌ Invalid command format")
                    print("Usage: inject <type> <thrusters> <duration>")
                    print("Example: inject 1 0,3,5 10")

            else:
                print("❌ Unknown command. Type 'menu' for help")

    except KeyboardInterrupt:
        pass
    finally:
        fault_injector.clear_fault()
        fault_injector.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
