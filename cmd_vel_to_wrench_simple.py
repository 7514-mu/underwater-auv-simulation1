#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Wrench
from rclpy.qos import QoSProfile

class SimpleCmdVelToWrench(Node):
    def __init__(self):
        super().__init__('simple_cmd_vel_to_wrench')
        self.subscription = self.create_subscription(
            Twist,
            '/rexrov/cmd_vel',
            self.cmd_vel_callback,
            QoSProfile(depth=10)
        )
        self.publisher = self.create_publisher(
            Wrench,
            '/rexrov/thruster_manager/input',
            QoSProfile(depth=10)
        )
        self.buoyancy_compensation = -15.0
        self.get_logger().info('Simple cmd_vel to Wrench converter started')

    def cmd_vel_callback(self, msg):
        wrench = Wrench()
        wrench.force.x = msg.linear.x * 100.0
        wrench.force.y = msg.linear.y * 100.0
        wrench.force.z = msg.linear.z * 500.0

        # 自动浮力补偿
        if abs(msg.linear.z) < 0.01:
            wrench.force.z += self.buoyancy_compensation

        wrench.torque.x = msg.angular.x * 50.0
        wrench.torque.y = msg.angular.y * 50.0
        wrench.torque.z = msg.angular.z * 50.0

        self.publisher.publish(wrench)

def main(args=None):
    rclpy.init(args=args)
    node = SimpleCmdVelToWrench()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
