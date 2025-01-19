from typing import Dict, Optional, List
import logging
import time
from threading import Lock, Thread, Event
from queue import Queue
from .message_broker import MessageBroker
from .state_manager import StateManager
from ..control.controller_manager import ControllerManager
from ..control.performance_monitor import PerformanceMonitor
from ..control.fault_predictor import FaultPredictor

class RobotManager:
    """机器人管理器"""
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('RobotManager')
        self.config = config
        
        # 组件管理
        self.message_broker = MessageBroker(config.get('message_broker', {}))
        self.state_manager = StateManager(config.get('state_manager', {}), self.logger)
        self.controller_manager = ControllerManager(config.get('controllers', {}))
        self.performance_monitor = PerformanceMonitor(config.get('monitor', {}))
        self.fault_predictor = FaultPredictor(config.get('fault_predictor', {}))
        
        # 线程控制
        self.stop_event = Event()
        self.threads: List[Thread] = []
        self.message_queue = Queue(maxsize=1000)
        
    def initialize(self):
        """初始化机器人"""
        try:
            # 初始化消息代理
            self.message_broker.initialize()
            
            # 初始化状态管理器
            if not self.state_manager.initialize():
                raise RuntimeError("状态管理器初始化失败")
            
            # 初始化控制器
            self.controller_manager.initialize()
            
            # 启动监控
            self.performance_monitor.start()
            
            # 注册消息处理器
            self._register_handlers()
            
            # 创建工作线程
            self.threads.extend([
                Thread(target=self._control_loop, name="control"),
                Thread(target=self._monitor_loop, name="monitor"),
                Thread(target=self._fault_detection_loop, name="fault"),
                Thread(target=self._message_processor_loop, name="processor")
            ])
            
            # 更新状态
            self.state_manager.update_state({
                'mode': 'ready',
                'timestamp': time.time()
            })
            
            self.logger.info("机器人初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化失败: {str(e)}")
            self.state_manager.add_error(str(e))
            raise
            
    def start(self):
        """启动机器人"""
        if not self.state_manager.get_state().get('mode') == 'ready':
            raise RuntimeError("机器人未初始化")
            
        try:
            # 更新状态
            self.state_manager.update_state({
                'mode': 'running',
                'timestamp': time.time()
            })
            
            # 启动所有线程
            self.stop_event.clear()
            for thread in self.threads:
                thread.start()
                
            self.logger.info("机器人启动")
            
        except Exception as e:
            self.logger.error(f"启动失败: {str(e)}")
            self.state_manager.add_error(str(e))
            self.state_manager.update_state({'mode': 'error'})
            raise
            
    def stop(self):
        """停止机器人"""
        try:
            # 更新状态
            self.state_manager.update_state({
                'mode': 'stopping',
                'timestamp': time.time()
            })
            
            # 停止所有线程
            self.stop_event.set()
            for thread in self.threads:
                thread.join()
                
            # 停止组件
            self.message_broker.stop()
            self.controller_manager.stop()
            self.performance_monitor.stop()
            self.state_manager.stop()
            
            # 更新状态
            self.state_manager.update_state({
                'mode': 'stopped',
                'timestamp': time.time()
            })
            
            self.logger.info("机器人停止")
            
        except Exception as e:
            self.logger.error(f"停止失败: {str(e)}")
            self.state_manager.add_error(str(e))
            raise
            
    def _register_handlers(self):
        """注册消息处理器"""
        # 系统消息处理
        self.message_broker.register_handler(
            'system/command',
            lambda msg: self.message_queue.put(('system_command', msg))
        )
        
        # 控制命令处理
        self.message_broker.register_handler(
            'control/command',
            lambda msg: self.message_queue.put(('control_command', msg))
        )
        
        # 传感器数据处理
        self.message_broker.register_handler(
            'sensor/data',
            lambda msg: self.message_queue.put(('sensor_data', msg))
        )
        
    def _control_loop(self):
        """控制循环"""
        while not self.stop_event.is_set():
            try:
                # 获取当前状态
                current_state = self.state_manager.get_state()
                if current_state['mode'] != 'running':
                    time.sleep(0.1)
                    continue
                    
                # 获取传感器数据
                sensor_data = self.message_broker.get_message('sensor/data')
                if not sensor_data:
                    continue
                    
                # 更新控制器
                control_output = self.controller_manager.update(sensor_data)
                
                # 发送控制命令
                self.message_broker.publish('control/output', control_output)
                
                # 更新性能指标
                self.performance_monitor.update_metrics({
                    'control_latency': control_output.get('latency', 0),
                    'control_error': control_output.get('error', 0)
                })
                
                # 更新状态
                self.state_manager.update_state({
                    'actuators': control_output.get('actuators', {}),
                    'timestamp': time.time()
                })
                
                time.sleep(0.01)  # 100Hz控制频率
                
            except Exception as e:
                self.logger.error(f"控制循环错误: {str(e)}")
                self.state_manager.add_error(str(e))
                self.state_manager.update_state({'mode': 'error'})
                break
                
    def _monitor_loop(self):
        """监控循环"""
        while not self.stop_event.is_set():
            try:
                # 获取系统状态
                system_status = self.message_broker.get_message('system/status')
                if system_status:
                    # 更新监控指标
                    self.performance_monitor.update_metrics(system_status)
                    
                    # 检查性能告警
                    alerts = self.performance_monitor.check_alerts()
                    if alerts:
                        self.message_broker.publish('system/alerts', alerts)
                        for alert in alerts:
                            self.state_manager.add_error(
                                f"性能告警: {alert['metric']} = {alert['value']:.2f}"
                            )
                        
                time.sleep(1.0)  # 1Hz监控频率
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {str(e)}")
                self.state_manager.add_error(str(e))
                
    def _fault_detection_loop(self):
        """故障检测循环"""
        while not self.stop_event.is_set():
            try:
                # 获取性能指标
                metrics = self.performance_monitor.get_metrics()
                
                # 预测故障
                fault_prob = self.fault_predictor.update(metrics)
                
                # 检查故障
                fault = self.fault_predictor.check_fault(fault_prob)
                if fault:
                    self.message_broker.publish('system/fault', fault)
                    self.state_manager.add_error(f"检测到潜在故障: {fault}")
                    
                time.sleep(0.1)  # 10Hz检测频率
                
            except Exception as e:
                self.logger.error(f"故障检测循环错误: {str(e)}")
                self.state_manager.add_error(str(e))
                
    def _message_processor_loop(self):
        """消息处理循环"""
        while not self.stop_event.is_set():
            try:
                # 获取消息
                msg_type, message = self.message_queue.get(timeout=1.0)
                
                # 处理不同类型的消息
                if msg_type == 'system_command':
                    self._handle_system_command(message)
                elif msg_type == 'control_command':
                    self._handle_control_command(message)
                elif msg_type == 'sensor_data':
                    self._handle_sensor_data(message)
                    
            except Exception as e:
                if not isinstance(e, TimeoutError):
                    self.logger.error(f"消息处理错误: {str(e)}")
                    self.state_manager.add_error(str(e))
                    
    def _handle_system_command(self, message: Dict):
        """处理系统命令"""
        try:
            command = message.get('command')
            if command == 'reset':
                self.state_manager.clear_errors()
                self.state_manager.update_state({'mode': 'ready'})
            elif command == 'emergency_stop':
                self.state_manager.update_state({'mode': 'emergency'})
                self.stop()
        except Exception as e:
            self.logger.error(f"处理系统命令错误: {str(e)}")
            self.state_manager.add_error(str(e))
            
    def _handle_control_command(self, message: Dict):
        """处理控制命令"""
        try:
            command = message.get('command')
            if command == 'activate':
                controller = message.get('controller')
                self.controller_manager.activate_controller(controller)
            elif command == 'deactivate':
                self.controller_manager.deactivate_controller()
        except Exception as e:
            self.logger.error(f"处理控制命令错误: {str(e)}")
            self.state_manager.add_error(str(e))
            
    def _handle_sensor_data(self, message: Dict):
        """处理传感器数据"""
        try:
            self.state_manager.update_state({
                'sensors': message,
                'timestamp': time.time()
            })
        except Exception as e:
            self.logger.error(f"处理传感器数据错误: {str(e)}")
            self.state_manager.add_error(str(e)) 