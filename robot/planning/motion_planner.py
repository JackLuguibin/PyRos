from typing import List, Dict, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import logging
from ..model import RobotDynamics, JointState
from .trajectory_generator import TrajectoryGenerator

@dataclass
class PlanningConfig:
    """运动规划配置"""
    planning_time: float = 5.0  # 规划时间限制(秒)
    goal_tolerance: float = 0.01  # 目标容差
    collision_check_resolution: float = 0.1  # 碰撞检测分辨率
    max_planning_attempts: int = 10  # 最大规划尝试次数

class MotionPlanner:
    """运动规划器"""
    
    def __init__(self, config: Dict, robot_dynamics: RobotDynamics,
                 logger: Optional[logging.Logger] = None):
        """初始化运动规划器
        
        Args:
            config: 规划配置
            robot_dynamics: 机器人动力学模型
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('MotionPlanner')
        self.config = PlanningConfig(**config)
        self.dynamics = robot_dynamics
        
        # 创建轨迹生成器
        self.trajectory_generator = TrajectoryGenerator(
            config=config.get('trajectory', {}),
            robot_dynamics=robot_dynamics,
            logger=logger
        )
        
    def plan_motion(self, start_state: Dict[str, JointState],
                   goal_state: Dict[str, JointState]) -> Optional[List[Dict[str, JointState]]]:
        """规划运动
        
        Args:
            start_state: 起始状态
            goal_state: 目标状态
            
        Returns:
            trajectory: 轨迹点列表，失败返回None
        """
        try:
            # 检查起始和目标状态
            if not self._check_state_validity(start_state):
                raise ValueError("起始状态无效")
            if not self._check_state_validity(goal_state):
                raise ValueError("目标状态无效")
                
            # 尝试规划
            for attempt in range(self.config.max_planning_attempts):
                # 生成路径点
                waypoints = self._generate_waypoints(start_state, goal_state)
                
                # 检查路径有效性
                if self._check_path_validity(waypoints):
                    # 生成轨迹
                    trajectory = self.trajectory_generator.generate_trajectory(waypoints)
                    return trajectory
                    
                self.logger.warning(f"规划尝试 {attempt + 1} 失败")
                
            return None
            
        except Exception as e:
            self.logger.error(f"运动规划失败: {str(e)}")
            return None
            
    def _check_state_validity(self, state: Dict[str, JointState]) -> bool:
        """检查状态有效性"""
        try:
            # 检查关节限位
            joint_limits = self.dynamics.get_joint_limits()
            
            for (joint_name, joint_state), (min_pos, max_pos) in zip(
                state.items(), joint_limits
            ):
                if not (min_pos <= joint_state.position <= max_pos):
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"状态检查失败: {str(e)}")
            return False
            
    def _check_path_validity(self, waypoints: List[Dict[str, JointState]]) -> bool:
        """检查路径有效性"""
        try:
            # 检查每个路径点
            for point in waypoints:
                if not self._check_state_validity(point):
                    return False
                    
            # 检查路径连续性
            for i in range(len(waypoints) - 1):
                if not self._check_segment_validity(waypoints[i], waypoints[i + 1]):
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"路径检查失败: {str(e)}")
            return False
            
    def _check_segment_validity(self, start: Dict[str, JointState],
                              end: Dict[str, JointState]) -> bool:
        """检查路径段有效性"""
        try:
            # 计算最大关节运动
            max_motion = max(
                abs(end[joint].position - start[joint].position)
                for joint in start.keys()
            )
            
            # 计算检查点数
            num_checks = max(
                2,
                int(max_motion / self.config.collision_check_resolution)
            )
            
            # 检查中间点
            for i in range(1, num_checks - 1):
                t = i / (num_checks - 1)
                point = {}
                
                for joint in start.keys():
                    position = (1 - t) * start[joint].position + t * end[joint].position
                    point[joint] = JointState(position=position)
                    
                if not self._check_state_validity(point):
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"路径段检查失败: {str(e)}")
            return False
            
    def _generate_waypoints(self, start: Dict[str, JointState],
                          goal: Dict[str, JointState]) -> List[Dict[str, JointState]]:
        """生成路径点"""
        # 简单实现：直接连接起点和终点
        return [start, goal] 