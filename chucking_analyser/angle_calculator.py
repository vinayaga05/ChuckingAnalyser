"""
Angle calculation and smoothing utilities.
"""

import numpy as np
from typing import List, Optional, Tuple
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d


def calculate_angle_3d(shoulder: np.ndarray, elbow: np.ndarray, wrist: np.ndarray) -> float:
    """
    Calculate angle at elbow joint in 3D space.
    
    Args:
        shoulder: 3D position of shoulder [x, y, z]
        elbow: 3D position of elbow [x, y, z]
        wrist: 3D position of wrist [x, y, z]
        
    Returns:
        Angle at elbow in degrees (0-180)
    """
    # Vectors from elbow to shoulder and elbow to wrist
    vec1 = shoulder - elbow
    vec2 = wrist - elbow
    
    # Normalize vectors
    vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-8)
    vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-8)
    
    # Calculate angle using dot product
    cos_angle = np.clip(np.dot(vec1_norm, vec2_norm), -1.0, 1.0)
    angle_rad = np.arccos(cos_angle)
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg


def calculate_elbow_extension(initial_angle: float, final_angle: float) -> float:
    """
    Calculate elbow extension from initial to final angle.
    
    Elbow extension is measured as the increase in elbow angle (straightening).
    A larger angle means more extension (straighter arm).
    
    Args:
        initial_angle: Initial elbow angle in degrees
        final_angle: Final elbow angle in degrees
        
    Returns:
        Extension in degrees (positive means arm straightened)
    """
    # Extension = final_angle - initial_angle
    # Positive extension means arm straightened (angle increased)
    return final_angle - initial_angle


def smooth_angles(angles: List[Optional[float]], window_length: int = 7, 
                  polyorder: int = 2, sigma: float = 1.5) -> List[Optional[float]]:
    """
    Smooth angle sequence using Savitzky-Golay filter and Gaussian smoothing.
    
    Args:
        angles: List of angle values (may contain None for missing data)
        window_length: Window length for Savitzky-Golay filter (must be odd)
        polyorder: Polynomial order for Savitzky-Golay filter
        sigma: Standard deviation for Gaussian smoothing
        
    Returns:
        Smoothed angle sequence (same length as input)
    """
    if not angles:
        return []
    
    # Convert to numpy array, marking None as NaN
    angle_array = np.array([a if a is not None else np.nan for a in angles])
    
    # Find valid (non-NaN) indices
    valid_mask = ~np.isnan(angle_array)
    valid_indices = np.where(valid_mask)[0]
    
    if len(valid_indices) == 0:
        return angles
    
    # Interpolate missing values for smoothing
    if len(valid_indices) < len(angle_array):
        angle_array = np.interp(
            np.arange(len(angle_array)),
            valid_indices,
            angle_array[valid_indices]
        )
    
    # Apply Gaussian smoothing first
    smoothed = gaussian_filter1d(angle_array, sigma=sigma)
    
    # Apply Savitzky-Golay filter if we have enough points
    if len(smoothed) >= window_length:
        if window_length % 2 == 0:
            window_length += 1
        smoothed = savgol_filter(smoothed, window_length, polyorder)
    
    # Convert back to list, restoring None for originally missing values
    result = []
    for i, original in enumerate(angles):
        if original is None:
            result.append(None)
        else:
            result.append(float(smoothed[i]))
    
    return result


def smooth_positions(positions: List[Optional[np.ndarray]], sigma: float = 2.0) -> List[Optional[np.ndarray]]:
    """
    Smooth 3D position sequence using Gaussian filter.
    
    Args:
        positions: List of 3D positions (may contain None)
        sigma: Standard deviation for Gaussian smoothing
        
    Returns:
        Smoothed position sequence
    """
    if not positions:
        return []
    
    # Extract valid positions
    valid_indices = [i for i, pos in enumerate(positions) if pos is not None]
    
    if len(valid_indices) == 0:
        return positions
    
    # Stack valid positions
    valid_positions = np.array([positions[i] for i in valid_indices])
    
    # Interpolate to full sequence
    all_positions = np.zeros((len(positions), 3))
    for dim in range(3):
        all_positions[:, dim] = np.interp(
            np.arange(len(positions)),
            valid_indices,
            valid_positions[:, dim]
        )
    
    # Smooth each dimension independently
    for dim in range(3):
        all_positions[:, dim] = gaussian_filter1d(all_positions[:, dim], sigma=sigma)
    
    # Convert back to list, preserving None for originally missing
    result = []
    for i, original in enumerate(positions):
        if original is None:
            result.append(None)
        else:
            result.append(all_positions[i])
    
    return result
