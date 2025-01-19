from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import logging
from ..core.transform import Transform, TransformManager

@dataclass
class JointState:
    """关节状态"""
    position: float = 0.0  # 位置(rad或m)
    velocity: float = 0.0  # 速度(rad/s或m/s)
    effort: float = 0.0    # 力矩或力(Nm或N)
    
@dataclass
class LinkState:
    """连杆状态"""
    position: np.ndarray = None    # 位置[x, y, z]
    orientation: np.ndarray = None # 姿态四元数[x, y, z, w]
    linear_vel: np.ndarray = None  # 线速度
    angular_vel: np.ndarray = None # 角速度

class RobotKinematics:
    """机器人运动学"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('RobotKinematics')
        self.config = config
        
        # 机器人参数
        self.dh_params = config.get('dh_params', [])  # DH参数
        self.joint_limits = config.get('joint_limits', [])  # 关节限位
        self.link_lengths = config.get('link_lengths', [])  # 连杆长度
        
        # 状态管理
        self.joint_states: Dict[str, JointState] = {}
        self.link_states: Dict[str, LinkState] = {}
        
        # 坐标变换
        self.transform_manager = TransformManager(
            config.get('transform_manager', {}),
            self.logger
        )
        
        # 雅可比矩阵缓存
        self.jacobian_cache: Dict[str, np.ndarray] = {}
        self.cache_valid = False
        
    def update_joint_state(self, joint_name: str, state: JointState) -> bool:
        """更新关节状态
        
        Args:
            joint_name: 关节名称
            state: 关节状态
            
        Returns:
            更新是否成功
        """
        try:
            # 检查关节限位
            if not self._check_joint_limits(joint_name, state.position):
                return False
                
            self.joint_states[joint_name] = state
            self.cache_valid = False
            return True
            
        except Exception as e:
            self.logger.error(f"更新关节状态失败: {str(e)}")
            return False
            
    def forward_kinematics(self, joint_positions: Dict[str, float]) -> Dict[str, Transform]:
        """正向运动学
        
        Args:
            joint_positions: 关节位置字典
            
        Returns:
            各连杆的位姿变换
        """
        try:
            transforms = {}
            current_transform = Transform(
                translation=np.zeros(3),
                rotation=np.eye(3)
            )
            
            # 计算每个连杆的变换
            for i, params in enumerate(self.dh_params):
                joint_name = f"joint_{i}"
                if joint_name not in joint_positions:
                    continue
                    
                # 计算DH变换矩阵
                theta = joint_positions[joint_name] + params.get('theta', 0)
                d = params.get('d', 0)
                a = params.get('a', 0)
                alpha = params.get('alpha', 0)
                
                # 计算变换矩阵
                transform = self._dh_transform(theta, d, a, alpha)
                current_transform = self._chain_transforms(
                    current_transform, transform
                )
                
                # 保存连杆变换
                link_name = f"link_{i}"
                transforms[link_name] = current_transform
                
                # 更新坐标变换管理器
                self.transform_manager.add_transform(
                    f"link_{i-1}" if i > 0 else "base",
                    link_name,
                    current_transform.translation,
                    current_transform.rotation
                )
                
            return transforms
            
        except Exception as e:
            self.logger.error(f"正向运动学计算失败: {str(e)}")
            return {}
            
    def inverse_kinematics(self, target_pose: Transform,
                          initial_guess: Optional[Dict[str, float]] = None,
                          max_iter: int = 100,
                          tolerance: float = 1e-3) -> Optional[Dict[str, float]]:
        """逆向运动学
        
        Args:
            target_pose: 目标位姿
            initial_guess: 初始关节角度
            max_iter: 最大迭代次数
            tolerance: 收敛阈值
            
        Returns:
            关节角度解
        """
        try:
            if initial_guess is None:
                initial_guess = {
                    f"joint_{i}": 0.0
                    for i in range(len(self.dh_params))
                }
                
            # 当前关节角度
            current_joints = initial_guess.copy()
            
            for _ in range(max_iter):
                # 计算当前位姿
                current_pose = self.forward_kinematics(current_joints)
                if not current_pose:
                    return None
                    
                # 计算位姿误差
                pose_error = self._compute_pose_error(
                    target_pose,
                    current_pose[f"link_{len(self.dh_params)-1}"]
                )
                
                # 检查收敛
                if np.linalg.norm(pose_error) < tolerance:
                    return current_joints
                    
                # 计算雅可比矩阵
                jacobian = self._compute_jacobian(current_joints)
                if jacobian is None:
                    return None
                    
                # 计算关节角度增量
                try:
                    delta_theta = np.linalg.pinv(jacobian) @ pose_error
                except np.linalg.LinAlgError:
                    self.logger.error("雅可比矩阵求逆失败")
                    return None
                    
                # 更新关节角度
                for i, delta in enumerate(delta_theta):
                    joint_name = f"joint_{i}"
                    current_joints[joint_name] += delta
                    
                    # 检查关节限位
                    if not self._check_joint_limits(joint_name, current_joints[joint_name]):
                        return None
                        
            self.logger.warning("逆运动学未收敛")
            return None
            
        except Exception as e:
            self.logger.error(f"逆运动学计算失败: {str(e)}")
            return None
            
    def compute_jacobian(self, joint_positions: Dict[str, float]) -> Optional[np.ndarray]:
        """计算雅可比矩阵
        
        Args:
            joint_positions: 关节位置
            
        Returns:
            6xn雅可比矩阵
        """
        try:
            # 检查缓存
            cache_key = tuple(joint_positions.items())
            if self.cache_valid and cache_key in self.jacobian_cache:
                return self.jacobian_cache[cache_key]
                
            # 计算雅可比矩阵
            jacobian = self._compute_jacobian(joint_positions)
            
            # 更新缓存
            if jacobian is not None:
                self.jacobian_cache[cache_key] = jacobian
                self.cache_valid = True
                
            return jacobian
            
        except Exception as e:
            self.logger.error(f"计算雅可比矩阵失败: {str(e)}")
            return None
            
    def _compute_jacobian(self, joint_positions: Dict[str, float]) -> Optional[np.ndarray]:
        """计算雅可比矩阵的具体实现"""
        try:
            n_joints = len(self.dh_params)
            jacobian = np.zeros((6, n_joints))
            
            # 计算每个关节的雅可比列
            transforms = self.forward_kinematics(joint_positions)
            end_effector = transforms[f"link_{n_joints-1}"]
            
            for i in range(n_joints):
                # 计算关节轴方向
                if i == 0:
                    joint_axis = np.array([0, 0, 1])  # 基座关节
                else:
                    prev_transform = transforms[f"link_{i-1}"]
                    joint_axis = prev_transform.rotation @ np.array([0, 0, 1])
                    
                # 计算到末端执行器的向量
                joint_pos = transforms[f"link_{i}"].translation
                end_pos = end_effector.translation
                r = end_pos - joint_pos
                
                # 计算线速度分量
                jacobian[0:3, i] = np.cross(joint_axis, r)
                
                # 计算角速度分量
                jacobian[3:6, i] = joint_axis
                
            return jacobian
            
        except Exception as e:
            self.logger.error(f"计算雅可比矩阵失败: {str(e)}")
            return None
            
    def _dh_transform(self, theta: float, d: float,
                     a: float, alpha: float) -> Transform:
        """计算DH变换矩阵"""
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)
        cos_alpha = np.cos(alpha)
        sin_alpha = np.sin(alpha)
        
        rotation = np.array([
            [cos_theta, -sin_theta * cos_alpha,  sin_theta * sin_alpha],
            [sin_theta,  cos_theta * cos_alpha, -cos_theta * sin_alpha],
            [0,         sin_alpha,               cos_alpha]
        ])
        
        translation = np.array([
            a * cos_theta,
            a * sin_theta,
            d
        ])
        
        return Transform(translation=translation, rotation=rotation)
        
    def _chain_transforms(self, t1: Transform, t2: Transform) -> Transform:
        """链接两个变换"""
        rotation = t1.rotation @ t2.rotation
        translation = t1.rotation @ t2.translation + t1.translation
        return Transform(translation=translation, rotation=rotation)
        
    def _compute_pose_error(self, target: Transform, current: Transform) -> np.ndarray:
        """计算位姿误差"""
        # 位置误差
        pos_error = target.translation - current.translation
        
        # 姿态误差
        rot_error = self._rotation_error(target.rotation, current.rotation)
        
        return np.concatenate([pos_error, rot_error])
        
    def _rotation_error(self, target_rot: np.ndarray,
                       current_rot: np.ndarray) -> np.ndarray:
        """计算旋转误差"""
        error_rot = target_rot @ current_rot.T
        return np.array([
            error_rot[2, 1] - error_rot[1, 2],
            error_rot[0, 2] - error_rot[2, 0],
            error_rot[1, 0] - error_rot[0, 1]
        ]) / 2.0
        
    def _check_joint_limits(self, joint_name: str, position: float) -> bool:
        """检查关节限位"""
        try:
            joint_idx = int(joint_name.split('_')[1])
            if joint_idx >= len(self.joint_limits):
                return True
                
            limits = self.joint_limits[joint_idx]
            return limits[0] <= position <= limits[1]
            
        except Exception:
            return True  # 解析失败时默认通过 