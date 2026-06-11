"""
Trajectory Debugger v10
=======================
Plots up to four trajectory layers on a GeoTIFF map for debugging:
  1. Desired trajectory  (AAAA.csv  – UTM x/y/yaw/tipus columns)
  2. GPS track           (experiment CSV – Lat gps / Lon_gps columns)
  3. Base position       (experiment CSV – Lat base / Lon_base columns)
  4. Recalculated base   (separate recalculated CSV)

v10 fixes:
  • Fixed residual/stubborn pixel marks bug where parts of lines or dots 
    remained on screen after hitting clear. Wipes the scene entirely and
    re-extracts a clean background array from the source raster.

v9 fixes:
  • Fixed "ghost points" bug. Items are now tracked the moment they are 
    added to the scene, preventing orphaned drawings if an exception occurs mid-loop.
  • Bulletproof _clear_drawings: explicitly sweeps the scene and removes all
    vector graphics to guarantee no leftover artifacts.

v8 additions:
  • Added fuzzy column matching and NaN-handling in _load_gps.

v7 additions:
  • L / P checkboxes per layer — toggle lines and points independently
  • ↑ button per layer — raise to front (z-order control)
  • Adaptive point radius (down to 0.01)
"""

import sys, re, traceback
import numpy as np
import pandas as pd
import utm
import rasterio

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog,
    QGraphicsScene, QGraphicsView, QGraphicsPixmapItem,
    QGraphicsLineItem, QGraphicsEllipseItem,
    QPushButton, QLabel, QCheckBox, QColorDialog, QSpinBox, QDoubleSpinBox,
    QHBoxLayout, QVBoxLayout, QSizePolicy
)
from PyQt5.QtCore  import Qt
from PyQt5.QtGui   import (
    QPixmap, QImage, QPainter, QPen, QBrush, QColor
)


# ── helpers ───────────────────────────────────────────────────────────────────

def latlon_to_pixel(img, lat, lon):
    e, n, _, _ = utm.from_latlon(lat, lon)
    row, col = img.index(e, n)
    return float(col), float(row)

def utm_to_pixel(img, x, y):
    row, col = img.index(x, y)
    return float(col), float(row)


# ── adaptive step spinbox ─────────────────────────────────────────────────────

class AdaptiveSpinBox(QDoubleSpinBox):
    """Adaptive step sizes:
       value < 0.1  →  step 0.01
       value < 1.0  →  step 0.1
       value ≥ 1.0  →  step 0.5
    Going DOWN uses ≤ at boundaries so 0.10→0.09 and 1.0→0.9 use the
    smaller step (avoids overshooting the previous tier).
    """
    def stepBy(self, steps):
        v = self.value()
        if steps > 0:
            step = 0.01 if v < 0.1 else 0.1 if v < 1.0 else 0.5
        else:
            step = 0.01 if v <= 0.1 else 0.1 if v <= 1.0 else 0.5
        self.setValue(round(v + steps * step, 2))


# ── main window ───────────────────────────────────────────────────────────────

LAYERS = ("desired", "gps", "base", "recalc")

class TrajectoryDebugger(QMainWindow):

    _colours = {
        "desired": QColor("#e74c3c"),
        "gps":     QColor("#2ecc71"),
        "base":    QColor("#3498db"),
        "recalc":  QColor("#f39c12"),
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trajectory Debugger v10")
        self.resize(1280, 800)

        self.img     = None
        self._points = {k: [] for k in LAYERS}
        self._types  = {"desired": []}
        self._items  = {k: [] for k in LAYERS}   # list of QGraphicsItem per layer
        
        # z-order: higher draws on top. Map (pixmap) stays at 0; layers start at 1+.
        self._zvalues = {k: i + 1 for i, k in enumerate(LAYERS)}

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        self.scene = QGraphicsScene(self)
        self.view  = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.view, stretch=1)

        # row 1: load + zoom
        row1 = QHBoxLayout()
        root.addLayout(row1)
        self.btn_map    = self._btn("Load Map",     self._load_map)
        self.btn_des    = self._btn("Load Desired", self._load_desired, enabled=False)
        self.btn_gps    = self._btn("Load GPS",     self._load_gps,     enabled=False)
        self.btn_recalc = self._btn("Load Recalc",  self._load_recalc,  enabled=False)
        self.btn_clear  = self._btn("Clear",        self._clear_drawings, enabled=False)
        for b in (self.btn_map, self.btn_des, self.btn_gps,
                  self.btn_recalc, self.btn_clear):
            row1.addWidget(b)
        row1.addStretch()
        for lbl, slot in (("  +  ", self._zoom_in), ("  −  ", self._zoom_out)):
            row1.addWidget(self._btn(lbl, slot))

        # row 2: per-layer controls
        row2 = QHBoxLayout()
        root.addLayout(row2)

        self._lines_chk  = {}
        self._points_chk = {}
        self._raise_btn  = {}
        self._widths = {}
        self._sizes  = {}
        self._cbtns  = {}

        labels = {"desired": "Desired", "gps": "GPS", "base": "Base", "recalc": "Recalc"}
        for key in LAYERS:
            lbl = labels[key]

            cb = QPushButton("●  " + lbl)
            cb.setStyleSheet(f"color: {self._colours[key].name()}; font-weight: bold;")
            cb.clicked.connect(lambda _, k=key, b=cb: self._pick_colour(k, b))
            row2.addWidget(cb)
            self._cbtns[key] = cb

            spin = QSpinBox()
            spin.setRange(1, 20)
            spin.setFixedWidth(48)
            spin.setToolTip(f"{lbl} line width")
            spin.blockSignals(True); spin.setValue(2); spin.blockSignals(False)
            spin.valueChanged.connect(self._redraw_all)
            row2.addWidget(spin)
            self._widths[key] = spin

            pspin = AdaptiveSpinBox()
            pspin.setRange(0.01, 30.0)
            pspin.setDecimals(2)
            pspin.setFixedWidth(70)
            pspin.setToolTip(f"{lbl} point radius (steps: 0.01 < 0.1 < 1.0 < 0.5)")
            pspin.blockSignals(True); pspin.setValue(4.0); pspin.blockSignals(False)
            pspin.valueChanged.connect(self._redraw_all)
            row2.addWidget(pspin)
            self._sizes[key] = pspin

            lchk = QCheckBox("L")
            lchk.setChecked(True)
            lchk.setToolTip(f"Show {lbl} lines")
            lchk.stateChanged.connect(lambda _, k=key: self._apply_visibility(k))
            row2.addWidget(lchk)
            self._lines_chk[key] = lchk

            pchk = QCheckBox("P")
            pchk.setChecked(True)
            pchk.setToolTip(f"Show {lbl} points")
            pchk.stateChanged.connect(lambda _, k=key: self._apply_visibility(k))
            row2.addWidget(pchk)
            self._points_chk[key] = pchk

            rb = QPushButton("↑")
            rb.setFixedWidth(26)
            rb.setToolTip(f"Bring {lbl} to front")
            rb.clicked.connect(lambda _, k=key: self._raise_to_front(k))
            row2.addWidget(rb)
            self._raise_btn[key] = rb

            row2.addSpacing(10)

        row2.addStretch()
        self.status = QLabel("Load a map to start.")
        row2.addWidget(self.status)

    @staticmethod
    def _btn(label, slot, enabled=True):
        b = QPushButton(label)
        b.setEnabled(enabled)
        b.clicked.connect(slot)
        return b

    def _pick_colour(self, key, button):
        col = QColorDialog.getColor(self._colours[key], self, f"Colour for {key}")
        if col.isValid():
            self._colours[key] = col
            button.setStyleSheet(f"color: {col.name()}; font-weight: bold;")
            self._rebuild_layer(key)

    # ── map loading ───────────────────────────────────────────────────────────

    def _load_map(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open GeoTIFF", ".", "GeoTIFF (*.tif *.tiff);;All (*)")
        if not path:
            return
        self.img = rasterio.open(path)
        data     = np.transpose(self.img.read(), (1, 2, 0)).copy()
        qimg     = QImage(data, data.shape[1], data.shape[0], QImage.Format_RGB888)
        imalayer = QGraphicsPixmapItem(QPixmap(qimg))
        self.scene.clear()
        self.scene.addItem(imalayer)
        self.view.fitInView(imalayer, Qt.KeepAspectRatio)
        self._points = {k: [] for k in LAYERS}
        self._types  = {"desired": []}
        self._items  = {k: [] for k in LAYERS}
        for b in (self.btn_des, self.btn_gps, self.btn_recalc, self.btn_clear):
            b.setEnabled(True)
        self.status.setText(
            f"Map loaded: {self.img.width}×{self.img.height}px  |  CRS: {self.img.crs}")

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
        self.status.setText(f"Desired: {len(pts)} points loaded.")
        self._rebuild_layer("desired")

    def _load_gps(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Experiment CSV", ".", "CSV (*.csv);;All (*)")
        if not path or self.img is None:
            return
            
        try:
            df = pd.read_csv(path)
        except Exception as e:
            self.status.setText(f"Error reading CSV: {e}")
            return
            
        lat_gps_col = next((c for c in df.columns if "lat" in c.lower() and "gps" in c.lower()), None)
        lon_gps_col = next((c for c in df.columns if "lon" in c.lower() and "gps" in c.lower()), None)
        lat_base_col = next((c for c in df.columns if "lat" in c.lower() and "base" in c.lower()), None)
        lon_base_col = next((c for c in df.columns if "lon" in c.lower() and "base" in c.lower()), None)

        if not lat_gps_col: lat_gps_col = next((c for c in df.columns if c.lower() in ["lat", "latitude"]), None)
        if not lon_gps_col: lon_gps_col = next((c for c in df.columns if c.lower() in ["lon", "longitude"]), None)

        gps_pts, base_pts = [], []
        
        for _, row in df.iterrows():
            if lat_gps_col and lon_gps_col:
                try:
                    lat_g, lon_g = row[lat_gps_col], row[lon_gps_col]
                    if pd.notna(lat_g) and pd.notna(lon_g):
                        col, r = latlon_to_pixel(self.img, float(lat_g), float(lon_g))
                        gps_pts.append((col, r))
                except Exception:
                    pass
                    
            if lat_base_col and lon_base_col:
                try:
                    lat_b, lon_b = row[lat_base_col], row[lon_base_col]
                    if pd.notna(lat_b) and pd.notna(lon_b):
                        lat_b, lon_b = float(lat_b), float(lon_b)
                        if lat_b > 1e6:
                            col, r = utm_to_pixel(self.img, lon_b, lat_b)
                        else:
                            col, r = latlon_to_pixel(self.img, lat_b, lon_b)
                        base_pts.append((col, r))
                except Exception:
                    pass

        self._points["gps"]  = gps_pts
        self._points["base"] = base_pts
        
        warnings = []
        if not lat_gps_col or not lon_gps_col: warnings.append("Missing GPS cols")
        if not lat_base_col or not lon_base_col: warnings.append("Missing Base cols")
        
        msg = f"GPS: {len(gps_pts)} pts | Base: {len(base_pts)} pts loaded."
        if warnings:
            msg += f" (Warning: {', '.join(warnings)})"
            
        self.status.setText(msg)
        self._rebuild_layer("gps")
        self._rebuild_layer("base")

    def _load_recalc(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Recalculated CSV", ".", "CSV (*.csv);;All (*)")
        if not path or self.img is None:
            return
        df = pd.read_csv(path)
        lat_col = next((c for c in df.columns if "lat_base_new" in c.lower()
                        or "lat_recalc" in c.lower()), None)
        lon_col = next((c for c in df.columns if "lon_base_new" in c.lower()
                        or "lon_recalc" in c.lower()), None)
        if lat_col is None or lon_col is None:
            self.status.setText("ERROR: expected 'Lat_base_new' / 'Lon_base_new' cols.")
            return
        pts = []
        for _, row in df.iterrows():
            try:
                col, r = latlon_to_pixel(self.img, row[lat_col], row[lon_col])
                pts.append((col, r))
            except Exception:
                pass
        self._points["recalc"] = pts
        self.status.setText(f"Recalculated: {len(pts)} pts from '{lat_col}' / '{lon_col}'.")
        self._rebuild_layer("recalc")

    # ── drawing ───────────────────────────────────────────────────────────────

    def _clear_drawings(self):
        """Wipes the entire canvas scene completely, then pulls a fresh, raw 
        pixel array straight from the background GeoTIFF handle to avoid residual marks.
        """
        self.scene.clear()

        if self.img is not None:
            try:
                data = np.transpose(self.img.read(), (1, 2, 0)).copy()
                qimg = QImage(data, data.shape[1], data.shape[0], QImage.Format_RGB888)
                imalayer = QGraphicsPixmapItem(QPixmap(qimg))
                self.scene.addItem(imalayer)
            except Exception as e:
                print(f"Error restoring clean map background: {e}")
                    
        self._points = {k: [] for k in LAYERS}
        self._types  = {"desired": []}
        self._items  = {k: [] for k in LAYERS}
        self.status.setText("Drawings cleared.")

    def _remove_items(self, key):
        """Removes specifically tracked items for a single layer."""
        for item in self._items.get(key, []):
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self._items[key] = []

    def _apply_visibility(self, key):
        show_lines  = self._lines_chk[key].isChecked()
        show_points = self._points_chk[key].isChecked()
        for item in self._items.get(key, []):
            if isinstance(item, QGraphicsLineItem):
                item.setVisible(show_lines)
            else:
                item.setVisible(show_points)

    def _raise_to_front(self, key):
        max_z = max(self._zvalues.values())
        if self._zvalues[key] < max_z:
            self._zvalues[key] = max_z + 1
        for item in self._items.get(key, []):
            item.setZValue(self._zvalues[key])
        self.status.setText(f"'{key}' brought to front (z={self._zvalues[key]}).")

    def _redraw_all(self):
        if self.img is None:
            return
        for key in LAYERS:
            self._rebuild_layer(key)

    def _rebuild_layer(self, key):
        if self.img is None:
            return
        self._remove_items(key)

        pts = self._points.get(key, [])
        if not pts:
            return

        try:
            colour      = self._colours[key]
            lw          = float(self._widths[key].value())
            r           = float(self._sizes[key].value())
            show_lines  = self._lines_chk[key].isChecked()
            show_points = self._points_chk[key].isChecked()
            z           = self._zvalues[key]
            types       = self._types.get(key, [])

            pen_line = QPen(colour, lw)
            pen_line.setCosmetic(False)
            pen_dot  = QPen(colour.darker(130), 1.0)
            brush    = QBrush(colour)

            # Important fix: ensure tracked list is clean before we start appending
            self._items[key] = []

            # — lines —
            for i in range(1, len(pts)):
                x0, y0 = float(pts[i - 1][0]), float(pts[i - 1][1])
                x1, y1 = float(pts[i][0]),     float(pts[i][1])
                line = QGraphicsLineItem(x0, y0, x1, y1)
                line.setPen(pen_line)
                line.setVisible(show_lines)
                line.setZValue(z)
                self.scene.addItem(line)
                # Appended instantly to avoid ghosting on failure
                self._items[key].append(line)

            # — dots —
            for i, (col, row) in enumerate(pts):
                cx, cy = float(col), float(row)
                t = types[i] if i < len(types) else "normal"
                ellipse = QGraphicsEllipseItem(cx - r, cy - r, 2.0 * r, 2.0 * r)
                if t == "pas":
                    ellipse.setPen(QPen(colour, max(0.5, lw - 1.0)))
                    ellipse.setBrush(QBrush(Qt.NoBrush))
                else:
                    ellipse.setPen(pen_dot)
                    ellipse.setBrush(brush)
                ellipse.setVisible(show_points)
                ellipse.setZValue(z)
                self.scene.addItem(ellipse)
                # Appended instantly to avoid ghosting on failure
                self._items[key].append(ellipse)

        except Exception as e:
            traceback.print_exc()
            self.status.setText(f"ERROR drawing '{key}': {e}")

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