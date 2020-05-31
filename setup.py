from os import path
from setuptools import setup, find_packages


for line in open('surficial/__init__.py', 'r'):
    if line.find("__version__") >= 0:
        version = line.split("=")[1].strip()
        version = version.strip('"')
        version = version.strip("'")
        continue

with open('VERSION.txt', 'w') as fp:
    fp.write(version)

current_directory = path.abspath(path.dirname(__file__))
with open(path.join(current_directory, 'README.rst'), 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(name='surficial',
      version=version,
      author='Michael Rahnis',
      author_email='mike@topomatrix.com',
      description='Python library and CLI tools to support analysis of stream long-profiles',
      long_description=long_description,
      long_description_content_type='text/x-rst',
      url='http://github.com/mrahnis/surficial',
      license='BSD',
      packages=find_packages(),
      install_requires=[
          'click',
          'pandas',
          'matplotlib',
          'shapely',
          'descartes',
          'rasterio',
          'fiona',
          'networkx',
          'adjusttext',
          'drapery'
      ],
      entry_points='''
          [console_scripts]
          surficial=surficial.cli.surficial:cli

          [surficial.subcommands]
          buffer=surficial.cli.buffer:buffer
          network=surficial.cli.network:network
          plan=surficial.cli.plan:plan
          profile=surficial.cli.profile:profile
          repair=surficial.cli.repair:repair
          station=surficial.cli.station:station
          identify=surficial.cli.identify:identify
      ''',
      keywords='cross-section, topography, survey, plotting',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering :: GIS'
      ])
