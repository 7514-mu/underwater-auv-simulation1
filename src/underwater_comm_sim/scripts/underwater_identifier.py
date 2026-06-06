#!/usr/bin/env python3
"""
水下识别仿真节点

对探测到的目标进行分类识别。

【理论依据】
  1. 声纳尺寸分类: 根据目标回波展宽估计目标尺寸
  2. 声纳形状分类: 根据长宽比区分鱼雷型/箱型
  3. 相机颜色匹配: 从图像中提取目标颜色特征
  4. 加权投票: 多特征融合 → 最终分类结果

使用方法:
  订阅 /detection/results (JSON)
  发布 /auv_1/identified_targets (JSON)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
import json
import numpy as np


# 已知航行器特征库
VEHICLE_DATABASE = {
    'torpedo_small': {
        'name': '小型鱼雷AUV (如ECA A9)',
        'length': 2.0,
        'width': 0.3,
        'aspect_ratio': 6.6,
        'color': 'dark_gray',
    },
    'box_medium': {
        'name': '中型箱式ROV (如RexROV)',
        'length': 2.0,
        'width': 1.5,
        'aspect_ratio': 1.3,
        'color': 'yellow',
    },
    'torpedo_medium': {
        'name': '中型鱼雷AUV (如Missile AUV)',
        'length': 3.0,
        'width': 0.3,
        'aspect_ratio': 10.0,
        'color': 'dark_gray',
    },
}


class UnderwaterIdentifier(Node):

    def __init__(self):
        super().__init__('underwater_identifier')

        self.declare_parameter('namespace', 'auv_1')
        self.declare_parameter('small_size_max', 1.0)
        self.declare_parameter('medium_size_max', 3.0)
        self.declare_parameter('aspect_ratio_threshold', 3.0)

        self.ns = self.get_parameter('namespace').value
        self.small_max = self.get_parameter('small_size_max').value
        self.medium_max = self.get_parameter('medium_size_max').value
        self.aspect_threshold = self.get_parameter('aspect_ratio_threshold').value

        # 订阅探测结果
        self.create_subscription(
            String, '/detection/results', self._detection_cb, 10)

        # 发布识别结果
        self.result_pub = self.create_publisher(
            String, f'/{self.ns}/identified_targets', 10)
        self.marker_pub = self.create_publisher(
            MarkerArray, '/identification/markers', 10)

        self.get_logger().info('=' * 60)
        self.get_logger().info('水下识别仿真节点已启动')
        self.get_logger().info(f'  命名空间: {self.ns}')
        self.get_logger().info(f'  特征库: {list(VEHICLE_DATABASE.keys())}')
        self.get_logger().info('=' * 60)

    def _detection_cb(self, msg):
        try:
            detection = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().error('探测结果JSON解析失败')
            return

        detections = detection.get('detections', [])
        if not detections:
            return

        identified = []
        for det in detections:
            if det.get('is_false_positive', False):
                continue

            # 特征提取
            span = det.get('span', 0.0)
            size = det.get('size', 0)
            mean_range = det.get('mean_range', 10.0)

            # 估计目标尺寸 (声纳角度展宽 × 距离)
            estimated_length = span
            estimated_width = max(size * mean_range * 0.02, 0.1)

            # 分类
            size_class = self._classify_size(estimated_length)
            shape_class = self._classify_shape(estimated_length, estimated_width)

            # 匹配特征库
            best_match, confidence = self._match_database(size_class, shape_class)

            identified.append({
                'id': det['id'],
                'position': det['world_pos'],
                'size_class': size_class,
                'shape_class': shape_class,
                'estimated_length': round(estimated_length, 2),
                'best_match': best_match,
                'confidence': round(confidence, 3),
            })

        if not identified:
            return

        # 发布结果
        now = self.get_clock().now().nanoseconds / 1e9
        result = {
            'timestamp': now,
            'identifier': self.ns,
            'targets': identified,
        }
        result_msg = String()
        result_msg.data = json.dumps(result, ensure_ascii=False)
        self.result_pub.publish(result_msg)

        # 发布标记
        self._publish_markers(identified)

        for t in identified:
            self.get_logger().info(
                f'识别: ID={t["id"]}, 类型={t["best_match"]}, '
                f'形状={t["shape_class"]}, 尺寸={t["size_class"]}, '
                f'置信度={t["confidence"]:.2f}')

    def _classify_size(self, estimated_length):
        """尺寸分类"""
        if estimated_length < self.small_max:
            return 'small'
        elif estimated_length < self.medium_max:
            return 'medium'
        else:
            return 'large'

    def _classify_shape(self, length, width):
        """形状分类: 鱼雷型 vs 箱型"""
        if width < 0.01:
            return 'unknown'
        aspect = length / width
        if aspect > self.aspect_threshold:
            return 'torpedo'
        else:
            return 'box'

    def _match_database(self, size_class, shape_class):
        """匹配特征库, 返回最佳匹配和置信度"""
        best_match = '未知目标'
        best_score = 0.0

        for key, profile in VEHICLE_DATABASE.items():
            score = 0.0

            # 形状匹配
            db_shape = 'torpedo' if profile['aspect_ratio'] > self.aspect_threshold else 'box'
            if shape_class == db_shape:
                score += 0.6
            elif shape_class == 'unknown':
                score += 0.2

            # 尺寸匹配
            db_size = 'small' if profile['length'] < self.small_max else 'medium'
            if size_class == db_size:
                score += 0.4

            if score > best_score:
                best_score = score
                best_match = profile['name']

        return best_match, best_score

    def _publish_markers(self, identified):
        markers = MarkerArray()
        for t in identified:
            pos = t['position']

            # 文本标记 (显示识别结果)
            marker = Marker()
            marker.header.frame_id = 'world'
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'identified_targets'
            marker.id = t['id'] + 10000
            marker.type = Marker.TEXT_VIEW_FACING
            marker.action = Marker.ADD
            marker.pose.position = Point(
                x=pos[0], y=pos[1], z=pos[2] + 1.5)
            marker.scale.z = 0.8
            marker.color.r = 1.0
            marker.color.g = 1.0
            marker.color.b = 1.0
            marker.color.a = 1.0
            marker.text = f'{t["best_match"]}\n{t["confidence"]:.0%}'
            marker.lifetime.sec = 2
            markers.markers.append(marker)

            # 蓝色球 (已识别目标)
            sphere = Marker()
            sphere.header.frame_id = 'world'
            sphere.header.stamp = self.get_clock().now().to_msg()
            sphere.ns = 'identified_targets'
            sphere.id = t['id'] + 20000
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position = Point(x=pos[0], y=pos[1], z=pos[2])
            sphere.scale.x = 1.2
            sphere.scale.y = 1.2
            sphere.scale.z = 1.2
            sphere.color.r = 0.0
            sphere.color.g = 0.5
            sphere.color.b = 1.0
            sphere.color.a = 0.6
            sphere.lifetime.sec = 2
            markers.markers.append(sphere)

        self.marker_pub.publish(markers)


def main():
    rclpy.init()
    node = UnderwaterIdentifier()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
