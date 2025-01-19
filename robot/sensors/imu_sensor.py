from typing import Dict, Any, Optional, List
import numpy as np
from dataclasses import dataclass
import logging
import smbus2
from .base_sensor import BaseSensor, SensorConfig

@dataclass
class IMUConfig(SensorConfig):
    """IMU配置"""
    address: int = 0x68  # I2C地址
    bus_number: int = 1  # I2C总线号
    gyro_scale: float = 131.0  # 陀螺仪比例
    accel_scale: float = 16384.0  # 加速度计比例
    enable_kalman: bool = True  # 启用卡尔曼滤波
    
class IMUSensor(BaseSensor):
    """IMU传感器"""
    
    # MPU6050寄存器地址
    PWR_MGMT_1 = 0x6B
    GYRO_XOUT_H = 0x43
    ACCEL_XOUT_H = 0x3B
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """初始化IMU传感器"""
        super().__init__(config, logger)
        self.config = IMUConfig(**config)
        self.bus = None
        
        # 卡尔曼滤波状态
        if self.config.enable_kalman:
            self.kalman_state = np.zeros(6)  # [ax, ay, az, gx, gy, gz]
            self.kalman_p = np.eye(6) * 100
            self.kalman_q = np.eye(6) * 0.1
            self.kalman_r = np.eye(6) * 0.1
        
    def connect(self) -> bool:
        """连接IMU"""
        try:
            # 创建I2C总线
            self.bus = smbus2.SMBus(self.config.bus_number)
            
            # 初始化MPU6050
            self.bus.write_byte_data(self.config.address, self.PWR_MGMT_1, 0)
            
            self.is_connected = True
            self.logger.info("IMU已连接")
            return True
            
        except Exception as e:
            self.logger.error(f"连接IMU失败: {str(e)}")
            return False
            
    def disconnect(self):
        """断开IMU"""
        try:
            if self.bus:
                self.bus.close()
            self.is_connected = False
            self.logger.info("IMU已断开")
            
        except Exception as e:
            self.logger.error(f"断开IMU失败: {str(e)}")
            
    def read(self) -> Dict[str, Any]:
        """读取IMU数据"""
        try:
            # 读取原始数据
            accel_data = self._read_accel()
            gyro_data = self._read_gyro()
            
            # 转换单位
            accel = np.array(accel_data) / self.config.accel_scale
            gyro = np.array(gyro_data) / self.config.gyro_scale
            
            # 卡尔曼滤波
            if self.config.enable_kalman:
                state = np.concatenate([accel, gyro])
                state = self._kalman_filter(state)
                accel = state[:3]
                gyro = state[3:]
                
            return {
                'accelerometer': {
                    'x': float(accel[0]),
                    'y': float(accel[1]),
                    'z': float(accel[2])
                },
                'gyroscope': {
                    'x': float(gyro[0]),
                    'y': float(gyro[1]),
                    'z': float(gyro[2])
                },
                'timestamp': time.time()
            }
            
        except Exception as e:
            self.logger.error(f"读取IMU数据失败: {str(e)}")
            return None
            
    def _read_accel(self) -> List[int]:
        """读取加速度计数据"""
        data = []
        for i in range(0, 6, 2):
            high = self.bus.read_byte_data(self.config.address, self.ACCEL_XOUT_H + i)
            low = self.bus.read_byte_data(self.config.address, self.ACCEL_XOUT_H + i + 1)
            value = (high << 8) | low
            if value > 32767:
                value -= 65536
            data.append(value)
        return data
        
    def _read_gyro(self) -> List[int]:
        """读取陀螺仪数据"""
        data = []
        for i in range(0, 6, 2):
            high = self.bus.read_byte_data(self.config.address, self.GYRO_XOUT_H + i)
            low = self.bus.read_byte_data(self.config.address, self.GYRO_XOUT_H + i + 1)
            value = (high << 8) | low
            if value > 32767:
                value -= 65536
            data.append(value)
        return data
        
    def _kalman_filter(self, measurement: np.ndarray) -> np.ndarray:
        """卡尔曼滤波"""
        # 预测
        x_pred = self.kalman_state
        p_pred = self.kalman_p + self.kalman_q
        
        # 更新
        k = p_pred @ np.linalg.inv(p_pred + self.kalman_r)
        self.kalman_state = x_pred + k @ (measurement - x_pred)
        self.kalman_p = (np.eye(6) - k) @ p_pred
        
        return self.kalman_state 