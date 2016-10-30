
first:
	@echo "Please pick a target from the makefile"

freeze:
	pip freeze -r requirements-devel.txt > requirements-devel2.txt
	mv requirements-devel2.txt requirements-devel.txt

test:
	pytest

dep-test:
	pip install -r requirements-devel.txt

lint:
	flake8


test-release:
	python setup.py register -r pypitest
	python setup.py sdist upload -r pypitest

real-release:
	python setup.py register -r pypi
	python setup.py sdist upload -r pypi
