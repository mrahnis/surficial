from setuptools import setup, find_packages


# Parse the version from the shapely module
for line in open('surficial/__init__.py', 'r'):
    if line.find("__version__") >= 0:
        version = line.split("=")[1].strip()
        version = version.strip('"')
        version = version.strip("'")
        continue

#open('VERSION.txt', 'wb').write(bytes(version, 'UTF-8'))
with open('VERSION.txt', 'w') as fp:
    fp.write(version)


setup(name='surficial',
	version=version,
	author='Michael Rahnis',
	author_email='michael.rahnis@fandm.edu',
	description='Python library and CLI tools to support analysis of stream long-profiles',
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
		'drapery'
	],
	entry_points='''
		[console_scripts]
		surficial=surficial.cli.surficial:cli
		buffer=surficial.cli.buffer:cli
		repair=surficial.cli.repair:cli
	''',
	keywords='cross-section, topography, survey, plotting',
	classifiers=[
		'Development Status :: 3 - Alpha',
		'License :: OSI Approved :: BSD License',
		'Programming Language :: Python',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Topic :: Scientific/Engineering :: GIS'
	]
)

