"""
Full arm rotation analysis with high-resolution sampling.

Analyzes elbow angle throughout the complete bowling arm rotation,
detecting any bend or straightening beyond measurement noise.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy.interpolate import interp1d
import csv


class FullRotationAnalyzer:
    """Analyzes elbow angle throughout full arm rotation."""
    
    def __init__(self, strict_tolerance: float = 3.0, icc_tolerance: float = 15.0):
        """
        Initialize analyzer.
        
        Args:
            strict_tolerance: Degrees of noise tolerance for strict mode
            icc_tolerance: Degrees tolerance for ICC mode (15°)
        """
        self.strict_tolerance = strict_tolerance
        self.icc_tolerance = icc_tolerance
        self.sampling_interval = 0.01  # 100 Hz sampling
    
    def analyze_full_rotation(self, landmarks_list: List[Dict], 
                             video_metadata: Dict,
                             bowling_arm: str,
                             horizontal_frame: Optional[int] = None,
                             release_frame: Optional[int] = None) -> Dict:
        """
        Analyze elbow angle throughout full arm rotation.
        
        Args:
            landmarks_list: Frame-by-frame landmark data
            video_metadata: Video FPS and other metadata
            bowling_arm: 'left' or 'right'
            horizontal_frame: Optional horizontal frame for ICC mode
            release_frame: Optional release frame for ICC mode
            
        Returns:
            Comprehensive analysis results
        """
        from .phase_detector import PhaseDetector
        from .angle_calculator import calculate_angle_3d
        
        fps = video_metadata['fps']
        
        # Calculate raw angles for all frames
        shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        raw_angles = []
        raw_confidences = []
        raw_timestamps = []
        
        for frame_idx, frame_data in enumerate(landmarks_list):
            timestamp = frame_idx / fps
            raw_timestamps.append(timestamp)
            
            if not frame_data['landmarks']:
                raw_angles.append(None)
                raw_confidences.append(0.0)
                continue
            
            lm = frame_data['landmarks']
            if all(idx in lm for idx in [shoulder_idx, elbow_idx, wrist_idx]):
                s = np.array([lm[shoulder_idx]['x'], lm[shoulder_idx]['y'], lm[shoulder_idx]['z']])
                e = np.array([lm[elbow_idx]['x'], lm[elbow_idx]['y'], lm[elbow_idx]['z']])
                w = np.array([lm[wrist_idx]['x'], lm[wrist_idx]['y'], lm[wrist_idx]['z']])
                
                angle = calculate_angle_3d(s, e, w)
                raw_angles.append(angle)
                
                conf = np.mean([lm[shoulder_idx]['visibility'],
                               lm[elbow_idx]['visibility'],
                               lm[wrist_idx]['visibility']])
                raw_confidences.append(conf)
            else:
                raw_angles.append(None)
                raw_confidences.append(0.0)
        
        # Find delivery window (full arm rotation)
        delivery_start, delivery_end = self._detect_delivery_window(
            raw_angles, raw_timestamps, horizontal_frame, release_frame
        )
        
        # Interpolate to 100 Hz (0.01s intervals)
        high_res_samples = self._interpolate_to_high_res(
            raw_angles, raw_confidences, raw_timestamps,
            delivery_start, delivery_end, fps
        )
        
        # Calculate noise tolerance from stable regions
        calculated_tolerance = self._calculate_noise_tolerance(high_res_samples)
        
        # Detect bend events in both modes
        strict_analysis = self._analyze_bends(
            high_res_samples, self.strict_tolerance, "strict"
        )
        
        icc_analysis = None
        if horizontal_frame is not None and release_frame is not None:
            icc_analysis = self._analyze_bends_icc_window(
                high_res_samples, horizontal_frame, release_frame,
                raw_timestamps, self.icc_tolerance
            )
        
        return {
            'native_fps': fps,
            'sampling_interval': self.sampling_interval,
            'delivery_start': delivery_start,
            'delivery_end': delivery_end,
            'high_res_samples': high_res_samples,
            'calculated_noise_tolerance': calculated_tolerance,
            'strict_tolerance': self.strict_tolerance,
            'icc_tolerance': self.icc_tolerance,
            'strict_analysis': strict_analysis,
            'icc_analysis': icc_analysis,
            'raw_angles': raw_angles,
            'raw_timestamps': raw_timestamps
        }
    
    def _detect_delivery_window(self, angles, timestamps, h_frame, r_frame):
        """Detect full arm rotation window."""
        # Find valid angle range
        valid_indices = [i for i, a in enumerate(angles) if a is not None]
        
        if not valid_indices:
            return 0, len(angles) - 1
        
        # Find max angle (peak extension)
        valid_angles = [angles[i] for i in valid_indices]
        max_angle = max(valid_angles)
        max_idx = valid_indices[valid_angles.index(max_angle)]
        
        # Start: 60 frames before peak (1 second at 60fps - captures wind-up)
        start_idx = max(0, max_idx - 60)
        
        # End: 30 frames after peak (0.5 seconds - captures follow-through)
        end_idx = min(len(angles) - 1, max_idx + 30)
        
        return start_idx, end_idx
    
    def _interpolate_to_high_res(self, raw_angles, raw_confidences, raw_timestamps,
                                 start_idx, end_idx, fps):
        """Interpolate angles to 100 Hz sampling."""
        # Extract delivery window
        window_angles = []
        window_confidences = []
        window_timestamps = []
        window_frames = []
        
        for i in range(start_idx, end_idx + 1):
            if raw_angles[i] is not None:
                window_angles.append(raw_angles[i])
                window_confidences.append(raw_confidences[i])
                window_timestamps.append(raw_timestamps[i])
                window_frames.append(i)
        
        if len(window_angles) < 2:
            return []
        
        # Create interpolation functions
        angle_interp = interp1d(window_timestamps, window_angles, 
                               kind='cubic', fill_value='extrapolate')
        conf_interp = interp1d(window_timestamps, window_confidences,
                              kind='linear', fill_value='extrapolate')
        
        # Generate 100 Hz timeline
        start_time = window_timestamps[0]
        end_time = window_timestamps[-1]
        
        high_res_times = np.arange(start_time, end_time, self.sampling_interval)
        
        # Interpolate
        samples = []
        for t in high_res_times:
            angle = float(angle_interp(t))
            confidence = float(conf_interp(t))
            
            # Determine if measured or interpolated
            is_measured = any(abs(t - rt) < (0.5 / fps) for rt in window_timestamps)
            
            # Find closest frame
            frame = int(t * fps)
            
            samples.append({
                'time': t,
                'angle': angle,
                'confidence': confidence,
                'measured': is_measured,
                'frame': frame
            })
        
        # Calculate changes
        for i in range(1, len(samples)):
            samples[i]['change'] = samples[i]['angle'] - samples[i-1]['angle']
        if samples:
            samples[0]['change'] = 0.0
        
        return samples
    
    def _calculate_noise_tolerance(self, samples):
        """Calculate noise tolerance from stable regions."""
        if len(samples) < 10:
            return 3.0  # Default
        
        # Find regions where angle is relatively stable
        changes = [abs(s.get('change', 0)) for s in samples]
        
        # Take 25th percentile of changes as noise floor
        sorted_changes = sorted([c for c in changes if c > 0])
        
        if not sorted_changes:
            return 3.0
        
        percentile_25 = sorted_changes[len(sorted_changes) // 4]
        percentile_75 = sorted_changes[3 * len(sorted_changes) // 4]
        
        # Noise tolerance = 75th percentile + margin
        calculated = percentile_75 * 1.5
        
        # Clamp between 2° and 5°
        return max(2.0, min(5.0, calculated))
    
    def _analyze_bends(self, samples, tolerance, mode):
        """Analyze bends with given tolerance."""
        bend_events = []
        
        for i in range(1, len(samples)):
            change = samples[i].get('change', 0)
            
            if abs(change) > tolerance:
                event_type = 'extension' if change > 0 else 'flexion'
                
                bend_events.append({
                    'time': samples[i]['time'],
                    'frame': samples[i]['frame'],
                    'type': event_type,
                    'magnitude': abs(change),
                    'change': change,
                    'angle_before': samples[i-1]['angle'],
                    'angle_after': samples[i]['angle'],
                    'phase': self._get_phase_label(i, len(samples))
                })
        
        # Calculate cumulative extension
        total_extension = 0
        for event in bend_events:
            if event['type'] == 'extension':
                total_extension += event['magnitude']
        
        # Verdict
        if not bend_events:
            verdict = 'likely within threshold'
            reason = f'No bend events detected above {tolerance:.1f}° tolerance ({mode} mode)'
        else:
            verdict = 'possible concern'
            num_events = len(bend_events)
            max_event = max(bend_events, key=lambda e: e['magnitude'])
            reason = f'{num_events} bend events detected (max: {max_event["magnitude"]:.1f}°, tolerance: {tolerance:.1f}°, {mode} mode)'
        
        return {
            'mode': mode,
            'tolerance': tolerance,
            'bend_events': bend_events,
            'num_events': len(bend_events),
            'total_extension': total_extension,
            'verdict': verdict,
            'reason': reason
        }
    
    def _analyze_bends_icc_window(self, samples, h_frame, r_frame, raw_timestamps, tolerance):
        """Analyze bends in ICC window (horizontal to release)."""
        h_time = raw_timestamps[h_frame] if h_frame < len(raw_timestamps) else 0
        r_time = raw_timestamps[r_frame] if r_frame < len(raw_timestamps) else samples[-1]['time']
        
        # Filter samples in ICC window
        icc_samples = [s for s in samples if h_time <= s['time'] <= r_time]
        
        if not icc_samples:
            return None
        
        # Calculate total extension in window
        initial_angle = icc_samples[0]['angle']
        final_angle = icc_samples[-1]['angle']
        total_extension = final_angle - initial_angle
        
        # Find bend events
        bend_events = []
        for i in range(1, len(icc_samples)):
            change = icc_samples[i]['angle'] - icc_samples[i-1]['angle']
            
            if abs(change) > 1.0:  # Any measurable change
                bend_events.append({
                    'time': icc_samples[i]['time'],
                    'frame': icc_samples[i]['frame'],
                    'type': 'extension' if change > 0 else 'flexion',
                    'magnitude': abs(change),
                    'change': change,
                    'angle_before': icc_samples[i-1]['angle'],
                    'angle_after': icc_samples[i]['angle'],
                    'phase': 'icc_window'
                })
        
        # ICC verdict
        if total_extension <= tolerance:
            verdict = 'likely within threshold'
            reason = f'Total extension {total_extension:.1f}° <= {tolerance:.1f}° (ICC mode: horizontal to release)'
        else:
            verdict = 'possible concern'
            reason = f'Total extension {total_extension:.1f}° > {tolerance:.1f}° (ICC mode: horizontal to release)'
        
        return {
            'mode': 'icc',
            'tolerance': tolerance,
            'total_extension': total_extension,
            'bend_events': bend_events,
            'num_events': len(bend_events),
            'verdict': verdict,
            'reason': reason,
            'window_start': h_time,
            'window_end': r_time
        }
    
    def _get_phase_label(self, idx, total):
        """Get phase label for a sample."""
        pos = idx / total
        if pos < 0.33:
            return 'early'
        elif pos < 0.67:
            return 'middle'
        else:
            return 'late'
    
    def export_samples_csv(self, samples: List[Dict], output_path: str):
        """Export high-resolution samples to CSV."""
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'time_sec', 'frame', 'elbow_angle_deg', 'change_deg',
                'measured', 'interpolated', 'confidence'
            ])
            writer.writeheader()
            
            for sample in samples:
                writer.writerow({
                    'time_sec': f"{sample['time']:.3f}",
                    'frame': sample['frame'],
                    'elbow_angle_deg': f"{sample['angle']:.2f}",
                    'change_deg': f"{sample.get('change', 0):.2f}",
                    'measured': 'yes' if sample['measured'] else 'no',
                    'interpolated': 'no' if sample['measured'] else 'yes',
                    'confidence': f"{sample['confidence']:.3f}"
                })
