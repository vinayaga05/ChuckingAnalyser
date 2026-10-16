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
        Detect the start of the critical delivery phase for extension measurement.
        
        ICC rules measure extension during the final delivery action. This identifies
        a frame approximately 15-20 frames before peak extension, which captures the
        critical phase where illegal elbow straightening would occur.
        
        Args:
            landmarks_list: List of frame data with landmarks
            bowling_arm: 'left' or 'right'
            start_frame: Start searching from this frame
            end_frame: Stop searching at this frame (None = end of video)
            
        Returns:
            Frame index for measurement start (critical phase begins), or None if not found
        """
        from .angle_calculator import calculate_angle_3d
        
        shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        if end_frame is None:
            end_frame = len(landmarks_list)
        
        # Find the frame with maximum elbow angle (peak extension)
        max_angle = 0
        max_angle_frame = None
        
        for i in range(start_frame, min(end_frame, len(landmarks_list))):
            frame_data = landmarks_list[i]
            
            if not frame_data['landmarks']:
                continue
            
            landmarks = frame_data['landmarks']
            
            if not all(idx in landmarks for idx in [shoulder_idx, elbow_idx, wrist_idx]):
                continue
            
            shoulder_3d = np.array([landmarks[shoulder_idx]['x'],
                                   landmarks[shoulder_idx]['y'],
                                   landmarks[shoulder_idx]['z']])
            elbow_3d = np.array([landmarks[elbow_idx]['x'],
                                landmarks[elbow_idx]['y'],
                                landmarks[elbow_idx]['z']])
            wrist_3d = np.array([landmarks[wrist_idx]['x'],
                                landmarks[wrist_idx]['y'],
                                landmarks[wrist_idx]['z']])
            
            angle = calculate_angle_3d(shoulder_3d, elbow_3d, wrist_3d)
            
            if angle > max_angle:
                max_angle = angle
                max_angle_frame = i
        
        if max_angle_frame is None:
            return None
        
        # The critical delivery phase for detecting chucking is the final 8-10 frames
        # (~0.13-0.17 sec at 60fps) before peak extension, where sudden elbow 
        # straightening (as opposed to whole-arm rotation) would occur.
        CRITICAL_PHASE_FRAMES = 10
        horizontal_frame = max(start_frame, max_angle_frame - CRITICAL_PHASE_FRAMES)
        
        return horizontal_frame
    
    @staticmethod
    def detect_ball_release(landmarks_list: List[Dict], bowling_arm: str,
                           horizontal_frame: int, search_window: int = 30) -> Optional[int]:
        """
        Detect ball release frame at or near peak extension.
        
        Ball release typically occurs at or just before the point of maximum
        elbow extension during the delivery action.
        
        Args:
            landmarks_list: List of frame data with landmarks
            bowling_arm: 'left' or 'right'
            horizontal_frame: Frame where critical phase began
            search_window: Number of frames to search after horizontal
            
        Returns:
            Frame index of estimated ball release (at peak extension)
        """
        from .angle_calculator import calculate_angle_3d
        
        shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        start_frame = horizontal_frame
        end_frame = min(horizontal_frame + search_window, len(landmarks_list))
        
        # Find maximum extension (largest elbow angle) in window
        max_angle = 0
        max_angle_frame = None
        
        for i in range(start_frame, end_frame):
            frame_data = landmarks_list[i]
            
            if not frame_data['landmarks']:
                continue
            
            landmarks = frame_data['landmarks']
            
            if not all(idx in landmarks for idx in [shoulder_idx, elbow_idx, wrist_idx]):
                continue
            
            shoulder = np.array([landmarks[shoulder_idx]['x'],
                               landmarks[shoulder_idx]['y'],
                               landmarks[shoulder_idx]['z']])
            elbow = np.array([landmarks[elbow_idx]['x'],
                            landmarks[elbow_idx]['y'],
                            landmarks[elbow_idx]['z']])
            wrist = np.array([landmarks[wrist_idx]['x'],
                            landmarks[wrist_idx]['y'],
                            landmarks[wrist_idx]['z']])
            
            angle = calculate_angle_3d(shoulder, elbow, wrist)
            
            if angle > max_angle:
                max_angle = angle
                max_angle_frame = i
        
        return max_angle_frame
