import numpy as np
from typing import Tuple
import math
import time

class AttitudeSolver:
    def __init__(self):
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0
        self.last_time = time.time()
        
        # 卡尔曼滤波参数
        self.Q_angle = 0.001
        self.Q_gyro = 0.003
        self.R_angle = 0.5
        
        self.Pk = np.zeros((2, 2))
        self.Pdot = np.zeros((4,))
        self.K = np.zeros((2,))
        
    def update(self, accel_data: dict, gyro_data: dict):
        """更新姿态解算
        
        Args:
            accel_data: 加速度数据 {'x':, 'y':, 'z':}
            gyro_data: 陀螺仪数据 {'x':, 'y':, 'z':}
        """
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # 计算欧拉角
        accel_pitch = math.atan2(accel_data['x'], 
                                math.sqrt(accel_data['y']**2 + accel_data['z']**2))
        accel_roll = math.atan2(-accel_data['y'], -accel_data['z'])
        
        # 卡尔曼滤波
        self.pitch = self._kalman_filter(accel_pitch, gyro_data['y'], dt)
        self.roll = self._kalman_filter(accel_roll, gyro_data['x'], dt)
        
        # 使用陀螺仪积分计算偏航角
        self.yaw += gyro_data['z'] * dt
        
    def _kalman_filter(self, angle_m: float, gyro_m: float, dt: float) -> float:
        """卡尔曼滤波器
        
        Args:
            angle_m: 测量的角度
            gyro_m: 测量的角速度
            dt: 时间间隔
            
        Returns:
            滤波后的角度
        """
        # 预测
        angle_pred = angle_m + gyro_m * dt
        
        # 更新Pk
        self.Pdot[0] = self.Q_angle - self.Pk[0][1] - self.Pk[1][0]
        self.Pdot[1] = -self.Pk[1][1]
        self.Pdot[2] = -self.Pk[1][1]
        self.Pdot[3] = self.Q_gyro
        
        self.Pk[0][0] += self.Pdot[0] * dt
        self.Pk[0][1] += self.Pdot[1] * dt
        self.Pk[1][0] += self.Pdot[2] * dt
        self.Pk[1][1] += self.Pdot[3] * dt
        
        # 计算卡尔曼增益
        S = self.Pk[0][0] + self.R_angle
        self.K[0] = self.Pk[0][0] / S
        self.K[1] = self.Pk[1][0] / S
        
        # 更新估计值
        angle_error = angle_m - angle_pred
        angle_est = angle_pred + self.K[0] * angle_error
        gyro_est = gyro_m + self.K[1] * angle_error
        
        # 更新误差协方差矩阵
        self.Pk[0][0] -= self.K[0] * self.Pk[0][0]
        self.Pk[0][1] -= self.K[0] * self.Pk[0][1]
        self.Pk[1][0] -= self.K[1] * self.Pk[0][0]
        self.Pk[1][1] -= self.K[1] * self.Pk[0][1]
        
        return angle_est
        
    def get_attitude(self) -> Tuple[float, float, float]:
        """获取当前姿态角"""
        return self.pitch, self.roll, self.yaw 