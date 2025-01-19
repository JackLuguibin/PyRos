from typing import List, Dict, Optional
import numpy as np
from dataclasses import dataclass
import logging
from ..model import RobotDynamics, JointState, TrajectoryOptimizer

@dataclass
class TrajectoryConfig:
    """轨迹生成配置"""
    time_step: float = 0.01  # 时间步长(秒)
    max_velocity: float = 1.0  # 最大速度
    max_acceleration: float = 2.0  # 最大加速度
    min_smoothness: float = 0.1  # 最小平滑度

class TrajectoryGenerator:
    """轨迹生成器"""
    
    def __init__(self, config: Dict, robot_dynamics: RobotDynamics,
                 logger: Optional[logging.Logger] = None):
        """初始化轨迹生成器
        
        Args:
            config: 轨迹生成配置
            robot_dynamics: 机器人动力学模型
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('TrajectoryGenerator')
        self.config = TrajectoryConfig(**config)
        self.dynamics = robot_dynamics
        
        # 创建轨迹优化器
        self.optimizer = TrajectoryOptimizer(
            config=config.get('optimizer', {}),
            robot_dynamics=robot_dynamics,
            logger=logger
        )
        
    def generate_trajectory(self, waypoints: List[Dict[str, JointState]]) -> List[Dict[str, JointState]]:
        """生成轨迹
        
        Args:
            waypoints: 路径点列表
            
        Returns:
            trajectory: 轨迹点列表
        """
        try:
            # 检查路径点
            if len(waypoints) < 2:
                raise ValueError("至少需要两个路径点")
                
            # 插值生成轨迹
            trajectory = self._interpolate_waypoints(waypoints)
            
            # 优化轨迹
            optimized = self.optimizer.optimize_trajectory(trajectory)
            
            return optimized
            
        except Exception as e:
            self.logger.error(f"轨迹生成失败: {str(e)}")
            return waypoints
            
    def _interpolate_waypoints(self, waypoints: List[Dict[str, JointState]]) -> List[Dict[str, JointState]]:
        """插值路径点
        
        Args:
            waypoints: 路径点列表
            
        Returns:
            trajectory: 插值后的轨迹点列表
        """
        trajectory = []
        
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            
            # 计算两点间的最大距离
            max_distance = max(
                abs(end[joint].position - start[joint].position)
                for joint in start.keys()
            )
            
            # 计算插值点数
            num_points = max(
                2,
                int(max_distance / (self.config.max_velocity * self.config.time_step))
            )
            
            # 线性插值
            for j in range(num_points):
                t = j / (num_points - 1)
                point = {}
                
                for joint in start.keys():
                    # 位置插值
                    position = (1 - t) * start[joint].position + t * end[joint].position
                    
                    # 速度计算
                    velocity = (end[joint].position - start[joint].position) / (
                        (num_points - 1) * self.config.time_step
                    )
                    
                    # 加速度计算
                    if j == 0:
                        acceleration = (velocity - start[joint].velocity) / self.config.time_step
                    elif j == num_points - 1:
                        acceleration = (end[joint].velocity - velocity) / self.config.time_step
                    else:
                        acceleration = 0.0
                        
                    point[joint] = JointState(
                        position=position,
                        velocity=velocity,
                        acceleration=acceleration
                    )
                    
                trajectory.append(point)
                
        return trajectory
        
    def generate_linear(self, start: np.ndarray, end: np.ndarray,
                       duration: float, dt: float = 0.01) -> List[np.ndarray]:
        """生成线性轨迹"""
        steps = int(duration / dt)
        trajectory = []
        
        for i in range(steps):
            t = i * dt / duration
            point = start + t * (end - start)
            trajectory.append(point)
            
        return trajectory
        
    def generate_minimum_jerk(self, waypoints: List[np.ndarray],
                            durations: List[float],
                            dt: float = 0.01) -> List[np.ndarray]:
        """生成最小加加速度轨迹"""
        trajectory = []
        
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            duration = durations[i]
            steps = int(duration / dt)
            
            for j in range(steps):
                t = j * dt / duration
                # 计算五次多项式系数
                point = self._minimum_jerk_point(start, end, t)
                trajectory.append(point)
                
        return trajectory
        
    def _minimum_jerk_point(self, start: np.ndarray, end: np.ndarray,
                           t: float) -> np.ndarray:
        """计算最小加加速度轨迹点"""
        # 五次多项式插值
        t3 = t * t * t
        t4 = t3 * t
        t5 = t4 * t
        
        p = start + (end - start) * (10*t3 - 15*t4 + 6*t5)
        return p 

    def generate_trapezoidal(self, start: np.ndarray, end: np.ndarray,
                            max_vel: float, max_acc: float,
                            dt: float = 0.01) -> List[np.ndarray]:
        """生成梯形速度轨迹"""
        distance = np.linalg.norm(end - start)
        direction = (end - start) / distance
        
        # 计算时间参数
        if max_vel * max_vel / max_acc > distance:
            # 三角形速度曲线
            t_acc = np.sqrt(distance / max_acc)
            t_const = 0
        else:
            # 梯形速度曲线
            t_acc = max_vel / max_acc
            t_const = (distance - max_vel * max_vel / max_acc) / max_vel
            
        t_total = 2 * t_acc + t_const
        steps = int(t_total / dt)
        trajectory = []
        
        for i in range(steps):
            t = i * dt
            if t < t_acc:
                # 加速阶段
                s = 0.5 * max_acc * t * t
            elif t < t_acc + t_const:
                # 匀速阶段
                s = max_vel * (t - t_acc / 2)
            else:
                # 减速阶段
                t_rem = t_total - t
                s = distance - 0.5 * max_acc * t_rem * t_rem
            
            point = start + direction * s
            trajectory.append(point)
        
        return trajectory
        
    def generate_scurve(self, start: np.ndarray, end: np.ndarray,
                       max_vel: float, max_acc: float, max_jerk: float,
                       dt: float = 0.01) -> List[np.ndarray]:
        """生成S曲线轨迹（七段式加减速）"""
        distance = np.linalg.norm(end - start)
        direction = (end - start) / distance
        
        # 计算时间参数
        t_j = max_acc / max_jerk  # 加加速时间
        t_a = max_vel / max_acc   # 加速时间
        
        # 完整的S曲线需要7个阶段
        t_total = 2 * (t_j + t_a)  # 简化计算，实际应考虑距离约束
        steps = int(t_total / dt)
        trajectory = []
        
        for i in range(steps):
            t = i * dt
            # 根据七段式S曲线计算位置
            # 具体实现省略，需要分段计算加加速度、加速度、速度和位置
            s = self._calculate_scurve_position(t, t_total, distance,
                                              max_vel, max_acc, max_jerk)
            point = start + direction * s
            trajectory.append(point)
        
        return trajectory
        
    def _calculate_scurve_position(self, t: float, t_total: float,
                                 distance: float, max_vel: float,
                                 max_acc: float, max_jerk: float) -> float:
        """计算S曲线某时刻的位置"""
        # 实现S曲线位置计算
        # 需要分段计算不同阶段的运动参数
        pass 