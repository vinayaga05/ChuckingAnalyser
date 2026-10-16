"""
Generate a synthetic test video for bowling action analysis.
"""

import cv2
import numpy as np


def create_bowling_action_video(output_path: str, duration_sec: int = 3, fps: int = 30):
    """
    Create a synthetic video of a person performing a bowling action.
    
    Args:
        output_path: Path to save the video
        duration_sec: Duration in seconds
        fps: Frames per second
    """
    width, height = 640, 480
    total_frames = duration_sec * fps
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    print(f"Generating {total_frames} frames at {fps} fps...")
    
    for frame_idx in range(total_frames):
        # Create blank frame
        frame = np.ones((height, width, 3), dtype=np.uint8) * 240
        
        # Draw ground line
        cv2.line(frame, (0, height - 50), (width, height - 50), (100, 100, 100), 2)
        
        # Calculate animation progress (0 to 1)
        progress = frame_idx / total_frames
        
        # Simulate bowling action phases
        if progress < 0.3:
            # Wind-up phase: arm back
            arm_angle = -30 - progress * 100
        elif progress < 0.6:
            # Delivery phase: arm swings through horizontal to release
            local_progress = (progress - 0.3) / 0.3
            arm_angle = -60 + local_progress * 150
        else:
            # Follow-through: arm continues up
            local_progress = (progress - 0.6) / 0.4
            arm_angle = 90 + local_progress * 45
        
        # Draw stick figure bowler
        draw_bowler(frame, width // 2, height - 100, arm_angle, progress)
        
        # Add frame counter
        cv2.putText(frame, f"Frame: {frame_idx}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        out.write(frame)
    
    out.release()
    print(f"Video saved to: {output_path}")


def draw_bowler(frame, center_x, foot_y, arm_angle, progress):
    """
    Draw a stick figure bowler.
    
    Args:
        frame: Image frame
        center_x: X position of center
        foot_y: Y position of feet
        arm_angle: Angle of bowling arm in degrees
        progress: Animation progress (0 to 1)
    """
    # Body proportions
    torso_height = 80
    leg_length = 70
    head_radius = 20
    upper_arm_length = 50
    forearm_length = 45
    
    # Positions
    hip_y = foot_y - leg_length
    shoulder_y = hip_y - torso_height
    head_y = shoulder_y - head_radius - 5
    
    # Draw head
    cv2.circle(frame, (center_x, head_y), head_radius, (0, 0, 0), 2)
    
    # Draw torso
    cv2.line(frame, (center_x, shoulder_y), (center_x, hip_y), (0, 0, 0), 3)
    
    # Draw legs (slight walking motion)
    leg_offset = int(10 * np.sin(progress * np.pi * 4))
    cv2.line(frame, (center_x, hip_y), (center_x - 15 + leg_offset, foot_y), (0, 0, 0), 3)
    cv2.line(frame, (center_x, hip_y), (center_x + 15 - leg_offset, foot_y), (0, 0, 0), 3)
    
    # Draw bowling arm (right arm)
    arm_angle_rad = np.radians(arm_angle)
    
    # Shoulder position (right shoulder is slightly to the right)
    shoulder_x = center_x + 25
    shoulder_pos = (shoulder_x, shoulder_y)
    
    # Elbow position
    elbow_x = shoulder_x + int(upper_arm_length * np.cos(arm_angle_rad))
    elbow_y = shoulder_y + int(upper_arm_length * np.sin(arm_angle_rad))
    elbow_pos = (elbow_x, elbow_y)
    
    # Simulate elbow extension during delivery
    # Extension increases during delivery phase (0.3 to 0.6)
    if 0.3 <= progress <= 0.6:
        local_progress = (progress - 0.3) / 0.3
        # Simulate some elbow straightening (10-12 degrees)
        extension_factor = 0.1 + local_progress * 0.08
    else:
        extension_factor = 0.1
    
    forearm_angle_offset = extension_factor * 20  # Additional straightening
    forearm_angle_rad = arm_angle_rad + np.radians(forearm_angle_offset)
    
    # Wrist position
    wrist_x = elbow_x + int(forearm_length * np.cos(forearm_angle_rad))
    wrist_y = elbow_y + int(forearm_length * np.sin(forearm_angle_rad))
    wrist_pos = (wrist_x, wrist_y)
    
    # Draw arm
    cv2.line(frame, shoulder_pos, elbow_pos, (0, 0, 255), 4)  # Upper arm (red)
    cv2.line(frame, elbow_pos, wrist_pos, (255, 0, 0), 4)  # Forearm (blue)
    
    # Draw joints
    cv2.circle(frame, shoulder_pos, 6, (0, 255, 0), -1)
    cv2.circle(frame, elbow_pos, 6, (0, 255, 0), -1)
    cv2.circle(frame, wrist_pos, 6, (0, 255, 0), -1)
    
    # Draw non-bowling arm (left arm) - static
    left_shoulder_x = center_x - 25
    left_shoulder_pos = (left_shoulder_x, shoulder_y)
    left_elbow_pos = (left_shoulder_x - 30, shoulder_y + 40)
    left_wrist_pos = (left_shoulder_x - 20, shoulder_y + 75)
    
    cv2.line(frame, left_shoulder_pos, left_elbow_pos, (100, 100, 100), 2)
    cv2.line(frame, left_elbow_pos, left_wrist_pos, (100, 100, 100), 2)


if __name__ == '__main__':
    create_bowling_action_video('test_bowling.mp4', duration_sec=3, fps=30)
