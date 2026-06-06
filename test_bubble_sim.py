#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import ApplyLinkWrench
from geometry_msgs.msg import Point, Vector3
import numpy as np

class BubbleDynamics(Node):
    def __init__(self):
        super().__init__('bubble_dynamics')

        self.declare_parameter('link_name', 'rexrov/base_link')
        self.declare_parameter('rate', 10.0)
        self.declare_parameter('bubble_density', 0.3)

        self.link_name = self.get_parameter('link_name').value
        self.rate = self.get_parameter('rate').value
        self.bubble_density = self.get_parameter('bubble_density').value
        self.dt = 1.0 / self.rate
        self.perturbation_timer = 0.0
        self.call_count = 0

        self.wrench_client = self.create_client(ApplyLinkWrench, '/apply_link_wrench')
        if not self.wrench_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('ApplyLinkWrench 服务未就绪')
            raise RuntimeError('服务不可用')

        self.timer = self.create_timer(self.dt, self.update)
        self.get_logger().info(f'气泡动力学节点启动，bubble_density={self.bubble_density}')

    def apply_force_with_callback(self, force):
        req = ApplyLinkWrench.Request()
        req.link_name = self.link_name
        req.reference_frame = 'world'
        req.reference_point = Point(x=0.0, y=0.0, z=0.0)
        req.wrench.force = Vector3(x=float(force[0]), y=float(force[1]), z=float(force[2]))
        req.wrench.torque = Vector3(x=0.0, y=0.0, z=0.0)
        req.start_time.sec = 0
        req.start_time.nanosec = 0
        req.duration.sec = -1
        req.duration.nanosec = 0

        future = self.wrench_client.call_async(req)
        future.add_done_callback(lambda f: self.wrench_callback(f, force))

    def wrench_callback(self, future, force):
        try:
            result = future.result()
            self.call_count += 1
            if result and result.success:
                self.get_logger().debug(f'#{self.call_count} 施力成功: [{force[0]:.1f}, {force[1]:.1f}, {force[2]:.1f}]')
            else:
                status = result.status_message if result else '无响应'
                self.get_logger().error(f'#{self.call_count} 施力失败: {status}')
        except Exception as e:
            self.get_logger().error(f'#{self.call_count} 施力异常: {str(e)}')

    def compute_perturbation(self):
        perturbation_period = 0.5
        self.perturbation_timer += self.dt
        if self.perturbation_timer < perturbation_period:
            return np.zeros(3)
        self.perturbation_timer = 0.0

        intensity = 500.0
        fx = np.random.uniform(-1.0, 1.0) * intensity * 0.9
        fy = np.random.uniform(-1.0, 1.0) * intensity * 0.9
        fz = np.random.uniform(0.3, 1.0) * intensity * 0.3
        return np.array([fx, fy, fz])

    def update(self):
        total_force = np.zeros(3)
        buoyancy_change = 220.33
        total_force[2] += buoyancy_change
        perturbation = self.compute_perturbation()
        total_force += perturbation

        self.get_logger().info(f'请求施力: [{total_force[0]:.2f}, {total_force[1]:.2f}, {total_force[2]:.2f}]')
        self.apply_force_with_callback(total_force)

def main():
    rclpy.init()
    try:
        node = BubbleDynamics()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()