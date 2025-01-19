# 树莓派舵机机器人控制系统

一个基于树莓派的模块化舵机机器人控制系统，提供灵活的舵机控制、传感器管理和动作组编程功能。该系统采用 Python 开发，支持远程控制和实时监控。

## 目录

- [功能特点](#功能特点)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [高级功能](#高级功能)
- [开发指南](#开发指南)
- [API参考](#api参考)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

## 功能特点

- **核心功能**
  - 模块化设计，易于扩展
  - 统一的状态管理
  - 完整的日志系统
  - 远程控制接口

- **动作控制**
  - 动作组的实时录制和回放
  - 动作序列的平滑插值
  - 动作轨迹优化
  - 并行动作执行

- **传感器支持**
  - 多种传感器集成
  - 实时数据过滤
  - 姿态解算支持
  - 可扩展的传感器架构

## 系统架构

### 核心模块

1. **状态管理器 (State Manager)**
   - 集中管理机器人状态
   - 线程安全的状态访问
   - 实时状态监控
   ```python
   from robot.core.state_manager import RobotStateManager
   
   # 创建状态管理器
   state_manager = RobotStateManager()
   
   # 更新状态
   state_manager.update_state('servos', 'servo1', {'angle': 90})
   
   # 获取状态
   servo_state = state_manager.get_state('servos', 'servo1')
   ```

2. **动作处理**
   - 动作序列插值
   ```python
   from robot.actions.interpolator import ActionInterpolator
   
   interpolator = ActionInterpolator()
   smooth_sequence = interpolator.interpolate(keyframes, num_points=10)
   ```
   
   - 动作优化
   ```python
   from robot.actions.optimizer import ActionOptimizer
   
   optimizer = ActionOptimizer()
   optimized_sequence = optimizer.optimize_timing(sequence, max_speed=300.0)
   reduced_jerk = optimizer.reduce_jerk(sequence, smoothing_factor=0.5)
   ```

3. **传感器处理**
   - 数据过滤器
   ```python
   from robot.sensors.filter import SensorFilter, KalmanFilter
   
   # 中值滤波
   filter = SensorFilter(window_size=10)
   filtered_value = filter.update(raw_value)
   
   # 卡尔曼滤波
   kalman = KalmanFilter()
   estimated_value = kalman.update(measurement)
   ```

## 高级功能

### 1. 动作序列优化

系统提供多种动作优化功能：

1. 时序优化
```python
# 根据最大速度限制优化动作时序
optimized = optimizer.optimize_timing(sequence, max_speed=300.0)
```

2. 抖动减少
```python
# 减少动作轨迹的抖动
smoothed = optimizer.reduce_jerk(sequence, smoothing_factor=0.5)
```

3. 轨迹平滑
```python
# 对动作序列进行平滑插值
interpolated = interpolator.interpolate(keyframes, num_points=10)
smoothed = interpolator.smooth_trajectory(frames, window_size=3)
```

### 2. 传感器数据处理

提供多种数据过滤方案：

1. 中值滤波
```python
filter = SensorFilter(window_size=10)
filtered = filter.update(raw_data)
```

2. 卡尔曼滤波
```python
kalman = KalmanFilter(process_variance=1e-4, measurement_variance=1e-2)
estimated = kalman.update(measurement)
```

### 3. 状态监控

实时监控机器人状态：

```python
# 获取特定类别的状态
servo_states = state_manager.get_state('servos')
sensor_data = state_manager.get_state('sensors')

# 获取完整状态
full_state = state_manager.get_full_state()
```

### 4. 动作组管理增强

系统提供了增强的动作组管理功能：

```python
from robot.actions.action_manager import ActionManager

# 创建动作管理器
manager = ActionManager()

# 从文件加载动作组
manager.load_from_file('actions/dance.yaml')

# 执行动作组（支持回调）
def on_complete(name: str, success: bool):
    print(f"动作组 {name} 执行{'成功' if success else '失败'}")

manager.execute('dance', parallel=True, callback=on_complete)
```

特点：
- 支持动作组的并行执行
- 提供执行完成回调
- 支持动态停止功能
- 线程安全的状态管理

### 5. 视觉处理增强

新增人脸检测功能：

```python
from robot.vision.face_detector import FaceDetector

# 创建人脸检测器
detector = FaceDetector()

# 检测人脸
faces = detector.detect(frame)

# 获取最大人脸
largest_face = detector.get_largest_face(faces)

# 绘制检测结果
detector.draw_faces(frame, faces)
```

特点：
- 支持多人脸检测
- 提供人脸位置和大小信息
- 支持最大人脸识别
- 可视化检测结果

### 6. 动作校准系统

提供动作校准功能：

```python
from robot.actions.calibrator import ActionCalibrator

# 创建校准器
calibrator = ActionCalibrator()

# 设置参考动作
calibrator.set_reference('wave', reference_frames)

# 校准动作序列
calibrated = calibrator.calibrate('wave', frames, max_angle_diff=5.0)

# 分析动作差异
differences = calibrator.analyze_difference('wave', frames)
```

特点：
- 基于参考动作的校准
- 可配置的角度差异阈值
- 自动角度校正
- 动作差异分析

### 7. 消息发布/订阅系统

系统提供了类似 ROS 的消息发布/订阅机制：

```python
from robot.core.message_broker import MessageBroker

# 创建消息代理
broker = MessageBroker()

# 订阅消息
def on_sensor_data(data):
    print(f"收到传感器数据: {data}")
broker.subscribe("sensor_data", on_sensor_data)

# 发布消息
broker.publish("sensor_data", {"temperature": 25.5})
```

特点：
- 异步消息处理
- 线程安全设计
- 支持多订阅者
- 自动错误处理

### 8. 状态机系统

提供完整的机器人状态管理：

```python
from robot.core.state_machine import StateMachine, RobotState

# 创建状态机
sm = StateMachine()

# 添加状态转换
def on_start():
    print("机器人启动中...")
sm.add_transition(RobotState.IDLE, RobotState.INITIALIZING, on_start)

# 添加状态处理器
def handle_running():
    print("机器人运行中...")
sm.add_state_handler(RobotState.RUNNING, handle_running)

# 执行状态转换
sm.transition_to(RobotState.INITIALIZING)
```

支持的状态：
- IDLE: 空闲状态
- INITIALIZING: 初始化中
- RUNNING: 运行中
- PAUSED: 已暂停
- ERROR: 错误状态
- CALIBRATING: 校准中
- RECORDING: 录制中
- EXECUTING: 执行中

### 9. 坐标变换系统

提供机器人坐标系统管理：

```python
from robot.core.transform import Transform, TransformTree

# 创建变换树
transform_tree = TransformTree()

# 添加变换关系
base_to_arm = Transform(
    translation=np.array([0, 0, 0.1]),
    rotation=np.eye(3)
)
transform_tree.add_transform("base", "arm", base_to_arm)

# 转换坐标点
point = np.array([0.1, 0.2, 0.3])
transformed = transform_tree.transform_point(point, "arm", "base")
```

特点：
- 支持多坐标系管理
- 自动计算变换链
- 提供逆变换计算
- 齐次变换矩阵支持

### 10. 任务规划系统

提供任务规划和执行管理：

```python
from robot.planning.task_planner import TaskPlanner, Task

# 创建任务规划器
planner = TaskPlanner()

# 定义任务
def grab_object():
    # 抓取物体的具体实现
    pass

task = Task(
    name="grab",
    action=grab_object,
    prerequisites=["move_to_position"],
    timeout=10.0
)

# 添加任务
planner.add_task(task)

# 执行任务
planner.execute_task("grab")

# 监控任务状态
status = planner.get_task_status("grab")
```

任务状态：
- PENDING: 等待执行
- RUNNING: 执行中
- COMPLETED: 已完成
- FAILED: 执行失败
- CANCELLED: 已取消

### 7. 动作组优化

系统提供了完整的动作组优化功能：

```python
from robot.actions.optimizer import ActionOptimizer

# 创建优化器
optimizer = ActionOptimizer()

# 时序优化
optimized = optimizer.optimize_timing(
    frames,
    min_delay=0.02,
    max_velocity=300.0
)

# 轨迹平滑
smoothed = optimizer.smooth_trajectory(
    frames,
    window_size=3
)

# 减少加加速度
optimized = optimizer.reduce_jerk(
    frames,
    max_accel=200.0
)
```

特点：
- 自动时序优化
- 高斯加权平滑
- 加速度限制
- 抖动控制

### 8. 动作组分析

提供动作分析和诊断工具：

```python
from robot.actions.analyzer import ActionAnalyzer

analyzer = ActionAnalyzer()

# 分析动作复杂度
metrics = analyzer.analyze_complexity(frames)
print(f"帧数: {metrics['frame_count']}")
print(f"舵机数: {metrics['servo_count']}")
print(f"总时长: {metrics['total_duration']}")

# 查找关键帧
critical_points = analyzer.find_critical_points(
    frames,
    threshold=10.0
)

# 检测异常
anomalies = analyzer.detect_anomalies(
    frames,
    velocity_threshold=300.0,
    accel_threshold=200.0
)
```

分析指标：
- 角度变化统计
- 时序分析
- 运动特征
- 异常检测

### 9. 版本管理

支持动作组和配置的版本管理：

```python
from robot.actions.action_version import ActionVersionManager
from robot.config.robot_config import RobotConfig

# 动作组版本管理
version_manager = ActionVersionManager()

# 保存版本
version_id = version_manager.save_action_group(
    name="wave_hand",
    frames=frames,
    version_name="v1.0.0",
    comment="Initial version"
)

# 加载版本
action_data = version_manager.load_action_group(version_id)

# 配置版本管理
config = RobotConfig()
config.save_version("v1.0.0", "Initial config")
config.compare_with_version("v0.9.0")
config.rollback("v0.9.0")
```

版本功能：
- 版本保存和加载
- 版本比较
- 回滚支持
- 元数据记录

## 最佳实践

19. 动作优化
    - 合理设置速度限制
    - 选择合适的平滑窗口
    - 注意加速度约束
    - 避免过度平滑

20. 动作分析
    - 定期检查异常
    - 关注关键帧
    - 监控性能指标
    - 分析优化效果

21. 版本管理
    - 规范版本命名
    - 添加详细注释
    - 定期清理旧版本
    - 保持版本完整性

## 系统特点

- **模块化设计**：核心功能模块化，便于扩展和维护
- **统一管理**：通过核心管理器统一管理所有组件
- **配置驱动**：使用 YAML 配置文件管理硬件设置和动作组
- **远程控制**：提供 XML-RPC 接口，支持远程操作
- **日志系统**：完整的日志记录，支持文件和控制台输出
- **优雅退出**：完善的资源清理和错误处理机制

## 系统架构

### 核心模块

1. **核心管理器 (Core Manager)**
   - 统一管理所有子系统
   - 处理系统初始化和关闭
   - 协调各模块间的通信

2. **舵机管理模块 (Servo Manager)**
   - 舵机初始化和配置
   - PWM 信号生成和控制
   - 多舵机协调管理
   - 角度限位保护

3. **传感器管理模块 (Sensor Manager)**
   - 支持多种传感器类型
   - 统一的传感器接口
   - 实时数据采集
   - 可扩展的传感器架构

4. **动作组管理模块 (Action Manager)**
   - 动作组定义和存储
   - 序列化动作执行
   - 支持延时和同步
   - 动作组的实时控制

5. **配置管理模块 (Config Manager)**
   - YAML 配置文件解析
   - 硬件参数管理
   - 动作组配置
   - 运行时配置更新

6. **日志系统 (Logger)**
   - 运行日志记录
   - 错误追踪
   - 调试信息输出
   - 日志文件管理

7. **RPC 服务器 (RPC Server)**
   - 远程控制接口
   - 实时状态查询
   - 安全的通信机制
   - 多客户端支持

## 硬件要求

- 树莓派 3B+ 或更高版本
- 舵机电源供应（建议使用独立电源）
- 支持的舵机型号：
  - SG90
  - MG996R
  - 其他标准 PWM 舵机
- 支持的传感器：
  - 超声波传感器（HC-SR04）
  - 更多传感器支持开发中

## 安装指南

### 1. 系统要求
```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install python3-pip python3-yaml
```

### 2. 安装 Python 依赖
```bash
# 克隆项目
git clone [项目地址]
cd [项目目录]

# 安装依赖
pip3 install -r requirements.txt
```

### 3. 配置硬件
```bash
# 启用 GPIO
sudo raspi-config
# 选择 "Interfacing Options" -> "GPIO" -> "Yes"
```

## 使用指南

### 1. 配置文件设置

创建并编辑配置文件：
```bash
cp config.yaml.example config.yaml
nano config.yaml
```

配置文件示例：
```yaml
# 舵机配置
servos:
  servo1:
    pin: 18              # GPIO引脚号
    min_pulse: 500       # 最小脉冲宽度(μs)
    max_pulse: 2500      # 最大脉冲宽度(μs)
    min_angle: 0         # 最小角度
    max_angle: 180       # 最大角度

# 传感器配置
sensors:
  ultrasonic1:
    type: ultrasonic     # 传感器类型
    trigger_pin: 17      # 触发引脚
    echo_pin: 27         # 回响引脚

# 动作组配置
action_groups:
  wave:                  # 动作组名称
    - servo_id: servo1   # 舵机ID
      angle: 90          # 目标角度
      delay: 0.5         # 延时(秒)
    - servo_id: servo1
      angle: 0
      delay: 0.5
```

### 2. 运行系统

基本运行：
```bash
python3 run.py
```

高级运行选项：
```bash
# 指定配置文件
python3 run.py -c custom_config.yaml

# 指定RPC服务器地址和端口
python3 run.py --host 192.168.1.100 -p 8888

# 查看帮助
python3 run.py --help
```

## 开发指南

### 1. 添加新的传感器类型

1. 创建新的传感器类文件 `robot/sensors/new_sensor.py`：
```python
from .sensor_base import SensorBase

class NewSensor(SensorBase):
    def __init__(self, pin: int, **kwargs):
        super().__init__(pin)
        # 初始化特定参数
        
    def _setup(self):
        """初始化传感器"""
        # 实现初始化逻辑
        
    def read(self):
        """读取传感器数据"""
        # 实现数据读取逻辑
        return data
        
    def cleanup(self):
        """清理资源"""
        # 实现清理逻辑
```

2. 在配置文件中使用新传感器：
```yaml
sensors:
  new_sensor1:
    type: new_sensor
    pin: 25
    # 其他特定参数
```

### 2. 创建自定义动作组

1. 在配置文件中定义动作组：
```yaml
action_groups:
  custom_action:
    - servo_id: servo1
      angle: 45
      delay: 0.5
    - servo_id: servo2
      angle: 90
      delay: 0.3
```

2. 通过RPC接口执行：
```python
client.execute_action_group("custom_action")
```

### 3. 使用姿态解算

1. 初始化传感器和解算器：
```python
from robot.sensors.imu import IMUSensor
from robot.core.attitude_solver import AttitudeSolver

imu = IMUSensor()
solver = AttitudeSolver()
```

2. 实时更新姿态：
```python
def update_attitude():
    data = imu.read()
    solver.update(data['accel'], data['gyro'])
    attitude = solver.get_attitude()
    return attitude
```

### 4. 实现人脸跟踪

1. 初始化检测器：
```python
detector = FaceDetector()
processor = VisionProcessor()

def track_face():
    while True:
        frame = processor.get_frame()
        faces = detector.detect(frame)
        if faces:
            face = detector.get_largest_face(faces)
            # 执行跟踪逻辑
            track_target(face['center'])
```

### 5. 使用动作校准

1. 校准动作序列：
```python
calibrator = ActionCalibrator()

# 加载参考动作
with open('reference.yaml', 'r') as f:
    reference = yaml.safe_load(f)
calibrator.set_reference('dance', reference)

# 校准动作
calibrated = calibrator.calibrate('dance', recorded_frames)
```

2. 分析动作质量：
```python
# 获取动作差异
differences = calibrator.analyze_difference('dance', frames)

# 输出分析结果
for servo_id, diff in differences.items():
    print(f"舵机 {servo_id} 平均偏差: {diff:.2f}度")
```

### 6. 使用消息系统

1. 创建自定义消息处理器：
```python
def handle_sensor_data(data):
    if data["temperature"] > 30:
        broker.publish("alarm", "温度过高")

broker.subscribe("sensor_data", handle_sensor_data)
```

2. 实现消息过滤：
```python
def temperature_filter(data):
    return "temperature" in data and data["temperature"] > 0

broker.subscribe("sensor_data", handle_sensor_data, filter=temperature_filter)
```

### 7. 状态机应用

1. 定义状态转换逻辑：
```python
def can_transition(from_state, to_state):
    # 实现状态转换验证逻辑
    return True

sm.add_transition_validator(can_transition)
```

2. 状态监控：
```python
def on_state_changed(old_state, new_state):
    logger.info(f"状态变更: {old_state} -> {new_state}")

sm.add_state_change_listener(on_state_changed)
```

## API 参考

### RPC 接口

1. 舵机控制
```python
# 设置舵机角度
set_servo_angle(servo_id: str, angle: float) -> bool
```

2. 动作组控制
```python
# 执行动作组
execute_action_group(group_name: str) -> bool
```

3. 传感器数据读取
```python
# 读取传感器数据
get_sensor_data(sensor_id: str) -> Any
```

## 故障排除

### 常见问题

1. GPIO 权限问题
```bash
sudo chmod a+rw /dev/gpiomem
```

2. 舵机控制问题
- 检查电源供应是否充足
- 验证 GPIO 引脚配置是否正确
- 确认 PWM 参数设置合适

3. 传感器读取问题
- 检查接线是否正确
- 验证传感器供电电压
- 确认 GPIO 引脚配置

### 调试建议

1. 启用详细日志：
```bash
# 修改 robot/utils/logger.py 中的日志级别
self.logger.setLevel(logging.DEBUG)
```

2. 检查系统日志：
```bash
tail -f logs/robot_*.log
```

## 项目结构
```
robot/
├── core/               # 核心模块
│   └── manager.py     # 核心管理器
├── servos/            # 舵机控制模块
│   ├── servo.py      # 舵机基类
│   └── servo_manager.py
├── sensors/           # 传感器模块
│   ├── sensor_base.py
│   └── ultrasonic.py
├── actions/           # 动作组模块
│   └── action_manager.py
├── config/           # 配置管理模块
│   └── config_manager.py
├── network/          # 网络通信模块
│   └── rpc_server.py
└── utils/            # 工具模块
    └── logger.py
```

## 最佳实践

1. 硬件配置
   - 使用独立的舵机电源供应
   - 注意 GPIO 引脚的电平要求
   - 合理布局接线，避免干扰

2. 软件开发
   - 遵循模块化设计原则
   - 做好异常处理
   - 及时记录日志
   - 注意资源的及时释放

3. 系统维护
   - 定期备份配置文件
   - 监控系统日志
   - 及时更新软件依赖

4. 姿态控制
   - 定期校准 IMU 传感器
   - 合理设置滤波参数
   - 注意采样频率
   - 考虑环境振动影响

5. 平衡控制
   - 根据实际负载调整 PID 参数
   - 避免积分饱和
   - 添加输出限幅
   - 实现平滑控制过渡

6. 动作编辑
   - 使用预览功能验证动作
   - 合理设置动作速度
   - 注意舵机负载
   - 保存重要动作序列

7. 视觉处理
   - 合理设置检测参数
   - 注意图像预处理
   - 考虑光照影响
   - 优化处理性能

8. 动作校准
   - 选择合适的参考动作
   - 定期更新参考数据
   - 合理设置差异阈值
   - 记录校准日志

9. 并行执行
   - 控制并行任务数量
   - 注意资源竞争
   - 实现优雅停止
   - 处理执行异常

10. 消息处理
    - 避免长时间阻塞
    - 合理设置队列大小
    - 实现消息过滤
    - 处理超时情况

11. 状态管理
    - 定义清晰的状态转换
    - 实现状态恢复机制
    - 记录状态变化历史
    - 处理异常状态

12. 任务规划
    - 合理设置任务依赖
    - 实现任务超时处理
    - 提供任务取消机制
    - 记录任务执行日志

13. 动作优化
    - 合理设置速度限制
    - 选择合适的平滑窗口
    - 注意加速度约束
    - 避免过度平滑

14. 动作分析
    - 定期检查异常
    - 关注关键帧
    - 监控性能指标
    - 分析优化效果

15. 版本管理
    - 规范版本命名
    - 添加详细注释
    - 定期清理旧版本
    - 保持版本完整性

## 版本历史

- v1.0.0 (2024-03-xx)
  - 初始版本发布
  - 基本功能实现
  - RPC 接口支持
  - 日志系统集成

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 联系方式

- 项目维护者: [维护者邮箱]
- 项目主页: [项目 GitHub 地址]

## 功能特点

- **动作组管理**
  - 支持动作组的实时录制和回放
  - 动作组的并行执行
  - 动作组的保存和加载
  - 支持动作组的实时停止

## API 参考

### RPC 接口

1. 基础控制
```python
# 设置舵机角度
set_servo_angle(servo_id: str, angle: float) -> bool

# 读取传感器数据
get_sensor_data(sensor_id: str) -> Any
```

2. 动作组控制
```python
# 执行动作组（支持并行执行）
execute_action_group(group_name: str, parallel: bool = False) -> bool

# 停止指定动作组
stop_action_group(group_name: str) -> bool

# 停止所有动作组
stop_all_groups() -> bool
```

3. 动作录制
```python
# 开始录制动作
start_recording() -> bool

# 停止录制并获取动作数据
stop_recording() -> List[Dict]

# 保存录制的动作组
save_recorded_actions(group_name: str) -> bool
```

### 动作组录制示例

1. 通过 RPC 客户端录制动作：
```python
from xmlrpc.client import ServerProxy

# 连接到RPC服务器
client = ServerProxy('http://localhost:8000')

# 开始录制
client.start_recording()

# 执行一系列舵机动作
client.set_servo_angle('servo1', 45)
time.sleep(1)
client.set_servo_angle('servo1', 90)
time.sleep(1)
client.set_servo_angle('servo1', 0)

# 停止录制并保存
actions = client.stop_recording()
client.save_recorded_actions('my_action')
```

2. 执行录制的动作组：
```python
# 串行执行
client.execute_action_group('my_action')

# 并行执行（与其他动作组同时运行）
client.execute_action_group('my_action', parallel=True)

# 停止正在执行的动作组
client.stop_action_group('my_action')
```

### 传感器支持

1. 超声波传感器 (HC-SR04)
```yaml
sensors:
  ultrasonic1:
    type: ultrasonic
    trigger_pin: 17
    echo_pin: 27
```

2. 红外传感器
```yaml
sensors:
  infrared1:
    type: infrared
    pin: 22
```

使用示例：
```python
# 读取超声波传感器距离
distance = client.get_sensor_data('ultrasonic1')  # 返回厘米数

# 读取红外传感器状态
detected = client.get_sensor_data('infrared1')    # 返回布尔值
```

## 高级功能

### 1. 姿态解算

系统提供基于 IMU 的姿态解算功能：

```python
from robot.core.attitude_solver import AttitudeSolver

# 创建姿态解算器
solver = AttitudeSolver()

# 更新姿态数据
accel_data = imu.read()['accel']
gyro_data = imu.read()['gyro']
solver.update(accel_data, gyro_data)

# 获取姿态角
pitch, roll, yaw = solver.get_attitude()
```

特点：
- 基于卡尔曼滤波的姿态融合
- 实时姿态角计算
- 自动处理陀螺仪漂移
- 支持欧拉角输出

### 2. 平衡控制

提供 PID 平衡控制器：

```python
from robot.control.balance_controller import BalanceController

# 创建平衡控制器
controller = BalanceController()

# 设置目标角度
controller.set_target(0.0)

# 设置 PID 参数
controller.set_pid(kp=20.0, ki=0.1, kd=0.4)

# 更新控制输出
output = controller.update(current_angle)
```

特点：
- 可调节的 PID 参数
- 实时控制输出
- 自动积分项重置
- 支持日志记录

### 3. 动作序列编辑器增强

动作序列编辑器新增预览功能：

```python
from robot.actions.sequence_editor import ActionSequenceEditor

# 创建编辑器
editor = ActionSequenceEditor(servo_ids=['servo1', 'servo2'])

# 设置预览回调
def preview_frame(frame):
    """处理单帧预览"""
    for servo_id, angle in frame.items():
        servo_manager.set_angle(servo_id, angle)

def preview_sequence(sequence, speed):
    """处理序列预览"""
    for frame in sequence:
        preview_frame(frame)
        time.sleep(0.5 / speed)
```

2. 启动编辑器：
```python
editor = ActionSequenceEditor(servo_ids)
editor.set_preview_callbacks(preview_frame, preview_sequence)
editor.run()
```

新增功能：
- 实时动作预览
- 可调节预览速度
- 支持单帧预览
- 支持序列播放

### 4. 实现人脸跟踪

1. 初始化检测器：
```python
detector = FaceDetector()
processor = VisionProcessor()

def track_face():
    while True:
        frame = processor.get_frame()
        faces = detector.detect(frame)
        if faces:
            face = detector.get_largest_face(faces)
            # 执行跟踪逻辑
            track_target(face['center'])
```

### 5. 使用动作校准

1. 校准动作序列：
```python
calibrator = ActionCalibrator()

# 加载参考动作
with open('reference.yaml', 'r') as f:
    reference = yaml.safe_load(f)
calibrator.set_reference('dance', reference)

# 校准动作
calibrated = calibrator.calibrate('dance', recorded_frames)
```

2. 分析动作质量：
```python
# 获取动作差异
differences = calibrator.analyze_difference('dance', frames)

# 输出分析结果
for servo_id, diff in differences.items():
    print(f"舵机 {servo_id} 平均偏差: {diff:.2f}度")
```

### 6. 动作校准系统

提供动作校准功能：

```python
from robot.actions.calibrator import ActionCalibrator

# 创建校准器
calibrator = ActionCalibrator()

# 设置参考动作
calibrator.set_reference('wave', reference_frames)

# 校准动作序列
calibrated = calibrator.calibrate('wave', frames, max_angle_diff=5.0)

# 分析动作差异
differences = calibrator.analyze_difference('wave', frames)
```

特点：
- 基于参考动作的校准
- 可配置的角度差异阈值
- 自动角度校正
- 动作差异分析

### 7. 消息发布/订阅系统

系统提供了类似 ROS 的消息发布/订阅机制：

```python
from robot.core.message_broker import MessageBroker

# 创建消息代理
broker = MessageBroker()

# 订阅消息
def on_sensor_data(data):
    print(f"收到传感器数据: {data}")
broker.subscribe("sensor_data", on_sensor_data)

# 发布消息
broker.publish("sensor_data", {"temperature": 25.5})
```

特点：
- 异步消息处理
- 线程安全设计
- 支持多订阅者
- 自动错误处理

### 8. 状态机系统

提供完整的机器人状态管理：

```python
from robot.core.state_machine import StateMachine, RobotState

# 创建状态机
sm = StateMachine()

# 添加状态转换
def on_start():
    print("机器人启动中...")
sm.add_transition(RobotState.IDLE, RobotState.INITIALIZING, on_start)

# 添加状态处理器
def handle_running():
    print("机器人运行中...")
sm.add_state_handler(RobotState.RUNNING, handle_running)

# 执行状态转换
sm.transition_to(RobotState.INITIALIZING)
```

支持的状态：
- IDLE: 空闲状态
- INITIALIZING: 初始化中
- RUNNING: 运行中
- PAUSED: 已暂停
- ERROR: 错误状态
- CALIBRATING: 校准中
- RECORDING: 录制中
- EXECUTING: 执行中

### 9. 坐标变换系统

提供机器人坐标系统管理：

```python
from robot.core.transform import Transform, TransformTree

# 创建变换树
transform_tree = TransformTree()

# 添加变换关系
base_to_arm = Transform(
    translation=np.array([0, 0, 0.1]),
    rotation=np.eye(3)
)
transform_tree.add_transform("base", "arm", base_to_arm)

# 转换坐标点
point = np.array([0.1, 0.2, 0.3])
transformed = transform_tree.transform_point(point, "arm", "base")
```

特点：
- 支持多坐标系管理
- 自动计算变换链
- 提供逆变换计算
- 齐次变换矩阵支持

### 10. 任务规划系统

提供任务规划和执行管理：

```python
from robot.planning.task_planner import TaskPlanner, Task

# 创建任务规划器
planner = TaskPlanner()

# 定义任务
def grab_object():
    # 抓取物体的具体实现
    pass

task = Task(
    name="grab",
    action=grab_object,
    prerequisites=["move_to_position"],
    timeout=10.0
)

# 添加任务
planner.add_task(task)

# 执行任务
planner.execute_task("grab")

# 监控任务状态
status = planner.get_task_status("grab")
```

任务状态：
- PENDING: 等待执行
- RUNNING: 执行中
- COMPLETED: 已完成
- FAILED: 执行失败
- CANCELLED: 已取消

## 最佳实践

13. 视觉处理
    - 合理设置检测参数
    - 注意图像预处理
    - 考虑光照影响
    - 优化处理性能

14. 动作校准
    - 选择合适的参考动作
    - 定期更新参考数据
    - 合理设置差异阈值
    - 记录校准日志

15. 并行执行
    - 控制并行任务数量
    - 注意资源竞争
    - 实现优雅停止
    - 处理执行异常

16. 消息处理
    - 避免长时间阻塞
    - 合理设置队列大小
    - 实现消息过滤
    - 处理超时情况

17. 状态管理
    - 定义清晰的状态转换
    - 实现状态恢复机制
    - 记录状态变化历史
    - 处理异常状态

18. 任务规划
    - 合理设置任务依赖
    - 实现任务超时处理
    - 提供任务取消机制
    - 记录任务执行日志

19. 动作优化
    - 合理设置速度限制
    - 选择合适的平滑窗口
    - 注意加速度约束
    - 避免过度平滑

20. 动作分析
    - 定期检查异常
    - 关注关键帧
    - 监控性能指标
    - 分析优化效果

21. 版本管理
    - 规范版本命名
    - 添加详细注释
    - 定期清理旧版本
    - 保持版本完整性
