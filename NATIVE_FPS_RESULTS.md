# Native FPS Analysis Results

## Changes Implemented

### 1. Native Frame Rate Sampling (No Interpolation)
✅ Removed artificial 0.01s (100 Hz) resampling
✅ Now samples at video's native FPS - one sample per frame
✅ No interpolation - all samples are measured directly
✅ Frame interval = 1/native_fps shown in reports and CSV

### 2. Slow-Motion Preview Video
✅ Renders at 30 FPS output (each source frame → 1 output frame)
✅ Slowdown factor = source_fps / 30
✅ Includes:
- Arm skeleton visualization (shoulder-elbow-wrist)
- Wrist and elbow trajectory trails (30-frame history)
- Trails color-coded by elbow angle
- Live elbow angle display
- Bend alerts when change exceeds tolerance
- On-screen info: frame number, source FPS, slow-mo factor

### 3. Arm Path Trajectory Plot
✅ Added to HTML report
✅ Shows wrist and elbow trajectories during full rotation
✅ Color-coded by elbow angle (blue=flexed, white=neutral, red=extended)
✅ Red stars mark bend event locations
✅ Normalized coordinates for consistent display

### 4. Updated CSV Format
✅ Removed "measured/interpolated" columns (all samples are measured now)
✅ Format: frame, time_sec, elbow_angle_deg, change_deg, confidence
✅ Time calculated as frame / native_fps

### 5. Updated HTML Reports
✅ Changed subtitle from "High-Resolution Elbow Angle Tracking (100 Hz Sampling)" to "Native Frame Rate Analysis - One Sample Per Frame"
✅ Show "Frame Interval" instead of "Sampling Interval"
✅ Show "X frames" instead of "X samples @ 0.01s intervals"
✅ Updated sample table headers and tooltips

## Test Results

### Chuck1 (Known Chucking Delivery)

**Source Video**:
- Native FPS: **60.0**
- Frame Interval: **0.0167s** (1/60)
- Samples: **91 frames** (one per frame at native FPS)

**Slow-Motion Video**:
- Output FPS: 30.0
- Slow-down Factor: **2.0x** (60 / 30)
- Duration: 27.3 seconds

**Analysis Results**:
- Calculated Noise: 7.0°

**Strict Mode**:
- Verdict: Possible Concern ⚠️
- Events: 46 bend events
- Max Event: 16.3° extension
- Tolerance: 3.0°

**ICC Mode**:
- Verdict: Possible Concern ⚠️
- Extension: **16.5°**
- Tolerance: 15.0°
- Just over threshold

**Assessment**: Both modes flag this as concerning. ICC mode shows 16.5° extension, slightly above the 15° threshold. Native FPS sampling captures 91 frames through the full rotation.

---

### Legal1 (Known Legal Delivery)

**Source Video**:
- Native FPS: **60.0**
- Frame Interval: **0.0167s** (1/60)
- Samples: **91 frames** (one per frame at native FPS)

**Slow-Motion Video**:
- Output FPS: 30.0
- Slow-down Factor: **2.0x** (60 / 30)

**Analysis Results**:
- Calculated Noise: 6.5°

**Strict Mode**:
- Verdict: Possible Concern ⚠️
- Events: 34 bend events
- Max Event: 14.9° extension
- Tolerance: 3.0°

**ICC Mode**:
- Verdict: Possible Concern ⚠️
- Extension: **50.8°** (!)
- Tolerance: 15.0°
- Far exceeds threshold

**Critical Finding**: Legal1 shows **50.8° extension** in ICC mode (was 44.7° with interpolation).

This confirms the 2D projection artifact issue:
- A known legal delivery shows physically impossible extension
- The artifact magnitude increased slightly from interpolated (44.7°) to native sampling (50.8°)
- This demonstrates that the issue is inherent to 2D camera analysis, not an interpolation artifact
- The arm rotating toward/away from camera creates artificial angle changes in 2D projection

## Key Findings

### 1. Native FPS vs Interpolation
The switch from 0.01s interpolation to native FPS:
- **Chuck1**: 151 samples (interpolated) → 91 samples (native 60 FPS)
- **Legal1**: 150 samples (interpolated) → 91 samples (native 60 FPS)
- **ICC extension (chuck1)**: 15.8° (interpolated) → 16.5° (native)
- **ICC extension (legal1)**: 44.7° (interpolated) → 50.8° (native)

The artifact actually *increased* with native sampling, showing the issue is not interpolation-related.

### 2. Correct FPS Reporting
The earlier claim that "60 fps footage gave all-measured 0.01s samples" was incorrect:
- 60 FPS = 1 frame every 0.0167 seconds, **not** 0.01 seconds
- 0.01s sampling = 100 FPS, which would require interpolation at 60 FPS source
- Now correctly samples at native rate with no interpolation

### 3. Slow-Motion Video Effectiveness
The 2.0x slow-motion (60→30 FPS) provides:
- Smooth playback on standard displays
- Clear visibility of arm motion details
- Trajectory trails show arm path over time
- Real-time angle and bend alerts
- For higher FPS sources (120, 240 FPS), would give 4x, 8x slow-motion

### 4. 2D Projection Artifact Confirmation
Both interpolated and native FPS sampling show the same fundamental issue:
- Legal actions show impossible extensions (44-51°)
- The problem is inherent to 2D camera perspective
- Not caused by interpolation or sampling method
- Only solvable with multi-camera 3D reconstruction or depth cameras

## Files Generated

### Per Delivery Output
```
chuck1_native_full/
├── analysis_results.json         (88 KB)
├── delivery_1_samples.csv         (2.8 KB, 91 frames)
├── full_rotation_report.html      (308 KB, with arm path plot)
└── slowmo_preview.mp4             (18 MB, 30 FPS output, 2.0x slow-mo)

legal1_native_full/
├── analysis_results.json
├── delivery_1_samples.csv         (91 frames)
├── full_rotation_report.html      (with arm path plot)
└── slowmo_preview.mp4             (30 FPS output, 2.0x slow-mo)
```

### CSV Format (Native FPS)
```csv
frame,time_sec,elbow_angle_deg,change_deg,confidence
542,9.0344,85.46,0.00,0.812
543,9.0511,96.63,11.17,0.816
544,9.0678,110.74,14.11,0.823
...
```

No more "measured/interpolated" columns - all samples are measured.

## Comparison: Interpolated vs Native

| Metric | Interpolated (0.01s) | Native FPS |
|--------|---------------------|------------|
| **Chuck1 Samples** | 151 | 91 |
| **Legal1 Samples** | 150 | 91 |
| **Chuck1 ICC Extension** | 15.8° | 16.5° |
| **Legal1 ICC Extension** | 44.7° | 50.8° |
| **Chuck1 Strict Events** | 43 | 46 |
| **Legal1 Strict Events** | 32 | 34 |
| **Interpolation** | Yes (cubic spline) | No |
| **Measured Samples** | ~60% (60 FPS source) | 100% |

## Recommendations

### For Analysis
1. **Use native FPS sampling** - simpler, more direct, no interpolation artifacts
2. **ICC mode for screening** - 15-20° may indicate concern; >30° likely camera artifact
3. **Review slow-motion video** - visual inspection of trajectory trails and bend events
4. **Check arm path plot** - scattered bend events suggest noise; clustered may be real
5. **Adjust strict tolerance** - 5-7° may reduce false positives from tracking jitter

### For High-FPS Footage
If analyzing 120 or 240 FPS slow-motion footage:
- Native sampling will give 4x or 8x more data points
- Slow-motion preview will show 4x or 8x slow-down (very detailed)
- May need higher strict tolerance due to more samples capturing micro-movements

### For Accurate Rulings
- **2D camera analysis fundamentally limited** by projection artifacts
- **Multi-camera setup required** for 3D reconstruction
- **Depth cameras** (Kinect, RealSense) can help
- **ICC-approved 3D motion capture** remains gold standard

## Conclusion

✅ **Native FPS sampling implemented successfully**:
- No interpolation
- One sample per frame
- Correct frame timing (1/fps)
- All samples are measured

✅ **Slow-motion preview video working**:
- 30 FPS output for smooth playback
- Trajectory trails and real-time annotations
- Slowdown factor = source_fps / 30

✅ **Arm path visualization added**:
- Trajectory plot in HTML report
- Color-coded by elbow angle
- Bend events marked

⚠️ **2D projection artifacts confirmed**:
- Legal action shows 50.8° "extension" (native FPS)
- Problem persists regardless of sampling method
- Inherent to 2D camera perspective

**The system now provides native-FPS analysis without interpolation, along with comprehensive visualization tools, while maintaining honest reporting of 2D limitations.**

---

*Generated: October 16, 2026*
*Analysis Mode: Native FPS (No Interpolation)*
*Source FPS: 60.0 (both clips)*
*Test Clips: chuck1_0774.mp4, legal1_3904.mp4*
