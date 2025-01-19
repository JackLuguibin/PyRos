# 树莓派舵机机器人控制系统

一个基于树莓派的模块化舵机机器人控制系统，提供灵活的舵机控制、传感器管理和动作组编程功能。该系统采用 Python 开发，支持远程控制和实时监控。

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
```
