"""
Generate self-contained HTML reports with charts and analysis.
"""

import os
import base64
import json
from typing import List, Dict
import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO


class HTMLReportGenerator:
    """Generates comprehensive HTML reports."""
    
    def generate_report(self, video_path: str, delivery_result: Dict,
                       landmarks_list: List[Dict], all_angles: List,
                       bowling_arm: str, output_path: str):
        """
        Generate self-contained HTML report.
        
        Args:
            video_path: Path to input video
            delivery_result: Delivery analysis result
            landmarks_list: All landmark data
            all_angles: Pre-calculated angles
            bowling_arm: Bowling arm
            output_path: Output HTML file path
        """
        html_content = self._build_html(
            video_path, delivery_result, landmarks_list,
            all_angles, bowling_arm
        )
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def _build_html(self, video_path, delivery_result, landmarks_list, all_angles, bowling_arm):
        """Build complete HTML document."""
        
        # Generate embedded chart
        chart_base64 = self._generate_angle_chart(
            all_angles, delivery_result, landmarks_list
        )
        
        # Extract key frames
        key_frames = self._extract_key_frames(
            video_path, delivery_result, landmarks_list, bowling_arm
        )
        
        # Build bend events table
        bend_events_html = self._build_bend_events_table(
            all_angles, delivery_result
        )
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bowling Action Analysis Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .disclaimer {{
            background: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin: 20px 0;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .verdict {{
            font-size: 1.8em;
            font-weight: bold;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }}
        .verdict.concern {{
            background: #fff3cd;
            color: #856404;
            border: 3px solid #ffc107;
        }}
        .verdict.within {{
            background: #d4edda;
            color: #155724;
            border: 3px solid #28a745;
        }}
        .verdict.unable {{
            background: #e2e3e5;
            color: #383d41;
            border: 3px solid #6c757d;
        }}
        .metric {{
            display: inline-block;
            margin: 15px 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            min-width: 150px;
        }}
        .metric-label {{
            font-size: 0.9em;
            color: #6c757d;
            text-transform: uppercase;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .key-frames {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .key-frame {{
            text-align: center;
        }}
        .key-frame img {{
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .key-frame-label {{
            margin-top: 10px;
            font-weight: 600;
            color: #333;
        }}
        .experimental-notice {{
            background: #d1ecf1;
            border-left: 5px solid #0c5460;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .pattern-evidence {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        .chart-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏏 Bowling Action Analysis Report</h1>
        <p>Cricket Chucking Detection using Computer Vision</p>
    </div>
    
    <div class="disclaimer">
        <strong>⚠️ Important Disclaimer:</strong> This analysis provides 2D camera-based estimates only and is <strong>NOT an official ICC ruling</strong>. 
        Formal assessment requires calibrated 3D motion capture. Use for preliminary screening only.
    </div>
    
    {self._build_verdict_section(delivery_result)}
    
    {self._build_metrics_section(delivery_result)}
    
    <div class="experimental-notice">
        <strong>🧪 Experimental Heuristic:</strong> The sudden-versus-smooth pattern detection is an experimental approach validated on only two reference clips. 
        It attempts to distinguish sudden elbow straightening (chucking) from smooth whole-arm rotation (legal), but cannot perfectly separate these effects with a single 2D camera.
        Results should be interpreted with caution and verified with proper biomechanical analysis.
    </div>
    
    {self._build_pattern_evidence_section(delivery_result, all_angles)}
    
    <div class="section">
        <h2>📊 Elbow Angle Over Time</h2>
        <div class="chart-container">
            <img src="data:image/png;base64,{chart_base64}" alt="Angle Chart">
        </div>
        <p><em>Chart shows elbow angle throughout delivery. Green line = horizontal frame, Red line = release frame, 
        Yellow band = 15° threshold for extension measurement.</em></p>
    </div>
    
    <div class="section">
        <h2>📸 Key Frame Snapshots</h2>
        <div class="key-frames">
            {self._build_key_frames_html(key_frames)}
        </div>
    </div>
    
    <div class="section">
        <h2>📋 Bend/Extension Events</h2>
        {bend_events_html}
    </div>
    
    {self._build_quality_notes_section(delivery_result)}
    
    <div class="section">
        <h2>📄 Raw Data</h2>
        <details>
            <summary><strong>Click to view complete analysis data (JSON)</strong></summary>
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 0.85em;">
{json.dumps(delivery_result, indent=2)}
            </pre>
        </details>
    </div>
    
    <div class="section" style="background: #f8f9fa; border-top: 3px solid #667eea;">
        <p style="text-align: center; color: #6c757d; margin: 0;">
            <strong>Generated by Cricket Bowling Action Analyser</strong><br>
            Analysis Date: {self._get_timestamp()}<br>
            Source Video: {os.path.basename(video_path)}
        </p>
    </div>
</body>
</html>"""
        
        return html
    
    def _build_verdict_section(self, delivery_result):
        """Build verdict section."""
        result = delivery_result.get('result', 'unknown')
        reason = delivery_result.get('reason', '')
        
        verdict_class = 'concern' if result == 'possible concern' else 'within' if result == 'likely within threshold' else 'unable'
        
        return f"""
    <div class="verdict {verdict_class}">
        {result.upper()}
    </div>
    <div class="section">
        <h3>Reasoning:</h3>
        <p style="font-size: 1.1em;">{reason}</p>
    </div>
"""
    
    def _build_metrics_section(self, delivery_result):
        """Build metrics section."""
        extension = delivery_result.get('elbow_extension', 0)
        confidence = delivery_result.get('pose_confidence', 0)
        max_change = delivery_result.get('max_frame_change', 0)
        pattern = delivery_result.get('extension_pattern', 'unknown')
        
        return f"""
    <div class="section">
        <h2>📊 Key Metrics</h2>
        <div class="metric">
            <div class="metric-label">Extension</div>
            <div class="metric-value">{extension:.1f}°</div>
        </div>
        <div class="metric">
            <div class="metric-label">Confidence</div>
            <div class="metric-value">{confidence:.2f}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Max Frame Change</div>
            <div class="metric-value">{max_change:.1f}°</div>
        </div>
        <div class="metric">
            <div class="metric-label">Pattern</div>
            <div class="metric-value" style="font-size: 1.2em;">{pattern.replace('_', ' ').title()}</div>
        </div>
    </div>
"""
    
    def _build_pattern_evidence_section(self, delivery_result, all_angles):
        """Build pattern evidence section."""
        h_frame = delivery_result.get('horizontal_frame')
        r_frame = delivery_result.get('release_frame')
        pattern = delivery_result.get('extension_pattern', 'unknown')
        
        if h_frame is None or r_frame is None:
            return ""
        
        # Get frame-to-frame changes
        changes = []
        for i in range(h_frame, min(r_frame, len(all_angles) - 1)):
            if all_angles[i] is not None and all_angles[i+1] is not None:
                changes.append(all_angles[i+1] - all_angles[i])
        
        if not changes:
            return ""
        
        max_change = max(changes)
        max_change_idx = changes.index(max_change)
        avg_change = np.mean(changes)
        
        # Determine where max change occurred
        position = "last 3 frames" if max_change_idx >= len(changes) - 3 else \
                  "first 3 frames" if max_change_idx < 3 else \
                  "middle frames"
        
        return f"""
    <div class="section">
        <h2>🔍 Pattern Evidence</h2>
        <div class="pattern-evidence">
            <p><strong>Pattern Detected:</strong> {pattern.replace('_', ' ').title()}</p>
            <p><strong>Maximum Single-Frame Change:</strong> {max_change:.1f}° (occurred in {position})</p>
            <p><strong>Average Frame-to-Frame Change:</strong> {avg_change:.1f}°</p>
            <p><strong>Total Frames Analyzed:</strong> {len(changes)}</p>
            
            <h4>Interpretation:</h4>
            <ul>
                <li><strong>Sudden Spike Pattern:</strong> Large change (>8°) in the last 2-3 frames suggests sudden elbow straightening (potential chucking)</li>
                <li><strong>Smooth/Gradual Pattern:</strong> Large changes early with gradual progression suggests smooth arm rotation (legal)</li>
                <li><strong>Note:</strong> Single 2D camera cannot perfectly separate elbow extension from whole-arm rotation</li>
            </ul>
        </div>
    </div>
"""
    
    def _build_quality_notes_section(self, delivery_result):
        """Build quality notes section."""
        notes = delivery_result.get('quality_notes', [])
        
        if not notes:
            return """
    <div class="section">
        <h2>✅ Quality Assessment</h2>
        <p style="color: #28a745; font-weight: 600;">No quality concerns detected</p>
    </div>
"""
        
        notes_html = "".join([f"<li>{note}</li>" for note in notes])
        
        return f"""
    <div class="section">
        <h2>⚠️ Quality Notes</h2>
        <ul style="color: #856404;">
            {notes_html}
        </ul>
    </div>
"""
    
    def _generate_angle_chart(self, all_angles, delivery_result, landmarks_list):
        """Generate angle chart as base64 PNG."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Filter valid angles
        valid_indices = [i for i, a in enumerate(all_angles) if a is not None]
        valid_angles = [all_angles[i] for i in valid_indices]
        
        if not valid_angles:
            return ""
        
        # Plot angle trace
        ax.plot(valid_indices, valid_angles, 'b-', linewidth=2, label='Elbow Angle')
        
        h_frame = delivery_result.get('horizontal_frame')
        r_frame = delivery_result.get('release_frame')
        
        # Mark key frames
        if h_frame is not None:
            ax.axvline(h_frame, color='green', linestyle='--', linewidth=2, label='Horizontal (Start)')
            if h_frame < len(all_angles) and all_angles[h_frame] is not None:
                ax.plot(h_frame, all_angles[h_frame], 'go', markersize=12)
        
        if r_frame is not None:
            ax.axvline(r_frame, color='red', linestyle='--', linewidth=2, label='Release (End)')
            if r_frame < len(all_angles) and all_angles[r_frame] is not None:
                ax.plot(r_frame, all_angles[r_frame], 'ro', markersize=12)
        
        # Mark measurement window
        if h_frame is not None and r_frame is not None:
            ax.axvspan(h_frame, r_frame, alpha=0.2, color='yellow', label='Measurement Window')
            
            # Show 15° threshold band
            if h_frame < len(all_angles) and all_angles[h_frame] is not None:
                threshold_line = all_angles[h_frame] + 15
                ax.axhline(threshold_line, color='orange', linestyle=':', linewidth=2, 
                          label='15° Threshold', alpha=0.7)
        
        ax.set_xlabel('Frame Number', fontsize=12, fontweight='bold')
        ax.set_ylabel('Elbow Angle (degrees)', fontsize=12, fontweight='bold')
        ax.set_title('Elbow Angle Throughout Delivery', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Convert to base64
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close()
        
        return img_base64
    
    def _extract_key_frames(self, video_path, delivery_result, landmarks_list, bowling_arm):
        """Extract and annotate key frames."""
        from .phase_detector import PhaseDetector
        from .angle_calculator import calculate_angle_3d
        
        h_frame = delivery_result.get('horizontal_frame')
        r_frame = delivery_result.get('release_frame')
        
        key_frames = []
        
        if h_frame is None or r_frame is None:
            return key_frames
        
        # Extract frames
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return key_frames
        
        shoulder_idx, elbow_idx, wrist_idx = PhaseDetector.get_arm_landmarks(bowling_arm)
        
        for frame_idx, label in [(h_frame, 'Horizontal (Start)'), 
                                  ((h_frame + r_frame) // 2, 'Mid-Point'),
                                  (r_frame, 'Release (End)')]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret and frame_idx < len(landmarks_list):
                # Draw annotation
                frame = self._annotate_key_frame(
                    frame, landmarks_list[frame_idx],
                    shoulder_idx, elbow_idx, wrist_idx
                )
                
                # Get angle
                angle = None
                if landmarks_list[frame_idx]['landmarks']:
                    lm = landmarks_list[frame_idx]['landmarks']
                    if all(idx in lm for idx in [shoulder_idx, elbow_idx, wrist_idx]):
                        s = np.array([lm[shoulder_idx]['x'], lm[shoulder_idx]['y'], lm[shoulder_idx]['z']])
                        e = np.array([lm[elbow_idx]['x'], lm[elbow_idx]['y'], lm[elbow_idx]['z']])
                        w = np.array([lm[wrist_idx]['x'], lm[wrist_idx]['y'], lm[wrist_idx]['z']])
                        angle = calculate_angle_3d(s, e, w)
                
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', frame)
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                
                key_frames.append({
                    'label': label,
                    'frame': frame_idx,
                    'angle': f"{angle:.1f}°" if angle else "N/A",
                    'image': img_base64
                })
        
        cap.release()
        return key_frames
    
    def _annotate_key_frame(self, frame, frame_data, shoulder_idx, elbow_idx, wrist_idx):
        """Annotate a key frame with bowling arm."""
        if not frame_data['landmarks']:
            return frame
        
        h, w = frame.shape[:2]
        lm = frame_data['landmarks']
        
        if all(idx in lm for idx in [shoulder_idx, elbow_idx, wrist_idx]):
            shoulder = lm[shoulder_idx]
            elbow = lm[elbow_idx]
            wrist = lm[wrist_idx]
            
            s_pos = (int(shoulder['x'] * w), int(shoulder['y'] * h))
            e_pos = (int(elbow['x'] * w), int(elbow['y'] * h))
            w_pos = (int(wrist['x'] * w), int(wrist['y'] * h))
            
            # Draw arm
            cv2.line(frame, s_pos, e_pos, (0, 255, 0), 4)
            cv2.line(frame, e_pos, w_pos, (0, 255, 0), 4)
            
            # Draw joints
            cv2.circle(frame, s_pos, 8, (255, 255, 0), -1)
            cv2.circle(frame, e_pos, 10, (255, 0, 0), -1)
            cv2.circle(frame, w_pos, 8, (255, 255, 0), -1)
        
        return frame
    
    def _build_key_frames_html(self, key_frames):
        """Build HTML for key frames."""
        html = ""
        for kf in key_frames:
            html += f"""
            <div class="key-frame">
                <img src="data:image/jpeg;base64,{kf['image']}" alt="{kf['label']}">
                <div class="key-frame-label">{kf['label']}</div>
                <div>Frame {kf['frame']}</div>
                <div>Angle: {kf['angle']}</div>
            </div>
"""
        return html
    
    def _build_bend_events_table(self, all_angles, delivery_result):
        """Build bend events table."""
        h_frame = delivery_result.get('horizontal_frame')
        r_frame = delivery_result.get('release_frame')
        
        if h_frame is None or r_frame is None:
            return "<p>No bend events detected</p>"
        
        events = []
        for i in range(h_frame, min(r_frame, len(all_angles) - 1)):
            if all_angles[i] is not None and all_angles[i+1] is not None:
                change = all_angles[i+1] - all_angles[i]
                if abs(change) > 3.0:  # Significant change
                    events.append({
                        'frame': i+1,
                        'phase': self._get_phase_label(i+1, h_frame, r_frame),
                        'change': change,
                        'angle_before': all_angles[i],
                        'angle_after': all_angles[i+1]
                    })
        
        if not events:
            return "<p>No significant bend events detected (threshold: 3°)</p>"
        
        rows = ""
        for event in events:
            event_type = "Extension" if event['change'] > 0 else "Flexion"
            severity = "High" if abs(event['change']) > 8 else "Medium" if abs(event['change']) > 5 else "Low"
            rows += f"""
            <tr>
                <td>{event['frame']}</td>
                <td>{event['phase']}</td>
                <td>{event_type}</td>
                <td>{abs(event['change']):.1f}°</td>
                <td>{event['angle_before']:.1f}° → {event['angle_after']:.1f}°</td>
                <td>{severity}</td>
            </tr>
"""
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>Frame</th>
                    <th>Phase</th>
                    <th>Type</th>
                    <th>Change</th>
                    <th>Angles</th>
                    <th>Severity</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
"""
    
    def _get_phase_label(self, frame, h_frame, r_frame):
        """Get phase label for a frame."""
        total = r_frame - h_frame
        pos = frame - h_frame
        
        if pos < total * 0.33:
            return "Early"
        elif pos < total * 0.67:
            return "Middle"
        else:
            return "Late"
    
    def _get_timestamp(self):
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
