#!/usr/bin/env python3
"""
Subscribe to /padih_controller/debug_topic and save to CSV.

Usage:
    python3 debug_topic_to_csv.py
    python3 debug_topic_to_csv.py --output my_data.csv
    python3 debug_topic_to_csv.py --mapping my_mapping.json --topic /custom/topic

Press Ctrl+C to stop and save the CSV.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

import csv
import json
import argparse
import signal
import sys
from datetime import datetime


class DebugTopicLogger(Node):
    def __init__(self, topic, output_file, field_mapping):
        super().__init__('debug_topic_logger')

        self.output_file = output_file
        self.field_mapping = field_mapping  # {int_index: "name"}

        # Build column list (sorted by index, "unknown_N" for unmapped)
        self.columns = []           # final CSV column order
        self.col_indices = []       # indices that map to those columns
        self.expected_size = None   # set on first message

        # Open CSV file
        self.csv_file = open(output_file, 'w', newline='')
        self.writer = None  # built on first message (need length)

        self.msg_count = 0

        # Subscribe
        self.subscription = self.create_subscription(
            Float64MultiArray,
            topic,
            self.callback,
            10
        )

        self.get_logger().info(f"Subscribed to {topic}")
        self.get_logger().info(f"Writing to {output_file}")
        self.get_logger().info("Waiting for messages... (Ctrl+C to stop)")

    def callback(self, msg):
        data = list(msg.data)

        # First message → build header
        if self.writer is None:
            self.expected_size = len(data)
            self.columns = []
            self.col_indices = []
            for i in range(self.expected_size):
                name = self.field_mapping.get(i, f"unknown_{i}")
                self.columns.append(name)
                self.col_indices.append(i)

            self.writer = csv.writer(self.csv_file)
            self.writer.writerow(self.columns)
            self.csv_file.flush()

            self.get_logger().info(f"First message received — {self.expected_size} fields")
            self.get_logger().info(f"Columns: {self.columns}")

        # Write the row (handles slightly varying sizes)
        row = []
        for i in self.col_indices:
            row.append(data[i] if i < len(data) else "")
        self.writer.writerow(row)
        self.csv_file.flush()

        self.msg_count += 1
        if self.msg_count % 50 == 0:
            self.get_logger().info(f"Logged {self.msg_count} messages")

    def close(self):
        if self.csv_file:
            self.csv_file.close()
        self.get_logger().info(f"Saved {self.msg_count} messages to {self.output_file}")


def load_mapping(json_file):
    """Load field mapping from JSON file. Returns {int: str}."""
    with open(json_file, 'r') as f:
        data = json.load(f)
    mapping = {int(k): v for k, v in data['field_mapping'].items()}
    return mapping


def main():
    parser = argparse.ArgumentParser(description="Log /padih_controller/debug_topic to CSV")
    parser.add_argument('--topic', default='/padih_controller/debug_topic',
                        help='ROS2 topic name (default: /padih_controller/debug_topic)')
    parser.add_argument('--mapping', default='padih_debug_mapping.json',
                        help='JSON file with field_mapping (default: padih_debug_mapping.json)')
    parser.add_argument('--output', '-o', default=None,
                        help='Output CSV file (default: debug_<timestamp>.csv)')
    args = parser.parse_args()

    # Default output file
    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"debug_{ts}.csv"

    # Load mapping
    try:
        mapping = load_mapping(args.mapping)
        print(f"✓ Loaded mapping with {len(mapping)} fields from {args.mapping}")
    except FileNotFoundError:
        print(f"⚠ Mapping file '{args.mapping}' not found — columns will be 'unknown_N'")
        mapping = {}
    except Exception as e:
        print(f"⚠ Error loading mapping ({e}) — columns will be 'unknown_N'")
        mapping = {}

    # Start ROS2
    rclpy.init()
    node = DebugTopicLogger(args.topic, args.output, mapping)

    # Graceful shutdown on Ctrl+C
    def shutdown(signum, frame):
        print("\n[!] Stopping...")
        node.close()
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(0)
    signal.signal(signal.SIGINT, shutdown)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
