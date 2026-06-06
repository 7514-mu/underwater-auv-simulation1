#!/usr/bin/env python3
"""
简单测试湍流效果
"""
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import ApplyLinkWrench
import time
import random
import math

class TurbulenceTester(Node):
    def __init__(self):
        super().__init__('turbulence_tester')
        self.wrench_client = self.create_client(ApplyLinkWrench, '/apply_link_wrench')

        if not self.wrench_client.wait_for_service(timeout_sec=5.0):
            print("❌ ApplyLinkWrench服务未就绪")
            return

        print("✅ 服务已就绪，开始测试湍流效果")
        print("   将施加随机力到机器人本体")

        magnitude = 1500.0  # high intensity

        for i in range(50):  # 持续5秒
            # 随机扰动力（高斯分布）
            fx = random.gauss(0, magnitude)
            fy = random.gauss(0, magnitude)
            fz = random.gauss(0, magnitude * 0.3)

            # 施加力
            req = ApplyLinkWrench.Request()
            req.link_name = 'rexrov/base_link'
            req.reference_frame = 'world'
            req.reference_point.x = 0.0
            req.reference_point.y = 0.0
            req.reference_point.z = 0.0

            req.wrench.force.x = float(fx)
            req.wrench.force.y = float(fy)
            req.wrench.force.z = float(fz)
            req.wrench.torque.x = 0.0
            req.wrench.torque.y = 0.0
            req.wrench.torque.z = 0.0

            req.start_time.sec = 0
            req.start_time.nanosec = 0
            req.duration.sec = -1  # 持续施加
            req.duration.nanosec = 0

            future = self.wrench_client.call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=0.5)

            if i % 10 == 0:
                print(f"   施力 {i}: F=[{fx:.1f}, {fy:.1f}, {fz:.1f}] N")

            time.sleep(0.1)

        print("✅ 测试完成")

def main():
    rclpy.init()
    try:
        tester = TurbulenceTester()
    except KeyboardInterrupt:
        print("\n测试中断")
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
