import os
from setuptools import setup

this_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(this_dir, "README.rst"), "r") as f:
    long_description = f.read()

with open(os.path.join(this_dir, "requirements.txt"), "r") as f:
    requirements = f.read()

install_requires = [line for line in requirements.splitlines() if line]

setup(
    name="hisensetv",
    description="MQTT interface to Hisense televisions.",
    long_description=long_description,
    version="0.0.8a1",
    author="Alex M.",
    author_email="7845120+newAM@users.noreply.github.com",
    url="https://github.com/newAM/hisensetv",
    license="MIT",
    python_requires=">=3.6",
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    entry_points={"console_scripts": ["hisensetv=hisensetv.__main__:main"]},
    packages=["hisensetv"],
)
