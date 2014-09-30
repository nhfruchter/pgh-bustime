from setuptools import setup, find_packages
setup(
    name="pgh-bustime",
    version='0.2.2',
    author='Nathaniel Fruchter',
    author_email='fruchter@cmu.edu',
    packages=['pghbustime'],
    url='http://github.com/nhfruchter/pgh-bustime',
    license='LICENSE',
    description='Python wrapper for the Port Authority of Allegheny County realtime bus information API.',
    install_requires=['xmltodict', 'requests', 'repoze.lru', 'pytz']
)
