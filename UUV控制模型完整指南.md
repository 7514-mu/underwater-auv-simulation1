# UUV Simulator 支持的所有控制模型

## 📋 控制器总览

### 1. **PID控制器族** (你已使用)

| 控制器 | 文件 | 特点 | 应用场景 |
|--------|------|------|---------|
| **级联PID** | `rov_pid_controller.launch` | 三层：位置→速度→加速度 | ✅ 你正在使用 |
| **非线性PID** | `rov_nl_pid_controller.launch` | 带Hm项，抗干扰能力强 | 复杂环境 |
| **欠驱动PID** | `rov_ua_pid_controller.launch` | 针对欠驱动AUV | 部分推进器失效 |

**PID参数对比：**
```yaml
# 标准PID (你使用的)
Kp: [11993, 11993, 11993, 19460, 19460, 19460]
Kd: [9077, 9077, 9077, 18880, 18880, 18880]
Ki: [321, 321, 321, 2096, 2096, 2096]

# 非线性PID
Kp: [500, 500, 500, 300, 300, 300]
Kd: [50, 50, 50, 20, 20, 20]
Ki: [200, 200, 200, 100, 100, 100]
Hm: [50, 50, 50, 40, 40, 40]  # 非线性项
```

---

### 2. **滑模控制器** (Sliding Mode) ⭐ 高级

**文件：** `rov_sf_controller.launch`

**特点：**
- ✅ 强鲁棒性（对参数变化不敏感）
- ✅ 抗干扰能力强
- ✅ 适合故障情况下的控制
- ⚠️ 控制输入可能有抖动

**参数：**
```yaml
Kd: [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
lambda: 1.0  # 滑模面斜率
c: 1.0       # 边界层厚度
saturation: 5000  # 推力饱和
```

**适用场景：**
- 洋流干扰环境
- 推进器故障情况
- 参数不确定情况

---

### 3. **基于模型的控制器** (Model-Based)

| 控制器 | 文件 | 特点 |
|--------|------|------|
| **全速MB控制器** | `rov_mb_fl_controller.launch` | 快速响应，精确模型 |
| **慢速MB控制器** | `rov_mb_sm_controller.launch` | 节能，稳定 |

**特点：**
- ✅ 使用AUV动力学模型
- ✅ 控制精度高
- ⚠️ 依赖精确的模型参数
- ⚠️ 计算量大

**要求：**
- 精确的质量矩阵
- 水动力系数
- 附加质量矩阵

---

### 4. **非基于模型控制器** (Non-Model-Based)

**文件：** `rov_nmb_sm_controller.launch`

**特点：**
- ✅ 不需要精确模型
- ✅ 自适应能力强
- ⚠️ 控制精度较低

---

### 5. **PD+重力补偿**

**文件：** `rov_pd_grav_compensation_controller.launch`

**特点：**
- ✅ 自动补偿浮力/重力
- ✅ 垂直方向控制好
- ✅ 适合定深控制

**应用：**
- 深度保持
- 悬停作业
- 垂直面移动

---

### 6. **几何跟踪控制器** (Geometric Tracking)

**文件：** `auv_geometric_tracking_controller.launch`

**特点：**
- ✅ 适用于AUV（非ROV）
- ✅ 轨迹跟踪精度高
- ✅ 适用于长距离导航

**与ROV区别：**
- AUV：自主航行，流线型
- ROV：系缆作业，Box形状

---

## 🚀 启动不同控制器

### 方法1：使用官方Launch文件

**PID控制器（你正在使用）：**
```bash
ros2 launch uuv_trajectory_control rov_pid_controller.launch \
  uuv_name:=rexrov \
  model_name:=rexrov
```

**滑模控制器（推荐故障场景）：**
```bash
ros2 launch uuv_trajectory_control rov_sf_controller.launch \
  uuv_name:=rexrov \
  model_name:=rexrov
```

**非线性PID（推荐复杂环境）：**
```bash
ros2 launch uuv_trajectory_control rov_nl_pid_controller.launch \
  uuv_name:=rexrov \
  model_name:=rexrov
```

---

### 方法2：直接运行控制节点

**加速度控制（底层）：**
```bash
ros2 run uuv_control_cascaded_pid acceleration_control.py \
  --ros-args \
  -r cmd_accel:=/rexrov/cmd_accel \
  -r thruster_manager/input:=/rexrov/thruster_manager/input \
  --params-file ~/ros2_ws/src/uuv_control/uuv_control_cascaded_pids/config/rexrov/inertial.yaml
```

**速度控制（中层）：**
```bash
ros2 run uuv_control_cascaded_pid velocity_control.py \
  --ros-args \
  -r cmd_vel:=/rexrov/cmd_vel \
  -r odom:=/rexrov/pose_gt \
  -r cmd_accel:=/rexrov/cmd_accel \
  --params-file ~/ros2_ws/vel_pid_body_frame.yaml
```

**位置控制（高层）：**
```bash
ros2 run uuv_control_cascaded_pid position_control.py \
  --ros-args \
  -r cmd_pose:=/rexrov/cmd_pose \
  -r odom:=/rexrov/pose_gt \
  -r cmd_vel:=/rexrov/cmd_vel
```

---

## 📊 控制器性能对比

### 正常环境性能

| 控制器 | 响应速度 | 控制精度 | 稳定性 | 计算量 |
|--------|---------|---------|--------|--------|
| 级联PID | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| 非线性PID | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| 滑模控制 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Model-Based | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 故障环境性能

| 控制器 | 单推进器失效 | 洋流干扰 | 参数不确定 |
|--------|-------------|---------|-----------|
| 级联PID | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| 非线性PID | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 滑模控制 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Model-Based | ⭐⭐ | ⭐⭐ | ⭐ |

---

## 🎯 推荐使用场景

### 场景1：正常作业（推荐级联PID）
```bash
# 你当前的配置就是最佳选择
✅ 级联PID + 键盘控制
✅ 稳定可靠，易于调试
```

### 场景2：故障注入测试（推荐滑模控制）
```bash
# 滑模控制的鲁棒性强，适合故障场景
ros2 launch uuv_trajectory_control rov_sf_controller.launch \
  uuv_name:=rexrov model_name:=rexrov

# 测试推进器故障时的性能对比
```

### 场景3：洋流干扰环境（推荐非线性PID）
```bash
# 非线性PID抗干扰能力强
ros2 launch uuv_trajectory_control rov_nl_pid_controller.launch \
  uuv_name:=rexrov model_name:=rexrov

# 配合洋流干扰测试
```

### 场景4：轨迹跟踪（推荐几何跟踪）
```bash
# 长距离、高精度轨迹跟踪
ros2 launch uuv_trajectory_control auv_geometric_tracking_controller.launch \
  uuv_name:=rexrov model_name:=rexrov
```

---

## 💡 研究建议

### 本科毕业设计
**使用级联PID即可**（你当前的配置）
- ✅ 已验证可行
- ✅ 文档完整
- ✅ 易于解释

### 硕士论文
**对比2-3种控制器**
```python
控制器对比实验：
1. 级联PID（基准）
2. 滑模控制（鲁棒性）
3. 非线性PID（抗干扰）

实验条件：
- 正常状态
- T0失效（0%）
- 洋流干扰1.5m/s
- T0失效 + 洋流

评估指标：
- 轨迹跟踪误差
- 控制能耗
- 稳定时间
```

### 科研论文
**提出新的容错控制策略**
```python
创新方向：
1. 故障检测 + 控制器切换
2. 自适应PID参数调整
3. 多控制器融合（级联+滑模）
4. 深度学习辅助控制

验证方法：
- 在UUV Simulator上测试
- 对比现有控制器
- 鲁棒性验证
```

---

## 📁 配置文件位置

**PID配置：**
```
~/ros2_ws/src/uuv_control/uuv_trajectory_control/config/controllers/
├── pid/rexrov/params.yaml           # 标准PID
├── nl_pid/rexrov/params.yaml        # 非线性PID
└── models/rexrov/params.yaml        # 模型参数
```

**Launch文件：**
```
~/ros2_ws/src/uuv_control/uuv_trajectory_control/launch/
├── rov_pid_controller.launch        # PID控制器
├── rov_sf_controller.launch         # 滑模控制
├── rov_nl_pid_controller.launch     # 非线性PID
└── auv_geometric_tracking_controller.launch  # 几何跟踪
```

---

## 🎓 总结

**你当前的配置（级联PID）是很好的选择：**
- ✅ 适合基础研究
- ✅ 稳定可靠
- ✅ 易于理解

**如需进阶研究，可以：**
1. 对比PID vs 滑模控制在故障下的表现
2. 研究控制器参数自适应调整
3. 提出新的容错控制策略
4. 集成多种控制器的混合方案

**需要我帮你测试某个控制器吗？**
