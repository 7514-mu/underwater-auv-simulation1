# 🧪 传感器故障测试指南

## 📡 传感器故障类型

本故障注入系统支持两种传感器故障：

### 1. IMU故障（选项30）
**故障描述**：修改IMU传感器数据，添加噪声和偏置

**影响**：
- 加速度数据噪声 → 机器人姿态估计抖动
- 角速度数据噪声 → 姿态角速度估计偏差
- 航行器路径不再平滑，出现抖动

**强度级别**：
- **low**：加速度噪声 ±0.01 m/s²，角速度噪声 ±0.005 rad/s
- **medium**：加速度噪声 ±0.05 m/s²，角速度噪声 ±0.02 rad/s
- **high**：加速度噪声 ±0.15 m/s²，角速度噪声 ±0.1 rad/s

### 2. 磁力计故障（选项31）
**故障描述**：修改磁力计传感器数据，添加噪声和偏置

**影响**：
- 磁场数据偏置 → 航向角估计偏差
- 机器人走直线会偏航
- 导航精度下降

**强度级别**：
- **low**：磁场噪声 ±0.1 μT，偏置 0.5 μT
- **medium**：磁场噪声 ±0.2 μT，偏置 1.0 μT
- **high**：磁场噪声 ±0.5 μT，偏置 2.0 μT

---

## 🚀 测试方法

### 方法1：使用交互式故障注入系统（推荐）

```bash
# 1. 启动海洋环境
终端1: ros2 launch uuv_gazebo_worlds ocean_waves.launch

# 2. 加载机器人
终端2: ros2 launch uuv_descriptions upload_rexrov_default.launch.py

# 3. 启动控制器
终端3: ros2 launch uuv_trajectory_control rov_nmb_sm_controller.launch uuv_name:=rexrov

# 4. 发送目标（开始导航）
终端4: python3 go_to_target.py 10 0 -20

# 5. 启动故障注入系统
终端5: python3 interactive_fault_injector_fixed.py

# 6. 在机器人移动过程中注入传感器故障
请输入命令: 30
  选择IMU噪声强度: medium

# 7. 观察机器人姿态抖动

# 8. 停止故障
请输入命令: 17
```

### 方法2：使用独立测试脚本

```bash
# 1-4 步同上

# 5. 启动传感器故障测试脚本
终端5: python3 test_sensor_faults.py

# 6. 选择测试类型
请选择测试类型：
1 - IMU故障（中等强度，10秒）
2 - 磁力计故障（中等强度，10秒）
3 - IMU+磁力计组合故障（中等强度，10秒）
4 - 自定义测试

请输入选项 (1-4): 1

# 7. 观察故障效果
```

---

## 🧪 测试场景

### 场景1：IMU噪声测试

**目的**：测试IMU噪声对姿态控制的影响

**步骤**：
1. 发送目标位置，启动导航
2. 注入IMU故障（medium强度）
3. 观察机器人姿态抖动
4. 对比正常情况和故障情况

**预期效果**：
- 姿态角出现高频抖动
- 路径不再平滑
- 控制器输出更频繁的调整

### 场景2：磁力计偏置测试

**目的**：测试磁力计偏置对航向控制的影响

**步骤**：
1. 发送目标位置，启动导航
2. 注入磁力计故障（medium强度）
3. 观察机器人航向偏差
4. 检查是否偏离预定轨迹

**预期效果**：
- 航向角出现恒定偏差
- 机器人走直线会偏航
- 导航精度下降

### 场景3：组合故障测试

**目的**：测试IMU和磁力计同时故障的影响

**步骤**：
1. 发送目标位置，启动导航
2. 同时注入IMU和磁力计故障
3. 观察组合故障效果

**预期效果**：
- 姿态抖动 + 航向偏差
- 导航误差显著增大
- 控制器性能下降

### 场景4：不同强度对比测试

**目的**：比较不同强度级别的故障影响

**步骤**：
1. 测试low强度 → 轻微抖动/偏差
2. 测试medium强度 → 明显抖动/偏差
3. 测试high强度 → 严重抖动/偏差

**预期效果**：
- 强度越高，故障效果越明显
- high强度可能导致控制器失稳

---

## 📊 数据分析

### 查看传感器数据

```bash
# 查看IMU数据
ros2 topic echo /rexrov/imu/data

# 查看磁力计数据
ros2 topic echo /rexrov/magnetometer

# 记录数据用于分析
ros2 bag record /rexrov/imu/data /rexrov/magnetometer
```

### 对比原始数据和带噪声数据

```bash
# 原始IMU数据（无故障时）
ros2 topic echo /rexrov/imu/data_raw

# 带噪声的IMU数据（故障注入后）
ros2 topic echo /rexrov/imu/data
```

---

## 🔧 故障参数调优

### IMU故障参数

| 参数 | low | medium | high |
|------|-----|--------|------|
| 加速度噪声 (m/s²) | 0.01 | 0.05 | 0.15 |
| 加速度偏置 (m/s²) | 0.01 | 0.05 | 0.10 |
| 角速度噪声 (rad/s) | 0.005 | 0.02 | 0.10 |

### 磁力计故障参数

| 参数 | low | medium | high |
|------|-----|--------|------|
| 磁场噪声 (μT) | 0.1 | 0.2 | 0.5 |
| 磁场偏置 (μT) | 0.5 | 1.0 | 2.0 |

**自定义参数**：
在 `test_sensor_faults.py` 中修改以下变量：
```python
self.imu_noise_std = 0.05      # IMU噪声标准差
self.imu_bias = [0.05, 0.05, 0.05]  # IMU偏置
self.imu_angular_noise = 0.02  # 角速度噪声

self.mag_noise_std = 0.2       # 磁力计噪声标准差
self.mag_bias = [1.0, 1.0, 1.0]   # 磁力计偏置
```

---

## 💡 测试建议

1. **导航中测试**：传感器故障必须在机器人导航时才能观察效果
2. **先单独测试**：先单独测试IMU或磁力计，再测试组合故障
3. **对比测试**：记录正常情况和故障情况的数据进行对比
4. **逐步增加强度**：从low开始，逐步增加到medium和high
5. **观察控制器响应**：观察控制器如何应对传感器故障
6. **记录数据**：使用ros2 bag记录数据用于后期分析

---

## ❓ 常见问题

### Q1: 为什么传感器故障没有效果？

A: 请确保：
- 机器人正在导航中（不是静止状态）
- 控制器正在运行
- 传感器话题正在发布数据
- 故障已成功激活（使用选项15查看）

### Q2: 如何判断故障是否注入成功？

A: 使用以下方法：
```bash
# 查看活动故障
选择选项: 15

# 查看传感器数据
ros2 topic echo /rexrov/imu/data

# 检查噪声注入节点
ros2 node list | grep sensor
```

### Q3: 能否修改传感器话题名称？

A: 可以。在 `interactive_fault_injector_fixed.py` 中修改：
```python
# 原始数据话题
self.imu_sub = self.create_subscription(Imu, '/rexrov/imu/data_raw', ...)

# 修改后的数据话题
self.imu_pub = self.create_publisher(Imu, '/rexrov/imu/data', ...)
```

### Q4: 如何自定义故障强度？

A: 使用方法2（独立测试脚本），选择选项4（自定义测试）

---

## 📚 相关文件

- **主脚本**: [interactive_fault_injector_fixed.py](interactive_fault_injector_fixed.py)
- **测试脚本**: [test_sensor_faults.py](test_sensor_faults.py)
- **导航脚本**: [go_to_target.py](go_to_target.py)
- **主文档**: [FAULT_INJECTOR_README.md](FAULT_INJECTOR_README.md)
