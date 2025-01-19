from typing import Dict, List, Optional
import numpy as np
import logging
from .motion_controller import MotionController, TrajectoryGenerator
from .pid_controller import PIDController

class TrajectoryController(MotionController):
    def __init__(self, config: Dict,
                 trajectory_generator: TrajectoryGenerator,
                 logger: Optional[logging.Logger] = None):
        """轨迹控制器
        
        Args:
            config: 控制器配置
            trajectory_generator: 轨迹生成器
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('TrajectoryController')
        self.config = config
        self.generator = trajectory_generator
        
        # 创建关节控制器
        self.joint_controllers = {}
        for joint_id, joint_config in config.get('joints', {}).items():
            self.joint_controllers[joint_id] = PIDController(**joint_config)
            
        # 轨迹缓存
        self.trajectory = []
        self.current_point = 0
        
        # 状态变量
        self.target_state = {}
        self.current_state = {}
        
    def update(self, state: Dict, dt: float) -> Dict:
        """更新控制
        
        Args:
            state: 当前状态
            dt: 时间间隔
            
        Returns:
            控制输出
        """
        self.current_state = state
        outputs = {}
        
        # 获取目标状态
        if self.trajectory and self.current_point < len(self.trajectory):
            self.target_state = self.trajectory[self.current_point]
            self.current_point += 1
        
        # 计算各关节控制输出
        for joint_id, controller in self.joint_controllers.items():
            if joint_id in self.target_state and joint_id in state:
                outputs[joint_id] = controller.compute(
                    self.target_state[joint_id],
                    state[joint_id],
                    dt
                )
                
        return outputs
        
    def set_trajectory(self, waypoints: List[Dict], durations: List[float]):
        """设置轨迹
        
        Args:
            waypoints: 路径点列表
            durations: 时间间隔列表
        """
        self.trajectory = self.generator.interpolate(waypoints, durations)
        self.current_point = 0
        
    def reset(self):
        """重置控制器"""
        for controller in self.joint_controllers.values():
            controller.reset()
        self.trajectory = []
        self.current_point = 0
        
    def get_state(self) -> Dict:
        """获取控制器状态"""
        return {
            'target_state': self.target_state.copy(),
            'current_state': self.current_state.copy(),
            'trajectory_progress': self.current_point / len(self.trajectory) if self.trajectory else 0,
            'joint_stats': {
                joint_id: controller.get_stats()
                for joint_id, controller in self.joint_controllers.items()
            }
        } 