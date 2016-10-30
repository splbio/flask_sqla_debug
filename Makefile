
freeze:
	pip freeze -r requirements-devel.txt > requirements-devel2.txt
	mv requirements-devel2.txt requirements-devel.txt

test:
	pytest

dep-test:
	pip install -r requirements-devel.txt
