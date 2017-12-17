all : clean  create-venv build


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
		python3 setup.py install

build:
	    .venv/bin/python setup.py bdist_egg

create-venv:
	virtualenv --python=python3 .venv
	. .venv/bin/activate
	pip install -r requirements.txt   
