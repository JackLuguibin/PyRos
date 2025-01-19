class RobotSimulator:
    def __init__(self, config: Dict):
        self.dynamics = RobotDynamics(config.get('dynamics', {}))
        self.dt = 0.001  # 仿真时间步长
        
    def simulate_step(self, current_state: Dict[str, JointState],
                     control_input: np.ndarray) -> Dict[str, JointState]:
        """仿真一个时间步"""
        try:
            # 计算加速度
            q_ddot = self.dynamics.compute_forward_dynamics(
                current_state,
                control_input
            )
            
            # 更新状态
            next_state = {}
            for i, (name, state) in enumerate(current_state.items()):
                # 欧拉积分
                velocity = state.velocity + q_ddot[i] * self.dt
                position = state.position + velocity * self.dt
                
                next_state[name] = JointState(
                    position=position,
                    velocity=velocity
                )
                
            return next_state
            
        except Exception as e:
            self.logger.error(f"仿真步进失败: {str(e)}")
            return current_state 