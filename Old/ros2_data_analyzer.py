#!/usr/bin/env python3
"""
ROS2 Data Analyzer — Integrated Tool for Bag Extraction, CSV Plotting, & Real-Time Monitoring

Features:
  • Tab 1: Bag to CSV — Extract ROS2 bag topics to CSV files with timestamp + flattened fields
  • Tab 2: CSV Plotter — Load CSV files and plot with configurable axes (same/separate plots)
  • Tab 3: Real-time Monitor — Live plot from ROS2 topics or bag replay
"""

import sys
import os
import json
import csv
import subprocess
import threading
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QTextEdit, QFileDialog, QMessageBox,
    QLineEdit, QGroupBox, QCheckBox, QListWidget, QListWidgetItem,
    QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar, QTableWidget,
    QTableWidgetItem, QSplitter, QScrollArea, QGridLayout, QDialog,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect
from PyQt5.QtGui import QFont, QIcon, QColor

# ══════════════════════════════════════════════════════════════════
#  BACKEND: BAG READER (ROS2 rosbag2)
# ══════════════════════════════════════════════════════════════════
class BagReader:
    """Reads ROS2 .db3 bag files and extracts messages."""
    
    @staticmethod
    def get_topics(bag_path: str) -> Dict[str, str]:
        """Detect topics in a bag file → {topic_name: msg_type}"""
        try:
            import rosbag2_py
            reader = rosbag2_py.SequentialReader()
            reader.open(rosbag2_py.StorageOptions(uri=bag_path, storage_id='sqlite3'),
                       rosbag2_py.ConverterOptions())
            topics = {}
            for topic_info in reader.get_all_topics_and_types():
                topics[topic_info.name] = topic_info.type
            reader.close()
            return topics
        except Exception as e:
            return {}

    @staticmethod
    def extract_topic_to_dict(bag_path: str, topic_name: str) -> List[Dict]:
        """Extract all messages from a topic → list of {timestamp, field1, field2, ...}"""
        try:
            import rosbag2_py
            from rosidl_runtime_py.utilities import get_message
            
            reader = rosbag2_py.SequentialReader()
            reader.open(rosbag2_py.StorageOptions(uri=bag_path, storage_id='sqlite3'),
                       rosbag2_py.ConverterOptions())
            
            messages = []
            while reader.has_next():
                topic, msg, ts = reader.read_next()
                if topic == topic_name:
                    msg_dict = BagReader._msg_to_dict(msg, ts)
                    messages.append(msg_dict)
            reader.close()
            return messages
        except Exception as e:
            print(f"Error reading topic {topic_name}: {e}")
            return []

    @staticmethod
    def _msg_to_dict(msg: Any, timestamp: int) -> Dict:
        """Flatten a ROS2 message into a flat dict: {timestamp, field.subfield, ...}"""
        flat = {"timestamp": timestamp / 1e9}  # ns → seconds
        
        def flatten(obj, prefix=""):
            if hasattr(obj, '__dict__'):
                for key, val in obj.__dict__.items():
                    if key.startswith('_'):
                        continue
                    new_key = f"{prefix}{key}" if prefix else key
                    if isinstance(val, (int, float, bool)):
                        flat[new_key] = val
                    elif isinstance(val, str):
                        pass  # Skip strings
                    elif isinstance(val, (list, tuple)):
                        for i, v in enumerate(val):
                            if isinstance(v, (int, float, bool)):
                                flat[f"{new_key}_{i}"] = v
                            else:
                                flatten(v, f"{new_key}_{i}.")
                    else:
                        flatten(val, f"{new_key}.")
        
        flatten(msg)
        return flat


# ══════════════════════════════════════════════════════════════════
#  BACKEND: CSV HANDLER
# ══════════════════════════════════════════════════════════════════
class CSVHandler:
    """Handle CSV file operations."""
    
    @staticmethod
    def write_csv(filepath: str, data: List[Dict]):
        """Write list of dicts to CSV file."""
        if not data:
            return
        keys = set()
        for record in data:
            keys.update(record.keys())
        keys = sorted(list(keys))
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)

    @staticmethod
    def read_csv(filepath: str) -> pd.DataFrame:
        """Read CSV and return pandas DataFrame."""
        return pd.read_csv(filepath)


# ══════════════════════════════════════════════════════════════════
#  BACKEND: ROS2 TOPIC DETECTOR
# ══════════════════════════════════════════════════════════════════
class TopicDetector:
    """Detect available ROS2 topics."""
    
    @staticmethod
    def get_available_topics() -> Dict[str, str]:
        """Get all available ROS2 topics → {topic_name: msg_type}"""
        try:
            import rclpy
            from rclpy.node import Node
            
            if not rclpy.ok():
                rclpy.init()
            
            node = Node('topic_detector')
            topic_names_and_types = node.get_topic_names_and_types()
            topics = {}
            
            for name, types in topic_names_and_types:
                if types:
                    topics[name] = types[0]  # Get first message type
            
            node.destroy_node()
            return topics
        except Exception as e:
            print(f"Error detecting topics: {e}")
            return {}


# ══════════════════════════════════════════════════════════════════
#  BACKEND: ROS2 SUBSCRIBER (Real-time monitoring)
# ══════════════════════════════════════════════════════════════════
class ROSSubscriber:
    """Subscribe to live ROS2 topics."""
    
    def __init__(self, topic_name: str, callback):
        self.topic_name = topic_name
        self.callback = callback
        self.running = False
        self.node = None
    
    def start(self):
        """Start subscription in a thread."""
        try:
            import rclpy
            from rclpy.node import Node
            
            class ListenerNode(Node):
                def __init__(self, topic, cb):
                    super().__init__('data_analyzer_listener')
                    self.callback = cb
                    self.sub = self.create_subscription(
                        type(None),  # Wildcard — we'll handle any type
                        topic,
                        self._listener_cb,
                        10
                    )
                
                def _listener_cb(self, msg):
                    self.callback(msg)
            
            if not rclpy.ok():
                rclpy.init()
            self.node = ListenerNode(self.topic_name, self.callback)
            self.running = True
            
            # Spin in a loop
            while self.running:
                rclpy.spin_once(self.node, timeout_sec=0.1)
        except Exception as e:
            print(f"ROS subscription error: {e}")
    
    def stop(self):
        self.running = False
        if self.node:
            self.node.destroy_node()


# ══════════════════════════════════════════════════════════════════
#  BAG PLAYER — Replay .db3 files with ROS2
# ══════════════════════════════════════════════════════════════════
class BagPlayer:
    """Control ROS2 bag playback."""
    
    def __init__(self):
        self.process = None
        self.is_playing = False
    
    def play(self, bag_path: str, rate: float = 1.0, loop: bool = False):
        """Start playing a bag file."""
        try:
            import subprocess
            
            cmd = ["ros2", "bag", "play", bag_path, "--rate", str(rate)]
            if loop:
                cmd.append("--loop")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.is_playing = True
            return True
        except Exception as e:
            print(f"Error starting bag playback: {e}")
            return False
    
    def stop(self):
        """Stop playback."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.is_playing = False
    
    def is_alive(self) -> bool:
        """Check if playback is still running."""
        if self.process:
            return self.process.poll() is None
        return False


# ══════════════════════════════════════════════════════════════════
#  WORKER THREADS
# ══════════════════════════════════════════════════════════════════
class TopicDetectorWorker(QThread):
    """Background worker to detect available ROS2 topics."""
    topics_found = pyqtSignal(dict)  # {topic_name: msg_type}
    error = pyqtSignal(str)

    def run(self):
        try:
            topics = TopicDetector.get_available_topics()
            self.topics_found.emit(topics)
        except Exception as e:
            self.error.emit(str(e))


class BagExtractorWorker(QThread):
    """Background worker for bag extraction."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)  # {topic: filepath, ...}
    error = pyqtSignal(str)

    def __init__(self, bag_path: str, output_dir: str, topics: List[str]):
        super().__init__()
        self.bag_path = bag_path
        self.output_dir = output_dir
        self.topics = topics

    def run(self):
        try:
            results = {}
            for i, topic in enumerate(self.topics):
                self.progress.emit(int(100 * i / len(self.topics)))
                messages = BagReader.extract_topic_to_dict(self.bag_path, topic)
                if messages:
                    filename = topic.replace('/', '_').strip('_') + '.csv'
                    filepath = os.path.join(self.output_dir, filename)
                    CSVHandler.write_csv(filepath, messages)
                    results[topic] = filepath
            self.progress.emit(100)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


# ══════════════════════════════════════════════════════════════════
#  UI: TAB 1 — BAG TO CSV
# ══════════════════════════════════════════════════════════════════
class BagToCSVWidget(QWidget):
    """Extract topics from ROS2 bag files to CSV."""
    
    def __init__(self):
        super().__init__()
        self.bag_path = None
        self.topics_dict = {}
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # File selection
        file_group = QGroupBox("Bag File Selection")
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No bag selected")
        self.file_label.setStyleSheet("color: #888; font-size: 12px;")
        browse_btn = QPushButton("Browse Bag File...")
        browse_btn.clicked.connect(self.browse_bag)
        file_layout.addWidget(self.file_label, stretch=1)
        file_layout.addWidget(browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Topic detection
        detect_group = QGroupBox("Available Topics")
        detect_layout = QVBoxLayout()
        detect_btn = QPushButton("🔍 Detect Topics")
        detect_btn.clicked.connect(self.detect_topics)
        detect_layout.addWidget(detect_btn)
        
        # Topic list with checkboxes
        self.topic_list = QListWidget()
        self.topic_list.setMinimumHeight(200)
        detect_layout.addWidget(QLabel("Select topics to export:"))
        detect_layout.addWidget(self.topic_list)
        detect_group.setLayout(detect_layout)
        layout.addWidget(detect_group)
        
        # Output directory
        output_group = QGroupBox("Output Configuration")
        output_layout = QHBoxLayout()
        self.output_label = QLabel(str(Path.home() / "ros2_data"))
        self.output_label.setStyleSheet("color: #888; font-size: 12px;")
        output_browse = QPushButton("Choose Output Directory...")
        output_browse.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_label, stretch=1)
        output_layout.addWidget(output_browse)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Progress and export
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        export_btn = QPushButton("▶ Export Selected Topics to CSV")
        export_btn.setStyleSheet("font-weight: bold; padding: 12px;")
        export_btn.clicked.connect(self.export_topics)
        layout.addWidget(export_btn)
        
        # Log
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        log_layout.addWidget(self.log)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
    
    def browse_bag(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select ROS2 Bag File", "", "*.db3")
        if path:
            self.bag_path = path
            self.file_label.setText(Path(path).name)
            self.log.append(f"✓ Bag loaded: {Path(path).name}")
    
    def detect_topics(self):
        if not self.bag_path:
            QMessageBox.warning(self, "Warning", "Please select a bag file first.")
            return
        
        self.log.append("🔍 Detecting topics...")
        self.topics_dict = BagReader.get_topics(self.bag_path)
        self.topic_list.clear()
        
        for topic, msg_type in sorted(self.topics_dict.items()):
            item = QListWidgetItem(f"{topic} ({msg_type})")
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, topic)
            self.topic_list.addItem(item)
        
        self.log.append(f"✓ Found {len(self.topics_dict)} topics")
    
    def browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_label.setText(path)
    
    def export_topics(self):
        if not self.bag_path:
            QMessageBox.warning(self, "Warning", "Please select a bag file.")
            return
        
        selected = []
        for i in range(self.topic_list.count()):
            item = self.topic_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select at least one topic.")
            return
        
        output_dir = self.output_label.text()
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        self.worker = BagExtractorWorker(self.bag_path, output_dir, selected)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_export_finished)
        self.worker.error.connect(self.on_export_error)
        self.worker.start()
    
    def on_export_finished(self, results):
        self.log.append(f"\n✓ Export complete! {len(results)} topics saved.")
        for topic, path in results.items():
            self.log.append(f"  • {topic} → {Path(path).name}")
        self.progress.setVisible(False)
        QMessageBox.information(self, "Success", f"Exported {len(results)} topics to CSV.")
    
    def on_export_error(self, error):
        self.log.append(f"✗ Error: {error}")
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Error", error)


# ══════════════════════════════════════════════════════════════════
#  UI: TAB 2 — CSV PLOTTER
# ══════════════════════════════════════════════════════════════════
class CSVPlotterWidget(QWidget):
    """Load and plot CSV files with configurable axes."""
    
    def __init__(self):
        super().__init__()
        self.csv_data = None
        self.csv_path = None
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QHBoxLayout()
        
        # Left panel: controls
        left_panel = QVBoxLayout()
        
        # File selection
        file_group = QGroupBox("Load CSV File")
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #888; font-size: 12px;")
        file_browse = QPushButton("Browse...")
        file_browse.clicked.connect(self.load_csv)
        file_layout.addWidget(self.file_label, stretch=1)
        file_layout.addWidget(file_browse)
        file_group.setLayout(file_layout)
        left_panel.addWidget(file_group)
        
        # Column selection
        col_group = QGroupBox("Plot Configuration")
        col_layout = QVBoxLayout()
        
        col_layout.addWidget(QLabel("X-axis:"))
        self.x_combo = QComboBox()
        col_layout.addWidget(self.x_combo)
        
        col_layout.addWidget(QLabel("Y-axis (select multiple):"))
        self.y_list = QListWidget()
        self.y_list.setSelectionMode(self.y_list.MultiSelection)
        self.y_list.setMaximumHeight(150)
        col_layout.addWidget(self.y_list)
        
        col_layout.addWidget(QLabel("Plot Style:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Same Plot", "Separate Subplots", "Separate Windows"])
        col_layout.addWidget(self.style_combo)
        
        plot_btn = QPushButton("📊 Plot Data")
        plot_btn.setStyleSheet("font-weight: bold; padding: 10px;")
        plot_btn.clicked.connect(self.plot_data)
        col_layout.addWidget(plot_btn)
        
        col_layout.addStretch()
        col_group.setLayout(col_layout)
        left_panel.addWidget(col_group)
        
        # Right panel: matplotlib canvas
        right_panel = QVBoxLayout()
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        right_panel.addWidget(self.canvas)
        
        # Layout assembly
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)
        
        self.setLayout(main_layout)
    
    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "*.csv")
        if path:
            self.csv_path = path
            self.file_label.setText(Path(path).name)
            
            try:
                self.csv_data = CSVHandler.read_csv(path)
                columns = list(self.csv_data.columns)
                
                self.x_combo.clear()
                self.x_combo.addItems(columns)
                if "timestamp" in columns:
                    self.x_combo.setCurrentText("timestamp")
                
                self.y_list.clear()
                for col in columns:
                    if col != "timestamp":
                        item = QListWidgetItem(col)
                        item.setCheckState(Qt.Checked)
                        self.y_list.addItem(item)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {e}")
    
    def plot_data(self):
        if self.csv_data is None:
            QMessageBox.warning(self, "Warning", "Please load a CSV file first.")
            return
        
        x_col = self.x_combo.currentText()
        y_cols = [self.y_list.item(i).text() 
                  for i in range(self.y_list.count()) 
                  if self.y_list.item(i).checkState() == Qt.Checked]
        
        if not y_cols:
            QMessageBox.warning(self, "Warning", "Please select at least one Y column.")
            return
        
        style = self.style_combo.currentText()
        
        try:
            self.figure.clear()
            
            if style == "Same Plot":
                ax = self.figure.add_subplot(111)
                for y_col in y_cols:
                    ax.plot(self.csv_data[x_col], self.csv_data[y_col], label=y_col, marker='o', markersize=2)
                ax.set_xlabel(x_col)
                ax.set_ylabel("Value")
                ax.legend()
                ax.grid(True, alpha=0.3)
            
            elif style == "Separate Subplots":
                n = len(y_cols)
                for idx, y_col in enumerate(y_cols, 1):
                    ax = self.figure.add_subplot(n, 1, idx)
                    ax.plot(self.csv_data[x_col], self.csv_data[y_col], label=y_col, marker='o', markersize=2)
                    ax.set_ylabel(y_col)
                    ax.grid(True, alpha=0.3)
                    if idx == n:
                        ax.set_xlabel(x_col)
            
            elif style == "Separate Windows":
                # Plot each in its own window
                for y_col in y_cols:
                    fig, ax = plt.subplots(figsize=(8, 5))
                    ax.plot(self.csv_data[x_col], self.csv_data[y_col], label=y_col, marker='o', markersize=2)
                    ax.set_xlabel(x_col)
                    ax.set_ylabel(y_col)
                    ax.set_title(y_col)
                    ax.grid(True, alpha=0.3)
                    ax.legend()
                    fig.tight_layout()
                plt.show()
                return
            
            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to plot: {e}")


# ══════════════════════════════════════════════════════════════════
#  UI: TAB 3 — REAL-TIME MONITOR
# ══════════════════════════════════════════════════════════════════
class RealtimeMonitorWidget(QWidget):
    """Real-time plotting from ROS2 topics or bag replay."""
    
    def __init__(self):
        super().__init__()
        self.mode = "live"  # "live" or "replay"
        self.data_buffer = defaultdict(list)
        self.timestamps = []
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QHBoxLayout()
        
        # Left panel: controls
        left_panel = QVBoxLayout()
        
        # Mode selection
        mode_group = QGroupBox("Monitor Mode")
        mode_layout = QVBoxLayout()
        self.mode_live = QCheckBox("Live ROS2 Topics")
        self.mode_live.setChecked(True)
        self.mode_live.stateChanged.connect(lambda: self.set_mode("live"))
        self.mode_replay = QCheckBox("Bag Replay")
        self.mode_replay.stateChanged.connect(lambda: self.set_mode("replay"))
        mode_layout.addWidget(self.mode_live)
        mode_layout.addWidget(self.mode_replay)
        mode_group.setLayout(mode_layout)
        left_panel.addWidget(mode_group)
        
        # Topic selection
        topic_group = QGroupBox("Topic Selection")
        topic_layout = QVBoxLayout()
        
        # Detect topics button
        detect_btn = QPushButton("🔍 Detect Available Topics")
        detect_btn.clicked.connect(self.detect_topics)
        topic_layout.addWidget(detect_btn)
        
        # Topics list
        topic_layout.addWidget(QLabel("Available topics:"))
        self.topics_list = QListWidget()
        self.topics_list.setMaximumHeight(150)
        self.topics_list.itemClicked.connect(self.on_topic_selected)
        topic_layout.addWidget(self.topics_list)
        
        # Selected topic input
        topic_layout.addWidget(QLabel("Selected topic:"))
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("/robot/odometry")
        topic_layout.addWidget(self.topic_input)
        
        topic_layout.addWidget(QLabel("Fields to plot (comma-separated):"))
        self.fields_input = QLineEdit()
        self.fields_input.setPlaceholderText("x, y, z")
        topic_layout.addWidget(self.fields_input)
        
        topic_group.setLayout(topic_layout)
        left_panel.addWidget(topic_group)
        
        # Bag replay options
        self.replay_group = QGroupBox("Bag Replay Options")
        replay_layout = QVBoxLayout()
        replay_layout.addWidget(QLabel("Bag file:"))
        bag_layout = QHBoxLayout()
        self.bag_input = QLineEdit()
        self.bag_input.setPlaceholderText("Select a .db3 file")
        bag_browse = QPushButton("Browse...")
        bag_browse.clicked.connect(self.browse_replay_bag)
        bag_layout.addWidget(self.bag_input)
        bag_layout.addWidget(bag_browse)
        replay_layout.addLayout(bag_layout)
        self.replay_group.setLayout(replay_layout)
        self.replay_group.setVisible(False)
        left_panel.addWidget(self.replay_group)
        
        # Control buttons
        ctrl_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start Monitoring")
        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)
        left_panel.addLayout(ctrl_layout)
        
        # Status
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        left_panel.addWidget(self.status_label)
        
        left_panel.addStretch()
        
        # Right panel: matplotlib live plot
        right_panel = QVBoxLayout()
        self.rt_figure = Figure(figsize=(8, 6), dpi=100)
        self.rt_canvas = FigureCanvas(self.rt_figure)
        right_panel.addWidget(self.rt_canvas)
        
        # Layout assembly
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)
        
        self.setLayout(main_layout)
    
    def set_mode(self, mode):
        self.mode = mode
        if mode == "live":
            self.mode_replay.setChecked(False)
            self.replay_group.setVisible(False)
        else:
            self.mode_live.setChecked(False)
            self.replay_group.setVisible(True)
    
    def detect_topics(self):
        """Detect available ROS2 topics in background."""
        self.status_label.setText("Status: Detecting topics...")
        self.topics_list.clear()
        
        self.detector_worker = TopicDetectorWorker()
        self.detector_worker.topics_found.connect(self.on_topics_detected)
        self.detector_worker.error.connect(self.on_detection_error)
        self.detector_worker.start()
    
    def on_topics_detected(self, topics: Dict[str, str]):
        """Handle detected topics."""
        self.topics_list.clear()
        
        if not topics:
            self.status_label.setText("Status: No topics detected")
            return
        
        for topic_name, msg_type in sorted(topics.items()):
            item = QListWidgetItem(f"{topic_name}\n({msg_type})")
            item.setData(Qt.UserRole, topic_name)
            self.topics_list.addItem(item)
        
        self.status_label.setText(f"Status: Found {len(topics)} topics")
    
    def on_detection_error(self, error: str):
        """Handle topic detection error."""
        self.status_label.setText(f"Status: Detection failed — {error}")
        QMessageBox.warning(self, "Detection Error", f"Could not detect topics:\n{error}\n\nMake sure ROS2 is running.")
    
    def on_topic_selected(self, item: QListWidgetItem):
        """Auto-fill topic name when user selects from list."""
        topic_name = item.data(Qt.UserRole)
        self.topic_input.setText(topic_name)
    
    def browse_replay_bag(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Bag File", "", "*.db3")
        if path:
            self.bag_input.setText(path)
    
    def start_monitoring(self):
        topic = self.topic_input.text().strip()
        fields = [f.strip() for f in self.fields_input.text().split(',') if f.strip()]
        
        if not topic or not fields:
            QMessageBox.warning(self, "Warning", "Please enter topic and fields.")
            return
        
        self.status_label.setText("Status: Monitoring...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.data_buffer.clear()
        self.timestamps.clear()
        
        if self.mode == "live":
            self.start_live_monitoring(topic, fields)
        else:
            self.start_replay_monitoring(topic, fields)
    
    def start_live_monitoring(self, topic, fields):
        """Real-time subscription to ROS2 topic."""
        def on_message(msg):
            timestamp = datetime.now().timestamp()
            self.timestamps.append(timestamp)
            msg_dict = BagReader._msg_to_dict(msg, int(timestamp * 1e9))
            for field in fields:
                if field in msg_dict:
                    self.data_buffer[field].append(msg_dict[field])
            
            if len(self.timestamps) % 10 == 0:  # Update plot every 10 messages
                self.update_live_plot(fields)
        
        self.sub_thread = threading.Thread(
            target=lambda: self._monitor_thread(on_message),
            daemon=True
        )
        self.sub_thread.start()
    
    def _monitor_thread(self, callback):
        try:
            import rclpy
            from rclpy.node import Node
            from rclpy.qos import QoSProfile
            from rosidl_runtime_py.utilities import get_message
            
            topic_name = self.topic_input.text().strip()
            
            # Initialize ROS2 if needed
            if not rclpy.ok():
                rclpy.init()
            
            # Create a temporary node to get topic type
            temp_node = Node('temp_topic_getter')
            topic_types = dict(temp_node.get_topic_names_and_types())
            temp_node.destroy_node()
            
            if topic_name not in topic_types:
                self.status_label.setText(f"Status: Error — Topic '{topic_name}' not found")
                return
            
            # Get the message type
            msg_type_str = topic_types[topic_name][0]
            msg_class = get_message(msg_type_str)
            
            # Create monitor node with proper subscription
            class MonitorNode(Node):
                def __init__(self, topic, msg_type, cb):
                    super().__init__('rt_monitor')
                    self.callback = cb
                    self.subscription = self.create_subscription(
                        msg_type,
                        topic,
                        self._msg_callback,
                        QoSProfile(depth=1)
                    )
                
                def _msg_callback(self, msg):
                    self.callback(msg)
            
            node = MonitorNode(topic_name, msg_class, callback)
            while self.stop_btn.isEnabled():
                rclpy.spin_once(node, timeout_sec=0.1)
            node.destroy_node()
        except Exception as e:
            import traceback
            self.status_label.setText(f"Status: Error — {str(e)}")
            print(f"Monitor error: {e}")
            traceback.print_exc()
    
    def start_replay_monitoring(self, topic, fields):
        """Replay from bag file and plot live."""
        bag_path = self.bag_input.text().strip()
        if not bag_path or not os.path.exists(bag_path):
            QMessageBox.warning(self, "Warning", "Invalid bag file path.")
            return
        
        messages = BagReader.extract_topic_to_dict(bag_path, topic)
        if not messages:
            QMessageBox.warning(self, "Warning", f"No messages found for topic {topic}.")
            return
        
        for msg in messages:
            self.timestamps.append(msg.get("timestamp", 0))
            for field in fields:
                if field in msg:
                    self.data_buffer[field].append(msg[field])
        
        self.update_live_plot(fields)
        self.status_label.setText(f"Status: Replayed {len(messages)} messages")
    
    def update_live_plot(self, fields):
        if not self.timestamps or not self.data_buffer:
            return
        
        try:
            self.rt_figure.clear()
            ax = self.rt_figure.add_subplot(111)
            
            for field in fields:
                if field in self.data_buffer and self.data_buffer[field]:
                    ax.plot(self.timestamps[:len(self.data_buffer[field])], 
                           self.data_buffer[field], label=field, marker='o', markersize=2)
            
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Value")
            ax.legend()
            ax.grid(True, alpha=0.3)
            self.rt_figure.tight_layout()
            self.rt_canvas.draw()
        except Exception as e:
            print(f"Plot error: {e}")
    
    def stop_monitoring(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Status: Stopped")




# ══════════════════════════════════════════════════════════════════
#  UI: TAB 4 — BAG PLAYER
# ══════════════════════════════════════════════════════════════════
class BagPlayerWidget(QWidget):
    """Play/replay ROS2 bag files with controls."""
    
    def __init__(self):
        super().__init__()
        self.player = BagPlayer()
        self.monitor_timer = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # File selection
        file_group = QGroupBox("Select Bag File")
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No bag selected")
        self.file_label.setStyleSheet("color: #888; font-size: 12px;")
        file_browse = QPushButton("Browse Bag File...")
        file_browse.clicked.connect(self.browse_bag)
        file_layout.addWidget(self.file_label, stretch=1)
        file_layout.addWidget(file_browse)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Playback settings
        settings_group = QGroupBox("Playback Settings")
        settings_layout = QGridLayout()
        
        # Playback rate
        settings_layout.addWidget(QLabel("Playback Rate:"), 0, 0)
        self.rate_spinbox = QDoubleSpinBox()
        self.rate_spinbox.setValue(1.0)
        self.rate_spinbox.setMinimum(0.1)
        self.rate_spinbox.setMaximum(10.0)
        self.rate_spinbox.setSingleStep(0.1)
        self.rate_spinbox.setSuffix("x")
        settings_layout.addWidget(self.rate_spinbox, 0, 1)
        
        # Loop option
        self.loop_checkbox = QCheckBox("Loop playback")
        settings_layout.addWidget(self.loop_checkbox, 0, 2)
        
        # Additional ROS2 options
        settings_layout.addWidget(QLabel("Additional args:"), 1, 0)
        self.args_input = QLineEdit()
        self.args_input.setPlaceholderText("e.g., --topics /odom /tf (optional)")
        settings_layout.addWidget(self.args_input, 1, 1, 1, 2)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Playback controls
        control_group = QGroupBox("Playback Control")
        control_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play Bag")
        self.play_btn.setStyleSheet("font-weight: bold; padding: 12px; background-color: #2e9e3e; color: white; border: none; border-radius: 6px;")
        self.play_btn.clicked.connect(self.play_bag)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("font-weight: bold; padding: 12px; background-color: #d32f2f; color: white; border: none; border-radius: 6px;")
        self.stop_btn.clicked.connect(self.stop_bag)
        
        control_layout.addWidget(self.play_btn, 1)
        control_layout.addWidget(self.stop_btn, 1)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Status
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 12px; padding: 10px; background-color: #f5f5f5; border-radius: 4px;")
        layout.addWidget(self.status_label)
        
        # Info box
        info_group = QGroupBox("Info")
        info_layout = QVBoxLayout()
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(200)
        info_text.setText(
            "ℹ Bag Player allows you to replay ROS2 bag files.\n\n"
            "How to use:\n"
            "1. Select a .db3 bag file\n"
            "2. Configure playback speed and options\n"
            "3. Click ▶ Play Bag to start playback\n"
            "4. All topics in the bag will be published as live ROS2 topics\n"
            "5. Use Tab 3 (Real-time Monitor) in 'Live ROS2 Topics' mode to subscribe\n\n"
            "Example workflow:\n"
            "• Play a bag file from this tab\n"
            "• Switch to Tab 3 → Live ROS2 Topics mode\n"
            "• Enter a topic name (e.g., /odometry)\n"
            "• Watch live data visualization while bag plays"
        )
        info_layout.addWidget(info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        self.setLayout(layout)
        
        # Timer to monitor playback status
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_playback_status)
    
    def browse_bag(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select ROS2 Bag File", "", "*.db3")
        if path:
            self.bag_path = path
            self.file_label.setText(Path(path).name)
            self.status_label.setText(f"Status: Ready — {Path(path).name}")
    
    def play_bag(self):
        if not hasattr(self, 'bag_path') or not self.bag_path:
            QMessageBox.warning(self, "Warning", "Please select a bag file first.")
            return
        
        rate = self.rate_spinbox.value()
        loop = self.loop_checkbox.isChecked()
        
        # Show confirmation
        loop_text = " (looping)" if loop else ""
        speed_text = f" at {rate}x speed" if rate != 1.0 else ""
        
        reply = QMessageBox.question(
            self, "Start Playback?",
            f"Play {Path(self.bag_path).name}{speed_text}{loop_text}?\n\n"
            "All topics will be available as live ROS2 topics.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Attempt to play
        success = self.player.play(self.bag_path, rate=rate, loop=loop)
        
        if success:
            self.play_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText(
                f"Status: ▶ Playing {Path(self.bag_path).name} at {rate}x speed"
            )
            self.monitor_timer.start(500)  # Check status every 500ms
        else:
            QMessageBox.critical(
                self, "Error",
                "Failed to start playback.\n\n"
                "Make sure:\n"
                "• ROS2 is installed and sourced\n"
                "• The bag file path is correct\n"
                "• 'ros2 bag play' command is available"
            )
    
    def stop_bag(self):
        self.player.stop()
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Status: Stopped")
        self.monitor_timer.stop()
    
    def check_playback_status(self):
        """Periodically check if playback is still running."""
        if not self.player.is_alive():
            self.play_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("Status: Playback finished")
            self.monitor_timer.stop()


# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
class ROS2DataAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROS2 Data Analyzer")
        self.setGeometry(100, 100, 1400, 800)
        
        # Create tabs
        tabs = QTabWidget()
        
        self.bag_player = BagPlayerWidget()
        self.bag_to_csv = BagToCSVWidget()
        self.csv_plotter = CSVPlotterWidget()
        self.realtime = RealtimeMonitorWidget()
        
        tabs.addTab(self.bag_player, "▶ Bag Player")
        tabs.addTab(self.bag_to_csv, "📦 Bag → CSV")
        tabs.addTab(self.csv_plotter, "📊 CSV Plotter")
        tabs.addTab(self.realtime, "📡 Real-time Monitor")
        
        self.setCentralWidget(tabs)


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ROS2DataAnalyzer()
    window.show()
    sys.exit(app.exec_())
