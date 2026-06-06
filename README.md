# 🌊 极地水下装备环境适应性仿真平台

基于 **ROS 2 Humble + Gazebo 11** 的水下多装备仿真系统，在 [Plankton](https://github.com/Liquid-ai/Plankton)（UUV Simulator 的 ROS 2 移植版）基础上进行深度开发，集成了气泡动力学仿真、声学通信仿真、多装备探测识别跟踪、故障注入测试等功能，并面向极地环境迁移进行了物理模型和声学模型的重构。

> **原项目地址**：https://github.com/Liquid-ai/Plankton
> **参考项目**：https://github.com/Subhaaaash/Plankton | https://github.com/1mozon/Plankton

---

## ✨ 功能特性

| 模块 | 功能说明 |
|------|---------|
| **水动力学仿真** | 基于 Fossen 六自由度框架，支持 RexROV（盒式ROV，8推进器）和鱼雷形 AUV（200kg）等多种载具 |
| **气泡动力学仿真** | 物理建模气泡对载具的力学影响（阻力、浮力、漂移力、随机扰动）及光学效应（米氏散射、比尔-朗伯衰减、色移） |
| **声学通信仿真** | 集成声速计算（Mackenzie 1981）、吸收损失（Francois-Garrison）、多径效应、多普勒频移、信噪比评估 |
| **探测识别跟踪** | 声呐点云目标检测 → 尺寸/形状分类识别 → Alpha-Beta 滤波跟踪，完整闭环 |
| **故障注入系统** | 6 种推进器故障（完全失效、部分失效、卡死、反转、振荡、渐进退化），8 种预设测试场景 |
| **惯导仿真** | 九状态扩展卡尔曼滤波器，融合 IMU + DVL + 压力 + 磁力计 |
| **多装备协同** | 双 AUV 并行仿真，声学通信链路模拟，协同任务仿真 |
| **级联 PID 控制** | 三层控制架构（位置→速度→加速度），支持机体坐标系/世界坐标系切换 |
| **极地环境迁移** | 极地温盐深剖面建模、冰盖几何与粗糙度建模、冰下混响仿真、极地环境噪声建模 |

---

## 🖥️ 系统环境

| 项目 | 要求 |
|------|------|
| 操作系统 | Ubuntu 22.04（原生或 WSL2） |
| ROS 版本 | ROS 2 Humble |
| 仿真器 | Gazebo 11 Classic |
| Shell | zsh（或 bash） |
| Python | 3.10（系统自带，**避免 conda**） |
| 内存 | 编译时建议 16GB+，WSL2 需增加 swap |
| 硬盘 | 2GB+（编译后约 600MB） |

---

## 📦 安装部署

### 1. 安装 ROS 2 Humble

```bash
# 设置 UTF-8 locale
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# 添加 ROS 2 源
sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(source /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 安装桌面版
sudo apt update && sudo apt install -y ros-humble-desktop

# 安装开发工具
sudo apt install -y python3-colcon-common-extensions ros-dev-tools

# 配置环境
echo "source /opt/ros/humble/setup.bash" >> ~/.zshrc
source ~/.zshrc
```

### 2. 安装 Gazebo 11

```bash
sudo apt install -y gazebo11 libgazebo11-dev
sudo apt install -y ros-humble-gazebo-ros-pkgs
echo "source /usr/share/gazebo/setup.sh" >> ~/.zshrc
source ~/.zshrc
```

### 3. 获取源码并编译

```bash
# 创建工作空间
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src

# 克隆源码（二选一）
git clone https://github.com/<你的用户名>/underwater-auv-simulation.git .
# 或直接将本项目源码复制到 src/ 下

# 安装依赖
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y

# 编译（WSL2 建议单线程）
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release --parallel-workers 1

# 配置环境
echo "source \$HOME/ros2_ws/install/setup.bash" >> ~/.zshrc
source ~/.zshrc
```

### 4. WSL2 特别注意

- **增加 swap**：编译需要大量内存，建议增加 32GB swap
  ```bash
  sudo fallocate -l 32G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  ```
- **避免 conda**：conda 会劫持 Python 导致编译失败，执行 `conda deactivate` 并 `conda config --set auto_activate false`
- **渲染问题**：如 gzclient 崩溃，尝试 `export LIBGL_ALWAYS_SOFTWARE=1` 或 `export SVGA_VGPU10=0`

---

## 🚀 快速启动

### 完整任务仿真（一键启动）

```bash
ros2 launch underwater_mission_sim underwater_mission.launch.py
```

### 分步启动（推荐调试时使用）

**终端 1** — Gazebo 海洋环境：
```bash
source ~/.zshrc
ros2 launch uuv_gazebo_worlds ocean_waves.launch
```

**终端 2** — 部署 RexROV（等待 Gazebo 启动后）：
```bash
ros2 launch uuv_descriptions upload_rexrov_default.launch.py \
  mode:=default x:=0 y:=0 z:=-20 namespace:=rexrov gazebo_namespace:="''"
```

**终端 3** — PID 控制系统：
```bash
export RCUTILS_LOGGING_SEVERITY=ERROR

ros2 run uuv_control_cascaded_pid acceleration_control.py --ros-args \
  -r cmd_accel:=/rexrov/cmd_accel \
  -r thruster_manager/input:=/rexrov/thruster_manager/input \
  --params-file ~/ros2_ws/src/uuv_control/uuv_control_cascaded_pids/config/rexrov/inertial.yaml &

ros2 run uuv_control_cascaded_pid velocity_control.py --ros-args \
  -r cmd_vel:=/rexrov/cmd_vel -r odom:=/rexrov/pose_gt -r cmd_accel:=/rexrov/cmd_accel \
  --params-file ~/ros2_ws/vel_pid_body_frame.yaml &

ros2 launch uuv_thruster_manager thruster_manager.launch model_name:=rexrov uuv_name:=rexrov
```

**终端 4** — 键盘控制：
```bash
ros2 run uuv_teleop vehicle_keyboard_teleop --ros-args \
  -r output:=/rexrov/cmd_vel --log-level error
```

### 操控按键

| 按键 | 功能 | 按键 | 功能 |
|------|------|------|------|
| W / S | 前进 / 后退 | Q / E | 左转 / 右转 |
| A / D | 左移 / 右移 | I / K | 俯仰 |
| X / Z | 下潜 / 上浮 | J / L | 横滚 |
| 1 / 2 | 慢速 / 快速 | Ctrl+C | 退出 |

### 气泡仿真

```bash
ros2 launch underwater_bubble_sim ocean_bubbles.launch.py
```

### 故障注入

```bash
ros2 launch uuv_fault_injection fault_injection.launch.py
```

---

## 📁 项目结构

```
ros2_ws/
├── src/
│   ├── underwater_bubble_sim/        # 🔬 气泡动力学仿真（自研）
│   │   ├── scripts/
│   │   │   ├── bubble_generator.py       # 气泡可视化生成
│   │   │   ├── bubble_dynamics.py        # 气泡力学效应计算
│   │   │   └── bubble_image_processor.py # 光学效应后处理
│   │   ├── config/bubble_params.yaml
│   │   └── launch/ocean_bubbles.launch.py
│   │
│   ├── underwater_comm_sim/          # 📡 声学通信仿真（自研）
│   │   ├── scripts/
│   │   │   ├── acoustic_comm_simulator.py  # 声学通信链路仿真
│   │   │   ├── underwater_detector.py      # 声呐目标检测
│   │   │   ├── underwater_identifier.py    # 目标分类识别
│   │   │   └── underwater_tracker.py       # Alpha-Beta 跟踪
│   │   └── config/comm_params.yaml
│   │
│   ├── underwater_mission_sim/       # 🎯 任务级仿真（自研）
│   │   ├── launch/underwater_mission.launch.py
│   │   └── config/underwater_simulation_params.yaml
│   │
│   ├── uuv_fault_injection/          # ⚠️ 故障注入系统（自研）
│   │   ├── scripts/
│   │   │   ├── fault_injector.py          # 推进器故障注入
│   │   │   └── fault_monitor.py           # 实时监控仪表
│   │   └── config/fault_scenarios.yaml
│   │
│   ├── plankton/                     # 🔧 核心仿真框架
│   ├── uuv_gazebo_plugins/           #    Gazebo 水下物理插件（C++）
│   ├── uuv_sensor_plugins/           #    传感器仿真插件（IMU/DVL/声呐/相机等）
│   ├── uuv_world_plugins/            #    海洋洋流环境插件
│   ├── uuv_control/                  #    级联 PID + 轨迹控制
│   ├── uuv_descriptions/             #    机器人 URDF/xacro 模型
│   │   └── urdf/
│   │       ├── rexrov_base.xacro          # RexROV（1863kg，8推进器）
│   │       └── missile_auv_base.xacro     # 鱼雷形 AUV（200kg）
│   ├── uuv_gazebo_worlds/            #    仿真世界（海洋/湖泊/沉船等）
│   ├── uuv_thruster_manager/         #    推进器分配（TAM 矩阵）
│   ├── uuv_teleop/                   #    键盘/手柄遥控
│   └── eca_a9_plankton/              #    ECA A9 AUV 模型
│
├── fault_test/                       # 故障测试框架
├── docs/                             # 中文技术文档
├── tools/                            # 辅助工具
└── user_needs/                       # 需求分析文档
```

---

## 🎯 载具模型

### RexROV（默认）

- **类型**：盒式 ROV，基于 SF 30k
- **质量**：1862.87 kg
- **推进器**：8 个（4 个倾斜 + 4 个水平 45°）
- **传感器**：IMU、DVL、磁力计、压力、3 个相机、GPS、位姿真值
- **水动力**：Fossen 模型，完整 6×6 附加质量矩阵

### 鱼雷形 AUV（Missile AUV）

- **尺寸**：长 3m，直径 0.3m
- **质量**：200 kg
- **外形**：流线型圆柱体 + 头锥 + 尾翼 + 4 推进器
- **水动力**：强各向异性（低纵向附加质量，高横向阻尼）

---

## ⚠️ 已知问题与解决

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `uuv_assistants` 编译失败 | `btScalar`/`tf2` 与 Humble 不兼容 | 使用本项目已修正的代码 |
| Gazebo 时钟偏移警告 | 源码时间戳不一致 | `find src/ -exec touch {} +` |
| `gzclient` 渲染崩溃 | WSL2 显卡驱动兼容性 | `export LIBGL_ALWAYS_SOFTWARE=1` |
| `spawn_entity` 服务不可用 | 命名空间问题 | 添加参数 `gazebo_namespace:="''"` |
| 调头后控制方向漂移 | 默认使用世界坐标系 | 设置 `odom_vel_in_world: False` |
| 话题 QoS 不匹配 | Python 默认 QoS 无法订阅 Gazebo | 使用 `/cmd_vel` 替代直接订阅推进器话题 |
| conda 劫持 Python | catkin_pkg 等模块找不到 | `conda deactivate` + `conda config --set auto_activate false` |

---

## 📊 仿真节点与话题

### 关键话题

| 话题 | 类型 | 说明 |
|------|------|------|
| `/<ns>/pose_gt` | Odometry | 位姿真值 |
| `/<ns>/imu` | Imu | 惯性测量 |
| `/<ns>/dvl` | TwistWithCovarianceStamped | 多普勒计程仪 |
| `/<ns>/cmd_vel` | Twist | 速度指令 |
| `/<ns>/thruster_manager/input` | Wrench | 推进器力矩指令 |
| `/<ns>/camera*/image_raw` | Image | 相机图像 |
| `/<ns>/comm_tx` / `comm_rx` | String | 声学通信收发 |
| `/detection/results` | String(JSON) | 检测结果 |
| `/tracking/markers` | MarkerArray | 跟踪可视化 |

### 关键服务

| 服务 | 说明 |
|------|------|
| `/<ns>/set_fluid_density` | 动态修改海水密度 |
| `/hydrodynamics/set_current_velocity` | 设置洋流 |
| `/<ns>/thrusters/id_<n>/set_thrust_force_efficiency` | 设置推进器效率 |
| `/<ns>/go_to` | 导航至目标点 |
| `/apply_link_wrench` | 施加外力/力矩 |

---

## 📄 许可证

本项目基于 Plankton（UUV Simulator）开发，遵循原项目许可证。

---

## 🙏 致谢

- [Plankton](https://github.com/Liquid-ai/Plankton) — UUV Simulator 的 ROS 2 移植版
- [Subhaaaash/Plankton](https://github.com/Subhaaaash/Plankton) — Humble 开发分支参考
- [1mozon/Plankton](https://github.com/1mozon/Plankton) — 魔改版代码参考
