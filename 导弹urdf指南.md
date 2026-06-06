# 导弹形AUV替换RexROV完整指南

## 概述

将 UUV Simulator 中默认的 RexROV（箱形ROV）替换为导弹/鱼雷形 AUV，包括模型定义、推进器配置、水动力参数、传感器、PID控制等全部步骤。

---

## 1. 文件结构

```
src/uuv_descriptions/
├── robots/
│   └── missile_auv.xacro              # 顶层模型（水动力+插件）
├── urdf/
│   ├── missile_auv_base.xacro         # 基础模型（几何/惯性）
│   ├── missile_auv_actuators.xacro    # 推进器配置
│   └── missile_auv_sensors.xacro      # 传感器配置
├── launch/
│   └── upload_missile_auv.launch.py   # Spawn启动文件
└── meshes/
    └── prop.dae                       # 螺旋桨网格（复用RexROV）

src/uuv_control/
├── uuv_thruster_manager/config/missile_auv/
│   ├── thruster_manager.yaml          # 推进器管理器配置
│   └── TAM.yaml                       # 推进器分配矩阵
└── uuv_control_cascaded_pids/config/missile_auv/
    ├── inertial.yaml                  # 惯性参数
    └── vel_pid_control.yaml           # 速度PID参数

start_missile_pid.sh                   # PID控制启动脚本
```

---

## 2. 模型定义

### 2.1 基础模型 (`missile_auv_base.xacro`)

关键参数：
- **长度**: 3.0m，**直径**: 0.3m
- **质量**: 200kg
- **惯性**: Ixx=1.5（滚转小），Iyy=Izz=15（俯仰/偏航大）
- **几何**: 圆柱体沿X轴，前端加鼻锥（小圆柱+球体），后端尾锥
- **CG**: 位于 base_link 原点 (0,0,0)

```xml
<xacro:property name="length" value="3.0"/>
<xacro:property name="diameter" value="0.3"/>
<xacro:property name="mass" value="200.0"/>
```

**注意事项：**
- URDF 不支持 `<cone>` 几何，用圆柱+球体替代
- 圆柱体需用 `rpy="0 1.5708 0"` 旋转使其沿X轴
- `*gazebo` 块从顶层传入（不在base里直接写插件）

### 2.2 顶层模型 (`missile_auv.xacro`)

顶层负责：
1. 定义水动力模型宏（**必须在实例化base之前定义**）
2. 实例化 `missile_auv_base`，传入 Gazebo 插件块
3. 加载 `libuuv_underwater_object_ros_plugin.so` 水动力插件

```xml
<!-- 水动力模型宏（先定义） -->
<xacro:macro name="missile_auv_hydro_model" params="namespace">
  <link name="${namespace}/base_link">
    <!-- 参数必须放在 <link> 子元素内，不能直接放在 <plugin> 下 -->
    <neutrally_buoyant>0</neutrally_buoyant>
    <volume>0.195</volume>
    <center_of_buoyancy>0.0 0.0 0.08</center_of_buoyancy>
    <hydrodynamic_model>
      <type>fossen</type>
      <added_mass>...</added_mass>
      <linear_damping>...</linear_damping>
      <quadratic_damping>...</quadratic_damping>
    </hydrodynamic_model>
  </link>
</xacro:macro>

<!-- 然后实例化 -->
<xacro:missile_auv_base namespace="..." ...>
  <gazebo>
    <plugin name="..." filename="libuuv_underwater_object_ros_plugin.so">
      <xacro:missile_auv_hydro_model namespace="..."/>
    </plugin>
  </gazebo>
</xacro:missile_auv_base>
```

#### 关键踩坑点：

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 模型掉落不浮 | 水动力参数直接放在 `<plugin>` 下 | 必须放在 `<link name="...">` 子元素内 |
| 宏未定义错误 | `missile_auv_hydro_model` 在使用后才定义 | 宏定义必须在使用之前 |
| CG/CB间距太小导致翻滚 | CoB 的 z=0.02 太小 | 改为 z=0.08，恢复力矩增大4倍 |

#### 水动力参数选择：

```
体积: V = π * r² * L = π * 0.15² * 3.0 ≈ 0.195 m³
浮力: F_b = V * ρ * g = 0.195 * 1028 * 9.81 ≈ 1966 N
重力: F_g = m * g = 200 * 9.81 = 1962 N
净浮力: ≈ 4N 正浮力（失效时自动上浮）
```

附加质量矩阵（鱼雷形：X小、Y/Z大）：
```
       X    Y    Z    K    M    N
X:    25    0    0    0    0    0    ← 流线型，X轴附加质量小
Y:     0  150    0    0    0    0    ← 横截面大
Z:     0    0  150    0    0    0    ← 横截面大
K:     0    0    0   10    0    0    ← 滚转惯量小
M:     0    0    0    0   35    0    ← 俯仰惯量
N:     0    0    0    0    0   35    ← 偏航惯量
```

阻尼参数（需要足够大才能稳定）：
```
线性阻尼:   -20   -80   -80   -10   -30   -30
二次阻尼:   -80  -300  -300   -30  -100  -100
```

---

## 3. 推进器配置

### 3.1 布局 (`missile_auv_actuators.xacro`)

5个推进器：

```
        鼻锥 →  ○─────────────────○  ← 尾部
                │     鱼雷体       │
           T1↑ T3→            T3→ T1↑
           (z) (y)     T0→    (y) (z)
                          (x)
                │                 │
           T2↑ T4→            T4→ T2↑
```

| 推进器 | 位置 | RPY | 推力方向 | 功能 |
|--------|------|-----|----------|------|
| T0 (主推) | x=-1.4 | (0,0,0) | +X | 前进/后退 |
| T1 (前垂) | x=0.8 | (0,-π/2,0) | +Z | 升沉/俯仰 |
| T2 (后垂) | x=-0.8 | (0,-π/2,0) | +Z | 升沉/俯仰 |
| T3 (前侧) | x=0.8 | (0,0,π/2) | +Y | 横移/偏航 |
| T4 (后侧) | x=-0.8 | (0,0,π/2) | +Y | 横移/偏航 |

#### RPY 推力方向推导：

```
推进器宏的关节轴默认是子坐标系 X 轴 [1,0,0]
需要通过 RPY 旋转将其映射到父坐标系的目标方向：

目标 +Z: Ry(-π/2) 将子X → 父+Z ✓
  注意: Ry(+π/2) 将子X → 父-Z ✗（方向反了）

目标 +Y: Rz(+π/2) 将子X → 父+Y ✓
```

#### 使用标准 UUV 宏：

```xml
<xacro:macro name="missile_thruster_macro"
  params="namespace thruster_id *origin">
  <xacro:thruster_module_first_order_basic_fcn_macro
    namespace="${namespace}"
    thruster_id="${thruster_id}"
    mesh_filename="${prop_mesh_file}"
    dyn_time_constant="0.05"
    rotor_constant="0.01">
    <xacro:insert_block name="origin"/>
  </xacro:thruster_module_first_order_basic_fcn_macro>
</xacro:macro>
```

**关键：必须使用标准 UUV 宏**（如 `thruster_module_first_order_basic_fcn_macro`），否则推进器管理器无法识别。使用正确的插件：`libuuv_thruster_ros_plugin.so`（不是 `libuuv_gazebo_thruster_plugin.so`）。

---

## 4. 推进器分配矩阵 (TAM)

### 4.1 TAM 矩阵 (`TAM.yaml`)

```
         T0     T1     T2     T3     T4
X:      1.0    0.0    0.0    0.0    0.0    ← 只有主推
Y:      0.0    0.0    0.0    1.0    1.0    ← 两个侧推
Z:      0.0    1.0    1.0    0.0    0.0    ← 两个垂推
Roll:   0.0    0.0    0.0    0.0    0.0    ← 无法主动控制
Pitch:  0.0   -0.8    0.8    0.0    0.0    ← 垂推差动（力臂=0.8m）
Yaw:    0.0    0.0    0.0    0.8   -0.8    ← 侧推差动（力臂=0.8m）
```

### 4.2 TAM.yaml 格式要求（重要！）

```yaml
# ✅ 正确：单行数组
/**:
  ros__parameters:
    tam: [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, ...]

# ❌ 错误：多行数组会导致 ROS2 参数解析崩溃！
/**:
  ros__parameters:
    tam: [1.0, 0.0, 0.0, 0.0, 0.0,
          0.0, 0.0, 0.0, 1.0, 1.0, ...]
```

多行数组格式会导致 `thruster_allocator` 启动时崩溃，且错误被重定向到 `/dev/null` 很难发现。

### 4.3 推进器管理器配置 (`thruster_manager.yaml`)

```yaml
/**:
  ros__parameters:
    thruster_manager:
      tf_prefix: missile_auv
      base_link: base_link
      thruster_topic_prefix: thrusters/
      thruster_topic_suffix: /input
      thruster_frame_base: thruster_
      max_thrust: 500.0
      timeout: -1.0
      update_rate: 50.0
      conversion_fcn: proportional
      conversion_fcn_params:
        gain: 0.01              # 必须匹配 rotor_constant
```

`gain` 必须匹配 xacro 中的 `rotor_constant`（都是 0.01）。

---

## 5. PID 控制参数

### 5.1 控制链路

```
cmd_vel → velocity_control.py → cmd_accel → acceleration_control.py → thruster_manager/input → TAM → 各推进器
```

### 5.2 惯性参数 (`inertial.yaml`)

```yaml
/**:
  ros__parameters:
    pid:
      mass: 250.0            # body_mass + X轴added_mass ≈ 200+25=225, 取稍大
      inertial:
        ixx: 11.5            # body_Ixx(1.5) + added_mass_K(10)
        iyy: 50.0            # body_Iyy(15) + added_mass_M(35)
        izz: 50.0            # body_Izz(15) + added_mass_N(35)
```

**注意：** mass 不要用全轴平均值（会导致X轴过补偿振荡）。鱼雷形AUV的X轴附加质量远小于Y/Z轴。

### 5.3 速度PID参数 (`vel_pid_control.yaml`)

```yaml
/**:
  ros__parameters:
    linear_p: 5.0
    linear_i: 1.0
    linear_d: 1.0
    linear_sat: 20.0

    angular_p: 5.0
    angular_i: 1.0
    angular_d: 2.0
    angular_sat: 5.0

    odom_vel_in_world: False   # pose_gt 的速度已是机体坐标系
```

**`odom_vel_in_world` 的选择：**
- `False`: pose_gt 的速度已在机体坐标系 → 直接用
- `True`: 假设速度在世界坐标系 → 会旋转到机体坐标系

Gazebo 的 pose_gt 发布的速度在**机体坐标系**（child frame）。设为 `True` 会导致：
- yaw=0 时正常（旋转矩阵=单位阵）
- yaw≠0 时往错误方向飘（速度被多转了一次）

---

## 6. 启动文件

### 6.1 Spawn 启动文件 (`upload_missile_auv.launch.py`)

关键修改：`gazebo_namespace` 默认值改为空字符串：

```python
'gazebo_namespace': LaunchConfiguration('gazebo_namespace', default="''")
```

原因：`/spawn_entity` 服务名不带 `/gazebo` 前缀。

### 6.2 PID 启动脚本 (`start_missile_pid.sh`)

```bash
#!/bin/bash
source /home/wei1367/ros2_ws/install/setup.bash

NAMESPACE="missile_auv"

# 清理旧进程
killall -9 velocity_control.py acceleration_control.py thruster_allocator.py 2>/dev/null
sleep 1

# 1. 推进器管理器
ros2 launch uuv_thruster_manager thruster_manager.launch \
  model_name:=$NAMESPACE uuv_name:=$NAMESPACE > /dev/null 2>&1 &
sleep 5

# 2. 加速度控制器（namespace下运行）
ros2 run uuv_control_cascaded_pid acceleration_control.py \
  --ros-args \
  -r __ns:=/$NAMESPACE \
  -p tf_prefix:="$NAMESPACE/" \
  --params-file .../inertial.yaml \
  > /dev/null 2>&1 &
sleep 3

# 3. 速度控制器（namespace下运行，odom重映射到pose_gt）
ros2 run uuv_control_cascaded_pid velocity_control.py \
  --ros-args \
  -r __ns:=/$NAMESPACE \
  -r odom:=/$NAMESPACE/pose_gt \
  --params-file .../vel_pid_control.yaml \
  > /dev/null 2>&1 &
sleep 3
```

**注意：** 不要把所有输出重定向到 `/dev/null`，否则启动失败看不到错误。建议开发阶段去掉重定向。

---

## 7. 完整启动步骤

```bash
# 终端1: Gazebo 海洋世界
source /opt/ros/humble/setup.zsh
ros2 launch uuv_gazebo_worlds ocean_waves.launch

# 终端2: 等Gazebo加载完，spawn导弹模型
source /home/wei1367/ros2_ws/install/setup.zsh
ros2 launch uuv_descriptions upload_missile_auv.launch.py

# 终端3: 等模型出现，启动PID控制
source /home/wei1367/ros2_ws/install/setup.zsh
./start_missile_pid.sh

# 终端4: 确认 ThrusterAllocator: ready 后，键盘控制
source /home/wei1367/ros2_ws/install/setup.zsh
ros2 run uuv_teleop vehicle_keyboard_teleop.py \
  --ros-args -r cmd_vel:=/missile_auv/cmd_vel -r output:=/missile_auv/cmd_vel
```

---

## 8. 验证命令

```bash
# 检查节点是否齐全
ros2 node list | grep -E "thruster_allocator|velocity_control|acceleration_control"

# 检查话题链路
ros2 topic info /missile_auv/cmd_vel              # Pub:1 Sub:1
ros2 topic info /missile_auv/cmd_accel             # Pub:1 Sub:1
ros2 topic info /missile_auv/thruster_manager/input  # Pub:1 Sub:1（关键！）

# 直接测试推进器
ros2 topic pub /missile_auv/thrusters/id_0/input std_msgs/msg/Float64 \
  '{data: 50.0}' --once

# 测试力矩分配
ros2 topic pub /missile_auv/thruster_manager/input geometry_msgs/msg/Wrench \
  '{force: {x: 50.0}}' --once
```

---

## 9. 踩坑总结

| 序号 | 问题 | 现象 | 根因 | 解决 |
|------|------|------|------|------|
| 1 | `<cone>` 几何 | URDF解析失败 | URDF不支持cone | 用cylinder+sphere替代 |
| 2 | 水动力参数位置 | 模型下沉不浮 | 参数直接放在plugin下 | 放在 `<link>` 子元素内 |
| 3 | 宏定义顺序 | xacro报未定义 | hydro_model宏在base之后定义 | 宏定义移到实例化之前 |
| 4 | 传感器origin | 编译失败 | 部分传感器宏不接受`*origin` | 移除GPS等的origin块 |
| 5 | gazebo_namespace | Waiting for service | 默认`/gazebo`前缀不匹配 | 改为空字符串 `''` |
| 6 | TAM.yaml格式 | thruster_allocator崩溃 | 多行数组ROS2解析失败 | 改为单行数组 |
| 7 | 垂推方向 | 上推力变为下推 | Ry(π/2) → -Z方向 | 改为 Ry(-π/2) → +Z方向 |
| 8 | odom_vel_in_world | 转向后移动往X飘 | pose_gt速度已是机体坐标系，多转了一次 | 改为 `False` |
| 9 | PID质量过大 | 前进时振荡 | mass=350远超X轴有效质量225 | 改为250 |
| 10 | CG/CB间距 | 翻滚不稳定 | z=0.02恢复力矩太小 | 改为z=0.08 |
| 11 | rclpy.ok()崩溃 | ROS2节点全部崩溃 | 残留进程损坏daemon | `ros2 daemon stop && start` |
