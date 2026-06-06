#!/usr/bin/env python3
"""Save one frame from a camera topic to a PNG file."""
import sys
import rclpy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

topic = sys.argv[1] if len(sys.argv) > 1 else '/rexrov/camera/camera_image'
outfile = sys.argv[2] if len(sys.argv) > 2 else '/home/wei1367/ros2_ws/camera_snapshot.png'

rclpy.init()
node = rclpy.create_node('image_saver')
bridge = CvBridge()
saved = False

def callback(msg):
    global saved
    if saved:
        return
    try:
        cv_img = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        import cv2
        cv2.imwrite(outfile, cv_img)
        print(f'Saved: {outfile} ({cv_img.shape[1]}x{cv_img.shape[0]})')
        saved = True
    except Exception as e:
        print(f'Error: {e}')

sub = node.create_subscription(Image, topic, callback, 10)
print(f'Waiting for image on {topic}...')
import time
timeout = 10.0
start = time.time()
while not saved and (time.time() - start) < timeout:
    rclpy.spin_once(node, timeout_sec=0.5)

if not saved:
    print(f'Timeout: no image received in {timeout}s')
node.destroy_node()
rclpy.shutdown()
