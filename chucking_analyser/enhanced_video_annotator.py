"""
Enhanced video annotation with slow-motion, alerts, and phase markers.
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple


class EnhancedVideoAnnotator:
    """Creates enhanced annotated videos with alerts and slow-motion."""
    
    def __init__(self):
        """Initialize enhanced video annotator."""
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.7
        self.font_thickness = 2
        
    def create_enhanced_video(self, input_video: str, output_video: str,
                             landmarks_list: List[Dict],
                             delivery_result: Dict,
                             bowling_arm: str,
                             fps: float):
        """
        Create enhanced annotated video with slow-motion and alerts.
        
        Args:
            input_video: Path to input video
            output_video: Path to output video
            landmarks_list: List of frame data with landmarks
            delivery_result: Delivery analysis result
            bowling_arm: 'left' or 'right'
            fps: Original video FPS
        """
        from .phase_detector import PhaseDetector
        from .angle_calculator import calculate_angle_3d
        
        cap = cv2.VideoCapture(input_video)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {input_video}")
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Output at same FPS as input
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
        
        shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        h_frame = delivery_result.get('horizontal_frame')
        r_frame = delivery_result.get('release_frame')
        
        # Pre-calculate all angles for alert detection
        all_angles = self._calculate_all_angles(landmarks_list, shoulder_idx, elbow_idx, wrist_idx)
        bend_events = self._detect_bend_events(all_angles, h_frame, r_frame)
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Draw base annotation
            frame = self._draw_base_annotation(
                frame, landmarks_list, frame_idx, bowling_arm,
                shoulder_idx, elbow_idx, wrist_idx, all_angles
            )
            
            # Draw phase markers
            frame = self._draw_phase_markers(
                frame, frame_idx, h_frame, r_frame, width, height
            )
            
            # Draw delivery info
            frame = self._draw_delivery_info(
                frame, delivery_result, frame_idx, h_frame, r_frame, width, height
            )
            
            # Draw bend alerts
            frame = self._draw_bend_alerts(
                frame, frame_idx, bend_events, width, height
            )
            
            # Write frame (with slow-motion handled by repetition)
            repeat_count = self._get_frame_repeat_count(frame_idx, h_frame, r_frame)
            for _ in range(repeat_count):
                out.write(frame)
            
            frame_idx += 1
        
        cap.release()
        out.release()
    
    def _calculate_all_angles(self, landmarks_list, shoulder_idx, elbow_idx, wrist_idx):
        """Pre-calculate all elbow angles."""
        from .angle_calculator import calculate_angle_3d
        
        angles = []
        for frame_data in landmarks_list:
            if not frame_data['landmarks']:
                angles.append(None)
                continue
            
            lm = frame_data['landmarks']
            if all(idx in lm for idx in [shoulder_idx, elbow_idx, wrist_idx]):
                s = np.array([lm[shoulder_idx]['x'], lm[shoulder_idx]['y'], lm[shoulder_idx]['z']])
                e = np.array([lm[elbow_idx]['x'], lm[elbow_idx]['y'], lm[elbow_idx]['z']])
                w = np.array([lm[wrist_idx]['x'], lm[wrist_idx]['y'], lm[wrist_idx]['z']])
                angles.append(calculate_angle_3d(s, e, w))
            else:
                angles.append(None)
        
        return angles
    
    def _detect_bend_events(self, angles, h_frame, r_frame):
        """Detect significant bend/extension events."""
        if h_frame is None or r_frame is None:
            return []
        
        events = []
        for i in range(max(0, h_frame), min(r_frame + 1, len(angles) - 1)):
            if angles[i] is not None and angles[i+1] is not None:
                change = angles[i+1] - angles[i]
                if abs(change) > 5.0:  # Significant change
                    events.append({
                        'frame': i+1,
                        'change': change,
                        'angle_before': angles[i],
                        'angle_after': angles[i+1],
                        'type': 'extension' if change > 0 else 'flexion'
                    })
        
        return events
    
    def _draw_base_annotation(self, frame, landmarks_list, frame_idx,
                             bowling_arm, shoulder_idx, elbow_idx, wrist_idx, all_angles):
        """Draw skeleton and bowling arm highlight."""
        if frame_idx >= len(landmarks_list):
            return frame
        
        frame_data = landmarks_list[frame_idx]
        if not frame_data['landmarks']:
            return frame
        
        h, w = frame.shape[:2]
        lm = frame_data['landmarks']
        
        # Draw bowling arm (highlighted)
        if all(idx in lm for idx in [shoulder_idx, elbow_idx, wrist_idx]):
            shoulder = lm[shoulder_idx]
            elbow = lm[elbow_idx]
            wrist = lm[wrist_idx]
            
            s_pos = (int(shoulder['x'] * w), int(shoulder['y'] * h))
            e_pos = (int(elbow['x'] * w), int(elbow['y'] * h))
            w_pos = (int(wrist['x'] * w), int(wrist['y'] * h))
            
            # Draw arm segments
            cv2.line(frame, s_pos, e_pos, (0, 255, 0), 5)
            cv2.line(frame, e_pos, w_pos, (0, 255, 0), 5)
            
            # Draw joints
            cv2.circle(frame, s_pos, 8, (255, 255, 0), -1)
            cv2.circle(frame, e_pos, 8, (255, 0, 0), -1)  # Elbow in red
            cv2.circle(frame, w_pos, 8, (255, 255, 0), -1)
            
            # Label elbow
            cv2.putText(frame, "ELBOW", (e_pos[0] + 15, e_pos[1] - 15),
                       self.font, 0.6, (255, 0, 0), 2)
        
        # Show current angle
        if frame_idx < len(all_angles) and all_angles[frame_idx] is not None:
            angle = all_angles[frame_idx]
            cv2.putText(frame, f"Angle: {angle:.1f}", (20, h - 20),
                       self.font, self.font_scale, (255, 255, 255), self.font_thickness)
        
        return frame
    
    def _draw_phase_markers(self, frame, frame_idx, h_frame, r_frame, width, height):
        """Draw phase markers at top."""
        marker_y = 40
        
        if h_frame is not None and frame_idx == h_frame:
            cv2.rectangle(frame, (0, 0), (width, 80), (0, 255, 255), -1)
            cv2.putText(frame, "HORIZONTAL - Measurement Starts", (20, marker_y),
                       self.font, 1.0, (0, 0, 0), 3)
        
        if r_frame is not None and frame_idx == r_frame:
            cv2.rectangle(frame, (0, 0), (width, 80), (0, 0, 255), -1)
            cv2.putText(frame, "RELEASE - Measurement Ends", (20, marker_y),
                       self.font, 1.0, (255, 255, 255), 3)
        
        return frame
    
    def _draw_delivery_info(self, frame, delivery_result, frame_idx, h_frame, r_frame, width, height):
        """Draw delivery information overlay."""
        info_x = 20
        info_y_start = 100
        
        # Show measurement window
        if h_frame is not None and r_frame is not None:
            if h_frame <= frame_idx <= r_frame:
                # Inside measurement window
                extension = delivery_result.get('elbow_extension', 0)
                max_change = delivery_result.get('max_frame_change', 0)
                
                cv2.putText(frame, f"Extension: {extension:.1f}", (info_x, info_y_start),
                           self.font, 0.8, (0, 255, 255), 2)
                cv2.putText(frame, f"Max Change: {max_change:.1f}/frame", (info_x, info_y_start + 30),
                           self.font, 0.7, (255, 255, 255), 2)
                
                # Progress bar
                progress = (frame_idx - h_frame) / (r_frame - h_frame) if r_frame > h_frame else 0
                bar_width = 200
                bar_x = width - bar_width - 20
                bar_y = 100
                
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + 20), (100, 100, 100), -1)
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_width * progress), bar_y + 20), (0, 255, 0), -1)
                cv2.putText(frame, "Measurement", (bar_x, bar_y - 5), self.font, 0.5, (255, 255, 255), 1)
        
        # Show verdict at bottom
        result = delivery_result.get('result', 'unknown')
        color = (0, 255, 0) if result == 'likely within threshold' else (0, 165, 255)
        if result == 'unable to assess':
            color = (128, 128, 128)
        
        cv2.putText(frame, f"Verdict: {result.upper()}", (20, height - 60),
                   self.font, 0.7, color, 2)
        
        reason = delivery_result.get('reason', '')
        if len(reason) > 60:
            reason = reason[:57] + "..."
        cv2.putText(frame, reason, (20, height - 30),
                   self.font, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def _draw_bend_alerts(self, frame, frame_idx, bend_events, width, height):
        """Draw alerts for significant bend/extension events."""
        for event in bend_events:
            if event['frame'] == frame_idx:
                # Show alert
                alert_height = 100
                cv2.rectangle(frame, (0, height//2 - alert_height//2),
                            (width, height//2 + alert_height//2), (0, 0, 0), -1)
                
                alert_text = f"{'EXTENSION' if event['type'] == 'extension' else 'FLEXION'}: {abs(event['change']):.1f}"
                cv2.putText(frame, "ALERT!", (width//2 - 100, height//2 - 20),
                           self.font, 1.2, (0, 0, 255) if event['type'] == 'extension' else (255, 0, 0), 3)
                cv2.putText(frame, alert_text, (width//2 - 150, height//2 + 20),
                           self.font, 1.0, (255, 255, 255), 2)
                cv2.putText(frame, f"{event['angle_before']:.1f} -> {event['angle_after']:.1f}",
                           (width//2 - 100, height//2 + 50),
                           self.font, 0.8, (255, 255, 0), 2)
        
        return frame
    
    def _get_frame_repeat_count(self, frame_idx, h_frame, r_frame):
        """Get frame repeat count for slow-motion effect."""
        # Slow down at key moments
        if h_frame is not None and abs(frame_idx - h_frame) <= 2:
            return 3  # 3x slow-motion at horizontal
        if r_frame is not None and abs(frame_idx - r_frame) <= 2:
            return 3  # 3x slow-motion at release
        return 1  # Normal speed
