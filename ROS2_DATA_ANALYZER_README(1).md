# ROS2 Data Analyzer

A comprehensive PyQt5 tool for analyzing ROS2 bag files and real-time data streams.

## Features

### ▶ **Tab 1: Bag Player**
- Load and **play/replay ROS2 `.db3` bag files**
- Configurable playback speed (0.1x to 10x)
- Loop playback option
- All topics are published as live ROS2 topics during playback
- Monitor playback status in real-time
- Stop playback at any time

**Perfect for:**
- Replaying robot missions for analysis
- Testing algorithms with recorded data
- Simulating real-world scenarios in development

### 🎯 **Tab 2: Bag → CSV Converter**
- Load ROS2 `.db3` bag files
- Automatically detect all topics
- Select topics to export
- Flatten nested message fields into CSV columns
- Multi-threaded extraction with progress tracking

**Output CSV structure:**
```
timestamp, field1, field2, nested.field, nested.array_0, nested.array_1, ...
1.234567, 10.5, 20.3, 15.0, 1.0, 2.0, ...
1.234678, 10.6, 20.4, 15.1, 1.1, 2.1, ...
```

### 📊 **Tab 3: CSV Plotter**
- Load exported CSV files
- Configure X and Y axes
- Plot multiple fields on same graph or separate subplots
- View plots in the app or open in separate windows
- Three plot styles:
  - **Same Plot**: All Y columns on one graph
  - **Separate Subplots**: Stacked subplots in one window
  - **Separate Windows**: Each field in its own window

### 📡 **Tab 4: Real-time Monitor**
Two modes for live data visualization:

**Live Mode:** Subscribe to active ROS2 topics and plot in real-time
**Replay Mode:** Replay a bag file and plot data as if monitoring live

Select fields and watch the plot update in real-time.

## Installation

### 1. Install dependencies

```bash
# Core PyQt5 and plotting
pip install PyQt5 matplotlib pandas numpy

# ROS2 bag and topic handling
# (Usually available in ROS2 environment; if not:)
pip install rosbag2-py rclpy
```

### 2. Make executable and run

```bash
chmod +x ros2_data_analyzer.py
python3 ros2_data_analyzer.py
```

## Usage

### Quick Start 1: Play a Bag File Live

1. **Play the bag:**
   - Open **Tab 1: Bag Player**
   - Click "Browse Bag File..." and select your `.db3` bag
   - Set playback speed (default 1.0x = real-time)
   - Optionally enable "Loop playback"
   - Click "▶ Play Bag"
   - All topics are now published as live ROS2 topics

2. **Monitor in real-time:**
   - Open **Tab 4: Real-time Monitor**
   - Choose "Live ROS2 Topics" mode
   - Enter topic name (e.g., `/odometry`)
   - Enter fields to plot (e.g., `pose.position.x, pose.position.y`)
   - Click "▶ Start Monitoring" to watch live as bag plays

3. **Switch back to stop:**
   - Return to **Tab 1: Bag Player**
   - Click "⏹ Stop" to end playback

### Quick Start 2: Bag File → CSV → Plot

1. **Extract data from bag:**
   - Open **Tab 2: Bag → CSV**
   - Click "Browse Bag File..." and select your `.db3` bag
   - Click "🔍 Detect Topics" to see available topics
   - Configure output directory
   - Click "▶ Export Selected Topics to CSV"
   - Wait for extraction to complete

2. **Plot the CSV data:**
   - Open **Tab 3: CSV Plotter**
   - Click "Browse..." and select one of the generated CSV files
   - X-axis automatically defaults to `timestamp`
   - Select one or more Y columns to plot
   - Choose plot style (Same Plot / Separate Subplots / Separate Windows)
   - Click "📊 Plot Data"

3. **Real-time monitoring (optional):**
   - Open **Tab 4: Real-time Monitor**
   - Choose mode: **Live ROS2 Topics** or **Bag Replay**
   - Enter topic name (e.g., `/robot/odometry`)
   - Enter fields to plot (e.g., `x, y, z`)
   - Click "▶ Start Monitoring" to begin plotting

## CSV Format Details

Each exported CSV has:
- **`timestamp`**: Unix timestamp in seconds (extracted from ROS2 message)
- **Scalar fields**: Direct column (e.g., `temperature: 25.5`)
- **Nested fields**: Dot notation (e.g., `pose.position.x`)
- **Arrays/Vectors**: Indexed columns (e.g., `accel_0, accel_1, accel_2`)

**Example CSV:**
```
timestamp,pose.position.x,pose.position.y,pose.position.z,twist.linear.x,twist.linear.y,twist.linear.z
1234567890.123,0.0,0.0,0.0,0.5,0.0,0.0
1234567890.133,0.05,0.0,0.0,0.5,0.0,0.0
1234567890.143,0.10,0.0,0.0,0.5,0.0,0.0
```

## Troubleshooting

### Bag Player Issues

**"Failed to start playback" error**
- Make sure ROS2 is installed and your environment is sourced:
  ```bash
  source /opt/ros/<distro>/setup.bash
  # or your workspace
  source ~/your_ws/install/setup.bash
  ```
- Verify `ros2 bag play` works in terminal:
  ```bash
  ros2 bag play /path/to/bag.db3
  ```
- Check the bag file path is correct and ends in `.db3`

**Topics not appearing after playback starts**
- It takes a moment for topics to appear. Wait a few seconds.
- Check playback is running — status should say "Playing..."
- Verify the bag file actually contains data (not just metadata)

**Playback too fast/slow**
- Adjust the "Playback Rate" spinner before clicking ▶ Play Bag
- 1.0x = real-time, 2.0x = 2x speed, 0.5x = half speed

**"No topics detected" when loading a bag file
- Ensure the bag file path is correct and ends in `.db3`
- The bag file must have at least one message recorded
- ROS2 rosbag2 libraries must be installed

### Real-time monitoring shows no data
- For **Live mode**: Ensure ROS2 nodes are actively publishing to the topic
- For **Replay mode**: Topic name must match exactly (case-sensitive)
- Check that fields you're trying to plot exist in the message

### Plot appears empty
- Ensure you've selected at least one Y-axis column
- Check that the CSV file has data rows (not just headers)
- For numeric columns: verify data types are numeric (not strings)

## Advanced Features

### Custom field filtering
In CSV Plotter, you can:
- Select multiple Y columns for comparison
- Mix numeric and boolean fields
- Switch between plot styles without reloading

### Batch processing
To export multiple bags at once, create a script:

```python
from ros2_data_analyzer import BagReader, CSVHandler
import os

for bag_file in os.listdir("./bags/"):
    if bag_file.endswith(".db3"):
        topics = BagReader.get_topics(f"./bags/{bag_file}")
        for topic in topics:
            messages = BagReader.extract_topic_to_dict(f"./bags/{bag_file}", topic)
            filename = f"./data/{topic.replace('/', '_')}.csv"
            os.makedirs("./data", exist_ok=True)
            CSVHandler.write_csv(filename, messages)
```

## Notes

- Bag extraction is multi-threaded; large bags may take a moment
- Real-time plotting buffers data in memory; very long sessions may use significant RAM
- CSV files are fully self-contained and can be analyzed with Excel, pandas, or any CSV tool
- Timestamp values are always in **seconds** (with decimal precision)

## License

Free to use and modify for ROS2 projects.
