import os
from setuptools import setup

this_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(this_dir, "readme.rst"), "r") as f:
    long_description = f.read()

setup(
    name="hisensetv",
    description="MQTT interface to Hisense televisions.",
    long_description=long_description,
    version="0.0.2",
    author="Alex M.",
    author_email="7845120+newAM@users.noreply.github.com",
    url="https://github.com/newAM/hisensetv",
    license="MIT",
    python_requires=">=3.6",
    install_requires=["paho-mqtt>=1.5.0"],
    entry_points={"console_scripts": ["hisensetv=hisensetv.__main__:main"]},
    packages=["hisensetv"],
)
