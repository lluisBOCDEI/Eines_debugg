#!/usr/bin/env python3
"""
Example: Using ROS2 Data Analyzer components programmatically
"""

from pathlib import Path
import sys

# These examples show how to use the analyzer components outside the GUI

# ══════════════════════════════════════════════════════════════════
# EXAMPLE 1: Extract a specific topic from a bag file
# ══════════════════════════════════════════════════════════════════
def example_extract_single_topic():
    """Extract one topic from a bag and save to CSV."""
    from ros2_data_analyzer import BagReader, CSVHandler
    
    bag_path = "/path/to/your/recording.db3"
    output_dir = "/tmp/ros2_data"
    topic_to_extract = "/robot/odometry"
    
    # Get messages from topic
    messages = BagReader.extract_topic_to_dict(bag_path, topic_to_extract)
    
    if messages:
        # Save to CSV
        output_path = f"{output_dir}/{topic_to_extract.strip('/').replace('/', '_')}.csv"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        CSVHandler.write_csv(output_path, messages)
        print(f"✓ Extracted {len(messages)} messages to {output_path}")
    else:
        print(f"✗ No messages found for topic {topic_to_extract}")


# ══════════════════════════════════════════════════════════════════
# EXAMPLE 2: Batch extract all topics from a bag file
# ══════════════════════════════════════════════════════════════════
def example_extract_all_topics():
    """Extract all topics from a bag file."""
    from ros2_data_analyzer import BagReader, CSVHandler
    
    bag_path = "/path/to/your/recording.db3"
    output_dir = "/tmp/ros2_data"
    
    # Detect all topics
    topics = BagReader.get_topics(bag_path)
    print(f"Found {len(topics)} topics:")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    for topic_name, msg_type in topics.items():
        print(f"  Extracting {topic_name}...", end=" ", flush=True)
        messages = BagReader.extract_topic_to_dict(bag_path, topic_name)
        
        if messages:
            filename = topic_name.strip('/').replace('/', '_') + '.csv'
            filepath = Path(output_dir) / filename
            CSVHandler.write_csv(str(filepath), messages)
            print(f"✓ {len(messages)} messages")
        else:
            print("(empty)")


# ══════════════════════════════════════════════════════════════════
# EXAMPLE 3: Load CSV and analyze with pandas
# ══════════════════════════════════════════════════════════════════
def example_analyze_csv():
    """Load a CSV and perform analysis."""
    from ros2_data_analyzer import CSVHandler
    import pandas as pd
    
    csv_path = "/tmp/ros2_data/robot_odometry.csv"
    
    # Load with pandas
    df = CSVHandler.read_csv(csv_path)
    
    print(f"CSV has {len(df)} rows and {len(df.columns)} columns")
    print(f"\nColumns: {list(df.columns)}")
    
    # Statistics
    print(f"\nBasic statistics:")
    print(df.describe())
    
    # Filter data
    print(f"\nFiltering rows where pose.position.x > 1.0:")
    filtered = df[df['pose.position.x'] > 1.0]
    print(f"  Found {len(filtered)} rows")
    
    # Compute velocity
    if 'twist.linear.x' in df.columns:
        print(f"\nMax velocity: {df['twist.linear.x'].max():.3f} m/s")
        print(f"Avg velocity: {df['twist.linear.x'].mean():.3f} m/s")


# ══════════════════════════════════════════════════════════════════
# EXAMPLE 4: Plot CSV data programmatically
# ══════════════════════════════════════════════════════════════════
def example_plot_csv():
    """Load CSV and create plots."""
    from ros2_data_analyzer import CSVHandler
    import matplotlib.pyplot as plt
    
    csv_path = "/tmp/ros2_data/robot_odometry.csv"
    df = CSVHandler.read_csv(csv_path)
    
    # Plot position over time
    fig, axes = plt.subplots(3, 1, figsize=(10, 8))
    
    # X position
    axes[0].plot(df['timestamp'], df['pose.position.x'])
    axes[0].set_ylabel('X position (m)')
    axes[0].grid(True, alpha=0.3)
    
    # Y position
    axes[1].plot(df['timestamp'], df['pose.position.y'])
    axes[1].set_ylabel('Y position (m)')
    axes[1].grid(True, alpha=0.3)
    
    # Z position
    axes[2].plot(df['timestamp'], df['pose.position.z'])
    axes[2].set_ylabel('Z position (m)')
    axes[2].set_xlabel('Time (s)')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/tmp/position_trajectory.png', dpi=100)
    print("✓ Saved plot to /tmp/position_trajectory.png")
    plt.show()


# ══════════════════════════════════════════════════════════════════
# EXAMPLE 5: Compare multiple topics side-by-side
# ══════════════════════════════════════════════════════════════════
def example_compare_topics():
    """Load multiple CSV files and plot them together."""
    from ros2_data_analyzer import CSVHandler
    import matplotlib.pyplot as plt
    
    # Load multiple CSVs
    odom_df = CSVHandler.read_csv("/tmp/ros2_data/robot_odometry.csv")
    gps_df = CSVHandler.read_csv("/tmp/ros2_data/robot_gps.csv")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Odometry
    ax1.plot(odom_df['pose.position.x'], odom_df['pose.position.y'], 'b-', label='Odometry')
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_title('Robot Path - Odometry')
    ax1.grid(True, alpha=0.3)
    ax1.axis('equal')
    
    # GPS
    ax2.plot(gps_df['latitude'], gps_df['longitude'], 'r-', label='GPS')
    ax2.set_xlabel('Latitude')
    ax2.set_ylabel('Longitude')
    ax2.set_title('Robot Path - GPS')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/tmp/path_comparison.png', dpi=100)
    print("✓ Saved comparison plot to /tmp/path_comparison.png")
    plt.show()


# ══════════════════════════════════════════════════════════════════
# EXAMPLE 6: Extract and immediately plot (pipeline)
# ══════════════════════════════════════════════════════════════════
def example_pipeline():
    """Full pipeline: extract → load → plot."""
    from ros2_data_analyzer import BagReader, CSVHandler
    import matplotlib.pyplot as plt
    from pathlib import Path
    
    # Config
    bag_path = "/path/to/recording.db3"
    topic = "/robot/odometry"
    output_dir = "/tmp/analysis"
    
    # Step 1: Extract
    print("Extracting from bag...")
    messages = BagReader.extract_topic_to_dict(bag_path, topic)
    
    # Step 2: Save
    print("Saving to CSV...")
    output_path = Path(output_dir) / "odometry.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    CSVHandler.write_csv(str(output_path), messages)
    
    # Step 3: Load and plot
    print("Plotting...")
    df = CSVHandler.read_csv(str(output_path))
    
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    
    if 'pose.position.x' in df.columns:
        axes[0, 0].plot(df['timestamp'], df['pose.position.x'])
        axes[0, 0].set_title('X Position')
    
    if 'pose.position.y' in df.columns:
        axes[0, 1].plot(df['timestamp'], df['pose.position.y'])
        axes[0, 1].set_title('Y Position')
    
    if 'twist.linear.x' in df.columns:
        axes[1, 0].plot(df['timestamp'], df['twist.linear.x'])
        axes[1, 0].set_title('Linear Velocity X')
    
    if 'twist.angular.z' in df.columns:
        axes[1, 1].plot(df['timestamp'], df['twist.angular.z'])
        axes[1, 1].set_title('Angular Velocity Z')
    
    for ax in axes.flat:
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Time (s)')
    
    plt.tight_layout()
    print("✓ Pipeline complete")
    plt.show()


# ══════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ROS2 Data Analyzer Examples")
    parser.add_argument('example', nargs='?', default='list',
                       help='Example to run: extract_single, extract_all, analyze, plot, compare, pipeline')
    args = parser.parse_args()
    
    examples = {
        'extract_single': example_extract_single_topic,
        'extract_all': example_extract_all_topics,
        'analyze': example_analyze_csv,
        'plot': example_plot_csv,
        'compare': example_compare_topics,
        'pipeline': example_pipeline,
    }
    
    if args.example == 'list':
        print("Available examples:")
        for name in examples:
            print(f"  python3 examples.py {name}")
    elif args.example in examples:
        print(f"\n{'='*60}")
        print(f"Running: {args.example}")
        print(f"{'='*60}\n")
        examples[args.example]()
    else:
        print(f"Unknown example: {args.example}")
        sys.exit(1)
