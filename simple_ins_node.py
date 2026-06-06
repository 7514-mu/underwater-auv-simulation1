#!/usr/bin/env python3
"""
简单的惯性导航系统（INS）节点
融合IMU、GPS、DVL、压力传感器数据
使用扩展卡尔曼滤波（EKF）
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, MagneticField, FluidPressure, NavSatFix
from geometry_msgs.msg import TwistWithCovarianceStamped, Vector3Stamped
from nav_msgs.msg import Odometry
import numpy as np
from collections import deque
import math

class SimpleINS(Node):
    def __init__(self):
        super().__init__('simple_ins')

        # 状态向量: [x, y, z, vx, vy, vz, roll, pitch, yaw]
        self.state = np.zeros(9)
        self.state_covariance = np.eye(9) * 0.1  # 初始协方差

        # 传感器数据缓冲
        self.imu_buffer = deque(maxlen=10)
        self.gps_buffer = deque(maxlen=10)
        self.dvl_buffer = deque(maxlen=10)
        self.pressure_buffer = deque(maxlen=10)
        self.mag_buffer = deque(maxlen=10)

        # 时间戳
        self.last_time = None
        self.dt = 0.02  # 假设50Hz

        # INS配置
        self.use_gps = False  # GPS在水下不可用
        self.use_pressure = True
        self.use_dvl = True
        self.use_mag = True

        print("="*70)
        print("🧭 简单惯性导航系统（INS）")
        print("="*70)
        print("📡 正在订阅传感器数据...")

        # 订阅传感器
        self.imu_sub = self.create_subscription(Imu, '/rexrov/imu', self.imu_callback, 10)
        self.gps_sub = self.create_subscription(NavSatFix, '/rexrov/gps', self.gps_callback, 10)
        self.dvl_sub = self.create_subscription(TwistWithCovarianceStamped, '/rexrov/dvl', self.dvl_callback, 10)
        self.pressure_sub = self.create_subscription(FluidPressure, '/rexrov/pressure', self.pressure_callback, 10)
        self.mag_sub = self.create_subscription(Vector3Stamped, '/rexrov/magnetometer', self.mag_callback, 10)

        # 发布估计的位姿
        self.ins_pub = self.create_publisher(Odometry, '/rexrov/ins/estimate', 10)

        # 创建定时器进行状态预测
        self.create_timer(0.02, self.predict_and_update)  # 50Hz

        print("✅ INS节点已启动")
        print("💡 融合传感器: IMU + DVL + 压力 + 磁力计")
        print("💡 发布话题: /rexrov/ins/estimate")
        print()

    def imu_callback(self, msg):
        """IMU回调 - 提供加速度和角速度"""
        self.imu_buffer.append({
            'time': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'angular_velocity': np.array([
                msg.angular_velocity.x,
                msg.angular_velocity.y,
                msg.angular_velocity.z
            ]),
            'linear_acceleration': np.array([
                msg.linear_acceleration.x,
                msg.linear_acceleration.y,
                msg.linear_acceleration.z
            ])
        })

    def gps_callback(self, msg):
        """GPS回调 - 提供绝对位置（仅水面）"""
        if msg.status.status == 0:  # 有效
            # 简单的经纬度到UTM转换（这里简化处理）
            self.gps_buffer.append({
                'time': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
                'position': np.array([msg.latitude, msg.longitude, 0.0])
            })

    def dvl_callback(self, msg):
        """DVL回调 - 提供速度测量"""
        self.dvl_buffer.append({
            'time': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'velocity': np.array([
                msg.twist.twist.linear.x,
                msg.twist.twist.linear.y,
                msg.twist.twist.linear.z
            ])
        })

    def pressure_callback(self, msg):
        """压力传感器回调 - 提供深度"""
        pressure = msg.fluid_pressure
        # 转换为深度（淡水）
        depth = (pressure - 101325) / (1000 * 9.81)

        self.pressure_buffer.append({
            'time': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'depth': depth
        })

    def mag_callback(self, msg):
        """磁力计回调 - 提供航向角"""
        mag = np.array([msg.vector.x, msg.vector.y, msg.vector.z])

        # 简单的磁力计航向计算
        yaw = math.atan2(-mag[1], mag[0])

        self.mag_buffer.append({
            'time': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'yaw': yaw
        })

    def predict_and_update(self):
        """EKF预测和更新步骤"""
        if len(self.imu_buffer) == 0:
            return

        # 获取最新的IMU数据
        imu_data = self.imu_buffer[-1]

        # === 预测步骤 ===
        # 状态转移: x(k+1) = f(x(k), u(k))
        # u(k) = [ax, ay, az, wx, wy, wz] (IMU测量)

        # 提取IMU数据
        accel = imu_data['linear_acceleration']
        omega = imu_data['angular_velocity']

        # 简单的运动学模型
        # 位置更新: p(k+1) = p(k) + v(k)*dt + 0.5*a*dt^2
        self.state[0:3] += self.state[3:6] * self.dt + 0.5 * accel * self.dt**2

        # 速度更新: v(k+1) = v(k) + a*dt
        self.state[3:6] += accel * self.dt

        # 姿态更新: theta(k+1) = theta(k) + omega*dt
        self.state[6:9] += omega * self.dt

        # 协方差预测
        # P(k+1|k) = F*P(k|k)*F' + Q
        # 简化：增加过程噪声
        Q = np.eye(9) * 0.001
        self.state_covariance += Q

        # === 更新步骤 ===
        # 1. DVL速度更新
        if len(self.dvl_buffer) > 0 and self.use_dvl:
            dvl_data = self.dvl_buffer[-1]
            z_vel = dvl_data['velocity']

            # 测量矩阵H（提取速度）
            H_vel = np.zeros((3, 9))
            H_vel[0, 3] = 1  # vx
            H_vel[1, 4] = 1  # vy
            H_vel[2, 5] = 1  # vz

            # 卡尔曼增益
            R_vel = np.eye(3) * 0.01  # 测量噪声
            S = H_vel @ self.state_covariance @ H_vel.T + R_vel
            K = self.state_covariance @ H_vel.T @ np.linalg.inv(S)

            # 状态更新
            y = z_vel - self.state[3:6]  # 残差
            self.state += K @ y
            self.state_covariance = (np.eye(9) - K @ H_vel) @ self.state_covariance

        # 2. 压力传感器深度更新
        if len(self.pressure_buffer) > 0 and self.use_pressure:
            press_data = self.pressure_buffer[-1]
            z_depth = press_data['depth']

            # 测量矩阵H（提取z位置）
            H_depth = np.zeros((1, 9))
            H_depth[0, 2] = 1  # z

            # 卡尔曼增益
            R_depth = np.eye(1) * 0.1  # 测量噪声
            S = H_depth @ self.state_covariance @ H_depth.T + R_depth
            K = self.state_covariance @ H_depth.T @ np.linalg.inv(S)

            # 状态更新
            y = np.array([z_depth]) - self.state[2:3]  # 残差
            self.state += K @ y
            self.state_covariance = (np.eye(9) - K @ H_depth) @ self.state_covariance

        # 3. 磁力计航向更新
        if len(self.mag_buffer) > 0 and self.use_mag:
            mag_data = self.mag_buffer[-1]
            z_yaw = mag_data['yaw']

            # 测量矩阵H（提取偏航角）
            H_yaw = np.zeros((1, 9))
            H_yaw[0, 8] = 1  # yaw

            # 卡尔曼增益
            R_yaw = np.eye(1) * 0.05  # 测量噪声
            S = H_yaw @ self.state_covariance @ H_yaw.T + R_yaw
            K = self.state_covariance @ H_yaw.T @ np.linalg.inv(S)

            # 状态更新（考虑角度wrap-around）
            yaw_error = z_yaw - self.state[8]
            # 归一化到[-pi, pi]
            yaw_error = (yaw_error + np.pi) % (2 * np.pi) - np.pi

            self.state += K * yaw_error
            self.state_covariance = (np.eye(9) - K @ H_yaw) @ self.state_covariance

        # 发布估计的位姿
        self.publish_odometry()

    def publish_odometry(self):
        """发布里程计消息"""
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "world"
        msg.child_frame_id = "rexrov/base_link"

        # 位置
        msg.pose.pose.position.x = self.state[0]
        msg.pose.pose.position.y = self.state[1]
        msg.pose.pose.position.z = self.state[2]

        # 姿态（欧拉角转四元数）
        roll, pitch, yaw = self.state[6:9]
        q = self.euler_to_quaternion(roll, pitch, yaw)
        msg.pose.pose.orientation.x = q[0]
        msg.pose.pose.orientation.y = q[1]
        msg.pose.pose.orientation.z = q[2]
        msg.pose.pose.orientation.w = q[3]

        # 速度
        msg.twist.twist.linear.x = self.state[3]
        msg.twist.twist.linear.y = self.state[4]
        msg.twist.twist.linear.z = self.state[5]

        # 协方差（简化）
        msg.pose.covariance = list(self.state_covariance[0:6, 0:6].flatten())

        self.ins_pub.publish(msg)

    def euler_to_quaternion(self, roll, pitch, yaw):
        """欧拉角转四元数"""
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        q = np.zeros(4)
        q[0] = cr * cp * cy + sr * sp * sy  # x
        q[1] = sr * cp * cy - cr * sp * sy  # y
        q[2] = cr * sp * cy + sr * cp * sy  # z
        q[3] = cr * cp * sy - sr * sp * cy  # w

        return q

def main():
    rclpy.init()

    try:
        ins = SimpleINS()

        print("🧭 INS节点正在运行...")
        print("💡 正在融合传感器数据...")
        print("💡 发布融合后的位姿估计")
        print()

        rclpy.spin(ins)

    except KeyboardInterrupt:
        print("\n👋 INS节点已停止")
    finally:
        ins.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
