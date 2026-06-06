#!/usr/bin/env python3
"""
发送机器人到目标位置（使用GoTo服务）
用法: python3 go_to_target.py x y z
例如: python3 go_to_target.py 5 0 -20
"""

import rclpy
from rclpy.node import Node
from uuv_control_msgs.srv import GoTo
import sys

class GoToTarget(Node):
    def __init__(self, x, y, z):
        super().__init__('go_to_target')

        # 目标位置
        self.target_x = float(x)
        self.target_y = float(y)
        self.target_z = float(z)

        # 创建GoTo服务客户端
        self.go_to_client = self.create_client(GoTo, '/rexrov/go_to')

        print(f"✅ 节点已启动")
        print(f"📍 目标位置: x={self.target_x}, y={self.target_y}, z={self.target_z}")
        print(f"🎯 等待GoTo服务...")

        # 等待服务可用
        if not self.go_to_client.wait_for_service(timeout_sec=5.0):
            print("❌ GoTo服务不可用")
            return

        # 发送目标
        self.send_goal()

    def send_goal(self):
        """发送目标位置"""
        from uuv_control_msgs.msg import Waypoint
        from geometry_msgs.msg import Point
        from std_msgs.msg import Header
        from builtin_interfaces.msg import Time

        # 创建航路点
        waypoint = Waypoint()
        
        # 设置header
        waypoint.header.stamp = self.get_clock().now().to_msg()
        waypoint.header.frame_id = 'world'
        
        # 设置位置
        waypoint.point.x = self.target_x
        waypoint.point.y = self.target_y
        waypoint.point.z = self.target_z
        
        # 设置参数
        waypoint.max_forward_speed = 0.5
        waypoint.heading_offset = 0.0
        waypoint.use_fixed_heading = False
        waypoint.radius_of_acceptance = 0.5

        # 创建请求
        request = GoTo.Request()
        request.waypoint = waypoint
        request.max_forward_speed = 0.5
        request.interpolator = 'lipb'

        # 调用服务
        future = self.go_to_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result() is not None:
            response = future.result()
            if response.success:
                print(f"✅ 目标设置成功！机器人正在移动到 ({self.target_x}, {self.target_y}, {self.target_z})")
            else:
                print("❌ 目标设置失败")
        else:
            print("❌ 服务调用超时")

def main():
    if len(sys.argv) != 4:
        print("❌ 用法错误!")
        print("用法: python3 go_to_target.py x y z")
        print("例如: python3 go_to_target.py 5 0 -20")
        sys.exit(1)

    x = sys.argv[1]
    y = sys.argv[2]
    z = sys.argv[3]

    rclpy.init()

    try:
        go_to_target = GoToTarget(x, y, z)
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
