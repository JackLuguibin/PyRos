from typing import List, Dict, Optional
import numpy as np
import logging
from .analyzer import ActionAnalyzer

class ActionEvaluator:
    def __init__(self, logger: logging.Logger = None):
        """动作评分器"""
        self.logger = logger
        self.analyzer = ActionAnalyzer(logger)
        
    def evaluate_action(self, frames: List[Dict]) -> Dict:
        """评估动作质量
        
        Returns:
            评分结果
        """
        scores = {
            'smoothness': self._evaluate_smoothness(frames),
            'efficiency': self._evaluate_efficiency(frames),
            'stability': self._evaluate_stability(frames),
            'complexity': self._evaluate_complexity(frames),
            'symmetry': self._evaluate_symmetry(frames)
        }
        
        # 计算总分
        weights = {
            'smoothness': 0.25,
            'efficiency': 0.2,
            'stability': 0.25,
            'complexity': 0.15,
            'symmetry': 0.15
        }
        
        total_score = sum(score * weights[key] 
                         for key, score in scores.items())
        
        return {
            'total_score': total_score,
            'detailed_scores': scores,
            'suggestions': self._generate_suggestions(scores)
        }
        
    def _evaluate_smoothness(self, frames: List[Dict]) -> float:
        """评估动作平滑度"""
        if len(frames) < 3:
            return 1.0
            
        jerk_scores = []
        for i in range(2, len(frames)):
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                if servo_id in frames[i-1] and servo_id in frames[i-2]:
                    # 计算加加速度
                    dt = frames[i-1].get('delay', 0.02)
                    jerk = abs(frames[i][servo_id] - 2*frames[i-1][servo_id] +
                             frames[i-2][servo_id]) / (dt * dt * dt)
                    
                    # 将加加速度映射到0-1分数
                    score = 1.0 / (1.0 + jerk * 0.001)
                    jerk_scores.append(score)
                    
        return np.mean(jerk_scores) if jerk_scores else 1.0
        
    def _evaluate_efficiency(self, frames: List[Dict]) -> float:
        """评估动作效率"""
        if len(frames) < 2:
            return 1.0
            
        # 分析能量消耗
        total_energy = 0
        useful_movement = 0
        
        for i in range(1, len(frames)):
            dt = frames[i-1].get('delay', 0.02)
            
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                if servo_id in frames[i-1]:
                    # 计算速度和位移
                    velocity = abs(frames[i][servo_id] - 
                                 frames[i-1][servo_id]) / dt
                    displacement = abs(frames[i][servo_id] - 
                                    frames[i-1][servo_id])
                    
                    # 累计能量和有效运动
                    total_energy += velocity * velocity * dt
                    useful_movement += displacement
                    
        # 计算效率得分
        if total_energy == 0:
            return 1.0
            
        efficiency = useful_movement / (total_energy ** 0.5)
        return min(1.0, efficiency * 0.1)  # 归一化到0-1
        
    def _evaluate_stability(self, frames: List[Dict]) -> float:
        """评估动作稳定性"""
        if len(frames) < 2:
            return 1.0
            
        # 分析速度变化
        velocity_changes = []
        
        for i in range(2, len(frames)):
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                if servo_id in frames[i-1] and servo_id in frames[i-2]:
                    dt = frames[i-1].get('delay', 0.02)
                    
                    v1 = (frames[i-1][servo_id] - frames[i-2][servo_id]) / dt
                    v2 = (frames[i][servo_id] - frames[i-1][servo_id]) / dt
                    
                    velocity_change = abs(v2 - v1)
                    velocity_changes.append(velocity_change)
                    
        if not velocity_changes:
            return 1.0
            
        # 计算稳定性得分
        stability = 1.0 / (1.0 + np.std(velocity_changes))
        return min(1.0, stability)
        
    def _evaluate_complexity(self, frames: List[Dict]) -> float:
        """评估动作复杂度"""
        # 分析方向变化
        direction_changes = 0
        total_movements = 0
        
        for i in range(1, len(frames)):
            for servo_id in frames[i]:
                if servo_id == 'delay':
                    continue
                    
                if servo_id in frames[i-1]:
                    movement = frames[i][servo_id] - frames[i-1][servo_id]
                    if abs(movement) > 0.1:  # 忽略微小变化
                        total_movements += 1
                        if i > 1 and servo_id in frames[i-2]:
                            prev_movement = frames[i-1][servo_id] - frames[i-2][servo_id]
                            if np.sign(movement) != np.sign(prev_movement):
                                direction_changes += 1
                                
        if total_movements == 0:
            return 1.0
            
        # 计算复杂度得分
        complexity_ratio = direction_changes / total_movements
        return 1.0 - min(1.0, complexity_ratio * 2)
        
    def _evaluate_symmetry(self, frames: List[Dict]) -> float:
        """评估动作对称性"""
        # 检测可能的对称舵机对
        servo_ids = set()
        for frame in frames:
            servo_ids.update(k for k in frame.keys() if k != 'delay')
            
        # 假设左右对称的舵机ID包含'left'/'right'
        left_servos = {s for s in servo_ids if 'left' in s.lower()}
        right_servos = {s for s in servo_ids if 'right' in s.lower()}
        
        if not left_servos or not right_servos:
            return 1.0  # 无法评估对称性
            
        # 计算对称性得分
        symmetry_scores = []
        
        for left in left_servos:
            right = left.lower().replace('left', 'right')
            if right in right_servos:
                for frame in frames:
                    if left in frame and right in frame:
                        # 计算对称差异
                        diff = abs(frame[left] - frame[right])
                        score = 1.0 / (1.0 + diff * 0.1)
                        symmetry_scores.append(score)
                        
        return np.mean(symmetry_scores) if symmetry_scores else 1.0
        
    def _generate_suggestions(self, scores: Dict) -> List[Dict]:
        """生成改进建议"""
        suggestions = []
        
        # 平滑度建议
        if scores['smoothness'] < 0.7:
            suggestions.append({
                'aspect': 'smoothness',
                'score': scores['smoothness'],
                'message': '动作不够平滑，建议：\n'
                          '1. 增加过渡帧\n'
                          '2. 减小加速度\n'
                          '3. 使用平滑插值'
            })
            
        # 效率建议
        if scores['efficiency'] < 0.6:
            suggestions.append({
                'aspect': 'efficiency',
                'score': scores['efficiency'],
                'message': '动作效率较低，建议：\n'
                          '1. 减少不必要的运动\n'
                          '2. 优化运动路径\n'
                          '3. 调整速度曲线'
            })
            
        # 稳定性建议
        if scores['stability'] < 0.7:
            suggestions.append({
                'aspect': 'stability',
                'score': scores['stability'],
                'message': '动作稳定性不足，建议：\n'
                          '1. 控制速度变化\n'
                          '2. 避免突然加速\n'
                          '3. 增加关键帧'
            })
            
        # 复杂度建议
        if scores['complexity'] < 0.5:
            suggestions.append({
                'aspect': 'complexity',
                'score': scores['complexity'],
                'message': '动作过于复杂，建议：\n'
                          '1. 简化动作序列\n'
                          '2. 减少方向变化\n'
                          '3. 合并相似动作'
            })
            
        # 对称性建议
        if scores['symmetry'] < 0.8:
            suggestions.append({
                'aspect': 'symmetry',
                'score': scores['symmetry'],
                'message': '动作对称性不足，建议：\n'
                          '1. 检查对称舵机角度\n'
                          '2. 调整不对称动作\n'
                          '3. 使用镜像功能'
            })
            
        return suggestions 

    def generate_report(self, frames: List[Dict], 
                       save_path: Optional[str] = None) -> Dict:
        """生成详细的评估报告
        
        Args:
            frames: 动作序列
            save_path: 报告保存路径
            
        Returns:
            评估报告数据
        """
        # 基础评分
        evaluation = self.evaluate_action(frames)
        
        # 添加详细分析
        report = {
            'summary': evaluation,
            'details': {
                'frame_analysis': self._analyze_frames(frames),
                'servo_analysis': self._analyze_servos(frames),
                'timing_analysis': self._analyze_timing(frames),
                'pattern_analysis': self._analyze_patterns(frames)
            },
            'visualizations': self._generate_visualizations(frames)
        }
        
        # 保存报告
        if save_path:
            self._save_report(report, save_path)
        
        return report
        
    def _analyze_frames(self, frames: List[Dict]) -> Dict:
        """分析每一帧的特征"""
        frame_analysis = []
        
        for i, frame in enumerate(frames):
            analysis = {
                'frame_index': i,
                'active_servos': len([k for k in frame.keys() if k != 'delay']),
                'delay': frame.get('delay', 0.02)
            }
            
            if i > 0:
                # 计算与前一帧的差异
                changes = {}
                for servo_id in frame:
                    if servo_id == 'delay':
                        continue
                    if servo_id in frames[i-1]:
                        changes[servo_id] = abs(frame[servo_id] - 
                                             frames[i-1][servo_id])
                analysis['changes'] = changes
                analysis['max_change'] = max(changes.values()) if changes else 0
            
            frame_analysis.append(analysis)
        
        return {
            'frames': frame_analysis,
            'statistics': {
                'total_frames': len(frames),
                'avg_delay': np.mean([f.get('delay', 0.02) for f in frames]),
                'max_servo_change': max(f.get('max_change', 0) 
                                      for f in frame_analysis[1:])
            }
        }
        
    def _analyze_servos(self, frames: List[Dict]) -> Dict:
        """分析每个舵机的运动特征"""
        servo_stats = {}
        
        # 获取所有舵机ID
        servo_ids = set()
        for frame in frames:
            servo_ids.update(k for k in frame.keys() if k != 'delay')
        
        for servo_id in servo_ids:
            angles = []
            velocities = []
            accelerations = []
            
            for i, frame in enumerate(frames):
                if servo_id in frame:
                    angles.append(frame[servo_id])
                    
                    if i > 0 and servo_id in frames[i-1]:
                        dt = frames[i-1].get('delay', 0.02)
                        v = (frame[servo_id] - frames[i-1][servo_id]) / dt
                        velocities.append(v)
                        
                        if i > 1 and servo_id in frames[i-2]:
                            a = (v - (frames[i-1][servo_id] - 
                                 frames[i-2][servo_id]) / dt) / dt
                            accelerations.append(a)
                        
            servo_stats[servo_id] = {
                'angle_range': (min(angles), max(angles)),
                'total_movement': sum(abs(angles[i] - angles[i-1]) 
                                    for i in range(1, len(angles))),
                'avg_velocity': np.mean(np.abs(velocities)) if velocities else 0,
                'max_velocity': max(np.abs(velocities)) if velocities else 0,
                'avg_acceleration': np.mean(np.abs(accelerations)) 
                                  if accelerations else 0,
                'direction_changes': sum(1 for i in range(1, len(velocities))
                                       if np.sign(velocities[i]) != 
                                       np.sign(velocities[i-1]))
                                       if len(velocities) > 1 else 0
            }
        
        return servo_stats
        
    def _analyze_timing(self, frames: List[Dict]) -> Dict:
        """分析时序特征"""
        delays = [frame.get('delay', 0.02) for frame in frames]
        
        return {
            'total_duration': sum(delays),
            'delay_stats': {
                'min': min(delays),
                'max': max(delays),
                'mean': np.mean(delays),
                'std': np.std(delays)
            },
            'timing_distribution': np.histogram(delays, bins=10)[0].tolist(),
            'timing_patterns': self._find_timing_patterns(delays)
        }
        
    def _analyze_patterns(self, frames: List[Dict]) -> Dict:
        """分析动作模式"""
        return {
            'repetitive_patterns': self._find_repetitive_patterns(frames),
            'synchronized_movements': self._analyze_synchronization(frames),
            'sequential_patterns': self._analyze_sequence_patterns(frames)
        }
        
    def _generate_visualizations(self, frames: List[Dict]) -> Dict:
        """生成可视化数据"""
        servo_ids = set()
        for frame in frames:
            servo_ids.update(k for k in frame.keys() if k != 'delay')
        
        visualizations = {
            'angle_trajectories': {},
            'velocity_profiles': {},
            'acceleration_profiles': {},
            'timing_distribution': self._get_timing_visualization(frames),
            'servo_coordination': self._get_coordination_visualization(frames)
        }
        
        # 生成每个舵机的轨迹数据
        for servo_id in servo_ids:
            angles = []
            times = []
            t = 0
            
            for frame in frames:
                if servo_id in frame:
                    angles.append(frame[servo_id])
                    times.append(t)
                t += frame.get('delay', 0.02)
            
            visualizations['angle_trajectories'][servo_id] = {
                'times': times,
                'angles': angles
            }
        
        return visualizations
        
    def _find_timing_patterns(self, delays: List[float]) -> List[Dict]:
        """查找时序模式"""
        patterns = []
        min_pattern_length = 3
        max_pattern_length = len(delays) // 2
        
        for length in range(min_pattern_length, max_pattern_length + 1):
            for start in range(len(delays) - length * 2):
                pattern = delays[start:start + length]
                next_segment = delays[start + length:start + length * 2]
                
                if np.allclose(pattern, next_segment, rtol=0.1):
                    patterns.append({
                        'start_index': start,
                        'length': length,
                        'pattern': pattern
                    })
        
        return patterns
        
    def _get_timing_visualization(self, frames: List[Dict]) -> Dict:
        """生成时序可视化数据"""
        delays = [frame.get('delay', 0.02) for frame in frames]
        hist, bins = np.histogram(delays, bins=20)
        
        return {
            'histogram': {
                'counts': hist.tolist(),
                'bins': bins.tolist()
            },
            'cumulative': np.cumsum(delays).tolist()
        }
        
    def _get_coordination_visualization(self, frames: List[Dict]) -> Dict:
        """生成舵机协调性可视化数据"""
        servo_ids = set()
        for frame in frames:
            servo_ids.update(k for k in frame.keys() if k != 'delay')
        
        coordination = {
            'correlation_matrix': {},
            'phase_plots': {}
        }
        
        # 计算舵机间的相关性
        for servo1 in servo_ids:
            coordination['correlation_matrix'][servo1] = {}
            for servo2 in servo_ids:
                if servo1 != servo2:
                    angles1 = []
                    angles2 = []
                    
                    for frame in frames:
                        if servo1 in frame and servo2 in frame:
                            angles1.append(frame[servo1])
                            angles2.append(frame[servo2])
                        
                    if angles1 and angles2:
                        correlation = np.corrcoef(angles1, angles2)[0, 1]
                        coordination['correlation_matrix'][servo1][servo2] = correlation
        
        return coordination
        
    def _save_report(self, report: Dict, save_path: str):
        """保存评估报告"""
        import json
        import os
        
        # 创建报告目录
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 保存JSON报告
        with open(save_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # 如果需要，生成HTML报告
        if save_path.endswith('.html'):
            self._generate_html_report(report, save_path)
        
    def _generate_html_report(self, report: Dict, save_path: str):
        """生成HTML格式的报告"""
        # 这里可以使用模板引擎生成漂亮的HTML报告
        # 包含图表、数据表格等
        pass 