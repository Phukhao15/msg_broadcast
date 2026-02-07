from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in msg_broadcast/__init__.py
from msg_broadcast import __version__ as version

setup(
	name="msg_broadcast",
	version=version,
	description="Internal message broadcast system\\",
	author="ITG",
	author_email="phusitb@itg.co.th",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
