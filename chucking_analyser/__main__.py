"""
CLI entry point for chucking analyser.
"""

import argparse
import json
import sys
import os

from .analyser import BowlingAnalyser


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description='Analyse cricket bowling actions for illegal elbow extension (chucking)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m chucking_analyser analyse video.mp4
  python -m chucking_analyser analyse video.mp4 --output results/
  python -m chucking_analyser analyse video.mp4 --overrides overrides.json

Note: This tool provides 2D camera estimates only and is NOT an official ruling.
For accurate biomechanical analysis, ICC-approved 3D motion capture is required.
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Analyse command
    analyse_parser = subparsers.add_parser('analyse', help='Analyse bowling video')
    analyse_parser.add_argument('video', help='Path to input video file')
    analyse_parser.add_argument('--output', '-o', default='output',
                               help='Output directory (default: output)')
    analyse_parser.add_argument('--overrides', help='JSON file with manual frame overrides')
    analyse_parser.add_argument('--enhanced', action='store_true',
                               help='Generate enhanced video and HTML report with charts and alerts')
    analyse_parser.add_argument('--full-rotation', action='store_true',
                               help='Use full rotation analysis with strict no-bend rules (samples every 0.01s)')
    analyse_parser.add_argument('--strict-tolerance', type=float, default=3.0,
                               help='Noise tolerance in degrees for strict mode (default: 3.0)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'analyse':
        return analyse_command(args)
    
    return 0


def analyse_command(args):
    """Execute analyse command."""
    
    if not os.path.exists(args.video):
        print(f"ERROR: Video file not found: {args.video}", file=sys.stderr)
        return 1
    
    # Load manual overrides if provided
    manual_overrides = None
    if args.overrides:
        if not os.path.exists(args.overrides):
            print(f"ERROR: Overrides file not found: {args.overrides}", file=sys.stderr)
            return 1
        
        with open(args.overrides, 'r') as f:
            manual_overrides = json.load(f)
        print(f"Loaded manual overrides from: {args.overrides}")
    
    print(f"Analysing video: {args.video}")
    print(f"Output directory: {args.output}")
    print()
    print("=" * 70)
    print("DISCLAIMER")
    print("=" * 70)
    print("This tool provides 2D camera-based estimates and is NOT an official ruling.")
    print("ICC regulations require calibrated 3D motion capture for formal assessment.")
    print("Results should be treated as preliminary screening only.")
    print("=" * 70)
    print()
    
    analyser = BowlingAnalyser(strict_tolerance=args.strict_tolerance)
    
    try:
        results = analyser.analyse_video(
            args.video, args.output, manual_overrides, 
            enhanced_report=args.enhanced,
            full_rotation_mode=args.full_rotation
        )
        
        print("\n" + "=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)
        
        for delivery in results:
            print(f"\nDelivery {delivery['delivery_number']}:")
            
            if 'strict_verdict' in delivery:
                # Full rotation mode
                print(f"  Native FPS: {delivery['native_fps']:.1f}")
                print(f"  Samples: {delivery['num_samples']} @ 0.01s intervals")
                print(f"  Calculated noise: {delivery['calculated_noise_tolerance']:.1f}°")
                print(f"\n  STRICT MODE (no-bend rule, tolerance: {delivery['strict_tolerance']:.1f}°):")
                print(f"    Verdict: {delivery['strict_verdict']}")
                print(f"    Events: {delivery['strict_num_events']}")
                print(f"    Reason: {delivery['strict_reason']}")
                print(f"\n  ICC MODE (15° threshold, horizontal to release):")
                print(f"    Verdict: {delivery['icc_verdict']}")
                print(f"    Extension: {delivery.get('icc_extension', 0):.1f}°")
                print(f"    Reason: {delivery['icc_reason']}")
            else:
                # Pattern-based mode
                print(f"  Extension: {delivery['elbow_extension']:.1f}°")
                print(f"  Result: {delivery['result']}")
                print(f"  Confidence: {delivery['pose_confidence']:.2f}")
                if delivery.get('quality_notes'):
                    print(f"  Notes: {', '.join(delivery['quality_notes'])}")
        
        print(f"\nFull results saved to: {args.output}/")
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        analyser.close()


if __name__ == '__main__':
    sys.exit(main())
