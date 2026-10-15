"""
Detection of bowling deliveries in video.
"""

import numpy as np
from typing import List, Dict, Tuple


class DeliveryDetector:
    """Detects bowling delivery sequences in video."""
    
    def __init__(self, min_motion_threshold: float = 0.02, 
                 min_delivery_frames: int = 20,
                 max_delivery_frames: int = 100):
        """
        Initialize delivery detector.
        
        Args:
            min_motion_threshold: Minimum wrist motion to consider as active
            min_delivery_frames: Minimum frames for a valid delivery
            max_delivery_frames: Maximum frames for a delivery sequence
        """
        self.min_motion_threshold = min_motion_threshold
        self.min_delivery_frames = min_delivery_frames
        self.max_delivery_frames = max_delivery_frames
    
    def detect_deliveries(self, landmarks_list: List[Dict], 
                         bowling_arm: str) -> List[Tuple[int, int]]:
        """
        Detect delivery sequences based on bowling arm motion.
        
        Args:
            landmarks_list: List of frame data with landmarks
            bowling_arm: 'left' or 'right'
            
        Returns:
            List of (start_frame, end_frame) tuples for each delivery
        """
        from .phase_detector import PhaseDetector
        
        _, _, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        # Calculate wrist motion for each frame
        motion_scores = self._calculate_motion_scores(landmarks_list, wrist_idx)
        
        # Find active periods
        active_periods = self._find_active_periods(motion_scores)
        
        # Filter and merge periods into deliveries
        deliveries = self._merge_into_deliveries(active_periods)
        
        return deliveries
    
    def _calculate_motion_scores(self, landmarks_list: List[Dict], 
                                 wrist_idx: int) -> List[float]:
        """Calculate motion score for each frame."""
        motion_scores = [0.0]
        
        for i in range(1, len(landmarks_list)):
            prev_frame = landmarks_list[i-1]
            curr_frame = landmarks_list[i]
            
            if not (prev_frame['landmarks'] and curr_frame['landmarks']):
                motion_scores.append(0.0)
                continue
            
            if wrist_idx not in prev_frame['landmarks'] or \
               wrist_idx not in curr_frame['landmarks']:
                motion_scores.append(0.0)
                continue
            
            prev_wrist = np.array([
                prev_frame['landmarks'][wrist_idx]['x'],
                prev_frame['landmarks'][wrist_idx]['y'],
                prev_frame['landmarks'][wrist_idx]['z']
            ])
            curr_wrist = np.array([
                curr_frame['landmarks'][wrist_idx]['x'],
                curr_frame['landmarks'][wrist_idx]['y'],
                curr_frame['landmarks'][wrist_idx]['z']
            ])
            
            motion = np.linalg.norm(curr_wrist - prev_wrist)
            motion_scores.append(motion)
        
        return motion_scores
    
    def _find_active_periods(self, motion_scores: List[float]) -> List[Tuple[int, int]]:
        """Find continuous periods of motion above threshold."""
        active_periods = []
        in_active = False
        start_frame = 0
        
        for i, score in enumerate(motion_scores):
            if not in_active and score > self.min_motion_threshold:
                in_active = True
                start_frame = i
            elif in_active and score <= self.min_motion_threshold:
                in_active = False
                if i - start_frame >= self.min_delivery_frames:
                    active_periods.append((start_frame, i))
        
        if in_active and len(motion_scores) - start_frame >= self.min_delivery_frames:
            active_periods.append((start_frame, len(motion_scores)))
        
        return active_periods
    
    def _merge_into_deliveries(self, active_periods: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merge and filter active periods into delivery sequences."""
        if not active_periods:
            return []
        
        deliveries = []
        current_start, current_end = active_periods[0]
        
        for start, end in active_periods[1:]:
            # If gap is small, merge
            if start - current_end < 10:
                current_end = end
            else:
                # Save current delivery if valid
                if current_end - current_start <= self.max_delivery_frames:
                    deliveries.append((current_start, current_end))
                current_start, current_end = start, end
        
        # Don't forget last delivery
        if current_end - current_start <= self.max_delivery_frames:
            deliveries.append((current_start, current_end))
        
        return deliveries
