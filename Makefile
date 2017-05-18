PACKAGE = mythtv_services_api

SOURCE = \
	setup.py \
	setup.cfg \
	$(PACKAGE)/send.py \
	$(PACKAGE)/utilities.py \
	$(PACKAGE)/__init__.py \
	$(PACKAGE)/_version.py

usage:
	@echo "\nUse: make install VERSION=M.m.f e.g VERSION=1.2.3\n"

$(PACKAGE).egg-info/PKG-INFO install:
	@test -n "$(VERSION)"
	@python2 setup.py bdist_wheel
	@sudo -H pip2 install dist/$(PACKAGE)-$(VERSION)-py2-none-any.whl
	@python3 setup.py bdist_wheel
	@sudo -H pip3 install dist/$(PACKAGE)-$(VERSION)-py3-none-any.whl
	@git commit --all --message "Add .whl files for $(VERSION)" dist/$(PACKAGE)-$(VERSION)-py?-none-any.whl

clean:
	@rm -f  $(PACKAGE)/*.pyc
	@rm -rf $(PACKAGE)/__pycache__
	@rm -rf $(PACKAGE).egg-info
	@rm -rf build/*

clobber: clean
	@git rm -f dist/$(PACKAGE)-$(VERSION)-py?-none-any.whl

uninstall:
	sudo -H pip2 uninstall $(PACKAGE)
	sudo -H pip3 uninstall $(PACKAGE)
