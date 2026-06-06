# AUV Fault Injection System

## 概述 / Overview

故障注入系统，用于在水下机器人仿真环境中测试AUV的鲁棒性和容错能力。

A fault injection system for testing AUV robustness and fault tolerance in underwater robot simulation.

## 功能特性 / Features

### 6种故障类型 / 6 Fault Types

1. **完全失效 (COMPLETE FAILURE)** - 推进器完全停止
2. **部分失效 (PARTIAL FAILURE)** - 推进器效率降至50%
3. **推进器卡死 (STUCK THRUSTER)** - 推进器锁定在当前推力值
4. **推力反向 (REVERSE THRUST)** - 产生相反方向的推力
5. **推力振荡 (OSCILLATING)** - 随机推力波动
6. **渐进退化 (PROGRESSIVE)** - 推进器效率逐渐降低

## 安装 / Installation

```bash
cd ~/ros2_ws
colcon build --packages-select uuv_fault_injection
source ~/.zshrc
```

## 使用方法 / Usage

### 方法1: 启动故障注入器 / Method 1: Start Fault Injector

```bash
# 新终端启动故障注入系统
ros2 run uuv_fault_injection fault_injector
```

### 方法2: 使用Launch文件 / Method 2: Using Launch File

```bash
ros2 launch uuv_fault_injection fault_injection.launch.py namespace:=rexrov
```

## 故障注入命令 / Fault Injection Commands

```
fault_injector> inject <故障类型> <推进器索引> <持续时间秒>

示例 / Examples:
- inject 1 0 10          → 推进器0完全失效10秒
- inject 2 0,1,2 15      → 推进器0,1,2部分失效15秒
- inject 3 5 8           → 推进器5卡死8秒
- inject 4 6 10          → 推进器6推力反向10秒
- inject 5 3,7 12        → 推进器3,7振荡12秒
- inject 6 0,1,2,3,4,5 20 → 推进器0-5渐进退化20秒
```

### 其他命令 / Other Commands

```
clear      → 清除所有故障 / Clear all faults
status     → 查看故障状态 / Show fault status
menu       → 显示帮助菜单 / Show menu
```

## RexROV推进器索引 / RexROV Thruster Index

```
0,1: 前部推进器 (Surge前后)
2,3: 中部推进器 (Sway左右)
4,5: 后部推进器 (Surge前后)
6:   垂直推进器 (Heave上下)
7:   偏航推进器 (Yaw旋转)
```

## 测试场景 / Test Scenarios

配置文件包含8个预定义测试场景:

1. **单推进器失效** - 测试容错能力
2. **多推进器部分失效** - 测试降级运行
3. **推进器卡死** - 测试紧急处理
4. **推力反向** - 测试传感器融合
5. **推力振荡** - 测试控制稳定性
6. **渐进退化** - 测试预防性维护
7. **重大故障** - 测试紧急上浮
8. **深度控制失效** - 测试浮力控制

## 故障监控 / Fault Monitoring

```bash
# 启动性能监控器 (需要matplotlib)
ros2 run uuv_fault_injection fault_monitor
```

监控器显示:
- 实时位置 (X, Y, Z)
- 实时速度 (Vx, Vy, Vz)
- 故障对AUV性能的影响

## 应用场景 / Applications

### 师兄任务相关 / For Senior Brother's Task

1. **测试模型缺陷** - 注入故障发现AUV控制弱点
2. **最大化干扰** - 找到最关键的故障组合
3. **仿真到现实** - 将仿真结果应用到实际模型

### 研究方向 / Research Directions

- 故障诊断与识别 (Fault Diagnosis)
- 容错控制算法 (Fault-Tolerant Control)
- 强化学习 + 路径规划 (RL + Path Planning)
- 自主导航鲁棒性 (Autonomous Navigation Robustness)

## 故障注入示例 / Example Session

```bash
$ ros2 run uuv_fault_injection fault_injector

╔════════════════════════════════════════════════════════════╗
║           🔧 AUV FAULT INJECTION SYSTEM                     ║
╠════════════════════════════════════════════════════════════╣
║  Fault Types:                                               ║
║  1️⃣  COMPLETE FAILURE    - Selected thrusters stop        ║
║  2️⃣  PARTIAL FAILURE     - Reduced efficiency (50%)       ║
║  ...                                                        ║
╚════════════════════════════════════════════════════════════╝

fault_injector> inject 1 0 10
⚠️  FAULT INJECTED: COMPLETE FAILURE
📍 Affected Thrusters: [0]
⏱️  Duration: 10.0s

fault_injector> status
Fault Active: Type=1, Thrusters=[0], Remaining=7.5s

fault_injector> clear
✅ All faults cleared
```

## 技术细节 / Technical Details

### 故障注入原理 / Fault Injection Principle

系统订阅原始推进器命令，根据故障类型修改后重新发布:

```python
# 完全失效
msg.data = 0.0

# 部分失效
msg.data = original_cmd * 0.5

# 推力反向
msg.data = -original_cmd

# 推力振荡
msg.data = original_cmd + random(-0.3, 0.3)
```

### Topic结构 / Topic Structure

```
/rexrov/thrusters/id_0/input      ← 原始命令
FaultInjector ← 订阅并修改
FaultInjector → 发布修改后命令
ThrusterPlugin ← 接收故障命令
```

## 故障注入系统架构

```
┌─────────────────┐
│  Teleop/Controller │
└────────┬────────┘
         │ cmd_vel
         ↓
┌─────────────────┐
│ Thruster Manager│
└────────┬────────┘
         │ thrust commands
         ↓
┌─────────────────────┐ ← 故障注入点
│   FAULT INJECTOR    │
│  (modifies commands)│
└────────┬────────────┘
         │ faulty commands
         ↓
┌─────────────────┐
│  Thruster Plugin│
└────────┬────────┘
         │ force
         ↓
┌─────────────────┐
│     Gazebo      │
└─────────────────┘
```

## 文件结构 / File Structure

```
uuv_fault_injection/
├── package.xml
├── setup.py
├── config/
│   └── fault_scenarios.yaml      # 预定义故障场景
├── launch/
│   └── fault_injection.launch.py
├── uuv_fault_injection/
│   ├── __init__.py
│   └── scripts/
│       ├── fault_injector.py     # 主故障注入节点
│       └── fault_monitor.py      # 性能监控节点
└── README.md
```

## 后续工作 / Future Work

- [ ] 添加传感器故障注入 (IMU, DVL, 压力传感器)
- [ ] 实现故障诊断算法
- [ ] 集成强化学习控制器
- [ ] 添加故障预测功能
- [ ] 支持自定义故障曲线

## 参考 / References

- UUV Simulator: https://github.com/uuvsimulator/uuv_simulator
- Plankton: https://github.com/Subhaaaash/Plankton
- ROS 2 Humble Documentation

## License

Apache-2.0
