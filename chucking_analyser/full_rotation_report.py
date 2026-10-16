"""
Enhanced HTML report generator for full rotation analysis.
"""

import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List
import os


class FullRotationHTMLReport:
    """Generate comprehensive HTML reports for full rotation analysis."""
    
    def generate_report(self, result: Dict, video_path: str, output_path: str):
        """Generate full rotation HTML report."""
        
        analysis = result['full_rotation_analysis']
        samples = analysis['high_res_samples']
        
        # Generate charts
        angle_vs_time_chart = self._create_angle_vs_time_chart(samples, analysis)
        sample_dist_chart = self._create_sample_distribution_chart(samples)
        
        # Build HTML
        html = self._build_html(
            result, analysis, samples,
            angle_vs_time_chart, sample_dist_chart,
            video_path
        )
        
        with open(output_path, 'w') as f:
            f.write(html)
    
    def _create_angle_vs_time_chart(self, samples, analysis):
        """Create elbow angle vs time chart with bend events."""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        times = [s['time'] for s in samples]
        angles = [s['angle'] for s in samples]
        
        # Plot angle trace
        ax.plot(times, angles, 'b-', linewidth=1.5, label='Elbow Angle')
        
        # Highlight bend events from strict analysis
        strict_events = analysis['strict_analysis']['bend_events']
        if strict_events:
            event_times = [e['time'] for e in strict_events]
            event_angles = [e['angle_after'] for e in strict_events]
            event_colors = ['red' if e['type'] == 'extension' else 'orange' 
                           for e in strict_events]
            
            for t, a, c in zip(event_times, event_angles, event_colors):
                ax.scatter(t, a, c=c, s=50, alpha=0.6, zorder=5)
        
        # Mark ICC window if available
        if analysis['icc_analysis']:
            icc = analysis['icc_analysis']
            ax.axvspan(icc['window_start'], icc['window_end'], 
                      alpha=0.1, color='green', label='ICC Window (H→R)')
        
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Elbow Angle (degrees)', fontsize=12)
        ax.set_title('Elbow Angle Throughout Full Arm Rotation', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')
        
        # Convert to base64
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode()
        plt.close()
        
        return img_base64
    
    def _create_sample_distribution_chart(self, samples):
        """Create histogram of angle changes."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Histogram of changes
        changes = [abs(s.get('change', 0)) for s in samples if s.get('change') is not None]
        ax1.hist(changes, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
        ax1.set_xlabel('Absolute Change per 0.01s (degrees)', fontsize=11)
        ax1.set_ylabel('Count', fontsize=11)
        ax1.set_title('Distribution of Angle Changes', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.axvline(x=3.0, color='red', linestyle='--', linewidth=2, 
                   label='Default Strict Tolerance (3°)')
        ax1.legend()
        
        # Box plot of angles
        angles = [s['angle'] for s in samples]
        ax2.boxplot([angles], vert=True, patch_artist=True,
                   boxprops=dict(facecolor='lightblue'),
                   medianprops=dict(color='red', linewidth=2))
        ax2.set_ylabel('Elbow Angle (degrees)', fontsize=11)
        ax2.set_title('Angle Distribution', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.set_xticklabels(['Full Rotation'])
        
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode()
        plt.close()
        
        return img_base64
    
    def _build_html(self, result, analysis, samples, chart1, chart2, video_path):
        """Build complete HTML document."""
        
        video_name = os.path.basename(video_path)
        strict = analysis['strict_analysis']
        icc = analysis['icc_analysis']
        
        # Verdict colors
        strict_color = '#d32f2f' if strict['verdict'] == 'possible concern' else '#388e3c'
        icc_color = '#d32f2f' if icc and icc['verdict'] == 'possible concern' else '#388e3c'
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Full Rotation Analysis - {video_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.2em;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .disclaimer {{
            background: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 15px;
            margin: 20px;
            border-radius: 5px;
        }}
        .disclaimer strong {{
            color: #856404;
        }}
        .content {{
            padding: 30px;
        }}
        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .metadata-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .metadata-item .label {{
            font-size: 0.85em;
            color: #666;
            margin-bottom: 5px;
        }}
        .metadata-item .value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #1e3c72;
        }}
        .verdicts {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .verdict-card {{
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .verdict-card h2 {{
            margin-bottom: 15px;
            font-size: 1.5em;
        }}
        .verdict-card .verdict {{
            font-size: 1.8em;
            font-weight: bold;
            margin: 15px 0;
            text-transform: uppercase;
        }}
        .verdict-card .detail {{
            margin: 8px 0;
            font-size: 1em;
        }}
        .verdict-card .detail strong {{
            display: inline-block;
            min-width: 100px;
        }}
        .strict-card {{
            background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%);
            border-left: 5px solid #fdcb6e;
        }}
        .icc-card {{
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            border-left: 5px solid #0984e3;
            color: white;
        }}
        .chart-section {{
            margin: 30px 0;
        }}
        .chart-section h2 {{
            color: #1e3c72;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .chart-section img {{
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .collapsible {{
            background-color: #667eea;
            color: white;
            cursor: pointer;
            padding: 18px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 1.2em;
            font-weight: bold;
            border-radius: 8px;
            margin-top: 20px;
            transition: 0.3s;
        }}
        .collapsible:hover {{
            background-color: #5568d3;
        }}
        .collapsible.active {{
            background-color: #5568d3;
        }}
        .collapsible:after {{
            content: '\\002B';
            color: white;
            font-weight: bold;
            float: right;
            margin-left: 5px;
        }}
        .collapsible.active:after {{
            content: "\\2212";
        }}
        .collapsible-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background-color: #f8f9fa;
            border-radius: 0 0 8px 8px;
        }}
        .table-wrapper {{
            max-height: 500px;
            overflow: auto;
            padding: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        th {{
            background: #1e3c72;
            color: white;
            padding: 12px;
            text-align: left;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f1f3f5;
        }}
        .measured {{
            color: #388e3c;
            font-weight: bold;
        }}
        .interpolated {{
            color: #f57c00;
        }}
        .download-link {{
            display: inline-block;
            margin: 20px 0;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            transition: 0.3s;
        }}
        .download-link:hover {{
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏏 Full Arm Rotation Analysis</h1>
            <div class="subtitle">High-Resolution Elbow Angle Tracking (100 Hz Sampling)</div>
            <div class="subtitle" style="margin-top: 10px; font-size: 0.95em;">{video_name}</div>
        </div>
        
        <div class="disclaimer">
            <strong>⚠️ IMPORTANT DISCLAIMER:</strong> This is a 2D camera-based analysis and is NOT an official ruling. 
            ICC regulations require calibrated 3D motion capture. 2D projections can create artificial angle changes due to 
            camera perspective, especially when the arm rotates toward or away from the camera. Results should be treated 
            as preliminary screening only.
        </div>
        
        <div class="content">
            <h2 style="color: #1e3c72; margin-bottom: 20px;">📊 Analysis Metadata</h2>
            <div class="metadata">
                <div class="metadata-item">
                    <div class="label">Native FPS</div>
                    <div class="value">{result['native_fps']:.1f}</div>
                </div>
                <div class="metadata-item">
                    <div class="label">Sampling Interval</div>
                    <div class="value">{result['sampling_interval']:.3f} s</div>
                </div>
                <div class="metadata-item">
                    <div class="label">Total Samples</div>
                    <div class="value">{result['num_samples']}</div>
                </div>
                <div class="metadata-item">
                    <div class="label">Calculated Noise</div>
                    <div class="value">{result['calculated_noise_tolerance']:.1f}°</div>
                </div>
                <div class="metadata-item">
                    <div class="label">Horizontal Frame</div>
                    <div class="value">{result['horizontal_frame'] if result['horizontal_frame'] else 'N/A'}</div>
                </div>
                <div class="metadata-item">
                    <div class="label">Release Frame</div>
                    <div class="value">{result['release_frame'] if result['release_frame'] else 'N/A'}</div>
                </div>
            </div>
            
            <h2 style="color: #1e3c72; margin-bottom: 20px;">🎯 Analysis Verdicts</h2>
            <div class="verdicts">
                <div class="verdict-card strict-card">
                    <h2>🔬 STRICT MODE</h2>
                    <p style="margin-bottom: 10px; font-size: 0.95em;">
                        No-bend rule: Arm should not bend during rotation beyond measurement noise.
                    </p>
                    <div class="verdict" style="color: {strict_color};">
                        {strict['verdict'].upper()}
                    </div>
                    <div class="detail"><strong>Tolerance:</strong> {result['strict_tolerance']:.1f}°</div>
                    <div class="detail"><strong>Bend Events:</strong> {strict['num_events']}</div>
                    {self._format_max_event(strict['bend_events'])}
                    <div class="detail" style="margin-top: 15px; font-style: italic;">
                        {strict['reason']}
                    </div>
                </div>
                
                <div class="verdict-card icc-card">
                    <h2>📏 ICC MODE</h2>
                    <p style="margin-bottom: 10px; font-size: 0.95em;">
                        ICC Rule: Max 15° extension from horizontal to release.
                    </p>
                    <div class="verdict" style="color: {'#fff' if icc and icc['verdict'] == 'likely within threshold' else '#ffeb3b'};">
                        {icc['verdict'].upper() if icc else 'N/A'}
                    </div>
                    <div class="detail"><strong>Tolerance:</strong> {result['icc_tolerance']:.1f}°</div>
                    <div class="detail"><strong>Measured:</strong> {result['icc_extension']:.1f}°</div>
                    <div class="detail" style="margin-top: 15px; font-style: italic;">
                        {icc['reason'] if icc else 'ICC window not detected'}
                    </div>
                </div>
            </div>
            
            <div class="chart-section">
                <h2>📈 Elbow Angle vs Time</h2>
                <img src="data:image/png;base64,{chart1}" alt="Angle vs Time Chart">
                <p style="margin-top: 10px; color: #666; font-size: 0.9em;">
                    Red dots = extension events, Orange dots = flexion events. 
                    Green shaded region = ICC window (horizontal to release).
                </p>
            </div>
            
            <div class="chart-section">
                <h2>📊 Sample Statistics</h2>
                <img src="data:image/png;base64,{chart2}" alt="Distribution Charts">
            </div>
            
            {self._build_bend_events_table(strict['bend_events'], 'strict')}
            
            {self._build_bend_events_table(icc['bend_events'], 'icc') if icc else ''}
            
            <button class="collapsible">
                📋 Full Sample Table ({len(samples)} samples @ 0.01s intervals)
            </button>
            <div class="collapsible-content">
                <div class="table-wrapper">
                    {self._build_samples_table(samples)}
                </div>
            </div>
            
            <a href="delivery_{result['delivery_number']}_samples.csv" class="download-link" download>
                📥 Download Full Samples CSV
            </a>
        </div>
        
        <div class="footer">
            Generated by Cricket Bowling Action Analyser (Full Rotation Mode) • 
            2D Camera-Based Screening Tool • 
            Not for Official Rulings
        </div>
    </div>
    
    <script>
        var coll = document.getElementsByClassName("collapsible");
        for (var i = 0; i < coll.length; i++) {{
            coll[i].addEventListener("click", function() {{
                this.classList.toggle("active");
                var content = this.nextElementSibling;
                if (content.style.maxHeight) {{
                    content.style.maxHeight = null;
                }} else {{
                    content.style.maxHeight = content.scrollHeight + "px";
                }}
            }});
        }}
    </script>
</body>
</html>"""
        
        return html
    
    def _format_max_event(self, events):
        """Format maximum bend event."""
        if not events:
            return '<div class="detail"><strong>Max Event:</strong> None</div>'
        
        max_event = max(events, key=lambda e: e['magnitude'])
        return f'''<div class="detail"><strong>Max Event:</strong> {max_event['magnitude']:.1f}° 
                  ({max_event['type']}) at {max_event['time']:.2f}s</div>'''
    
    def _build_bend_events_table(self, events, mode):
        """Build bend events table."""
        if not events:
            return ''
        
        mode_label = 'Strict Mode' if mode == 'strict' else 'ICC Mode'
        rows = []
        for i, event in enumerate(events[:50], 1):  # Limit to first 50
            rows.append(f'''
                <tr>
                    <td>{i}</td>
                    <td>{event['time']:.3f}s</td>
                    <td>{event['frame']}</td>
                    <td>{event['type'].title()}</td>
                    <td>{event['magnitude']:.2f}°</td>
                    <td>{event['angle_before']:.2f}°</td>
                    <td>{event['angle_after']:.2f}°</td>
                    <td>{event.get('phase', 'N/A')}</td>
                </tr>
            ''')
        
        table = f'''
            <button class="collapsible">
                📍 Bend Events - {mode_label} ({len(events)} events{' - showing first 50' if len(events) > 50 else ''})
            </button>
            <div class="collapsible-content">
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Time</th>
                                <th>Frame</th>
                                <th>Type</th>
                                <th>Magnitude</th>
                                <th>Before</th>
                                <th>After</th>
                                <th>Phase</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        '''
        return table
    
    def _build_samples_table(self, samples):
        """Build full samples table."""
        rows = []
        for i, sample in enumerate(samples, 1):
            status_class = 'measured' if sample['measured'] else 'interpolated'
            status_text = '✓ Measured' if sample['measured'] else '◐ Interpolated'
            
            rows.append(f'''
                <tr>
                    <td>{i}</td>
                    <td>{sample['time']:.3f}</td>
                    <td>{sample['frame']}</td>
                    <td>{sample['angle']:.2f}°</td>
                    <td>{sample.get('change', 0):.2f}°</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{sample['confidence']:.3f}</td>
                </tr>
            ''')
        
        return f'''
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Time (s)</th>
                        <th>Frame</th>
                        <th>Elbow Angle</th>
                        <th>Change</th>
                        <th>Status</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        '''
