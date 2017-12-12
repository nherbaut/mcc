all : clean freeze build

venv: .venv/bin/activate

clean: clean-build clean-pyc 

clean-build:
		rm -fr build/
		rm -fr dist/
		rm -fr .eggs/
		find . -name '*.egg-info' -exec rm -fr {} +
		find . -name '*.egg' -exec rm -f {} +

clean-pyc:
		find . -name '*.pyc' -exec rm -f {} +
		find . -name '*.pyo' -exec rm -f {} +
		find . -name '*~' -exec rm -f {} +
		find . -name '__pycache__' -exec rm -fr {} +

install: clean
		python setup.py install

build:
	    .venv/bin/python setup.py bdist_egg

freeze:
		. .venv/bin/activate && pip freeze > requirements.txt