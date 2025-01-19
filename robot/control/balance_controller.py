from typing import Dict, Optional, Tuple
import numpy as np
import logging
from .pid_controller import PIDController

class BalanceController:
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """平衡控制器
        
        Args:
            config: 控制器配置
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('BalanceController')
        self.config = config
        
        # 创建姿态控制器
        self.roll_controller = PIDController(**config.get('roll', {}))
        self.pitch_controller = PIDController(**config.get('pitch', {}))
        self.yaw_controller = PIDController(**config.get('yaw', {}))
        
        # 状态变量
        self.target_angles = {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
        self.current_angles = {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
        
        # 补偿参数
        self.gravity_comp = config.get('gravity_compensation', 0.0)
        self.gyro_comp = config.get('gyro_compensation', 0.0)
        
    def update(self, imu_data: Dict, dt: float) -> Dict[str, float]:
        """更新平衡控制
        
        Args:
            imu_data: IMU数据
            dt: 时间间隔
            
        Returns:
            控制输出
        """
        # 更新当前姿态
        self.current_angles = {
            'roll': imu_data.get('roll', 0.0),
            'pitch': imu_data.get('pitch', 0.0),
            'yaw': imu_data.get('yaw', 0.0)
        }
        
        # 计算各轴控制输出
        outputs = {
            'roll': self.roll_controller.compute(
                self.target_angles['roll'],
                self.current_angles['roll'],
                dt
            ),
            'pitch': self.pitch_controller.compute(
                self.target_angles['pitch'],
                self.current_angles['pitch'],
                dt
            ),
            'yaw': self.yaw_controller.compute(
                self.target_angles['yaw'],
                self.current_angles['yaw'],
                dt
            )
        }
        
        # 添加补偿
        outputs = self._apply_compensation(outputs, imu_data)
        
        return outputs
        
    def set_target(self, roll: Optional[float] = None,
                  pitch: Optional[float] = None,
                  yaw: Optional[float] = None):
        """设置目标姿态"""
        if roll is not None:
            self.target_angles['roll'] = roll
        if pitch is not None:
            self.target_angles['pitch'] = pitch
        if yaw is not None:
            self.target_angles['yaw'] = yaw
            
    def _apply_compensation(self, outputs: Dict[str, float],
                          imu_data: Dict) -> Dict[str, float]:
        """应用补偿"""
        # 重力补偿
        outputs['pitch'] += np.sin(np.radians(self.current_angles['pitch'])) * self.gravity_comp
        
        # 陀螺仪补偿
        if 'gyro' in imu_data:
            gyro = imu_data['gyro']
            outputs['roll'] += gyro.get('x', 0.0) * self.gyro_comp
            outputs['pitch'] += gyro.get('y', 0.0) * self.gyro_comp
            outputs['yaw'] += gyro.get('z', 0.0) * self.gyro_comp
            
        return outputs
        
    def reset(self):
        """重置控制器"""
        self.roll_controller.reset()
        self.pitch_controller.reset()
        self.yaw_controller.reset()
        self.target_angles = {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
        
    def get_state(self) -> Dict:
        """获取控制器状态"""
        return {
            'target_angles': self.target_angles.copy(),
            'current_angles': self.current_angles.copy(),
            'roll_stats': self.roll_controller.get_stats(),
            'pitch_stats': self.pitch_controller.get_stats(),
            'yaw_stats': self.yaw_controller.get_stats()
        } 