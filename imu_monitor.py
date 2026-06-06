#!/usr/bin/env python3
"""
超简洁版IMU显示器
一行显示所有关键数据
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

class SimpleIMUMonitor(Node):
    def __init__(self):
        super().__init__('simple_imu_monitor')

        print("💡 IMU实时监控（每秒刷新，按Ctrl+C停止）")
        print("=" * 70)

        # 订阅IMU
        self.imu_sub = self.create_subscription(Imu, '/rexrov/imu', self.imu_callback, 10)

        # 计数器（每秒打印一次）
        self.count = 0

    def imu_callback(self, msg):
        self.count += 1

        # 每50条打印一次（约1秒）
        if self.count % 50 == 0:
            # 提取数据
            ax = msg.linear_acceleration.x
            ay = msg.linear_acceleration.y
            az = msg.linear_acceleration.z

            wx = msg.angular_velocity.x
            wy = msg.angular_velocity.y
            wz = msg.angular_velocity.z

            # 两行显示
            print(f"\r📊 加速度 (m/s²):  X={ax:7.3f}  Y={ay:7.3f}  Z={az:7.3f}")
            print(f"🔄 角速度 (rad/s): X={wx:8.5f}  Y={wy:8.5f}  Z={wz:8.5f}\n", end='', flush=True)

def main():
    rclpy.init()

    try:
        monitor = SimpleIMUMonitor()
        rclpy.spin(monitor)
    except KeyboardInterrupt:
        print("\n\n👋 停止监控")
    finally:
        monitor.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
