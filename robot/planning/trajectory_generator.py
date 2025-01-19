from typing import List, Dict
import numpy as np
import logging

class TrajectoryGenerator:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        
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