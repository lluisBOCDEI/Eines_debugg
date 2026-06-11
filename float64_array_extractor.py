#!/usr/bin/env python3
"""
Float64MultiArray Extractor & Renamer

Extracts std_msgs/Float64MultiArray topics from ROS2 bag files
and renames columns based on a user-provided mapping.

Useful for controller debug data where array indices have semantic meaning.
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Optional
import sys


class Float64MultiArrayExtractor:
    """Extract and process Float64MultiArray data from bag files."""
    
    @staticmethod
    def extract_with_mapping(
        messages: List[Dict],
        field_mapping: Dict[int, str],
        timestamp_field: str = 'timestamp'
    ) -> List[Dict]:
        """
        Extract array data and rename columns based on mapping.
        
        Args:
            messages: List of dicts from bag extraction
            field_mapping: {index: "meaningful_name", ...}
                          e.g., {0: "timestamp", 1: "ref_speed", ...}
            timestamp_field: Which key contains the timestamp
        
        Returns:
            List of dicts with renamed columns
        """
        processed = []
        
        for msg in messages:
            row = {}
            
            # Get the data array
            if 'data' in msg:
                data = msg['data']
                
                # Map indices to meaningful names
                for idx, value in enumerate(data):
                    if idx in field_mapping:
                        col_name = field_mapping[idx]
                    else:
                        col_name = f"unknown_{idx}"
                    
                    row[col_name] = value
            
            # Ensure timestamp is first
            if timestamp_field in row:
                ts = row.pop(timestamp_field)
                new_row = {'timestamp': ts}
                new_row.update(row)
                processed.append(new_row)
            else:
                processed.append(row)
        
        return processed
    
    @staticmethod
    def save_mapping_template(output_file: str, num_fields: int):
        """Generate a template mapping file based on number of fields."""
        template = {
            "description": "Field mapping for Float64MultiArray debug topic",
            "field_mapping": {
                str(i): f"field_{i}" for i in range(num_fields)
            },
            "notes": [
                "Replace 'field_N' with meaningful names for each index",
                "Example: {\"0\": \"timestamp\", \"1\": \"reference_speed\", ...}",
                "Unmapped fields will be named 'unknown_N'"
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(template, f, indent=2)
        
        print(f"✓ Template saved to {output_file}")
        print(f"  Edit this file to map indices to meaningful names")
    
    @staticmethod
    def load_mapping(mapping_file: str) -> Dict[int, str]:
        """Load field mapping from JSON file."""
        try:
            with open(mapping_file, 'r') as f:
                data = json.load(f)
                # Convert string keys to ints
                mapping = {int(k): v for k, v in data['field_mapping'].items()}
                return mapping
        except Exception as e:
            print(f"Error loading mapping: {e}")
            return {}


# ══════════════════════════════════════════════════════════════════
#  EXAMPLE MAPPINGS FOR COMMON CONTROLLER DATA
# ══════════════════════════════════════════════════════════════════

EXAMPLE_MAPPINGS = {
    "padih_controller": {
        0: "timestamp",
        1: "reference_speed",
        2: "actual_speed_left",
        3: "speed_error_left",
        4: "left_position",
        5: "left_velocity",
        6: "left_effort",
        7: "left_power",
        8: "right_position",
        9: "right_velocity",
        10: "right_effort",
        11: "right_power",
        12: "imu_roll",
        13: "imu_pitch",
        14: "imu_yaw",
        15: "battery_voltage",
        16: "battery_current",
        17: "temperature_left",
        18: "temp_error_left",
        19: "current_limit_left",
        20: "current_actual_left",
        21: "current_error_left",
        22: "controller_temp",
        23: "load_percentage",
        24: "encoder_left_error",
        25: "encoder_left_position",
        26: "motor_left_kp",
        27: "motor_left_ki",
        28: "motor_left_kd",
        29: "motor_left_integral_max",
        30: "motor_right_p_gain",
        31: "motor_right_i_gain",
        32: "encoder_right_position",
        33: "encoder_right_error",
        34: "encoder_right_position_ref",
        35: "encoder_right_velocity",
        36: "motor_right_kd",
        37: "motor_right_integral_max",
        38: "motor_right_kp",
        39: "motor_right_ki",
        40: "speed_limit_max_positive",
        41: "speed_limit_max_negative",
        42: "speed_limit_acceleration",
        43: "speed_limit_deceleration",
        44: "speed_limit_negative_max",
        45: "speed_limit_negative_min",
        46: "speed_limit_neg_accel",
        47: "speed_limit_neg_decel",
    }
}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract and rename Float64MultiArray data from ROS2 bags"
    )
    parser.add_argument('command', choices=['template', 'example'],
                       help='template: create mapping template | example: show example mapping')
    parser.add_argument('--output', '-o', help='Output file for template')
    parser.add_argument('--fields', '-f', type=int, default=48,
                       help='Number of fields (for template generation)')
    parser.add_argument('--controller', default='padih_controller',
                       help='Which example controller to show')
    
    args = parser.parse_args()
    
    if args.command == 'template':
        output = args.output or 'float64_mapping.json'
        Float64MultiArrayExtractor.save_mapping_template(output, args.fields)
    
    elif args.command == 'example':
        if args.controller in EXAMPLE_MAPPINGS:
            mapping = EXAMPLE_MAPPINGS[args.controller]
            print(f"\n{'═' * 70}")
            print(f"Example Mapping: {args.controller}")
            print(f"{'═' * 70}\n")
            
            for idx, name in sorted(mapping.items()):
                print(f"  [{idx:2d}] {name}")
            
            print(f"\n{'═' * 70}")
            print("To use this mapping:")
            print("  1. Save to a JSON file: mapping.json")
            print("  2. Use with the data analyzer or custom script")
            print(f"{'═' * 70}\n")
        else:
            print(f"Unknown controller: {args.controller}")
            print(f"Available: {list(EXAMPLE_MAPPINGS.keys())}")
