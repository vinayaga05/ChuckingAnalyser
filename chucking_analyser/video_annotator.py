"""
Video annotation for visualizing analysis results.
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple


# MediaPipe Pose connections for drawing skeleton
POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),  # Arms
    (11, 23), (12, 24), (23, 24),  # Torso
    (23, 25), (24, 26), (25, 27), (26, 28),  # Legs
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),  # Face
    (9, 10),  # Mouth
    (15, 17), (15, 19), (15, 21), (17, 19),  # Left hand
    (16, 18), (16, 20), (16, 22), (18, 20),  # Right hand
    (25, 27), (27, 29), (29, 31), (27, 31),  # Left foot
    (26, 28), (28, 30), (30, 32), (28, 32),  # Right foot
]


class VideoAnnotator:
    """Creates annotated videos showing analysis results."""
    
    def __init__(self):
        """Initialize video annotator."""
        pass
    
    def create_annotated_video(self, input_video: str, output_video: str,
                               landmarks_list: List[Dict], 
                               delivery_results: List[Dict],
                               bowling_arm: str):
        """
        Create annotated output video with analysis overlay.
        
        Args:
            input_video: Path to input video
            output_video: Path to output video
            landmarks_list: List of frame data with landmarks
            delivery_results: List of delivery analysis results
            bowling_arm: 'left' or 'right'
        """
        cap = cv2.VideoCapture(input_video)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open input video: {input_video}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
        
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Draw pose landmarks
            if frame_idx < len(landmarks_list):
                frame = self._draw_pose_landmarks(
                    frame, landmarks_list[frame_idx], bowling_arm
                )
            
            # Draw delivery annotations
            frame = self._draw_delivery_annotations(
                frame, frame_idx, delivery_results, landmarks_list, bowling_arm
            )
            
            out.write(frame)
            frame_idx += 1
        
        cap.release()
        out.release()
    
    def _draw_pose_landmarks(self, frame: np.ndarray, frame_data: Dict, 
                            bowling_arm: str) -> np.ndarray:
        """Draw pose landmarks on frame."""
        if not frame_data['landmarks']:
            return frame
        
        h, w = frame.shape[:2]
        landmarks = frame_data['landmarks']
        
        # Draw connections (skeleton)
        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx in landmarks and end_idx in landmarks:
                start = landmarks[start_idx]
                end = landmarks[end_idx]
                
                if start['visibility'] > 0.5 and end['visibility'] > 0.5:
                    start_pos = (int(start['x'] * w), int(start['y'] * h))
                    end_pos = (int(end['x'] * w), int(end['y'] * h))
                    cv2.line(frame, start_pos, end_pos, (200, 200, 200), 2)
        
        # Draw landmarks
        for idx, lm in landmarks.items():
            if lm['visibility'] > 0.5:
                pos = (int(lm['x'] * w), int(lm['y'] * h))
                cv2.circle(frame, pos, 4, (0, 100, 255), -1)
                cv2.circle(frame, pos, 5, (255, 255, 255), 1)
        
        # Highlight bowling arm
        from .phase_detector import PhaseDetector
        shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        if all(idx in landmarks for idx in [shoulder_idx, elbow_idx, wrist_idx]):
            shoulder = landmarks[shoulder_idx]
            elbow = landmarks[elbow_idx]
            wrist = landmarks[wrist_idx]
            
            # Draw highlighted bowling arm
            cv2.line(
                frame,
                (int(shoulder['x'] * w), int(shoulder['y'] * h)),
                (int(elbow['x'] * w), int(elbow['y'] * h)),
                (0, 255, 0), 4
            )
            cv2.line(
                frame,
                (int(elbow['x'] * w), int(elbow['y'] * h)),
                (int(wrist['x'] * w), int(wrist['y'] * h)),
                (0, 255, 0), 4
            )
            
            # Draw joint circles
            for idx in [shoulder_idx, elbow_idx, wrist_idx]:
                lm = landmarks[idx]
                pos = (int(lm['x'] * w), int(lm['y'] * h))
                cv2.circle(frame, pos, 6, (0, 255, 0), -1)
                cv2.circle(frame, pos, 7, (255, 255, 255), 1)
        
        return frame
    
    def _draw_delivery_annotations(self, frame: np.ndarray, frame_idx: int,
                                   delivery_results: List[Dict],
                                   landmarks_list: List[Dict],
                                   bowling_arm: str) -> np.ndarray:
        """Draw delivery-specific annotations."""
        from .phase_detector import PhaseDetector
        from .angle_calculator import calculate_angle_3d
        
        # Find which delivery (if any) this frame belongs to
        current_delivery = None
        for delivery in delivery_results:
            if delivery['start_frame'] <= frame_idx <= delivery['end_frame']:
                current_delivery = delivery
                break
        
        if not current_delivery:
            return frame
        
        h, w = frame.shape[:2]
        
        # Draw delivery status
        status_text = f"Delivery {delivery_results.index(current_delivery) + 1}"
        cv2.putText(frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Mark key frames
        if frame_idx == current_delivery['horizontal_frame']:
            cv2.putText(frame, "ARM HORIZONTAL", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        if frame_idx == current_delivery['release_frame']:
            cv2.putText(frame, "BALL RELEASE", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Show current elbow angle
        if frame_idx < len(landmarks_list) and landmarks_list[frame_idx]['landmarks']:
            shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
            landmarks = landmarks_list[frame_idx]['landmarks']
            
            if all(idx in landmarks for idx in [shoulder_idx, elbow_idx, wrist_idx]):
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
                angle_text = f"Elbow: {angle:.1f}°"
                cv2.putText(frame, angle_text, (10, h - 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # Show extension result if in measurement window
        if (current_delivery['horizontal_frame'] is not None and 
            current_delivery['release_frame'] is not None and
            current_delivery['horizontal_frame'] <= frame_idx <= current_delivery['release_frame']):
            ext_text = f"Extension: {current_delivery['elbow_extension']:.1f}°"
            cv2.putText(frame, ext_text, (10, h - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            result_text = f"Result: {current_delivery['result']}"
            color = (0, 255, 0) if current_delivery['result'] == 'likely within threshold' else (0, 165, 255)
            cv2.putText(frame, result_text, (10, h - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        return frame
