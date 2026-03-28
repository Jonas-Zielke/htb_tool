"""
HTB Tool — Setup for pip install
"""
from setuptools import setup, find_packages

setup(
    name="htb-tool",
    version="1.0.0",
    description="Hack The Box CLI Tool Manager",
    author="HTB Tool",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "": ["templates/*.j2"],
    },
    py_modules=["htb"],
    install_requires=[
        "click>=8.0",
        "rich>=13.0",
        "jinja2>=3.0",
        "pyyaml>=6.0",
        "requests>=2.28",
        "beautifulsoup4>=4.12",
    ],
    entry_points={
        "console_scripts": [
            "htb=htb:cli",
        ],
    },
    python_requires=">=3.10",
)
