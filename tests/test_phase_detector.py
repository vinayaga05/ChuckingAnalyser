"""
Unit tests for phase detection.
"""

import unittest
import numpy as np
from chucking_analyser.phase_detector import PhaseDetector


class TestPhaseDetector(unittest.TestCase):
    """Test phase detection functions."""
    
    def create_landmark_frame(self, frame_idx, timestamp, landmarks_dict=None):
        """Helper to create a frame data dictionary."""
        return {
            'frame_idx': frame_idx,
            'timestamp': timestamp,
            'landmarks': landmarks_dict,
            'confidence': 0.9 if landmarks_dict else 0.0
        }
    
    def create_arm_landmarks(self, shoulder_pos, elbow_pos, wrist_pos, arm='right'):
        """Helper to create landmark dictionary for an arm."""
        if arm == 'right':
            shoulder_idx = PhaseDetector.RIGHT_SHOULDER
            elbow_idx = PhaseDetector.RIGHT_ELBOW
            wrist_idx = PhaseDetector.RIGHT_WRIST
        else:
            shoulder_idx = PhaseDetector.LEFT_SHOULDER
            elbow_idx = PhaseDetector.LEFT_ELBOW
            wrist_idx = PhaseDetector.LEFT_WRIST
        
        return {
            shoulder_idx: {
                'x': shoulder_pos[0], 'y': shoulder_pos[1], 
                'z': shoulder_pos[2], 'visibility': 0.9
            },
            elbow_idx: {
                'x': elbow_pos[0], 'y': elbow_pos[1], 
                'z': elbow_pos[2], 'visibility': 0.9
            },
            wrist_idx: {
                'x': wrist_pos[0], 'y': wrist_pos[1], 
                'z': wrist_pos[2], 'visibility': 0.9
            },
        }
    
    def test_get_arm_landmarks_right(self):
        """Test getting right arm landmark indices."""
        shoulder, elbow, wrist = PhaseDetector.get_arm_landmarks('right')
        
        self.assertEqual(shoulder, PhaseDetector.RIGHT_SHOULDER)
        self.assertEqual(elbow, PhaseDetector.RIGHT_ELBOW)
        self.assertEqual(wrist, PhaseDetector.RIGHT_WRIST)
    
    def test_get_arm_landmarks_left(self):
        """Test getting left arm landmark indices."""
        shoulder, elbow, wrist = PhaseDetector.get_arm_landmarks('left')
        
        self.assertEqual(shoulder, PhaseDetector.LEFT_SHOULDER)
        self.assertEqual(elbow, PhaseDetector.LEFT_ELBOW)
        self.assertEqual(wrist, PhaseDetector.LEFT_WRIST)
    
    def test_detect_bowling_arm_right(self):
        """Test detecting right arm as bowling arm."""
        # Create sequence with more right arm motion
        landmarks_list = []
        
        for i in range(10):
            # Right arm moves, left arm static
            landmarks = {}
            
            # Static left arm
            landmarks.update(self.create_arm_landmarks(
                [0.3, 0.5, 0.0],
                [0.25, 0.5, 0.0],
                [0.2, 0.5, 0.0],
                arm='left'
            ))
            
            # Moving right arm
            landmarks.update(self.create_arm_landmarks(
                [0.7, 0.5, 0.0],
                [0.75, 0.5 + i * 0.05, 0.0],
                [0.8, 0.5 + i * 0.1, 0.0],
                arm='right'
            ))
            
            frame = self.create_landmark_frame(i, i / 30.0, landmarks)
            landmarks_list.append(frame)
        
        bowling_arm = PhaseDetector.detect_bowling_arm(landmarks_list)
        self.assertEqual(bowling_arm, 'right')
    
    def test_detect_bowling_arm_left(self):
        """Test detecting left arm as bowling arm."""
        landmarks_list = []
        
        for i in range(10):
            landmarks = {}
            
            # Moving left arm
            landmarks.update(self.create_arm_landmarks(
                [0.3, 0.5, 0.0],
                [0.25, 0.5 + i * 0.05, 0.0],
                [0.2, 0.5 + i * 0.1, 0.0],
                arm='left'
            ))
            
            # Static right arm
            landmarks.update(self.create_arm_landmarks(
                [0.7, 0.5, 0.0],
                [0.75, 0.5, 0.0],
                [0.8, 0.5, 0.0],
                arm='right'
            ))
            
            frame = self.create_landmark_frame(i, i / 30.0, landmarks)
            landmarks_list.append(frame)
        
        bowling_arm = PhaseDetector.detect_bowling_arm(landmarks_list)
        self.assertEqual(bowling_arm, 'left')
    
    def test_detect_arm_horizontal(self):
        """Test detecting when arm reaches horizontal."""
        landmarks_list = []
        
        # Create sequence where arm moves from down to horizontal to up
        for i in range(15):
            # Arm gradually rises
            angle = -60 + i * 10  # -60° to +80°
            angle_rad = np.radians(angle)
            
            shoulder_pos = [0.5, 0.5, 0.0]
            # Elbow position traces an arc
            elbow_pos = [
                0.5 + 0.2 * np.cos(angle_rad),
                0.5 + 0.2 * np.sin(angle_rad),
                0.0
            ]
            wrist_pos = [
                0.5 + 0.4 * np.cos(angle_rad),
                0.5 + 0.4 * np.sin(angle_rad),
                0.0
            ]
            
            landmarks = self.create_arm_landmarks(
                shoulder_pos, elbow_pos, wrist_pos, arm='right'
            )
            
            frame = self.create_landmark_frame(i, i / 30.0, landmarks)
            landmarks_list.append(frame)
        
        horizontal_frame = PhaseDetector.detect_arm_horizontal(landmarks_list, 'right')
        
        self.assertIsNotNone(horizontal_frame)
        # Should be around frame 6 (when angle is near 0)
        self.assertGreater(horizontal_frame, 4)
        self.assertLess(horizontal_frame, 9)
    
    def test_detect_ball_release(self):
        """Test detecting ball release from wrist deceleration."""
        landmarks_list = []
        
        # Create sequence with wrist accelerating then decelerating
        for i in range(20):
            if i < 10:
                # Accelerating phase
                speed = i * 0.05
            else:
                # Decelerating phase
                speed = (20 - i) * 0.03
            
            wrist_x = 0.5 + sum(j * 0.05 if j < 10 else (20 - j) * 0.03 
                               for j in range(i + 1))
            
            shoulder_pos = [0.5, 0.5, 0.0]
            elbow_pos = [0.6, 0.5, 0.0]
            wrist_pos = [wrist_x, 0.6, 0.0]
            
            landmarks = self.create_arm_landmarks(
                shoulder_pos, elbow_pos, wrist_pos, arm='right'
            )
            
            frame = self.create_landmark_frame(i, i / 30.0, landmarks)
            landmarks_list.append(frame)
        
        # Horizontal at frame 5, look for release after
        release_frame = PhaseDetector.detect_ball_release(
            landmarks_list, 'right', horizontal_frame=5
        )
        
        self.assertIsNotNone(release_frame)
        # Release should be after horizontal
        self.assertGreater(release_frame, 5)
    
    def test_detect_arm_horizontal_not_found(self):
        """Test when arm never reaches horizontal."""
        landmarks_list = []
        
        # Create sequence where arm stays low
        for i in range(10):
            shoulder_pos = [0.5, 0.5, 0.0]
            elbow_pos = [0.5, 0.7, 0.0]  # Below shoulder
            wrist_pos = [0.5, 0.9, 0.0]
            
            landmarks = self.create_arm_landmarks(
                shoulder_pos, elbow_pos, wrist_pos, arm='right'
            )
            
            frame = self.create_landmark_frame(i, i / 30.0, landmarks)
            landmarks_list.append(frame)
        
        horizontal_frame = PhaseDetector.detect_arm_horizontal(landmarks_list, 'right')
        
        # Should not find horizontal position
        self.assertIsNone(horizontal_frame)


if __name__ == '__main__':
    unittest.main()
