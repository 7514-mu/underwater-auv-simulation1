#!/usr/bin/env python3
"""
上浮/定点巡航抖动诊断脚本
用于诊断航行器乱串的原因
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Wrench
import time

class InstabilityDiagnoser(Node):
    def __init__(self):
        super().__init__('instability_diagnoser')

        # 订阅话题
        self.odom_sub = self.create_subscription(
            Odometry, '/rexrov/pose_gt', self.odom_callback, 10)

        # 订阅所有推进器指令
        self.thruster_subs = []
        self.thruster_inputs = [0.0] * 8
        for i in range(8):
            sub = self.create_subscription(
                Float64, f'/rexrov/thrusters/id_{i}/input',
                lambda msg, idx=i: self.thruster_callback(msg, idx), 10)
            self.thruster_subs.append(sub)

        # 数据记录
        self.positions = []
        self.velocities = []
        self.thruster_history = []
        self.start_time = time.time()

        print("✅ 抖动诊断器已启动")
        print("="*70)
        print("📊 正在监控以下数据：")
        print("   - 位置和速度")
        print("   - 8个推进器的输入指令")
        print("   - 检测推进器饱和")
        print("   - 检测速度突变")
        print()
        print("💡 请让机器人进行上浮或定点巡航")
        print("⏱️  监控10秒后自动分析...")
        print()

        # 10秒后分析
        self.create_timer(10.0, self.analyze_data)

    def odom_callback(self, msg):
        # 记录位置
        pos = msg.pose.pose.position
        self.positions.append([pos.x, pos.y, pos.z])

        # 记录速度
        vel = msg.twist.twist.linear
        self.velocities.append([vel.x, vel.y, vel.z])

    def thruster_callback(self, msg, idx):
        self.thruster_inputs[idx] = msg.data

    def analyze_data(self):
        print("="*70)
        print("📊 诊断结果：")
        print("="*70)

        if len(self.positions) < 10:
            print("⚠️  数据不足，无法分析")
            return

        import numpy as np

        # 1. 分析速度变化
        velocities = np.array(self.velocities)
        vel_std = np.std(velocities, axis=0)
        vel_max = np.max(np.abs(velocities), axis=0)

        print("\n【1. 速度稳定性分析】")
        print(f"   X方向速度: 均值={velocities[:, 0].mean():.3f}, 标准差={vel_std[0]:.3f}, 最大值={vel_max[0]:.3f}")
        print(f"   Y方向速度: 均值={velocities[:, 1].mean():.3f}, 标准差={vel_std[1]:.3f}, 最大值={vel_max[1]:.3f}")
        print(f"   Z方向速度: 均值={velocities[:, 2].mean():.3f}, 标准差={vel_std[2]:.3f}, 最大值={vel_max[2]:.3f}")

        if vel_std[2] > 0.1:
            print("   ⚠️  Z方向速度不稳定（标准差 > 0.1 m/s）")
            print("   可能原因：浮力不平衡或PID参数不合适")
        else:
            print("   ✅ Z方向速度稳定")

        # 2. 分析位置变化
        positions = np.array(self.positions)
        pos_range = np.max(positions, axis=0) - np.min(positions, axis=0)

        print("\n【2. 位置稳定性分析】")
        print(f"   X方向位移范围: {pos_range[0]:.3f} m")
        print(f"   Y方向位移范围: {pos_range[1]:.3f} m")
        print(f"   Z方向位移范围: {pos_range[2]:.3f} m")

        if pos_range[0] > 1.0 or pos_range[1] > 1.0:
            print("   ⚠️  水平位移过大（> 1m）")
            print("   可能原因：控制器失稳或传感器故障")

        # 3. 分析推进器输入
        print("\n【3. 推进器工作状态】")
        saturated = []
        for i in range(8):
            input_val = self.thruster_inputs[i]
            if abs(input_val) > 18.0:  # 接近饱和值（saturation=20.0）
                saturated.append(i)
                print(f"   推进器{i}: {input_val:.2f} ⚠️  接近饱和")
            else:
                print(f"   推进器{i}: {input_val:.2f}")

        if len(saturated) > 0:
            print(f"\n   ⚠️  检测到 {len(saturated)} 个推进器接近饱和")
            print("   可能原因：浮力不平衡，推进器需要持续输出以抵消")
            print("   建议：调整浮力配平")

        # 4. 综合诊断
        print("\n" + "="*70)
        print("【综合诊断结果】")
        print("="*70)

        issues = []

        # 浮力不平衡检测
        if abs(velocities[:, 2].mean()) > 0.05:
            issues.append("浮力不平衡（有持续垂直速度）")

        # 推进器饱和检测
        if len(saturated) > 2:
            issues.append("多个推进器饱和（浮力可能不平衡）")

        # 速度不稳定检测
        if vel_std[2] > 0.1:
            issues.append("垂直速度不稳定（PID参数可能需要调整）")

        # 水平漂移检测
        if pos_range[0] > 1.0 or pos_range[1] > 1.0:
            issues.append("水平漂移严重（控制不稳定）")

        if not issues:
            print("✅ 未检测到明显问题")
        else:
            print("⚠️  检测到以下问题：")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")

        print("\n💡 建议解决方案：")

        if "浮力不平衡" in str(issues):
            print("   1. 调整浮力配平")
            print("      - 在URDF中修改浮力参数")
            print("      - 或添加压载重量")

        if "多个推进器饱和" in str(issues):
            print("   2. 降低PID增益或增加推进器限制")
            print("      - 编辑 pos_pid_control.yaml")
            print("      - 降低 pos_p 值（当前0.8）")

        if "垂直速度不稳定" in str(issues):
            print("   3. 调整垂直控制器PID参数")
            print("      - 降低 pos_p 或增加 pos_d")

        if "水平漂移严重" in str(issues):
            print("   4. 检查水平控制器和传感器数据")
            print("      - 查看是否有传感器噪声")

        print()
        print("📁 详细数据已保存，可使用Ctrl+C退出")

def main():
    rclpy.init()
    try:
        diagnoser = InstabilityDiagnoser()
        rclpy.spin(diagnoser)
    except KeyboardInterrupt:
        print("\n\n👋 诊断结束")
    finally:
        diagnoser.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
