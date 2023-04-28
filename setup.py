from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in nexgo_etr/__init__.py
from nexgo_etr import __version__ as version

setup(
	name="nexgo_etr",
	version=version,
	description="intergration for the nexgo-n5 gadget",
	author="Verckys Orwa",
	author_email="VerckysOrwa@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
