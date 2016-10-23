=========
Surficial
=========

Surficial is a Python library and CLI tools to support stream long-profile analysis and plotting.

.. image:: https://anaconda.org/mrahnis/surficial/badges/version.svg   :target: https://anaconda.org/mrahnis/surficial
.. image:: https://anaconda.org/mrahnis/surficial/badges/installer/conda.svg   :target: https://conda.anaconda.org/mrahnis


Installation
============

To install from Anaconda Cloud:


To install from the Python Package Index:

	$pip install surficial

To install from the source distribution execute the setup script in the surficial directory:

	$python setup.py install

Examples
========

Display usage information:

surficial --help # print the subcommands
surficial profile --help 
surficial plan --help
surficial network --help

The example scripts may be run like so:

	$surficial profile stream_ln.shp elevation.tif --point terrace_pt.shp terrace --point feature_pt.shp features --styles styles.json

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