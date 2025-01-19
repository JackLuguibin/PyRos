from typing import Dict, Optional, List
import logging
import time
from threading import Lock, Event
from dataclasses import dataclass, field
from collections import deque
from .message_broker import MessageBroker

@dataclass
class RobotStateData:
    """机器人状态数据"""
    timestamp: float = 0.0
    mode: str = 'idle'
    position: Dict = field(default_factory=dict)  # x, y, z
    orientation: Dict = field(default_factory=dict)  # roll, pitch, yaw
    velocity: Dict = field(default_factory=dict)  # linear, angular
    battery: Dict = field(default_factory=dict)  # voltage, current, percentage
    sensors: Dict = field(default_factory=dict)  # 传感器数据
    actuators: Dict = field(default_factory=dict)  # 执行器状态
    errors: List[str] = field(default_factory=list)  # 错误列表

class StateManager:
    """状态管理器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('StateManager')
        self.config = config
        
        # 状态数据
        self.current_state = RobotStateData()
        self.state_history = deque(maxlen=config.get('history_size', 1000))
        self.state_lock = Lock()
        
        # 消息代理
        self.message_broker = MessageBroker(config.get('message_broker', {}))
        
        # 状态监控
        self.monitor_event = Event()
        self.monitor_interval = config.get('monitor_interval', 0.1)  # 100ms
        self.state_validators = {
            'position': self._validate_position,
            'orientation': self._validate_orientation,
            'velocity': self._validate_velocity,
            'battery': self._validate_battery
        }
        
        # 状态限制
        self.limits = config.get('limits', {
            'position': {'x': (-10, 10), 'y': (-10, 10), 'z': (0, 2)},
            'velocity': {'linear': (-2, 2), 'angular': (-1, 1)},
            'battery': {'voltage': (10, 12.6), 'current': (-20, 20)}
        })
        
    def initialize(self):
        """初始化状态管理器"""
        try:
            # 初始化消息代理
            self.message_broker.initialize()
            
            # 注册消息处理器
            self._register_handlers()
            
            # 启动状态监控
            self.monitor_event.set()
            
            self.logger.info("状态管理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"初始化失败: {str(e)}")
            return False
            
    def stop(self):
        """停止状态管理器"""
        self.monitor_event.clear()
        self.message_broker.stop()
        
    def update_state(self, state_data: Dict) -> bool:
        """更新状态
        
        Args:
            state_data: 新的状态数据
            
        Returns:
            更新是否成功
        """
        try:
            # 验证状态数据
            if not self._validate_state(state_data):
                return False
                
            # 更新状态
            with self.state_lock:
                for key, value in state_data.items():
                    setattr(self.current_state, key, value)
                self.current_state.timestamp = time.time()
                
                # 保存历史
                self.state_history.append(self.current_state)
                
            # 发布状态更新消息
            self.message_broker.publish('state/updated', self.get_state())
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新状态失败: {str(e)}")
            return False
            
    def get_state(self) -> Dict:
        """获取当前状态"""
        with self.state_lock:
            return {
                'timestamp': self.current_state.timestamp,
                'mode': self.current_state.mode,
                'position': self.current_state.position,
                'orientation': self.current_state.orientation,
                'velocity': self.current_state.velocity,
                'battery': self.current_state.battery,
                'sensors': self.current_state.sensors,
                'actuators': self.current_state.actuators,
                'errors': self.current_state.errors
            }
            
    def get_history(self, duration: float = None) -> List[Dict]:
        """获取历史状态
        
        Args:
            duration: 历史时长(秒)，None表示全部历史
            
        Returns:
            历史状态列表
        """
        with self.state_lock:
            if duration is None:
                return list(self.state_history)
                
            current_time = time.time()
            return [
                state for state in self.state_history
                if current_time - state.timestamp <= duration
            ]
            
    def add_error(self, error: str):
        """添加错误信息"""
        with self.state_lock:
            if error not in self.current_state.errors:
                self.current_state.errors.append(error)
                self.message_broker.publish('state/error', {'error': error})
                
    def clear_errors(self):
        """清除错误信息"""
        with self.state_lock:
            self.current_state.errors.clear()
            
    def _register_handlers(self):
        """注册消息处理器"""
        self.message_broker.register_handler(
            'sensor/data',
            lambda msg: self.update_state({'sensors': msg})
        )
        self.message_broker.register_handler(
            'actuator/status',
            lambda msg: self.update_state({'actuators': msg})
        )
        self.message_broker.register_handler(
            'battery/status',
            lambda msg: self.update_state({'battery': msg})
        )
        
    def _validate_state(self, state_data: Dict) -> bool:
        """验证状态数据"""
        try:
            for key, value in state_data.items():
                if key in self.state_validators:
                    if not self.state_validators[key](value):
                        self.logger.warning(f"状态验证失败: {key}")
                        return False
            return True
        except Exception as e:
            self.logger.error(f"状态验证错误: {str(e)}")
            return False
            
    def _validate_position(self, position: Dict) -> bool:
        """验证位置数据"""
        limits = self.limits['position']
        return all(
            limits[axis][0] <= position.get(axis, 0) <= limits[axis][1]
            for axis in ('x', 'y', 'z')
        )
        
    def _validate_orientation(self, orientation: Dict) -> bool:
        """验证姿态数据"""
        return all(
            -3.15 <= orientation.get(angle, 0) <= 3.15
            for angle in ('roll', 'pitch', 'yaw')
        )
        
    def _validate_velocity(self, velocity: Dict) -> bool:
        """验证速度数据"""
        limits = self.limits['velocity']
        return (limits['linear'][0] <= velocity.get('linear', 0) <= limits['linear'][1] and
                limits['angular'][0] <= velocity.get('angular', 0) <= limits['angular'][1])
                
    def _validate_battery(self, battery: Dict) -> bool:
        """验证电池数据"""
        limits = self.limits['battery']
        return (limits['voltage'][0] <= battery.get('voltage', 0) <= limits['voltage'][1] and
                limits['current'][0] <= battery.get('current', 0) <= limits['current'][1]) 