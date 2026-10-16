"""
Main analysis orchestration.
"""

import json
import os
from typing import List, Dict, Optional, Tuple
import numpy as np

from .pose_detector import PoseDetector
from .delivery_detector import DeliveryDetector
from .phase_detector import PhaseDetector
from .angle_calculator import calculate_angle_3d, calculate_elbow_extension, smooth_positions
from .video_annotator import VideoAnnotator
from .enhanced_video_annotator import EnhancedVideoAnnotator
from .html_report_generator import HTMLReportGenerator
from .extension_analyzer import analyze_extension_pattern, classify_action


class BowlingAnalyser:
    """Main analyser for cricket bowling actions."""
    
    ICC_THRESHOLD = 15.0  # degrees
    
    def __init__(self):
        """Initialize analyser components."""
        self.pose_detector = PoseDetector()
        self.delivery_detector = DeliveryDetector()
        self.video_annotator = VideoAnnotator()
        self.enhanced_video_annotator = EnhancedVideoAnnotator()
        self.html_report_generator = HTMLReportGenerator()
    
    def analyse_video(self, video_path: str, output_dir: str,
                     manual_overrides: Optional[Dict] = None,
                     enhanced_report: bool = False) -> List[Dict]:
        """
        Analyse bowling video for illegal actions.
        
        Args:
            video_path: Path to input video
            output_dir: Directory for output files
            manual_overrides: Optional dict with manual frame overrides
                             Format: {delivery_idx: {'horizontal_frame': int, 'release_frame': int}}
            enhanced_report: Generate enhanced video and HTML report
        
        Returns:
            List of delivery analysis results
        """
        os.makedirs(output_dir, exist_ok=True)
        
        print("Processing video with MediaPipe Pose...")
        landmarks_list, video_metadata = self.pose_detector.process_video(video_path)
        
        print("Detecting bowling arm...")
        bowling_arm = PhaseDetector.detect_bowling_arm(landmarks_list)
        print(f"  Detected: {bowling_arm} arm")
        
        print("Detecting deliveries...")
        deliveries = self.delivery_detector.detect_deliveries(landmarks_list, bowling_arm)
        print(f"  Found {len(deliveries)} delivery sequences")
        
        if not deliveries:
            print("WARNING: No deliveries detected. Video may need manual review.")
            # Treat entire video as one delivery for manual override
            deliveries = [(0, len(landmarks_list) - 1)]
        
        delivery_results = []
        
        for idx, (start_frame, end_frame) in enumerate(deliveries):
            print(f"\nAnalysing delivery {idx + 1}...")
            
            result = self._analyse_delivery(
                landmarks_list, bowling_arm, start_frame, end_frame,
                idx, manual_overrides, video_metadata['fps']
            )
            
            delivery_results.append(result)
            
            print(f"  Extension: {result['elbow_extension']:.1f}°")
            print(f"  Result: {result['result']}")
            print(f"  Reason: {result['reason']}")
        
        # Save JSON results
        json_path = os.path.join(output_dir, 'analysis_results.json')
        with open(json_path, 'w') as f:
            json.dump({
                'video_path': video_path,
                'bowling_arm': bowling_arm,
                'video_metadata': video_metadata,
                'deliveries': delivery_results,
                'disclaimer': 'This is a 2D camera estimate only and not an official ruling.'
            }, f, indent=2)
        
        print(f"\nResults saved to: {json_path}")
        
        # Create annotated video
        if enhanced_report and len(delivery_results) > 0:
            # Enhanced video with slow-motion and alerts
            output_video = os.path.join(output_dir, 'enhanced_annotated_video.mp4')
            print(f"\nCreating enhanced annotated video: {output_video}")
            self.enhanced_video_annotator.create_enhanced_video(
                video_path, output_video, landmarks_list,
                delivery_results[0], bowling_arm, video_metadata['fps']
            )
            
            # HTML report
            html_report_path = os.path.join(output_dir, 'analysis_report.html')
            print(f"Generating HTML report: {html_report_path}")
            
            # Calculate all angles for report
            shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
            all_angles = []
            for frame_data in landmarks_list:
                if not frame_data['landmarks']:
                    all_angles.append(None)
                    continue
                lm = frame_data['landmarks']
                if all(idx in lm for idx in [shoulder_idx, elbow_idx, wrist_idx]):
                    s = np.array([lm[shoulder_idx]['x'], lm[shoulder_idx]['y'], lm[shoulder_idx]['z']])
                    e = np.array([lm[elbow_idx]['x'], lm[elbow_idx]['y'], lm[elbow_idx]['z']])
                    w = np.array([lm[wrist_idx]['x'], lm[wrist_idx]['y'], lm[wrist_idx]['z']])
                    all_angles.append(calculate_angle_3d(s, e, w))
                else:
                    all_angles.append(None)
            
            self.html_report_generator.generate_report(
                video_path, delivery_results[0], landmarks_list,
                all_angles, bowling_arm, html_report_path
            )
            print(f"HTML report saved: {html_report_path}")
        else:
            # Standard annotated video
            output_video = os.path.join(output_dir, 'annotated_video.mp4')
            print(f"\nCreating annotated video: {output_video}")
            self.video_annotator.create_annotated_video(
                video_path, output_video, landmarks_list, delivery_results, bowling_arm
            )
        
        return delivery_results
    
    def _analyse_delivery(self, landmarks_list: List[Dict], bowling_arm: str,
                         start_frame: int, end_frame: int, delivery_idx: int,
                         manual_overrides: Optional[Dict], fps: float) -> Dict:
        """Analyse a single delivery."""
        
        shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        # Detect key phases (or use manual overrides)
        if manual_overrides and delivery_idx in manual_overrides:
            overrides = manual_overrides[delivery_idx]
            horizontal_frame = overrides.get('horizontal_frame')
            release_frame = overrides.get('release_frame')
        else:
            horizontal_frame = PhaseDetector.detect_arm_horizontal(
                landmarks_list, bowling_arm, start_frame, end_frame
            )
            release_frame = None
            if horizontal_frame is not None:
                release_frame = PhaseDetector.detect_ball_release(
                    landmarks_list, bowling_arm, horizontal_frame
                )
        
        result = {
            'delivery_number': delivery_idx + 1,
            'start_frame': start_frame,
            'end_frame': end_frame,
            'start_timestamp': start_frame / fps,
            'end_timestamp': end_frame / fps,
            'bowling_arm': bowling_arm,
            'horizontal_frame': horizontal_frame,
            'horizontal_timestamp': horizontal_frame / fps if horizontal_frame else None,
            'release_frame': release_frame,
            'release_timestamp': release_frame / fps if release_frame else None,
            'elbow_extension': 0.0,
            'pose_confidence': 0.0,
            'quality_notes': [],
            'result': 'unable to assess',
            'reason': 'unknown'
        }
        
        # Check if we can measure
        if horizontal_frame is None:
            result['reason'] = 'arm horizontal frame not detected'
            result['quality_notes'].append('Could not detect arm reaching horizontal position')
            return result
        
        if release_frame is None:
            result['reason'] = 'ball release frame not detected'
            result['quality_notes'].append('Could not detect ball release')
            return result
        
        # Extract and smooth positions
        positions = self._extract_arm_positions(
            landmarks_list, horizontal_frame, release_frame,
            shoulder_idx, elbow_idx, wrist_idx
        )
        
        if not positions['valid']:
            result['reason'] = 'insufficient landmark data'
            result['quality_notes'].append('Missing or low-confidence landmarks')
            return result
        
        # Calculate RAW angles first (for pattern detection)
        raw_angles = []
        for i in range(len(positions['shoulder'])):
            if (positions['shoulder'][i] is not None and 
                positions['elbow'][i] is not None and 
                positions['wrist'][i] is not None):
                angle = calculate_angle_3d(
                    positions['shoulder'][i], 
                    positions['elbow'][i], 
                    positions['wrist'][i]
                )
                raw_angles.append(angle)
            else:
                raw_angles.append(None)
        
        # Analyze extension pattern using RAW angles to detect chucking
        # (smoothing would hide the sudden spike that indicates illegal action)
        extension_analysis = analyze_extension_pattern(
            raw_angles, 0, len(raw_angles) - 1
        )
        
        # Now smooth positions for extension measurement
        shoulder_pos = smooth_positions(positions['shoulder'], sigma=1.5)
        elbow_pos = smooth_positions(positions['elbow'], sigma=1.5)
        wrist_pos = smooth_positions(positions['wrist'], sigma=1.5)
        
        # Calculate smoothed angles for final extension measurement
        smoothed_angles = []
        for i in range(len(shoulder_pos)):
            if shoulder_pos[i] is not None and elbow_pos[i] is not None and wrist_pos[i] is not None:
                angle = calculate_angle_3d(shoulder_pos[i], elbow_pos[i], wrist_pos[i])
                smoothed_angles.append(angle)
            else:
                smoothed_angles.append(None)
        
        initial_angle = smoothed_angles[0] if smoothed_angles[0] is not None else 0
        final_angle = smoothed_angles[-1] if smoothed_angles[-1] is not None else 0
        
        extension = calculate_elbow_extension(initial_angle, final_angle)
        
        result['elbow_extension'] = extension
        result['pose_confidence'] = positions['avg_confidence']
        
        result['extension_pattern'] = extension_analysis['pattern']
        result['max_frame_change'] = extension_analysis['max_frame_change']
        
        # Assess quality
        if positions['avg_confidence'] < 0.5:
            result['quality_notes'].append('Low pose detection confidence')
        
        measurement_window = release_frame - horizontal_frame
        if measurement_window < 5:
            result['quality_notes'].append('Very short measurement window')
        
        # Check for negative extension (arm bending instead of straightening)
        if extension < 0:
            result['quality_notes'].append(f'Negative extension detected (arm bending, not straightening)')
            result['result'] = 'unable to assess'
            result['reason'] = 'negative extension suggests incorrect phase detection'
            return result
        
        # Classify result using pattern analysis
        classification, reason = classify_action(
            extension_analysis, extension, positions['avg_confidence']
        )
        
        result['result'] = classification
        result['reason'] = reason
        
        return result
    
    def _extract_arm_positions(self, landmarks_list: List[Dict],
                              horizontal_frame: int, release_frame: int,
                              shoulder_idx: int, elbow_idx: int, 
                              wrist_idx: int) -> Dict:
        """Extract arm joint positions for measurement window."""
        
        shoulder_positions = []
        elbow_positions = []
        wrist_positions = []
        confidences = []
        
        for frame_idx in range(horizontal_frame, release_frame + 1):
            if frame_idx >= len(landmarks_list):
                break
            
            frame_data = landmarks_list[frame_idx]
            
            if not frame_data['landmarks']:
                shoulder_positions.append(None)
                elbow_positions.append(None)
                wrist_positions.append(None)
                confidences.append(0.0)
                continue
            
            landmarks = frame_data['landmarks']
            
            if all(idx in landmarks for idx in [shoulder_idx, elbow_idx, wrist_idx]):
                shoulder = np.array([
                    landmarks[shoulder_idx]['x'],
                    landmarks[shoulder_idx]['y'],
                    landmarks[shoulder_idx]['z']
                ])
                elbow = np.array([
                    landmarks[elbow_idx]['x'],
                    landmarks[elbow_idx]['y'],
                    landmarks[elbow_idx]['z']
                ])
                wrist = np.array([
                    landmarks[wrist_idx]['x'],
                    landmarks[wrist_idx]['y'],
                    landmarks[wrist_idx]['z']
                ])
                
                shoulder_positions.append(shoulder)
                elbow_positions.append(elbow)
                wrist_positions.append(wrist)
                
                # Average visibility of the three joints
                conf = np.mean([
                    landmarks[shoulder_idx]['visibility'],
                    landmarks[elbow_idx]['visibility'],
                    landmarks[wrist_idx]['visibility']
                ])
                confidences.append(conf)
            else:
                shoulder_positions.append(None)
                elbow_positions.append(None)
                wrist_positions.append(None)
                confidences.append(0.0)
        
        valid_count = sum(1 for p in elbow_positions if p is not None)
        
        return {
            'valid': valid_count >= 3,
            'shoulder': shoulder_positions,
            'elbow': elbow_positions,
            'wrist': wrist_positions,
            'avg_confidence': np.mean(confidences) if confidences else 0.0
        }
    
    def close(self):
        """Release resources."""
        self.pose_detector.close()
