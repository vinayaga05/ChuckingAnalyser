# Cricket Bowling Action Analyser

A Python prototype for detecting illegal elbow extension ("chucking") in cricket bowling actions using computer vision.

## ⚠️ Important Disclaimer

**This tool provides 2D camera-based estimates only and is NOT an official ruling.**

ICC regulations require calibrated 3D motion capture systems for formal biomechanical assessment of bowling actions. Results from this tool should be treated as preliminary screening only.

## Overview

This analyser uses MediaPipe Pose Landmarker to track body landmarks in bowling videos and estimate elbow extension during delivery. According to ICC regulations, elbow extension from when the bowling arm reaches horizontal until ball release must not exceed **15 degrees**.

### Features

- Automatic pose detection and landmark tracking
- Automatic bowling arm detection (left/right)
- Automatic delivery sequence detection
- Key phase detection (arm horizontal, ball release)
- 2D elbow extension estimation
- Per-delivery quality assessment
- JSON results output
- Annotated video output with skeleton overlay and analysis

## Installation

### Requirements

- Python 3.8 or higher
- pip

### Setup

```bash
# Install dependencies
pip install -r requirements.txt
```

### Dependencies

- `mediapipe>=0.10.0` - Pose detection
- `opencv-python>=4.8.0` - Video processing
- `numpy>=1.24.0` - Numerical computation
- `scipy>=1.10.0` - Signal processing and smoothing

## Usage

### Basic Analysis

```bash
python -m chucking_analyser analyse video.mp4
```

This will:
1. Process the video with MediaPipe Pose
2. Detect bowling deliveries
3. Analyse elbow extension for each delivery
4. Save results to `output/analysis_results.json`
5. Create annotated video at `output/annotated_video.mp4`

### Custom Output Directory

```bash
python -m chucking_analyser analyse video.mp4 --output my_results/
```

### Manual Frame Overrides

If automatic detection fails, you can manually specify key frames:

```bash
python -m chucking_analyser analyse video.mp4 --overrides overrides.json
```

Example `overrides.json`:
```json
{
  "0": {
    "horizontal_frame": 45,
    "release_frame": 58
  },
  "1": {
    "horizontal_frame": 120,
    "release_frame": 135
  }
}
```

The keys are delivery indices (0-based).

## Output Format

### JSON Results

The analysis produces a JSON file with:

```json
{
  "video_path": "video.mp4",
  "bowling_arm": "right",
  "video_metadata": {
    "fps": 30.0,
    "frame_count": 300,
    "width": 1920,
    "height": 1080
  },
  "deliveries": [
    {
      "delivery_number": 1,
      "start_frame": 10,
      "end_frame": 70,
      "start_timestamp": 0.333,
      "end_timestamp": 2.333,
      "bowling_arm": "right",
      "horizontal_frame": 45,
      "horizontal_timestamp": 1.5,
      "release_frame": 58,
      "release_timestamp": 1.933,
      "elbow_extension": 12.5,
      "pose_confidence": 0.87,
      "quality_notes": [],
      "result": "likely within threshold",
      "reason": "extension 12.5° <= 15.0°"
    }
  ],
  "disclaimer": "This is a 2D camera estimate only and not an official ruling."
}
```

### Result Classifications

- **likely within threshold**: Extension ≤ 15°, good confidence
- **possible concern**: Extension > 15° or near threshold, requires review
- **unable to assess**: Low confidence, occlusion, or detection failure

### Annotated Video

The output video includes:
- Full body pose skeleton overlay
- Highlighted bowling arm in green
- Delivery number indicator
- Key frame markers (ARM HORIZONTAL, BALL RELEASE)
- Real-time elbow angle display
- Extension measurement during critical phase
- Result classification

## Filming Guidance

For best results, follow these filming guidelines:

### Camera Setup

1. **Side-on view**: Camera perpendicular to bowling direction
2. **Fixed camera**: No panning or movement during delivery
3. **High frame rate**: 60+ fps recommended (minimum 30 fps)
4. **Resolution**: 1080p or higher
5. **Good lighting**: Ensure bowler is well-lit and clearly visible
6. **Unobstructed view**: Clear view of entire bowling arm throughout delivery

### Framing

- Include full body of bowler in frame
- Ensure bowling arm visible from start of run-up through follow-through
- Avoid camera angles that cause self-occlusion
- Keep bowler at consistent distance (no zooming)

### What to Avoid

- Front-on or back-on camera angles
- Moving or handheld camera
- Low frame rates (<30 fps)
- Poor lighting or shadows obscuring arm
- Obstructions between camera and bowler
- Wide shots where bowler is too small in frame

## Architecture

The codebase is modular to support future extensions:

```
chucking_analyser/
├── __init__.py           # Package initialization
├── __main__.py           # CLI entry point
├── pose_detector.py      # MediaPipe Pose integration
├── delivery_detector.py  # Bowling delivery detection
├── phase_detector.py     # Key phase detection (horizontal, release)
├── angle_calculator.py   # Angle calculation and smoothing
├── video_annotator.py    # Annotated video generation
└── analyser.py          # Main analysis orchestration

tests/
├── test_angle_calculator.py  # Angle calculation tests
└── test_phase_detector.py    # Phase detection tests
```

This modular design allows for future additions like:
- Foot placement analysis (no-ball detection)
- Front-foot landing analysis
- Follow-through analysis
- Multiple camera angles

## Testing

Run unit tests:

```bash
python -m pytest tests/
```

Or with unittest:

```bash
python -m unittest discover tests/
```

The test suite includes:
- 3D angle calculation validation
- Extension measurement verification
- Smoothing algorithm tests
- Phase detection with synthetic sequences
- Bowling arm detection tests

## Limitations

### Current Limitations

1. **2D estimation only**: Cannot account for depth/rotation relative to camera
2. **Single camera**: No multi-view triangulation
3. **No calibration**: No camera intrinsic/extrinsic calibration
4. **View dependent**: Results affected by camera angle
5. **Occlusion sensitive**: Performance degrades if arm is obscured
6. **Frame rate dependent**: Accuracy limited by video frame rate

### Known Issues

- May struggle with very fast bowlers (high angular velocity)
- Performance degrades in poor lighting
- Requires relatively clean background for best pose detection
- Cannot measure hyperextension accurately
- No ground truth validation against 3D motion capture

## Roadmap

### Near-term Improvements

1. **Expert labelling**: Collect expert-labelled training data
2. **Temporal model**: LSTM/Transformer for temporal pose refinement
3. **Video classifier**: SlowFast or similar for action classification
4. **Cross-validation**: Split train/test by bowler (not by delivery)
5. **Confidence calibration**: Better uncertainty quantification

### Medium-term Goals

1. **Multi-camera support**: Triangulation from multiple angles
2. **Camera calibration**: Intrinsic and extrinsic calibration workflow
3. **3D reconstruction**: Full 3D arm pose estimation
4. **No-ball detection**: Front-foot, height, wide ball analysis
5. **Bowler database**: Track individual bowler profiles

### Long-term Vision

1. **On-device deployment**: Mobile app for field use
2. **Real-time analysis**: Live match analysis
3. **Automated alerts**: Flagging for umpire review
4. **Biomechanical insights**: Injury risk and performance optimization
5. **Integration**: ICC-approved system integration pathway

### Research Directions

- Transfer learning from 3D motion capture data
- Physics-informed neural networks for pose constraints
- Uncertainty quantification for borderline cases
- Semi-supervised learning with limited labelled data
- Domain adaptation across different filming conditions

## Technical Details

### Pose Detection

Uses MediaPipe Pose Landmarker (model complexity 2) to extract 33 body landmarks per frame. Key landmarks for bowling analysis:

- Shoulder (11/12): Upper arm anchor point
- Elbow (13/14): Joint of interest
- Wrist (15/16): Hand position for release detection

### Smoothing

Landmark positions are smoothed using:
1. Gaussian filter (σ=2.0) for 3D positions
2. Savitzky-Golay filter (window=7, order=2) for angles

### Phase Detection

- **Horizontal**: Minimum angle between arm and horizontal line
- **Release**: Wrist deceleration following peak velocity

### Extension Measurement

Elbow angle calculated using 3D dot product:
```
angle = arccos((v1 · v2) / (|v1| |v2|))
```
where v1 = shoulder→elbow, v2 = elbow→wrist

Extension = final_angle - initial_angle (positive = straightening)

## Contributing

This is a research prototype. Contributions welcome for:

- Improved detection algorithms
- Additional test cases
- Documentation improvements
- Bug fixes
- Performance optimizations

## License

See repository license file.

## Acknowledgments

- MediaPipe team for pose detection models
- ICC for biomechanical research on legal bowling actions
- Cricket biomechanics research community

## Citation

If you use this tool in research, please acknowledge:
- The 2D limitation and preliminary nature of results
- MediaPipe Pose framework
- ICC bowling regulations (Law 21.2)

## Contact

For questions, issues, or collaboration opportunities, please open an issue on the repository.

---

## Full Rotation Analysis Mode (NEW)

### Overview

The new `--full-rotation` mode provides comprehensive elbow angle tracking throughout the entire bowling arm rotation, replacing the experimental sudden-vs-smooth heuristic with high-resolution continuous sampling.

### Features

- **100 Hz Sampling**: Continuous 0.01-second intervals throughout full arm rotation
- **Dual Evaluation Modes**:
  - **Strict Mode**: No-bend rule - arm should not bend beyond noise tolerance during rotation
  - **ICC Mode**: Standard 15° extension threshold from horizontal to release
- **CSV Export**: Full sample data at 0.01s resolution with measured/interpolated flags
- **Comprehensive Reports**: HTML reports with dual verdicts, charts, sample tables, bend events
- **Event Tracking**: Every bend/extension event with timestamp, frame, magnitude, and phase

### Usage

```bash
# Full rotation analysis with enhanced reporting
python -m chucking_analyser analyse video.mp4 --output results/ --full-rotation --enhanced

# Adjust strict mode tolerance (default: 3.0°)
python -m chucking_analyser analyse video.mp4 --output results/ --full-rotation --strict-tolerance 5.0
```

### Output Files

- `delivery_N_samples.csv` - All 0.01s samples with angles, changes, confidence
- `full_rotation_report.html` - Self-contained visual report with:
  - Dual verdict cards (Strict + ICC)
  - Elbow angle vs time chart with highlighted bend events
  - Sample distribution analysis
  - Collapsible full sample table
  - Bend event tables with detailed metadata
- `analysis_results.json` - Complete analysis data

### Understanding Results

**Strict Mode**: Detects any elbow angle change exceeding the tolerance threshold throughout the full rotation. Very sensitive to:
- Tracking noise and jitter
- 2D projection artifacts (arm rotating toward/away from camera)
- Camera perspective effects

**ICC Mode**: Measures total extension in the ICC-defined window (horizontal to release). Still affected by 2D projection.

**Important**: The test results demonstrate that 2D camera analysis creates significant artifacts. For example, a known legal delivery (legal1) shows 44.7° "extension" in ICC mode - physically impossible and clearly a 2D projection artifact.

### Interpreting Verdicts

- **Verdict: "Likely within threshold"**: No significant bend events detected above tolerance
- **Verdict: "Possible concern"**: Bend events detected; requires manual review to distinguish real bending from 2D artifacts

### Recommendations

1. **Examine the HTML report**: Visual inspection of angle traces and event distribution
2. **Review the CSV**: Check if "bend events" cluster (real) or are evenly distributed (noise/artifacts)
3. **Compare both modes**: ICC mode more forgiving; strict mode very sensitive
4. **Adjust tolerance**: For 2D analysis, strict tolerance of 5-7° may reduce false positives
5. **Use for screening only**: Cannot replace 3D motion capture for definitive assessment

See `FULL_ROTATION_ANALYSIS_RESULTS.md` for detailed test results and analysis of 2D projection effects.

---

**Remember**: This tool is for preliminary screening only. Official rulings require ICC-approved 3D motion capture analysis.
