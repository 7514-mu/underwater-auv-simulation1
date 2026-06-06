#!/usr/bin/env python3
"""
浮力平衡测试脚本
用于检查机器人的浮力状态
"""

import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import GetEntityState
from geometry_msgs.msg import Point

class BuoyancyChecker(Node):
    def __init__(self):
        super().__init__('buoyancy_checker')

        # 创建服务客户端
        self.state_client = self.create_client(
            GetEntityState, '/gazebo/get_entity_state')

        if not self.state_client.wait_for_service(timeout_sec=5.0):
            print("❌ Gazebo服务未就绪")
            return

        print("✅ 浮力平衡检查器已启动")
        print("="*60)

        # 获取机器人状态
        req = GetEntityState.Request()
        req.name = 'rexrov::base_link'
        req.reference_frame = 'world'

        future = self.state_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result() is not None:
            response = future.result()
            state = response.state

            print("📊 机器人当前状态：")
            print(f"   位置: x={state.pose.position.x:.2f}, "
                  f"y={state.pose.position.y:.2f}, "
                  f"z={state.pose.position.z:.2f}")
            print(f"   线速度: x={state.twist.linear.x:.3f}, "
                  f"y={state.twist.linear.y:.3f}, "
                  f"z={state.twist.linear.z:.3f}")
            print(f"   角速度: x={state.twist.angular.x:.3f}, "
                  f"y={state.twist.angular.y:.3f}, "
                  f"z={state.twist.angular.z:.3f}")
            print()

            # 分析垂直速度
            vz = state.twist.linear.z
            if abs(vz) < 0.01:
                print("✅ 垂直速度接近0，浮力基本平衡")
            elif vz > 0.01:
                print(f"⚠️  正在上浮（vz={vz:.3f} m/s）")
                print("   可能原因：浮力 > 重力")
                print("   建议：增加压载重量或减小浮力")
            else:
                print(f"⚠️  正在下沉（vz={vz:.3f} m/s）")
                print("   可能原因：重力 > 浮力")
                print("   建议：减小压载重量或增加浮力")

            print()
            print("💡 定点巡航抖动可能原因：")
            print("   1. 浮力不平衡 → 推进器持续工作抵消浮力")
            print("   2. 接近水面时波浪效应")
            print("   3. PID参数不合适（垂直控制）")
            print("   4. 推进器饱和")
            print()

        else:
            print("❌ 获取机器人状态失败")

def main():
    rclpy.init()
    try:
        checker = BuoyancyChecker()
    except KeyboardInterrupt:
        print("\n检查中断")
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
