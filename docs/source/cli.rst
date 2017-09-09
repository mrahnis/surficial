=======================
Command Line User Guide
=======================

The surficial command line interface allows you to execute commands that
operate on a directed graph containing stream centerline geometries. Online help lists the subcommands.

.. code-block:: console

	$ surficial --help
	Usage: surficial [OPTIONS] COMMAND [ARGS]...

	Options:
	  --version      Show the version and exit.
	  -v, --verbose  Enables verbose mode
	  --help         Show this message and exit.

	Commands:
	  buffer   Buffers a network graph or path within a...
	  network  Plots the network graph Example: surficial...
	  plan     Plots a planview map Example: surficial...
	  profile  Plots a long profile Example: surficial...
	  repair   Closes gaps in a network graph Example:...
	  station  Creates a series of evenly spaced stations...


The list below describes the purpose of the individual commands. Command usage can be had by accessing the ``--help`` of each command.

buffer
------

.. code-block:: console

	$ surficial buffer --help
	Usage: surficial buffer <options> <alignment_file> <output_file> <float>

	  Buffers a network graph or path within a network graph

	  Example:
	  surficial buffer stream_ln.shp buf.shp 100.0 -s 5

	Options:
	  -s, --source <int>  Source node ID
	  -o, --outlet <int>  Outlet node ID
	  --help              Show this message and exit.

network
-------

.. code-block:: console

	$ surficial network --help
	Usage: surficial network <options> <alignment_file>

	  Plots the network graph

	  Example:
	  surficial network stream_ln.shp

	Options:
	  --help  Show this message and exit.

plan
----

.. code-block:: console

	$ surficial plan --help
	Usage: surficial plan <options> <alignment_file>

	  Plots a planview map

	  Example:
	  surficial plan stream_ln.shp --points terrace_pt.shp terrace --points feature_pt.shp features

	Options:
	  --points <point_file> <style>  Plot points on the planview map using a given
	                                 style
	  --styles <styles_file>         JSON file containing plot styles
	  --show-nodes / --hide-nodes    Label network nodes in the alignment
	  --help                         Show this message and exit.

repair
------

.. code-block:: console

	$ surficial repair --help
	Usage: surficial repair <options> <alignment_file>

	  Closes gaps in a network graph

	  Example:
	  surficial repair stream_ln.shp stream_ln_snap.shp --decimal 4

	Options:
	  -o, --output <output_file>  Output file
	  -d, --decimal <int>         Decimal place precision
	  --help                      Show this message and exit.

profile
-------

.. code-block:: console

	$ surficial profile --help
	Usage: surficial profile <options> <alignment_file>

	  Plots a long profile

	  Example:
	  surficial profile stream_ln.shp --surface elevation.tif --points feature_pt.shp features --points terrace_pt.shp terrace --styles styles.json

	Options:
	  --surface <surface_file>
	  --points <point_file> <style>  Points to project onto profile using a given
	                                 style
	  --styles <styles_file>         JSON file containing plot styles
	  --label / --no-label           Label features from a given field in the
	                                 features dataset
	  --despike / --no-despike       Eliminate elevation up-spikes from the stream
	                                 profile
	  --densify <float>              Densify lines with regularly spaced stations
	                                 given a value for step in map units
	  --radius <float>               Search radius buffer; points within the
	                                 buffer will display in profile
	  --invert / --no-invert         Invert the x-axis
	  -e, --exaggeration <int>       Vertical exaggeration of the profile
	  --help                         Show this message and exit.

station
-------

.. code-block:: console

	$ surficial station --help
	Usage: surficial station <options> <alignment_file> <output_file> <float>

	  Creates a series of evenly spaced stations

	  Example:
	  surficial station stream_ln.shp station_pt.shp 20

	Options:
	  --help  Show this message and exit.
