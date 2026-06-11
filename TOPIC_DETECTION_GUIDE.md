#!/usr/bin/env python3
"""
ROS2 Data Analyzer — Topic Detection Feature Guide

NEW: Tab 4 (Real-time Monitor) now includes automatic ROS2 topic detection!
"""

# ══════════════════════════════════════════════════════════════════
# WHAT'S NEW
# ══════════════════════════════════════════════════════════════════

"""
The Real-time Monitor tab now has a "Detect Available Topics" button
that automatically discovers all ROS2 topics running on your system.

Features:
✓ One-click topic discovery
✓ Shows topic name and message type
✓ Click a topic to auto-populate the field
✓ Works with any ROS2 setup (real robot, simulation, bag replay)
"""

# ══════════════════════════════════════════════════════════════════
# WORKFLOW
# ══════════════════════════════════════════════════════════════════

"""
WORKFLOW 1: Monitor Real Robot
================================

1. Ensure robot is running and publishing topics

2. Open "Tab 4: Real-time Monitor"

3. Make sure "Live ROS2 Topics" mode is selected

4. Click "🔍 Detect Available Topics"
   → Tool queries ROS2 and finds all active topics
   → Topics appear in the list with their message types

5. Click on a topic in the list to select it
   → Topic name auto-fills in "Selected topic" field
   
6. Enter fields to plot (e.g., "x, y, z")

7. Click "▶ Start Monitoring"
   → Live data visualization starts immediately!


WORKFLOW 2: Play Bag and Monitor
==================================

1. Go to "Tab 1: Bag Player"

2. Load your .db3 bag file

3. Click "▶ Play Bag"
   → Bag playback starts in background
   → All topics from bag are published live

4. Switch to "Tab 4: Real-time Monitor"

5. Make sure "Live ROS2 Topics" mode is selected

6. Click "🔍 Detect Available Topics"
   → All topics from the playing bag appear
   → Same as if the robot were running!

7. Click a topic to select it

8. Enter fields to plot

9. Click "▶ Start Monitoring"
   → Watch live visualization as bag plays!


WORKFLOW 3: Pre-loaded Bag Replay
==================================

1. "Tab 4: Real-time Monitor" → Switch to "Bag Replay" mode

2. Click "Choose Output Directory..." → Select a .db3 bag file

3. Enter topic name (e.g., "/odometry")

4. Enter fields to plot

5. Click "▶ Start Monitoring"
   → Bag is extracted and plotted (no live playback needed)
   → Useful for post-analysis
"""

# ══════════════════════════════════════════════════════════════════
# TROUBLESHOOTING
# ══════════════════════════════════════════════════════════════════

"""
Q: "No topics detected" / "Detection failed"

A: Make sure:
   • ROS2 is installed and your environment is sourced
   • ROS2 nodes are actually publishing (check: ros2 topic list)
   • For bag playback: bag player is running (see Tab 1 status)
   
   If using bag player:
   - Go back to Tab 1, ensure status says "Playing..."
   - Wait a few seconds for topics to appear (there's a delay)
   - Click "Detect" again


Q: Topic detected but fields won't plot

A: The field names you enter must match the message structure.
   
   Common field names:
   - For /odometry (nav_msgs/Odometry):
     pose.pose.position.x, pose.pose.position.y, twist.twist.linear.x
   
   - For /cmd_vel (geometry_msgs/Twist):
     linear.x, linear.y, angular.z
   
   - For /imu (sensor_msgs/Imu):
     linear_acceleration.x, angular_velocity.z
   
   If unsure, try extracting to CSV first (Tab 2) to see available fields.


Q: Detected topics but clicking on them doesn't work

A: Make sure you're clicking on the topic item in the list.
   The topic name should appear in the "Selected topic" field below.
   If it's not showing, try clicking again.


Q: Performance is slow when detecting

A: Large ROS2 systems with many topics (100+) may take a few seconds.
   The detection runs in background so the UI won't freeze.
   Just wait for "Status: Found X topics" message.
"""

# ══════════════════════════════════════════════════════════════════
# QUICK REFERENCE
# ══════════════════════════════════════════════════════════════════

"""
Button: "🔍 Detect Available Topics"
→ Queries your ROS2 system for all active topics
→ Takes 1-5 seconds depending on system size
→ Results appear in the "Available topics:" list

Topics List:
→ Click any topic to auto-fill the "Selected topic:" field
→ Shows topic name and message type
→ Only shows if detection was successful

Selected Topic Field:
→ You can type manually OR click a topic to auto-fill
→ Must match exact ROS2 topic name (case-sensitive)

Fields Input:
→ Comma-separated list of message fields
→ Get field names from CSV (Tab 2) if unsure
→ Example: "position.x, position.y, velocity.z"

Start/Stop Buttons:
→ "▶ Start Monitoring" → Begin live plotting
→ "⏹ Stop" → Stop the visualization
"""

# ══════════════════════════════════════════════════════════════════
# EXAMPLE WORKFLOWS
# ══════════════════════════════════════════════════════════════════

"""
Example 1: Monitor a Moving Robot
==================================

Setup:
- Robot publishing /odometry, /gps, /battery topics
- Everything running normally

Steps:
1. Tab 4 → Click "🔍 Detect Available Topics"
2. Wait for topics to appear...
3. See: /odometry (nav_msgs/Odometry)
4. Click /odometry in the list
5. Detected topic name fills: "/odometry"
6. Enter fields: "pose.pose.position.x, pose.pose.position.y"
7. Click "▶ Start Monitoring"
8. Watch real-time X,Y position plot update


Example 2: Analyze Recorded Mission (with playback)
====================================================

Setup:
- Recorded a mission to mission.db3

Steps:
1. Tab 1 (Bag Player) → Browse and load mission.db3
2. Set playback speed to 0.5x (slow motion analysis)
3. Click "▶ Play Bag"
4. Tab 4 → "Live ROS2 Topics" mode selected
5. Click "🔍 Detect Available Topics"
6. See all topics from the bag
7. Click /odometry to select it
8. Enter: "pose.pose.position.x, twist.twist.linear.x"
9. Click "▶ Start Monitoring"
10. Watch slow-motion replay with plot updating in sync


Example 3: Compare Multiple Topics
===================================

Steps:
1. Detect topics once
2. Click /odometry → Start monitoring with "pose.pose.position.x"
3. Let it run for a bit, observe plot
4. Click ⏹ Stop
5. Click another topic (e.g., /gps)
6. Enter field: "latitude"  
7. Click "▶ Start Monitoring" again
8. Watch GPS latitude over time in separate plot session
"""

# ══════════════════════════════════════════════════════════════════
# UNDER THE HOOD
# ══════════════════════════════════════════════════════════════════

"""
How topic detection works:

1. Click "🔍 Detect Available Topics"
   ↓
2. TopicDetectorWorker thread spawns (non-blocking)
   ↓
3. Creates a temporary ROS2 node
   ↓
4. Calls node.get_topic_names_and_types()
   ↓
5. Gets all topics currently published
   ↓
6. Returns to UI thread with results
   ↓
7. Topics populate the list
   ↓
8. Status updates: "Found X topics"

The whole process runs in background so GUI stays responsive.
Typical detection time: 1-3 seconds
Maximum detected topics: Limited only by system (tested with 200+)
"""
