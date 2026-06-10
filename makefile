PLUGIN_NAME = LazyGeo
VERSION = $(shell grep "^version=" metadata.txt | cut -d= -f2)
ZIP_NAME = $(PLUGIN_NAME)-$(VERSION).zip

PLUGIN_FILES = \
	__init__.py \
	metadata.txt \
	lazygeo.py

.PHONY: zip clean

zip:
	@echo "Собираем $(ZIP_NAME)..."
	@mkdir -p dist/$(PLUGIN_NAME)
	@cp $(PLUGIN_FILES) dist/$(PLUGIN_NAME)/
	@cd dist && zip -r ../$(ZIP_NAME) $(PLUGIN_NAME)/
	@rm -rf dist/
	@echo "Готово: $(ZIP_NAME)"

clean:
	@rm -f $(PLUGIN_NAME)-*.zip
	@echo "Очищено"