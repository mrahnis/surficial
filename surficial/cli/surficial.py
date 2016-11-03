import sys

import click
from pkg_resources import iter_entry_points
from click_plugins import with_plugins

import surficial


@with_plugins(iter_entry_points('surficial.subcommands'))
@click.group()
@click.pass_context
@click.version_option(version=surficial.__version__, message='%(version)s')
def cli(ctx):
    pass
