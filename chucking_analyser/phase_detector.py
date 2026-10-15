"""
Detection of bowling phases: arm horizontal and ball release.
"""

import numpy as np
from typing import List, Optional, Dict, Tuple


class PhaseDetector:
    """Detects key phases in bowling action."""
    
    # MediaPipe Pose landmark indices
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    
    @staticmethod
    def detect_bowling_arm(landmarks_list: List[Dict]) -> str:
        """
        Detect which arm is the bowling arm based on motion.
        
        Args:
            landmarks_list: List of frame data with landmarks
            
        Returns:
            'left' or 'right' indicating bowling arm
        """
        left_wrist_motion = 0.0
        right_wrist_motion = 0.0
        
        for i in range(1, len(landmarks_list)):
            prev_frame = landmarks_list[i-1]
            curr_frame = landmarks_list[i]
            
            if prev_frame['landmarks'] and curr_frame['landmarks']:
                # Left wrist motion
                if PhaseDetector.LEFT_WRIST in prev_frame['landmarks'] and \
                   PhaseDetector.LEFT_WRIST in curr_frame['landmarks']:
                    prev_pos = np.array([
                        prev_frame['landmarks'][PhaseDetector.LEFT_WRIST]['x'],
                        prev_frame['landmarks'][PhaseDetector.LEFT_WRIST]['y']
                    ])
                    curr_pos = np.array([
                        curr_frame['landmarks'][PhaseDetector.LEFT_WRIST]['x'],
                        curr_frame['landmarks'][PhaseDetector.LEFT_WRIST]['y']
                    ])
                    left_wrist_motion += np.linalg.norm(curr_pos - prev_pos)
                
                # Right wrist motion
                if PhaseDetector.RIGHT_WRIST in prev_frame['landmarks'] and \
                   PhaseDetector.RIGHT_WRIST in curr_frame['landmarks']:
                    prev_pos = np.array([
                        prev_frame['landmarks'][PhaseDetector.RIGHT_WRIST]['x'],
                        prev_frame['landmarks'][PhaseDetector.RIGHT_WRIST]['y']
                    ])
                    curr_pos = np.array([
                        curr_frame['landmarks'][PhaseDetector.RIGHT_WRIST]['x'],
                        curr_frame['landmarks'][PhaseDetector.RIGHT_WRIST]['y']
                    ])
                    right_wrist_motion += np.linalg.norm(curr_pos - prev_pos)
        
        return 'left' if left_wrist_motion > right_wrist_motion else 'right'
    
    @staticmethod
    def get_arm_landmarks(bowling_arm: str) -> Tuple[int, int, int]:
        """
        Get MediaPipe landmark indices for the bowling arm.
        
        Args:
            bowling_arm: 'left' or 'right'
            
        Returns:
            Tuple of (shoulder_idx, elbow_idx, wrist_idx)
        """
        if bowling_arm == 'left':
            return (PhaseDetector.LEFT_SHOULDER, 
                   PhaseDetector.LEFT_ELBOW, 
                   PhaseDetector.LEFT_WRIST)
        else:
            return (PhaseDetector.RIGHT_SHOULDER, 
                   PhaseDetector.RIGHT_ELBOW, 
                   PhaseDetector.RIGHT_WRIST)
    
    @staticmethod
    def detect_arm_horizontal(landmarks_list: List[Dict], bowling_arm: str,
                             start_frame: int = 0, end_frame: Optional[int] = None) -> Optional[int]:
        """
        Detect frame where bowling arm reaches horizontal position.
        
        Args:
            landmarks_list: List of frame data with landmarks
            bowling_arm: 'left' or 'right'
            start_frame: Start searching from this frame
            end_frame: Stop searching at this frame (None = end of video)
            
        Returns:
            Frame index where arm is horizontal, or None if not found
        """
        shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        if end_frame is None:
            end_frame = len(landmarks_list)
        
        best_frame = None
        best_score = float('inf')
        
        for i in range(start_frame, min(end_frame, len(landmarks_list))):
            frame_data = landmarks_list[i]
            
            if not frame_data['landmarks']:
                continue
            
            landmarks = frame_data['landmarks']
            
            if shoulder_idx not in landmarks or elbow_idx not in landmarks:
                continue
            
            shoulder = np.array([landmarks[shoulder_idx]['x'], 
                               landmarks[shoulder_idx]['y']])
            elbow = np.array([landmarks[elbow_idx]['x'], 
                            landmarks[elbow_idx]['y']])
            
            # Calculate angle from horizontal (0 degrees = horizontal)
            arm_vector = elbow - shoulder
            angle_from_horizontal = np.abs(np.arctan2(arm_vector[1], arm_vector[0]))
            
            # Score is how close to horizontal (0 radians)
            score = angle_from_horizontal
            
            if score < best_score:
                best_score = score
                best_frame = i
        
        # Only return if reasonably horizontal (within ~30 degrees)
        if best_score < np.radians(30):
            return best_frame
        
        return None
    
    @staticmethod
    def detect_ball_release(landmarks_list: List[Dict], bowling_arm: str,
                           horizontal_frame: int, search_window: int = 30) -> Optional[int]:
        """
        Detect ball release frame based on wrist deceleration.
        
        Args:
            landmarks_list: List of frame data with landmarks
            bowling_arm: 'left' or 'right'
            horizontal_frame: Frame where arm reached horizontal
            search_window: Number of frames to search after horizontal
            
        Returns:
            Frame index of estimated ball release, or None if not found
        """
        _, _, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        start_frame = horizontal_frame
        end_frame = min(horizontal_frame + search_window, len(landmarks_list))
        
        wrist_speeds = []
        valid_frames = []
        
        for i in range(start_frame + 1, end_frame):
            prev_frame = landmarks_list[i-1]
            curr_frame = landmarks_list[i]
            
            if not (prev_frame['landmarks'] and curr_frame['landmarks']):
                continue
            
            if wrist_idx not in prev_frame['landmarks'] or \
               wrist_idx not in curr_frame['landmarks']:
                continue
            
            prev_wrist = np.array([
                prev_frame['landmarks'][wrist_idx]['x'],
                prev_frame['landmarks'][wrist_idx]['y']
            ])
            curr_wrist = np.array([
                curr_frame['landmarks'][wrist_idx]['x'],
                curr_frame['landmarks'][wrist_idx]['y']
            ])
            
            speed = np.linalg.norm(curr_wrist - prev_wrist)
            wrist_speeds.append(speed)
            valid_frames.append(i)
        
        if not wrist_speeds:
            return None
        
        # Find peak speed (likely near release)
        peak_idx = np.argmax(wrist_speeds)
        
        # Look for significant deceleration after peak
        for i in range(peak_idx + 1, len(wrist_speeds)):
            if wrist_speeds[i] < 0.5 * wrist_speeds[peak_idx]:
                return valid_frames[i]
        
        # If no clear deceleration, return peak
        return valid_frames[peak_idx] if peak_idx < len(valid_frames) else None
