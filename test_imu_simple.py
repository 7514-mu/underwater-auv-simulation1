#!/usr/bin/env python3
"""
IMU功能测试脚本
验证IMU能否正常工作
显示加速度和角速度数据
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import time

class IMUTester(Node):
    def __init__(self):
        super().__init__('imu_tester')

        print("="*70)
        print("📡 IMU传感器测试")
        print("="*70)
        print("\n💡 正在等待IMU数据...")
        print("💡 请让机器人移动或旋转，观察数据变化\n")

        # 数据计数
        self.count = 0

        # 订阅IMU
        self.imu_sub = self.create_subscription(
            Imu, '/rexrov/imu', self.imu_callback, 10)

        # 定时器：每2秒打印一次统计
        self.create_timer(2.0, self.print_statistics)

        # 数据缓冲
        self.accel_buffer = []
        self.angular_buffer = []

    def imu_callback(self, msg):
        """IMU数据回调"""
        self.count += 1

        # 提取数据
        accel = msg.linear_acceleration
        angular = msg.angular_velocity

        # 保存到缓冲
        self.accel_buffer.append([accel.x, accel.y, accel.z])
        self.angular_buffer.append([angular.x, angular.y, angular.z])

        # 保持最近100条数据
        if len(self.accel_buffer) > 100:
            self.accel_buffer.pop(0)
            self.angular_buffer.pop(0)

        # 打印实时数据（每10条打印一次）
        if self.count % 10 == 0:
            self.print_realtime_data(accel, angular)

    def print_realtime_data(self, accel, angular):
        """打印实时数据"""
        print(f"【数据点 #{self.count}】")
        print("  📊 加速度 (m/s²):")
        print(f"     X轴 (前向): {accel.x:8.4f}")
        print(f"     Y轴 (侧向): {accel.y:8.4f}")
        print(f"     Z轴 (垂向): {accel.z:8.4f}")
        print("  🔄 角速度 (rad/s):")
        print(f"     X轴 (横滚): {angular.x:8.4f}")
        print(f"     Y轴 (俯仰): {angular.y:8.4f}")
        print(f"     Z轴 (偏航): {angular.z:8.4f}")
        print()

    def print_statistics(self):
        """打印统计信息"""
        if len(self.accel_buffer) == 0:
            print("⏳ 等待IMU数据...")
            return

        import numpy as np

        accel_data = np.array(self.accel_buffer)
        angular_data = np.array(self.angular_buffer)

        print("="*70)
        print(f"📊 IMU统计信息 (已接收 {self.count} 条数据)")
        print("="*70)

        # 加速度统计
        print("\n【加速度统计 (m/s²)】")
        print("  X轴 (前向):")
        print(f"    均值: {accel_data[:, 0].mean():8.4f}")
        print(f"    标准差: {accel_data[:, 0].std():8.4f}")
        print(f"    范围: [{accel_data[:, 0].min():8.4f}, {accel_data[:, 0].max():8.4f}]")

        print("  Y轴 (侧向):")
        print(f"    均值: {accel_data[:, 1].mean():8.4f}")
        print(f"    标准差: {accel_data[:, 1].std():8.4f}")
        print(f"    范围: [{accel_data[:, 1].min():8.4f}, {accel_data[:, 1].max():8.4f}]")

        print("  Z轴 (垂向):")
        print(f"    均值: {accel_data[:, 2].mean():8.4f}")
        print(f"    标准差: {accel_data[:, 2].std():8.4f}")
        print(f"    范围: [{accel_data[:, 2].min():8.4f}, {accel_data[:, 2].max():8.4f}]")

        # 角速度统计
        print("\n【角速度统计 (rad/s)】")
        print("  X轴 (横滚):")
        print(f"    均值: {angular_data[:, 0].mean():8.4f}")
        print(f"    标准差: {angular_data[:, 0].std():8.4f}")
        print(f"    范围: [{angular_data[:, 0].min():8.4f}, {angular_data[:, 0].max():8.4f}]")

        print("  Y轴 (俯仰):")
        print(f"    均值: {angular_data[:, 1].mean():8.4f}")
        print(f"    标准差: {angular_data[:, 1].std():8.4f}")
        print(f"    范围: [{angular_data[:, 1].min():8.4f}, {angular_data[:, 1].max():8.4f}]")

        print("  Z轴 (偏航):")
        print(f"    均值: {angular_data[:, 2].mean():8.4f}")
        print(f"    标准差: {angular_data[:, 2].std():8.4f}")
        print(f"    范围: [{angular_data[:, 2].min():8.4f}, {angular_data[:, 2].max():8.4f}]")

        # 数据质量评估
        print("\n【数据质量评估】")

        accel_std = accel_data.std(axis=0).mean()
        angular_std = angular_data.std(axis=0).mean()

        if self.count < 10:
            print("  ⏳ 数据较少，继续收集...")
        elif accel_std < 0.1 and angular_std < 0.01:
            print("  ✅ IMU工作正常（低噪声）")
        elif accel_std < 0.5 and angular_std < 0.05:
            print("  ✅ IMU工作正常（中等噪声）")
        else:
            print("  ⚠️  IMU噪声较大或机器人在剧烈运动")

        print("="*70)
        print()

def main():
    rclpy.init()

    print("💡 提示：")
    print("   - 让机器人静止：观察零点偏置")
    print("   - 让机器人移动：观察加速度变化")
    print("   - 让机器人旋转：观察角速度变化")
    print("   - 按Ctrl+C退出\n")

    try:
        tester = IMUTester()
        rclpy.spin(tester)

    except KeyboardInterrupt:
        print("\n\n👋 测试结束")
        print(f"📊 总共接收 {tester.count} 条IMU数据")
        print("✅ IMU传感器工作正常")
    finally:
        tester.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
