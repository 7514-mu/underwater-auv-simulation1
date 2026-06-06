#!/usr/bin/env python3
"""
气泡动力学仿真节点

模拟水下环境气泡群对 ROV 的力学影响。

【理论依据】
  1. 阻力增加: Morison方程 F=0.5ρCdA_eff v² (Clift et al. 1978)
  2. 浮力变化: Archimedes原理 ΔF=ρgV_bubble
  3. 漂移力: Stokes粘性阻力 (Landau & Lifshitz 1987)
  4. 随机扰动: 气泡碰撞/破裂力脉冲简化模型

【体积分数】α = bubble_density × α_factor
  - α_factor = 0.15 (典型尾流气泡群体积分数上限)
  - 所有力的计算统一使用 α

使用方法:
  ros2 run underwater_bubble_sim bubble_dynamics.py --ros-args -p bubble_density:=0.5
"""

import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import ApplyLinkWrench
from geometry_msgs.msg import Point, Wrench, Vector3
from std_msgs.msg import Float64, String
import numpy as np
import math


class BubbleDynamics(Node):

    def __init__(self):
        super().__init__('bubble_dynamics')

        self.declare_parameter('link_name', 'rexrov/base_link')
        self.declare_parameter('rate', 10.0)
        self.declare_parameter('bubble_density', 0.3)
        self.declare_parameter('robot_volume', 0.5)
        self.declare_parameter('robot_cross_section', 0.3)
        self.declare_parameter('water_density', 998.2)

        self.link_name = self.get_parameter('link_name').value
        self.rate = self.get_parameter('rate').value
        self.bubble_density = self.get_parameter('bubble_density').value
        self.robot_volume = self.get_parameter('robot_volume').value
        self.robot_cross_section = self.get_parameter('robot_cross_section').value
        self.water_density = self.get_parameter('water_density').value

        self.dt = 1.0 / self.rate
        self.g = 9.81

        self.wrench_client = self.create_client(ApplyLinkWrench, '/apply_link_wrench')
        self.get_logger().info('等待 /apply_link_wrench 服务...')
        if not self.wrench_client.wait_for_service(timeout_sec=60.0):
            self.get_logger().error('ApplyLinkWrench 服务未就绪')
            raise RuntimeError('服务不可用')
        self.get_logger().info('/apply_link_wrench 服务已就绪')

        self.density_sub = self.create_subscription(
            Float64, '/bubble_sim/density', self.density_callback, 10)
        self.cmd_sub = self.create_subscription(
            String, '/bubble_sim/cmd', self.cmd_callback, 10)

        self.robot_velocity = np.zeros(3)
        self.perturbation_timer = 0.0
        self.perturbation_interval = 1.0 / max(self.bubble_density * 5.0, 0.5)

        self.get_logger().info('=' * 60)
        self.get_logger().info('气泡动力学仿真节点已启动')
        self.get_logger().info(f'  目标: {self.link_name}')
        self.get_logger().info(f'  频率: {self.rate} Hz')
        self.get_logger().info(f'  气泡密度: {self.bubble_density}')
        self.get_logger().info('=' * 60)

        self.timer = self.create_timer(self.dt, self.update)

    def density_callback(self, msg):
        self.bubble_density = max(0.0, min(1.0, msg.data))
        self.perturbation_interval = 1.0 / max(self.bubble_density * 5.0, 0.5)
        self.get_logger().debug(f'气泡密度更新: {self.bubble_density}')

    def cmd_callback(self, msg):
        cmd = msg.data.lower()
        if cmd == 'burst':
            self.bubble_density = 1.0
            self.get_logger().info('爆发模式：气泡密度设为最大')
        elif cmd == 'clear':
            self.bubble_density = 0.0
            self.get_logger().info('清除模式：气泡密度设为0')

    def compute_drag_force(self):
        """
        气泡附着 → 迎流面积增大 → 阻力增加

        【理论依据】Clift et al. (1978) 多相流阻力公式

        阻力公式：F_drag = 0.5 × ρ × Cd × A × v²

        气泡影响（Clift经验公式）：
        - 有效截面积 A_eff = A_base × (1 + K_AREA × void_fraction)
        - K_AREA ≈ 2.0~3.5（Clift经验范围，取中值2.5）
        - void_fraction = bubble_density × VOID_FRACTION_MAX
        """
        VOID_FRACTION_MAX = 0.15  # 气泡体积分数上限（实验观测值）
        K_AREA = 2.5  # Clift et al. 经验系数范围 2.0~3.5

        if self.bubble_density < 0.01:
            return np.zeros(3)

        v = np.linalg.norm(self.robot_velocity)
        if v < 0.01:
            return np.zeros(3)

        Cd = 1.0  # 方头ROV的阻力系数
        void_fraction = self.bubble_density * VOID_FRACTION_MAX
        A_base = self.robot_cross_section
        A_eff = A_base * (1.0 + K_AREA * void_fraction)

        drag_magnitude = 0.5 * self.water_density * Cd * A_eff * v**2

        v_dir = -self.robot_velocity / v
        return drag_magnitude * v_dir

    def compute_buoyancy_change(self):
        """
        气泡附着 → 等效密度降低 → 浮力变化

        【理论依据】阿基米德原理 + 气泡体积分数

        原理：
        - 气泡体积 V_bubble = V_robot × void_fraction
        - void_fraction = bubble_density × VOID_FRACTION_MAX（实验观测上限约0.15）
        - 气泡密度 ρ_air ≈ 1.2 kg/m³，远小于水，可忽略
        - 等效密度 ρ_eff = (ρ_water × V_robot + ρ_air × V_bubble) / (V_robot + V_bubble)
        - 浮力变化：ΔF_buoyancy = ρ_water × g × V_bubble

        效果：气泡附着 → 浮力增大（向上力）
        """
        VOID_FRACTION_MAX = 0.15  # 气泡体积分数上限（实验观测值）

        if self.bubble_density < 0.01:
            return 0.0

        void_fraction = self.bubble_density * VOID_FRACTION_MAX
        V_bubble = self.robot_volume * void_fraction
        delta_buoyancy = self.water_density * self.g * V_bubble

        return delta_buoyancy

    def compute_drift_force(self):
        """
        气泡上升流 → 对机器人产生向上的拖曳力

        【理论依据】Stokes阻力公式 (Landau & Lifshitz, 1987)

        原理：
        - 气泡上升速度 v_bubble = (2/9) × r² × g × (ρ_water - ρ_air) / μ
        - 对于 r ≈ 1mm 的气泡，v_bubble ≈ 0.3~0.5 m/s
        - 气泡流带动周围水体向上运动，形成上升流场
        - 对机器人产生向上的粘性拖曳力：F_drift ∝ bubble_density × v_bubble × μ × A

        Stokes阻力公式：F = 6πμRv（单个球体）
        群体效应修正：F_drift = C_DRIFT × α × v_bubble × μ × A
        其中 α = bubble_density × VOID_FRACTION_MAX（体积分数）
        """
        VOID_FRACTION_MAX = 0.15  # 气泡体积分数上限
        C_DRIFT = 120.0  # 群体效应修正系数（实验拟合值）
        v_bubble = 0.35  # 典型气泡上升速度 (Clift et al. 实验值)
        mu = 1.002e-3  # 水的动力粘度 (20°C)

        if self.bubble_density < 0.01:
            return 0.0

        alpha = self.bubble_density * VOID_FRACTION_MAX
        drift_force = C_DRIFT * alpha * v_bubble * mu * self.robot_cross_section

        return drift_force

    def compute_perturbation(self):
        """
        气泡碰撞/破裂产生的随机力脉冲

        简化模型：将气泡群对ROV的随机碰撞近似为力脉冲
        - 方向随机，偏向上方（气泡浮力方向）
        - 强度 k × α，k = 40N（工程估算，基于气泡动量转移）
        - 频率与气泡密度成正比

        参考: Clift et al. (1978) 气泡-固体碰撞力学
        """
        self.perturbation_timer += self.dt
        if self.perturbation_timer < self.perturbation_interval:
            return np.zeros(3)

        self.perturbation_timer = 0.0

        k_perturbation = 40.0  # 扰动强度系数 (N)
        alpha = self.bubble_density * 0.15
        intensity = k_perturbation * alpha

        fx = np.random.uniform(-1.0, 1.0) * intensity * 0.3
        fy = np.random.uniform(-1.0, 1.0) * intensity * 0.3
        fz = np.random.uniform(0.3, 1.0) * intensity

        return np.array([fx, fy, fz])

    def update(self):
        total_force = np.zeros(3)

        drag = self.compute_drag_force()
        total_force += drag

        buoyancy_change = self.compute_buoyancy_change()
        total_force[2] += buoyancy_change

        drift = self.compute_drift_force()
        total_force[2] += drift

        perturbation = self.compute_perturbation()
        total_force += perturbation

        self.get_logger().debug(f'力计算: drag={np.linalg.norm(drag):.2f}, buoyancy={buoyancy_change:.2f}, drift={drift:.2f}, pert={np.linalg.norm(perturbation):.2f}, 总力={np.linalg.norm(total_force):.2f}')

        if np.any(np.abs(total_force) > 0.001):
            self.apply_force(total_force)

    def apply_force(self, force):
        req = ApplyLinkWrench.Request()
        req.link_name = self.link_name
        req.reference_frame = 'world'
        req.reference_point = Point(x=0.0, y=0.0, z=0.0)
        req.wrench.force = Vector3(
            x=float(force[0]), y=float(force[1]), z=float(force[2]))
        req.wrench.torque = Vector3(x=0.0, y=0.0, z=0.0)
        req.start_time.sec = 0
        req.start_time.nanosec = 0
        req.duration.sec = -1
        req.duration.nanosec = 0

        self.get_logger().debug(f'施加力到{self.link_name}: [{force[0]:.2f}, {force[1]:.2f}, {force[2]:.2f}]')
        self.wrench_client.call_async(req)

    def wrench_callback(self, future):
        try:
            result = future.result()
            if result and not result.success:
                self.get_logger().error(f'施力失败: {result.status_message}')
        except Exception as e:
            self.get_logger().error(f'施力异常: {str(e)}')


def main():
    rclpy.init()
    node = BubbleDynamics()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()