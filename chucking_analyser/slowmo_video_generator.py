"""
Slow-motion video generator with arm trajectory visualization.

Renders at 30 FPS output where each source frame becomes one output frame,
creating slow-motion playback (e.g., 240 FPS source = 8x slow-mo).
"""

import cv2
import numpy as np
from typing import List, Dict
from collections import deque


class SlowMotionVideoGenerator:
    """Generate slow-motion preview video with trajectory trails and annotations."""
    
    OUTPUT_FPS = 30.0  # Always render at 30 FPS
    
    def __init__(self):
        self.trail_length = 30  # Number of frames for trajectory trail
    
    def create_slowmo_video(self, video_path: str, output_path: str,
                           landmarks_list: List[Dict], result: Dict,
                           bowling_arm: str):
        """
        Create slow-motion preview video with trajectory visualization.
        
        Args:
            video_path: Input video path
            output_path: Output video path
            landmarks_list: Frame-by-frame landmarks
            result: Analysis result with full rotation data
            bowling_arm: 'left' or 'right'
        """
        from .phase_detector import PhaseDetector
        
        cap = cv2.VideoCapture(video_path)
        source_fps = result['native_fps']
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Calculate slow-down factor
        slowdown_factor = source_fps / self.OUTPUT_FPS
        
        # Output video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.OUTPUT_FPS, (width, height))
        
        # Get arm landmark indices
        shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        # Get analysis data
        analysis = result['full_rotation_analysis']
        samples = analysis['native_samples']
        bend_events = analysis['strict_analysis']['bend_events']
        
        # Create frame-to-angle lookup
        frame_angles = {s['frame']: s['angle'] for s in samples}
        frame_changes = {s['frame']: s['change'] for s in samples}
        
        # Trajectory trails
        wrist_trail = deque(maxlen=self.trail_length)
        elbow_trail = deque(maxlen=self.trail_length)
        
        # Delivery window
        delivery_start = analysis['delivery_start']
        delivery_end = analysis['delivery_end']
        
        frame_idx = 0
        
        print(f"  Generating slow-motion video ({slowdown_factor:.1f}x slow-down)...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Only process delivery frames
            if delivery_start <= frame_idx <= delivery_end:
                # Get landmarks
                landmarks = landmarks_list[frame_idx]['landmarks']
                
                if landmarks and all(idx in landmarks for idx in [shoulder_idx, elbow_idx, wrist_idx]):
                    # Get positions
                    shoulder = landmarks[shoulder_idx]
                    elbow = landmarks[elbow_idx]
                    wrist = landmarks[wrist_idx]
                    
                    # Convert to pixel coordinates
                    sh_pt = (int(shoulder['x'] * width), int(shoulder['y'] * height))
                    el_pt = (int(elbow['x'] * width), int(elbow['y'] * height))
                    wr_pt = (int(wrist['x'] * width), int(wrist['y'] * height))
                    
                    # Add to trails
                    elbow_trail.append(el_pt)
                    wrist_trail.append(wr_pt)
                    
                    # Draw trails (color-coded by elbow angle if available)
                    current_angle = frame_angles.get(frame_idx, 0)
                    self._draw_trail(frame, elbow_trail, current_angle, is_wrist=False)
                    self._draw_trail(frame, wrist_trail, current_angle, is_wrist=True)
                    
                    # Draw arm skeleton
                    cv2.line(frame, sh_pt, el_pt, (0, 255, 0), 3)
                    cv2.line(frame, el_pt, wr_pt, (0, 255, 0), 3)
                    cv2.circle(frame, sh_pt, 8, (255, 255, 255), -1)
                    cv2.circle(frame, el_pt, 10, (0, 255, 255), -1)
                    cv2.circle(frame, wr_pt, 8, (255, 255, 255), -1)
                    
                    # Draw elbow angle
                    if frame_idx in frame_angles:
                        angle = frame_angles[frame_idx]
                        change = frame_changes.get(frame_idx, 0)
                        
                        # Angle display
                        angle_text = f"Elbow: {angle:.1f}deg"
                        cv2.putText(frame, angle_text, (20, 50),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                        
                        # Change indicator
                        if abs(change) > result['strict_tolerance']:
                            change_text = f"BEND: {change:+.1f}deg"
                            color = (0, 0, 255) if change > 0 else (0, 165, 255)
                            cv2.putText(frame, change_text, (20, 100),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)
                    
                    # Check if this frame has a bend event
                    frame_events = [e for e in bend_events if e['frame'] == frame_idx]
                    if frame_events:
                        event = frame_events[0]
                        alert_text = f"! {event['type'].upper()}: {event['magnitude']:.1f}deg"
                        cv2.putText(frame, alert_text, (20, 150),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
            
            # Draw info overlay
            info_y = height - 120
            cv2.rectangle(frame, (10, info_y - 10), (400, height - 10),
                         (0, 0, 0), -1)
            cv2.rectangle(frame, (10, info_y - 10), (400, height - 10),
                         (255, 255, 255), 2)
            
            cv2.putText(frame, f"Frame: {frame_idx}", (20, info_y + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Source FPS: {source_fps:.1f}", (20, info_y + 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Slow-mo: {slowdown_factor:.1f}x", (20, info_y + 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            out.write(frame)
            frame_idx += 1
        
        cap.release()
        out.release()
        print(f"  Slow-motion video saved: {output_path}")
    
    def _draw_trail(self, frame, trail, current_angle, is_wrist=False):
        """Draw trajectory trail with color gradient based on angle."""
        if len(trail) < 2:
            return
        
        # Color based on angle (blue=extended, green=normal, red=flexed)
        if current_angle > 150:
            base_color = (255, 100, 0)  # Extended (cyan-ish)
        elif current_angle > 120:
            base_color = (100, 255, 100)  # Normal (green)
        else:
            base_color = (0, 100, 255)  # Flexed (orange-ish)
        
        # Draw trail with fading alpha
        points = list(trail)
        for i in range(len(points) - 1):
            alpha = i / len(points)  # Fade from 0 to 1
            thickness = int(2 + alpha * 2) if is_wrist else int(3 + alpha * 2)
            
            # Interpolate color with white for fading effect
            color = tuple(int(base_color[j] * alpha + 255 * (1 - alpha)) for j in range(3))
            
            cv2.line(frame, points[i], points[i + 1], color, thickness)
