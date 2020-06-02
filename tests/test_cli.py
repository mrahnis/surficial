from click.testing import CliRunner

import surficial
from surficial.cli.surficial import cli

def test_surficial():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0


def test_buffer():
    runner = CliRunner()
    result = runner.invoke(cli, ['buffer', '--help'])
    assert result.exit_code == 0


def test_identify():
    runner = CliRunner()
    result = runner.invoke(cli, ['identify', '--help'])
    assert result.exit_code == 0


def test_network():
    runner = CliRunner()
    result = runner.invoke(cli, ['network', '--help'])
    assert result.exit_code == 0


def test_plan():
    runner = CliRunner()
    result = runner.invoke(cli, ['plan', '--help'])
    assert result.exit_code == 0


def test_profile():
    runner = CliRunner()
    result = runner.invoke(cli, ['profile', '--help'])
    assert result.exit_code == 0


def test_repair():
    runner = CliRunner()
    result = runner.invoke(cli, ['repair', '--help'])
    assert result.exit_code == 0


def test_station():
    runner = CliRunner()
    result = runner.invoke(cli, ['station', '--help'])
    assert result.exit_code == 0
