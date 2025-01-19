from typing import Dict, Optional, List, Callable
import logging
from enum import Enum, auto
from dataclasses import dataclass
from threading import Lock

class State(Enum):
    """机器人状态"""
    IDLE = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()
    EMERGENCY = auto()
    STOPPING = auto()
    STOPPED = auto()

@dataclass
class Transition:
    """状态转换"""
    from_state: State
    to_state: State
    condition: Optional[Callable] = None
    action: Optional[Callable] = None

class StateMachine:
    """状态机"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('StateMachine')
        self.config = config
        
        # 状态管理
        self.current_state = State.IDLE
        self.state_lock = Lock()
        
        # 转换规则
        self.transitions: List[Transition] = []
        self._init_transitions()
        
        # 状态处理器
        self.state_handlers: Dict[State, Callable] = {}
        self._init_handlers()
        
    def _init_transitions(self):
        """初始化转换规则"""
        self.transitions.extend([
            # 空闲->就绪
            Transition(
                from_state=State.IDLE,
                to_state=State.READY,
                condition=self._can_be_ready,
                action=self._prepare_system
            ),
            # 就绪->运行
            Transition(
                from_state=State.READY,
                to_state=State.RUNNING,
                condition=self._can_run,
                action=self._start_system
            ),
            # 运行->暂停
            Transition(
                from_state=State.RUNNING,
                to_state=State.PAUSED,
                action=self._pause_system
            ),
            # 暂停->运行
            Transition(
                from_state=State.PAUSED,
                to_state=State.RUNNING,
                condition=self._can_resume,
                action=self._resume_system
            ),
            # 任意->错误
            Transition(
                from_state=None,
                to_state=State.ERROR,
                action=self._handle_error
            ),
            # 任意->紧急
            Transition(
                from_state=None,
                to_state=State.EMERGENCY,
                action=self._handle_emergency
            ),
            # 任意->停止中
            Transition(
                from_state=None,
                to_state=State.STOPPING,
                action=self._prepare_stop
            ),
            # 停止中->已停止
            Transition(
                from_state=State.STOPPING,
                to_state=State.STOPPED,
                condition=self._can_stop,
                action=self._complete_stop
            )
        ])
        
    def _init_handlers(self):
        """初始化状态处理器"""
        self.state_handlers.update({
            State.IDLE: self._handle_idle,
            State.READY: self._handle_ready,
            State.RUNNING: self._handle_running,
            State.PAUSED: self._handle_paused,
            State.ERROR: self._handle_error,
            State.EMERGENCY: self._handle_emergency,
            State.STOPPING: self._handle_stopping,
            State.STOPPED: self._handle_stopped
        })
        
    def transition_to(self, target_state: State) -> bool:
        """状态转换
        
        Args:
            target_state: 目标状态
            
        Returns:
            转换是否成功
        """
        try:
            with self.state_lock:
                # 查找可用转换
                transition = self._find_transition(target_state)
                if not transition:
                    self.logger.warning(
                        f"无效转换: {self.current_state} -> {target_state}"
                    )
                    return False
                    
                # 检查条件
                if transition.condition and not transition.condition():
                    self.logger.warning(
                        f"转换条件不满足: {self.current_state} -> {target_state}"
                    )
                    return False
                    
                # 执行转换
                if transition.action:
                    transition.action()
                    
                # 更新状态
                old_state = self.current_state
                self.current_state = target_state
                
                # 调用处理器
                if target_state in self.state_handlers:
                    self.state_handlers[target_state]()
                    
                self.logger.info(f"状态转换: {old_state} -> {target_state}")
                return True
                
        except Exception as e:
            self.logger.error(f"状态转换失败: {str(e)}")
            return False
            
    def get_state(self) -> State:
        """获取当前状态"""
        with self.state_lock:
            return self.current_state
            
    def _find_transition(self, target_state: State) -> Optional[Transition]:
        """查找转换规则"""
        for transition in self.transitions:
            if transition.to_state == target_state and \
               (transition.from_state is None or
                transition.from_state == self.current_state):
                return transition
        return None
        
    # 转换条件
    def _can_be_ready(self) -> bool:
        """检查是否可以就绪"""
        return True  # 根据实际情况实现
        
    def _can_run(self) -> bool:
        """检查是否可以运行"""
        return True  # 根据实际情况实现
        
    def _can_resume(self) -> bool:
        """检查是否可以恢复"""
        return True  # 根据实际情况实现
        
    def _can_stop(self) -> bool:
        """检查是否可以停止"""
        return True  # 根据实际情况实现
        
    # 转换动作
    def _prepare_system(self):
        """准备系统"""
        pass  # 根据实际情况实现
        
    def _start_system(self):
        """启动系统"""
        pass  # 根据实际情况实现
        
    def _pause_system(self):
        """暂停系统"""
        pass  # 根据实际情况实现
        
    def _resume_system(self):
        """恢复系统"""
        pass  # 根据实际情况实现
        
    def _prepare_stop(self):
        """准备停止"""
        pass  # 根据实际情况实现
        
    def _complete_stop(self):
        """完成停止"""
        pass  # 根据实际情况实现
        
    # 状态处理器
    def _handle_idle(self):
        """处理空闲状态"""
        pass  # 根据实际情况实现
        
    def _handle_ready(self):
        """处理就绪状态"""
        pass  # 根据实际情况实现
        
    def _handle_running(self):
        """处理运行状态"""
        pass  # 根据实际情况实现
        
    def _handle_paused(self):
        """处理暂停状态"""
        pass  # 根据实际情况实现
        
    def _handle_error(self):
        """处理错误状态"""
        pass  # 根据实际情况实现
        
    def _handle_emergency(self):
        """处理紧急状态"""
        pass  # 根据实际情况实现
        
    def _handle_stopping(self):
        """处理停止中状态"""
        pass  # 根据实际情况实现
        
    def _handle_stopped(self):
        """处理已停止状态"""
        pass  # 根据实际情况实现 