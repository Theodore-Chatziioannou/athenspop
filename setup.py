"""Packaging settings."""
import os
from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

setup(
    name="athenspop",
    version='0.1',
    python_requires='>=3.8',
    description="Building a synthetic population for Athens",
    packages=find_packages(),
    entry_points={"console_scripts": ["athenspop = athenspop.cli:cli"]},
    install_requires=install_requires
)
