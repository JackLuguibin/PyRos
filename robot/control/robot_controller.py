from typing import Dict, Optional
import logging
from ..kinematics.motion_planner import MotionPlanner
from ..core.message_broker import MessageBroker

class RobotController:
    """机器人控制器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('RobotController')
        self.config = config
        
        # 运动规划器
        self.motion_planner = MotionPlanner(config.get('motion_planner', {}))
        
        # 消息代理
        self.message_broker = MessageBroker(config.get('message_broker', {}))
        
        # 注册消息处理器
        self.message_broker.register_handler(
            'control/joint_target',
            self._handle_joint_target
        )
        self.message_broker.register_handler(
            'control/cartesian_target',
            self._handle_cartesian_target
        )
        
    def _handle_joint_target(self, message: Dict):
        """处理关节目标"""
        try:
            target_joints = message.get('positions', {})
            duration = message.get('duration')
            
            # 获取当前状态
            current_joints = self._get_current_joints()
            
            # 规划轨迹
            trajectory = self.motion_planner.plan_joint_motion(
                target_joints,
                current_joints,
                duration
            )
            
            if not trajectory:
                self.logger.error("轨迹规划失败")
                return
                
            # 执行轨迹
            if not self.motion_planner.execute_trajectory(trajectory):
                self.logger.error("轨迹执行失败")
                
        except Exception as e:
            self.logger.error(f"处理关节目标失败: {str(e)}")
            
    def _handle_cartesian_target(self, message: Dict):
        """处理笛卡尔目标"""
        try:
            target_pose = message.get('pose')
            duration = message.get('duration')
            linear = message.get('linear', True)
            
            if not target_pose:
                self.logger.error("未指定目标位姿")
                return
                
            # 获取当前状态
            current_joints = self._get_current_joints()
            
            # 规划轨迹
            trajectory = self.motion_planner.plan_cartesian_motion(
                target_pose,
                current_joints,
                duration,
                linear
            )
            
            if not trajectory:
                self.logger.error("轨迹规划失败")
                return
                
            # 执行轨迹
            if not self.motion_planner.execute_trajectory(trajectory):
                self.logger.error("轨迹执行失败")
                
        except Exception as e:
            self.logger.error(f"处理笛卡尔目标失败: {str(e)}")
            
    def _get_current_joints(self) -> Dict[str, JointState]:
        """获取当前关节状态"""
        try:
            # 从消息代理获取关节状态
            joint_states = self.message_broker.get_message('joint_states')
            if not joint_states:
                return {}
                
            return joint_states.get('states', {})
            
        except Exception as e:
            self.logger.error(f"获取关节状态失败: {str(e)}")
            return {} 