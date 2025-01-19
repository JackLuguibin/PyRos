from typing import Dict, List, Optional
import numpy as np
import logging
import zmq
import json
from threading import Thread, Lock
from .advanced_controller import AdvancedController
import time
import hashlib
import zlib
import base64
import copy

class DistributedController(AdvancedController):
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        
        # ZMQ通信
        self.context = zmq.Context()
        self.publisher = self.context.socket(zmq.PUB)
        self.subscriber = self.context.socket(zmq.SUB)
        
        # 配置网络
        self.node_id = config.get('node_id', 'node0')
        self.peers = config.get('peers', [])
        
        pub_port = config.get('pub_port', 5555)
        self.publisher.bind(f"tcp://*:{pub_port}")
        
        for peer in self.peers:
            self.subscriber.connect(f"tcp://{peer['host']}:{peer['port']}")
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, peer['id'])
            
        # 共享状态
        self.shared_state: Dict = {}
        self.state_lock = Lock()
        
        # 启动接收线程
        self.running = True
        self.receiver_thread = Thread(target=self._receive_loop)
        self.receiver_thread.start()
        
        # 初始化容错机制
        self._init_fault_tolerance()
        
        # 初始化网络协议
        self._init_network_protocol()
        
    def _compute_control(self, state: Dict,
                        predicted_action: Dict,
                        dt: float) -> Dict:
        """计算分布式控制输出"""
        # 发布本地状态
        self._publish_state(state)
        
        # 获取共享状态
        with self.state_lock:
            shared_state = self.shared_state.copy()
            
        # 计算一致性控制
        output = self._compute_consensus(state, shared_state)
        
        return output
        
    def _compute_consensus(self, local_state: Dict,
                          shared_state: Dict) -> Dict:
        """计算一致性控制"""
        outputs = {}
        
        # 计算平均状态
        avg_state = self._compute_average_state(local_state, shared_state)
        
        # 生成一致性控制
        for key in local_state:
            if key in avg_state:
                # 向平均状态靠拢
                error = avg_state[key] - local_state[key]
                outputs[key] = error * 0.5  # 简单比例控制
                
        return outputs
        
    def _compute_average_state(self, local_state: Dict,
                             shared_state: Dict) -> Dict:
        """计算平均状态"""
        avg_state = {}
        
        # 合并所有状态
        all_states = [local_state]
        for node_id, state in shared_state.items():
            if isinstance(state, dict):
                all_states.append(state)
                
        # 计算平均值
        for key in local_state:
            values = []
            for state in all_states:
                if key in state:
                    values.append(state[key])
            if values:
                avg_state[key] = np.mean(values)
                
        return avg_state
        
    def _publish_state(self, state: Dict):
        """发布状态"""
        message = {
            'node_id': self.node_id,
            'state': state,
            'timestamp': time.time()
        }
        
        try:
            self.publisher.send_string(
                f"{self.node_id} {json.dumps(message)}"
            )
        except Exception as e:
            self.logger.error(f"发布状态失败: {str(e)}")
            
    def _receive_loop(self):
        """接收循环"""
        while self.running:
            try:
                message = self.subscriber.recv_string()
                node_id, data = message.split(' ', 1)
                data = json.loads(data)
                
                with self.state_lock:
                    self.shared_state[node_id] = data['state']
                    
            except Exception as e:
                self.logger.error(f"接收状态失败: {str(e)}")
                
    def reset(self):
        """重置控制器"""
        super().reset()
        with self.state_lock:
            self.shared_state.clear()
            
    def __del__(self):
        """清理资源"""
        self.running = False
        if hasattr(self, 'receiver_thread'):
            self.receiver_thread.join()
        self.publisher.close()
        self.subscriber.close()
        self.context.term()
        
    def _init_fault_tolerance(self):
        """初始化容错机制"""
        # 心跳检测
        self.heartbeat_interval = self.config.get('heartbeat_interval', 1.0)
        self.heartbeat_timeout = self.config.get('heartbeat_timeout', 3.0)
        self.last_heartbeats = {}
        
        # 状态一致性检查
        self.state_versions = {}
        self.version_conflicts = {}
        
        # 网络分区检测
        self.quorum_size = len(self.peers) // 2 + 1
        self.partition_timeout = self.config.get('partition_timeout', 5.0)
        
        # 启动心跳线程
        self.heartbeat_thread = Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.start()
        
    def _heartbeat_loop(self):
        """心跳检测循环"""
        while self.running:
            try:
                # 发送心跳
                self._send_heartbeat()
                
                # 检查超时节点
                self._check_timeouts()
                
                # 检查网络分区
                self._check_partition()
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"心跳检测错误: {str(e)}")
                
    def _send_heartbeat(self):
        """发送心跳"""
        message = {
            'type': 'heartbeat',
            'node_id': self.node_id,
            'timestamp': time.time(),
            'state_version': self._get_state_version()
        }
        
        try:
            self.publisher.send_string(
                f"{self.node_id} {json.dumps(message)}"
            )
        except Exception as e:
            self.logger.error(f"发送心跳失败: {str(e)}")
            
    def _check_timeouts(self):
        """检查超时节点"""
        current_time = time.time()
        
        for peer in self.peers:
            node_id = peer['id']
            last_time = self.last_heartbeats.get(node_id, 0)
            
            if current_time - last_time > self.heartbeat_timeout:
                self._handle_node_failure(node_id)
                
    def _handle_node_failure(self, node_id: str):
        """处理节点失败"""
        self.logger.warning(f"节点 {node_id} 可能已失效")
        
        # 从共享状态中移除
        with self.state_lock:
            if node_id in self.shared_state:
                del self.shared_state[node_id]
                
        # 更新网络拓扑
        self.peers = [p for p in self.peers if p['id'] != node_id]
        
    def _check_partition(self):
        """检查网络分区"""
        active_nodes = len([t for t in self.last_heartbeats.values()
                           if time.time() - t < self.partition_timeout])
        
        if active_nodes < self.quorum_size:
            self._handle_network_partition()
            
    def _handle_network_partition(self):
        """处理网络分区"""
        self.logger.warning("检测到网络分区")
        
        # 进入安全模式
        self._enter_safe_mode()
        
    def _enter_safe_mode(self):
        """进入安全模式"""
        # 停止状态同步
        with self.state_lock:
            self.shared_state.clear()
            
        # 使用保守控制策略
        self._use_conservative_control()
        
    def _use_conservative_control(self):
        """使用保守控制策略"""
        # 降低控制增益
        self.control_gain *= 0.5
        
        # 限制输出范围
        self.output_limit *= 0.5
        
    def _get_state_version(self) -> str:
        """获取状态版本"""
        # 使用状态的哈希作为版本
        state_str = json.dumps(self.local_state, sort_keys=True)
        return hashlib.md5(state_str.encode()).hexdigest()
        
    def _check_state_consistency(self):
        """检查状态一致性"""
        # 统计版本
        version_counts = {}
        for node_id, version in self.state_versions.items():
            version_counts[version] = version_counts.get(version, 0) + 1
            
        # 检测冲突
        max_count = max(version_counts.values())
        if max_count < self.quorum_size:
            self._resolve_state_conflict()
            
    def _resolve_state_conflict(self):
        """解决状态冲突"""
        self.logger.warning("检测到状态冲突")
        
        # 请求状态同步
        self._request_state_sync()
        
    def _request_state_sync(self):
        """请求状态同步"""
        message = {
            'type': 'sync_request',
            'node_id': self.node_id,
            'timestamp': time.time()
        }
        
        try:
            self.publisher.send_string(
                f"{self.node_id} {json.dumps(message)}"
            )
        except Exception as e:
            self.logger.error(f"请求同步失败: {str(e)}")
            
    def _init_network_protocol(self):
        """初始化网络协议"""
        # 消息序列号
        self.message_seq = 0
        self.received_seqs = {}
        
        # 消息重传
        self.retransmit_timeout = self.config.get('retransmit_timeout', 0.5)
        self.max_retries = self.config.get('max_retries', 3)
        self.pending_messages = {}
        
        # 消息压缩
        self.compression_enabled = self.config.get('compression_enabled', True)
        self.compression_level = self.config.get('compression_level', 6)
        
        # 带宽控制
        self.bandwidth_limit = self.config.get('bandwidth_limit', 1000000)  # 1MB/s
        self.message_queue = []
        self.last_send_time = time.time()
        
    def _send_message(self, message: Dict):
        """发送消息"""
        # 添加序列号
        message['seq'] = self.message_seq
        self.message_seq += 1
        
        # 压缩消息
        if self.compression_enabled:
            message_data = self._compress_message(message)
        else:
            message_data = json.dumps(message)
            
        # 添加到待发送队列
        self.message_queue.append({
            'data': message_data,
            'size': len(message_data),
            'time': time.time(),
            'retries': 0
        })
        
        # 发送队列中的消息
        self._process_message_queue()
        
    def _process_message_queue(self):
        """处理消息队列"""
        current_time = time.time()
        elapsed = current_time - self.last_send_time
        
        # 计算可用带宽
        available_bytes = int(self.bandwidth_limit * elapsed)
        
        while self.message_queue and available_bytes > 0:
            message = self.message_queue[0]
            
            if message['size'] <= available_bytes:
                # 发送消息
                try:
                    self.publisher.send_string(
                        f"{self.node_id} {message['data']}"
                    )
                    self.message_queue.pop(0)
                    available_bytes -= message['size']
                except Exception as e:
                    self.logger.error(f"发送消息失败: {str(e)}")
                    
                    # 重试处理
                    if message['retries'] < self.max_retries:
                        message['retries'] += 1
                        message['time'] = current_time
                    else:
                        self.message_queue.pop(0)
            else:
                break
            
        self.last_send_time = current_time
        
    def _compress_message(self, message: Dict) -> str:
        """压缩消息"""
        message_str = json.dumps(message)
        compressed = zlib.compress(
            message_str.encode(),
            level=self.compression_level
        )
        return base64.b64encode(compressed).decode()
        
    def _decompress_message(self, data: str) -> Dict:
        """解压消息"""
        compressed = base64.b64decode(data)
        decompressed = zlib.decompress(compressed)
        return json.loads(decompressed.decode())
        
    def _handle_message(self, message: Dict):
        """处理接收到的消息"""
        # 检查序列号
        seq = message.get('seq')
        if seq is None:
            return
        
        node_id = message.get('node_id')
        if node_id is None:
            return
        
        # 检查是否重复消息
        last_seq = self.received_seqs.get(node_id, -1)
        if seq <= last_seq:
            return
        
        self.received_seqs[node_id] = seq
        
        # 处理不同类型的消息
        message_type = message.get('type')
        if message_type == 'state':
            self._handle_state_message(message)
        elif message_type == 'heartbeat':
            self._handle_heartbeat_message(message)
        elif message_type == 'sync_request':
            self._handle_sync_request(message)
        elif message_type == 'sync_response':
            self._handle_sync_response(message)
        
    def _init_recovery(self):
        """初始化故障恢复"""
        # 状态快照
        self.state_snapshots = []
        self.max_snapshots = self.config.get('max_snapshots', 10)
        
        # 故障检测
        self.fault_detectors = {
            'timeout': self._detect_timeout,
            'state_divergence': self._detect_state_divergence,
            'performance_degradation': self._detect_performance_degradation
        }
        
        # 恢复策略
        self.recovery_strategies = {
            'timeout': self._recover_from_timeout,
            'state_divergence': self._recover_from_divergence,
            'performance_degradation': self._recover_from_degradation
        }
        
    def _create_snapshot(self):
        """创建状态快照"""
        snapshot = {
            'state': copy.deepcopy(self.local_state),
            'shared_state': copy.deepcopy(self.shared_state),
            'timestamp': time.time(),
            'metrics': self.get_metrics()
        }
        
        self.state_snapshots.append(snapshot)
        if len(self.state_snapshots) > self.max_snapshots:
            self.state_snapshots.pop(0)
            
    def _detect_faults(self):
        """检测故障"""
        faults = []
        
        for name, detector in self.fault_detectors.items():
            if detector():
                faults.append(name)
                
        return faults
        
    def _recover_from_faults(self, faults: List[str]):
        """从故障中恢复"""
        for fault in faults:
            strategy = self.recovery_strategies.get(fault)
            if strategy:
                try:
                    strategy()
                except Exception as e:
                    self.logger.error(f"恢复失败 {fault}: {str(e)}")
                    
    def _detect_timeout(self) -> bool:
        """检测超时"""
        current_time = time.time()
        return any(current_time - t > self.heartbeat_timeout * 2
                  for t in self.last_heartbeats.values())
                  
    def _detect_state_divergence(self) -> bool:
        """检测状态发散"""
        if not self.state_snapshots:
            return False
            
        last_snapshot = self.state_snapshots[-1]
        current_state = self.local_state
        
        # 计算状态差异
        diff = 0
        for key in current_state:
            if key in last_snapshot['state']:
                diff += abs(current_state[key] - last_snapshot['state'][key])
                
        return diff > self.config.get('divergence_threshold', 10.0)
        
    def _detect_performance_degradation(self) -> bool:
        """检测性能下降"""
        if len(self.performance_metrics['mse']) < 100:
            return False
            
        recent_mse = np.mean(self.performance_metrics['mse'][-100:])
        baseline_mse = np.mean(self.performance_metrics['mse'][-500:-100])
        
        return recent_mse > baseline_mse * 1.5
        
    def _recover_from_timeout(self):
        """从超时中恢复"""
        # 重新初始化网络连接
        self._reinit_network()
        
        # 请求状态同步
        self._request_state_sync()
        
    def _recover_from_divergence(self):
        """从状态发散中恢复"""
        # 回滚到最近的稳定状态
        if self.state_snapshots:
            last_stable = self.state_snapshots[-1]
            self.local_state = copy.deepcopy(last_stable['state'])
            
        # 重新同步状态
        self._request_state_sync()
        
    def _recover_from_degradation(self):
        """从性能下降中恢复"""
        # 重置控制器参数
        self._reset_control_params()
        
        # 清理性能指标
        self.performance_metrics['mse'] = []
        self.performance_metrics['mae'] = [] 