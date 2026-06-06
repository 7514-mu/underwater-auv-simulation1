# AUV 故障测试系统 (Fault Test System)

**版本**: v1.0
**日期**: 2026-04-15
**适用于**: ROS 2 Humble + UUV Simulator + RexROV

---

## 📁 目录结构

```
fault_test/
├── README.md                        # 本文件（主入口）
├── scripts/                         # 脚本和代码
│   ├── fault_injector_standalone.py  # 故障注入器（主程序）
│   └── fault_injection_start.sh      # 快速启动脚本
├── docs/                            # 文档
│   ├── 故障注入系统_完整指南.md       # 主文档（推荐先看）
│   ├── AUV故障注入系统_完整文档.md    # 技术参考文档
│   ├── 故障测试_实时记录.md           # 测试记录模板
│   └── 故障注入系统_使用指南.md       # 快速参考
└── examples/                        # 测试示例
    └── test_scenarios.md             # 测试场景说明
```

---

## 🚀 快速开始

### 1️⃣ 查看文档

**推荐阅读顺序**:

1. 📖 [docs/故障注入系统_完整指南.md](docs/故障注入系统_完整指南.md) - **必读！**系统介绍和使用方法
2. 📝 [docs/故障测试_实时记录.md](docs/故障测试_实时记录.md) - 测试记录模板
3. 📘 [docs/AUV故障注入系统_完整文档.md](docs/AUV故障注入系统_完整文档.md) - 详细技术文档

### 2️⃣ 启动系统

**方法1: 使用启动脚本**
```bash
cd ~/ros2_ws/fault_test/scripts
./fault_injection_start.sh
```

**方法2: 手动启动（6个终端）**
```bash
# 终端1: Gazebo
source ~/.zshrc
ros2 launch uuv_gazebo_worlds ocean_waves.launch

# 终端2: RexROV
source ~/.zshrc
ros2 launch uuv_descriptions upload_rexrov_default.launch.py mode:=default x:=0 y:=0 z:=-20 namespace:=rexrov gazebo_namespace:="''"

# 终端3: 推进器管理器
source ~/.zshrc
ros2 launch uuv_thruster_manager thruster_manager.launch model_name:=rexrov

# 终端4: 命令转换器
source ~/.zshrc
python3 ~/ros2_ws/cmd_vel_to_wrench_simple.py

# 终端5: 键盘控制
source ~/.zshrc
python3 ~/ros2_ws/simple_teleop.py

# 终端6: 故障注入器 ⭐
source ~/.zshrc
python3 ~/ros2_ws/fault_test/scripts/fault_injector_standalone.py
```

### 3️⃣ 注入故障

在故障注入器终端输入：

```bash
fault_injector> inject 1 0 10  # 推进器0完全失效10秒
fault_injector> status         # 查看故障状态
fault_injector> clear          # 清除故障
fault_injector> menu           # 显示帮助
```

---

## 🔧 6种故障类型

| 类型 | 名称 | 命令示例 | 应用场景 |
|------|------|----------|----------|
| 1️⃣ | COMPLETE FAILURE | `inject 1 0 10` | 测试容错能力 |
| 2️⃣ | PARTIAL FAILURE | `inject 2 0,1,2 15` | 测试降级运行 |
| 3️⃣ | STUCK THRUSTER | `inject 3 5 8` | 测试紧急处理 |
| 4️⃣ | REVERSE THRUST | `inject 4 6 10` | 测试传感器融合 |
| 5️⃣ | OSCILLATING | `inject 5 3,7 12` | 测试控制稳定性 |
| 6️⃣ | PROGRESSIVE | `inject 6 0,1,2,3,4,5 20` | 测试预测性维护 |

**⚠️ 警告**: 推力反向故障（类型4）最危险！按上浮反而下潜。

---

## 🎮 RexROV推进器索引

```
前视图:
  0(前左)     1(前右)     → Surge (前后)
    ○━━━○
    │     │
  2(中左)     3(中右)     → Sway (左右)
    ○━━━○
    │     │
  4(后左)     5(后右)     → Surge (前后)
    ○━━━○
  6: Heave (垂直/上下)
  7: Yaw (偏航/旋转)
```

---

## 🧪 测试场景

### 场景1: 单推进器失效
```bash
inject 1 0 10  # 推进器0失效10秒
```

### 场景2: 垂直推进器失效（关键测试）
```bash
inject 1 6 10  # 垂直推进器失效，AUV无法维持深度
```

### 场景3: 推力反向（危险！）
```bash
inject 4 6 10  # 垂直推进器反向，按上浮反而下潜
```

### 场景4: 多推进器失效
```bash
inject 1 0,1,2,3 10  # 4个推进器同时失效
```

更多测试场景请查看 [docs/故障注入系统_完整指南.md](docs/故障注入系统_完整指南.md)

---

## 🎯 师兄任务应用

### 任务1: 测试模型缺陷
通过故障注入发现AUV控制系统的弱点

**实验**:
```bash
# 测试每个推进器的重要性
for i in {0..7}; do
    inject 1 $i 10
    # 记录影响
done
```

### 任务2: 最大化干扰
找到对AUV干扰最大的故障组合

**实验**:
```bash
inject 1 0,1,2,3,4,5,6,7 10  # 全部推进器失效
inject 4 6 10                   # 垂直推进器反向
```

### 任务3: 仿真到现实
将仿真结果应用到实际AUV模型

**数据收集**:
- 每种故障的特征参数
- 故障对性能的影响曲线
- 故障检测阈值

### 任务4: 强化学习 + 路径规划
训练AI在故障情况下仍能完成任务

**数据收集**:
```bash
# 收集故障数据用于训练
for fault_type in {1..6}; do
    for thruster in {0..7}; do
        inject $fault_type $thruster 10
        clear
    done
done
```

---

## 📊 系统架构

```
控制器 (键盘/自动驾驶)
    ↓ cmd_vel
推进器管理器 (Thruster Manager)
    ↓ thrust commands
┌─────────────────┐ ← 故障注入点
│   故障注入器    │  (拦截并修改命令)
└─────────────────┘
    ↓ faulty commands
推进器插件 (Thruster Plugin)
    ↓ force
Gazebo仿真环境
```

---

## 🛠️ 故障排除

### 问题1: 故障注入器无法控制推进器
**解决**: 确保故障注入器最后启动

### 问题2: AUV完全失控
**解决**: 输入`clear`清除故障，或按空格键紧急停止

### 问题3: 推进器索引错误
**解决**: RexROV只有8个推进器（索引0-7），不要超出范围

---

## 📚 完整文档

| 文档 | 说明 | 推荐度 |
|------|------|--------|
| [docs/故障测试_实时记录.md](docs/故障测试_实时记录.md) | 测试记录模板，用于记录实验数据 | ⭐⭐⭐⭐⭐ |

---

## 📝 文件说明

### 脚本 (scripts/)

| 文件 | 说明 | 用途 |
|------|------|------|
| fault_injector_standalone.py | 故障注入器主程序 | 注入各种故障 |
| fault_injection_start.sh | 快速启动脚本 | 查看启动命令 |

### 文档 (docs/)

| 文件 | 说明 |
|------|------|
| 故障测试_实时记录.md | 测试记录模板（用于记录实验数据） |

---

## 🎓 快速参考

### 启动故障注入器
```bash
python3 ~/ros2_ws/fault_test/scripts/fault_injector_standalone.py
```

### 注入故障命令格式
```bash
inject <故障类型(1-6)> <推进器索引(0-7,逗号分隔)> <持续时间(秒)>
```

### 示例
```bash
inject 1 0 10          # 推进器0完全失效10秒
inject 2 0,1,2 15      # 推进器0,1,2部分失效15秒
inject 4 6 10          # 推进器6推力反向10秒
```

### 其他命令
```bash
status  # 查看故障状态
clear   # 清除所有故障
menu    # 显示帮助菜单
```

---

## 🚀 使用流程

1. **阅读文档** - 查看 [docs/故障注入系统_完整指南.md](docs/故障注入系统_完整指南.md)
2. **启动仿真** - 按照"快速开始"启动6个终端
3. **注入故障** - 在故障注入器终端输入命令
4. **观察记录** - 使用 [docs/故障测试_实时记录.md](docs/故障测试_实时记录.md) 记录数据
5. **分析结果** - 完成师兄的4个任务

---

## 🎯 师兄任务清单

- [ ] **任务1**: 测试模型缺陷
  - [ ] 单推进器失效测试
  - [ ] 多推进器失效测试
  - [ ] 关键推进器测试

- [ ] **任务2**: 最大化干扰
  - [ ] 找出最致命故障组合
  - [ ] 测试临界失效点

- [ ] **任务3**: 仿真到现实
  - [ ] 建立故障模型库
  - [ ] 验证容错算法
  - [ ] 优化推进器布局

- [ ] **任务4**: 强化学习 + 路径规划
  - [ ] 收集故障数据
  - [ ] 训练RL模型
  - [ ] 验证路径规划鲁棒性

---

## 📧 帮助

遇到问题？
1. 查看 [docs/AUV故障注入系统_完整文档.md](docs/AUV故障注入系统_完整文档.md) 的"故障排除"章节
2. 检查启动顺序是否正确
3. 确认所有Topic都在运行: `ros2 topic list | grep thruster`

---

**最后更新**: 2026-04-15
**维护者**: [待填写]
**状态**: ✅ 可用

---

**祝实验成功！Good luck with your research! 🚀**
