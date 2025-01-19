from typing import Dict, Optional, Tuple
import numpy as np
from scipy.spatial.transform import Rotation
import logging
from dataclasses import dataclass

@dataclass
class AttitudeState:
    """姿态状态"""
    roll: float = 0.0  # 横滚角(rad)
    pitch: float = 0.0  # 俯仰角(rad)
    yaw: float = 0.0  # 偏航角(rad)
    roll_rate: float = 0.0  # 横滚角速度(rad/s)
    pitch_rate: float = 0.0  # 俯仰角速度(rad/s)
    yaw_rate: float = 0.0  # 偏航角速度(rad/s)

class AttitudeSolver:
    """姿态解算器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('AttitudeSolver')
        self.config = config
        
        # 配置参数
        self.filter_alpha = config.get('filter_alpha', 0.1)  # 滤波系数
        self.gravity = config.get('gravity', 9.81)  # 重力加速度
        self.dt = config.get('dt', 0.01)  # 采样周期
        
        # 姿态状态
        self.state = AttitudeState()
        
        # 传感器偏置
        self.gyro_bias = np.zeros(3)  # 陀螺仪偏置
        self.accel_bias = np.zeros(3)  # 加速度计偏置
        
        # 卡尔曼滤波参数
        self.P = np.eye(6) * 0.1  # 状态协方差
        self.Q = np.eye(6) * config.get('process_noise', 0.001)  # 过程噪声
        self.R = np.eye(6) * config.get('measurement_noise', 0.1)  # 测量噪声
        
    def update(self, imu_data: Dict) -> AttitudeState:
        """更新姿态解算
        
        Args:
            imu_data: IMU数据，包含加速度和角速度
        
        Returns:
            更新后的姿态状态
        """
        try:
            # 提取IMU数据
            accel = np.array([
                imu_data.get('ax', 0.0),
                imu_data.get('ay', 0.0),
                imu_data.get('az', 0.0)
            ])
            
            gyro = np.array([
                imu_data.get('gx', 0.0),
                imu_data.get('gy', 0.0),
                imu_data.get('gz', 0.0)
            ])
            
            # 补偿传感器偏置
            accel = accel - self.accel_bias
            gyro = gyro - self.gyro_bias
            
            # 姿态预测
            predicted_state = self._predict_state(gyro)
            
            # 加速度计观测更新
            measured_angles = self._compute_angles_from_accel(accel)
            
            # 卡尔曼滤波更新
            self._kalman_update(predicted_state, measured_angles)
            
            return self.state
            
        except Exception as e:
            self.logger.error(f"姿态解算错误: {str(e)}")
            return self.state
            
    def _predict_state(self, gyro: np.ndarray) -> AttitudeState:
        """预测姿态状态"""
        # 更新角速度
        predicted = AttitudeState()
        predicted.roll_rate = gyro[0]
        predicted.pitch_rate = gyro[1]
        predicted.yaw_rate = gyro[2]
        
        # 积分得到角度
        predicted.roll = self.state.roll + gyro[0] * self.dt
        predicted.pitch = self.state.pitch + gyro[1] * self.dt
        predicted.yaw = self.state.yaw + gyro[2] * self.dt
        
        return predicted
        
    def _compute_angles_from_accel(self, accel: np.ndarray) -> Tuple[float, float]:
        """从加速度计数据计算俯仰角和横滚角"""
        # 归一化加速度
        norm = np.linalg.norm(accel)
        if norm == 0:
            return 0.0, 0.0
            
        accel = accel / norm
        
        # 计算俯仰角和横滚角
        pitch = np.arcsin(-accel[0])
        roll = np.arctan2(accel[1], accel[2])
        
        return roll, pitch
        
    def _kalman_update(self, predicted: AttitudeState, measured: Tuple[float, float]):
        """卡尔曼滤波更新"""
        # 构建状态向量
        x = np.array([
            predicted.roll,
            predicted.pitch,
            predicted.yaw,
            predicted.roll_rate,
            predicted.pitch_rate,
            predicted.yaw_rate
        ])
        
        # 构建测量向量
        z = np.array([
            measured[0],  # 测量的横滚角
            measured[1],  # 测量的俯仰角
            self.state.yaw,  # 保持原偏航角
            predicted.roll_rate,
            predicted.pitch_rate,
            predicted.yaw_rate
        ])
        
        # 预测步骤
        F = np.eye(6)  # 状态转移矩阵
        F[0:3, 3:6] = np.eye(3) * self.dt
        
        x = F @ x
        self.P = F @ self.P @ F.T + self.Q
        
        # 更新步骤
        H = np.eye(6)  # 观测矩阵
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        
        x = x + K @ (z - H @ x)
        self.P = (np.eye(6) - K @ H) @ self.P
        
        # 更新状态
        self.state.roll = x[0]
        self.state.pitch = x[1]
        self.state.yaw = x[2]
        self.state.roll_rate = x[3]
        self.state.pitch_rate = x[4]
        self.state.yaw_rate = x[5]
        
    def calibrate(self, imu_data: List[Dict], duration: float = 1.0) -> bool:
        """校准传感器偏置
        
        Args:
            imu_data: IMU数据列表
            duration: 校准持续时间(秒)
        
        Returns:
            校准是否成功
        """
        try:
            if not imu_data:
                return False
                
            # 计算平均值
            accel_sum = np.zeros(3)
            gyro_sum = np.zeros(3)
            count = 0
            
            start_time = imu_data[0].get('timestamp', 0)
            for data in imu_data:
                if data.get('timestamp', 0) - start_time > duration:
                    break
                    
                accel_sum += np.array([
                    data.get('ax', 0.0),
                    data.get('ay', 0.0),
                    data.get('az', 0.0)
                ])
                
                gyro_sum += np.array([
                    data.get('gx', 0.0),
                    data.get('gy', 0.0),
                    data.get('gz', 0.0)
                ])
                
                count += 1
                
            if count == 0:
                return False
                
            # 更新偏置
            self.accel_bias = accel_sum / count
            self.gyro_bias = gyro_sum / count
            
            # 补偿重力
            self.accel_bias[2] -= self.gravity
            
            self.logger.info("传感器校准完成")
            return True
            
        except Exception as e:
            self.logger.error(f"传感器校准失败: {str(e)}")
            return False
            
    def reset(self):
        """重置状态"""
        self.state = AttitudeState()
        self.P = np.eye(6) * 0.1
        self.gyro_bias = np.zeros(3)
        self.accel_bias = np.zeros(3) 