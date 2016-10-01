=========
Surficial
=========

Surficial is a Python library and CLI tools to support stream long-profile analysis and plotting.

Dependencies
============

Surficial 0.0.0 depends on:

* `Python 2.7 or 3.x`_
* NumPy_
* pandas_
* matplotlib_
* Shapely_
* networkx_

Installation
============

To install from the Python Package Index:

	$pip install surficial

To install from the source distribution execute the setup script in the surficial directory:

	$python setup.py install

Examples
========

The example scripts may be run like so:

	$longprofile plot .\examples\piney-run\stream_ln_z.shp .\examples\piney-run\elevation_utm.tif --terrace .\examples\piney-run\terrace_pt_utm.shp --features .\examples\piney-run\feature_pt_utm.shp

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