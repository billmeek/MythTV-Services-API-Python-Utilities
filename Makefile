PACKAGE = mythtv_services_api

SOURCE = \
	setup.py \
	setup.cfg \
	$(PACKAGE)/send.py \
	$(PACKAGE)/utilities.py \
	$(PACKAGE)/__init__.py \
	$(PACKAGE)/_version.py

$(PACKAGE).egg-info/PKG-INFO: $(SOURCE)
	python2 setup.py bdist_wheel
	sudo -H pip2 install dist/$(PACKAGE)-*.*.*-py2-none-any.whl
	python3 setup.py bdist_wheel
	sudo -H pip3 install dist/$(PACKAGE)-*.*.*-py3-none-any.whl

clean:
	@rm -f $(PACKAGE)/*.pyc
	@rm -rf $(PACKAGE)/__pycache__
	@rm -rf build/*

clobber: clean
	@git rm -f dist/$(PACKAGE)-*.*.*-py?-none-any.whl
	@rm -rf $(PACKAGE).egg-info

uninstall:
	sudo -H pip2 uninstall $(PACKAGE)
	sudo -H pip3 uninstall $(PACKAGE)

# :!make --dry-run
