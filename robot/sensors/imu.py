import smbus
import math
import time
from .sensor_base import SensorBase
import logging

class IMUSensor(SensorBase):
    # MPU6050 寄存器地址
    PWR_MGMT_1 = 0x6B
    ACCEL_XOUT = 0x3B
    GYRO_XOUT = 0x43
    
    def __init__(self, bus_num: int = 1, device_addr: int = 0x68, logger: logging.Logger = None):
        self.bus = smbus.SMBus(bus_num)
        self.device_addr = device_addr
        self.logger = logger
        super().__init__(0)  # IMU不需要GPIO引脚
        
    def _setup(self):
        """初始化IMU传感器"""
        # 唤醒MPU6050
        self.bus.write_byte_data(self.device_addr, self.PWR_MGMT_1, 0)
        if self.logger:
            self.logger.debug("IMU传感器初始化完成")
            
    def read(self) -> dict:
        """读取IMU数据
        
        Returns:
            包含加速度和角速度的字典
        """
        try:
            # 读取加速度数据
            accel_data = self._read_accel()
            
            # 读取陀螺仪数据
            gyro_data = self._read_gyro()
            
            return {
                'accel': accel_data,
                'gyro': gyro_data
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"读取IMU数据失败: {e}")
            return None
            
    def _read_accel(self) -> dict:
        """读取加速度数据"""
        raw_data = self._read_block(self.ACCEL_XOUT, 6)
        
        accel_x = self._combine_raw(raw_data[0], raw_data[1])
        accel_y = self._combine_raw(raw_data[2], raw_data[3])
        accel_z = self._combine_raw(raw_data[4], raw_data[5])
        
        # 转换为g值
        scale = 16384.0  # ±2g范围
        
        return {
            'x': accel_x / scale,
            'y': accel_y / scale,
            'z': accel_z / scale
        }
        
    def _read_gyro(self) -> dict:
        """读取陀螺仪数据"""
        raw_data = self._read_block(self.GYRO_XOUT, 6)
        
        gyro_x = self._combine_raw(raw_data[0], raw_data[1])
        gyro_y = self._combine_raw(raw_data[2], raw_data[3])
        gyro_z = self._combine_raw(raw_data[4], raw_data[5])
        
        # 转换为度/秒
        scale = 131.0  # ±250度/秒范围
        
        return {
            'x': gyro_x / scale,
            'y': gyro_y / scale,
            'z': gyro_z / scale
        }
        
    def _read_block(self, reg: int, length: int) -> List[int]:
        """读取连续的寄存器数据"""
        return self.bus.read_i2c_block_data(self.device_addr, reg, length)
        
    def _combine_raw(self, msb: int, lsb: int) -> int:
        """合并高低字节并处理符号"""
        value = (msb << 8) + lsb
        if value >= 0x8000:
            value = -((65535 - value) + 1)
        return value
        
    def cleanup(self):
        """清理资源"""
        self.bus.close() 