#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import ApplyLinkWrench, LinkRequest
from geometry_msgs.msg import Point, Vector3

class ForceTester(Node):
    def __init__(self):
        super().__init__('force_tester')
        self.apply_client = self.create_client(ApplyLinkWrench, '/apply_link_wrench')
        self.clear_client = self.create_client(LinkRequest, '/clear_link_wrenches')

        if not self.apply_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('Apply service not available')
            return
        if not self.clear_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('Clear service not available')
            return

        self.get_logger().info('Both services available')

        # Test 1: Apply a large constant force in X direction
        self.get_logger().info('=== Test 1: Apply 500N in X direction for 3 seconds ===')
        self.apply_constant_force(500.0, 0.0, 0.0, 3.0)

        # Test 2: Apply a large constant force in Z direction (up)
        self.get_logger().info('=== Test 2: Apply 500N in Z direction for 3 seconds ===')
        self.apply_constant_force(0.0, 0.0, 500.0, 3.0)

        # Test 3: Apply force in -Z direction (down)
        self.get_logger().info('=== Test 3: Apply 500N in -Z direction for 3 seconds ===')
        self.apply_constant_force(0.0, 0.0, -500.0, 3.0)

        self.get_logger().info('=== All tests completed ===')

    def apply_constant_force(self, fx, fy, fz, duration_sec):
        # Clear first
        clear_req = LinkRequest.Request()
        clear_req.link_name = 'rexrov/base_link'
        self.clear_client.call(clear_req)

        # Apply force
        req = ApplyLinkWrench.Request()
        req.link_name = 'rexrov/base_link'
        req.reference_frame = 'world'
        req.reference_point = Point(x=0.0, y=0.0, z=0.0)
        req.wrench.force = Vector3(x=float(fx), y=float(fy), z=float(fz))
        req.wrench.torque = Vector3(x=0.0, y=0.0, z=0.0)
        req.start_time.sec = 0
        req.start_time.nanosec = 0
        req.duration.sec = int(duration_sec)
        req.duration.nanosec = 0

        result = self.apply_client.call(req)
        self.get_logger().info(f'Applied force ({fx}, {fy}, {fz}) for {duration_sec}s: success={result.success}, status={result.status_message}')

def main():
    rclpy.init()
    node = ForceTester()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()