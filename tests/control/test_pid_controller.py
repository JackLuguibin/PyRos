import pytest
import numpy as np
from robot.control.pid_controller import PIDController

class TestPIDController:
    @pytest.fixture
    def pid(self):
        """创建基础PID控制器"""
        return PIDController(
            kp=1.0,
            ki=0.1,
            kd=0.01,
            min_output=-90,
            max_output=90,
            deadband=0.5
        )
        
    def test_basic_pid_control(self, pid):
        """测试基本PID控制功能"""
        # 测试目标跟踪
        output = pid.compute(target=45.0, current=0.0, dt=0.02)
        assert 0 < output <= 90
        
        # 测试死区
        output = pid.compute(target=0.2, current=0.0, dt=0.02)
        assert output == 0.0
        
        # 测试输出限幅
        output = pid.compute(target=180.0, current=0.0, dt=0.02)
        assert output == 90.0
        
    def test_adaptive_control(self, pid):
        """测试自适应控制功能"""
        # 配置自适应控制
        pid.configure_adaptive({
            'enabled': True,
            'learning_rate': 0.01
        })
        
        # 记录初始参数
        initial_kp = pid.kp
        
        # 执行多次控制
        for _ in range(10):
            pid.compute(target=45.0, current=0.0, dt=0.02)
            
        # 验证参数自适应
        assert pid.kp != initial_kp
        assert pid.adaptive_config['min_kp'] <= pid.kp <= pid.adaptive_config['max_kp']
        
    def test_disturbance_rejection(self, pid):
        """测试抗干扰能力"""
        # 配置抗干扰
        pid.configure_disturbance({
            'enabled': True,
            'filter_size': 5,
            'threshold': 1.0,
            'recovery_rate': 0.1
        })
        
        # 正常控制
        normal_output = pid.compute(target=45.0, current=0.0, dt=0.02)
        
        # 添加干扰
        disturbed_output = pid.compute(target=45.0, current=10.0, dt=0.02)
        
        # 验证干扰抑制
        assert abs(disturbed_output - normal_output) < abs(45.0 - 10.0)
        
    def test_feedforward_control(self, pid):
        """测试前馈控制"""
        # 配置前馈控制
        def model_func(target):
            return target * 0.1
            
        pid.configure_feedforward({
            'enabled': True,
            'gain': 0.5,
            'model': model_func
        })
        
        # 计算输出
        output = pid.compute(target=45.0, current=0.0, dt=0.02)
        
        # 验证前馈补偿
        assert output > pid._compute_pid(45.0 - 0.0, 0.02)
        
    def test_fuzzy_control(self, pid):
        """测试模糊控制"""
        # 配置模糊控制
        pid.configure_fuzzy({
            'enabled': True
        })
        
        # 添加模糊规则
        pid.add_fuzzy_rule('NB', 'PB')  # 负大误差->正大输出
        pid.add_fuzzy_rule('ZO', 'ZO')  # 零误差->零输出
        pid.add_fuzzy_rule('PB', 'NB')  # 正大误差->负大输出
        
        # 测试不同误差区间
        large_neg_output = pid.compute(target=-45.0, current=0.0, dt=0.02)
        zero_output = pid.compute(target=0.0, current=0.0, dt=0.02)
        large_pos_output = pid.compute(target=45.0, current=0.0, dt=0.02)
        
        # 验证模糊控制效果
        assert large_neg_output < 0
        assert abs(zero_output) < 1.0
        assert large_pos_output > 0
        
    def test_parameter_limits(self, pid):
        """测试参数限制"""
        # 设置极限参数
        pid.tune(kp=100.0, ki=10.0, kd=1.0)
        
        # 验证输出限幅
        output = pid.compute(target=180.0, current=0.0, dt=0.02)
        assert -90 <= output <= 90
        
        # 验证积分限幅
        for _ in range(10):
            output = pid.compute(target=180.0, current=0.0, dt=0.02)
            assert -90 <= output <= 90
            
    def test_reset_functionality(self, pid):
        """测试重置功能"""
        # 执行一些控制
        pid.compute(target=45.0, current=0.0, dt=0.02)
        
        # 重置控制器
        pid.reset()
        
        # 验证状态重置
        assert pid.last_error == 0.0
        assert pid.integral == 0.0
        assert pid.last_output == 0.0
        assert pid.stats['samples'] == 0
        
    def test_performance_stats(self, pid):
        """测试性能统计"""
        # 执行多次控制
        for i in range(10):
            pid.compute(target=45.0, current=float(i), dt=0.02)
            
        # 获取统计数据
        stats = pid.get_stats()
        
        # 验证统计结果
        assert stats['samples'] == 10
        assert stats['max_error'] > 0
        assert stats['min_error'] < 45.0
        assert stats['avg_error'] > 0
        
    def test_configuration_update(self, pid):
        """测试配置更新"""
        # 更新自适应配置
        adaptive_config = {
            'enabled': True,
            'learning_rate': 0.02
        }
        pid.configure_adaptive(adaptive_config)
        assert pid.adaptive_config['enabled']
        assert pid.adaptive_config['learning_rate'] == 0.02
        
        # 更新抗干扰配置
        disturbance_config = {
            'enabled': True,
            'threshold': 2.0
        }
        pid.configure_disturbance(disturbance_config)
        assert pid.disturbance_config['enabled']
        assert pid.disturbance_config['threshold'] == 2.0
        
    @pytest.mark.parametrize("target,current,expected_sign", [
        (45.0, 0.0, 1),    # 正误差
        (-45.0, 0.0, -1),  # 负误差
        (0.0, 0.0, 0)      # 零误差
    ])
    def test_output_direction(self, pid, target, current, expected_sign):
        """测试输出方向"""
        output = pid.compute(target, current, dt=0.02)
        if expected_sign == 0:
            assert abs(output) < pid.deadband
        else:
            assert np.sign(output) == expected_sign