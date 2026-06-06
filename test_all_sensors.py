#!/usr/bin/env python3
"""
RexROV传感器功能测试脚本
测试所有传感器包是否正常工作
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, MagneticField, FluidPressure, NavSatFix, Image
from geometry_msgs.msg import TwistWithCovarianceStamped, Vector3Stamped
from nav_msgs.msg import Odometry
import time

class SensorTester(Node):
    def __init__(self):
        super().__init__('sensor_tester')

        # 测试结果记录
        self.results = {}

        # 创建订阅者
        print("🔍 正在创建传感器订阅者...")

        # 1. IMU
        self.imu_received = False
        self.imu_sub = self.create_subscription(
            Imu, '/rexrov/imu', self.imu_callback, 10)

        # 2. 磁力计
        self.mag_received = False
        self.mag_sub = self.create_subscription(
            Vector3Stamped, '/rexrov/magnetometer', self.mag_callback, 10)

        # 3. GPS
        self.gps_received = False
        self.gps_sub = self.create_subscription(
            NavSatFix, '/rexrov/gps', self.gps_callback, 10)

        # 4. 压力传感器
        self.pressure_received = False
        self.pressure_sub = self.create_subscription(
            FluidPressure, '/rexrov/pressure', self.pressure_callback, 10)

        # 5. DVL (速度)
        self.dvl_received = False
        self.dvl_sub = self.create_subscription(
            TwistWithCovarianceStamped, '/rexrov/dvl', self.dvl_callback, 10)

        # 6. Pose GT (真值)
        self.pose_received = False
        self.pose_sub = self.create_subscription(
            Odometry, '/rexrov/pose_gt', self.pose_callback, 10)

        # 7. Camera
        self.camera_received = False
        self.camera_sub = self.create_subscription(
            Image, '/rexrov/camera', self.camera_callback, 10)

        print("✅ 订阅者创建完成\n")

        # 测试开始时间
        self.start_time = time.time()
        self.test_duration = 10.0  # 测试10秒

    def imu_callback(self, msg):
        if not self.imu_received:
            self.imu_received = True
            self.results['IMU'] = {
                'status': '✅ 正常',
                'data': f'角速度=[{msg.angular_velocity.x:.3f}, {msg.angular_velocity.y:.3f}, {msg.angular_velocity.z:.3f}]',
                'orientation': f'四元数=[{msg.orientation.x:.3f}, {msg.orientation.y:.3f}, {msg.orientation.z:.3f}, {msg.orientation.w:.3f}]'
            }
            print("✅ IMU 数据接收成功")

    def mag_callback(self, msg):
        if not self.mag_received:
            self.mag_received = True
            self.results['磁力计'] = {
                'status': '✅ 正常',
                'data': f'磁场=[{msg.vector.x:.2f}, {msg.vector.y:.2f}, {msg.vector.z:.2f}] μT'
            }
            print("✅ 磁力计 数据接收成功")

    def gps_callback(self, msg):
        if not self.gps_received:
            self.gps_received = True
            status = "有效" if msg.status.status == 0 else "无效"
            self.results['GPS'] = {
                'status': '✅ 正常' if status == "有效" else '⚠️ 无信号',
                'data': f'纬度={msg.latitude:.6f}, 经度={msg.longitude:.6f}, 状态={status}'
            }
            print(f"✅ GPS 数据接收成功 (状态: {status})")

    def pressure_callback(self, msg):
        if not self.pressure_received:
            self.pressure_received = True
            # 计算深度（流体压力公式）
            pressure_pa = msg.fluid_pressure
            depth_m = (pressure_pa - 101325) / (1000 * 9.81)  # 假设淡水
            self.results['压力传感器'] = {
                'status': '✅ 正常',
                'data': f'压力={pressure_pa:.1f} Pa, 深度约={depth_m:.2f} m'
            }
            print("✅ 压力传感器 数据接收成功")

    def dvl_callback(self, msg):
        if not self.dvl_received:
            self.dvl_received = True
            vel = msg.twist.twist.linear
            self.results['DVL'] = {
                'status': '✅ 正常',
                'data': f'速度=[{vel.x:.3f}, {vel.y:.3f}, {vel.z:.3f}] m/s'
            }
            print("✅ DVL 数据接收成功")

    def pose_callback(self, msg):
        # 这个会持续接收，所以只显示第一次
        if not self.pose_received:
            self.pose_received = True
            pos = msg.pose.pose.position
            ori = msg.pose.pose.orientation
            self.results['Pose_GT'] = {
                'status': '✅ 正常',
                'data': f'位置=[{pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f}]'
            }
            print("✅ Pose_GT 数据接收成功")

    def camera_callback(self, msg):
        if not self.camera_received:
            self.camera_received = True
            self.results['Camera'] = {
                'status': '✅ 正常',
                'data': f'分辨率={msg.width}x{msg.height}, 编码={msg.encoding}'
            }
            print("✅ Camera 数据接收成功")

    def print_results(self):
        print("\n" + "="*70)
        print("📊 传感器测试结果")
        print("="*70)

        # 传感器列表
        sensors = ['IMU', '磁力计', 'GPS', '压力传感器', 'DVL', 'Pose_GT', 'Camera']

        all_ok = True
        for sensor in sensors:
            if sensor in self.results:
                result = self.results[sensor]
                print(f"\n【{sensor}】")
                print(f"  状态: {result['status']}")
                print(f"  数据: {result['data']}")
                if '⚠️' in result['status']:
                    all_ok = False
            else:
                print(f"\n【{sensor}】")
                print(f"  状态: ❌ 未接收到数据")
                all_ok = False

        print("\n" + "="*70)
        if all_ok:
            print("✅ 所有传感器工作正常！")
        else:
            print("⚠️  部分传感器未正常工作")
        print("="*70)

        # 额外建议
        print("\n💡 建议：")
        if 'GPS' in self.results and '⚠️' in self.results['GPS']['status']:
            print("   - GPS无信号：机器人可能在水下（正常现象）")
        if not all_ok:
            print("   - 检查Gazebo和机器人是否正常启动")
            print("   - 使用 'ros2 topic list' 查看话题是否存在")
            print("   - 使用 'ros2 topic echo <topic_name>' 查看话题数据")

def main():
    rclpy.init()

    print("="*70)
    print("🧪 RexROV 传感器功能测试")
    print("="*70)
    print("💡 正在测试所有传感器，请稍候10秒...")
    print()

    try:
        tester = SensorTester()

        # 旋转10秒，收集数据
        start_time = time.time()
        while time.time() - start_time < tester.test_duration:
            rclpy.spin_once(tester, timeout_sec=0.1)

        # 打印结果
        tester.print_results()

    except KeyboardInterrupt:
        print("\n\n👋 测试中断")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
    finally:
        tester.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
