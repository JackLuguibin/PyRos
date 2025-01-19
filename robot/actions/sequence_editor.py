import tkinter as tk
from tkinter import ttk
import yaml
import os
from typing import List, Dict
import logging

class ActionSequenceEditor:
    def __init__(self, servo_ids: List[str], logger: logging.Logger = None):
        self.servo_ids = servo_ids
        self.logger = logger
        self.sequences = []
        self.current_sequence = []
        
        self._create_gui()
        
    def _create_gui(self):
        """创建图形界面"""
        self.root = tk.Tk()
        self.root.title("动作序列编辑器")
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 舵机控制区域
        servo_frame = ttk.LabelFrame(main_frame, text="舵机控制", padding="5")
        servo_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.servo_controls = {}
        for i, servo_id in enumerate(self.servo_ids):
            ttk.Label(servo_frame, text=servo_id).grid(row=i, column=0)
            scale = ttk.Scale(servo_frame, from_=0, to=180, orient=tk.HORIZONTAL)
            scale.grid(row=i, column=1)
            self.servo_controls[servo_id] = scale
            
        # 序列控制区域
        sequence_frame = ttk.LabelFrame(main_frame, text="序列控制", padding="5")
        sequence_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(sequence_frame, text="添加关键帧",
                  command=self._add_keyframe).grid(row=0, column=0)
        ttk.Button(sequence_frame, text="删除关键帧",
                  command=self._delete_keyframe).grid(row=0, column=1)
        ttk.Button(sequence_frame, text="保存序列",
                  command=self._save_sequence).grid(row=0, column=2)
        
        # 序列显示区域
        self.sequence_list = tk.Listbox(main_frame, height=10)
        self.sequence_list.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        # 预览控制区域
        self._create_preview_controls()
        
    def _create_preview_controls(self):
        """创建预览控制区域"""
        preview_frame = ttk.LabelFrame(self.root, text="动作预览", padding="5")
        preview_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(preview_frame, text="预览选中帧",
                   command=self._preview_frame).grid(row=0, column=0)
        ttk.Button(preview_frame, text="预览整个序列",
                   command=self._preview_sequence).grid(row=0, column=1)
        
        # 预览速度控制
        ttk.Label(preview_frame, text="预览速度:").grid(row=0, column=2)
        self.speed_scale = ttk.Scale(preview_frame, from_=0.1, to=2.0,
                                    orient=tk.HORIZONTAL)
        self.speed_scale.set(1.0)
        self.speed_scale.grid(row=0, column=3)
        
    def _add_keyframe(self):
        """添加关键帧"""
        frame = {}
        for servo_id, scale in self.servo_controls.items():
            frame[servo_id] = scale.get()
            
        self.current_sequence.append(frame)
        self._update_sequence_display()
        
        if self.logger:
            self.logger.debug(f"添加关键帧: {frame}")
            
    def _delete_keyframe(self):
        """删除选中的关键帧"""
        selection = self.sequence_list.curselection()
        if selection:
            index = selection[0]
            del self.current_sequence[index]
            self._update_sequence_display()
            
    def _update_sequence_display(self):
        """更新序列显示"""
        self.sequence_list.delete(0, tk.END)
        for i, frame in enumerate(self.current_sequence):
            self.sequence_list.insert(tk.END, f"Frame {i+1}: {frame}")
            
    def _save_sequence(self):
        """保存当前序列"""
        if not self.current_sequence:
            return
            
        try:
            # 创建保存目录
            os.makedirs("sequences", exist_ok=True)
            
            # 生成序列名称
            sequence_name = f"sequence_{len(self.sequences)+1}"
            file_path = os.path.join("sequences", f"{sequence_name}.yaml")
            
            # 保存到YAML文件
            with open(file_path, 'w') as f:
                yaml.dump({sequence_name: self.current_sequence}, f)
                
            self.sequences.append(self.current_sequence)
            self.current_sequence = []
            self._update_sequence_display()
            
            if self.logger:
                self.logger.info(f"序列已保存到: {file_path}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"保存序列失败: {e}")
            
    def _preview_frame(self):
        """预览选中的关键帧"""
        selection = self.sequence_list.curselection()
        if not selection:
            return
        
        frame = self.current_sequence[selection[0]]
        if self.preview_callback:
            self.preview_callback(frame)
        
    def _preview_sequence(self):
        """预览整个动作序列"""
        if not self.current_sequence:
            return
        
        speed = self.speed_scale.get()
        if self.preview_sequence_callback:
            self.preview_sequence_callback(self.current_sequence, speed)
        
    def set_preview_callbacks(self, frame_callback=None, sequence_callback=None):
        """设置预览回调函数"""
        self.preview_callback = frame_callback
        self.preview_sequence_callback = sequence_callback
        
    def run(self):
        """运行编辑器"""
        self.root.mainloop() 