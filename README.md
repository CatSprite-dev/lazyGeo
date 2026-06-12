# LazyGeo

QGIS plugin for preparing mineral license areas from Rosnedra licenses.

Reads an Excel file with corner point coordinates of a mineral license area in DMS format (GSK-2011), converts to Gauss-Kruger projection with automatic zone detection, creates a point layer and polygon in QGIS with a satellite basemap.
Further export (SHP, DXF, GeoJSON, etc.) is done via standard QGIS tools.

### Rosnedra coordinates (no header)
![Excel format](https://raw.githubusercontent.com/CatSprite-dev/lazyGeo/main/screenshots/excel_example.png)

### Result in QGIS
![Result in QGIS](https://raw.githubusercontent.com/CatSprite-dev/lazyGeo/main/screenshots/qgis_result.png)

## Quick start

1. Download `LazyGeo-x.x.zip` from Releases
2. QGIS → Plugins → Manage and Install Plugins → Install from ZIP
3. Open the plugin via Plugins → LazyGeo
4. Select Excel → adjust layer name if needed → Run

## Excel format

7 columns, coordinates in GSK-2011 in DMS format (degrees-minutes-seconds). No header row — data starts from the first row:

```
1  | 54 | 30 | 47.102 | 59 | 54 | 28.465
2  | 54 | 30 | 15.220 | 59 | 56 | 31.257
```

Column order: `# | Latitude ° | ′ | ″ | Longitude ° | ′ | ″`

Gauss-Kruger zone is detected automatically.

## Requirements

- QGIS 3.16+

## License

MIT

---

# LazyGeo

QGIS плагин для подготовки участков недр из лицензий Роснедра.

Читает Excel с координатами угловых точек участка недр в формате ГМС (ГСК-2011), конвертирует в проекцию Гаусса-Крюгера с автоматическим определением зоны, создаёт слой точек и полигон участка на карте QGIS и добавляет спутниковую подложку.  
Дальнейший экспорт (SHP, DXF, GeoJSON и др.) выполняется стандартными средствами QGIS.

### Координаты Роснедра (без шапки)
![Формат Excel](https://raw.githubusercontent.com/CatSprite-dev/lazyGeo/main/screenshots/excel_example.png)

### Результат в QGIS
![Результат в QGIS](https://raw.githubusercontent.com/CatSprite-dev/lazyGeo/main/screenshots/qgis_result.png)

## Быстрый старт

1. Скачай `LazyGeo-x.x.zip` из Releases
2. QGIS → Модули → Управление модулями → Установить из ZIP
3. Открой плагин через Модули → LazyGeo
4. Выбери Excel → при необходимости поправь название слоя → Запустить

## Формат Excel

7 колонок, координаты в ГСК-2011 в формате ГМС (градусы-минуты-секунды). Заголовки не нужны — данные сразу с первой строки:

```
1  | 54 | 30 | 47,102 | 59 | 54 | 28,465
2  | 54 | 30 | 15,220 | 59 | 56 | 31,257
```

Порядок колонок: `№ | Широта ° | ′ | ″ | Долгота ° | ′ | ″`

Зона Гаусса-Крюгера определяется автоматически.

## Требования

- QGIS 3.16+

## Лицензия

MIT