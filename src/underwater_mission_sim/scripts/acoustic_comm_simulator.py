#!/usr/bin/env python3
"""
水声通信仿真节点

模拟两个水下航行器之间的声学通信。

【理论依据】
  1. 传播延迟: t = distance / sound_speed (~1500 m/s)
  2. 传输损失: TL = 20*log10(r) + alpha*r (球面扩展 + Thorp吸收)
  3. 信噪比: SNR = SL - TL - NL + DI
  4. 气泡影响: 气泡密度增加 → 环境噪声增加 → SNR降低 → 丢包率上升

使用方法:
  ros2 topic pub /auv_1/comm_tx std_msgs/msg/String "{data: 'Hello'}"
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, String
from nav_msgs.msg import Odometry
import numpy as np
import json
import time
import random


class AcousticCommSimulator(Node):

    def __init__(self):
        super().__init__('acoustic_comm_simulator')

        # 声学参数
        self.declare_parameter('vehicle_1_namespace', 'auv_1')
        self.declare_parameter('vehicle_2_namespace', 'auv_2')
        self.declare_parameter('sound_speed', 1500.0)
        self.declare_parameter('source_level', 180.0)
        self.declare_parameter('noise_level', 70.0)
        self.declare_parameter('directivity_index', 10.0)
        self.declare_parameter('frequency', 25000.0)
        self.declare_parameter('packet_loss_threshold', 0.3)
        self.declare_parameter('bubble_noise_factor', 50.0)

        self.ns1 = self.get_parameter('vehicle_1_namespace').value
        self.ns2 = self.get_parameter('vehicle_2_namespace').value
        self.sound_speed = self.get_parameter('sound_speed').value
        self.source_level = self.get_parameter('source_level').value
        self.noise_level_base = self.get_parameter('noise_level').value
        self.directivity_index = self.get_parameter('directivity_index').value
        self.frequency = self.get_parameter('frequency').value
        self.packet_loss_threshold = self.get_parameter('packet_loss_threshold').value
        self.bubble_noise_factor = self.get_parameter('bubble_noise_factor').value

        # 状态
        self.pos1 = np.zeros(3)
        self.pos2 = np.zeros(3)
        self.pos1_valid = False
        self.pos2_valid = False
        self.bubble_density = 0.0
        self.pending_messages = []  # (deliver_time, target_ns, msg_json)
        self.msg_counter = 0

        # 订阅
        self.create_subscription(
            Odometry, f'/{self.ns1}/pose_gt', self._pose1_cb, 10)
        self.create_subscription(
            Odometry, f'/{self.ns2}/pose_gt', self._pose2_cb, 10)
        self.create_subscription(
            String, f'/{self.ns1}/comm_tx', lambda msg: self._tx_cb(msg, self.ns1), 10)
        self.create_subscription(
            String, f'/{self.ns2}/comm_tx', lambda msg: self._tx_cb(msg, self.ns2), 10)
        self.create_subscription(
            Float64, '/bubble_sim/density', self._density_cb, 10)

        # 发布
        self.rx1_pub = self.create_publisher(String, f'/{self.ns1}/comm_rx', 10)
        self.rx2_pub = self.create_publisher(String, f'/{self.ns2}/comm_rx', 10)
        self.status_pub = self.create_publisher(String, '/acoustic_comm/status', 10)

        # 定时器: 10Hz 检查待发送消息
        self.timer = self.create_timer(0.1, self._timer_cb)

        self.get_logger().info('=' * 60)
        self.get_logger().info('水声通信仿真节点已启动')
        self.get_logger().info(f'  航行器1: {self.ns1}')
        self.get_logger().info(f'  航行器2: {self.ns2}')
        self.get_logger().info(f'  声速: {self.sound_speed} m/s')
        self.get_logger().info(f'  频率: {self.frequency} Hz')
        self.get_logger().info('=' * 60)

    def _pose1_cb(self, msg):
        self.pos1 = np.array([
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            msg.pose.pose.position.z])
        self.pos1_valid = True

    def _pose2_cb(self, msg):
        self.pos2 = np.array([
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            msg.pose.pose.position.z])
        self.pos2_valid = True

    def _density_cb(self, msg):
        self.bubble_density = max(0.0, min(1.0, msg.data))

    def _tx_cb(self, msg, sender_ns):
        """收到发送请求，计算传播延迟和丢包"""
        if not self.pos1_valid or not self.pos2_valid:
            self.get_logger().warn('航行器位置未就绪，丢弃消息')
            return

        target_ns = self.ns2 if sender_ns == self.ns1 else self.ns1
        sender_pos = self.pos1 if sender_ns == self.ns1 else self.pos2
        target_pos = self.pos2 if sender_ns == self.ns1 else self.pos1

        distance = np.linalg.norm(sender_pos - target_pos)
        if distance < 0.01:
            distance = 0.01

        # 传播延迟
        delay = distance / self.sound_speed

        # 传输损失 (球面扩展 + Thorp吸收)
        tl = self._compute_transmission_loss(distance)

        # 信噪比 (含气泡噪声)
        bubble_noise = self.bubble_density * self.bubble_noise_factor
        snr = self.source_level - tl - (self.noise_level_base + bubble_noise) + self.directivity_index

        # 丢包判断
        lost = self._is_packet_lost(snr)

        # 构造消息
        self.msg_counter += 1
        now = self.get_clock().now().nanoseconds / 1e9
        msg_data = {
            'id': self.msg_counter,
            'sender': sender_ns,
            'data': msg.data,
            'distance': round(distance, 2),
            'delay_ms': round(delay * 1000, 1),
            'snr_db': round(snr, 1),
            'lost': lost,
            'tx_time': now,
        }

        if lost:
            self.get_logger().info(
                f'[丢包] {sender_ns}→{target_ns}: SNR={snr:.1f}dB, '
                f'距离={distance:.1f}m, 气泡噪声={bubble_noise:.1f}dB')
            self._publish_status(msg_data)
            return

        # 加入待发送队列 (模拟传播延迟)
        deliver_time = now + delay
        self.pending_messages.append((deliver_time, target_ns, msg_data))
        self.get_logger().info(
            f'[发送] {sender_ns}→{target_ns}: "{msg.data[:30]}", '
            f'距离={distance:.1f}m, 延迟={delay*1000:.1f}ms, SNR={snr:.1f}dB')

    def _compute_transmission_loss(self, distance):
        """传输损失 = 球面扩展 + Thorp吸收"""
        spreading = 20.0 * np.log10(max(distance, 0.1))
        # Thorp吸收公式 (dB/km)
        f_khz = self.frequency / 1000.0
        f2 = f_khz ** 2
        alpha_db_per_km = (0.11 * f2 / (1.0 + f2) +
                           44.0 * f2 / (4100.0 + f2) +
                           2.75e-4 * f2 + 0.003)
        absorption = alpha_db_per_km * distance / 1000.0
        return spreading + absorption

    def _is_packet_lost(self, snr):
        if snr < -5.0:
            return True
        if snr < self.packet_loss_threshold:
            loss_prob = 1.0 - snr / self.packet_loss_threshold
            return random.random() < min(1.0, max(0.0, loss_prob))
        return False

    def _timer_cb(self):
        """检查待发送消息队列"""
        now = self.get_clock().now().nanoseconds / 1e9
        delivered = []
        for i, (deliver_time, target_ns, msg_data) in enumerate(self.pending_messages):
            if now >= deliver_time:
                self._deliver_message(target_ns, msg_data)
                delivered.append(i)
        for i in reversed(delivered):
            self.pending_messages.pop(i)

    def _deliver_message(self, target_ns, msg_data):
        """投递消息到目标航行器"""
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
            f'[送达] →{target_ns}: "{msg_data["data"][:30]}", '
            f'实际延迟={(msg_data["rx_time"]-msg_data["tx_time"])*1000:.1f}ms')

    def _publish_status(self, msg_data):
        status = String()
        status.data = json.dumps(msg_data, ensure_ascii=False)
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
