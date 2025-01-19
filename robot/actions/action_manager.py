from typing import Dict, List, Optional, Callable
from ..servos.servo_manager import ServoManager
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
import yaml

class ActionGroup:
    def __init__(self, name: str, actions: List[dict]):
        self.name = name
        self.actions = actions
        self.is_running = False
        self.should_stop = False

class ActionGroupManager:
    def __init__(self, logger: logging.Logger):
        self.action_groups: Dict[str, ActionGroup] = {}
        self.servo_manager = None
        self.logger = logger
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.running_groups: Dict[str, threading.Event] = {}
        
    def initialize(self, servo_manager: ServoManager):
        """初始化动作组管理器"""
        self.servo_manager = servo_manager
        
    def load_action_groups(self, config: dict):
        """从配置加载动作组"""
        try:
            action_groups = config.get('action_groups', {})
            for group_name, actions in action_groups.items():
                self.register_action_group(group_name, actions)
                self.logger.info(f"已加载动作组: {group_name}")
        except Exception as e:
            self.logger.error(f"加载动作组失败: {e}")
            raise
        
    def register_action_group(self, group_name: str, actions: List[dict]):
        """注册新的动作组"""
        self.action_groups[group_name] = ActionGroup(group_name, actions)
        self.logger.debug(f"注册动作组: {group_name}")
        
    def execute_action_group(self, group_name: str, parallel: bool = False) -> bool:
        """执行动作组
        
        Args:
            group_name: 动作组名称
            parallel: 是否并行执行（与其他动作组）
        """
        if group_name in self.action_groups:
            group = self.action_groups[group_name]
            
            if parallel:
                # 并行执行
                self.executor.submit(self._execute_group, group)
                return True
            else:
                # 串行执行
                return self._execute_group(group)
        return False
        
    def _execute_group(self, group: ActionGroup) -> bool:
        """执行单个动作组"""
        if group.is_running:
            self.logger.warning(f"动作组 {group.name} 已在运行")
            return False
            
        try:
            group.is_running = True
            stop_event = threading.Event()
            self.running_groups[group.name] = stop_event
            
            self.logger.info(f"开始执行动作组: {group.name}")
            
            for action in group.actions:
                if stop_event.is_set():
                    self.logger.info(f"动作组 {group.name} 被终止")
                    break
                    
                servo_id = action['servo_id']
                angle = action['angle']
                delay = action.get('delay', 0)
                
                self.servo_manager.set_angle(servo_id, angle)
                if delay > 0:
                    time.sleep(delay)
                    
            self.logger.info(f"动作组 {group.name} 执行完成")
            return True
            
        except Exception as e:
            self.logger.error(f"执行动作组 {group.name} 失败: {e}")
            return False
            
        finally:
            group.is_running = False
            self.running_groups.pop(group.name, None)
            
    def stop_action_group(self, group_name: str):
        """停止指定的动作组"""
        if group_name in self.running_groups:
            self.running_groups[group_name].set()
            self.logger.info(f"已发送停止信号到动作组: {group_name}")
            
    def stop_all_groups(self):
        """停止所有运行中的动作组"""
        for group_name in list(self.running_groups.keys()):
            self.stop_action_group(group_name)

class ActionManager:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        self.actions: Dict[str, List[Dict]] = {}
        self.running_actions: Dict[str, threading.Event] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.Lock()
        
    def load_action(self, name: str, action_data: List[Dict]):
        """加载动作组"""
        with self._lock:
            self.actions[name] = action_data
            if self.logger:
                self.logger.info(f"加载动作组: {name}")
                
    def load_from_file(self, file_path: str):
        """从文件加载动作组"""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                for name, action in data.items():
                    self.load_action(name, action)
        except Exception as e:
            if self.logger:
                self.logger.error(f"加载动作文件失败: {e}")
                
    def execute(self, name: str, parallel: bool = False, 
                callback: Optional[Callable] = None):
        """执行动作组
        
        Args:
            name: 动作组名称
            parallel: 是否并行执行
            callback: 执行完成的回调函数
        """
        if name not in self.actions:
            if self.logger:
                self.logger.error(f"动作组不存在: {name}")
            return False
            
        if name in self.running_actions:
            if self.logger:
                self.logger.warning(f"动作组正在执行: {name}")
            return False
            
        stop_event = threading.Event()
        self.running_actions[name] = stop_event
        
        def _execute():
            try:
                action_data = self.actions[name]
                for frame in action_data:
                    if stop_event.is_set():
                        break
                    # 执行动作帧
                    self._execute_frame(frame)
                    # 等待指定延时
                    time.sleep(frame.get('delay', 0.1))
                    
                if callback:
                    callback(name, True)
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"执行动作组失败: {name}, {e}")
                if callback:
                    callback(name, False)
                    
            finally:
                with self._lock:
                    del self.running_actions[name]
                    
        if parallel:
            self.executor.submit(_execute)
        else:
            _execute()
            
        return True
        
    def stop(self, name: str = None):
        """停止动作组执行
        
        Args:
            name: 动作组名称，None表示停止所有
        """
        with self._lock:
            if name is None:
                # 停止所有动作组
                for stop_event in self.running_actions.values():
                    stop_event.set()
            elif name in self.running_actions:
                # 停止指定动作组
                self.running_actions[name].set()
                
    def _execute_frame(self, frame: Dict):
        """执行单个动作帧"""
        # 具体的执行逻辑由子类实现
        pass
        
    def cleanup(self):
        """清理资源"""
        self.stop()
        self.executor.shutdown() 