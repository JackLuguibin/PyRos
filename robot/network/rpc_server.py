from xmlrpc.server import SimpleXMLRPCServer
import threading
from typing import Optional, List, Dict, Any, Callable
from ..core.manager import RobotManager
import logging
import json
import socket
from queue import Queue
from dataclasses import dataclass
from .protocol import Message, CommandMessage, StateMessage, ErrorMessage
from .task_queue import TaskQueue, TaskPriority, TaskResult
from .heartbeat import HeartbeatMonitor
from .connection_pool import ConnectionPool
from .compression import CompressionManager
from .cache import CacheManager
from .rate_limiter import RateLimiter

@dataclass
class RPCRequest:
    """RPC请求"""
    method: str  # 方法名
    params: Dict  # 参数
    id: str  # 请求ID
    
@dataclass
class RPCResponse:
    """RPC响应"""
    result: Any  # 结果
    error: Optional[str] = None  # 错误信息
    id: Optional[str] = None  # 请求ID

class RobotRPCServer:
    def __init__(self, robot: RobotManager, config: Dict, logger: Optional[logging.Logger] = None):
        self.robot = robot
        self.logger = logger or logging.getLogger('RobotRPCServer')
        self.config = config
        
        # 服务器配置
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8000)
        
        # 任务队列
        self.task_queue = TaskQueue(config.get('task_queue', {}))
        
        # 压缩管理器
        self.compression = CompressionManager(
            config.get('compression', {})
        )
        
        # 缓存管理器
        self.cache = CacheManager(
            config.get('cache', {})
        )
        
        # 流量限制器
        self.rate_limiter = RateLimiter(
            config.get('rate_limit', {})
        )
        
        # 注册RPC方法
        self._register_methods()
        
    def _register_methods(self):
        """注册RPC方法"""
        # 基本控制 - 同步方法
        self.methods = {
            'get_sensor_data': self.get_sensor_data,
            'get_robot_state': self.get_robot_state,
            'stop_all': self.stop_all
        }
        
        # 异步任务 - 通过任务队列执行
        self.async_methods = {
            'execute_action_group': {
                'func': self.execute_action_group,
                'priority': TaskPriority.HIGH
            },
            'set_servo_angle': {
                'func': self.set_servo_angle,
                'priority': TaskPriority.NORMAL
            },
            'start_recording': {
                'func': self.start_recording,
                'priority': TaskPriority.LOW
            }
        }
        
    def start(self):
        """启动服务器"""
        # 启动任务队列
        self.task_queue.start()
        
        # 启动RPC服务器
        self.server_thread = threading.Thread(target=self._server_loop)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        self.logger.info(f"RPC服务器已启动在 {self.host}:{self.port}")
        
    def stop(self):
        """停止服务器"""
        # 停止任务队列
        self.task_queue.stop()
        
        # 停止RPC服务器
        if hasattr(self, 'server_socket'):
            self.server_socket.close()
            
    def handle_request(self, request: dict) -> dict:
        """处理RPC请求"""
        # 检查流量限制
        if not self.rate_limiter.allow():
            return {
                'error': '请求过于频繁',
                'id': request.get('id')
            }
            
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        # 检查缓存
        cache_key = f"{method}:{json.dumps(params)}"
        cached = self.cache.get(cache_key)
        if cached:
            return {
                'result': cached,
                'id': request_id,
                'cached': True
            }
            
        try:
            # 检查方法是否存在
            if method in self.methods:
                # 同步方法直接执行
                result = self.methods[method](**params)
                
                # 设置缓存
                if method in self.cacheable_methods:
                    self.cache.set(cache_key, result)
                
                return {
                    'result': result,
                    'id': request_id
                }
            elif method in self.async_methods:
                # 异步方法提交到任务队列
                task_config = self.async_methods[method]
                task_id = self.task_queue.submit(
                    task_config['func'],
                    priority=task_config['priority'],
                    **params
                )
                return {
                    'result': {'task_id': task_id},
                    'id': request_id
                }
            else:
                return {
                    'error': f"方法不存在: {method}",
                    'id': request_id
                }
                
        except Exception as e:
            self.logger.error(f"处理请求失败: {str(e)}")
            return {
                'error': str(e),
                'id': request_id
            }
            
    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        return self.task_queue.get_result(task_id)
        
    # RPC方法实现
    def execute_action_group(self, group_name: str, parallel: bool = False) -> bool:
        """执行动作组"""
        try:
            return self.robot.action_manager.execute_action_group(group_name, parallel)
        except Exception as e:
            self.logger.error(f"执行动作组出错: {e}")
            raise
            
    def set_servo_angle(self, servo_id: str, angle: float) -> bool:
        """设置舵机角度"""
        try:
            self.robot.servo_manager.set_angle(servo_id, angle)
            return True
        except Exception as e:
            self.logger.error(f"设置舵机角度出错: {e}")
            raise
            
    def get_sensor_data(self, sensor_id: str) -> Dict:
        """获取传感器数据"""
        try:
            return self.robot.sensor_manager.get_data(sensor_id)
        except Exception as e:
            self.logger.error(f"获取传感器数据出错: {e}")
            raise

class RPCServer:
    """RPC服务器"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('RPCServer')
        self.config = config
        
        # 服务器配置
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8081)
        self.max_clients = config.get('max_clients', 5)
        
        # 服务器状态
        self.running = False
        self.server_socket = None
        self.clients: Dict[str, socket.socket] = {}
        
        # 请求处理
        self.methods: Dict[str, Callable] = {}
        self.request_queue = Queue()
        self.response_queues: Dict[str, Queue] = {}
        
        # 工作线程
        self.threads: Dict[str, threading.Thread] = {}
        
        # 连接池
        self.pool = ConnectionPool(config.get('connection_pool', {}))
        
        # 心跳处理
        self.register_method('heartbeat', self._handle_heartbeat)
        
    def start(self):
        """启动服务器"""
        try:
            # 创建服务器套接字
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_clients)
            
            # 创建工作线程
            self.threads['acceptor'] = threading.Thread(
                target=self._accept_loop,
                name="acceptor"
            )
            self.threads['processor'] = threading.Thread(
                target=self._process_loop,
                name="processor"
            )
            
            # 启动线程
            self.running = True
            for thread in self.threads.values():
                thread.start()
                
            self.logger.info(f"RPC服务器启动于 {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"启动服务器失败: {str(e)}")
            self.stop()
            
    def stop(self):
        """停止服务器"""
        try:
            self.running = False
            
            # 关闭客户端连接
            for client in self.clients.values():
                client.close()
            self.clients.clear()
            
            # 关闭服务器套接字
            if self.server_socket:
                self.server_socket.close()
                
            # 停止线程
            for thread in self.threads.values():
                thread.join()
                
            self.logger.info("RPC服务器停止")
            
        except Exception as e:
            self.logger.error(f"停止服务器失败: {str(e)}")
            
    def register_method(self, method: str, handler: Callable):
        """注册RPC方法
        
        Args:
            method: 方法名
            handler: 处理函数
        """
        self.methods[method] = handler
        
    def _accept_loop(self):
        """接受连接循环"""
        while self.running:
            try:
                # 接受新连接
                client_socket, address = self.server_socket.accept()
                client_id = f"{address[0]}:{address[1]}"
                
                # 创建响应队列
                self.response_queues[client_id] = Queue()
                
                # 创建客户端处理线程
                self.threads[client_id] = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_id),
                    name=f"client_{client_id}"
                )
                self.threads[client_id].start()
                
                self.clients[client_id] = client_socket
                self.logger.info(f"客户端连接: {client_id}")
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"接受连接失败: {str(e)}")
                    
    def _handle_client(self, client_socket: socket.socket, client_id: str):
        """处理客户端连接
        
        Args:
            client_socket: 客户端套接字
            client_id: 客户端ID
        """
        # 创建心跳监控
        heartbeat = HeartbeatMonitor(
            self.config.get('heartbeat', {}),
            on_timeout=lambda: self._handle_client_timeout(client_id)
        )
        heartbeat.start()
        
        try:
            while self.running:
                # 接收请求
                data = client_socket.recv(4096)
                if not data:
                    break
                    
                # 解析请求
                request_data = json.loads(data.decode())
                request = RPCRequest(
                    method=request_data['method'],
                    params=request_data.get('params', {}),
                    id=request_data.get('id')
                )
                
                # 放入请求队列
                self.request_queue.put((client_id, request))
                
                # 等待响应
                if request.id:
                    response = self.response_queues[client_id].get()
                    
                    # 发送响应
                    response_data = json.dumps({
                        'result': response.result,
                        'error': response.error,
                        'id': response.id
                    }).encode()
                    client_socket.sendall(response_data)
                    
        except Exception as e:
            self.logger.error(f"处理客户端 {client_id} 失败: {str(e)}")
            
        finally:
            heartbeat.stop()
            # 清理客户端
            client_socket.close()
            self.clients.pop(client_id, None)
            self.response_queues.pop(client_id, None)
            self.logger.info(f"客户端断开: {client_id}")
            
    def _process_loop(self):
        """处理请求循环"""
        while self.running:
            try:
                # 获取请求
                client_id, request = self.request_queue.get(timeout=1.0)
                
                # 处理请求
                if request.method in self.methods:
                    try:
                        # 调用处理函数
                        result = self.methods[request.method](**request.params)
                        response = RPCResponse(result=result, id=request.id)
                    except Exception as e:
                        response = RPCResponse(
                            result=None,
                            error=str(e),
                            id=request.id
                        )
                else:
                    response = RPCResponse(
                        result=None,
                        error=f"方法不存在: {request.method}",
                        id=request.id
                    )
                    
                # 发送响应
                if request.id and client_id in self.response_queues:
                    self.response_queues[client_id].put(response)
                    
            except Exception as e:
                if self.running:
                    self.logger.error(f"处理请求失败: {str(e)}") 
            
    def _handle_heartbeat(self, client_id: str):
        """处理心跳请求"""
        if client_id in self.clients:
            return {'status': 'ok'}
        return {'status': 'error'}
        
    def _handle_client_timeout(self, client_id: str):
        """处理客户端超时"""
        self.logger.warning(f"客户端 {client_id} 心跳超时")
        if client_id in self.clients:
            self.clients[client_id].close() 