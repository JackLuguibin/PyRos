from typing import Dict, Optional
import numpy as np
import logging
import time
from dataclasses import dataclass
from .dynamics import RobotDynamics, DynamicsState
from ..kinematics.kinematics import JointState
from ..core.message_broker import MessageBroker

@dataclass
class ControllerGains:
    """控制器增益"""
    kp: np.ndarray  # 位置增益
    kd: np.ndarray  # 速度增益
    ki: np.ndarray  # 积分增益

class DynamicsController:
    """动力学控制器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('DynamicsController')
        self.config = config
        
        # 动力学模型
        self.dynamics = RobotDynamics(config.get('dynamics', {}))
        
        # 消息代理
        self.message_broker = MessageBroker(config.get('message_broker', {}))
        
        # 控制器参数
        gains_config = config.get('gains', {})
        self.gains = ControllerGains(
            kp=np.array(gains_config.get('kp', [100.0] * 6)),
            kd=np.array(gains_config.get('kd', [20.0] * 6)),
            ki=np.array(gains_config.get('ki', [1.0] * 6))
        )
        
        # 控制状态
        self.integral_error = np.zeros(6)
        self.last_time = time.time()
        self.dt = 0.001  # 1kHz控制频率
        
        # 注册消息处理器
        self.message_broker.register_handler(
            'control/joint_target',
            self._handle_joint_target
        )
        
    def compute_control(self, current_state: Dict[str, JointState],
                       target_state: Dict[str, JointState]) -> np.ndarray:
        """计算控制输出
        
        Args:
            current_state: 当前关节状态
            target_state: 目标关节状态
            
        Returns:
            关节力矩命令
        """
        try:
            # 计算时间间隔
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
            
            # 提取状态
            q = np.array([state.position for state in current_state.values()])
            q_dot = np.array([state.velocity for state in current_state.values()])
            
            q_d = np.array([state.position for state in target_state.values()])
            q_d_dot = np.array([state.velocity for state in target_state.values()])
            
            # 计算误差
            error = q_d - q
            error_dot = q_d_dot - q_dot
            
            # 更新积分误差
            self.integral_error += error * dt
            
            # 计算期望加速度
            q_d_ddot = (self.gains.kp * error + 
                       self.gains.kd * error_dot +
                       self.gains.ki * self.integral_error)
            
            # 计算逆动力学
            tau = self.dynamics.compute_inverse_dynamics(
                current_state,
                q_d_ddot
            )
            
            return tau
            
        except Exception as e:
            self.logger.error(f"计算控制输出失败: {str(e)}")
            return np.zeros(len(current_state))
            
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
                    f"joint_{i}": tau[i]
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
            
        except Exception as e:
            self.logger.error(f"获取关节状态失败: {str(e)}")
            return {} 