.PHONY: install install-uv test clean build docker-build docker-run

install:
        pip install -e .
        playwright install

install-uv:
        pip install uv
        uv pip install -e .
        playwright install

test:
        pytest

clean:
        rm -rf build/
        rm -rf dist/
        rm -rf *.egg-info
        find . -name "__pycache__" -exec rm -rf {} +
        find . -name "*.pyc" -delete
        find . -name "*.pyo" -delete
        find . -name "*.pyd" -delete

build:
        python setup.py sdist bdist_wheel

docker-build:
        docker build -t clippypour .

docker-run:
        docker run -p 12000:12000 --env-file .env clippypour

web:
        python -m clippypour.main web --port 12000

gui:
        python -m clippypour.main