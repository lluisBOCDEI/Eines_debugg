#!/usr/bin/env python3
"""
GUIDE: Processing Float64MultiArray Controller Debug Data

This guide shows how to work with unstructured array data from your
PADIH controller's debug topic.
"""

# ══════════════════════════════════════════════════════════════════
# THE PROBLEM
# ══════════════════════════════════════════════════════════════════

"""
Your debug topic publishes std_msgs/Float64MultiArray with ~48 values.
Without field names, the extracted CSV has columns like:

    timestamp, data_0, data_1, data_2, data_3, ...
    1776698165.19, 0.56, 0.0, -0.008, 1.71, ...

This is hard to analyze. You need to know:
  - What does data_1 represent? (reference speed? actual speed?)
  - What does data_4 mean? (position? velocity?)
  - How do values relate to each other?
"""

# ══════════════════════════════════════════════════════════════════
# SOLUTION: CREATE A MAPPING FILE
# ══════════════════════════════════════════════════════════════════

"""
Step 1: Generate a mapping file
================================

From your controller code or documentation, identify what each index means.
Create a JSON mapping file: debug_mapping.json

Example structure:
{
  "field_mapping": {
    "0": "timestamp",
    "1": "reference_speed",
    "2": "actual_speed_left",
    "3": "speed_error_left",
    "4": "left_motor_position",
    ...
  }
}

Step 2: Use the mapping to extract clean CSV
=============================================

Once you have the mapping, the CSV becomes readable:

    timestamp, reference_speed, actual_speed_left, speed_error_left, left_motor_position, ...
    1776698165.19, 0.56, 0.0, -0.008, 1.71, ...

Now you can:
  ✓ Plot reference vs actual speed
  ✓ Analyze control errors
  ✓ Compare left/right motor performance
  ✓ Find correlations between variables
"""

# ══════════════════════════════════════════════════════════════════
# STEP-BY-STEP WORKFLOW
# ══════════════════════════════════════════════════════════════════

"""
STEP 1: Identify Your Data Structure
======================================

From your message example, index analysis:

Index  | Sample Value    | Likely Meaning
-------|-----------------|------------------
0      | 1776698165.19   | Timestamp (unix seconds)
1      | 0.5604          | Reference speed (rad/s?)
2      | 0.0             | Actual speed left?
3      | -0.008          | Error left?
4-7    | 1.71, 1.68, ... | Left motor: pos, vel, effort, power?
8-11   | 1.71, 1.68, ... | Right motor: pos, vel, effort, power?
12-14  | 0, 0, 0         | IMU: roll, pitch, yaw?
15-17  | 0.10, -7.29, .. | Battery voltage, current, temp?
... and so on

ACTION: Look at your controller code (padih_controller) to confirm
        what each index represents.


STEP 2: Create Mapping File
=============================

Run:
    python3 float64_array_extractor.py template --output debug_mapping.json

This creates a template with all 48 fields as "field_0", "field_1", etc.

Then edit debug_mapping.json and replace with real names:

Before:
{
  "field_mapping": {
    "0": "field_0",
    "1": "field_1",
    ...
  }
}

After:
{
  "field_mapping": {
    "0": "timestamp",
    "1": "ref_speed",
    "2": "actual_speed_left",
    "3": "speed_error_left",
    "4": "motor_left_pos",
    "5": "motor_left_vel",
    "6": "motor_left_effort",
    "7": "motor_left_power",
    ...
  }
}


STEP 3: Extract Bag with Tool
===============================

Run the ROS2 Data Analyzer:
  python3 ros2_data_analyzer.py

  Tab 2 (Bag → CSV):
  1. Load your recording.db3 bag
  2. Detect topics
  3. Export /padih_controller/debug_topic to CSV
  4. Output: debug_topic.csv (with columns data_0, data_1, ...)


STEP 4: Post-Process CSV with Mapping
======================================

Use the float64_array_extractor.py in a Python script:

from float64_array_extractor import Float64MultiArrayExtractor
import pandas as pd

# Load the extracted CSV
df = pd.read_csv('debug_topic.csv')

# Load your mapping
mapping = Float64MultiArrayExtractor.load_mapping('debug_mapping.json')

# Rename columns according to mapping
rename_dict = {}
for old_idx in range(len(df.columns)):
    col_name = df.columns[old_idx]
    if col_name.startswith('data_'):
        idx = int(col_name.split('_')[1])
        if idx in mapping:
            rename_dict[col_name] = mapping[idx]

df = df.rename(columns=rename_dict)
df.to_csv('debug_topic_renamed.csv', index=False)

print("✓ Clean CSV with field names saved!")


STEP 5: Analyze & Visualize
============================

Now use Python to analyze:

import matplotlib.pyplot as plt

df = pd.read_csv('debug_topic_renamed.csv')

# Plot reference vs actual speed
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

ax1.plot(df['timestamp'], df['ref_speed'], label='Reference', linewidth=2)
ax1.plot(df['timestamp'], df['actual_speed_left'], label='Actual Left')
ax1.plot(df['timestamp'], df['actual_speed_right'], label='Actual Right')
ax1.set_ylabel('Speed (rad/s)')
ax1.legend()
ax1.grid(True)
ax1.set_title('Speed Control Performance')

# Plot control errors
ax2.plot(df['timestamp'], df['speed_error_left'], label='Left Error')
ax2.plot(df['timestamp'], df['speed_error_right'], label='Right Error')
ax2.set_ylabel('Error (rad/s)')
ax2.set_xlabel('Time (s)')
ax2.legend()
ax2.grid(True)
ax2.set_title('Control Errors')

plt.tight_layout()
plt.savefig('control_analysis.png', dpi=100)
plt.show()
"""

# ══════════════════════════════════════════════════════════════════
# QUICK REFERENCE: MAPPING TEMPLATE
# ══════════════════════════════════════════════════════════════════

"""
For PADIH controller (if applicable):

Index | Name                      | Description
------|---------------------------|------------------------------
0     | timestamp                 | Unix timestamp (seconds)
1     | ref_speed                 | Reference speed setpoint
2     | actual_speed_left         | Actual left wheel speed
3     | speed_error_left          | Speed error (ref - actual)
4-7   | motor_left_*              | Left motor data (pos, vel, effort, power)
8-11  | motor_right_*             | Right motor data (pos, vel, effort, power)
12-14 | imu_*                     | IMU data (roll, pitch, yaw)
15    | battery_voltage           | Battery voltage (V)
16    | battery_current           | Battery current (A)
17    | motor_left_temperature    | Left motor temperature
18    | temp_error_left           | Temperature control error
19    | current_limit_left        | Current limit left
20    | current_actual_left       | Actual current left
21    | current_error_left        | Current error left
22    | controller_temperature    | Controller board temperature
23    | load_percentage           | CPU/load percentage
24    | encoder_error_left        | Encoder reading error left
25    | encoder_position_left     | Encoder absolute position
26-28 | motor_left_pid_*          | Left motor PID gains (Kp, Ki, Kd)
29    | motor_left_integral_max   | Integral windup limit
30    | motor_right_kp            | Right motor P gain
31    | motor_right_ki            | Right motor I gain
32    | encoder_right_position    | Right encoder position
33    | encoder_right_error       | Right encoder error
34    | encoder_right_ref         | Right encoder reference
35    | encoder_right_velocity    | Right encoder velocity
36    | motor_right_kd            | Right motor D gain
37    | motor_right_integral_max  | Right integral limit
38    | motor_right_kp            | Right motor P gain (duplicate?)
39    | motor_right_ki            | Right motor I gain (duplicate?)
40    | speed_limit_max_pos       | Speed limit (positive max)
41    | speed_limit_max_neg       | Speed limit (negative max)
42    | speed_limit_accel         | Acceleration limit
43    | speed_limit_decel         | Deceleration limit
44    | speed_limit_neg_max       | Negative speed max
45    | speed_limit_neg_min       | Negative speed min
46    | speed_limit_neg_accel     | Negative acceleration
47    | speed_limit_neg_decel     | Negative deceleration

NOTE: These are guesses based on the example data pattern.
      Verify against your actual controller code!
"""

# ══════════════════════════════════════════════════════════════════
# COMMON ANALYSIS PATTERNS
# ══════════════════════════════════════════════════════════════════

"""
Pattern 1: Speed Control Performance
=====================================

# Compare reference vs actual
plt.figure(figsize=(12, 5))
plt.plot(df['timestamp'], df['ref_speed'], 'k-', linewidth=2, label='Reference')
plt.plot(df['timestamp'], df['actual_speed_left'], 'b-', alpha=0.7, label='Left')
plt.plot(df['timestamp'], df['actual_speed_right'], 'r-', alpha=0.7, label='Right')
plt.ylabel('Speed (rad/s)')
plt.xlabel('Time (s)')
plt.legend()
plt.grid(True)
plt.title('Speed Tracking Performance')
plt.tight_layout()
plt.show()


Pattern 2: Control Error Analysis
==================================

# Analyze errors over time
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

# Speed errors
axes[0].plot(df['timestamp'], df['speed_error_left'], label='Speed error left')
axes[0].plot(df['timestamp'], df['speed_error_right'], label='Speed error right')
axes[0].axhline(y=0, color='k', linestyle='--', alpha=0.3)
axes[0].set_ylabel('Error (rad/s)')
axes[0].legend()
axes[0].grid(True)
axes[0].set_title('Speed Control Errors')

# Temperature errors (if applicable)
if 'temp_error_left' in df:
    axes[1].plot(df['timestamp'], df['temp_error_left'], label='Temp error')
    axes[1].set_ylabel('Error (°C)')
    axes[1].legend()
    axes[1].grid(True)

plt.tight_layout()
plt.show()


Pattern 3: Motor Performance Comparison
========================================

# Side-by-side left vs right
fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# Position
axes[0, 0].plot(df['timestamp'], df['motor_left_pos'], label='Left')
axes[0, 0].plot(df['timestamp'], df['motor_right_pos'], label='Right')
axes[0, 0].set_ylabel('Position (rad)')
axes[0, 0].legend()
axes[0, 0].grid(True)

# Velocity
axes[0, 1].plot(df['timestamp'], df['motor_left_vel'], label='Left')
axes[0, 1].plot(df['timestamp'], df['motor_right_vel'], label='Right')
axes[0, 1].set_ylabel('Velocity (rad/s)')
axes[0, 1].legend()
axes[0, 1].grid(True)

# Effort
axes[1, 0].plot(df['timestamp'], df['motor_left_effort'], label='Left')
axes[1, 0].plot(df['timestamp'], df['motor_right_effort'], label='Right')
axes[1, 0].set_ylabel('Effort (Nm)')
axes[1, 0].legend()
axes[1, 0].grid(True)

# Power
axes[1, 1].plot(df['timestamp'], df['motor_left_power'], label='Left')
axes[1, 1].plot(df['timestamp'], df['motor_right_power'], label='Right')
axes[1, 1].set_ylabel('Power (W)')
axes[1, 1].set_xlabel('Time (s)')
axes[1, 1].legend()
axes[1, 1].grid(True)

plt.suptitle('Motor Performance Comparison', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()


Pattern 4: Diagnostic Heatmap
=============================

# Show all signals at once
import seaborn as sns

# Select numeric columns
numeric_cols = df.select_dtypes(include=[np.number]).columns
numeric_cols = [c for c in numeric_cols if c != 'timestamp']

# Normalize for visualization
df_norm = (df[numeric_cols] - df[numeric_cols].mean()) / df[numeric_cols].std()

# Heatmap
plt.figure(figsize=(16, 6))
sns.heatmap(df_norm.T, cmap='RdYlGn_r', center=0, cbar_kws={'label': 'Std deviations'})
plt.xlabel('Sample')
plt.ylabel('Signal')
plt.title('Controller Debug Signals Heatmap')
plt.tight_layout()
plt.show()
"""

# ══════════════════════════════════════════════════════════════════
# NEXT STEPS
# ══════════════════════════════════════════════════════════════════

"""
1. Examine your controller code to identify indices
   → Look for debug_msg construction in padih_controller source

2. Create a mapping file (JSON) with meaningful names
   → Run: python3 float64_array_extractor.py example --controller padih_controller

3. Extract bag to CSV using ROS2 Data Analyzer
   → Tab 2: Bag → CSV → Select debug_topic

4. Post-process with mapping (Python script provided)
   → Rename columns from data_0, data_1 to meaningful names

5. Analyze and visualize
   → Use pandas + matplotlib patterns shown above
   → Create publication-quality plots
   → Share insights with your team

6. Automate the pipeline
   → Create a single Python script that:
     - Loads bag messages directly
     - Applies mapping
     - Generates analysis plots
     - Saves cleaned CSV
"""

if __name__ == "__main__":
    print(__doc__)
