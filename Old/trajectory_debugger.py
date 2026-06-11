"""
Trajectory Debugger
====================
Plots three trajectory layers on a GeoTIFF map for debugging:
  1. Desired trajectory  (AAAA.csv  – UTM x/y columns)
  2. GPS track           (experiment CSV – Lat gps / Lon_gps columns)
  3. Recalculated base   (experiment CSV – Lat_base / Lon_base columns,
                          OR a separately loaded recalculated CSV)

Usage:
  python trajectory_debugger.py

Controls:
  • Load Map      – open the .tif ortophoto
  • Load Desired  – open AAAA.csv (UTM x, y, yaw, tipus)
  • Load GPS      – open experiment CSV (lat/lon GPS + base columns)
  • Load Recalc   – open an extra CSV with recalculated lat/lon columns
  • Colour buttons– pick line/point colour for each layer
  • + / -         – zoom
  • Arrow buttons – pan
  • Clear         – wipe all drawn layers (map stays)
"""

import sys, re, math
import numpy as np
import pandas as pd
import utm
import rasterio

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog,
    QGraphicsScene, QGraphicsView, QGraphicsPixmapItem,
    QPushButton, QLabel, QCheckBox, QColorDialog,
    QHBoxLayout, QVBoxLayout, QSizePolicy
)
from PyQt5.QtCore  import Qt, QPointF, QRectF
from PyQt5.QtGui   import (
    QPixmap, QImage, QPainter, QPen, QBrush, QColor, QFont
)


# ── helpers ──────────────────────────────────────────────────────────────────

def extract_vector3_x(s: str) -> float:
    """Return the x field from a geometry_msgs Vector3 string."""
    m = re.search(r"x=([-\d.eE+]+)", str(s))
    return float(m.group(1)) if m else float("nan")


def latlon_to_pixel(img, lat: float, lon: float):
    """Convert WGS84 lat/lon → pixel (col, row) using the open rasterio image."""
    e, n, _, _ = utm.from_latlon(lat, lon)
    row, col = img.index(e, n)
    return col, row


def utm_to_pixel(img, x: float, y: float):
    """Convert UTM easting/northing → pixel (col, row)."""
    row, col = img.index(x, y)
    return col, row


# ── main window ──────────────────────────────────────────────────────────────

class TrajectoryDebugger(QMainWindow):

    POINT_R = 4          # dot radius in pixels
    LINE_W  = 2          # line width in pixels

    # default colours
    _colours = {
        "desired": QColor("#e74c3c"),    # red
        "gps":     QColor("#2ecc71"),    # green
        "base":    QColor("#3498db"),    # blue
        "recalc":  QColor("#f39c12"),    # orange
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trajectory Debugger")
        self.resize(1280, 800)

        self.img        = None   # rasterio dataset
        self.imalayer   = None   # QGraphicsPixmapItem – background
        self.drawlayer  = None   # QGraphicsPixmapItem – drawings

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        # — map view —
        self.scene = QGraphicsScene(self)
        self.view  = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setRenderHint(QPainter.Antialiasing, False)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.view, stretch=1)

        # — toolbar row 1: load buttons + zoom/pan —
        row1 = QHBoxLayout()
        root.addLayout(row1)

        self.btn_map    = self._btn("Load Map",     self._load_map)
        self.btn_des    = self._btn("Load Desired", self._load_desired,  enabled=False)
        self.btn_gps    = self._btn("Load GPS",     self._load_gps,      enabled=False)
        self.btn_recalc = self._btn("Load Recalc",  self._load_recalc,   enabled=False)
        self.btn_clear  = self._btn("Clear",        self._clear_drawings, enabled=False)

        for b in (self.btn_map, self.btn_des, self.btn_gps,
                  self.btn_recalc, self.btn_clear):
            row1.addWidget(b)

        row1.addStretch()

        for lbl, key in (("●  Desired", "desired"), ("●  GPS", "gps"),
                         ("●  Base",    "base"),    ("●  Recalc", "recalc")):
            cb = QPushButton(lbl)
            cb.setStyleSheet(f"color: {self._colours[key].name()}; font-weight: bold;")
            cb.clicked.connect(lambda _, k=key, b=cb: self._pick_colour(k, b))
            row1.addWidget(cb)
            setattr(self, f"_cbtn_{key}", cb)

        row1.addStretch()

        for lbl, slot in (("  +  ", self._zoom_in), ("  −  ", self._zoom_out)):
            row1.addWidget(self._btn(lbl, slot))

        # — toolbar row 2: visibility toggles + status —
        row2 = QHBoxLayout()
        root.addLayout(row2)

        self.chk = {}
        for key, lbl in (("desired", "Desired"), ("gps", "GPS track"),
                         ("base",    "Base"),    ("recalc", "Recalculated")):
            c = QCheckBox(lbl)
            c.setChecked(True)
            c.stateChanged.connect(lambda state, k=key: self._toggle_layer(k, state))
            row2.addWidget(c)
            self.chk[key] = c

        row2.addStretch()
        self.status = QLabel("Load a map to start.")
        row2.addWidget(self.status)

    @staticmethod
    def _btn(label, slot, enabled=True):
        b = QPushButton(label)
        b.setEnabled(enabled)
        b.clicked.connect(slot)
        return b

    # ── colour picker ─────────────────────────────────────────────────────────

    def _pick_colour(self, key, button):
        col = QColorDialog.getColor(self._colours[key], self, f"Colour for {key}")
        if col.isValid():
            self._colours[key] = col
            button.setStyleSheet(f"color: {col.name()}; font-weight: bold;")
            self._redraw_all()

    # ── map loading ───────────────────────────────────────────────────────────

    def _load_map(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open GeoTIFF", ".", "GeoTIFF (*.tif *.tiff);;All (*)")
        if not path:
            return

        self.img = rasterio.open(path)
        data = self.img.read()                        # (bands, H, W)
        data = np.transpose(data, (1, 2, 0)).copy()   # (H, W, bands)

        qimg = QImage(data, data.shape[1], data.shape[0], QImage.Format_RGB888)
        self.imalayer  = QGraphicsPixmapItem(QPixmap(qimg))
        self.drawlayer = QGraphicsPixmapItem(QPixmap(qimg.size()))
        pixmap = self.drawlayer.pixmap()
        pixmap.fill(Qt.transparent)
        self.drawlayer.setPixmap(pixmap)

        self.scene.clear()
        self.scene.addItem(self.imalayer)
        self.scene.addItem(self.drawlayer)
        self.view.fitInView(self.imalayer, Qt.KeepAspectRatio)

        # internal layer stores: list of (col, row) per layer
        self._points = {"desired": [], "gps": [], "base": [], "recalc": []}
        self._types  = {"desired": []}   # for desired: 'normal'/'pas' markers

        for b in (self.btn_des, self.btn_gps, self.btn_recalc, self.btn_clear):
            b.setEnabled(True)

        self.status.setText(f"Map loaded: {self.img.width}×{self.img.height}px  |  CRS: {self.img.crs}")

    # ── data loading ──────────────────────────────────────────────────────────

    def _load_desired(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Desired Trajectory CSV", ".", "CSV (*.csv);;All (*)")
        if not path or self.img is None:
            return

        df = pd.read_csv(path)
        pts, types = [], []
        for _, row in df.iterrows():
            col, r = utm_to_pixel(self.img, row["x"], row["y"])
            pts.append((col, r))
            types.append(row.get("tipus", "normal"))

        self._points["desired"] = pts
        self._types["desired"]  = types
        self._redraw_all()
        self.status.setText(f"Desired: {len(pts)} points loaded.")

    def _load_gps(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Experiment CSV", ".", "CSV (*.csv);;All (*)")
        if not path or self.img is None:
            return

        df = pd.read_csv(path)
        gps_pts, base_pts = [], []

        for _, row in df.iterrows():
            # GPS track
            try:
                col, r = latlon_to_pixel(self.img, row["Lat gps"], row["Lon_gps"])
                gps_pts.append((col, r))
            except Exception:
                pass

            # Base position (raw columns – may be in UTM projection or lat/lon)
            try:
                lat_b = row["Lat base"]
                lon_b = row["Lon_base"]
                # If Lat_base looks like a UTM northing (> 1e6) use it directly
                if lat_b > 1e6:
                    col, r = utm_to_pixel(self.img, lon_b, lat_b)
                else:
                    col, r = latlon_to_pixel(self.img, lat_b, lon_b)
                base_pts.append((col, r))
            except Exception:
                pass

        self._points["gps"]  = gps_pts
        self._points["base"] = base_pts
        self._redraw_all()
        self.status.setText(
            f"GPS: {len(gps_pts)} pts  |  Base: {len(base_pts)} pts loaded.")

    def _load_recalc(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Recalculated CSV", ".", "CSV (*.csv);;All (*)")
        if not path or self.img is None:
            return

        df = pd.read_csv(path)
        pts = []

        # Auto-detect recalculated lat/lon columns
        lat_col = next((c for c in df.columns if "lat_base_new" in c.lower() or
                        "lat_recalc" in c.lower()), None)
        lon_col = next((c for c in df.columns if "lon_base_new" in c.lower() or
                        "lon_recalc" in c.lower()), None)

        if lat_col is None or lon_col is None:
            self.status.setText("ERROR: could not find recalc lat/lon columns. "
                                "Expected 'Lat_base_new' / 'Lon_base_new'.")
            return

        for _, row in df.iterrows():
            try:
                col, r = latlon_to_pixel(self.img, row[lat_col], row[lon_col])
                pts.append((col, r))
            except Exception:
                pass

        self._points["recalc"] = pts
        self._redraw_all()
        self.status.setText(f"Recalculated: {len(pts)} points loaded "
                            f"from '{lat_col}' / '{lon_col}'.")

    # ── drawing ───────────────────────────────────────────────────────────────

    def _clear_drawings(self):
        if self.drawlayer is None:
            return
        pixmap = self.drawlayer.pixmap()
        pixmap.fill(Qt.transparent)
        self.drawlayer.setPixmap(pixmap)
        self._points = {"desired": [], "gps": [], "base": [], "recalc": []}
        self._types  = {"desired": []}
        self.status.setText("Drawings cleared.")

    def _toggle_layer(self, key, state):
        self._redraw_all()

    def _redraw_all(self):
        if self.drawlayer is None:
            return

        pixmap = self.drawlayer.pixmap()
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        r = self.POINT_R
        ft = QFont("Helvetica", 7)
        painter.setFont(ft)

        for key in ("desired", "gps", "base", "recalc"):
            if not self.chk[key].isChecked():
                continue
            pts = self._points.get(key, [])
            if not pts:
                continue

            colour = self._colours[key]
            pen_line  = QPen(colour, self.LINE_W)
            pen_dot   = QPen(colour.darker(130), 1)
            brush_dot = QBrush(colour)

            # — lines —
            painter.setPen(pen_line)
            for i in range(1, len(pts)):
                painter.drawLine(pts[i-1][0], pts[i-1][1], pts[i][0], pts[i][1])

            # — dots —
            types = self._types.get(key, [None] * len(pts))
            for i, (col, row) in enumerate(pts):
                # For desired trajectory: distinguish 'pas' (hollow) from 'normal' (filled)
                t = types[i] if i < len(types) else "normal"
                if t == "pas":
                    painter.setPen(pen_line)
                    painter.setBrush(Qt.NoBrush)
                else:
                    painter.setPen(pen_dot)
                    painter.setBrush(brush_dot)
                painter.drawEllipse(col - r, row - r, 2*r, 2*r)

            # — index label on first point —
            painter.setPen(QPen(colour.darker(150)))
            if pts:
                painter.drawText(pts[0][0] + r + 2, pts[0][1] - r,
                                 key.capitalize())

        painter.end()
        self.drawlayer.setPixmap(pixmap)

    # ── zoom ──────────────────────────────────────────────────────────────────

    def _zoom_in(self):
        self.view.scale(1.3, 1.3)

    def _zoom_out(self):
        self.view.scale(1 / 1.3, 1 / 1.3)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self._zoom_in()
        else:
            self._zoom_out()


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TrajectoryDebugger()
    win.show()
    sys.exit(app.exec_())
