#!/usr/bin/env python3
"""
水下跟踪仿真节点

使用Alpha-Beta滤波器跟踪探测到的目标。

【理论依据】
  1. Alpha-Beta滤波器: 工程级跟踪算法
     - 预测: x_pred = x + v * dt
     - 残差: r = z - x_pred
     - 更新: x = x_pred + alpha * r, v = v + (beta/dt) * r
  2. 最近邻数据关联: 检测与最近航迹匹配
  3. 航迹管理: 试探 → 确认 → 滑行 → 丢失

使用方法:
  订阅 /detection/results (JSON)
  发布 /auv_1/tracked_target (PoseStamped)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped, Point
from nav_msgs.msg import Odometry
from visualization_msgs.msg import Marker, MarkerArray
import numpy as np
import json


class AlphaBetaFilter:
    """Alpha-Beta 滤波器 (3D)"""

    def __init__(self, alpha=0.3, beta=0.1, dt=0.1):
        self.alpha = alpha
        self.beta = beta
        self.dt = dt
        self.x = np.zeros(3)  # 位置估计
        self.v = np.zeros(3)  # 速度估计
        self.x_pred = np.zeros(3)
        self.initialized = False

    def predict(self):
        self.x_pred = self.x + self.v * self.dt
        return self.x_pred.copy()

    def update(self, measurement):
        if not self.initialized:
            self.x = measurement.copy()
            self.v = np.zeros(3)
            self.initialized = True
            self.x_pred = self.x.copy()
            return

        x_pred = self.x + self.v * self.dt
        residual = measurement - x_pred
        self.x = x_pred + self.alpha * residual
        self.v = self.v + (self.beta / self.dt) * residual
        self.x_pred = self.x.copy()


class Track:
    """航迹管理"""

    TENTATIVE = 'tentative'
    CONFIRMED = 'confirmed'
    COAST = 'coast'
    LOST = 'lost'

    def __init__(self, track_id, alpha, beta, dt, max_coast_time):
        self.track_id = track_id
        self.filter = AlphaBetaFilter(alpha, beta, dt)
        self.history = []
        self.status = self.TENTATIVE
        self.confirm_count = 0
        self.coast_count = 0
        self.max_coast_time = max_coast_time
        self.dt = dt
        self.last_update_time = 0.0

    def update_with_detection(self, detection, timestamp):
        self.filter.update(detection)
        self.history.append((timestamp, detection.copy()))
        if len(self.history) > 500:
            self.history = self.history[-500:]
        self.confirm_count += 1
        self.coast_count = 0
        self.last_update_time = timestamp
        if self.confirm_count >= 3:
            self.status = self.CONFIRMED

    def coast(self, timestamp):
        self.filter.predict()
        self.coast_count += 1
        if self.coast_count * self.dt > self.max_coast_time:
            self.status = self.LOST

    def get_position(self):
        return self.filter.x.copy()

    def get_velocity(self):
        return self.filter.v.copy()

    def get_predicted_position(self, steps=1):
        pred = self.filter.x + self.filter.v * self.dt * steps
        return pred


class UnderwaterTracker(Node):

    def __init__(self):
        super().__init__('underwater_tracker')

        self.declare_parameter('namespace', 'auv_1')
        self.declare_parameter('alpha_filter', 0.3)
        self.declare_parameter('beta_filter', 0.1)
        self.declare_parameter('track_update_rate', 10.0)
        self.declare_parameter('max_coast_time', 5.0)
        self.declare_parameter('prediction_steps', 5)
        self.declare_parameter('gate_distance', 5.0)

        self.ns = self.get_parameter('namespace').value
        self.alpha = self.get_parameter('alpha_filter').value
        self.beta = self.get_parameter('beta_filter').value
        self.rate = self.get_parameter('track_update_rate').value
        self.max_coast = self.get_parameter('max_coast_time').value
        self.pred_steps = self.get_parameter('prediction_steps').value
        self.gate_dist = self.get_parameter('gate_distance').value

        self.dt = 1.0 / self.rate
        self.tracks = []
        self.next_track_id = 1

        # 订阅探测结果
        self.create_subscription(
            String, '/detection/results', self._detection_cb, 10)

        # 发布
        self.target_pub = self.create_publisher(
            PoseStamped, f'/{self.ns}/tracked_target', 10)
        self.predicted_pub = self.create_publisher(
            PoseStamped, f'/{self.ns}/predicted_target', 10)
        self.marker_pub = self.create_publisher(
            MarkerArray, '/tracking/markers', 10)
        self.status_pub = self.create_publisher(
            String, '/tracking/status', 10)

        # 定时器: 更新航迹
        self.timer = self.create_timer(self.dt, self._update_cb)

        self.get_logger().info('=' * 60)
        self.get_logger().info('水下跟踪仿真节点已启动')
        self.get_logger().info(f'  命名空间: {self.ns}')
        self.get_logger().info(f'  Alpha-Beta: alpha={self.alpha}, beta={self.beta}')
        self.get_logger().info(f'  更新频率: {self.rate} Hz')
        self.get_logger().info('=' * 60)

    def _detection_cb(self, msg):
        try:
            detection = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        now = detection.get('timestamp', self.get_clock().now().nanoseconds / 1e9)
        detections = detection.get('detections', [])

        for det in detections:
            if det.get('is_false_positive', False):
                continue

            pos = np.array(det['world_pos'])
            self._associate_and_update(pos, now)

    def _associate_and_update(self, detection, timestamp):
        """最近邻数据关联"""
        best_track = None
        best_dist = float('inf')

        for track in self.tracks:
            if track.status == Track.LOST:
                continue
            pred = track.filter.predict()
            dist = np.linalg.norm(detection - pred)
            if dist < self.gate_dist and dist < best_dist:
                best_dist = dist
                best_track = track

        if best_track is not None:
            best_track.update_with_detection(detection, timestamp)
        else:
            # 新建航迹
            track = Track(self.next_track_id, self.alpha, self.beta,
                          self.dt, self.max_coast)
            self.next_track_id += 1
            track.update_with_detection(detection, timestamp)
            self.tracks.append(track)
            self.get_logger().info(f'新建航迹 #{track.track_id}')

    def _update_cb(self):
        now = self.get_clock().now().nanoseconds / 1e9

        # 清除丢失航迹
        self.tracks = [t for t in self.tracks if t.status != Track.LOST]

        # 对未更新的航迹执行滑行
        for track in self.tracks:
            if now - track.last_update_time > self.dt * 2:
                track.coast(now)

        # 找到最佳跟踪目标 (确认状态, 最近更新)
        best = None
        for track in self.tracks:
            if track.status in (Track.CONFIRMED, Track.COAST):
                if best is None or track.last_update_time > best.last_update_time:
                    best = track

        if best is None:
            return

        # 发布跟踪位置
        pos = best.get_position()
        vel = best.get_velocity()

        target_msg = PoseStamped()
        target_msg.header.frame_id = 'world'
        target_msg.header.stamp = self.get_clock().now().to_msg()
        target_msg.pose.position.x = float(pos[0])
        target_msg.pose.position.y = float(pos[1])
        target_msg.pose.position.z = float(pos[2])
        self.target_pub.publish(target_msg)

        # 发布预测位置
        pred = best.get_predicted_position(self.pred_steps)
        pred_msg = PoseStamped()
        pred_msg.header.frame_id = 'world'
        pred_msg.header.stamp = self.get_clock().now().to_msg()
        pred_msg.pose.position.x = float(pred[0])
        pred_msg.pose.position.y = float(pred[1])
        pred_msg.pose.position.z = float(pred[2])
        self.predicted_pub.publish(pred_msg)

        # 发布标记
        self._publish_markers(best)

        # 发布状态
        speed = np.linalg.norm(vel)
        status = {
            'timestamp': now,
            'track_id': best.track_id,
            'status': best.status,
            'position': pos.tolist(),
            'velocity': vel.tolist(),
            'speed_ms': round(float(speed), 3),
            'history_length': len(best.history),
            'coast_count': best.coast_count,
        }
        status_msg = String()
        status_msg.data = json.dumps(status, ensure_ascii=False)
        self.status_pub.publish(status_msg)

        self.get_logger().info(
            f'跟踪 #{best.track_id}: 位置=({pos[0]:.1f},{pos[1]:.1f},{pos[2]:.1f}), '
            f'速度={speed:.2f}m/s, 状态={best.status}')

    def _publish_markers(self, track):
        markers = MarkerArray()
        pos = track.get_position()
        vel = track.get_velocity()
        speed = np.linalg.norm(vel)

        # 绿色球: 当前跟踪位置
        current = Marker()
        current.header.frame_id = 'world'
        current.header.stamp = self.get_clock().now().to_msg()
        current.ns = 'tracking'
        current.id = track.track_id
        current.type = Marker.SPHERE
        current.action = Marker.ADD
        current.pose.position = Point(x=float(pos[0]), y=float(pos[1]), z=float(pos[2]))
        current.scale.x = 1.5
        current.scale.y = 1.5
        current.scale.z = 1.5
        color = (0.0, 1.0, 0.0) if track.status == Track.CONFIRMED else (1.0, 1.0, 0.0)
        current.color.r = color[0]
        current.color.g = color[1]
        current.color.b = color[2]
        current.color.a = 0.8
        current.lifetime.sec = 1
        markers.markers.append(current)

        # 蓝色线: 航迹历史
        if len(track.history) >= 2:
            trail = Marker()
            trail.header.frame_id = 'world'
            trail.header.stamp = self.get_clock().now().to_msg()
            trail.ns = 'tracking_trail'
            trail.id = track.track_id
            trail.type = Marker.LINE_STRIP
            trail.action = Marker.ADD
            trail.scale.x = 0.15
            trail.color.r = 0.0
            trail.color.g = 0.5
            trail.color.b = 1.0
            trail.color.a = 0.6
            trail.lifetime.sec = 1
            for _, hpos in track.history[-100:]:
                trail.points.append(Point(x=float(hpos[0]), y=float(hpos[1]), z=float(hpos[2])))
            markers.markers.append(trail)

        # 红色球: 预测位置
        pred = track.get_predicted_position(self.pred_steps)
        pred_marker = Marker()
        pred_marker.header.frame_id = 'world'
        pred_marker.header.stamp = self.get_clock().now().to_msg()
        pred_marker.ns = 'tracking_prediction'
        pred_marker.id = track.track_id
        pred_marker.type = Marker.SPHERE
        pred_marker.action = Marker.ADD
        pred_marker.pose.position = Point(x=float(pred[0]), y=float(pred[1]), z=float(pred[2]))
        pred_marker.scale.x = 0.8
        pred_marker.scale.y = 0.8
        pred_marker.scale.z = 0.8
        pred_marker.color.r = 1.0
        pred_marker.color.g = 0.0
        pred_marker.color.b = 0.0
        pred_marker.color.a = 0.5
        pred_marker.lifetime.sec = 1
        markers.markers.append(pred_marker)

        # 速度箭头
        if speed > 0.05:
            arrow = Marker()
            arrow.header.frame_id = 'world'
            arrow.header.stamp = self.get_clock().now().to_msg()
            arrow.ns = 'tracking_velocity'
            arrow.id = track.track_id
            arrow.type = Marker.ARROW
            arrow.action = Marker.ADD
            start = Point(x=float(pos[0]), y=float(pos[1]), z=float(pos[2]))
            scale = min(speed * 2.0, 10.0)
            v_dir = vel / speed
            end = Point(x=float(pos[0] + v_dir[0] * scale),
                        y=float(pos[1] + v_dir[1] * scale),
                        z=float(pos[2] + v_dir[2] * scale))
            arrow.points = [start, end]
            arrow.scale.x = 0.15
            arrow.scale.y = 0.3
            arrow.color.r = 0.0
            arrow.color.g = 1.0
            arrow.color.b = 1.0
            arrow.color.a = 0.8
            arrow.lifetime.sec = 1
            markers.markers.append(arrow)

        self.marker_pub.publish(markers)


def main():
    rclpy.init()
    node = UnderwaterTracker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
