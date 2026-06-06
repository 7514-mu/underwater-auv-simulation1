#!/usr/bin/env python3
"""
水下探测仿真节点

基于声纳(PointCloud2)数据进行目标探测。

【理论依据】
  1. 声纳点云距离检测: 目标点云距离显著短于周围背景
  2. 空间聚类: 相邻检测点合并为同一目标
  3. 坐标变换: 声纳坐标 → 世界坐标
  4. 气泡影响: 气泡散射 → 声纳有效距离缩短 + 虚警率上升

使用方法:
  本节点订阅 /auv_1/auv_1_sonar_controller/out (sensor_msgs/PointCloud2)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from std_msgs.msg import Float64, String
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
import numpy as np
import struct
import json
import math


class UnderwaterDetector(Node):

    def __init__(self):
        super().__init__('underwater_detector')

        # 参数
        self.declare_parameter('namespace', 'auv_1')
        self.declare_parameter('sonar_topic', '')
        self.declare_parameter('detection_range_max', 80.0)
        self.declare_parameter('detection_range_min', 1.0)
        self.declare_parameter('detection_threshold', 2.0)
        self.declare_parameter('cluster_distance', 3.0)
        self.declare_parameter('min_cluster_size', 3)
        self.declare_parameter('false_positive_rate', 0.02)
        self.declare_parameter('bubble_sonar_degradation', 0.3)
        self.declare_parameter('bubble_false_detect_factor', 0.1)

        self.ns = self.get_parameter('namespace').value
        sonar_topic = self.get_parameter('sonar_topic').value
        self.range_max = self.get_parameter('detection_range_max').value
        self.range_min = self.get_parameter('detection_range_min').value
        self.threshold = self.get_parameter('detection_threshold').value
        self.cluster_dist = self.get_parameter('cluster_distance').value
        self.min_cluster = self.get_parameter('min_cluster_size').value
        self.fp_rate = self.get_parameter('false_positive_rate').value
        self.bubble_sonar_deg = self.get_parameter('bubble_sonar_degradation').value
        self.bubble_fp_factor = self.get_parameter('bubble_false_detect_factor').value

        if not sonar_topic:
            sonar_topic = f'/{self.ns}/{self.ns}_sonar_controller/out'

        # 状态
        self.vehicle_pos = np.zeros(3)
        self.vehicle_yaw = 0.0
        self.pose_valid = False
        self.bubble_density = 0.0
        self.detection_id = 0

        # 订阅
        self.create_subscription(
            PointCloud2, sonar_topic, self._sonar_cb, 10)
        self.create_subscription(
            Odometry, f'/{self.ns}/pose_gt', self._pose_cb, 10)
        self.create_subscription(
            Float64, '/bubble_sim/density', self._density_cb, 10)

        # 发布
        self.marker_pub = self.create_publisher(
            MarkerArray, f'/{self.ns}/detected_objects', 10)
        self.result_pub = self.create_publisher(
            String, '/detection/results', 10)

        self.get_logger().info('=' * 60)
        self.get_logger().info('水下探测仿真节点已启动')
        self.get_logger().info(f'  命名空间: {self.ns}')
        self.get_logger().info(f'  声纳话题: {sonar_topic}')
        self.get_logger().info(f'  声纳范围: {self.range_min}~{self.range_max} m')
        self.get_logger().info('=' * 60)

    def _pose_cb(self, msg):
        p = msg.pose.pose.position
        self.vehicle_pos = np.array([p.x, p.y, p.z])
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.vehicle_yaw = math.atan2(siny_cosp, cosy_cosp)
        self.pose_valid = True

    def _density_cb(self, msg):
        self.bubble_density = max(0.0, min(1.0, msg.data))

    def _parse_pointcloud2(self, msg):
        """解析 PointCloud2 为 Nx3 numpy 数组 (x, y, z)"""
        # 找到 x, y, z 字段的偏移量
        field_map = {}
        for f in msg.fields:
            field_map[f.name] = (f.offset, f.datatype)

        # FLOAT32 = 7
        x_off = field_map.get('x', (0, 7))[0]
        y_off = field_map.get('y', (4, 7))[0]
        z_off = field_map.get('z', (8, 7))[0]

        point_step = msg.point_step
        n_points = msg.width * msg.height
        data = bytes(msg.data)

        points = []
        for i in range(n_points):
            base = i * point_step
            try:
                x = struct.unpack_from('f', data, base + x_off)[0]
                y = struct.unpack_from('f', data, base + y_off)[0]
                z = struct.unpack_from('f', data, base + z_off)[0]
            except struct.error:
                continue
            if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
                points.append([x, y, z])

        if not points:
            return np.zeros((0, 3))
        return np.array(points)

    def _sonar_cb(self, msg):
        if not self.pose_valid:
            return

        # 解析点云
        points = self._parse_pointcloud2(msg)
        if len(points) < self.min_cluster:
            return

        # 有效距离 (气泡影响)
        eff_max = self.range_max * (1.0 - self.bubble_density * self.bubble_sonar_deg)

        # 只保留航行器前方的点 (前方120度扇形)
        diffs = points - self.vehicle_pos
        ranges = np.linalg.norm(diffs, axis=1)
        angles = np.arctan2(diffs[:, 1], diffs[:, 0]) - self.vehicle_yaw
        angles = np.arctan2(np.sin(angles), np.cos(angles))  # 归一化到 [-pi, pi]
        front_mask = np.abs(angles) < np.radians(60)

        # 过滤范围
        valid_mask = front_mask & (ranges > self.range_min) & (ranges < eff_max)
        valid_points = points[valid_mask]
        valid_ranges = ranges[valid_mask]

        if len(valid_points) < self.min_cluster:
            self._publish_clear_markers()
            return

        # 直接对所有前方有效点聚类，找最大目标
        clusters = self._cluster_points(valid_points, valid_ranges)

        if not clusters:
            self._publish_clear_markers()
            return

        # 过滤有效目标（至少3个点才认为是真实目标）
        valid_clusters = [c for c in clusters if c['size'] >= 3]
        if not valid_clusters:
            self._publish_clear_markers()
            return

        # 按点数降序排列，保留所有有效目标
        valid_clusters.sort(key=lambda c: c['size'], reverse=True)
        self.get_logger().info(f'发现 {len(valid_clusters)} 个有效目标聚类')

        # 虚警注入 (气泡影响，低概率)
        fp_prob = self.fp_rate + self.bubble_density * self.bubble_fp_factor
        final_clusters = list(valid_clusters)
        if np.random.random() < fp_prob:
            false_angle = np.random.uniform(-math.pi, math.pi)
            false_range = np.random.uniform(self.range_min, eff_max * 0.7)
            world_angle = false_angle + self.vehicle_yaw
            false_pos = np.array([
                self.vehicle_pos[0] + false_range * math.cos(world_angle),
                self.vehicle_pos[1] + false_range * math.sin(world_angle),
                self.vehicle_pos[2],
            ])
            self.detection_id += 1
            final_clusters.append({
                'id': self.detection_id,
                'world_pos': false_pos.tolist(),
                'mean_range': float(false_range),
                'span': np.random.uniform(0.5, 2.0),
                'size': np.random.randint(2, 6),
                'is_false_positive': True,
            })

        self._publish_markers(final_clusters)
        self._publish_results(final_clusters)

    def _cluster_points(self, points, ranges):
        """基于空间距离聚类检测点"""
        if len(points) == 0:
            return []

        # 按距离排序
        sort_idx = np.argsort(ranges)
        sorted_points = points[sort_idx]
        sorted_ranges = ranges[sort_idx]

        clusters = []
        current_points = [sorted_points[0]]
        current_ranges = [sorted_ranges[0]]

        for i in range(1, len(sorted_points)):
            if np.linalg.norm(sorted_points[i] - sorted_points[i - 1]) < self.cluster_dist:
                current_points.append(sorted_points[i])
                current_ranges.append(sorted_ranges[i])
            else:
                if len(current_points) >= self.min_cluster:
                    clusters.append((np.array(current_points), np.array(current_ranges)))
                current_points = [sorted_points[i]]
                current_ranges = [sorted_ranges[i]]

        if len(current_points) >= self.min_cluster:
            clusters.append((np.array(current_points), np.array(current_ranges)))

        result = []
        for pts, rgs in clusters:
            centroid = np.mean(pts, axis=0)
            mean_range = np.mean(rgs)
            # 估算目标展宽
            if len(pts) > 1:
                span = np.max(np.linalg.norm(pts - centroid, axis=1)) * 2
            else:
                span = 0.5

            self.detection_id += 1
            result.append({
                'id': self.detection_id,
                'world_pos': centroid.tolist(),
                'mean_range': float(mean_range),
                'span': float(span),
                'size': len(pts),
                'is_false_positive': False,
            })

        return result

    def _publish_markers(self, clusters):
        markers = MarkerArray()
        for c in clusters:
            marker = Marker()
            marker.header.frame_id = 'world'
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'detected_objects'
            marker.id = c['id']
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position = Point(
                x=c['world_pos'][0],
                y=c['world_pos'][1],
                z=c['world_pos'][2])
            marker.scale.x = 1.0
            marker.scale.y = 1.0
            marker.scale.z = 1.0
            if c['is_false_positive']:
                marker.color.r = 1.0
                marker.color.g = 1.0
                marker.color.b = 0.0
            else:
                marker.color.r = 1.0
                marker.color.g = 0.0
                marker.color.b = 0.0
            marker.color.a = 0.8
            marker.lifetime.sec = 1
            markers.markers.append(marker)
        self.marker_pub.publish(markers)

    def _publish_clear_markers(self):
        m = MarkerArray()
        marker = Marker()
        marker.ns = 'detected_objects'
        marker.action = Marker.DELETEALL
        m.markers.append(marker)
        self.marker_pub.publish(m)

    def _publish_results(self, clusters):
        now = self.get_clock().now().nanoseconds / 1e9
        result = {
            'timestamp': now,
            'detector': self.ns,
            'bubble_density': self.bubble_density,
            'detections': clusters,
        }
        msg = String()
        msg.data = json.dumps(result, ensure_ascii=False)
        self.result_pub.publish(msg)

        real_count = sum(1 for c in clusters if not c['is_false_positive'])
        fp_count = sum(1 for c in clusters if c['is_false_positive'])
        self.get_logger().info(
            f'探测结果: {len(clusters)}个目标 (真实:{real_count}, 虚警:{fp_count}), '
            f'气泡密度={self.bubble_density:.1f}')


def main():
    rclpy.init()
    node = UnderwaterDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
