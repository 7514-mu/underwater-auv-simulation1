#!/usr/bin/env python3
"""
计算10推进器RexROV的推进器分配矩阵（TAM）
"""
import numpy as np
from scipy.spatial.transform import Rotation

def compute_tam_column(position, rpy_degrees):
    """计算单个推进器对TAM的贡献"""
    # 计算推力方向
    rot = Rotation.from_euler('xyz', np.deg2rad(rpy_degrees))
    thrust_direction = rot.apply([0, 0, 1])
    
    # 力的贡献（归一化）
    force = thrust_direction
    
    # 力矩的贡献：tau = r × F
    position = np.array(position)
    torque = np.cross(position, force)
    
    # 组合：[fx, fy, fz, mx, my, mz]
    tam_column = np.concatenate([force, torque])
    
    return tam_column

def print_tam_matrix(tam_matrix, thruster_count):
    """打印TAM矩阵"""
    print("\n" + "="*80)
    print(f"推进器分配矩阵 (TAM) - {thruster_count}推进器")
    print("="*80)
    
    # 推进器编号
    headers = [f"T{i}" for i in range(thruster_count)]
    header_str = "     " + "  ".join([f"{h:>6}" for h in headers])
    print(header_str)
    
    labels = ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']
    for i, label in enumerate(labels):
        values = tam_matrix[i, :]
        values_str = "  ".join([f"{v:6.3f}" for v in values])
        print(f"{label} [{values_str}]")
    
    print("="*80)

def main():
    # 10推进器配置（修正后）
    print("计算10推进器RexROV的TAM...")
    
    thrusters = [
        # (ID, 位置[x,y,z], RPY[roll,pitch,yaw])
        (0, [-0.890895, 0.334385, 0.528822], [0, -74.53, -53.21]),
        (1, [-0.890895, -0.334385, 0.528822], [0, -74.53, 53.21]),
        (2, [0.890895, 0.334385, 0.528822], [0, -105.47, 53.21]),
        (3, [0.890895, -0.334385, 0.528822], [0, -105.47, -53.21]),
        (4, [-0.412125, 0.505415, 0.129], [0, 0, 45]),
        (5, [-0.412125, -0.505415, 0.129], [0, 0, -45]),
        (6, [0.412125, 0.505415, 0.129], [0, 0, 135]),
        (7, [0.412125, -0.505415, 0.129], [0, 0, -135]),
        # 新增推进器（修正后）
        (8, [0.5, 0.0, 0.0], [0, -90, 0]),            # 前方，前进
        (9, [0.0, 0.6, 0.0], [-90, -90, 0]),         # 右侧，侧向
    ]
    
    print("\n推进器配置：")
    print("ID\t位置\t\t\tRPY\t\t\t功能")
    for tid, pos, rpy in thrusters:
        if tid < 8:
            func = "原始推进器"
        else:
            func = "新增推进器"
        print(f"{tid}\t{pos}\t{rpy}\t{func}")
    
    # 计算所有TAM列
    tam_columns = []
    for tid, pos, rpy in thrusters:
        tam_col = compute_tam_column(pos, rpy)
        tam_columns.append(tam_col)
        
        if tid >= 8:  # 打印新增推进器的详细信息
            print(f"\n推进器{tid}:")
            print(f"  位置: {pos}")
            print(f"  RPY: {rpy}")
            print(f"  TAM列: {tam_col}")
    
    # 组合成6×10矩阵
    tam_matrix = np.column_stack(tam_columns)
    
    # 打印完整TAM
    print_tam_matrix(tam_matrix, 10)
    
    # 保存到文件
    np.save('/home/wei1367/ros2_ws/tam_matrix_10thrusters.npy', tam_matrix)
    print("\n✅ TAM矩阵已保存到: ~/ros2_ws/tam_matrix_10thrusters.npy")
    
    # 保存为文本格式
    np.savetxt('/home/wei1367/ros2_ws/tam_matrix_10thrusters.txt', tam_matrix, fmt='%.6f', delimiter=', ')
    print("✅ TAM矩阵已保存到: ~/ros2_ws/tam_matrix_10thrusters.txt")
    
    # 生成Python代码格式的TAM
    print("\n" + "="*80)
    print("Python代码格式的TAM（可直接用于配置）")
    print("="*80)
    print("import numpy as np")
    print("tam_10thrusters = np.array([")
    for i in range(6):
        row_str = ", ".join([f"{tam_matrix[i,j]:.3f}" for j in range(10)])
        print(f"    [{row_str}],")
    print("])")

if __name__ == '__main__':
    main()
