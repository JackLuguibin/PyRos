from xmlrpc.server import SimpleXMLRPCServer
import threading
from typing import Optional
from ..core.manager import RobotManager

class RobotRPCServer:
    def __init__(self, robot: RobotManager, host: str = "0.0.0.0", port: int = 8000):
        self.robot = robot
        self.server = SimpleXMLRPCServer((host, port), allow_none=True)
        self.server_thread: Optional[threading.Thread] = None
        self._register_functions()
        
    def _register_functions(self):
        """注册RPC函数"""
        # 动作组控制
        self.server.register_function(self.execute_action_group, "execute_action_group")
        # 舵机控制
        self.server.register_function(self.set_servo_angle, "set_servo_angle")
        # 传感器读取
        self.server.register_function(self.get_sensor_data, "get_sensor_data")
        
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
    def execute_action_group(self, group_name: str) -> bool:
        """执行动作组"""
        try:
            self.robot.action_manager.execute_action_group(group_name)
            return True
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