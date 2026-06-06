#!/usr/bin/env python3
"""
Bubble Image Processor Node

对相机图像进行后处理，模拟水下气泡群的光学效应。

【理论依据】
  1. Mie散射理论: 气泡散射光强分布 (胡峻霖 2017)
  2. Beer-Lambert定律: 光强随传播距离指数衰减
  3. 水下光谱特性: 红光衰减>绿光>蓝光 (Smith & Baker 1981)
  4. 多次散射: PSF近似高斯分布 (胡峻霖 次数追踪算法)

Post-processes camera images to simulate underwater bubble effects:
- Scattering blur: Gaussian PSF approximation (Mie散射)
- Light attenuation: Beer-Lambert定律 I=I₀exp(-μL)
- Color shift: 红光吸收系数最大 (Smith & Baker 1981)
- Speckle noise: 气泡反射随机亮斑

Parameters:
  bubble_density (double) - bubble density factor 0.0~1.0 (default: 0.3)
  scattering_strength (double) - blur kernel size factor (default: 3.0)
  attenuation (double) - light attenuation factor (default: 0.85)
  red_attenuation (double) - red channel extra attenuation (default: 0.6)
  noise_level (double) - speckle noise intensity (default: 0.03)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class BubbleImageProcessor(Node):
    def __init__(self):
        super().__init__('bubble_image_processor')

        self.declare_parameter('namespace', 'rexrov')
        self.declare_parameter('camera_suffix', '')  # '', 'right', or 'left'
        self.declare_parameter('bubble_density', 0.3)
        self.declare_parameter('scattering_strength', 3.0)
        self.declare_parameter('attenuation', 0.85)
        self.declare_parameter('red_attenuation', 0.6)
        self.declare_parameter('noise_level', 0.03)

        ns = self.get_parameter('namespace').value
        suffix = self.get_parameter('camera_suffix').value
        self.bubble_density = self.get_parameter('bubble_density').value
        self.scattering_strength = self.get_parameter('scattering_strength').value
        self.attenuation = self.get_parameter('attenuation').value
        self.red_attenuation = self.get_parameter('red_attenuation').value
        self.noise_level = self.get_parameter('noise_level').value

        self.bridge = CvBridge()

        # RexROV camera topics: /rexrov/camera{suffix}/image_raw
        cam_name = f'{ns}/camera{suffix}'
        self.sub = self.create_subscription(
            Image,
            f'/{cam_name}/image_raw',
            self.image_callback,
            10)

        self.pub = self.create_publisher(
            Image,
            f'/{cam_name}/bubble_image',
            10)

        if not HAS_CV2:
            self.get_logger().warn(
                'OpenCV not installed. Image processing disabled. '
                'Install with: pip install opencv-python')
        else:
            self.get_logger().info(
                f'Bubble image processor: /{cam_name}/image_raw -> /{cam_name}/bubble_image, '
                f'density={self.bubble_density}')

    def image_callback(self, msg):
        if not HAS_CV2:
            return

        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'CV bridge error: {e}')
            return

        # 1. 散射模糊 (Mie散射效应)
        # 气泡密度越高，散射越强，模糊核越大
        # Mie散射理论：散射角与气泡半径、光波长相关
        ksize = int(self.scattering_strength * self.bubble_density * 10)
        if ksize % 2 == 0:
            ksize += 1
        ksize = max(1, min(ksize, 21))
        if ksize > 1:
            scattered = cv2.GaussianBlur(cv_image, (ksize, ksize), 0)
        else:
            scattered = cv_image

        # 2. 光衰减 (Beer-Lambert定律)
        # I = I0 × exp(-μ × L)
        # μ: 衰减系数，与气泡密度成正比
        # L: 光传播距离
        attenuation_factor = self.attenuation ** self.bubble_density
        scattered = (scattered * attenuation_factor).astype(np.uint8)

        # 3. 颜色偏移 (水下光谱特性, Smith & Baker 1981)
        # 红光吸收系数最大，蓝光最小
        # 气泡越多，红色通道衰减越明显
        b, g, r = cv2.split(scattered)
        red_factor = self.red_attenuation ** self.bubble_density
        r = (r * red_factor).astype(np.uint8)
        # 蓝光相对增强，模拟水下蓝绿色调
        b_enhance = 1.0 + self.bubble_density * 0.2
        b = np.clip(b.astype(np.float32) * b_enhance, 0, 255).astype(np.uint8)
        colored = cv2.merge([b, g, r])

        # 4. 散斑噪声 (气泡反射)
        # 气泡反射光线产生随机亮斑 (胡峻霖 2017: 多次散射光强递减)
        noise_std = self.noise_level * 255 * self.bubble_density
        noise = np.random.normal(0, noise_std, colored.shape).astype(np.float32)
        noisy = np.clip(colored.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        # 5. 对比度降低 (浑浊效应)
        if self.bubble_density > 0.1:
            alpha = 1.0 - self.bubble_density * 0.4
            beta = self.bubble_density * 25
            noisy = cv2.convertScaleAbs(noisy, alpha=alpha, beta=beta)

        # Publish processed image
        try:
            out_msg = self.bridge.cv2_to_imgmsg(noisy, encoding='bgr8')
            out_msg.header = msg.header
            self.pub.publish(out_msg)
        except Exception as e:
            self.get_logger().error(f'Publish error: {e}')


def main():
    rclpy.init()
    node = BubbleImageProcessor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
