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

import sys, re
import numpy as np
import pandas as pd
import utm
import rasterio

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog,
    QGraphicsScene, QGraphicsView, QGraphicsPixmapItem,
    QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsItemGroup,
    QPushButton, QLabel, QCheckBox, QColorDialog, QSpinBox, QDoubleSpinBox,
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

    POINT_R = 4.0        # default dot radius (overridden per layer by _sizes spinbox)

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
        # vector layer groups (QGraphicsItemGroup per trajectory)
        self._groups    = {"desired": None, "gps": None, "base": None, "recalc": None}

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
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.view, stretch=1)

        # — toolbar row 1: load + zoom buttons —
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
        for lbl, slot in (("  +  ", self._zoom_in), ("  −  ", self._zoom_out)):
            row1.addWidget(self._btn(lbl, slot))

        # — toolbar row 2: per-layer colour + width + visibility —
        row2 = QHBoxLayout()
        root.addLayout(row2)

        self.chk      = {}
        self._widths  = {}   # key → QSpinBox  (line width)
        self._sizes   = {}   # key → QDoubleSpinBox (point radius)
        self._cbtns   = {}   # key → QPushButton

        for key, lbl in (("desired", "Desired"), ("gps", "GPS"),
                         ("base", "Base"), ("recalc", "Recalc")):
            # colour button
            cb = QPushButton("●  " + lbl)
            cb.setStyleSheet(f"color: {self._colours[key].name()}; font-weight: bold;")
            cb.clicked.connect(lambda _, k=key, b=cb: self._pick_colour(k, b))
            row2.addWidget(cb)
            self._cbtns[key] = cb

            # width spinbox
            spin = QSpinBox()
            spin.setRange(1, 20)
            spin.setValue(2)
            spin.setFixedWidth(48)
            spin.setToolTip(f"{lbl} line width")
            spin.valueChanged.connect(self._redraw_all)
            row2.addWidget(spin)
            self._widths[key] = spin

            # point size spinbox
            pspin = QDoubleSpinBox()
            pspin.setRange(0.1, 30.0)
            pspin.setSingleStep(0.5)
            pspin.setValue(4.0)
            pspin.setDecimals(1)
            pspin.setFixedWidth(58)
            pspin.setToolTip(f"{lbl} point radius")
            pspin.valueChanged.connect(self._redraw_all)
            row2.addWidget(pspin)
            self._sizes[key] = pspin

            # visibility checkbox
            chk = QCheckBox("show")
            chk.setChecked(True)
            chk.stateChanged.connect(lambda state, k=key: self._toggle_layer(k, state))
            row2.addWidget(chk)
            self.chk[key] = chk

            row2.addSpacing(12)

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
        self.imalayer = QGraphicsPixmapItem(QPixmap(qimg))

        self.scene.clear()
        self.scene.addItem(self.imalayer)
        self.view.fitInView(self.imalayer, Qt.KeepAspectRatio)

        # reset data stores
        self._points = {"desired": [], "gps": [], "base": [], "recalc": []}
        self._types  = {"desired": []}
        self._groups = {"desired": None, "gps": None, "base": None, "recalc": None}

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
            types.append(str(row["tipus"]) if "tipus" in row.index else "normal")

        self._points["desired"] = pts
        self._types["desired"]  = types
        self._rebuild_layer("desired")
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
        self._rebuild_layer("gps")
        self._rebuild_layer("base")
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
        self._rebuild_layer("recalc")
        self.status.setText(f"Recalculated: {len(pts)} points loaded "
                            f"from '{lat_col}' / '{lon_col}'.")

    # ── drawing ───────────────────────────────────────────────────────────────

    def _clear_drawings(self):
        for key in list(self._groups):
            self._remove_group(key)
        self._points = {"desired": [], "gps": [], "base": [], "recalc": []}
        self._types  = {"desired": []}
        self.status.setText("Drawings cleared.")

    def _remove_group(self, key):
        g = self._groups.get(key)
        if g is not None:
            self.scene.removeItem(g)
            self._groups[key] = None

    def _toggle_layer(self, key, state):
        g = self._groups.get(key)
        if g is not None:
            g.setVisible(bool(state))

    def _redraw_all(self):
        """Rebuild all vector layers from stored point data."""
        for key in ("desired", "gps", "base", "recalc"):
            self._rebuild_layer(key)

    def _rebuild_layer(self, key):
        """Remove old group for key and build a fresh one from _points[key]."""
        self._remove_group(key)

        pts   = self._points.get(key, [])
        if not pts:
            return

        colour  = self._colours[key]
        lw      = self._widths[key].value()
        r       = self._sizes[key].value()
        visible = self.chk[key].isChecked()
        types   = self._types.get(key, [])

        pen_line = QPen(colour, lw)
        pen_line.setCosmetic(False)          # width scales with zoom
        pen_dot  = QPen(colour.darker(130), 1)
        brush    = QBrush(colour)

        group = QGraphicsItemGroup()

        # — lines —
        for i in range(1, len(pts)):
            x0, y0 = pts[i-1]
            x1, y1 = pts[i]
            line = QGraphicsLineItem(x0, y0, x1, y1)
            line.setPen(pen_line)
            group.addToGroup(line)

        # — dots —
        for i, (col, row) in enumerate(pts):
            t = types[i] if i < len(types) else "normal"
            ellipse = QGraphicsEllipseItem(col - r, row - r, 2*r, 2*r)
            if t == "pas":
                ellipse.setPen(QPen(colour, max(1, lw - 1)))
                ellipse.setBrush(Qt.NoBrush)
            else:
                ellipse.setPen(pen_dot)
                ellipse.setBrush(brush)
            group.addToGroup(ellipse)

        group.setVisible(visible)
        self.scene.addItem(group)
        self._groups[key] = group

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
