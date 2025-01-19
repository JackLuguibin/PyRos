from typing import Dict, Optional, List
import numpy as np
import logging
import time
from dataclasses import dataclass
from .dynamics import RobotDynamics, DynamicsState
from ..kinematics.kinematics import JointState
from ..core.message_broker import MessageBroker
from .robot_model import RobotDynamics

@dataclass
class ControllerConfig:
    """控制器配置"""
    kp: List[float]  # 位置增益
    kd: List[float]  # 速度增益
    ki: List[float]  # 积分增益
    max_effort: List[float]  # 最大力矩/力
    control_freq: float = 1000.0  # 控制频率(Hz)
    integral_limit: float = 1.0  # 积分限幅

class DynamicsController:
    """动力学控制器"""
    
    def __init__(self, config: Dict, robot_dynamics: RobotDynamics,
                 logger: Optional[logging.Logger] = None):
        """初始化控制器
        
        Args:
            config: 控制器配置
            robot_dynamics: 机器人动力学模型
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('DynamicsController')
        self.config = ControllerConfig(**config)
        self.dynamics = robot_dynamics
        
        # 初始化状态
        self.integral_error = np.zeros(len(self.config.kp))
        self.last_error = np.zeros(len(self.config.kp))
        self.dt = 1.0 / self.config.control_freq
        
        # 消息代理
        self.message_broker = MessageBroker(config.get('message_broker', {}))
        
        # 注册消息处理器
        self.message_broker.register_handler(
            'control/joint_target',
            self._handle_joint_target
        )
        
    def compute_control(self, current: Dict[str, JointState],
                       target: Dict[str, JointState]) -> Dict[str, float]:
        """计算控制输出
        
        Args:
            current: 当前关节状态
            target: 目标关节状态
            
        Returns:
            control: 关节控制输出(力矩/力)
        """
        try:
            # 提取状态
            current_pos = np.array([state.position for state in current.values()])
            current_vel = np.array([state.velocity for state in current.values()])
            target_pos = np.array([state.position for state in target.values()])
            target_vel = np.array([state.velocity for state in target.values()])
            
            # 计算误差
            pos_error = target_pos - current_pos
            vel_error = target_vel - current_vel
            
            # 更新积分误差
            self.integral_error += pos_error * self.dt
            self.integral_error = np.clip(
                self.integral_error,
                -self.config.integral_limit,
                self.config.integral_limit
            )
            
            # PID控制
            effort = (
                np.array(self.config.kp) * pos_error +
                np.array(self.config.kd) * vel_error +
                np.array(self.config.ki) * self.integral_error
            )
            
            # 力矩限幅
            effort = np.clip(
                effort,
                -np.array(self.config.max_effort),
                np.array(self.config.max_effort)
            )
            
            # 构建输出
            control = {
                joint_name: float(effort[i])
                for i, joint_name in enumerate(current.keys())
            }
            
            return control
            
        except Exception as e:
            self.logger.error(f"计算控制输出失败: {str(e)}")
            return {name: 0.0 for name in current.keys()}
            
    def reset(self):
        """重置控制器状态"""
        self.integral_error.fill(0.0)
        self.last_error.fill(0.0)
            
    def _handle_joint_target(self, message: Dict):
        """处理关节目标"""
        try:
            # 获取当前状态
            current_state = self._get_current_joints()
            if not current_state:
                return
                
            # 构造目标状态
            target_state = {}
            for joint_name, position in message.get('positions', {}).items():
                target_state[joint_name] = JointState(
                    position=position,
                    velocity=message.get('velocities', {}).get(joint_name, 0.0),
                    effort=0.0
                )
                
            # 计算控制输出
            tau = self.compute_control(current_state, target_state)
            
            # 发布控制命令
            self.message_broker.publish('actuator/torque_command', {
                'torques': {
                    f"joint_{i}": tau[f"joint_{i}"]
                    for i in range(len(tau))
                },
                'timestamp': time.time()
            })
            
        except Exception as e:
            self.logger.error(f"处理关节目标失败: {str(e)}")
            
    def _get_current_joints(self) -> Dict[str, JointState]:
        """获取当前关节状态"""
        try:
            joint_states = self.message_broker.get_message('joint_states')
            if not joint_states:
                return {}
                
            return joint_states.get('states', {}) 