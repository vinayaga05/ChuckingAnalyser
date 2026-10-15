"""
MediaPipe Pose detection and landmark extraction.
"""

import cv2
import numpy as np
from typing import List, Optional, Dict, Tuple
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import Image, ImageFormat
import urllib.request
import os


class PoseDetector:
    """Detects and tracks pose landmarks in video frames."""
    
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
    MODEL_PATH = "pose_landmarker_heavy.task"
    
    def __init__(self, min_detection_confidence: float = 0.5, 
                 min_tracking_confidence: float = 0.5):
        """
        Initialize pose detector.
        
        Args:
            min_detection_confidence: Minimum confidence for pose detection
            min_tracking_confidence: Minimum confidence for landmark tracking
        """
        # Download model if not present
        if not os.path.exists(self.MODEL_PATH):
            print(f"Downloading pose landmarker model...")
            urllib.request.urlretrieve(self.MODEL_URL, self.MODEL_PATH)
            print(f"Model downloaded to {self.MODEL_PATH}")
        
        # Create pose landmarker
        base_options = python.BaseOptions(model_asset_path=self.MODEL_PATH)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.pose_landmarker = vision.PoseLandmarker.create_from_options(options)
        
    def process_video(self, video_path: str) -> Tuple[List[Dict], Dict]:
        """
        Process video and extract pose landmarks for all frames.
        
        Args:
            video_path: Path to input video file
            
        Returns:
            Tuple of (landmarks_list, video_metadata)
            landmarks_list: List of landmark dictionaries for each frame
            video_metadata: Dictionary with fps, frame_count, width, height
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        video_metadata = {
            'fps': fps,
            'frame_count': frame_count,
            'width': width,
            'height': height
        }
        
        landmarks_list = []
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to MediaPipe Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = Image(image_format=ImageFormat.SRGB, data=frame_rgb)
            
            # Calculate timestamp in milliseconds
            timestamp_ms = int((frame_idx / fps) * 1000) if fps > 0 else frame_idx * 33
            
            # Detect pose
            results = self.pose_landmarker.detect_for_video(mp_image, timestamp_ms)
            
            frame_data = {
                'frame_idx': frame_idx,
                'timestamp': frame_idx / fps if fps > 0 else 0,
                'landmarks': None,
                'confidence': 0.0
            }
            
            if results.pose_landmarks and len(results.pose_landmarks) > 0:
                # Use first detected person
                pose_landmarks = results.pose_landmarks[0]
                landmarks_dict = {}
                
                for idx, landmark in enumerate(pose_landmarks):
                    landmarks_dict[idx] = {
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z,
                        'visibility': landmark.visibility
                    }
                frame_data['landmarks'] = landmarks_dict
                
                # Average visibility as overall confidence
                visibilities = [lm.visibility for lm in pose_landmarks]
                frame_data['confidence'] = np.mean(visibilities)
            
            landmarks_list.append(frame_data)
            frame_idx += 1
        
        cap.release()
        
        return landmarks_list, video_metadata
    
    def get_joint_position(self, landmarks: Dict, joint_idx: int) -> Optional[np.ndarray]:
        """
        Extract 3D position of a specific joint.
        
        Args:
            landmarks: Landmarks dictionary for a frame
            joint_idx: MediaPipe pose landmark index
            
        Returns:
            3D position array [x, y, z] or None if not available
        """
        if landmarks is None or joint_idx not in landmarks:
            return None
        
        lm = landmarks[joint_idx]
        return np.array([lm['x'], lm['y'], lm['z']])
    
    def get_joint_visibility(self, landmarks: Dict, joint_idx: int) -> float:
        """
        Get visibility/confidence of a specific joint.
        
        Args:
            landmarks: Landmarks dictionary for a frame
            joint_idx: MediaPipe pose landmark index
            
        Returns:
            Visibility score (0-1) or 0 if not available
        """
        if landmarks is None or joint_idx not in landmarks:
            return 0.0
        
        return landmarks[joint_idx]['visibility']
    
    def close(self):
        """Release resources."""
        self.pose_landmarker.close()
