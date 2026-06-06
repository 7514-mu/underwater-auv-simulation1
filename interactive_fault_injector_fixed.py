#!/usr/bin/env python3
"""
交互式官方故障注入系统
使用正确的服务名称
增强版：包含自定义故障类型（湍流、磁场、压力舱、传感器漂移、水温变化、IMU、磁力计）

物理故障（湍流、磁场、压力舱、传感器漂移）现在直接通过ApplyLinkWrench
对机器人本体施加真实的物理力，而非通过推进器模拟。

传感器故障（IMU、磁力计）通过订阅原始传感器数据，添加噪声和偏置后重新发布。
"""

import rclpy
from rclpy.node import Node
from uuv_world_ros_plugins_msgs.srv import SetCurrentVelocity
from gazebo_msgs.srv import ApplyLinkWrench
from geometry_msgs.msg import Vector3
from std_msgs.msg import Float64
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Vector3Stamped
import time
import sys
import random
import math
import threading
import numpy as np

class InteractiveFaultInjector(Node):
    def __init__(self):
        super().__init__('interactive_fault_injector')

        self.namespace = '/rexrov'

        # 创建服务客户端 - 使用正确的服务名称
        self.current_client = self.create_client(
            SetCurrentVelocity, '/hydrodynamics/set_current_velocity')
        self.wrench_client = self.create_client(
            ApplyLinkWrench, '/apply_link_wrench')

        # 为每个推进器创建服务客户端
        self.thruster_state_clients = {}
        self.thruster_eff_clients = {}

        for i in range(8):
            # 正确的服务名称格式
            state_srv = f'{self.namespace}/thrusters/id_{i}/set_thruster_state'
            eff_srv = f'{self.namespace}/thrusters/id_{i}/set_thrust_force_efficiency'

            # 创建客户端时使用std_srvs/SetBool
            from std_srvs.srv import SetBool
            from uuv_gazebo_ros_plugins_msgs.srv import SetThrusterEfficiency

            self.thruster_state_clients[i] = self.create_client(SetBool, state_srv)
            self.thruster_eff_clients[i] = self.create_client(SetThrusterEfficiency, eff_srv)

        # 创建推进器指令发布者（用于自定义故障）
        self.thruster_pubs = []
        for i in range(8):
            topic = f'{self.namespace}/thrusters/id_{i}/input'
            pub = self.create_publisher(Float64, topic, 10)
            self.thruster_pubs.append(pub)

        self.custom_fault_active = False
        self.custom_fault_thread = None
        self.active_faults = []  # 记录所有活动故障

        # 传感器故障参数
        self.imu_noise_std = 0.0  # IMU噪声标准差
        self.imu_bias = [0.0, 0.0, 0.0]  # IMU偏置 [ax, ay, az]
        self.imu_angular_noise = 0.0  # 角速度噪声
        self.imu_fault_active = False  # IMU故障是否激活

        self.mag_noise_std = 0.0  # 磁力计噪声标准差
        self.mag_bias = [0.0, 0.0, 0.0]  # 磁力计偏置
        self.mag_fault_active = False  # 磁力计故障是否激活

        # 创建传感器发布者和订阅者
        self.imu_pub = self.create_publisher(Imu, '/rexrov/imu/data', 10)
        self.imu_sub = self.create_subscription(Imu, '/rexrov/imu/data_raw', self.imu_callback, 10)

        self.mag_pub = self.create_publisher(Vector3Stamped, '/rexrov/magnetometer', 10)
        self.mag_sub = self.create_subscription(Vector3Stamped, '/rexrov/magnetometer_raw', self.mag_callback, 10)

        print("✅ 交互式故障注入系统已启动")
        print("💡 等待服务连接...")
        time.sleep(3)

        # 检查服务连接状态
        ready = True
        for i in range(8):
            if not self.thruster_state_clients[i].wait_for_service(timeout_sec=1.0):
                print(f"⚠️  警告: 推进器{i}状态服务未就绪")
                ready = False
            if not self.thruster_eff_clients[i].wait_for_service(timeout_sec=1.0):
                print(f"⚠️  警告: 推进器{i}效率服务未就绪")
                ready = False

        # 检查洋流和外力服务
        if not self.current_client.wait_for_service(timeout_sec=1.0):
            print("⚠️  警告: 洋流干扰服务未就绪")
            ready = False
        if not self.wrench_client.wait_for_service(timeout_sec=1.0):
            print("⚠️  警告: 外力干扰服务未就绪")
            ready = False

        if ready:
            print("✅ 所有服务已就绪")
        else:
            print("⚠️  部分服务未就绪，某些功能可能不可用")

    def clear_all_faults(self):
        """清除所有故障，恢复正常状态"""
        print("🔧 正在清除所有故障...")

        # 停止传感器故障
        self.stop_sensor_faults()

        # 停止自定义环境故障
        self.stop_custom_faults()

        # 清除所有持续施加的外力
        print("   🔧 清除外力...")
        self.apply_direct_force([0, 0, 0], [0, 0, 0])

        from uuv_gazebo_ros_plugins_msgs.srv import SetThrusterEfficiency

        # 恢复所有推进器效率到100%
        for i in range(8):
            try:
                req_eff = SetThrusterEfficiency.Request()
                req_eff.efficiency = 1.0
                future_eff = self.thruster_eff_clients[i].call_async(req_eff)
                rclpy.spin_until_future_complete(self, future_eff, timeout_sec=0.5)

            except Exception as e:
                print(f"⚠️  恢复推进器{i}时出错: {e}")

        # 清除洋流干扰（设置为0）
        try:
            req_current = SetCurrentVelocity.Request()
            req_current.velocity = 0.0
            req_current.horizontal_angle = 0.0
            req_current.vertical_angle = 0.0
            future_current = self.current_client.call_async(req_current)
            rclpy.spin_until_future_complete(self, future_current, timeout_sec=2.0)

            if future_current.result() is not None:
                response = future_current.result()
                if response.success:
                    print("   ✓ 洋流干扰已清除")
                else:
                    print("   ⚠️  洋流清除失败（服务返回失败）")
            else:
                print("   ⚠️  洋流清除超时")
        except Exception as e:
            print(f"   ⚠️  清除洋流时出错: {e}")

        print("✅ 所有故障已清除")
        print("💡 航行器会靠水动力阻尼自然减速（可能需要较长时间）")
        print("💡 如需紧急制动，请使用选项17")

    def inject_single_thruster_fault(self, thruster_id):
        """单推进器故障 - 使用效率0%模拟完全失效"""
        print(f"⚠️  注入故障：推进器{thruster_id}效率降低至0%（完全失效）")

        from uuv_gazebo_ros_plugins_msgs.srv import SetThrusterEfficiency

        req = SetThrusterEfficiency.Request()
        req.efficiency = 0.0  # 效率设为0模拟完全失效

        future = self.thruster_eff_clients[thruster_id].call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)

        if future.result() is not None:
            print(f"✅ 推进器{thruster_id}故障注入成功（效率=0%）")
        else:
            print(f"❌ 推进器{thruster_id}故障注入失败")

    def inject_efficiency_fault(self, thruster_id, efficiency):
        """推进器效率故障"""
        print(f"⚠️  注入故障：推进器{thruster_id}效率降低至{efficiency*100:.0f}%")

        from uuv_gazebo_ros_plugins_msgs.srv import SetThrusterEfficiency

        req = SetThrusterEfficiency.Request()
        req.efficiency = efficiency

        future = self.thruster_eff_clients[thruster_id].call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)

        if future.result() is not None:
            print(f"✅ 推进器{thruster_id}效率设置成功")
        else:
            print(f"❌ 推进器{thruster_id}效率设置失败")

    def inject_multiple_thrusters_fault(self, thruster_ids):
        """多推进器故障 - 使用效率0%模拟完全失效"""
        print(f"⚠️  注入故障：推进器{thruster_ids}效率降低至0%（同时失效）")

        from uuv_gazebo_ros_plugins_msgs.srv import SetThrusterEfficiency

        for tid in thruster_ids:
            req = SetThrusterEfficiency.Request()
            req.efficiency = 0.0
            future = self.thruster_eff_clients[tid].call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)

        print(f"✅ 推进器{thruster_ids}故障注入成功（效率=0%）")

    def inject_current_disturbance(self, velocity, angle=0.0):
        """洋流干扰"""
        print(f"⚠️  注入故障：洋流干扰，速度={velocity}m/s, 角度={angle}rad")

        req = SetCurrentVelocity.Request()
        req.velocity = float(velocity)
        req.horizontal_angle = float(angle)
        req.vertical_angle = 0.0

        future = self.current_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)

        if future.result() is not None:
            response = future.result()
            if response.success:
                print("✅ 洋流干扰注入成功")
            else:
                print("❌ 洋流干扰注入失败（服务返回失败）")
        else:
            print("❌ 洋流干扰注入失败（超时或服务不可用）")

    def apply_direct_force(self, force, torque, duration_sec=-1):
        """
        直接对机器人本体施加外力（ApplyLinkWrench）

        Args:
            force: [fx, fy, fz] 力向量（牛顿）
            torque: [tx, ty, tz] 力矩向量（牛·米）
            duration_sec: 持续时间（秒），-1表示持续施加
        """
        if not self.wrench_client.wait_for_service(timeout_sec=0.5):
            print("❌ ApplyLinkWrench服务不可用")
            return False

        req = ApplyLinkWrench.Request()
        req.link_name = 'rexrov/base_link'
        req.reference_frame = 'world'
        req.reference_point.x = 0.0
        req.reference_point.y = 0.0
        req.reference_point.z = 0.0

        # 确保值为float类型
        req.wrench.force.x = float(force[0])
        req.wrench.force.y = float(force[1])
        req.wrench.force.z = float(force[2])
        req.wrench.torque.x = float(torque[0])
        req.wrench.torque.y = float(torque[1])
        req.wrench.torque.z = float(torque[2])

        # 设置时间
        req.start_time.sec = 0
        req.start_time.nanosec = 0
        req.duration.sec = int(duration_sec)
        req.duration.nanosec = 0

        try:
            future = self.wrench_client.call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)

            if future.result() is not None:
                response = future.result()
                if not response.success:
                    print(f"⚠️  施力失败: {response.status_message}")
                    return False
                return True
            else:
                print("⚠️  施力超时")
                return False
        except Exception as e:
            print(f"⚠️  施力异常: {e}")
            return False

    def inject_collision(self, direction, force=10000):
        """
        模拟碰撞 - 瞬间冲击力

        Args:
            direction: 'front', 'back', 'left', 'right', 'up', 'down'
            force: 碰撞力（牛顿）
        """
        direction_map = {
            'front': [1, 0, 0],    # 向前碰撞 → 向后的力
            'back': [-1, 0, 0],    # 向后碰撞 → 向前的力
            'left': [0, -1, 0],    # 向左碰撞 → 向右的力
            'right': [0, 1, 0],    # 向右碰撞 → 向左的力
            'up': [0, 0, -1],     # 向上碰撞 → 向下的力
            'down': [0, 0, 1]     # 向下碰撞 → 向上的力
        }

        if direction not in direction_map:
            print(f"❌ 未知方向: {direction}")
            return False

        vec = direction_map[direction]
        force_vec = [vec[0] * force, vec[1] * force, vec[2] * force]

        print(f"\n💥 模拟碰撞：{direction}方向，{force}N")

        # 1. 施加碰撞力（持续）
        print("   ⚡ 施加冲击力...")
        self.apply_direct_force(force_vec, [0, 0, 0], -1)

        # 2. 等待很短时间（冲击持续时间）
        time.sleep(0.1)

        # 3. 立即清除力
        print("   🛑 清除冲击力...")
        self.apply_direct_force([0, 0, 0], [0, 0, 0], -1)

        print("✅ 碰撞完成（航行器会因惯性继续移动）")
        return True

    def inject_wrench_disturbance(self, force, torque):
        """外力干扰"""
        print(f"⚠️  注入故障：外力干扰 F={force}, T={torque}")

        req = ApplyLinkWrench.Request()
        req.link_name = 'rexrov/base_link'  # ROS使用单斜杠
        req.reference_frame = 'world'  # 世界坐标系（修复：不能为空）
        req.reference_point.x = 0.0
        req.reference_point.y = 0.0
        req.reference_point.z = 0.0

        # 确保值为float类型
        req.wrench.force.x = float(force[0])
        req.wrench.force.y = float(force[1])
        req.wrench.force.z = float(force[2])
        req.wrench.torque.x = float(torque[0])
        req.wrench.torque.y = float(torque[1])
        req.wrench.torque.z = float(torque[2])

        # 设置时间
        req.start_time.sec = 0
        req.start_time.nanosec = 0
        req.duration.sec = -1  # 持续施加（-1表示一直施加）
        req.duration.nanosec = 0

        future = self.wrench_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)

        if future.result() is not None:
            response = future.result()
            if response.success:
                print("✅ 外力干扰注入成功")
            else:
                print(f"❌ 外力干扰注入失败: {response.status_message}")
        else:
            print("❌ 外力干扰注入失败（超时）")

    def inject_turbulence_fault(self, intensity, duration=None):
        """湍流干扰 - 直接对机器人本体施加随机扰动力"""
        fault_name = f"湍流({intensity})"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  故障 '{fault_name}' 已经在运行中")
            return

        if intensity == "low":
            magnitude = 300.0
        elif intensity == "medium":
            magnitude = 800.0
        else:  # high
            magnitude = 1500.0

        print(f"⚠️  注入故障：水下湍流干扰（强度：{intensity}）")
        print("   效果：直接对机器人本体施加随机扰动力")
        print("   ⭐ 故障将持续运行，直到手动停止")

        stop_flag = threading.Event()

        def turbulence_task():
            count = 0
            print(f"   🔧 湍流任务已启动，开始施加力...")
            while not stop_flag.is_set():
                # 随机扰动力（高斯分布）
                fx = random.gauss(0, magnitude)
                fy = random.gauss(0, magnitude)
                fz = random.gauss(0, magnitude * 0.3)  # 垂直方向较小

                # 直接施加力到机器人本体（持续施加）
                success = self.apply_direct_force([fx, fy, fz], [0, 0, 0])

                # 第一次施力时打印详细信息
                if count == 0:
                    print(f"   ✅ 首次施力: F=[{fx:.1f}, {fy:.1f}, {fz:.1f}] N")
                    print(f"   结果={'成功' if success else '失败'}, 服务状态={'就绪' if self.wrench_client.wait_for_service(timeout_sec=0.1) else '未就绪'}")
                    print(f"   💡 湍流持续运行中（不再输出状态信息）")

                count += 1
                time.sleep(0.1)

            # 故障结束，从列表中移除
            if fault_name in [f['name'] for f in self.active_faults]:
                self.active_faults = [f for f in self.active_faults if f['name'] != fault_name]

        thread = threading.Thread(target=turbulence_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'type': 'turbulence',
            'thread': thread,
            'stop': stop_flag
        })

        print("✅ 湍流干扰已启动（将持续运行）")

    def inject_magnetic_fault(self, intensity, duration=None):
        """磁场干扰 - 直接对机器人本体施加小幅随机扰动力"""
        fault_name = f"磁场({intensity})"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  故障 '{fault_name}' 已经在运行中")
            return

        if intensity == "low":
            magnitude = 50.0
        elif intensity == "medium":
            magnitude = 100.0
        else:  # high
            magnitude = 200.0

        print(f"⚠️  注入故障：磁场干扰（强度：{intensity}）")
        print("   效果：直接对机器人本体施加小幅随机扰动力")
        print("   ⭐ 故障将持续运行，直到手动停止")

        stop_flag = threading.Event()

        def magnetic_task():
            count = 0
            print(f"   🔧 磁场任务已启动，开始施加力...")
            while not stop_flag.is_set():
                # 磁场干扰产生小幅随机力
                fx = random.gauss(0, magnitude)
                fy = random.gauss(0, magnitude)
                fz = random.gauss(0, magnitude * 0.5)

                # 直接施加力到机器人本体（持续施加）
                self.apply_direct_force([fx, fy, fz], [0, 0, 0])

                # 第一次施力时打印详细信息
                if count == 0:
                    print(f"   ✅ 首次施力: F=[{fx:.1f}, {fy:.1f}, {fz:.1f}] N")
                    print(f"   💡 磁场干扰持续运行中（不再输出状态信息）")

                count += 1
                time.sleep(0.2)

            if fault_name in [f['name'] for f in self.active_faults]:
                self.active_faults = [f for f in self.active_faults if f['name'] != fault_name]

        thread = threading.Thread(target=magnetic_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'type': 'magnetic',
            'thread': thread,
            'stop': stop_flag
        })

        print("✅ 磁场干扰已启动（将持续运行）")

    def inject_pressure_fault(self, leak_depth, duration=None):
        """压力舱进水 - 直接对机器人本体施加向下的持续力"""
        fault_name = f"压力舱({leak_depth})"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  故障 '{fault_name}' 已经在运行中")
            return

        # 计算额外质量
        if leak_depth == "shallow":
            extra_mass_kg = 50
        elif leak_depth == "medium":
            extra_mass_kg = 250
        else:  # deep
            extra_mass_kg = 500

        # 额外重力 (N) - 向下
        extra_gravity = extra_mass_kg * 9.81

        print(f"⚠️  注入故障：压力舱进水（深度：{leak_depth}）")
        print(f"   额外质量：{extra_mass_kg}kg，向下重力：{extra_gravity:.1f}N")
        print("   效果：直接对机器人本体施加向下的持续力")
        print("   ⭐ 故障将持续运行，直到手动停止")

        stop_flag = threading.Event()

        def pressure_task():
            count = 0
            print(f"   🔧 压力舱任务已启动，开始施加向下力...")
            # 施加持续向下的力
            while not stop_flag.is_set():
                # 向下的持续力（+z方向向下）
                self.apply_direct_force([0, 0, extra_gravity], [0, 0, 0])

                # 第一次施力时打印详细信息
                if count == 0:
                    print(f"   ✅ 首次施力: 向下力 {extra_gravity:.1f}N")
                    print(f"   💡 压力舱进水持续运行中（不再输出状态信息）")

                count += 1
                time.sleep(0.5)

            if fault_name in [f['name'] for f in self.active_faults]:
                self.active_faults = [f for f in self.active_faults if f['name'] != fault_name]

        thread = threading.Thread(target=pressure_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'type': 'pressure',
            'thread': thread,
            'stop': stop_flag
        })

        print("✅ 压力舱进水已启动（将持续运行）")

    def inject_sensor_drift(self, drift_type, duration=None):
        """传感器漂移 - 直接对机器人本体施加恒定漂移力"""
        fault_name = f"漂移({drift_type})"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  故障 '{fault_name}' 已经在运行中")
            return

        print(f"⚠️  注入故障：传感器漂移（类型：{drift_type}）")
        print("   效果：直接对机器人本体施加恒定漂移力")
        print("   ⭐ 故障将持续运行，直到手动停止")

        # 确定漂移方向和大小
        if "forward" in drift_type:
            drift_force = [100.0, 0.0, 0.0]  # 向前漂移
            drift_desc = "向前"
        elif "lateral" in drift_type:
            drift_force = [0.0, 100.0, 0.0]  # 向右侧漂移
            drift_desc = "向右"
        else:
            drift_force = [0.0, 0.0, 50.0]  # 向下漂移
            drift_desc = "向下"

        stop_flag = threading.Event()

        def drift_task():
            count = 0
            print(f"   🔧 传感器漂移任务已启动，开始施加漂移力...")
            while not stop_flag.is_set():
                # 施加恒定漂移力
                self.apply_direct_force(drift_force, [0, 0, 0])

                # 第一次施力时打印详细信息
                if count == 0:
                    force_mag = sum(drift_force)
                    print(f"   ✅ 首次施力: 漂移力 [{drift_force[0]:.1f}, {drift_force[1]:.1f}, {drift_force[2]:.1f}] N")
                    print(f"   💡 传感器漂移持续运行中（不再输出状态信息）")

                count += 1
                time.sleep(0.5)

            if fault_name in [f['name'] for f in self.active_faults]:
                self.active_faults = [f for f in self.active_faults if f['name'] != fault_name]

        thread = threading.Thread(target=drift_task)
        thread.start()

        self.active_faults.append({
            'name': fault_name,
            'type': 'drift',
            'thread': thread,
            'stop': stop_flag
        })

        print("✅ 传感器漂移已启动（将持续运行）")

    def inject_temperature_fault(self, temp_change, duration=None):
        """水温变化 - 通过修改所有推进器效率模拟密度变化"""
        print(f"⚠️  注入故障：水温变化（变化：{temp_change}）")
        print("   效果：所有推进器效率降低，浮力改变")
        print("   ⭐ 故障将持续运行，直到手动清除")

        # 计算效率降低（温度升高导致密度降低）
        if "high" in temp_change:
            efficiency = 0.7  # 降低30%
        elif "low" in temp_change:
            efficiency = 0.9  # 降低10%
        else:
            efficiency = 0.8  # 降低20%

        print(f"   所有推进器效率降低到 {efficiency*100:.0f}%")

        from uuv_gazebo_ros_plugins_msgs.srv import SetThrusterEfficiency

        # 修改所有推进器效率
        for i in range(8):
            req = SetThrusterEfficiency.Request()
            req.efficiency = efficiency
            future = self.thruster_eff_clients[i].call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=0.5)

        print("✅ 水温变化已应用（使用选项0清除）")

    def imu_callback(self, msg):
        """处理IMU数据，注入噪声和偏置"""
        if not self.imu_fault_active:
            # 故障未激活，直接转发原始数据
            noisy_msg = msg
        else:
            # 创建新消息
            noisy_msg = Imu()
            noisy_msg.header = msg.header
            noisy_msg.orientation = msg.orientation
            noisy_msg.orientation_covariance = msg.orientation_covariance

            # 注入线加速度噪声和偏置
            noisy_msg.linear_acceleration.x = msg.linear_acceleration.x + \
                                               np.random.normal(0, self.imu_noise_std) + self.imu_bias[0]
            noisy_msg.linear_acceleration.y = msg.linear_acceleration.y + \
                                               np.random.normal(0, self.imu_noise_std) + self.imu_bias[1]
            noisy_msg.linear_acceleration.z = msg.linear_acceleration.z + \
                                               np.random.normal(0, self.imu_noise_std) + self.imu_bias[2]
            noisy_msg.linear_acceleration_covariance = msg.linear_acceleration_covariance

            # 注入角速度噪声
            noisy_msg.angular_velocity.x = msg.angular_velocity.x + \
                                            np.random.normal(0, self.imu_angular_noise)
            noisy_msg.angular_velocity.y = msg.angular_velocity.y + \
                                            np.random.normal(0, self.imu_angular_noise)
            noisy_msg.angular_velocity.z = msg.angular_velocity.z + \
                                            np.random.normal(0, self.imu_angular_noise)
            noisy_msg.angular_velocity_covariance = msg.angular_velocity_covariance

        # 发布（故障或原始数据）
        self.imu_pub.publish(noisy_msg)

    def mag_callback(self, msg):
        """处理磁力计数据，注入噪声和偏置"""
        if not self.mag_fault_active:
            # 故障未激活，直接转发原始数据
            noisy_msg = msg
        else:
            # 创建新消息
            noisy_msg = Vector3Stamped()
            noisy_msg.header = msg.header

            # 注入磁场噪声和偏置
            noisy_msg.vector.x = msg.vector.x + np.random.normal(0, self.mag_noise_std) + self.mag_bias[0]
            noisy_msg.vector.y = msg.vector.y + np.random.normal(0, self.mag_noise_std) + self.mag_bias[1]
            noisy_msg.vector.z = msg.vector.z + np.random.normal(0, self.mag_noise_std) + self.mag_bias[2]

        # 发布（故障或原始数据）
        self.mag_pub.publish(noisy_msg)

    def inject_imu_fault(self, intensity='low'):
        """IMU故障 - 添加噪声和偏置"""
        fault_name = f"IMU故障({intensity})"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  故障 '{fault_name}' 已经在运行中")
            return

        print(f"⚠️  注入故障：IMU噪声干扰（强度：{intensity}）")
        print("   效果：修改IMU传感器数据，添加噪声和偏置")
        print("   ⭐ 故障将持续运行，直到手动停止")

        if intensity == 'low':
            self.imu_noise_std = 0.005  # 轻微噪声（降低）
            self.imu_bias = [0.0, 0.0, 0.0]  # 无偏置（避免干扰控制）
            self.imu_angular_noise = 0.002  # 轻微角速度噪声（降低）
            print("   噪声水平：加速度 ±0.005 m/s²，角速度 ±0.002 rad/s")
            print("   💡 预期效果：轻微抖动，不影响下沉")
        elif intensity == 'medium':
            self.imu_noise_std = 0.01  # 中等噪声（降低）
            self.imu_bias = [0.0, 0.0, 0.0]  # 无偏置（避免干扰控制）
            self.imu_angular_noise = 0.005  # 中等角速度噪声（降低）
            print("   噪声水平：加速度 ±0.01 m/s²，角速度 ±0.005 rad/s")
            print("   💡 预期效果：明显抖动，仍可下沉")
        elif intensity == 'high':
            self.imu_noise_std = 0.03  # 严重噪声（降低）
            self.imu_bias = [0.0, 0.0, 0.0]  # 无偏置（避免干扰控制）
            self.imu_angular_noise = 0.02  # 严重角速度噪声（降低）
            print("   噪声水平：加速度 ±0.03 m/s²，角速度 ±0.02 rad/s")
            print("   💡 预期效果：严重抖动，可能影响控制")
        else:  # 自定义
            print("   ⚠️  未知强度，使用low级别")
            self.imu_noise_std = 0.005
            self.imu_bias = [0.0, 0.0, 0.0]
            self.imu_angular_noise = 0.002

        self.imu_fault_active = True

        self.active_faults.append({
            'name': fault_name,
            'type': 'imu',
            'stop': threading.Event()
        })

        print("✅ IMU噪声注入已启动（将持续运行）")
        print("💡 测试建议：在机器人导航时观察姿态抖动")

    def inject_magnetometer_fault(self, intensity='low'):
        """磁力计故障 - 添加偏置和噪声"""
        fault_name = f"磁力计故障({intensity})"

        if fault_name in [f['name'] for f in self.active_faults]:
            print(f"⚠️  故障 '{fault_name}' 已经在运行中")
            return

        print(f"⚠️  注入故障：磁力计干扰（强度：{intensity}）")
        print("   效果：修改磁力计传感器数据，添加噪声和偏置")
        print("   ⭐ 故障将持续运行，直到手动停止")

        if intensity == 'low':
            self.mag_noise_std = 0.1  # 轻微噪声
            self.mag_bias = [0.5, 0.5, 0.5]  # 轻微偏置（单位：μT）
            print("   噪声水平：±0.1 μT，偏置 0.5 μT")
        elif intensity == 'medium':
            self.mag_noise_std = 0.2  # 中等噪声
            self.mag_bias = [1.0, 1.0, 1.0]  # 中等偏置
            print("   噪声水平：±0.2 μT，偏置 1.0 μT")
        else:  # high
            self.mag_noise_std = 0.5  # 严重噪声
            self.mag_bias = [2.0, 2.0, 2.0]  # 严重偏置
            print("   噪声水平：±0.5 μT，偏置 2.0 μT")

        self.mag_fault_active = True

        self.active_faults.append({
            'name': fault_name,
            'type': 'magnetometer',
            'stop': threading.Event()
        })

        print("✅ 磁力计故障注入已启动（将持续运行）")
        print("💡 测试建议：在机器人导航时观察航向偏差")

    def stop_sensor_faults(self):
        """停止IMU和磁力计故障"""
        sensor_faults = [f for f in self.active_faults if f['type'] in ['imu', 'magnetometer']]

        if not sensor_faults:
            print("ℹ️  没有运行中的传感器故障")
            return

        print(f"🔧 正在停止 {len(sensor_faults)} 个传感器故障...")

        # 停止IMU故障
        if self.imu_fault_active:
            self.imu_fault_active = False
            self.imu_noise_std = 0.0
            self.imu_bias = [0.0, 0.0, 0.0]
            self.imu_angular_noise = 0.0
            print("   ✓ IMU故障已停止")

        # 停止磁力计故障
        if self.mag_fault_active:
            self.mag_fault_active = False
            self.mag_noise_std = 0.0
            self.mag_bias = [0.0, 0.0, 0.0]
            print("   ✓ 磁力计故障已停止")

        # 从活动故障列表中移除
        self.active_faults = [f for f in self.active_faults if f['type'] not in ['imu', 'magnetometer']]

        print("✅ 所有传感器故障已停止")

    def stop_custom_faults(self):
        """停止所有自定义环境故障（包括传感器故障）"""
        # 先停止传感器故障
        self.stop_sensor_faults()

        # 再停止环境故障
        env_faults = [f for f in self.active_faults if f['type'] not in ['imu', 'magnetometer']]

        if not env_faults:
            return

        print(f"🔧 正在停止 {len(env_faults)} 个环境故障...")
        for fault in env_faults:
            fault['stop'].set()

        # 等待所有线程结束
        for fault in env_faults:
            fault['thread'].join(timeout=1.0)

        # 移除环境故障
        self.active_faults = [f for f in self.active_faults if f['type'] in ['imu', 'magnetometer']]

        print("✅ 所有环境故障已停止")

    def show_active_faults(self):
        """显示当前活动的故障"""
        if not self.active_faults:
            print("ℹ️  当前没有运行中的环境故障")
        else:
            print(f"📊 当前活动的环境故障 ({len(self.active_faults)}个)：")
            for i, fault in enumerate(self.active_faults, 1):
                print(f"   {i}. {fault['name']}")

def print_menu():
    print("\n" + "="*70)
    print("🎯 交互式故障注入系统 - 完整版（支持故障组合）")
    print("="*70)
    print("【推进器故障】")
    print("0 - 清除所有故障（恢复正常）")
    print("1 - 推进器0完全失效")
    print("2 - 推进器1完全失效")
    print("3 - 推进器0和1同时失效")
    print("4 - 推进器0效率降低至30%")
    print("5 - 推进器0效率降低至10%")
    print("6 - 推进器2完全失效（中部推进器）")
    print("7 - 推进器6完全失效（垂直推进器）")
    print("\n【环境干扰故障（可组合，持续运行）】")
    print("10 - 水下湍流干扰 - 直接施加随机扰动力")
    print("11 - 磁场干扰 - 直接施加小幅随机力")
    print("12 - 压力舱进水 - 直接施加持续向下力")
    print("13 - 传感器漂移 - 直接施加恒定漂移力")
    print("14 - 水温变化")
    print("8 - 洋流干扰（1.5m/s侧向流）")
    print("\n【传感器故障（需要导航中测试，可组合）】")
    print("30 - IMU噪声干扰 - 修改加速度和角速度数据")
    print("31 - 磁力计干扰 - 修改磁场数据")
    print("\n【瞬间故障（碰撞）】")
    print("20 - 碰撞 - 前方")
    print("21 - 碰撞 - 后方")
    print("22 - 碰撞 - 左侧")
    print("23 - 碰撞 - 右侧")
    print("24 - 碰撞 - 上方")
    print("25 - 碰撞 - 下方")
    print("\n【其他】")
    print("15 - 查看当前活动故障")
    print("16 - 停止所有环境故障（保留推进器故障）")
    print("17 - 停止传感器故障（保留环境故障和推进器故障）")
    print("\n其他 - m显示菜单，q退出系统")
    print("="*70)
    print()

def main():
    rclpy.init()
    
    try:
        injector = InteractiveFaultInjector()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("💡 请确保:")
        print("   1. Gazebo和RexROV正在运行")
        print("   2. 推进器管理器已启动")
        print("   3. ROS 2环境已正确配置")
        rclpy.shutdown()
        return

    print_menu()
    print("💡 使用提示：")
    print("   - 在终端4按W键测试AUV响应")
    print("   - 在终端6观察故障效果")
    print("   - 环境故障（10-14）持续运行，不会自动停止")
    print("   - 环境故障直接对机器人本体施加物理力（非推进器模拟）")
    print("   - 传感器故障（30-31）需要机器人导航时才能观察效果")
    print("   - 碰撞故障（20-25）是瞬间冲击，施力后立即清除")
    print("   - 可以同时运行多个环境故障和传感器故障，实现故障组合")
    print("   - 推进器故障（1-7）也会和环境故障、传感器故障叠加")
    print("   - 使用选项15查看当前活动故障")
    print("   - 使用选项0清除所有故障，选项16只停止环境故障")
    print("   - 使用选项17只停止传感器故障")
    print()

    try:
        while rclpy.ok():
            try:
                cmd = input("请输入命令: ").strip()

                if not cmd:
                    continue

                if cmd.lower() == 'q':
                    print("👋 退出故障注入系统")
                    injector.clear_all_faults()
                    break

                if cmd.lower() == 'm':
                    print_menu()
                    continue

                choice = int(cmd)

                if choice == 0:
                    injector.clear_all_faults()
                    print("💡 现在可以按W键测试正常控制")

                elif choice == 1:
                    injector.inject_single_thruster_fault(0)
                    print("💡 现在可以按W键观察推进器0故障的影响")

                elif choice == 2:
                    injector.inject_single_thruster_fault(1)
                    print("💡 现在可以按W键观察推进器1故障的影响")

                elif choice == 3:
                    injector.inject_multiple_thrusters_fault([0, 1])
                    print("💡 现在可以按W键观察双推进器故障的影响")

                elif choice == 4:
                    injector.inject_efficiency_fault(0, 0.3)
                    print("💡 现在可以按W键观察效率降低的影响")

                elif choice == 5:
                    injector.inject_efficiency_fault(0, 0.1)
                    print("💡 现在可以按W键观察严重效率降低的影响")

                elif choice == 6:
                    injector.inject_single_thruster_fault(2)
                    print("💡 现在可以按W键观察中部推进器故障的影响")

                elif choice == 7:
                    injector.inject_single_thruster_fault(6)
                    print("💡 现在可以按W键观察垂直推进器故障的影响")

                elif choice == 8:
                    injector.inject_current_disturbance(1.5, 1.57)
                    print("💡 现在可以按W键观察洋流干扰的影响")

                elif choice == 9:
                    injector.inject_wrench_disturbance([2000, 1000, -500], [500, 200, 200])
                    print("💡 观察外力干扰的影响（会持续几秒钟）")

                elif choice == 10:
                    level = input("  选择湍流强度 (low/medium/high): ").strip()
                    injector.inject_turbulence_fault(level)

                elif choice == 11:
                    level = input("  选择磁场强度 (low/medium/high): ").strip()
                    injector.inject_magnetic_fault(level)

                elif choice == 12:
                    depth = input("  选择进水深度 (shallow/medium/deep): ").strip()
                    injector.inject_pressure_fault(depth)

                elif choice == 13:
                    drift = input("  选择漂移类型 (forward/lateral): ").strip()
                    injector.inject_sensor_drift(drift)

                elif choice == 14:
                    temp = input("  选择温度变化 (temp_high/temp_low): ").strip()
                    injector.inject_temperature_fault(temp)

                elif choice == 15:
                    injector.show_active_faults()

                elif choice == 16:
                    injector.stop_custom_faults()

                elif choice == 17:
                    injector.stop_sensor_faults()

                elif choice == 30:
                    level = input("  选择IMU噪声强度 (low/medium/high): ").strip()
                    injector.inject_imu_fault(level)

                elif choice == 31:
                    level = input("  选择磁力计干扰强度 (low/medium/high): ").strip()
                    injector.inject_magnetometer_fault(level)

                elif choice == 20:
                    injector.inject_collision('front', 10000)

                elif choice == 21:
                    injector.inject_collision('back', 10000)

                elif choice == 22:
                    injector.inject_collision('left', 10000)

                elif choice == 23:
                    injector.inject_collision('right', 10000)

                elif choice == 24:
                    injector.inject_collision('up', 8000)

                elif choice == 25:
                    injector.inject_collision('down', 12000)

                else:
                    print("❌ 无效命令，请输入0-31或q")

                print("\n等待下一个命令...")

            except ValueError:
                print("❌ 无效输入，请输入数字")
            except Exception as e:
                print(f"❌ 执行错误: {e}")

    except KeyboardInterrupt:
        print("\n👋 用户中断，正在退出...")
    finally:
        injector.clear_all_faults()
        injector.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
