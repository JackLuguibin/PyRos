from typing import List, Dict, Optional, Tuple
import numpy as np
from scipy.optimize import minimize
from dataclasses import dataclass
import logging
from .robot_model import RobotDynamics
from .joint_state import JointState

@dataclass
class OptimizationConfig:
    """优化配置"""
    max_iterations: int = 100  # 最大迭代次数
    tolerance: float = 1e-6    # 收敛容差
    constraints_weight: float = 1.0  # 约束权重
    smoothness_weight: float = 0.5   # 平滑权重
    method: str = 'SLSQP'  # 优化方法
    min_waypoint_distance: float = 0.1  # 最小路径点距离
    max_velocity: float = 1.0  # 最大速度
    max_acceleration: float = 2.0  # 最大加速度

class TrajectoryOptimizer:
    """轨迹优化器"""
    
    def __init__(self, config: Dict, robot_dynamics: RobotDynamics, 
                 logger: Optional[logging.Logger] = None):
        """初始化轨迹优化器
        
        Args:
            config: 优化器配置
            robot_dynamics: 机器人动力学模型
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('TrajectoryOptimizer')
        self.config = OptimizationConfig(**config)
        self.dynamics = robot_dynamics
        
    def optimize_trajectory(self, trajectory: List[Dict[str, JointState]]) -> List[Dict[str, JointState]]:
        """优化轨迹
        
        Args:
            trajectory: 原始轨迹点列表
            
        Returns:
            优化后的轨迹点列表
        """
        try:
            # 提取关节角度
            waypoints = np.array([
                [state.position for state in point.values()]
                for point in trajectory
            ])
            
            # 构建约束
            constraints = {
                'joint_limits': self.dynamics.get_joint_limits(),
                'velocity_limits': [self.config.max_velocity] * waypoints.shape[1],
                'acceleration_limits': [self.config.max_acceleration] * waypoints.shape[1]
            }
            
            # 优化轨迹
            optimized_waypoints, info = self.optimize(waypoints, constraints)
            
            if not info['success']:
                self.logger.warning(f"轨迹优化失败: {info.get('error', '未知错误')}")
                return trajectory
                
            # 重建轨迹点列表
            optimized_trajectory = []
            dt = self.config.min_waypoint_distance  # 时间步长
            
            for i, point in enumerate(optimized_waypoints):
                joint_states = {}
                for j, (joint_name, original_state) in enumerate(trajectory[0].items()):
                    # 计算速度和加速度
                    velocity = 0.0
                    acceleration = 0.0
                    
                    if i > 0:
                        velocity = (point[j] - optimized_waypoints[i-1][j]) / dt
                        if i > 1:
                            prev_velocity = (optimized_waypoints[i-1][j] - optimized_waypoints[i-2][j]) / dt
                            acceleration = (velocity - prev_velocity) / dt
                    
                    joint_states[joint_name] = JointState(
                        position=point[j],
                        velocity=velocity,
                        acceleration=acceleration
                    )
                optimized_trajectory.append(joint_states)
                
            return optimized_trajectory
            
        except Exception as e:
            self.logger.error(f"轨迹优化失败: {str(e)}")
            return trajectory
            
    def optimize(self, waypoints: np.ndarray, 
                constraints: Dict) -> Tuple[np.ndarray, Dict]:
        """优化轨迹点
        
        Args:
            waypoints: 路径点数组 (N, dof)
            constraints: 约束字典
                - joint_limits: 关节限位 [(min, max), ...]
                - velocity_limits: 速度限位 [max_vel, ...]
                - acceleration_limits: 加速度限位 [max_acc, ...]
                
        Returns:
            optimized_trajectory: 优化后的轨迹
            info: 优化信息
        """
        try:
            if len(waypoints) < 2:
                return waypoints, {'success': True, 'message': '路径点太少，无需优化'}
                
            # 初始化
            num_points = len(waypoints)
            num_dof = waypoints.shape[1]
            trajectory = waypoints.copy().flatten()
            
            # 构建约束
            bounds = self._get_bounds(num_points, num_dof, constraints)
            opt_constraints = self._get_constraints(num_points, num_dof, constraints)
            
            # 优化
            result = minimize(
                fun=self._objective_function,
                x0=trajectory,
                args=(waypoints, num_points, num_dof),
                method=self.config.method,
                bounds=bounds,
                constraints=opt_constraints,
                options={
                    'maxiter': self.config.max_iterations,
                    'ftol': self.config.tolerance
                }
            )
            
            # 重塑结果
            optimized = result.x.reshape(num_points, num_dof)
            
            # 返回结果
            info = {
                'success': result.success,
                'message': result.message,
                'iterations': result.nit,
                'objective': result.fun
            }
            
            return optimized, info
            
        except Exception as e:
            self.logger.error(f"轨迹优化失败: {str(e)}")
            return waypoints, {'success': False, 'error': str(e)}
            
    def _objective_function(self, x: np.ndarray, waypoints: np.ndarray,
                          num_points: int, num_dof: int) -> float:
        """目标函数"""
        trajectory = x.reshape(num_points, num_dof)
        
        # 路径偏差代价
        deviation_cost = np.sum((trajectory - waypoints) ** 2)
        
        # 平滑性代价
        smoothness_cost = 0.0
        if num_points > 2:
            velocity = np.diff(trajectory, axis=0)
            acceleration = np.diff(velocity, axis=0)
            smoothness_cost = (
                np.sum(velocity ** 2) + 
                self.config.smoothness_weight * np.sum(acceleration ** 2)
            )
            
        # 总代价
        total_cost = (
            self.config.constraints_weight * deviation_cost +
            self.config.smoothness_weight * smoothness_cost
        )
        
        return float(total_cost)
        
    def _get_bounds(self, num_points: int, num_dof: int,
                   constraints: Dict) -> List[Tuple[float, float]]:
        """获取优化边界"""
        joint_limits = constraints.get('joint_limits', [])
        if not joint_limits:
            joint_limits = [(-np.inf, np.inf)] * num_dof
            
        bounds = []
        for _ in range(num_points):
            bounds.extend(joint_limits)
            
        return bounds
        
    def _get_constraints(self, num_points: int, num_dof: int,
                        constraints: Dict) -> List[Dict]:
        """获取优化约束"""
        velocity_limits = constraints.get('velocity_limits', [])
        acceleration_limits = constraints.get('acceleration_limits', [])
        
        constraints_list = []
        
        # 速度约束
        if velocity_limits and num_points > 1:
            def velocity_constraint(x):
                trajectory = x.reshape(num_points, num_dof)
                velocity = np.diff(trajectory, axis=0) / self.config.min_waypoint_distance
                return np.array([
                    limit - np.max(np.abs(velocity[:, i]))
                    for i, limit in enumerate(velocity_limits)
                ])
                
            constraints_list.append({
                'type': 'ineq',
                'fun': velocity_constraint
            })
            
        # 加速度约束
        if acceleration_limits and num_points > 2:
            def acceleration_constraint(x):
                trajectory = x.reshape(num_points, num_dof)
                velocity = np.diff(trajectory, axis=0) / self.config.min_waypoint_distance
                acceleration = np.diff(velocity, axis=0) / self.config.min_waypoint_distance
                return np.array([
                    limit - np.max(np.abs(acceleration[:, i]))
                    for i, limit in enumerate(acceleration_limits)
                ])
                
            constraints_list.append({
                'type': 'ineq',
                'fun': acceleration_constraint
            })
            
        return constraints_list 