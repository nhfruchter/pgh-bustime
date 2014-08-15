from setuptools import setup, find_packages
import logging, os.path


setup(
    name = "pghbustime",
    version = "0.1",
    packages = find_packages(),
    install_requires = ['xmltodict>=0.9.0', 'requests>=2.0.0', 'repoze.lru'],
    package_data = {'': '*.md'},

    author = "Nathaniel Fruchter",
    author_email = "nhfruchter@gmail.com",
    description = "Python interface to the bus time API for the Port Authority of Allegheny County.",
    license = "MIT",
    keywords = "bus bustime api pittsburgh civic transportation transport transit",
    url = "http://github.com/nhfruchter/pgh-bustime"
)
