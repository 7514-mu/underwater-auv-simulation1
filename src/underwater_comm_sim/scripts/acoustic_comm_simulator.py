#!/usr/bin/env python3
"""
水声通信仿真节点 (arlpy 增强版)

基于 arlpy 水声库的声学通信仿真，支持：
  - 声速随温度/盐度/深度变化 (Mackenzie 1981)
  - 海水吸收 (Francois-Garrison 模型)
  - 气泡对声速的影响 (Wood 1964)
  - 多径效应 (海面/海底反射, Rayleigh 反射系数)
  - 多普勒效应
  - 误码估计

安装 arlpy:
  pip install arlpy

使用方法:
  ros2 topic pub /auv_1/comm_tx std_msgs/msg/String "{data: 'Hello'}"
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, String
from nav_msgs.msg import Odometry
import numpy as np
import json
import random

try:
    import arlpy.uwa
    HAS_ARLPY = True
except ImportError:
    HAS_ARLPY = False


class AcousticCommSimulator(Node):

    def __init__(self):
        super().__init__('acoustic_comm_simulator')

        # --- 通信参数 ---
        self.declare_parameter('vehicle_1_namespace', 'auv_1')
        self.declare_parameter('vehicle_2_namespace', 'auv_2')
        self.declare_parameter('frequency', 25000.0)
        self.declare_parameter('source_level', 180.0)
        self.declare_parameter('noise_level', 70.0)
        self.declare_parameter('directivity_index', 10.0)
        self.declare_parameter('packet_loss_threshold', 0.3)
        self.declare_parameter('bubble_noise_factor', 50.0)

        # --- 环境参数 (arlpy) ---
        self.declare_parameter('temperature', 10.0)           # 水温 °C
        self.declare_parameter('salinity', 35.0)              # 盐度 ppt
        self.declare_parameter('water_depth', 50.0)           # 海底深度 m
        self.declare_parameter('ph', 8.1)
        self.declare_parameter('wind_speed', 3.0)             # 风速 m/s
        self.declare_parameter('bottom_density', 1800.0)      # 海底密度 kg/m³
        self.declare_parameter('bottom_soundspeed', 1600.0)   # 海底声速 m/s
        self.declare_parameter('bottom_attenuation', 0.5)     # 海底衰减 dB/λ
        self.declare_parameter('enable_multipath', True)
        self.declare_parameter('enable_doppler', True)

        # 读取参数
        self.ns1 = self.get_parameter('vehicle_1_namespace').value
        self.ns2 = self.get_parameter('vehicle_2_namespace').value
        self.frequency = self.get_parameter('frequency').value
        self.source_level = self.get_parameter('source_level').value
        self.noise_level_base = self.get_parameter('noise_level').value
        self.directivity_index = self.get_parameter('directivity_index').value
        self.packet_loss_threshold = self.get_parameter('packet_loss_threshold').value
        self.bubble_noise_factor = self.get_parameter('bubble_noise_factor').value

        self.temperature = self.get_parameter('temperature').value
        self.salinity = self.get_parameter('salinity').value
        self.water_depth = self.get_parameter('water_depth').value
        self.ph = self.get_parameter('ph').value
        self.wind_speed = self.get_parameter('wind_speed').value
        self.bottom_density = self.get_parameter('bottom_density').value
        self.bottom_soundspeed = self.get_parameter('bottom_soundspeed').value
        self.bottom_attenuation = self.get_parameter('bottom_attenuation').value
        self.enable_multipath = self.get_parameter('enable_multipath').value
        self.enable_doppler = self.get_parameter('enable_doppler').value

        # 状态
        self.pos1 = np.zeros(3)
        self.pos2 = np.zeros(3)
        self.vel1 = np.zeros(3)
        self.vel2 = np.zeros(3)
        self.pos1_valid = False
        self.pos2_valid = False
        self.bubble_density = 0.0
        self.pending_messages = []
        self.msg_counter = 0

        # 订阅
        self.create_subscription(
            Odometry, f'/{self.ns1}/pose_gt', self._pose1_cb, 10)
        self.create_subscription(
            Odometry, f'/{self.ns2}/pose_gt', self._pose2_cb, 10)
        self.create_subscription(
            String, f'/{self.ns1}/comm_tx',
            lambda msg: self._tx_cb(msg, self.ns1), 10)
        self.create_subscription(
            String, f'/{self.ns2}/comm_tx',
            lambda msg: self._tx_cb(msg, self.ns2), 10)
        self.create_subscription(
            Float64, '/bubble_sim/density', self._density_cb, 10)

        # 发布
        self.rx1_pub = self.create_publisher(
            String, f'/{self.ns1}/comm_rx', 10)
        self.rx2_pub = self.create_publisher(
            String, f'/{self.ns2}/comm_rx', 10)
        self.status_pub = self.create_publisher(
            String, '/acoustic_comm/status', 10)
        self.channel_pub = self.create_publisher(
            String, '/acoustic_comm/channel', 10)

        # 定时器: 10Hz
        self.timer = self.create_timer(0.1, self._timer_cb)

        self.get_logger().info('=' * 60)
        self.get_logger().info('水声通信仿真节点已启动 (arlpy 增强版)')
        arlpy_status = '已加载' if HAS_ARLPY else '未安装 (pip install arlpy)'
        self.get_logger().info(f'  arlpy: {arlpy_status}')
        self.get_logger().info(f'  航行器: {self.ns1} <-> {self.ns2}')
        self.get_logger().info(f'  频率: {self.frequency} Hz')
        self.get_logger().info(
            f'  温度: {self.temperature}C, 盐度: {self.salinity}ppt, '
            f'水深: {self.water_depth}m')
        self.get_logger().info(
            f'  多径: {"开" if self.enable_multipath else "关"}, '
            f'多普勒: {"开" if self.enable_doppler else "关"}')
        self.get_logger().info('=' * 60)

    # ---- 回调 ----

    def _pose1_cb(self, msg):
        self.pos1 = np.array([
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            msg.pose.pose.position.z])
        self.vel1 = np.array([
            msg.twist.twist.linear.x,
            msg.twist.twist.linear.y,
            msg.twist.twist.linear.z])
        self.pos1_valid = True

    def _pose2_cb(self, msg):
        self.pos2 = np.array([
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            msg.pose.pose.position.z])
        self.vel2 = np.array([
            msg.twist.twist.linear.x,
            msg.twist.twist.linear.y,
            msg.twist.twist.linear.z])
        self.pos2_valid = True

    def _density_cb(self, msg):
        self.bubble_density = max(0.0, min(1.0, msg.data))

    def _tx_cb(self, msg, sender_ns):
        if not self.pos1_valid or not self.pos2_valid:
            self.get_logger().warn('航行器位置未就绪，丢弃消息')
            return

        target_ns = self.ns2 if sender_ns == self.ns1 else self.ns1
        sender_pos = self.pos1 if sender_ns == self.ns1 else self.pos2
        target_pos = self.pos2 if sender_ns == self.ns1 else self.pos1
        sender_vel = self.vel1 if sender_ns == self.ns1 else self.vel2
        target_vel = self.vel2 if sender_ns == self.ns1 else self.vel1

        # 深度 (z 为负值，取绝对值)
        sender_depth = abs(sender_pos[2])
        target_depth = abs(target_pos[2])
        avg_depth = (sender_depth + target_depth) / 2.0

        # 1. 声速 (温度/盐度/深度)
        sound_speed = self._compute_sound_speed(avg_depth)

        # 2. 直达路径
        direct_distance = np.linalg.norm(target_pos - sender_pos)
        if direct_distance < 0.01:
            direct_distance = 0.01
        delay = direct_distance / sound_speed

        # 3. 传输损失 (球面扩展 + Francois-Garrison 吸收)
        tl = self._compute_transmission_loss(direct_distance, avg_depth)

        # 4. 气泡效应
        bubble_noise = self._compute_bubble_noise(sound_speed)

        # 5. 多径
        multipath_paths = self._compute_multipath(
            sender_pos, target_pos, sound_speed)
        multipath_fading = self._compute_multipath_fading(multipath_paths)

        # 6. 多普勒
        direction = (target_pos - sender_pos) / direct_distance
        doppler_hz = self._compute_doppler(
            sender_vel, target_vel, direction, sound_speed)

        # 7. 综合 SNR
        snr = (self.source_level - tl - multipath_fading
               - (self.noise_level_base + bubble_noise)
               + self.directivity_index)

        # 8. 丢包
        lost = self._is_packet_lost(snr)

        # 构造消息
        self.msg_counter += 1
        now = self.get_clock().now().nanoseconds / 1e9
        msg_data = {
            'id': self.msg_counter,
            'sender': sender_ns,
            'data': msg.data,
            'distance': round(direct_distance, 2),
            'delay_ms': round(delay * 1000, 1),
            'sound_speed': round(sound_speed, 1),
            'snr_db': round(snr, 1),
            'tl_db': round(tl, 1),
            'bubble_noise_db': round(bubble_noise, 1),
            'multipath_fading_db': round(multipath_fading, 1),
            'doppler_hz': round(doppler_hz, 1),
            'lost': lost,
            'tx_time': now,
            'channel': {
                'temperature': self.temperature,
                'salinity': self.salinity,
                'sender_depth': round(sender_depth, 1),
                'target_depth': round(target_depth, 1),
                'paths': [
                    {'name': p['name'],
                     'distance': round(p['distance'], 2),
                     'delay_ms': round(p['delay'] * 1000, 1),
                     'amplitude_db': round(p['amplitude_db'], 1)}
                    for p in multipath_paths
                ],
            },
        }

        # 发布信道信息
        ch = String()
        ch.data = json.dumps(msg_data.get('channel', {}), ensure_ascii=False)
        self.channel_pub.publish(ch)

        if lost:
            self._publish_status(msg_data)
            self.get_logger().info(
                f'[丢包] {sender_ns}->{target_ns}: SNR={snr:.1f}dB, '
                f'距离={direct_distance:.1f}m, TL={tl:.1f}dB, '
                f'气泡={bubble_noise:.1f}dB, 多径={multipath_fading:.1f}dB, '
                f'多普勒={doppler_hz:.1f}Hz')
            return

        deliver_time = now + delay
        self.pending_messages.append((deliver_time, target_ns, msg_data))
        self.get_logger().info(
            f'[发送] {sender_ns}->{target_ns}: "{msg.data[:30]}", '
            f'距离={direct_distance:.1f}m, 延迟={delay*1000:.1f}ms, '
            f'SNR={snr:.1f}dB, 声速={sound_speed:.1f}m/s, '
            f'多普勒={doppler_hz:.1f}Hz')

    # ---- 水声计算 (arlpy) ----

    def _compute_sound_speed(self, depth):
        """声速: Mackenzie (1981)"""
        if HAS_ARLPY:
            return arlpy.uwa.soundspeed(
                self.temperature, self.salinity, depth)
        T, S, D = self.temperature, self.salinity, depth
        return (1448.96 + 4.591*T - 5.304e-2*T**2 + 2.374e-4*T**3
                + 1.340*(S-35) + 1.630e-2*D + 1.675e-7*D**2
                - 1.025e-2*T*(S-35) - 7.139e-13*T*D**3)

    def _compute_transmission_loss(self, distance, depth):
        """TL = 球面扩展 + Francois-Garrison 吸收"""
        spreading = 20.0 * np.log10(max(distance, 0.1))

        if HAS_ARLPY:
            absorption_linear = arlpy.uwa.absorption(
                self.frequency, distance,
                self.temperature, self.salinity, depth, self.ph)
            absorption_db = -20.0 * np.log10(max(absorption_linear, 1e-30))
        else:
            f_khz = self.frequency / 1000.0
            f2 = f_khz ** 2
            alpha_db_per_km = (0.11 * f2 / (1.0 + f2)
                               + 44.0 * f2 / (4100.0 + f2)
                               + 2.75e-4 * f2 + 0.003)
            absorption_db = alpha_db_per_km * distance / 1000.0

        return spreading + absorption_db

    def _compute_bubble_noise(self, base_sound_speed):
        """气泡效应: 噪声增加 + 声速变化"""
        if self.bubble_density < 1e-6:
            return 0.0

        # bubble_density (0-1) 映射到空化率 void_fraction
        void_fraction = self.bubble_density * 1e-4

        if HAS_ARLPY:
            # Wood (1964) 气泡声速模型
            c_bubbly = arlpy.uwa.bubble_soundspeed(
                void_fraction, c=base_sound_speed)
            # 声速变化导致的阻抗失配 → 额外噪声
            c_ratio = c_bubbly / base_sound_speed
        else:
            rho_w, rho_a, c_a = 1025.0, 1.225, 340.0
            rho_mix = void_fraction * rho_a + (1 - void_fraction) * rho_w
            kappa_mix = (void_fraction / (rho_a * c_a**2)
                         + (1 - void_fraction) / (rho_w * base_sound_speed**2))
            c_bubbly = 1.0 / np.sqrt(rho_mix * kappa_mix)
            c_ratio = c_bubbly / base_sound_speed

        # 气泡噪声 = 密度因子 * 基础噪声系数 + 声速失配损失
        noise_increase = self.bubble_density * self.bubble_noise_factor
        if c_ratio < 1.0:
            noise_increase += -20.0 * np.log10(max(c_ratio, 0.01))

        return noise_increase

    def _compute_multipath(self, sender_pos, target_pos, sound_speed):
        """多径: 直达 + 海面反射 + 海底反射"""
        d_tx = abs(sender_pos[2])
        d_rx = abs(target_pos[2])
        r = np.sqrt((target_pos[0] - sender_pos[0])**2
                     + (target_pos[1] - sender_pos[1])**2)
        bottom = self.water_depth

        paths = [{
            'name': 'direct',
            'distance': np.linalg.norm(target_pos - sender_pos),
            'delay': np.linalg.norm(target_pos - sender_pos) / sound_speed,
            'amplitude_db': 0.0,
        }]

        if not self.enable_multipath:
            return paths

        direct_dist = paths[0]['distance']

        # 海面反射 (镜像源法)
        surface_dist = np.sqrt(r**2 + (d_tx + d_rx)**2)
        surface_rc = self._surface_reflection_coeff(r, d_tx + d_rx)
        paths.append({
            'name': 'surface',
            'distance': surface_dist,
            'delay': surface_dist / sound_speed,
            'amplitude_db': 20.0 * np.log10(max(abs(surface_rc), 1e-10)),
        })

        # 海底反射
        dz_bottom = 2 * bottom - d_tx - d_rx
        if dz_bottom > 0:
            bottom_dist = np.sqrt(r**2 + dz_bottom**2)
            bottom_angle = np.arctan2(r, dz_bottom)
            bottom_rc = self._bottom_reflection_coeff(bottom_angle)
            paths.append({
                'name': 'bottom',
                'distance': bottom_dist,
                'delay': bottom_dist / sound_speed,
                'amplitude_db': 20.0 * np.log10(max(abs(bottom_rc), 1e-10)),
            })

        return paths

    def _surface_reflection_coeff(self, range_h, depth_sum):
        """海面反射系数"""
        angle = np.arctan2(range_h, max(depth_sum, 0.01))
        if HAS_ARLPY and self.bubble_density > 0.01:
            loss = arlpy.uwa.bubble_surface_loss(
                self.wind_speed, self.frequency, angle)
            return abs(loss)
        return 0.95

    def _bottom_reflection_coeff(self, angle):
        """海底反射系数: Rayleigh"""
        if HAS_ARLPY:
            rho_w = arlpy.uwa.density(self.temperature, self.salinity)
            c_w = self._compute_sound_speed(self.water_depth)
            return abs(arlpy.uwa.reflection_coeff(
                angle, self.bottom_density, self.bottom_soundspeed,
                self.bottom_attenuation, rho_w, c_w))

        # 简化 Rayleigh
        rho_w, c_w = 1025.0, 1500.0
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        cos_b_sq = 1 - (self.bottom_soundspeed / c_w * sin_a)**2
        cos_b = np.sqrt(max(cos_b_sq, 0.0)) if cos_b_sq > 0 else 0.01
        Z_w = rho_w * c_w / max(cos_a, 0.01)
        Z_b = self.bottom_density * self.bottom_soundspeed / max(cos_b, 0.01)
        return abs((Z_b - Z_w) / (Z_b + Z_w))

    def _compute_multipath_fading(self, paths):
        """多径 ISI 导致的等效 SNR 损失 (dB)"""
        if len(paths) <= 1:
            return 0.0

        direct_dist = paths[0]['distance']
        isi_power = 0.0
        for p in paths[1:]:
            reflection = 10 ** (p['amplitude_db'] / 20.0)
            spreading_ratio = direct_dist / p['distance']
            isi_power += (reflection * spreading_ratio) ** 2

        if isi_power > 0:
            return 10.0 * np.log10(1.0 + isi_power)
        return 0.0

    def _compute_doppler(self, sender_vel, target_vel, direction, sound_speed):
        """多普勒频移 (Hz)"""
        if not self.enable_doppler:
            return 0.0

        rel_vel = np.dot(sender_vel - target_vel, direction)

        if HAS_ARLPY:
            f_shifted = arlpy.uwa.doppler(
                rel_vel, self.frequency, sound_speed)
            return f_shifted - self.frequency

        return 2.0 * rel_vel / sound_speed * self.frequency

    # ---- 丢包与投递 ----

    def _is_packet_lost(self, snr):
        if snr < -5.0:
            return True
        if snr < self.packet_loss_threshold:
            loss_prob = 1.0 - snr / self.packet_loss_threshold
            return random.random() < min(1.0, max(0.0, loss_prob))
        return False

    def _timer_cb(self):
        now = self.get_clock().now().nanoseconds / 1e9
        delivered = []
        for i, (deliver_time, target_ns, msg_data) in enumerate(
                self.pending_messages):
            if now >= deliver_time:
                self._deliver_message(target_ns, msg_data)
                delivered.append(i)
        for i in reversed(delivered):
            self.pending_messages.pop(i)

    def _deliver_message(self, target_ns, msg_data):
        msg_data['rx_time'] = self.get_clock().now().nanoseconds / 1e9
        json_str = json.dumps(msg_data, ensure_ascii=False)
        out_msg = String()
        out_msg.data = json_str

        if target_ns == self.ns1:
            self.rx1_pub.publish(out_msg)
        else:
            self.rx2_pub.publish(out_msg)

        self._publish_status(msg_data)
        self.get_logger().info(
            f'[送达] ->{target_ns}: "{msg_data["data"][:30]}", '
            f'实际延迟={((msg_data["rx_time"]-msg_data["tx_time"])*1000):.1f}ms, '
            f'声速={msg_data.get("sound_speed", 0):.1f}m/s')

    def _publish_status(self, msg_data):
        status = String()
        brief = {k: v for k, v in msg_data.items() if k != 'channel'}
        status.data = json.dumps(brief, ensure_ascii=False)
        self.status_pub.publish(status)


def main():
    rclpy.init()
    node = AcousticCommSimulator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
