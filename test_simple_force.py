#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import ApplyLinkWrench
from geometry_msgs.msg import Point, Vector3

def main():
    rclpy.init()
    node = Node('test_force_simple')

    client = node.create_client(ApplyLinkWrench, '/apply_link_wrench')
    if not client.wait_for_service(timeout_sec=5.0):
        node.get_logger().error('Service not available')
        return

    req = ApplyLinkWrench.Request()
    req.link_name = 'rexrov/base_link'
    req.reference_frame = 'world'
    req.reference_point = Point(x=0.0, y=0.0, z=0.0)
    req.wrench.force = Vector3(x=500.0, y=0.0, z=0.0)
    req.wrench.torque = Vector3(x=0.0, y=0.0, z=0.0)
    req.start_time.sec = 0
    req.start_time.nanosec = 0
    req.duration.sec = 5
    req.duration.nanosec = 0

    node.get_logger().info('Calling /apply_link_wrench with 500N in X for 5 seconds...')
    result = client.call(req)
    node.get_logger().info(f'Result: success={result.success}, status={result.status_message}')

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()