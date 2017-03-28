from setuptools import setup, find_packages
setup(
    name="pgh-bustime",
    version='0.8.5',
    author='Nathaniel Fruchter',
    author_email='pghbustime@gmail.com',
    packages=['pghbustime'],
    url='http://github.com/nhfruchter/pgh-bustime',
    license='LICENSE',
    description='Python wrapper for the Port Authority of Allegheny County realtime bus information API.',
    install_requires=['xmltodict', 'requests', 'pytz']
)
