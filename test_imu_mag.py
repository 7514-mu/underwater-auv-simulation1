#!/usr/bin/env python3
"""
IMU和磁力计传感器测试脚本
专门测试这两个传感器的数据质量
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Vector3Stamped
import numpy as np
from collections import deque

class IMUMagTester(Node):
    def __init__(self):
        super().__init__('imu_mag_tester')

        # 数据缓冲区（保存最近100条数据）
        self.imu_buffer = deque(maxlen=100)
        self.mag_buffer = deque(maxlen=100)

        print("="*70)
        print("🧪 IMU和磁力计传感器测试")
        print("="*70)
        print("\n📡 正在订阅传感器数据...")

        # 订阅IMU
        self.imu_sub = self.create_subscription(
            Imu, '/rexrov/imu', self.imu_callback, 10)

        # 订阅磁力计
        self.mag_sub = self.create_subscription(
            Vector3Stamped, '/rexrov/magnetometer', self.mag_callback, 10)

        # 测试时间
        self.test_duration = 5.0  # 测试5秒
        self.start_time = None

    def imu_callback(self, msg):
        if self.start_time is None:
            self.start_time = rclpy.clock.Clock().now()

        # 保存数据
        self.imu_buffer.append({
            'time': rclpy.clock.Clock().now(),
            'angular_velocity': [
                msg.angular_velocity.x,
                msg.angular_velocity.y,
                msg.angular_velocity.z
            ],
            'linear_acceleration': [
                msg.linear_acceleration.x,
                msg.linear_acceleration.y,
                msg.linear_acceleration.z
            ]
        })

    def mag_callback(self, msg):
        if self.start_time is None:
            self.start_time = rclpy.clock.Clock().now()

        # 保存数据
        self.mag_buffer.append({
            'time': rclpy.clock.Clock().now(),
            'magnetic_field': [
                msg.vector.x,
                msg.vector.y,
                msg.vector.z
            ]
        })

    def analyze_imu(self):
        print("\n" + "="*70)
        print("📊 IMU 传感器分析")
        print("="*70)

        if len(self.imu_buffer) == 0:
            print("❌ 未接收到IMU数据")
            return

        # 提取数据
        angular_data = np.array([d['angular_velocity'] for d in self.imu_buffer])
        accel_data = np.array([d['linear_acceleration'] for d in self.imu_buffer])

        print(f"\n✅ 接收到 {len(self.imu_buffer)} 条IMU数据")
        print(f"✅ 数据频率约 {len(self.imu_buffer) / self.test_duration:.1f} Hz")

        # 角速度分析
        print("\n【角速度分析】")
        print("  X轴 (横滚):")
        print(f"    均值 = {np.mean(angular_data[:, 0]):.6f} rad/s")
        print(f"    标准差 = {np.std(angular_data[:, 0]):.6f} rad/s")
        print(f"    范围 = [{np.min(angular_data[:, 0]):.6f}, {np.max(angular_data[:, 0]):.6f}]")

        print("  Y轴 (俯仰):")
        print(f"    均值 = {np.mean(angular_data[:, 1]):.6f} rad/s")
        print(f"    标准差 = {np.std(angular_data[:, 1]):.6f} rad/s")
        print(f"    范围 = [{np.min(angular_data[:, 1]):.6f}, {np.max(angular_data[:, 1]):.6f}]")

        print("  Z轴 (偏航):")
        print(f"    均值 = {np.mean(angular_data[:, 2]):.6f} rad/s")
        print(f"    标准差 = {np.std(angular_data[:, 2]):.6f} rad/s")
        print(f"    范围 = [{np.min(angular_data[:, 2]):.6f}, {np.max(angular_data[:, 2]):.6f}]")

        # 加速度分析
        print("\n【线加速度分析】")
        print("  X轴 (前向):")
        print(f"    均值 = {np.mean(accel_data[:, 0]):.6f} m/s²")
        print(f"    标准差 = {np.std(accel_data[:, 0]):.6f} m/s²")
        print(f"    范围 = [{np.min(accel_data[:, 0]):.6f}, {np.max(accel_data[:, 0]):.6f}]")

        print("  Y轴 (侧向):")
        print(f"    均值 = {np.mean(accel_data[:, 1]):.6f} m/s²")
        print(f"    标准差 = {np.std(accel_data[:, 1]):.6f} m/s²")
        print(f"    范围 = [{np.min(accel_data[:, 1]):.6f}, {np.max(accel_data[:, 1]):.6f}]")

        print("  Z轴 (垂向):")
        print(f"    均值 = {np.mean(accel_data[:, 2]):.6f} m/s²")
        print(f"    标准差 = {np.std(accel_data[:, 2]):.6f} m/s²")
        print(f"    范围 = [{np.min(accel_data[:, 2]):.6f}, {np.max(accel_data[:, 2]):.6f}]")

        # 数据质量评估
        print("\n【数据质量评估】")
        accel_std = np.std(accel_data, axis=0)
        angular_std = np.std(angular_data, axis=0)

        if np.mean(accel_std) < 0.1:
            print("  ✅ 加速度噪声：低（< 0.1 m/s²）")
        elif np.mean(accel_std) < 0.5:
            print("  ⚠️  加速度噪声：中等（0.1-0.5 m/s²）")
        else:
            print("  ❌ 加速度噪声：高（> 0.5 m/s²）")

        if np.mean(angular_std) < 0.01:
            print("  ✅ 角速度噪声：低（< 0.01 rad/s）")
        elif np.mean(angular_std) < 0.05:
            print("  ⚠️  角速度噪声：中等（0.01-0.05 rad/s）")
        else:
            print("  ❌ 角速度噪声：高（> 0.05 rad/s）")

    def analyze_mag(self):
        print("\n" + "="*70)
        print("📊 磁力计传感器分析")
        print("="*70)

        if len(self.mag_buffer) == 0:
            print("❌ 未接收到磁力计数据")
            return

        # 提取数据
        mag_data = np.array([d['magnetic_field'] for d in self.mag_buffer])

        print(f"\n✅ 接收到 {len(self.mag_buffer)} 条磁力计数据")
        print(f"✅ 数据频率约 {len(self.mag_buffer) / self.test_duration:.1f} Hz")

        # 磁场分析
        print("\n【磁场强度分析】")
        print("  X轴:")
        print(f"    均值 = {np.mean(mag_data[:, 0]):.3f} μT")
        print(f"    标准差 = {np.std(mag_data[:, 0]):.6f} μT")
        print(f"    范围 = [{np.min(mag_data[:, 0]):.3f}, {np.max(mag_data[:, 0]):.3f}] μT")

        print("  Y轴:")
        print(f"    均值 = {np.mean(mag_data[:, 1]):.3f} μT")
        print(f"    标准差 = {np.std(mag_data[:, 1]):.6f} μT")
        print(f"    范围 = [{np.min(mag_data[:, 1]):.3f}, {np.max(mag_data[:, 1]):.3f}] μT")

        print("  Z轴:")
        print(f"    均值 = {np.mean(mag_data[:, 2]):.3f} μT")
        print(f"    标准差 = {np.std(mag_data[:, 2]):.6f} μT")
        print(f"    范围 = [{np.min(mag_data[:, 2]):.3f}, {np.max(mag_data[:, 2]):.3f}] μT")

        # 计算总磁场强度
        mag_magnitude = np.linalg.norm(mag_data, axis=1)
        print(f"\n  总磁场强度:")
        print(f"    均值 = {np.mean(mag_magnitude):.3f} μT")
        print(f"    标准差 = {np.std(mag_magnitude):.6f} μT")

        # 数据质量评估
        print("\n【数据质量评估】")
        mag_std = np.std(mag_data, axis=0)

        if np.mean(mag_std) < 0.5:
            print("  ✅ 磁场噪声：低（< 0.5 μT）")
        elif np.mean(mag_std) < 2.0:
            print("  ⚠️  磁场噪声：中等（0.5-2.0 μT）")
        else:
            print("  ❌ 磁场噪声：高（> 2.0 μT）")

        # 地磁场强度检查（约 25-65 μT）
        if 20 < np.mean(mag_magnitude) < 70:
            print(f"  ✅ 磁场强度合理（{np.mean(mag_magnitude):.1f} μT，在地磁场范围内）")
        else:
            print(f"  ⚠️  磁场强度异常（{np.mean(mag_magnitude):.1f} μT，可能受干扰）")

def main():
    rclpy.init()

    try:
        tester = IMUMagTester()

        print(f"\n⏱️  测试时长: {tester.test_duration} 秒")
        print("💡 请保持机器人静止或缓慢移动")
        print()

        # 旋转指定时间
        start_time = rclpy.clock.Clock().now()
        while rclpy.ok():
            rclpy.spin_once(tester, timeout_sec=0.1)

            # 计算已用时间
            # 注意：这里简化处理，实际应该用时间差

            # 使用数据缓冲区大小判断是否完成测试
            if len(tester.imu_buffer) >= int(tester.test_duration * 50):  # 假设50Hz
                break

        # 分析数据
        tester.analyze_imu()
        tester.analyze_mag()

        print("\n" + "="*70)
        print("✅ 测试完成")
        print("="*70)

    except KeyboardInterrupt:
        print("\n\n👋 测试中断")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
