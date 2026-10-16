"""
Find the actual maximum extension point in bowling deliveries.
"""

import json
import numpy as np

def analyze_extension_window(debug_json_path):
    """Analyze where actual maximum extension occurs."""
    with open(debug_json_path, 'r') as f:
        data = json.load(f)
    
    angles = data['angles']['values']
    frames = data['angles']['frames']
    h_frame = data['horizontal_frame']
    r_frame = data['release_frame']
    
    print(f"\nAnalyzing: {debug_json_path}")
    print(f"Detected horizontal: {h_frame}, release: {r_frame}")
    
    # Find valid angles
    valid_data = [(f, a) for f, a in zip(frames, angles) if a is not None]
    
    if not valid_data:
        print("No valid angles!")
        return
    
    # Find maximum angle (most straightened arm)
    max_angle = max(a for _, a in valid_data)
    max_frame = [f for f, a in valid_data if a == max_angle][0]
    
    print(f"Maximum angle (straightest arm): {max_angle:.1f}° at frame {max_frame}")
    
    # Find angles around detected frames
    if h_frame in frames:
        h_idx = frames.index(h_frame)
        h_angle = angles[h_idx]
        print(f"Detected horizontal angle: {h_angle:.1f}° at frame {h_frame}")
    
    if r_frame in frames:
        r_idx = frames.index(r_frame)
        r_angle = angles[r_idx]
        print(f"Detected release angle: {r_angle:.1f}° at frame {r_frame}")
    
    # Look for the actual extension by finding min angle before max
    # (arm goes from bent -> straight during delivery)
    
    # Find minimum angle before max (most bent position before straightening)
    before_max = [(f, a) for f, a in valid_data if f < max_frame and a is not None]
    if before_max:
        min_before = min(a for _, a in before_max)
        min_frame_before = [f for f, a in before_max if a == min_before][0]
        
        print(f"\nMost bent (before max): {min_before:.1f}° at frame {min_frame_before}")
        print(f"Actual extension: {max_angle - min_before:.1f}°")
        print(f"Frames from bent to straight: {min_frame_before} -> {max_frame}")
    
    # Show angles in window around detected horizontal
    print(f"\nAngles around detected horizontal (frame {h_frame}):")
    for offset in range(-5, 6):
        f = h_frame + offset
        if f in frames:
            idx = frames.index(f)
            a = angles[idx]
            marker = " <-- HORIZONTAL" if offset == 0 else ""
            marker += " <-- RELEASE" if f == r_frame else ""
            if a is not None:
                print(f"  Frame {f:4d}: {a:6.1f}°{marker}")


if __name__ == '__main__':
    analyze_extension_window('chuck1_debug.json')
    analyze_extension_window('legal1_debug.json')
