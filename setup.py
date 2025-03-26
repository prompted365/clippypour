from setuptools import setup, find_packages

with open("readme.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="clippypour",
    version="0.1.0",
    author="prompted365",
    author_email="info@prompted365.com",
    description="AI-driven, clipboard-free form-filling automation system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/prompted365/clippypour",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "clippypour=clippypour.main:main_cli",
            "clippypour-gui=clippypour.main:main_gui",
        ],
    },
)