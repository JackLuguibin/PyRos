from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging
from ..model import JointState
from .motion_planner import MotionPlanner

@dataclass
class TaskConfig:
    """任务规划配置"""
    max_task_steps: int = 100  # 最大任务步骤数
    retry_attempts: int = 3  # 重试次数

class TaskPlanner:
    """任务规划器"""
    
    def __init__(self, config: Dict, motion_planner: MotionPlanner,
                 logger: Optional[logging.Logger] = None):
        """初始化任务规划器
        
        Args:
            config: 任务配置
            motion_planner: 运动规划器
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger('TaskPlanner')
        self.config = TaskConfig(**config)
        self.motion_planner = motion_planner
        
    def plan_task(self, task: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """规划任务
        
        Args:
            task: 任务描述
            
        Returns:
            plan: 任务计划，失败返回None
        """
        try:
            # 解析任务
            steps = self._parse_task(task)
            if not steps:
                return None
                
            # 规划每个步骤
            plan = []
            current_state = task.get('initial_state')
            
            for step in steps:
                # 规划运动
                trajectory = self._plan_step(current_state, step)
                if not trajectory:
                    return None
                    
                # 更新当前状态
                current_state = trajectory[-1]
                
                # 添加到计划中
                plan.append({
                    'type': step['type'],
                    'trajectory': trajectory,
                    'params': step.get('params', {})
                })
                
            return plan
            
        except Exception as e:
            self.logger.error(f"任务规划失败: {str(e)}")
            return None
            
    def _parse_task(self, task: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """解析任务"""
        try:
            steps = task.get('steps', [])
            if not steps:
                raise ValueError("任务步骤为空")
                
            if len(steps) > self.config.max_task_steps:
                raise ValueError("任务步骤过多")
                
            return steps
            
        except Exception as e:
            self.logger.error(f"任务解析失败: {str(e)}")
            return None
            
    def _plan_step(self, current_state: Dict[str, JointState],
                  step: Dict[str, Any]) -> Optional[List[Dict[str, JointState]]]:
        """规划步骤"""
        try:
            # 获取目标状态
            goal_state = self._get_step_goal(step)
            if not goal_state:
                return None
                
            # 尝试规划运动
            for attempt in range(self.config.retry_attempts):
                trajectory = self.motion_planner.plan_motion(
                    current_state,
                    goal_state
                )
                if trajectory:
                    return trajectory
                    
                self.logger.warning(f"步骤规划尝试 {attempt + 1} 失败")
                
            return None
            
        except Exception as e:
            self.logger.error(f"步骤规划失败: {str(e)}")
            return None
            
    def _get_step_goal(self, step: Dict[str, Any]) -> Optional[Dict[str, JointState]]:
        """获取步骤目标状态"""
        try:
            if 'goal_state' in step:
                return step['goal_state']
                
            # 根据步骤类型生成目标状态
            if step['type'] == 'move_to':
                return self._create_move_goal(step['params'])
            elif step['type'] == 'grasp':
                return self._create_grasp_goal(step['params'])
            else:
                raise ValueError(f"未知的步骤类型: {step['type']}")
                
        except Exception as e:
            self.logger.error(f"获取目标状态失败: {str(e)}")
            return None
            
    def _create_move_goal(self, params: Dict[str, Any]) -> Dict[str, JointState]:
        """创建移动目标"""
        # 简单实现：直接使用目标位置
        return {
            joint: JointState(position=position)
            for joint, position in params.get('positions', {}).items()
        }
        
    def _create_grasp_goal(self, params: Dict[str, Any]) -> Dict[str, JointState]:
        """创建抓取目标"""
        # 简单实现：设置抓取器位置
        return {
            'gripper': JointState(
                position=0.0 if params.get('open', True) else 1.0
            )
        } 