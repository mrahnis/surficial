=========
Surficial
=========

Surficial is a Python library and CLI tools to support stream long-profile analysis and plotting.

The CLI displays matplotlib plots of showing long-profile or plan view maps. It is meant to be simple and accepts as arguments a set of 2D or 3D stream centerlines, and an elevation source. Optional arguments may include one or more point datasets to display on the profile, along with plot styles from a JSON file.

.. image:: https://anaconda.org/mrahnis/surficial/badges/version.svg
	:target: https://anaconda.org/mrahnis/surficial

.. image:: https://anaconda.org/mrahnis/surficial/badges/installer/conda.svg
	:target: https://conda.anaconda.org/mrahnis


Installation
============

To install from Anaconda Cloud:

If you are starting from scratch the first thing to do is install the Anaconda Python distribution and add the necessary channels to obtain all the dependencies:

	>>>conda config --append channels conda-forge

	>>>conda config --append channels mrahnis

Then install surficial:

	>>>conda install surficial

To install from the Python Package Index:

	>>>pip install surficial

To install from the source distribution execute the setup script in the surficial directory:

	>>>python setup.py install

Examples
========

Display usage information:

	>>>surficial --help

	>>>surficial profile --helpA

	>>>surficial plan --help

	>>>surficial network --help

Scripts may be run from the commandline like so:

	>>>surficial profile stream_ln.shp elevation.tif --point terrace_pt.shp terrace --point feature_pt.shp features --styles styles.json

The above plots a long-profile from a set of stream centerlines (stream_ln.shp), and projects points onto the profile (terrace_pt.shp and feature_pt.shp), where the point styles (terrace and features) are read from styles.json.

License
=======

BSD

Documentation
=============

Latest `html`_

.. _`Python 2.7 or 3.x`: http://www.python.org
.. _NumPy: http://www.numpy.org
.. _pandas: http://pandas.pydata.org
.. _matplotlib: http://matplotlib.org
.. _Shapely: https://github.com/Toblerity/Shapely
.. _networkx: http://networkx.github.io/

.. _release page: https://github.com/mrahnis/surficial/releases

.. _html: http://surficial.readthedocs.org/en/latest/