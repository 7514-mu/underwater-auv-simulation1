#!/usr/bin/env python3
"""
Underwater Bubble Generator Node

Spawns transparent sphere models in Gazebo to visualize underwater bubbles.
Physical bubble radius: 1~5mm (Clift 1978; 胡峻霖 2017)
Display radius = physical_radius × visual_scale (for Gazebo visibility)

Published topics:
  /bubble_sim/status (std_msgs/String)

Subscribed topics:
  /bubble_sim/cmd (std_msgs/String) - commands: "reset", "burst"

Parameters:
  pool_size (int) - number of visual bubble models (default: 15)
  min_radius (double) - minimum physical bubble radius (default: 0.001 m)
  max_radius (double) - maximum physical bubble radius (default: 0.005 m)
  visual_scale (double) - display magnification factor (default: 10.0)
  rise_speed (double) - bubble rise speed in m/s (default: 0.3)
  source_x/y/z (double) - bubble source center position
  source_range (double) - source spread range in meters (default: 5.0)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from gazebo_msgs.srv import SpawnEntity, SetEntityState
from gazebo_msgs.msg import EntityState
import random
import time


BUBBLE_SDF_TEMPLATE = """<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{name}">
    <static>true</static>
    <link name="link">
      <visual name="visual">
        <transparency>0.6</transparency>
        <geometry>
          <sphere><radius>{radius}</radius></sphere>
        </geometry>
        <material>
          <ambient>0.5 0.8 1.0 0.4</ambient>
          <diffuse>0.6 0.85 1.0 0.4</diffuse>
          <specular>0.9 0.95 1.0 1.0</specular>
        </material>
      </visual>
    </link>
  </model>
</sdf>"""


class BubbleGenerator(Node):
    def __init__(self):
        super().__init__('bubble_generator')

        self.declare_parameter('pool_size', 15)
        self.declare_parameter('min_radius', 0.001)
        self.declare_parameter('max_radius', 0.005)
        self.declare_parameter('visual_scale', 10.0)
        self.declare_parameter('rise_speed', 0.3)
        self.declare_parameter('source_x', 0.0)
        self.declare_parameter('source_y', 0.0)
        self.declare_parameter('source_z', -20.0)
        self.declare_parameter('source_range', 5.0)

        self.pool_size = self.get_parameter('pool_size').value
        self.min_radius = self.get_parameter('min_radius').value
        self.max_radius = self.get_parameter('max_radius').value
        self.visual_scale = self.get_parameter('visual_scale').value
        self.rise_speed = self.get_parameter('rise_speed').value
        self.source_x = self.get_parameter('source_x').value
        self.source_y = self.get_parameter('source_y').value
        self.source_z = self.get_parameter('source_z').value
        self.source_range = self.get_parameter('source_range').value

        self.status_pub = self.create_publisher(String, '/bubble_sim/status', 10)
        self.cmd_sub = self.create_subscription(
            String, '/bubble_sim/cmd', self.cmd_callback, 10)

        self.spawn_client = self.create_client(SpawnEntity, '/spawn_entity')
        self.set_state_client = self.create_client(SetEntityState, '/gazebo/set_entity_state')

        self.get_logger().info('Waiting for Gazebo services...')
        self.spawn_client.wait_for_service(timeout_sec=60.0)
        self.set_state_client.wait_for_service(timeout_sec=60.0)
        self.get_logger().info('Gazebo services ready')

        self.bubbles = []
        self.spawned_ok = set()  # track which bubbles actually spawned

        # Spawn pool synchronously (blocking, one by one)
        self.spawn_pool()

        # Only start update timer after all spawns attempted
        if self.spawned_ok:
            self.last_time = time.time()
            self.timer = self.create_timer(0.2, self.update)
            self.get_logger().info(
                f'Bubble generator running: {len(self.spawned_ok)}/{self.pool_size} bubbles, '
                f'source=({self.source_x},{self.source_y},{self.source_z})')
        else:
            self.get_logger().error('No bubbles spawned successfully, timer not started')

    def spawn_one(self, name, x, y, z, radius):
        """Spawn a single bubble model synchronously. Returns True on success."""
        sdf = BUBBLE_SDF_TEMPLATE.format(name=name, radius=radius)
        request = SpawnEntity.Request()
        request.name = name
        request.xml = sdf
        request.robot_namespace = ''
        request.initial_pose.position.x = x
        request.initial_pose.position.y = y
        request.initial_pose.position.z = z
        request.initial_pose.orientation.w = 1.0

        for attempt in range(3):
            future = self.spawn_client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
            result = future.result()
            if result is not None and result.success:
                return True
            self.get_logger().warn(
                f'Spawn {name} attempt {attempt+1} failed: '
                f'{result.status_message if result else "timeout"}')
            time.sleep(0.5)
        return False

    def spawn_pool(self):
        for i in range(self.pool_size):
            name = f'bubble_{i}'
            x = self.source_x + random.uniform(-self.source_range, self.source_range)
            y = self.source_y + random.uniform(-self.source_range, self.source_range)
            z = self.source_z + random.uniform(-2.0, 2.0)
            # Physical radius: 1~5mm, display radius = physical × visual_scale
            r_physical = random.uniform(self.min_radius, self.max_radius)
            r_display = r_physical * self.visual_scale

            ok = self.spawn_one(name, x, y, z, r_display)
            if ok:
                self.spawned_ok.add(i)
                if i == 0:
                    self.get_logger().info(
                        f'First bubble OK: pos=({x:.1f},{y:.1f},{z:.1f}), '
                        f'r={r_physical*1000:.1f}mm (display={r_display*1000:.0f}mm)')

            self.bubbles.append({
                'id': i,
                'name': name,
                'x': x, 'y': y, 'z': z,
                'base_z': z,
                'radius_physical': r_physical,
                'radius_display': r_display,
                'vx': random.uniform(-0.02, 0.02),
                'vy': random.uniform(-0.02, 0.02),
                'vz': self.rise_speed * random.uniform(0.7, 1.3),
            })

        self.get_logger().info(
            f'Spawn complete: {len(self.spawned_ok)}/{self.pool_size} successful')

    def recycle_bubble(self, b):
        b['x'] = self.source_x + random.uniform(-self.source_range, self.source_range)
        b['y'] = self.source_y + random.uniform(-self.source_range, self.source_range)
        b['z'] = self.source_z + random.uniform(-2.0, 2.0)
        b['vx'] = random.uniform(-0.02, 0.02)
        b['vy'] = random.uniform(-0.02, 0.02)
        b['vz'] = self.rise_speed * random.uniform(0.7, 1.3)

    def cmd_callback(self, msg):
        cmd = msg.data.lower()
        if cmd == 'reset':
            for b in self.bubbles:
                self.recycle_bubble(b)
            self.get_logger().info('All bubbles recycled')
        elif cmd == 'burst':
            for b in self.bubbles:
                b['x'] = self.source_x + random.uniform(-10, 10)
                b['y'] = self.source_y + random.uniform(-10, 10)
                b['z'] = self.source_z + random.uniform(-5, 5)
                b['vz'] = self.rise_speed * random.uniform(1.5, 3.0)
            self.get_logger().info('Burst mode')

    def update(self):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        for b in self.bubbles:
            if b['id'] not in self.spawned_ok:
                continue

            b['x'] += b['vx'] * dt
            b['y'] += b['vy'] * dt
            b['z'] += b['vz'] * dt

            b['vx'] += random.uniform(-0.08, 0.08) * dt
            b['vy'] += random.uniform(-0.08, 0.08) * dt

            if b['z'] >= -0.1:
                self.recycle_bubble(b)

            state = EntityState()
            state.name = b['name']
            state.pose.position.x = b['x']
            state.pose.position.y = b['y']
            state.pose.position.z = b['z']
            state.pose.orientation.w = 1.0
            state.reference_frame = 'world'

            self.set_state_client.call_async(
                SetEntityState.Request(state=state))

        status = String()
        status.data = f'active: {len(self.spawned_ok)}, rise: {self.rise_speed:.2f} m/s'
        self.status_pub.publish(status)


def main():
    rclpy.init()
    node = BubbleGenerator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
