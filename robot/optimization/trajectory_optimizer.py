from typing import List, Dict
from robot.dynamics.robot_dynamics import RobotDynamics
from robot.control.joint_state import JointState

class TrajectoryOptimizer:
    def __init__(self, config: Dict):
        self.dynamics = RobotDynamics(config.get('dynamics', {}))
        
    def optimize_trajectory(self, trajectory: List[Dict[str, JointState]]) -> List[Dict[str, JointState]]:
        """优化轨迹"""
        try:
            optimized = []
            
            for i in range(len(trajectory)-1):
                current = trajectory[i]
                next_point = trajectory[i+1]
                
                # 检查动力学约束
                if self._check_dynamics_constraints(current, next_point):
                    optimized.append(current)
                else:
                    # 插入中间点
                    mid_point = self._generate_intermediate_point(
                        current,
                        next_point
                    )
                    optimized.extend([current, mid_point])
                    
            return optimized
            
        except Exception as e:
            self.logger.error(f"轨迹优化失败: {str(e)}")
            return trajectory 