#!/usr/bin/env python3
"""
Complete Example: Extract, Process, and Analyze Float64MultiArray Debug Data

This script shows the full workflow:
1. Extract bag file with ROS2 Data Analyzer
2. Create field mapping
3. Post-process CSV
4. Generate analysis plots
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json

# ══════════════════════════════════════════════════════════════════
# STEP 1: CREATE MAPPING FILE
# ══════════════════════════════════════════════════════════════════

def create_padih_mapping(output_file='padih_debug_mapping.json'):
    """Create a mapping file for PADIH controller debug topic."""
    
    # Based on the message structure analysis
    mapping = {
        "description": "Field mapping for PADIH controller debug topic",
        "message_type": "std_msgs/Float64MultiArray",
        "total_fields": 48,
        "field_mapping": {
            "0": "timestamp",
            "1": "Linear x velocity command",
            "2": "Linear y velocity command",
            "3": "Angular z velocity command  ",
            "4": "Left wheel velocity command (output of the controller)",
            "5": "Right wheel velocity command (output of the controller)",
            "6": "Caster fork velocity command (output of the controller)",
            "7": "Caster wheel velocity command (output of the controller)",
            "8": "Left wheel velocity command (without limit)",
            "9": "Right wheel velocity command (without limit)",
            "10": "Caster fork position command (without limit)",
            "11": "Caster wheel velocity command (without limit)",
            "12": "Current linear x command (should be teh same as Linear x command)",
            "13": "Current linear y command (should be teh same as Linear y command)",
            "14": "Current Angular z command (should be teh same as Angular z command)",
            "15": "Time difference between loops inside the controller. (Used to limit the ammount of commands per second)",
            "16": "Odometry X position estimation",
            "17": "Odometry linear x velocity estimation",
            "18": "Odometry linear x acceleration etsimation",
            "19": "Odometry X position estimation",
            "20": "Odometry linear y velocity estimation",
            "21": "Odometry linear y acceleration etsimation",
            "22": "Left wheel position in radians",
            "23": "Right wheel position in radians",
            "24": "Caster Fork position in radians",
            "25": "Caster wheel position in radians",
            "26": "Left wheel velocity in radians/s",
            "27": "Right wheel velocity in radians/s",
            "28": "Right wheel velocity in radians/s",
            "29": "Caster Fork velocity in radians/s",
            "30": "Caster wheel velocity in radians/s",
            "31": "Base heading in radians",
            "32": "Base angular velocity in rad/s",
            "33": "Left wheel position readings",
            "34": "Right wheel position readings",
            "35": "Caster fork position readings",
            "36": "Caster wheel position readings",
            "37": "Left wheel velocity readings",
            "38": "Right wheel velocity readings",
            "39": "Caster fork velocity readings",
            "40": "Caster wheel velocity readings",
            "41": "max_right_wheel_motor_speed_",
            "42": "max_left_wheel_motor_speed_",
            "43": "max_caster_fork_motor_pos_",
            "44": "max_caster_wheel_motor_speed_",
            "45": "min_right_wheel_motor_speed_",
            "46": "min_left_wheel_motor_speed_",
            "47": "min_caster_fork_motor_pos_",
            "48": "min_caster_wheel_motor_speed_",
        },
        "notes": [
            "Edit field names to match your actual controller output",
            "Index 0 is always timestamp",
            "Verify against your controller code for accuracy"
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"✓ Mapping file created: {output_file}")
    return mapping


# ══════════════════════════════════════════════════════════════════
# STEP 2: LOAD AND PROCESS CSV
# ══════════════════════════════════════════════════════════════════

def load_and_rename_csv(csv_path: str, mapping_file: str) -> pd.DataFrame:
    """Load CSV from bag extraction and rename columns using mapping."""
    
    print(f"\nLoading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Load mapping
    print(f"Loading mapping from {mapping_file}...")
    with open(mapping_file, 'r') as f:
        mapping = json.load(f)
    
    field_mapping = {int(k): v for k, v in mapping['field_mapping'].items()}
    
    # Rename columns
    rename_dict = {}
    for col in df.columns:
        if col.startswith('data_'):
            try:
                idx = int(col.split('_')[1])
                if idx in field_mapping:
                    rename_dict[col] = field_mapping[idx]
            except:
                pass
    
    df = df.rename(columns=rename_dict)
    print(f"✓ Renamed {len(rename_dict)} columns")
    
    return df


def save_processed_csv(df: pd.DataFrame, output_path: str):
    """Save processed dataframe to CSV."""
    df.to_csv(output_path, index=False)
    print(f"✓ Saved to {output_path}")


# ══════════════════════════════════════════════════════════════════
# STEP 3: ANALYSIS & VISUALIZATION
# ══════════════════════════════════════════════════════════════════

def plot_speed_control(df: pd.DataFrame, output_file='speed_control.png'):
    """Plot speed reference vs actual performance."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
    
    # Speed tracking
    ax1.plot(df['timestamp'], df['reference_speed'], 'k-', linewidth=2.5, 
             label='Reference', zorder=3)
    ax1.plot(df['timestamp'], df['actual_speed_left'], 'b-', alpha=0.7, 
             label='Left wheel', linewidth=1.5)
    ax1.plot(df['timestamp'], df['actual_speed_right'], 'r-', alpha=0.7, 
             label='Right wheel', linewidth=1.5)
    ax1.set_ylabel('Speed (rad/s)', fontsize=12, fontweight='bold')
    ax1.set_title('Speed Control Tracking Performance', fontsize=13, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Control errors
    ax2.plot(df['timestamp'], df['speed_error_left'], 'b-', alpha=0.7, 
             label='Left error', linewidth=1.5)
    ax2.plot(df['timestamp'], df['speed_error_right'], 'r-', alpha=0.7, 
             label='Right error', linewidth=1.5)
    ax2.axhline(y=0, color='k', linestyle='--', alpha=0.3, linewidth=1)
    ax2.set_ylabel('Error (rad/s)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
    ax2.set_title('Control Error Analysis', fontsize=13, fontweight='bold')
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Saved plot to {output_file}")
    plt.close()


def plot_motor_comparison(df: pd.DataFrame, output_file='motor_comparison.png'):
    """Compare left vs right motor performance."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Position
    axes[0, 0].plot(df['timestamp'], df['motor_left_position'], label='Left', alpha=0.7)
    axes[0, 0].plot(df['timestamp'], df['motor_right_position'], label='Right', alpha=0.7)
    axes[0, 0].set_ylabel('Position (rad)', fontweight='bold')
    axes[0, 0].set_title('Motor Position', fontweight='bold')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Velocity
    axes[0, 1].plot(df['timestamp'], df['motor_left_velocity'], label='Left', alpha=0.7)
    axes[0, 1].plot(df['timestamp'], df['motor_right_velocity'], label='Right', alpha=0.7)
    axes[0, 1].set_ylabel('Velocity (rad/s)', fontweight='bold')
    axes[0, 1].set_title('Motor Velocity', fontweight='bold')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Effort
    axes[1, 0].plot(df['timestamp'], df['motor_left_effort'], label='Left', alpha=0.7)
    axes[1, 0].plot(df['timestamp'], df['motor_right_effort'], label='Right', alpha=0.7)
    axes[1, 0].set_ylabel('Effort (Nm)', fontweight='bold')
    axes[1, 0].set_title('Motor Effort', fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Power
    axes[1, 1].plot(df['timestamp'], df['motor_left_power'], label='Left', alpha=0.7)
    axes[1, 1].plot(df['timestamp'], df['motor_right_power'], label='Right', alpha=0.7)
    axes[1, 1].set_ylabel('Power (W)', fontweight='bold')
    axes[1, 1].set_xlabel('Time (s)', fontweight='bold')
    axes[1, 1].set_title('Motor Power', fontweight='bold')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.suptitle('Left vs Right Motor Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Saved plot to {output_file}")
    plt.close()


def plot_diagnostics(df: pd.DataFrame, output_file='diagnostics.png'):
    """Plot system diagnostics."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Temperature
    axes[0, 0].plot(df['timestamp'], df['motor_left_temperature'], label='Motor', alpha=0.7)
    axes[0, 0].plot(df['timestamp'], df['controller_temperature'], label='Controller', alpha=0.7)
    axes[0, 0].set_ylabel('Temperature (°C)', fontweight='bold')
    axes[0, 0].set_title('System Temperature', fontweight='bold')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Battery
    axes[0, 1].plot(df['timestamp'], df['battery_voltage'], label='Voltage', alpha=0.7)
    ax_curr = axes[0, 1].twinx()
    ax_curr.plot(df['timestamp'], df['battery_current'], 'r-', label='Current', alpha=0.7)
    axes[0, 1].set_ylabel('Voltage (V)', fontweight='bold')
    ax_curr.set_ylabel('Current (A)', fontweight='bold', color='r')
    axes[0, 1].set_title('Battery Status', fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Current (motor)
    axes[1, 0].plot(df['timestamp'], df['current_actual_left'], label='Actual', alpha=0.7)
    axes[1, 0].axhline(y=df['current_limit_left'].iloc[0], color='r', 
                       linestyle='--', label='Limit', linewidth=2)
    axes[1, 0].set_ylabel('Current (A)', fontweight='bold')
    axes[1, 0].set_title('Motor Current (Left)', fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Load
    axes[1, 1].plot(df['timestamp'], df['load_percentage'], alpha=0.7, linewidth=2)
    axes[1, 1].fill_between(df['timestamp'], 0, df['load_percentage'], alpha=0.3)
    axes[1, 1].set_ylabel('Load (%)', fontweight='bold')
    axes[1, 1].set_xlabel('Time (s)', fontweight='bold')
    axes[1, 1].set_title('CPU Load', fontweight='bold')
    axes[1, 1].set_ylim([0, 100])
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.suptitle('System Diagnostics', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Saved plot to {output_file}")
    plt.close()


def generate_summary_stats(df: pd.DataFrame, output_file='summary_stats.txt'):
    """Generate statistical summary."""
    with open(output_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("DEBUG DATA SUMMARY STATISTICS\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Recording Duration: {df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]:.2f} seconds\n")
        f.write(f"Number of Samples: {len(df)}\n")
        f.write(f"Sample Rate: {len(df) / (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]):.1f} Hz\n\n")
        
        f.write("Speed Control:\n")
        f.write(f"  Reference speed: {df['reference_speed'].mean():.3f} ± {df['reference_speed'].std():.3f} rad/s\n")
        f.write(f"  Left speed error: {abs(df['speed_error_left']).mean():.3f} ± {df['speed_error_left'].std():.3f} rad/s\n")
        f.write(f"  Right speed error: {abs(df['speed_error_right']).mean():.3f} ± {df['speed_error_right'].std():.3f} rad/s\n\n")
        
        f.write("Motor Statistics:\n")
        f.write(f"  Left position range: {df['motor_left_position'].min():.2f} to {df['motor_left_position'].max():.2f} rad\n")
        f.write(f"  Left max velocity: {df['motor_left_velocity'].abs().max():.3f} rad/s\n")
        f.write(f"  Left avg effort: {df['motor_left_effort'].mean():.3f} Nm\n")
        f.write(f"  Left max power: {df['motor_left_power'].max():.1f} W\n\n")
        
        f.write("System Health:\n")
        f.write(f"  Avg battery voltage: {df['battery_voltage'].mean():.2f} V\n")
        f.write(f"  Peak current: {df['battery_current'].abs().max():.1f} A\n")
        f.write(f"  Max temperature (motor): {df['motor_left_temperature'].max():.1f} °C\n")
        f.write(f"  Max temperature (controller): {df['controller_temperature'].max():.1f} °C\n")
        f.write(f"  Max CPU load: {df['load_percentage'].max():.1f} %\n")
    
    print(f"✓ Summary stats saved to {output_file}")


# ══════════════════════════════════════════════════════════════════
# MAIN WORKFLOW
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    print("=" * 70)
    print("Float64MultiArray Debug Data Processing Pipeline")
    print("=" * 70)
    
    # Step 1: Create mapping
    print("\n[1/5] Creating field mapping...")
    mapping = create_padih_mapping('padih_debug_mapping.json')
    
    # Step 2: Load and process CSV
    # (User runs ROS2 Data Analyzer first to generate CSV)
    csv_file = 'debug_topic.csv'
    if not Path(csv_file).exists():
        print(f"\n[!] CSV file not found: {csv_file}")
        print("    First, run ROS2 Data Analyzer:")
        print("      1. Tab 2: Load your .db3 bag")
        print("      2. Detect topics")
        print("      3. Export /padih_controller/debug_topic to CSV")
        print("      4. Save as: debug_topic.csv")
        sys.exit(1)
    
    print(f"\n[2/5] Loading and processing CSV...")
    df = load_and_rename_csv(csv_file, 'padih_debug_mapping.json')
    
    print(f"\n[3/5] Saving processed CSV...")
    save_processed_csv(df, 'debug_topic_processed.csv')
    
    print(f"\n[4/5] Generating plots...")
    plot_speed_control(df)
    plot_motor_comparison(df)
    plot_diagnostics(df)
    
    print(f"\n[5/5] Generating summary statistics...")
    generate_summary_stats(df)
    
    print("\n" + "=" * 70)
    print("✓ COMPLETE!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  • debug_topic_processed.csv - Processed data with named columns")
    print("  • speed_control.png - Speed tracking and error analysis")
    print("  • motor_comparison.png - Left vs right motor performance")
    print("  • diagnostics.png - System health diagnostics")
    print("  • summary_stats.txt - Statistical summary")
    print("=" * 70)
