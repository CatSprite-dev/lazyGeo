PLUGIN_NAME = LazyGeo
VERSION = $(shell grep "^version=" metadata.txt | cut -d= -f2)
ZIP_NAME = $(PLUGIN_NAME)-$(VERSION).zip

PLUGIN_FILES = \
	__init__.py \
	metadata.txt \
	lazygeo.py \
	LICENSE

DEPS = openpyxl

.PHONY: zip clean icon

icon:
	@echo "Генерируем img/icon.png..."
	@rsvg-convert -w 32 -h 32 img/iconsource.svg -o img/icon.png
	@echo "Готово: img/icon.png"

zip: icon
	@echo "Ставим зависимости в libs/..."
	@rm -rf libs
	@pip3 install $(DEPS) --target libs --quiet
	@echo "Собираем $(ZIP_NAME)..."
	@mkdir -p dist/$(PLUGIN_NAME)
	@cp $(PLUGIN_FILES) dist/$(PLUGIN_NAME)/
	@cp -R libs dist/$(PLUGIN_NAME)/
	@cp -R img dist/$(PLUGIN_NAME)/
	@cd dist && zip -r ../$(ZIP_NAME) $(PLUGIN_NAME)/ -x "*/__pycache__/*" -x "*.pyc"
	@rm -rf dist/
	@echo "Готово: $(ZIP_NAME)"

clean:
	@rm -f $(PLUGIN_NAME)-*.zip
	@rm -rf dist/ libs/ img/icon.png
	@echo "Очищено"
