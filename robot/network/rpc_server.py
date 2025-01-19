from xmlrpc.server import SimpleXMLRPCServer
import threading
from typing import Optional, List, Dict
from ..core.manager import RobotManager
import logging

class RobotRPCServer:
    def __init__(self, robot: RobotManager, host: str = "0.0.0.0", port: int = 8000):
        self.robot = robot
        self.server = SimpleXMLRPCServer((host, port), allow_none=True)
        self.server_thread: Optional[threading.Thread] = None
        self._register_functions()
        
    def _register_functions(self):
        """注册RPC函数"""
        # 基本控制
        self.server.register_function(self.set_servo_angle, "set_servo_angle")
        self.server.register_function(self.get_sensor_data, "get_sensor_data")
        
        # 动作组控制
        self.server.register_function(self.execute_action_group, "execute_action_group")
        self.server.register_function(self.stop_action_group, "stop_action_group")
        self.server.register_function(self.stop_all_groups, "stop_all_groups")
        
        # 动作录制
        self.server.register_function(self.start_recording, "start_recording")
        self.server.register_function(self.stop_recording, "stop_recording")
        self.server.register_function(self.save_recorded_actions, "save_recorded_actions")
        
    def start(self):
        """启动RPC服务器"""
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        print(f"RPC服务器已启动在 http://localhost:8000")
        
    def stop(self):
        """停止RPC服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            
    # RPC方法
    def execute_action_group(self, group_name: str, parallel: bool = False) -> bool:
        """执行动作组"""
        try:
            return self.robot.action_manager.execute_action_group(group_name, parallel)
        except Exception as e:
            print(f"执行动作组出错: {e}")
            return False
            
    def set_servo_angle(self, servo_id: str, angle: float) -> bool:
        """设置舵机角度"""
        try:
            self.robot.servo_manager.set_angle(servo_id, angle)
            return True
        except Exception as e:
            print(f"设置舵机角度出错: {e}")
            return False
            
    def get_sensor_data(self, sensor_id: str):
        """获取传感器数据"""
        try:
            return self.robot.sensor_manager.get_sensor_data(sensor_id)
        except Exception as e:
            print(f"读取传感器数据出错: {e}")
            return None
            
    def stop_action_group(self, group_name: str) -> bool:
        """停止动作组"""
        try:
            self.robot.action_manager.stop_action_group(group_name)
            return True
        except Exception as e:
            print(f"停止动作组出错: {e}")
            return False
            
    def stop_all_groups(self) -> bool:
        """停止所有动作组"""
        try:
            self.robot.action_manager.stop_all_groups()
            return True
        except Exception as e:
            print(f"停止所有动作组出错: {e}")
            return False
            
    def start_recording(self) -> bool:
        """开始录制动作"""
        try:
            self.robot.action_recorder.start_recording()
            return True
        except Exception as e:
            print(f"开始录制出错: {e}")
            return False
            
    def stop_recording(self) -> List[Dict]:
        """停止录制动作"""
        try:
            return self.robot.action_recorder.stop_recording()
        except Exception as e:
            print(f"停止录制出错: {e}")
            return []
            
    def save_recorded_actions(self, group_name: str) -> bool:
        """保存录制的动作组"""
        try:
            actions = self.robot.action_recorder.stop_recording()
            return self.robot.action_recorder.save_action_group(group_name, actions)
        except Exception as e:
            print(f"保存动作组出错: {e}")
            return False 