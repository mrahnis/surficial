=========
Surficial
=========

Surficial is a Python library and CLI tools to support stream long-profile analysis and plotting.

The CLI displays matplotlib plots of showing long-profile or plan view maps. It is meant to be simple. It accepts as arguments a set of 2D or 3D stream centerlines, and optionally a elevation source. Optional arguments may include one or more point datasets to display on the profile, along with plot styles from a JSON file.

.. image:: https://github.com/mrahnis/surficial/workflows/Python%20package/badge.svg
    :target: https://github.com/mrahnis/surficial/actions?query=workflow%3A%22Python+package%22
    :alt: Python Package

.. image:: https://github.com/mrahnis/surficial/workflows/Conda%20package/badge.svg
    :target: https://github.com/mrahnis/surficial/actions?query=workflow%3A%22Conda+package%22
    :alt: Conda Package

.. image:: https://readthedocs.org/projects/surficial/badge/?version=latest
    :target: http://surficial.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://coveralls.io/repos/github/mrahnis/surficial/badge.svg?branch=main
    :target: https://coveralls.io/github/mrahnis/surficial?branch=main

Installation
============

.. image:: https://img.shields.io/pypi/v/surficial.svg
    :target: https://pypi.org/project/surficial/

.. image:: https://anaconda.org/mrahnis/surficial/badges/version.svg
    :target: https://anaconda.org/mrahnis/surficial

To install from the Python Package Index:

.. code:: console

    pip install surficial

To install from Anaconda Cloud:

If you are starting from scratch the first thing to do is install the Anaconda Python distribution, add the necessary channels to obtain the dependencies and install surficial.

.. code:: console

    conda config --append channels conda-forge
    conda install drapery surficial -c mrahnis

To install from the source distribution:

Execute the setup script in the surficial directory:

.. code:: console

    python setup.py install

Examples
========

Display usage information:

.. code:: console

    surficial --help
    surficial profile --help
    surficial plan --help
    surficial network --help

Scripts may be run from the commandline like so:

.. code:: console

    surficial profile stream_ln.shp --surface elevation.tif --points terrace_pt.shp terrace --points feature_pt.shp features --styles styles.json

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