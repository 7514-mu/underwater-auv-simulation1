#!/usr/bin/env python3
"""
计算推进器分配矩阵（TAM）
根据rexrov_actuators.xacro中的推进器配置计算
"""

import numpy as np
from scipy.spatial.transform import Rotation

def compute_thrust_direction(rpy_degrees):
    """从RPY计算推力方向向量"""
    r = Rotation.from_euler('xyz', np.deg2rad(rpy_degrees))
    # 推进器推力沿自身Z轴正方向
    thrust_vector = r.apply([0, 0, 1])  
    return thrust_vector

def compute_tam_column(position, thrust_direction):
    """
    计算一个推进器对TAM的贡献（归一化）
    
    Args:
        position: [x, y, z] 推进器位置（米）
        thrust_direction: [dx, dy, dz] 推力方向（单位向量）
    
    Returns:
        TAM列: [fx, fy, fz, mx, my, mz]
    """
    position = np.array(position)
    direction = np.array(thrust_direction)
    
    # 力的贡献（单位推力）
    force = direction
    
    # 力矩的贡献：τ = r × F
    torque = np.cross(position, force)
    
    return np.concatenate([force, torque])

def print_tam_matrix(tam_matrix):
    """打印TAM矩阵"""
    print("\n" + "="*70)
    print("推进器分配矩阵 (TAM)")
    print("="*70)
    print("     T0      T1      T2      T3      T4      T5      T6      T7")
    
    labels = ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']
    for i, label in enumerate(labels):
        values = tam_matrix[i, :]
        print(f"{label} {[f'{v:7.3f}' for v in values]}")
    print("="*70)

def main():
    # 当前RexROV的8个推进器配置（从rexrov_actuators.xacro）
    thrusters = [
        # ID: (position, rpy)
        (0, [-0.890895, 0.334385, 0.528822], [0, -74.53, -53.21]),
        (1, [-0.890895, -0.334385, 0.528822], [0, -74.53, 53.21]),
        (2, [0.890895, 0.334385, 0.528822], [0, -105.47, 53.21]),
        (3, [0.890895, -0.334385, 0.528822], [0, -105.47, -53.21]),
        (4, [-0.412125, 0.505415, 0.129], [0, 0, 45]),
        (5, [-0.412125, -0.505415, 0.129], [0, 0, -45]),
        (6, [0.412125, 0.505415, 0.129], [0, 0, 135]),
        (7, [0.412125, -0.505415, 0.129], [0, 0, -135]),
    ]
    
    print("计算推进器分配矩阵...")
    print("每个推进器的配置：")
    print("ID\t位置\t\t\t\tRPY")
    for tid, pos, rpy in thrusters:
        print(f"{tid}\t{pos}\t{rpy}")
    
    # 计算TAM矩阵
    tam_columns = []
    for tid, pos, rpy in thrusters:
        direction = compute_thrust_direction(rpy)
        tam_col = compute_tam_column(pos, direction)
        tam_columns.append(tam_col)
        
        print(f"\n推进器{tid}:")
        print(f"  位置: {pos}")
        print(f"  RPY: {rpy}")
        print(f"  推力方向: {direction}")
        print(f"  TAM列: {tam_col}")
    
    # 组合成6×8矩阵
    tam_matrix = np.column_stack(tam_columns)
    
    print_tam_matrix(tam_matrix)
    
    # 保存到文件
    np.save('/home/wei1367/ros2_ws/tam_matrix.npy', tam_matrix)
    print("\n✅ TAM矩阵已保存到: ~/ros2_ws/tam_matrix.npy")

if __name__ == '__main__':
    main()
