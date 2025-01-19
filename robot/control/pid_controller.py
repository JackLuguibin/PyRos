from typing import Optional, Dict
import numpy as np
import logging

class PIDController:
    def __init__(self, kp: float = 1.0, ki: float = 0.0, kd: float = 0.0,
                 min_output: float = -float('inf'),
                 max_output: float = float('inf'),
                 deadband: float = 0.0,
                 logger: Optional[logging.Logger] = None):
        """PID控制器
        
        Args:
            kp: 比例系数
            ki: 积分系数
            kd: 微分系数
            min_output: 输出下限
            max_output: 输出上限
            deadband: 死区范围
            logger: 日志记录器
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.min_output = min_output
        self.max_output = max_output
        self.deadband = deadband
        self.logger = logger or logging.getLogger('PIDController')
        
        # 控制状态
        self.last_error = 0.0
        self.integral = 0.0
        self.last_output = 0.0
        
        # 积分限幅
        self.integral_min = min_output / ki if ki != 0 else -float('inf')
        self.integral_max = max_output / ki if ki != 0 else float('inf')
        
        # 性能统计
        self.stats = {
            'max_error': 0.0,
            'min_error': 0.0,
            'total_error': 0.0,
            'samples': 0,
            'overshoots': 0
        }
        
        # 自适应控制参数
        self.adaptive_config = {
            'enabled': False,
            'learning_rate': 0.01,
            'min_kp': 0.1,
            'max_kp': 10.0,
            'min_ki': 0.0,
            'max_ki': 1.0,
            'min_kd': 0.0,
            'max_kd': 1.0
        }
        
        # 前馈控制参数
        self.feedforward_config = {
            'enabled': False,
            'gain': 1.0,
            'model': None  # 可以是函数或查找表
        }
        
        # 抗干扰参数
        self.disturbance_config = {
            'enabled': False,
            'filter_size': 5,
            'threshold': 1.0,
            'recovery_rate': 0.1
        }
        self.error_history = []
        
        # 模糊控制参数
        self.fuzzy_config = {
            'enabled': False,
            'rules': [],
            'error_sets': {
                'NB': (-float('inf'), -3),
                'NM': (-3, -1),
                'NS': (-1, 0),
                'ZO': (-0.1, 0.1),
                'PS': (0, 1),
                'PM': (1, 3),
                'PB': (3, float('inf'))
            },
            'output_sets': {
                'NB': -1.0,
                'NM': -0.6,
                'NS': -0.3,
                'ZO': 0.0,
                'PS': 0.3,
                'PM': 0.6,
                'PB': 1.0
            }
        }
        
    def compute(self, target: float, current: float, dt: float) -> float:
        """增强的PID计算"""
        error = target - current
        
        # 更新误差历史
        self.error_history.append(error)
        if len(self.error_history) > self.disturbance_config['filter_size']:
            self.error_history.pop(0)
            
        # 干扰检测和处理
        if self.disturbance_config['enabled']:
            error = self._handle_disturbance(error)
            
        # 模糊控制
        if self.fuzzy_config['enabled']:
            fuzzy_output = self._compute_fuzzy(error)
            output = fuzzy_output * self.max_output
        else:
            # 自适应参数调整
            if self.adaptive_config['enabled']:
                self._adapt_parameters(error, dt)
                
            # 计算PID输出
            output = self._compute_pid(error, dt)
            
            # 添加前馈控制
            if self.feedforward_config['enabled']:
                output += self._compute_feedforward(target)
                
        # 输出限幅
        output = np.clip(output, self.min_output, self.max_output)
        
        return output
        
    def _compute_pid(self, error: float, dt: float) -> float:
        """基础PID计算"""
        if abs(error) < self.deadband:
            self.integral = 0
            self.last_error = 0
            return 0.0
            
        self.integral += error * dt
        self.integral = np.clip(
            self.integral,
            self.integral_min,
            self.integral_max
        )
        
        derivative = (error - self.last_error) / dt if dt > 0 else 0
        
        output = (
            self.kp * error +
            self.ki * self.integral +
            self.kd * derivative
        )
        
        self.last_error = error
        return output
        
    def _adapt_parameters(self, error: float, dt: float):
        """自适应参数调整"""
        if not self.adaptive_config['enabled']:
            return
            
        # 基于误差变化调整参数
        error_change = (error - self.last_error) / dt if dt > 0 else 0
        
        # 调整Kp
        if abs(error) > self.deadband:
            self.kp += self.adaptive_config['learning_rate'] * abs(error)
            self.kp = np.clip(
                self.kp,
                self.adaptive_config['min_kp'],
                self.adaptive_config['max_kp']
            )
            
        # 调整Ki
        if abs(self.integral) > self.deadband:
            self.ki += self.adaptive_config['learning_rate'] * abs(self.integral)
            self.ki = np.clip(
                self.ki,
                self.adaptive_config['min_ki'],
                self.adaptive_config['max_ki']
            )
            
        # 调整Kd
        if abs(error_change) > self.deadband:
            self.kd += self.adaptive_config['learning_rate'] * abs(error_change)
            self.kd = np.clip(
                self.kd,
                self.adaptive_config['min_kd'],
                self.adaptive_config['max_kd']
            )
            
    def _handle_disturbance(self, error: float) -> float:
        """干扰处理"""
        if not self.disturbance_config['enabled']:
            return error
            
        # 计算移动平均
        avg_error = np.mean(self.error_history)
        
        # 检测突变
        if abs(error - avg_error) > self.disturbance_config['threshold']:
            # 平滑处理
            error = avg_error + (error - avg_error) * self.disturbance_config['recovery_rate']
            
        return error
        
    def _compute_feedforward(self, target: float) -> float:
        """计算前馈控制输出"""
        if not self.feedforward_config['enabled']:
            return 0.0
            
        if callable(self.feedforward_config['model']):
            # 使用模型函数
            ff_output = self.feedforward_config['model'](target)
        elif isinstance(self.feedforward_config['model'], dict):
            # 使用查找表
            ff_output = self.feedforward_config['model'].get(target, 0.0)
        else:
            ff_output = target
            
        return ff_output * self.feedforward_config['gain']
        
    def _compute_fuzzy(self, error: float) -> float:
        """计算模糊控制输出"""
        if not self.fuzzy_config['enabled']:
            return 0.0
            
        # 计算隶属度
        memberships = {}
        for set_name, (low, high) in self.fuzzy_config['error_sets'].items():
            if error <= low:
                memberships[set_name] = 0.0
            elif error >= high:
                memberships[set_name] = 0.0
            else:
                # 三角隶属度函数
                center = (low + high) / 2
                if error < center:
                    memberships[set_name] = (error - low) / (center - low)
                else:
                    memberships[set_name] = (high - error) / (high - center)
                    
        # 应用模糊规则
        outputs = []
        weights = []
        
        for rule in self.fuzzy_config['rules']:
            condition = rule['if']
            action = rule['then']
            
            # 计算规则权重
            weight = memberships.get(condition, 0.0)
            if weight > 0:
                outputs.append(self.fuzzy_config['output_sets'][action])
                weights.append(weight)
                
        # 计算加权平均
        if weights:
            return np.average(outputs, weights=weights)
        return 0.0
        
    def configure_adaptive(self, config: Dict):
        """配置自适应控制"""
        self.adaptive_config.update(config)
        
    def configure_feedforward(self, config: Dict):
        """配置前馈控制"""
        self.feedforward_config.update(config)
        
    def configure_disturbance(self, config: Dict):
        """配置抗干扰"""
        self.disturbance_config.update(config)
        
    def configure_fuzzy(self, config: Dict):
        """配置模糊控制"""
        self.fuzzy_config.update(config)
        
    def add_fuzzy_rule(self, condition: str, action: str):
        """添加模糊规则"""
        self.fuzzy_config['rules'].append({
            'if': condition,
            'then': action
        })
        
    def reset(self):
        """重置控制器状态"""
        self.last_error = 0.0
        self.integral = 0.0
        self.last_output = 0.0
        self.stats = {
            'max_error': 0.0,
            'min_error': 0.0,
            'total_error': 0.0,
            'samples': 0,
            'overshoots': 0
        }
        
    def get_stats(self) -> dict:
        """获取性能统计
        
        Returns:
            统计数据字典
        """
        if self.stats['samples'] > 0:
            avg_error = self.stats['total_error'] / self.stats['samples']
        else:
            avg_error = 0.0
            
        return {
            'max_error': self.stats['max_error'],
            'min_error': self.stats['min_error'],
            'avg_error': avg_error,
            'samples': self.stats['samples'],
            'overshoots': self.stats['overshoots']
        }
        
    def _update_stats(self, error: float):
        """更新统计数据"""
        self.stats['samples'] += 1
        self.stats['total_error'] += abs(error)
        self.stats['max_error'] = max(self.stats['max_error'], error)
        self.stats['min_error'] = min(self.stats['min_error'], error)
        
    def _check_overshoot(self, error: float, last_error: float) -> bool:
        """检测过冲
        
        当误差变号且幅值增大时认为发生过冲
        """
        return (error * last_error < 0 and 
                abs(error) > abs(last_error))
                
    def tune(self, kp: Optional[float] = None,
            ki: Optional[float] = None,
            kd: Optional[float] = None):
        """调整PID参数
        
        Args:
            kp: 新的比例系数
            ki: 新的积分系数
            kd: 新的微分系数
        """
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
            # 更新积分限幅
            self.integral_min = self.min_output / ki if ki != 0 else -float('inf')
            self.integral_max = self.max_output / ki if ki != 0 else float('inf')
        if kd is not None:
            self.kd = kd
            
        # 重置状态
        self.reset()
        
    def set_output_limits(self, min_output: float, max_output: float):
        """设置输出限幅
        
        Args:
            min_output: 输出下限
            max_output: 输出上限
        """
        self.min_output = min_output
        self.max_output = max_output
        
        # 更新积分限幅
        if self.ki != 0:
            self.integral_min = min_output / self.ki
            self.integral_max = max_output / self.ki
            
    def set_deadband(self, deadband: float):
        """设置死区范围
        
        Args:
            deadband: 新的死区范围
        """
        self.deadband = deadband
        
    def get_parameters(self) -> dict:
        """获取控制器参数
        
        Returns:
            参数字典
        """
        return {
            'kp': self.kp,
            'ki': self.ki,
            'kd': self.kd,
            'min_output': self.min_output,
            'max_output': self.max_output,
            'deadband': self.deadband
        }