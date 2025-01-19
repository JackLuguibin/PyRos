import numpy as np
import time
from ..dynamics import RobotDynamics, DynamicsParams, JointState
from ..dynamics_controller import DynamicsController

def run_dynamics_example():
    """运行动力学示例"""
    
    # 配置参数
    config = {
        'dynamics': {
            'dynamics_params': {
                'link_1': {
                    'mass': 1.0,
                    'inertia': [
                        [0.1, 0, 0],
                        [0, 0.1, 0],
                        [0, 0, 0.1]
                    ],
                    'com': [0, 0, 0.5],
                    'damping': 0.1,
                    'friction': 0.1
                },
                'link_2': {
                    'mass': 0.8,
                    'inertia': [
                        [0.08, 0, 0],
                        [0, 0.08, 0],
                        [0, 0, 0.08]
                    ],
                    'com': [0, 0, 0.4],
                    'damping': 0.1,
                    'friction': 0.1
                }
            }
        },
        'gains': {
            'kp': [100.0, 100.0],
            'kd': [20.0, 20.0],
            'ki': [1.0, 1.0]
        }
    }
    
    # 创建控制器
    controller = DynamicsController(config)
    
    # 初始状态
    current_state = {
        'joint_0': JointState(position=0.0, velocity=0.0),
        'joint_1': JointState(position=0.0, velocity=0.0)
    }
    
    # 目标状态
    target_state = {
        'joint_0': JointState(position=np.pi/2, velocity=0.0),
        'joint_1': JointState(position=np.pi/4, velocity=0.0)
    }
    
    # 仿真循环
    dt = 0.001
    t = 0.0
    while t < 5.0:  # 仿真5秒
        # 计算控制输出
        tau = controller.compute_control(current_state, target_state)
        
        # 计算加速度
        q_ddot = controller.dynamics.compute_forward_dynamics(
            current_state,
            tau
        )
        
        # 更新状态
        for i, (name, state) in enumerate(current_state.items()):
            # 欧拉积分
            state.velocity += q_ddot[i] * dt
            state.position += state.velocity * dt
            
        # 打印状态
        print(f"t={t:.3f}s:")
        for name, state in current_state.items():
            print(f"  {name}: pos={state.position:.3f}, vel={state.velocity:.3f}")
            
        t += dt
        time.sleep(dt)

if __name__ == '__main__':
    run_dynamics_example() 