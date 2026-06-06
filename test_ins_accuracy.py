#!/usr/bin/env python3
"""
INS精度测试脚本
对比INS估计与真值的差异
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import numpy as np
from collections import deque
import time

class INSAccuracyTester(Node):
    def __init__(self):
        super().__init__('ins_accuracy_tester')

        print("="*70)
        print("🧪 INS精度测试")
        print("="*70)
        print("📊 正在对比INS估计与真值...")
        print()

        # 数据缓冲
        self.gt_buffer = deque(maxlen=1000)
        self.ins_buffer = deque(maxlen=1000)
        self.errors = deque(maxlen=1000)

        # 订阅真值
        self.gt_sub = self.create_subscription(
            Odometry, '/rexrov/pose_gt', self.gt_callback, 10)

        # 订阅INS估计
        self.ins_sub = self.create_subscription(
            Odometry, '/rexrov/ins/estimate', self.ins_callback, 10)

        # 测试时长
        self.test_duration = 30.0  # 测试30秒
        self.start_time = None

        # 创建定时器打印统计信息
        self.create_timer(5.0, self.print_statistics)

    def gt_callback(self, msg):
        """真值回调"""
        self.gt_buffer.append({
            'time': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'position': np.array([
                msg.pose.pose.position.x,
                msg.pose.pose.position.y,
                msg.pose.pose.position.z
            ]),
            'velocity': np.array([
                msg.twist.twist.linear.x,
                msg.twist.twist.linear.y,
                msg.twist.twist.linear.z
            ])
        })

        # 计算误差（如果INS数据也到了）
        if len(self.ins_buffer) > 0:
            self.calculate_error()

    def ins_callback(self, msg):
        """INS估计回调"""
        self.ins_buffer.append({
            'time': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'position': np.array([
                msg.pose.pose.position.x,
                msg.pose.pose.position.y,
                msg.pose.pose.position.z
            ]),
            'velocity': np.array([
                msg.twist.twist.linear.x,
                msg.twist.twist.linear.y,
                msg.twist.twist.linear.z
            ])
        })

        # 计算误差（如果真值数据也到了）
        if len(self.gt_buffer) > 0:
            self.calculate_error()

    def calculate_error(self):
        """计算误差"""
        if len(self.gt_buffer) == 0 or len(self.ins_buffer) == 0:
            return

        # 获取最新的数据
        gt = self.gt_buffer[-1]
        ins = self.ins_buffer[-1]

        # 位置误差
        pos_error = np.linalg.norm(gt['position'] - ins['position'])

        # 速度误差
        vel_error = np.linalg.norm(gt['velocity'] - ins['velocity'])

        # 保存误差
        self.errors.append({
            'time': gt['time'],
            'pos_error': pos_error,
            'vel_error': vel_error,
            'position_diff': gt['position'] - ins['position'],
            'velocity_diff': gt['velocity'] - ins['velocity']
        })

        # 首次收到数据
        if self.start_time is None:
            self.start_time = gt['time']
            print("✅ 开始接收数据...")
            print("💡 测试时长: 30秒")
            print("💡 每5秒更新统计信息\n")

    def print_statistics(self):
        """打印统计信息"""
        if len(self.errors) == 0:
            print("⏳ 等待数据...")
            return

        errors_array = np.array([
            [e['pos_error'], e['vel_error']] for e in self.errors
        ])

        # 计算统计量
        pos_errors = errors_array[:, 0]
        vel_errors = errors_array[:, 1]

        print("="*70)
        print("📊 INS精度统计（实时更新）")
        print("="*70)

        print(f"\n【位置误差】")
        print(f"  平均误差: {np.mean(pos_errors):.4f} m")
        print(f"  标准差:   {np.std(pos_errors):.4f} m")
        print(f"  最大误差: {np.max(pos_errors):.4f} m")
        print(f"  最小误差: {np.min(pos_errors):.4f} m")
        print(f"  当前误差: {pos_errors[-1]:.4f} m")

        print(f"\n【速度误差】")
        print(f"  平均误差: {np.mean(vel_errors):.4f} m/s")
        print(f"  标准差:   {np.std(vel_errors):.4f} m/s")
        print(f"  最大误差: {np.max(vel_errors):.4f} m/s")
        print(f"  最小误差: {np.min(vel_errors):.4f} m/s")
        print(f"  当前误差: {vel_errors[-1]:.4f} m/s")

        # 精度评估
        print(f"\n【精度评估】")
        mean_pos_error = np.mean(pos_errors)
        if mean_pos_error < 0.1:
            print("  ✅ 位置精度: 优秀 (< 0.1 m)")
        elif mean_pos_error < 0.5:
            print("  ⚠️  位置精度: 良好 (0.1-0.5 m)")
        elif mean_pos_error < 1.0:
            print("  ⚠️  位置精度: 一般 (0.5-1.0 m)")
        else:
            print("  ❌ 位置精度: 较差 (> 1.0 m)")

        mean_vel_error = np.mean(vel_errors)
        if mean_vel_error < 0.05:
            print("  ✅ 速度精度: 优秀 (< 0.05 m/s)")
        elif mean_vel_error < 0.1:
            print("  ⚠️  速度精度: 良好 (0.05-0.1 m/s)")
        elif mean_vel_error < 0.2:
            print("  ⚠️  速度精度: 一般 (0.1-0.2 m/s)")
        else:
            print("  ❌ 速度精度: 较差 (> 0.2 m/s)")

        print("="*70)

def main():
    rclpy.init()

    try:
        tester = INSAccuracyTester()

        print("⏱️  测试时长: 30秒")
        print("💡 建议让机器人移动以观察动态精度")
        print()

        # 运行30秒
        start_time = time.time()
        while time.time() - start_time < tester.test_duration:
            rclpy.spin_once(tester, timeout_sec=0.1)

        # 最终统计
        if len(tester.errors) > 0:
            print("\n" + "="*70)
            print("📊 最终测试报告")
            print("="*70)

            errors_array = np.array([
                [e['pos_error'], e['vel_error']] for e in tester.errors
            ])

            pos_errors = errors_array[:, 0]
            vel_errors = errors_array[:, 1]

            print(f"\n✅ 总共采集 {len(tester.errors)} 个数据点")
            print(f"\n【位置误差汇总】")
            print(f"   平均: {np.mean(pos_errors):.4f} m")
            print(f"   标准差: {np.std(pos_errors):.4f} m")
            print(f"   RMS: {np.sqrt(np.mean(pos_errors**2)):.4f} m")

            print(f"\n【速度误差汇总】")
            print(f"   平均: {np.mean(vel_errors):.4f} m/s")
            print(f"   标准差: {np.std(vel_errors):.4f} m/s")
            print(f"   RMS: {np.sqrt(np.mean(vel_errors**2)):.4f} m/s")

            print("\n" + "="*70)
            print("✅ 测试完成")
            print("="*70)

    except KeyboardInterrupt:
        print("\n\n👋 测试中断")
    finally:
        tester.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
