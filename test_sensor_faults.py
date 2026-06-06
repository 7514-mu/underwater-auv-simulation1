#!/usr/bin/env python3
"""
传感器故障测试脚本
用于测试IMU和磁力计故障注入功能

使用方法：
1. 启动Gazebo和RexROV
2. 启动控制器：ros2 launch uuv_trajectory_control rov_nmb_sm_controller.launch uuv_name:=rexrov
3. 发送目标：python3 go_to_target.py 10 0 -20
4. 在机器人移动过程中，运行此脚本注入传感器故障
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Vector3Stamped
import numpy as np
import time

class SensorFaultTester(Node):
    def __init__(self):
        super().__init__('sensor_fault_tester')

        # 创建发布者和订阅者
        self.imu_pub = self.create_publisher(Imu, '/rexrov/imu/data', 10)
        self.imu_sub = self.create_subscription(Imu, '/rexrov/imu/data_raw', self.imu_callback, 10)

        self.mag_pub = self.create_publisher(Vector3Stamped, '/rexrov/magnetometer', 10)
        self.mag_sub = self.create_subscription(Vector3Stamped, '/rexrov/magnetometer_raw', self.mag_callback, 10)

        # 故障参数
        self.imu_fault_active = False
        self.imu_noise_std = 0.05
        self.imu_bias = [0.05, 0.05, 0.05]
        self.imu_angular_noise = 0.02

        self.mag_fault_active = False
        self.mag_noise_std = 0.2
        self.mag_bias = [1.0, 1.0, 1.0]

        self.imu_count = 0
        self.mag_count = 0

        print("✅ 传感器故障测试器已启动")
        print("💡 请确保机器人正在导航中")
        print("💡 选择要测试的故障类型")
        print()

    def imu_callback(self, msg):
        """处理IMU数据"""
        if not self.imu_fault_active:
            # 直接转发
            self.imu_pub.publish(msg)
            return

        # 创建新消息
        noisy_msg = Imu()
        noisy_msg.header = msg.header
        noisy_msg.orientation = msg.orientation
        noisy_msg.orientation_covariance = msg.orientation_covariance

        # 注入噪声
        noisy_msg.linear_acceleration.x = msg.linear_acceleration.x + \
                                           np.random.normal(0, self.imu_noise_std) + self.imu_bias[0]
        noisy_msg.linear_acceleration.y = msg.linear_acceleration.y + \
                                           np.random.normal(0, self.imu_noise_std) + self.imu_bias[1]
        noisy_msg.linear_acceleration.z = msg.linear_acceleration.z + \
                                           np.random.normal(0, self.imu_noise_std) + self.imu_bias[2]
        noisy_msg.linear_acceleration_covariance = msg.linear_acceleration_covariance

        noisy_msg.angular_velocity.x = msg.angular_velocity.x + \
                                        np.random.normal(0, self.imu_angular_noise)
        noisy_msg.angular_velocity.y = msg.angular_velocity.y + \
                                        np.random.normal(0, self.imu_angular_noise)
        noisy_msg.angular_velocity.z = msg.angular_velocity.z + \
                                        np.random.normal(0, self.imu_angular_noise)
        noisy_msg.angular_velocity_covariance = msg.angular_velocity_covariance

        self.imu_pub.publish(noisy_msg)

        # 每100次打印一次
        self.imu_count += 1
        if self.imu_count % 100 == 0:
            print(f"   IMU: {self.imu_count} 条消息已注入噪声")

    def mag_callback(self, msg):
        """处理磁力计数据"""
        if not self.mag_fault_active:
            # 直接转发
            self.mag_pub.publish(msg)
            return

        # 创建新消息
        noisy_msg = Vector3Stamped()
        noisy_msg.header = msg.header

        # 注入噪声
        noisy_msg.vector.x = msg.vector.x + np.random.normal(0, self.mag_noise_std) + self.mag_bias[0]
        noisy_msg.vector.y = msg.vector.y + np.random.normal(0, self.mag_noise_std) + self.mag_bias[1]
        noisy_msg.vector.z = msg.vector.z + np.random.normal(0, self.mag_noise_std) + self.mag_bias[2]

        self.mag_pub.publish(noisy_msg)

        # 每100次打印一次
        self.mag_count += 1
        if self.mag_count % 100 == 0:
            print(f"   磁力计: {self.mag_count} 条消息已注入噪声")

    def test_imu_fault(self, duration=10):
        """测试IMU故障"""
        print("\n🧪 开始IMU故障测试（持续{}秒）".format(duration))
        print("   故障参数：")
        print("   - 加速度噪声: ±{} m/s²".format(self.imu_noise_std))
        print("   - 加速度偏置: [{}, {}, {}] m/s²".format(*self.imu_bias))
        print("   - 角速度噪声: ±{} rad/s".format(self.imu_angular_noise))
        print("   💡 观察机器人姿态抖动")

        self.imu_fault_active = True
        time.sleep(duration)
        self.imu_fault_active = False

        print("✅ IMU故障测试完成")

    def test_magnetometer_fault(self, duration=10):
        """测试磁力计故障"""
        print("\n🧪 开始磁力计故障测试（持续{}秒）".format(duration))
        print("   故障参数：")
        print("   - 磁场噪声: ±{} μT".format(self.mag_noise_std))
        print("   - 磁场偏置: [{}, {}, {}] μT".format(*self.mag_bias))
        print("   💡 观察机器人航向偏差")

        self.mag_fault_active = True
        time.sleep(duration)
        self.mag_fault_active = False

        print("✅ 磁力计故障测试完成")

    def test_combined_fault(self, duration=10):
        """测试组合故障"""
        print("\n🧪 开始IMU+磁力计组合故障测试（持续{}秒）".format(duration))
        print("   故障参数：")
        print("   - IMU: 加速度噪声±{} m/s²，角速度噪声±{} rad/s".format(
            self.imu_noise_std, self.imu_angular_noise))
        print("   - 磁力计: 磁场噪声±{} μT".format(self.mag_noise_std))
        print("   💡 观察组合故障效果")

        self.imu_fault_active = True
        self.mag_fault_active = True
        time.sleep(duration)
        self.imu_fault_active = False
        self.mag_fault_active = False

        print("✅ 组合故障测试完成")

def main():
    rclpy.init()

    try:
        tester = SensorFaultTester()

        print("请选择测试类型：")
        print("1 - IMU故障（中等强度，10秒）")
        print("2 - 磁力计故障（中等强度，10秒）")
        print("3 - IMU+磁力计组合故障（中等强度，10秒）")
        print("4 - 自定义测试")

        choice = input("\n请输入选项 (1-4): ").strip()

        if choice == '1':
            # 启动ROS节点
            rclpy.spin_once(tester, timeout_sec=0.1)
            tester.test_imu_fault(duration=10)

        elif choice == '2':
            rclpy.spin_once(tester, timeout_sec=0.1)
            tester.test_magnetometer_fault(duration=10)

        elif choice == '3':
            rclpy.spin_once(tester, timeout_sec=0.1)
            tester.test_combined_fault(duration=10)

        elif choice == '4':
            # 自定义测试
            try:
                duration = float(input("  持续时间（秒）: ").strip())
                fault_type = input("  故障类型 (imu/mag/both): ").strip().lower()

                rclpy.spin_once(tester, timeout_sec=0.1)

                if fault_type == 'imu':
                    intensity = input("  强度 (low/medium/high): ").strip().lower()
                    if intensity == 'low':
                        tester.imu_noise_std = 0.01
                        tester.imu_bias = [0.01, 0.01, 0.01]
                        tester.imu_angular_noise = 0.005
                    elif intensity == 'high':
                        tester.imu_noise_std = 0.15
                        tester.imu_bias = [0.1, 0.1, 0.1]
                        tester.imu_angular_noise = 0.1
                    tester.test_imu_fault(duration=duration)

                elif fault_type == 'mag':
                    intensity = input("  强度 (low/medium/high): ").strip().lower()
                    if intensity == 'low':
                        tester.mag_noise_std = 0.1
                        tester.mag_bias = [0.5, 0.5, 0.5]
                    elif intensity == 'high':
                        tester.mag_noise_std = 0.5
                        tester.mag_bias = [2.0, 2.0, 2.0]
                    tester.test_magnetometer_fault(duration=duration)

                elif fault_type == 'both':
                    tester.test_combined_fault(duration=duration)

                else:
                    print("❌ 无效的故障类型")

            except ValueError:
                print("❌ 无效的持续时间")

        else:
            print("❌ 无效的选项")

        print("\n💡 使用 Ctrl+C 退出")

        # 保持节点运行
        while rclpy.ok():
            rclpy.spin_once(tester, timeout_sec=0.1)

    except KeyboardInterrupt:
        print("\n\n👋 测试中断")
    finally:
        tester.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
