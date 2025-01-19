from typing import Dict, List, Optional
import numpy as np
import logging
from .kinematics import RobotKinematics, Transform, JointState
from ..core.message_broker import MessageBroker
from .dynamics import RobotDynamics

class MotionPlanner:
    """运动规划器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('MotionPlanner')
        self.config = config
        
        # 运动学模块
        self.kinematics = RobotKinematics(config.get('kinematics', {}))
        
        # 消息代理
        self.message_broker = MessageBroker(config.get('message_broker', {}))
        
        # 规划参数
        self.max_velocity = config.get('max_velocity', 1.0)  # rad/s
        self.max_acceleration = config.get('max_acceleration', 2.0)  # rad/s^2
        self.planning_freq = config.get('planning_freq', 100)  # Hz
        self.dt = 1.0 / self.planning_freq
        
        # 动力学模块
        self.dynamics = RobotDynamics(config.get('dynamics', {}))
        
    def plan_joint_motion(self, target_joints: Dict[str, float],
                         current_joints: Dict[str, JointState],
                         duration: float = None) -> List[Dict[str, float]]:
        """关节空间运动规划
        
        Args:
            target_joints: 目标关节角度
            current_joints: 当前关节状态
            duration: 期望运动时间(秒)
            
        Returns:
            关节轨迹点列表
        """
        try:
            # 计算最大运动时间
            max_time = 0.0
            for joint_name, target_pos in target_joints.items():
                if joint_name not in current_joints:
                    continue
                current_pos = current_joints[joint_name].position
                delta = abs(target_pos - current_pos)
                
                # 计算时间
                t1 = np.sqrt(delta / self.max_acceleration)  # 加速时间
                t2 = delta / self.max_velocity  # 匀速时间
                joint_time = min(2 * t1, t1 + t2)
                max_time = max(max_time, joint_time)
                
            # 使用指定时间或计算时间
            motion_time = duration or max_time
            n_points = int(motion_time * self.planning_freq)
            
            # 生成轨迹点
            trajectory = []
            for i in range(n_points + 1):
                t = i * self.dt
                s = t / motion_time  # 归一化时间
                
                # 五次多项式插值
                s3 = s * s * s
                s4 = s3 * s
                s5 = s4 * s
                scale = 10 * s3 - 15 * s4 + 6 * s5
                
                # 计算关节位置
                point = {}
                for joint_name, target_pos in target_joints.items():
                    if joint_name not in current_joints:
                        continue
                    current_pos = current_joints[joint_name].position
                    point[joint_name] = current_pos + \
                                      (target_pos - current_pos) * scale
                                      
                trajectory.append(point)
                
            return trajectory
            
        except Exception as e:
            self.logger.error(f"关节运动规划失败: {str(e)}")
            return []
            
    def plan_cartesian_motion(self, target_pose: Transform,
                            current_joints: Dict[str, JointState],
                            duration: float = None,
                            linear: bool = True) -> List[Dict[str, float]]:
        """笛卡尔空间运动规划
        
        Args:
            target_pose: 目标位姿
            current_joints: 当前关节状态
            duration: 期望运动时间(秒)
            linear: 是否为直线运动
            
        Returns:
            关节轨迹点列表
        """
        try:
            # 获取当前位姿
            current_joints_pos = {
                name: state.position
                for name, state in current_joints.items()
            }
            transforms = self.kinematics.forward_kinematics(current_joints_pos)
            if not transforms:
                return []
                
            current_pose = transforms[f"link_{len(self.kinematics.dh_params)-1}"]
            
            # 计算运动时间
            pos_error = np.linalg.norm(
                target_pose.translation - current_pose.translation
            )
            motion_time = duration or (pos_error / self.max_velocity)
            n_points = int(motion_time * self.planning_freq)
            
            # 生成轨迹点
            trajectory = []
            for i in range(n_points + 1):
                t = i * self.dt
                s = t / motion_time  # 归一化时间
                
                # 五次多项式插值
                s3 = s * s * s
                s4 = s3 * s
                s5 = s4 * s
                scale = 10 * s3 - 15 * s4 + 6 * s5
                
                # 计算中间位姿
                if linear:
                    # 线性插值
                    translation = current_pose.translation + \
                                (target_pose.translation - current_pose.translation) * scale
                    rotation = self._slerp(
                        current_pose.rotation,
                        target_pose.rotation,
                        scale
                    )
                else:
                    # 关节空间插值
                    translation = target_pose.translation
                    rotation = target_pose.rotation
                    
                intermediate_pose = Transform(
                    translation=translation,
                    rotation=rotation
                )
                
                # 逆运动学求解
                joint_solution = self.kinematics.inverse_kinematics(
                    intermediate_pose,
                    current_joints_pos
                )
                if joint_solution is None:
                    self.logger.error(f"逆运动学求解失败: t={t:.2f}")
                    return []
                    
                trajectory.append(joint_solution)
                current_joints_pos = joint_solution
                
            return trajectory
            
        except Exception as e:
            self.logger.error(f"笛卡尔运动规划失败: {str(e)}")
            return []
            
    def execute_trajectory(self, trajectory: List[Dict[str, float]]) -> bool:
        """执行轨迹
        
        Args:
            trajectory: 关节轨迹点列表
            
        Returns:
            执行是否成功
        """
        try:
            for point in trajectory:
                # 发布关节命令
                self.message_broker.publish('motion/joint_command', {
                    'positions': point,
                    'timestamp': time.time()
                })
                
                # 等待执行周期
                time.sleep(self.dt)
                
            return True
            
        except Exception as e:
            self.logger.error(f"轨迹执行失败: {str(e)}")
            return False
            
    def _slerp(self, r1: np.ndarray, r2: np.ndarray, t: float) -> np.ndarray:
        """旋转矩阵球面线性插值"""
        # 转换为四元数
        q1 = self._rotation_to_quaternion(r1)
        q2 = self._rotation_to_quaternion(r2)
        
        # 四元数插值
        dot = np.sum(q1 * q2)
        if dot < 0:
            q2 = -q2
            dot = -dot
            
        if dot > 0.9995:
            # 线性插值
            q = q1 + t * (q2 - q1)
        else:
            # 球面插值
            theta = np.arccos(dot)
            q = (np.sin((1-t)*theta) * q1 + np.sin(t*theta) * q2) / np.sin(theta)
            
        # 归一化
        q = q / np.linalg.norm(q)
        
        # 转换回旋转矩阵
        return self._quaternion_to_rotation(q)
        
    def _rotation_to_quaternion(self, r: np.ndarray) -> np.ndarray:
        """旋转矩阵转四元数"""
        trace = np.trace(r)
        if trace > 0:
            s = np.sqrt(trace + 1.0) * 2
            w = 0.25 * s
            x = (r[2,1] - r[1,2]) / s
            y = (r[0,2] - r[2,0]) / s
            z = (r[1,0] - r[0,1]) / s
        else:
            if r[0,0] > r[1,1] and r[0,0] > r[2,2]:
                s = np.sqrt(1.0 + r[0,0] - r[1,1] - r[2,2]) * 2
                w = (r[2,1] - r[1,2]) / s
                x = 0.25 * s
                y = (r[0,1] + r[1,0]) / s
                z = (r[0,2] + r[2,0]) / s
            elif r[1,1] > r[2,2]:
                s = np.sqrt(1.0 + r[1,1] - r[0,0] - r[2,2]) * 2
                w = (r[0,2] - r[2,0]) / s
                x = (r[0,1] + r[1,0]) / s
                y = 0.25 * s
                z = (r[1,2] + r[2,1]) / s
            else:
                s = np.sqrt(1.0 + r[2,2] - r[0,0] - r[1,1]) * 2
                w = (r[1,0] - r[0,1]) / s
                x = (r[0,2] + r[2,0]) / s
                y = (r[1,2] + r[2,1]) / s
                z = 0.25 * s
        return np.array([w, x, y, z])
        
    def _quaternion_to_rotation(self, q: np.ndarray) -> np.ndarray:
        """四元数转旋转矩阵"""
        w, x, y, z = q
        return np.array([
            [1-2*y*y-2*z*z,  2*x*y-2*w*z,    2*x*z+2*w*y],
            [2*x*y+2*w*z,    1-2*x*x-2*z*z,  2*y*z-2*w*x],
            [2*x*z-2*w*y,    2*y*z+2*w*x,    1-2*x*x-2*y*y]
        ])

    def plan_trajectory(self, start_state: Dict[str, JointState],
                       target_state: Dict[str, JointState]) -> List[Dict[str, float]]:
        """规划轨迹"""
        try:
            trajectory = []
            current_state = start_state.copy()
            
            while not self._reached_target(current_state, target_state):
                # 计算动力学约束
                max_velocity = self._compute_max_velocity(current_state)
                max_acceleration = self._compute_max_acceleration(current_state)
                
                # 生成轨迹点
                next_state = self._generate_trajectory_point(
                    current_state,
                    target_state,
                    max_velocity,
                    max_acceleration
                )
                
                trajectory.append(next_state)
                current_state = next_state
                
            return trajectory
            
        except Exception as e:
            self.logger.error(f"轨迹规划失败: {str(e)}")
            return []