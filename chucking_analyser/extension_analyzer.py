"""
Advanced extension analysis to detect sudden vs smooth straightening.
"""

import numpy as np
from typing import List, Optional, Tuple


def analyze_extension_pattern(angles: List[Optional[float]], 
                              start_idx: int, 
                              end_idx: int) -> dict:
    """
    Analyze the pattern of elbow extension to detect chucking.
    
    Chucking is characterized by SUDDEN straightening at the end,
    while legal actions show smooth acceleration throughout.
    
    Args:
        angles: List of elbow angles
        start_idx: Start of measurement window
        end_idx: End of measurement window
        
    Returns:
        Dict with extension metrics
    """
    # Extract valid angles in window
    window_angles = []
    for i in range(start_idx, min(end_idx + 1, len(angles))):
        if angles[i] is not None:
            window_angles.append(angles[i])
    
    if len(window_angles) < 3:
        return {
            'total_extension': 0.0,
            'max_frame_change': 0.0,
            'sudden_change_detected': False,
            'pattern': 'insufficient_data'
        }
    
    # Calculate frame-to-frame changes
    frame_changes = []
    for i in range(1, len(window_angles)):
        change = window_angles[i] - window_angles[i-1]
        frame_changes.append(change)
    
    total_extension = window_angles[-1] - window_angles[0]
    max_frame_change = max(frame_changes) if frame_changes else 0.0
    avg_frame_change = np.mean(frame_changes) if frame_changes else 0.0
    std_frame_change = np.std(frame_changes) if frame_changes else 0.0
    
    # Detect chucking: look for large changes in the LAST 2-3 frames
    # (chucking = sudden straightening at the end, not smooth acceleration throughout)
    if len(frame_changes) >= 3:
        # Check last 3 frames
        last_3_changes = frame_changes[-3:]
        max_last_3 = max(last_3_changes)
        
        # Also check first half for comparison
        first_half = frame_changes[:len(frame_changes)//2]
        max_first_half = max(first_half) if first_half else 0
        
        # Chucking detected if:
        # 1. Large change (>8°) in last 3 frames, AND
        # 2. That change is larger than anything in first half (indicating it's not just acceleration)
        sudden_change_detected = (max_last_3 > 8.0 and max_last_3 > max_first_half)
    else:
        sudden_change_detected = max_frame_change > 10.0
    
    # Classify pattern
    if sudden_change_detected:
        pattern = 'sudden_spike'
    elif total_extension > 20 and std_frame_change < 3.0:
        pattern = 'smooth_large'
    elif total_extension > 15:
        pattern = 'gradual_large'
    else:
        pattern = 'normal'
    
    return {
        'total_extension': total_extension,
        'max_frame_change': max_frame_change,
        'avg_frame_change': avg_frame_change,
        'sudden_change_detected': sudden_change_detected,
        'pattern': pattern,
        'frame_changes': frame_changes
    }


def classify_action(extension_analysis: dict, total_extension: float, 
                   confidence: float) -> Tuple[str, str]:
    """
    Classify bowling action based on extension analysis.
    
    NOTE: The sudden-versus-smooth pattern detection is an EXPERIMENTAL heuristic
    validated on only two reference clips. Single 2D camera cannot perfectly
    separate elbow extension from whole-arm rotation.
    
    Returns:
        (result, reason) tuple
    """
    pattern = extension_analysis['pattern']
    sudden = extension_analysis['sudden_change_detected']
    max_change = extension_analysis['max_frame_change']
    
    # Use "unable to assess" more liberally for ambiguous cases
    if confidence < 0.4:
        return 'unable to assess', 'low confidence pose detection'
    
    # If confidence is marginal and pattern is ambiguous, be conservative
    if confidence < 0.55 and pattern not in ['sudden_spike', 'normal']:
        return 'unable to assess', 'marginal confidence with ambiguous pattern - recommend expert review'
    
    # Priority 1: Detect chucking by sudden spike at the end (experimental heuristic)
    if sudden and max_change > 8.0:
        return 'possible concern', f'sudden elbow straightening detected ({max_change:.1f}° spike) [experimental pattern-based detection]'
    elif pattern == 'sudden_spike':
        return 'possible concern', f'abrupt extension pattern ({max_change:.1f}° peak change) [experimental heuristic - single 2D camera limitation]'
    
    # Priority 2: Large smooth extension is likely whole-arm rotation (experimental)
    elif pattern == 'smooth_large' or pattern == 'gradual_large':
        # Note the experimental nature
        return 'likely within threshold', f'smooth extension pattern (total {total_extension:.1f}°, likely arm rotation not elbow straightening) [experimental - cannot perfectly separate with 2D]'
    
    # Priority 3: Normal threshold-based classification (more reliable)
    elif total_extension <= 15:
        return 'likely within threshold', f'extension {total_extension:.1f}° <= 15.0°'
    elif total_extension <= 20:
        # Be more conservative for borderline cases
        return 'possible concern', f'extension {total_extension:.1f}° moderately above threshold - recommend expert review'
    else:
        return 'possible concern', f'large extension {total_extension:.1f}° detected - expert review required'
