import os

from qgis.PyQt.QtWidgets import (QAction, QFileDialog, QMessageBox,
                                   QDialog, QVBoxLayout, QLabel, QPushButton,
                                   QProgressBar, QLineEdit, QStackedWidget, QWidget)
from qgis.PyQt.QtCore import QThread, pyqtSignal, QSettings, QMetaType
from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsProject, QgsCoordinateReferenceSystem,
    QgsField, QgsRasterLayer
)
from pyproj import Transformer
import pandas as pd

# ─── Константы ────────────────────────────────────────────────────────────────
CRS_SOURCE = "EPSG:7683"    # ГСК-2011
CRS_GK_BASE = 20900            # база EPSG для зон Гаусса-Крюгера
GOOGLE_SATELLITE_URL = (
    "type=xyz&url=https://mt1.google.com/vt/lyrs%3Ds%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D"
    "&zmax=20&zmin=0"
)


# ─── Геодезия ─────────────────────────────────────────────────────────────────

def dms_to_dd(d, m, s):
    return float(d) + float(m) / 60 + float(str(s).replace(',', '.')) / 3600


def parse_excel(path):
    df = pd.read_excel(path, header=None)
    if df.shape[1] < 7:
        raise ValueError(f"Ожидается 7 колонок, найдено {df.shape[1]}")
    points = []
    for _, row in df.iterrows():
        try:
            points.append({
                "id":  int(row[0]),
                "lat": dms_to_dd(row[1], row[2], row[3]),
                "lon": dms_to_dd(row[4], row[5], row[6]),
            })
        except (ValueError, TypeError):
            continue
    if not points:
        raise ValueError("Не удалось прочитать координаты из файла")
    return sorted(points, key=lambda x: x["id"])


def convert_to_gk(points):
    avg_lon = sum(p["lon"] for p in points) / len(points)
    zone = int(avg_lon / 6) + 1
    transformer = Transformer.from_crs(CRS_SOURCE, f"EPSG:{CRS_GK_BASE + zone}", always_xy=True)
    for p in points:
        e, n = transformer.transform(p["lon"], p["lat"])
        p["x"] = round(n, 3)
        p["y"] = round(e, 3)
    return points, zone


# ─── Воркер ───────────────────────────────────────────────────────────────────

class ConvertWorker(QThread):
    finished = pyqtSignal(list, int)
    error    = pyqtSignal(str)

    def __init__(self, xlsx_path):
        super().__init__()
        self.xlsx_path = xlsx_path

    def run(self):
        try:
            points = parse_excel(self.xlsx_path)
            points, zone = convert_to_gk(points)
            self.finished.emit(points, zone)
        except Exception as e:
            self.error.emit(str(e))


# ─── Диалог ───────────────────────────────────────────────────────────────────

SETTINGS_KEY = "lazygeo/last_dir"


class LazyGeoDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface     = iface
        self.worker    = None
        self.xlsx_path = None
        self.settings  = QSettings()
        self.setWindowTitle("LazyGeo")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title = QLabel("LazyGeo")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1F4E79;")
        layout.addWidget(title)

        sub = QLabel("Excel координаты ГМС → карта QGIS")
        sub.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(sub)

        # Кнопка выбора файла
        self.btn_excel = QPushButton("📂  Выбрать файл")
        self.btn_excel.setStyleSheet(self._btn_style("#1F4E79", size=13))
        self.btn_excel.clicked.connect(self._pick_excel)
        layout.addWidget(self.btn_excel)

        self.lbl_excel = QLabel("")
        self.lbl_excel.setStyleSheet("color: #155724; font-size: 10px; padding-left: 4px;")
        layout.addWidget(self.lbl_excel)

        # Поле названия — скрыто до выбора файла
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название слоя")
        self.name_input.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        self.name_input.hide()
        layout.addWidget(self.name_input)

        # Stacked: кнопка запуска ↔ спиннер
        self.stack = QStackedWidget()
        self.stack.hide()

        # Страница 0 — кнопка запуска
        run_widget = QWidget()
        run_layout = QVBoxLayout(run_widget)
        run_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_run = QPushButton("▶  Запустить")
        self.btn_run.setStyleSheet(self._btn_style("#2E7D32", size=13))
        self.btn_run.clicked.connect(self._run)
        run_layout.addWidget(self.btn_run)

        # Страница 1 — спиннер
        spin_widget = QWidget()
        spin_layout = QVBoxLayout(spin_widget)
        spin_layout.setContentsMargins(0, 0, 0, 0)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        spin_layout.addWidget(self.progress)

        self.stack.addWidget(run_widget)   # индекс 0
        self.stack.addWidget(spin_widget)  # индекс 1
        layout.addWidget(self.stack)

        self.setLayout(layout)

    def _btn_style(self, color, size=12):
        return f"""
            QPushButton {{
                background: {color}; color: white;
                border: none; padding: 9px;
                border-radius: 4px; font-size: {size}px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
            QPushButton:disabled {{ background: #aaa; }}
        """

    def _pick_excel(self):
        last_dir = self.settings.value(SETTINGS_KEY, "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбери Excel с координатами", last_dir,
            "Excel файлы (*.xlsx *.xls)")
        if path:
            self.xlsx_path = path
            self.settings.setValue(SETTINGS_KEY, os.path.dirname(path))
            self.lbl_excel.setText(os.path.basename(path))
            name = os.path.splitext(os.path.basename(path))[0]
            self.name_input.setText(name)
            self.name_input.show()
            self.stack.show()
            self.stack.setCurrentIndex(0)

    def _run(self):
        self.layer_name = self.name_input.text().strip() or "лицензия"
        self.stack.setCurrentIndex(1)
        self.btn_excel.setEnabled(False)

        self.worker = ConvertWorker(self.xlsx_path)
        self.worker.finished.connect(self._on_success)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_success(self, points, zone):
        epsg = CRS_GK_BASE + zone
        crs  = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")

        # Создаём проект и подложку только если проект пустой
        if not QgsProject.instance().mapLayers():
            basemap = QgsRasterLayer(GOOGLE_SATELLITE_URL, "Google Satellite", "wms")
            if basemap.isValid():
                QgsProject.instance().addMapLayer(basemap)
            QgsProject.instance().setCrs(crs)

        # Слой точек
        pt_layer = QgsVectorLayer("Point", f"points_{self.layer_name}", "memory")
        pt_layer.setCrs(crs)
        pr = pt_layer.dataProvider()
        pr.addAttributes([
            QgsField("id", QMetaType.Int),
            QgsField("X",  QMetaType.Double),
            QgsField("Y",  QMetaType.Double),
        ])
        pt_layer.updateFields()

        pts_geom = []
        for p in points:
            f = QgsFeature()
            pt = QgsPointXY(p["y"], p["x"])
            f.setGeometry(QgsGeometry.fromPointXY(pt))
            f.setAttributes([p["id"], p["x"], p["y"]])
            pr.addFeature(f)
            pts_geom.append(pt)

        QgsProject.instance().addMapLayer(pt_layer)

        # Полигон
        poly_layer = QgsVectorLayer("Polygon", self.layer_name, "memory")
        poly_layer.setCrs(crs)
        pr2 = poly_layer.dataProvider()
        pr2.addAttributes([QgsField("name", QMetaType.QString)])
        poly_layer.updateFields()

        poly_f = QgsFeature()
        poly_f.setGeometry(QgsGeometry.fromPolygonXY([pts_geom + [pts_geom[0]]]))
        poly_f.setAttributes([self.layer_name])
        pr2.addFeature(poly_f)

        QgsProject.instance().addMapLayer(poly_layer)

        # Зум
        self.iface.setActiveLayer(poly_layer)
        self.iface.zoomToActiveLayer()

        # Уведомление и закрытие
        self.iface.messageBar().pushSuccess(
            "LazyGeo",
            f"Готово — {len(points)} точек, зона ГК {zone} (EPSG:{epsg})"
        )
        self.close()

    def _on_error(self, error):
        self._restore_ui()
        QMessageBox.critical(self, "LazyGeo", f"Ошибка:\n{error}")

    def _restore_ui(self):
        self.stack.setCurrentIndex(0)
        self.btn_excel.setEnabled(True)


# ─── Плагин ───────────────────────────────────────────────────────────────────

class LazyGeoPlugin:
    def __init__(self, iface):
        self.iface  = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction("LazyGeo", self.iface.mainWindow())
        self.action.setToolTip("Excel координаты → карта QGIS")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("LazyGeo", self.action)

    def unload(self):
        self.iface.removePluginMenu("LazyGeo", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        self.dialog = LazyGeoDialog(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()