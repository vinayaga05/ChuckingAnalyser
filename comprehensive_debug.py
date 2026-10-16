"""
Comprehensive debug of both videos.
"""

import json
import numpy as np
from chucking_analyser.pose_detector import PoseDetector
from chucking_analyser.phase_detector import PhaseDetector
from chucking_analyser.angle_calculator import calculate_angle_3d

def comprehensive_debug(video_path, name):
    print(f"\n{'='*70}")
    print(f"{name}: {video_path}")
    print('='*70)
    
    detector = PoseDetector()
    landmarks_list, meta = detector.process_video(video_path)
    detector.close()
    
    bowling_arm = PhaseDetector.detect_bowling_arm(landmarks_list)
    shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
    
    # Calculate all angles
    angles = []
    for i in range(len(landmarks_list)):
        if not landmarks_list[i]['landmarks']:
            angles.append(None)
            continue
        lm = landmarks_list[i]['landmarks']
        if all(idx in lm for idx in [shoulder_idx, elbow_idx, wrist_idx]):
            s = np.array([lm[shoulder_idx]['x'], lm[shoulder_idx]['y'], lm[shoulder_idx]['z']])
            e = np.array([lm[elbow_idx]['x'], lm[elbow_idx]['y'], lm[elbow_idx]['z']])
            w = np.array([lm[wrist_idx]['x'], lm[wrist_idx]['y'], lm[wrist_idx]['z']])
            angles.append(calculate_angle_3d(s, e, w))
        else:
            angles.append(None)
    
    # Find max
    valid_angles = [(i, a) for i, a in enumerate(angles) if a is not None]
    max_angle = max(a for _, a in valid_angles)
    max_frame = [i for i, a in valid_angles if a == max_angle][0]
    
    print(f"Max angle: {max_angle:.1f}° at frame {max_frame}")
    
    # Detect phases
    h_frame = PhaseDetector.detect_arm_horizontal(landmarks_list, bowling_arm)
    r_frame = PhaseDetector.detect_ball_release(landmarks_list, bowling_arm, h_frame) if h_frame else None
    
    print(f"Detected horizontal: {h_frame}")
    print(f"Detected release: {r_frame}")
    
    if h_frame and r_frame:
        h_angle = angles[h_frame]
        r_angle = angles[r_frame]
        extension = r_angle - h_angle
        
        print(f"\nMeasurement:")
        print(f"  Horizontal frame {h_frame}: {h_angle:.1f}°")
        print(f"  Release frame {r_frame}: {r_angle:.1f}°")
        print(f"  Extension: {extension:.1f}°")
        print(f"  Window: {r_frame - h_frame} frames ({(r_frame - h_frame) / meta['fps']:.3f} sec)")
        
        # Show angles in window
        print(f"\n  Angles in measurement window:")
        for i in range(max(0, h_frame - 2), min(len(angles), r_frame + 3)):
            marker = ""
            if i == h_frame:
                marker = " <-- START"
            elif i == r_frame:
                marker = " <-- END"
            elif i == max_frame:
                marker = " <-- MAX"
            
            a = angles[i]
            if a:
                print(f"    Frame {i:4d}: {a:6.1f}°{marker}")
    
    # Show angles around max
    print(f"\n  Angles around max (frame {max_frame}):")
    for i in range(max(0, max_frame - 10), min(len(angles), max_frame + 11)):
        a = angles[i]
        marker = " <-- MAX" if i == max_frame else ""
        if a:
            print(f"    Frame {i:4d}: {a:6.1f}°{marker}")

if __name__ == '__main__':
    comprehensive_debug('/home/ubuntu/.cursor/projects/workspace/uploads/chuck1_0774.mp4', 'CHUCK1 (ILLEGAL)')
    comprehensive_debug('/home/ubuntu/.cursor/projects/workspace/uploads/legal1_3904.mp4', 'LEGAL1 (LEGAL)')
