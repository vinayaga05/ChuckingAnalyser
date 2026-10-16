"""
Debug script to analyze bowling videos in detail.
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from chucking_analyser.pose_detector import PoseDetector
from chucking_analyser.phase_detector import PhaseDetector
from chucking_analyser.angle_calculator import calculate_angle_3d, smooth_positions
from chucking_analyser.delivery_detector import DeliveryDetector


def debug_video(video_path, output_prefix):
    """Debug a single video."""
    print(f"\n{'='*70}")
    print(f"Debugging: {video_path}")
    print('='*70)
    
    # Process video
    pose_detector = PoseDetector()
    landmarks_list, video_metadata = pose_detector.process_video(video_path)
    pose_detector.close()
    
    print(f"Video: {video_metadata['fps']:.1f} fps, {video_metadata['frame_count']} frames")
    
    # Detect bowling arm
    bowling_arm = PhaseDetector.detect_bowling_arm(landmarks_list)
    print(f"Bowling arm: {bowling_arm}")
    
    # Get landmark indices
    shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
    print(f"Tracking landmarks: shoulder={shoulder_idx}, elbow={elbow_idx}, wrist={wrist_idx}")
    
    # Detect deliveries
    delivery_detector = DeliveryDetector()
    deliveries = delivery_detector.detect_deliveries(landmarks_list, bowling_arm)
    
    if not deliveries:
        deliveries = [(0, len(landmarks_list) - 1)]
        print("No deliveries detected, using full video")
    else:
        print(f"Found {len(deliveries)} deliveries")
    
    # Analyze first delivery
    start_frame, end_frame = deliveries[0]
    print(f"Delivery window: frames {start_frame}-{end_frame}")
    
    # Detect phases
    horizontal_frame = PhaseDetector.detect_arm_horizontal(
        landmarks_list, bowling_arm, start_frame, end_frame
    )
    print(f"Horizontal frame: {horizontal_frame}")
    
    release_frame = None
    if horizontal_frame:
        release_frame = PhaseDetector.detect_ball_release(
            landmarks_list, bowling_arm, horizontal_frame
        )
    print(f"Release frame: {release_frame}")
    
    # Calculate angles for all frames
    angles = []
    confidences = []
    frame_indices = []
    
    for frame_idx in range(start_frame, min(end_frame + 1, len(landmarks_list))):
        frame_data = landmarks_list[frame_idx]
        
        if not frame_data['landmarks']:
            angles.append(None)
            confidences.append(0.0)
        else:
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
                
                angle = calculate_angle_3d(shoulder, elbow, wrist)
                angles.append(angle)
                
                conf = np.mean([
                    landmarks[shoulder_idx]['visibility'],
                    landmarks[elbow_idx]['visibility'],
                    landmarks[wrist_idx]['visibility']
                ])
                confidences.append(conf)
            else:
                angles.append(None)
                confidences.append(0.0)
        
        frame_indices.append(frame_idx)
    
    # Report key angles
    if horizontal_frame and release_frame:
        h_idx = horizontal_frame - start_frame
        r_idx = release_frame - start_frame
        
        if h_idx < len(angles) and r_idx < len(angles):
            h_angle = angles[h_idx]
            r_angle = angles[r_idx]
            
            print(f"\nKey angles:")
            print(f"  At horizontal (frame {horizontal_frame}): {h_angle:.1f}°")
            print(f"  At release (frame {release_frame}): {r_angle:.1f}°")
            print(f"  Extension (release - horizontal): {r_angle - h_angle:.1f}°")
            print(f"  Average confidence: {np.mean([c for c in confidences if c > 0]):.2f}")
    
    # Plot angles
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Angle trace
    valid_indices = [i for i, a in enumerate(angles) if a is not None]
    valid_angles = [angles[i] for i in valid_indices]
    valid_frames = [frame_indices[i] for i in valid_indices]
    
    ax1.plot(valid_frames, valid_angles, 'b-', linewidth=2, label='Elbow angle')
    
    if horizontal_frame:
        ax1.axvline(horizontal_frame, color='orange', linestyle='--', linewidth=2, label='Horizontal')
    if release_frame:
        ax1.axvline(release_frame, color='red', linestyle='--', linewidth=2, label='Release')
    
    # Mark measurement window
    if horizontal_frame and release_frame:
        ax1.axvspan(horizontal_frame, release_frame, alpha=0.2, color='yellow', label='Measurement window')
    
    ax1.set_xlabel('Frame number', fontsize=12)
    ax1.set_ylabel('Elbow angle (degrees)', fontsize=12)
    ax1.set_title(f'Elbow Angle Trace - {output_prefix}', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Confidence
    ax2.plot(frame_indices, confidences, 'g-', linewidth=2, label='Landmark confidence')
    
    if horizontal_frame:
        ax2.axvline(horizontal_frame, color='orange', linestyle='--', linewidth=2)
    if release_frame:
        ax2.axvline(release_frame, color='red', linestyle='--', linewidth=2)
    
    ax2.set_xlabel('Frame number', fontsize=12)
    ax2.set_ylabel('Confidence', fontsize=12)
    ax2.set_title('Landmark Visibility/Confidence', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_debug.png', dpi=150, bbox_inches='tight')
    print(f"\nDebug plot saved: {output_prefix}_debug.png")
    
    # Save detailed data
    debug_data = {
        'video': video_path,
        'bowling_arm': bowling_arm,
        'horizontal_frame': horizontal_frame,
        'release_frame': release_frame,
        'angles': {
            'frames': frame_indices,
            'values': angles,
            'confidences': confidences
        }
    }
    
    with open(f'{output_prefix}_debug.json', 'w') as f:
        json.dump(debug_data, f, indent=2)
    print(f"Debug data saved: {output_prefix}_debug.json")


if __name__ == '__main__':
    debug_video('/home/ubuntu/.cursor/projects/workspace/uploads/chuck1_0774.mp4', 'chuck1')
    debug_video('/home/ubuntu/.cursor/projects/workspace/uploads/legal1_3904.mp4', 'legal1')
