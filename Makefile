.PHONY: pyinstaller package dev run

pyinstaller:
	pyinstaller --noconfirm --distpath='dist_pyi' PRE\ Workbench.spec

package:
	./package.sh

dev:
	python3 setup.py build_ext --inplace

run:
	python3 -m pre_workbench
