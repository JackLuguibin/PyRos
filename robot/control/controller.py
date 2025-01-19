from typing import Dict, List, Optional, Tuple, Callable
import numpy as np
import logging
from dataclasses import dataclass
from ..config.robot_config import ServoConfig
from .pid_controller import PIDController

@dataclass
class ControlState:
    """控制状态"""
    target_angle: float = 0.0
    current_angle: float = 0.0
    velocity: float = 0.0
    acceleration: float = 0.0
    error: float = 0.0
    integral: float = 0.0
    last_error: float = 0.0
    output: float = 0.0
    timestamp: float = 0.0

class RobotController:
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """机器人控制器
        
        Args:
            config: 控制器配置
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('RobotController')
        self.config = config
        
        # 舵机控制器
        self.servo_controllers: Dict[str, PIDController] = {}
        
        # 控制状态
        self.states: Dict[str, ControlState] = {}
        
        # 控制回调
        self.callbacks: Dict[str, List[Callable]] = {
            'pre_update': [],
            'post_update': [],
            'error': []
        }
        
        # 初始化控制器
        self._init_controllers()
        
    def _init_controllers(self):
        """初始化控制器"""
        for servo_id, servo_config in self.config['servos'].items():
            # 创建PID控制器
            pid_config = {
                'kp': servo_config.get('kp', 1.0),
                'ki': servo_config.get('ki', 0.1),
                'kd': servo_config.get('kd', 0.01),
                'min_output': servo_config.get('min_angle', -90),
                'max_output': servo_config.get('max_angle', 90),
                'deadband': servo_config.get('deadband', 0.5)
            }
            self.servo_controllers[servo_id] = PIDController(**pid_config)
            
            # 初始化状态
            self.states[servo_id] = ControlState()
            
    def update(self, servo_id: str, target: float, 
              current: float, dt: float) -> float:
        """更新控制器
        
        Args:
            servo_id: 舵机ID
            target: 目标角度
            current: 当前角度
            dt: 时间间隔
            
        Returns:
            控制输出
        """
        # 前置处理
        for callback in self.callbacks['pre_update']:
            try:
                callback(servo_id, target, current, dt)
            except Exception as e:
                self.logger.error(f"前置处理错误: {str(e)}")
                self._handle_error(e)
                
        # 获取控制器和状态
        controller = self.servo_controllers.get(servo_id)
        state = self.states.get(servo_id)
        
        if not controller or not state:
            raise ValueError(f"未找到舵机控制器: {servo_id}")
            
        try:
            # 更新状态
            state.target_angle = target
            state.current_angle = current
            state.error = target - current
            
            # 计算速度和加速度
            velocity = (current - state.current_angle) / dt
            acceleration = (velocity - state.velocity) / dt
            
            state.velocity = velocity
            state.acceleration = acceleration
            
            # 计算控制输出
            output = controller.compute(
                target,
                current,
                dt
            )
            
            # 应用约束
            output = self._apply_constraints(
                servo_id,
                output,
                state
            )
            
            # 更新状态
            state.output = output
            state.timestamp = state.timestamp + dt
            
            # 后置处理
            for callback in self.callbacks['post_update']:
                try:
                    callback(servo_id, state)
                except Exception as e:
                    self.logger.error(f"后置处理错误: {str(e)}")
                    self._handle_error(e)
                    
            return output
            
        except Exception as e:
            self.logger.error(f"控制器更新错误: {str(e)}")
            self._handle_error(e)
            return 0.0
            
    def _apply_constraints(self, servo_id: str,
                          output: float,
                          state: ControlState) -> float:
        """应用控制约束
        
        Args:
            servo_id: 舵机ID
            output: 控制输出
            state: 控制状态
            
        Returns:
            约束后的输出
        """
        servo_config = self.config['servos'].get(servo_id)
        if not servo_config:
            return output
            
        # 角度限位
        output = np.clip(
            output,
            servo_config.get('min_angle', -90),
            servo_config.get('max_angle', 90)
        )
        
        # 速度限制
        max_velocity = servo_config.get('max_velocity', 300)
        if abs(state.velocity) > max_velocity:
            output = state.current_angle + np.sign(state.velocity) * max_velocity
            
        # 加速度限制
        max_acceleration = servo_config.get('max_acceleration', 200)
        if abs(state.acceleration) > max_acceleration:
            output = (state.current_angle + 
                     state.velocity * 0.02 +
                     np.sign(state.acceleration) * max_acceleration * 0.0002)
            
        return output
        
    def add_callback(self, event: str, callback: Callable):
        """添加控制回调
        
        Args:
            event: 事件类型 ('pre_update', 'post_update', 'error')
            callback: 回调函数
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)
            
    def remove_callback(self, event: str, callback: Callable):
        """移除控制回调"""
        if event in self.callbacks:
            self.callbacks[event].remove(callback)
            
    def _handle_error(self, error: Exception):
        """处理控制错误"""
        for callback in self.callbacks['error']:
            try:
                callback(error)
            except Exception as e:
                self.logger.error(f"错误处理失败: {str(e)}")
                
    def get_state(self, servo_id: str) -> Optional[ControlState]:
        """获取控制状态"""
        return self.states.get(servo_id)
        
    def reset(self, servo_id: Optional[str] = None):
        """重置控制器
        
        Args:
            servo_id: 指定舵机ID，None表示重置所有
        """
        if servo_id:
            if servo_id in self.servo_controllers:
                self.servo_controllers[servo_id].reset()
                self.states[servo_id] = ControlState()
        else:
            for controller in self.servo_controllers.values():
                controller.reset()
            self.states = {
                servo_id: ControlState()
                for servo_id in self.servo_controllers
            }
            
    def tune_pid(self, servo_id: str,
                kp: Optional[float] = None,
                ki: Optional[float] = None,
                kd: Optional[float] = None):
        """调整PID参数
        
        Args:
            servo_id: 舵机ID
            kp: 比例系数
            ki: 积分系数
            kd: 微分系数
        """
        controller = self.servo_controllers.get(servo_id)
        if controller:
            if kp is not None:
                controller.kp = kp
            if ki is not None:
                controller.ki = ki
            if kd is not None:
                controller.kd = kd
                
    def get_pid_params(self, servo_id: str) -> Optional[Dict[str, float]]:
        """获取PID参数"""
        controller = self.servo_controllers.get(servo_id)
        if controller:
            return {
                'kp': controller.kp,
                'ki': controller.ki,
                'kd': controller.kd
            }
        return None 