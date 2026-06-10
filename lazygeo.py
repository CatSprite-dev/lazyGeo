import os
from qgis.PyQt.QtWidgets import (QAction, QFileDialog, QMessageBox,
                                   QDialog, QVBoxLayout, QLabel, QPushButton,
                                   QProgressBar)
from qgis.PyQt.QtCore import QThread, pyqtSignal, QSettings
from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsProject, QgsCoordinateReferenceSystem,
    QgsField, QgsVectorFileWriter, QgsCoordinateTransformContext,
    QgsRasterLayer
)
from qgis.PyQt.QtCore import QVariant
from pyproj import Transformer

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# ─── Геодезия ─────────────────────────────────────────────────────────────────

def dms_to_dd(d, m, s):
    return float(d) + float(m) / 60 + float(str(s).replace(',', '.')) / 3600


def parse_excel(path):
    if not HAS_PANDAS:
        raise ImportError("Установи pandas и openpyxl")
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
    transformer = Transformer.from_crs("EPSG:7683", f"EPSG:{20900 + zone}", always_xy=True)
    for p in points:
        e, n = transformer.transform(p["lon"], p["lat"])
        p["x"] = round(n, 3)
        p["y"] = round(e, 3)
    return points, zone


# ─── Воркер ───────────────────────────────────────────────────────────────────

class ConvertWorker(QThread):
    finished = pyqtSignal(list, int, str)
    error    = pyqtSignal(str)

    def __init__(self, xlsx_path):
        super().__init__()
        self.xlsx_path = xlsx_path

    def run(self):
        try:
            points = parse_excel(self.xlsx_path)
            points, zone = convert_to_gk(points)
            out_dir = os.path.dirname(self.xlsx_path)
            self.finished.emit(points, zone, out_dir)
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
        self.setMinimumWidth(440)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("LazyGeo")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1F4E79;")
        layout.addWidget(title)

        sub = QLabel("Excel координаты ГМС → проект QGIS + SHP + DXF")
        sub.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(sub)

        self.btn_excel = QPushButton("Выбрать Excel с координатами")
        self.btn_excel.setStyleSheet(self._btn_style())
        self.btn_excel.clicked.connect(self._pick_excel)
        layout.addWidget(self.btn_excel)

        self.lbl_excel = QLabel("Файл не выбран")
        self.lbl_excel.setStyleSheet("color: #888; font-size: 10px; padding-left: 4px;")
        layout.addWidget(self.lbl_excel)

        self.btn_run = QPushButton("▶  Запустить")
        self.btn_run.setStyleSheet(self._btn_style())
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run)
        layout.addWidget(self.btn_run)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.hide()
        layout.addWidget(self.status)

        self.setLayout(layout)

    def _btn_style(self, color="#1F4E79"):
        return f"""
            QPushButton {{
                background: {color}; color: white;
                border: none; padding: 9px;
                border-radius: 4px; font-size: 12px;
            }}
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
            self.lbl_excel.setStyleSheet("color: #155724; font-size: 10px; padding-left: 4px;")
            self.btn_run.setEnabled(True)

    def _run(self):
        self.btn_run.setEnabled(False)
        self.btn_excel.setEnabled(False)
        self.progress.show()
        self._set_status("⏳ Обрабатываю...", "#856404", "#fff3cd")

        self.worker = ConvertWorker(self.xlsx_path)
        self.worker.finished.connect(self._on_success)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_success(self, points, zone, out_dir):
        self.progress.hide()

        if not HAS_PANDAS:
            self.btn_excel.setEnabled(True)
            self.btn_run.setEnabled(True)
            QMessageBox.critical(self, "LazyGeo",
                "Не найдены зависимости pandas / openpyxl.\n\n"
                "Откройте в QGIS:\n"
                "Плагины → Консоль Python\n\n"
                "И выполните:\n"
                "import pip\n"
                "pip.main(['install', 'pandas', 'openpyxl'])")
            return

        epsg = 20900 + zone
        crs  = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")

        # 1. Новый проект
        QgsProject.instance().clear()

        # 2. Подложка
        google_url = "type=xyz&url=https://mt1.google.com/vt/lyrs%3Ds%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D&zmax=20&zmin=0"
        basemap = QgsRasterLayer(google_url, "Google Satellite", "wms")
        if basemap.isValid():
            QgsProject.instance().addMapLayer(basemap)

        # 3. Проекция проекта
        QgsProject.instance().setCrs(crs)

        # 4. Слой точек
        pt_layer = QgsVectorLayer("Point", "Точки участка", "memory")
        pt_layer.setCrs(crs)
        pr = pt_layer.dataProvider()
        pr.addAttributes([
            QgsField("id", QVariant.Int),
            QgsField("X",  QVariant.Double),
            QgsField("Y",  QVariant.Double),
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

        # 5. SHP полигон
        shp_path = os.path.join(out_dir, "лицензия.shp")
        poly_layer = QgsVectorLayer("Polygon", "лицензия", "memory")
        poly_layer.setCrs(crs)
        pr2 = poly_layer.dataProvider()
        pr2.addAttributes([QgsField("name", QVariant.String)])
        poly_layer.updateFields()

        poly_f = QgsFeature()
        poly_f.setGeometry(QgsGeometry.fromPolygonXY([pts_geom + [pts_geom[0]]]))
        poly_f.setAttributes(["лицензия"])
        pr2.addFeature(poly_f)

        # Сохраняем SHP
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        write_result, error_msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
            poly_layer, shp_path,
            QgsCoordinateTransformContext(), options
        )
        if write_result != QgsVectorFileWriter.NoError:
            raise Exception(f"Ошибка сохранения SHP: {error_msg}")

        # Загружаем SHP как слой
        shp_layer = QgsVectorLayer(shp_path, "лицензия", "ogr")
        QgsProject.instance().addMapLayer(shp_layer)

        # 6. DXF
        dxf_path = os.path.join(out_dir, "лицензия.dxf")
        options_dxf = QgsVectorFileWriter.SaveVectorOptions()
        options_dxf.driverName = "DXF"
        options_dxf.fileEncoding = "UTF-8"
        QgsVectorFileWriter.writeAsVectorFormatV3(
            shp_layer, dxf_path,
            QgsCoordinateTransformContext(), options_dxf
        )

        # 7. Зум
        self.iface.mapCanvas().setExtent(shp_layer.extent())
        self.iface.mapCanvas().refresh()

        self._set_status(
            f"✅ Готово!\n"
            f"{len(points)} точек • зона ГК {zone} • EPSG:{epsg}\n"
            f"Файлы сохранены в папке:\n{out_dir}",
            "#155724", "#d4edda"
        )
        self.btn_excel.setEnabled(True)
        self.btn_run.setEnabled(True)

    def _on_error(self, error):
        self.progress.hide()
        self.btn_excel.setEnabled(True)
        self.btn_run.setEnabled(True)
        self._set_status(f"❌ {error}", "#721c24", "#f8d7da")
        QMessageBox.critical(self, "LazyGeo", f"Ошибка:\n{error}")

    def _set_status(self, text, color="#333", bg="#EBF3FB"):
        self.status.setText(text)
        self.status.setStyleSheet(
            f"padding: 10px; background: {bg}; border-radius: 4px; color: {color};")
        self.status.show()


# ─── Плагин ───────────────────────────────────────────────────────────────────

class LazyGeoPlugin:
    def __init__(self, iface):
        self.iface  = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction("LazyGeo", self.iface.mainWindow())
        self.action.setToolTip("Excel координаты → SHP + DXF в ГК ГСК-2011")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("LazyGeo", self.action)

    def unload(self):
        self.iface.removePluginMenu("LazyGeo", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        if not self.dialog:
            self.dialog = LazyGeoDialog(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
