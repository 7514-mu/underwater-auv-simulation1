#!/usr/bin/env python3
"""
AUV Fault Monitor
Monitors AUV performance during fault injection
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Wrench
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import numpy as np

class FaultMonitor(Node):
    """Monitor AUV performance metrics during fault injection"""

    def __init__(self):
        super().__init__('fault_monitor')

        # Subscribe to odometry
        self.odom_sub = self.create_subscription(
            Odometry,
            '/rexrov/odom',
            self.odom_callback,
            10
        )

        # Subscribe to thruster commands
        self.thruster_subs = []
        for i in range(8):
            topic = f'/rexrov/thrusters/id_{i}/input'
            sub = self.create_subscription(
                # Float64,
                # topic,
                # lambda msg, idx=i: self.thruster_callback(msg, idx),
                # 10
            )
            self.thruster_subs.append(sub)

        # Data storage
        self.max_points = 500
        self.time_data = deque(maxlen=self.max_points)
        self.position_data = {
            'x': deque(maxlen=self.max_points),
            'y': deque(maxlen=self.max_points),
            'z': deque(maxlen=self.max_points)
        }
        self.velocity_data = {
            'x': deque(maxlen=self.max_points),
            'y': deque(maxlen=self.max_points),
            'z': deque(maxlen=self.max_points)
        }

        self.start_time = None
        self.current_pos = [0, 0, 0]
        self.current_vel = [0, 0, 0]

        self.get_logger().info('📊 Fault Monitor Started')

    def odom_callback(self, msg):
        """Process odometry data"""
        if self.start_time is None:
            self.start_time = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

        current_time = (msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9) - self.start_time

        # Store position
        self.current_pos = [
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            msg.pose.pose.position.z
        ]

        # Store velocity
        self.current_vel = [
            msg.twist.twist.linear.x,
            msg.twist.twist.linear.y,
            msg.twist.twist.linear.z
        ]

        # Update data
        self.time_data.append(current_time)
        self.position_data['x'].append(self.current_pos[0])
        self.position_data['y'].append(self.current_pos[1])
        self.position_data['z'].append(self.current_pos[2])
        self.velocity_data['x'].append(self.current_vel[0])
        self.velocity_data['y'].append(self.current_vel[1])
        self.velocity_data['z'].append(self.current_vel[2])

def main():
    rclpy.init()

    monitor = FaultMonitor()

    # Spin in background
    import threading
    spin_thread = threading.Thread(target=rclpy.spin, args=(monitor,), daemon=True)
    spin_thread.start()

    # Setup plots
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle('🔧 AUV Fault Monitor', fontsize=16, fontweight='bold')

    # Position plot
    ax1 = axes[0]
    ax1.set_title('Position')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Position (m)')
    ax1.grid(True, alpha=0.3)

    line_x, = ax1.plot([], [], 'r-', label='X', linewidth=2)
    line_y, = ax1.plot([], [], 'g-', label='Y', linewidth=2)
    line_z, = ax1.plot([], [], 'b-', label='Z', linewidth=2)
    ax1.legend()

    # Velocity plot
    ax2 = axes[1]
    ax2.set_title('Velocity')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Velocity (m/s)')
    ax2.grid(True, alpha=0.3)

    line_vx, = ax2.plot([], [], 'r-', label='Vx', linewidth=2)
    line_vy, = ax2.plot([], [], 'g-', label='Vy', linewidth=2)
    line_vz, = ax2.plot([], [], 'b-', label='Vz', linewidth=2)
    ax2.legend()

    def update(frame):
        if len(monitor.time_data) > 0:
            times = list(monitor.time_data)

            # Update position plot
            line_x.set_data(times, list(monitor.position_data['x']))
            line_y.set_data(times, list(monitor.position_data['y']))
            line_z.set_data(times, list(monitor.position_data['z']))

            ax1.set_xlim(max(0, times[-1] - 30), times[-1] + 1)
            ax1.set_ylim(
                min(min(monitor.position_data['x']), min(monitor.position_data['y']), min(monitor.position_data['z'])) - 1,
                max(max(monitor.position_data['x']), max(monitor.position_data['y']), max(monitor.position_data['z'])) + 1
            )

            # Update velocity plot
            line_vx.set_data(times, list(monitor.velocity_data['x']))
            line_vy.set_data(times, list(monitor.velocity_data['y']))
            line_vz.set_data(times, list(monitor.velocity_data['z']))

            ax2.set_xlim(max(0, times[-1] - 30), times[-1] + 1)
            ax2.set_ylim(-1.5, 1.5)

        return line_x, line_y, line_z, line_vx, line_vy, line_vz

    ani = FuncAnimation(fig, update, interval=100, blit=False)

    print("\n📊 Fault Monitor Running - Close plot window to exit")
    plt.tight_layout()
    plt.show()

    monitor.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
