#!/usr/bin/env python3
"""
水下环境仿真模块 - 统一管理湍流、涡流、温度、气泡效果

原理：所有环境效果都通过 ApplyLinkWrench 施加时变外力来实现
- 湍流：Ornstein-Uhlenbeck 有色噪声过程
- 涡流：旋转力场模型
- 温度：密度公式 → 浮力补偿力
- 气泡：随机脉冲力

使用方法：
  python3 underwater_environment_sim.py --turbulence 500 --vortex 300 --temperature 25 --bubble 50
"""

import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import ApplyLinkWrench
from geometry_msgs.msg import Point, Wrench, Vector3
import numpy as np
import argparse
import time


class OrnsteinUhlenbeckProcess:
    """
    Ornstein-Uhlenbeck 过程 - 生成时间相关的有色噪声

    用于模拟真实湍流的时间相关性：
    - 大尺度涡流 → 大 tau（长相关时间）
    - 小尺度涡流 → 小 tau（短相关时间）

    公式：dx = -theta * x * dt + sigma * dW
    其中 theta = 1/tau（相关时间的倒数）
    """

    def __init__(self, dim=3, tau=1.0, sigma=1.0, dt=0.1):
        self.dim = dim
        self.tau = tau
        self.sigma = sigma
        self.dt = dt
        self.state = np.zeros(dim)
        self.theta = 1.0 / tau if tau > 0 else 0.0

    def sample(self):
        noise = np.random.randn(self.dim)
        self.state += -self.theta * self.state * self.dt + self.sigma * np.sqrt(self.dt) * noise
        return self.state.copy()


class VortexModel:
    """
    涡流模型 - 模拟水下漩涡

    使用旋转力场：
    - 切向力：F_t = k * r * exp(-r² / R²)
    - 径向力：F_r = -k_r * r（向心）

    参数：
    - strength: 涡流强度 (N)
    - radius: 涡流半径 (m)
    - center: 涡流中心位置 (x, y, z)
    """

    def __init__(self, strength=100.0, radius=5.0, center=(0.0, 0.0, -20.0)):
        self.strength = strength
        self.radius = radius
        self.center = np.array(center)

    def get_force(self, position):
        r_vec = position - self.center
        r = np.linalg.norm(r_vec)

        if r < 0.01:
            return np.zeros(3)

        r_hat = r_vec / r

        z_axis = np.array([0.0, 0.0, 1.0])
        tangent = np.cross(z_axis, r_hat)
        tangent_norm = np.linalg.norm(tangent)
        if tangent_norm > 1e-6:
            tangent = tangent / tangent_norm

        radial_decay = np.exp(-r**2 / self.radius**2)
        tangential_force = self.strength * r * radial_decay * tangent

        radial_force = -0.3 * self.strength * r * radial_decay * r_hat

        return tangential_force + radial_force


class TemperatureModel:
    """
    温度模型 - 温度影响水密度，进而影响浮力

    公式：
    - 密度：ρ(T) = 1000 - 0.2 × (T - 4)²  (纯水)
    - 浮力：F_b = ρ(T) × g × V
    - 补偿力：ΔF = (ρ(T) - ρ_ref) × g × V

    分层水温：
    - 表层 (0-10m): 温暖
    - 温跃层 (10-100m): 快速降温
    - 深层 (>100m): 寒冷
    """

    def __init__(self, surface_temp=25.0, deep_temp=5.0, thermocline_depth=10.0,
                 thermocline_width=90.0, robot_volume=0.5):
        self.surface_temp = surface_temp
        self.deep_temp = deep_temp
        self.thermocline_depth = thermocline_depth
        self.thermocline_width = thermocline_width
        self.robot_volume = robot_volume
        self.g = 9.81
        self.ref_density = 998.2  # 20°C 参考密度

    def get_temperature(self, depth):
        if depth < self.thermocline_depth:
            return self.surface_temp
        elif depth > self.thermocline_depth + self.thermocline_width:
            return self.deep_temp
        else:
            frac = (depth - self.thermocline_depth) / self.thermocline_width
            return self.surface_temp + (self.deep_temp - self.surface_temp) * frac

    def temperature_to_density(self, temp_c):
        if temp_c < 0:
            return 917.0
        rho = 1000.0 - 0.2 * (temp_c - 4.0)**2
        return max(950.0, min(rho, 1000.0))

    def get_buoyancy_correction(self, depth):
        temp = self.get_temperature(depth)
        rho = self.temperature_to_density(temp)
        delta_rho = rho - self.ref_density
        return delta_rho * self.g * self.robot_volume


class BubbleModel:
    """
    气泡模型 - 模拟气泡对机器人的随机扰动

    气泡效应：
    - 随机方向的小力脉冲
    - 主要向上（气泡浮力方向）
    - 强度与气泡量相关
    """

    def __init__(self, intensity=50.0, rate=0.3):
        self.intensity = intensity
        self.rate = rate
        self.time_since_last = 0.0

    def get_force(self, dt):
        self.time_since_last += dt
        if self.time_since_last < 1.0 / self.rate:
            return np.zeros(3)

        self.time_since_last = 0.0

        fx = np.random.uniform(-1.0, 1.0) * self.intensity * 0.3
        fy = np.random.uniform(-1.0, 1.0) * self.intensity * 0.3
        fz = np.random.uniform(0.5, 1.0) * self.intensity

        return np.array([fx, fy, fz])


class UnderwaterEnvironmentSim(Node):
    """
    水下环境仿真节点

    统一管理所有环境效果，通过 ApplyLinkWrench 施加到机器人
    """

    def __init__(self, link_name='rexrov/base_link', rate=10.0,
                 turbulence_intensity=0.0, vortex_strength=0.0,
                 temperature=25.0, bubble_intensity=0.0):
        super().__init__('underwater_environment_sim')

        self.link_name = link_name
        self.rate = rate
        self.dt = 1.0 / rate

        self.wrench_client = self.create_client(ApplyLinkWrench, '/apply_link_wrench')
        if not self.wrench_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('ApplyLinkWrench 服务未就绪')
            raise RuntimeError('服务不可用')

        self.turbulence = OrnsteinUhlenbeckProcess(
            dim=3, tau=2.0, sigma=turbulence_intensity, dt=self.dt
        ) if turbulence_intensity > 0 else None

        self.vortex = VortexModel(
            strength=vortex_strength, radius=5.0, center=(0.0, 0.0, -20.0)
        ) if vortex_strength > 0 else None

        self.temp_model = TemperatureModel(
            surface_temp=temperature, deep_temp=5.0,
            robot_volume=0.5
        )

        self.bubble = BubbleModel(
            intensity=bubble_intensity, rate=0.3
        ) if bubble_intensity > 0 else None

        self.robot_position = np.array([0.0, 0.0, -20.0])

        self.get_logger().info('=' * 60)
        self.get_logger().info('水下环境仿真模块已启动')
        self.get_logger().info(f'  目标: {link_name}')
        self.get_logger().info(f'  频率: {rate} Hz')
        self.get_logger().info(f'  湍流强度: {turbulence_intensity} N')
        self.get_logger().info(f'  涡流强度: {vortex_strength} N')
        self.get_logger().info(f'  表层水温: {temperature} °C')
        self.get_logger().info(f'  气泡强度: {bubble_intensity} N')
        self.get_logger().info('=' * 60)

        self.timer = self.create_timer(self.dt, self.update)

    def update(self):
        total_force = np.zeros(3)

        if self.turbulence is not None:
            turb_force = self.turbulence.sample()
            total_force += turb_force

        if self.vortex is not None:
            vortex_force = self.vortex.get_force(self.robot_position)
            total_force += vortex_force

        depth = -self.robot_position[2]
        buoyancy_correction = self.temp_model.get_buoyancy_correction(depth)
        total_force[2] += buoyancy_correction

        if self.bubble is not None:
            bubble_force = self.bubble.get_force(self.dt)
            total_force += bubble_force

        self.apply_force(total_force)

    def apply_force(self, force):
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

        self.wrench_client.call_async(req)


def main():
    parser = argparse.ArgumentParser(description='水下环境仿真模块')
    parser.add_argument('--link', type=str, default='rexrov/base_link',
                        help='目标 link 名称')
    parser.add_argument('--rate', type=float, default=10.0,
                        help='更新频率 (Hz)')
    parser.add_argument('--turbulence', type=float, default=0.0,
                        help='湍流强度 (N)，推荐 100-1000')
    parser.add_argument('--vortex', type=float, default=0.0,
                        help='涡流强度 (N)，推荐 100-500')
    parser.add_argument('--temperature', type=float, default=25.0,
                        help='表层水温 (°C)')
    parser.add_argument('--bubble', type=float, default=0.0,
                        help='气泡扰动强度 (N)，推荐 10-100')

    args = parser.parse_args()

    rclpy.init()

    try:
        sim = UnderwaterEnvironmentSim(
            link_name=args.link,
            rate=args.rate,
            turbulence_intensity=args.turbulence,
            vortex_strength=args.vortex,
            temperature=args.temperature,
            bubble_intensity=args.bubble,
        )
        rclpy.spin(sim)
    except KeyboardInterrupt:
        print('\n仿真已停止')
    except Exception as e:
        print(f'错误: {e}')
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
