#!/usr/bin/env python3
"""
实时对比真值和INS估计
简单文本输出
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import numpy as np

class GTINSComparator(Node):
    def __init__(self):
        super().__init__('gt_ins_comparator')

        print("="*70)
        print("📊 真值 vs INS估计 - 实时对比")
        print("="*70)
        print()

        # 数据
        self.gt_data = None
        self.ins_data = None

        # 订阅真值
        self.gt_sub = self.create_subscription(
            Odometry, '/rexrov/pose_gt', self.gt_callback, 10)

        # 订阅INS估计
        self.ins_sub = self.create_subscription(
            Odometry, '/rexrov/ins/estimate', self.ins_callback, 10)

        # 定时器：每秒打印一次
        self.create_timer(1.0, self.print_comparison)

    def gt_callback(self, msg):
        self.gt_data = msg

    def ins_callback(self, msg):
        self.ins_data = msg

    def print_comparison(self):
        if self.gt_data is None or self.ins_data is None:
            print("⏳ 等待数据...")
            return

        # 提取数据
        gt_pos = self.gt_data.pose.pose.position
        ins_pos = self.ins_data.pose.pose.position

        gt_vel = self.gt_data.twist.twist.linear
        ins_vel = self.ins_data.twist.twist.linear

        # 计算误差
        pos_error = np.sqrt(
            (gt_pos.x - ins_pos.x)**2 +
            (gt_pos.y - ins_pos.y)**2 +
            (gt_pos.z - ins_pos.z)**2
        )

        vel_error = np.sqrt(
            (gt_vel.x - ins_vel.x)**2 +
            (gt_vel.y - ins_vel.y)**2 +
            (gt_vel.z - ins_vel.z)**2
        )

        # 打印对比
        print("="*70)
        print("📊 真值 vs INS估计")
        print("="*70)

        print("\n【位置对比】")
        print(f"  真值:    X={gt_pos.x:8.3f}, Y={gt_pos.y:8.3f}, Z={gt_pos.z:8.3f}")
        print(f"  INS估计: X={ins_pos.x:8.3f}, Y={ins_pos.y:8.3f}, Z={ins_pos.z:8.3f}")
        print(f"  误差:    {pos_error:8.3f} m")

        print("\n【速度对比】")
        print(f"  真值:    X={gt_vel.x:8.3f}, Y={gt_vel.y:8.3f}, Z={gt_vel.z:8.3f}")
        print(f"  INS估计: X={ins_vel.x:8.3f}, Y={ins_vel.y:8.3f}, Z={ins_vel.z:8.3f}")
        print(f"  误差:    {vel_error:8.3f} m/s")

        # 精度评估
        print("\n【精度评估】")
        if pos_error < 0.1:
            print("  ✅ 位置精度: 优秀")
        elif pos_error < 0.5:
            print("  ⚠️  位置精度: 良好")
        elif pos_error < 1.0:
            print("  ⚠️  位置精度: 一般")
        else:
            print("  ❌ 位置精度: 较差")

        if vel_error < 0.05:
            print("  ✅ 速度精度: 优秀")
        elif vel_error < 0.1:
            print("  ⚠️  速度精度: 良好")
        elif vel_error < 0.2:
            print("  ⚠️  速度精度: 一般")
        else:
            print("  ❌ 速度精度: 较差")

        print("="*70)

def main():
    rclpy.init()

    try:
        comparator = GTINSComparator()
        print("💡 正在接收数据，每秒更新一次...")
        print("💡 按Ctrl+C退出\n")

        rclpy.spin(comparator)

    except KeyboardInterrupt:
        print("\n\n👋 对比器已停止")
    finally:
        comparator.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
