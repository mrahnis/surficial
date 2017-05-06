from click.testing import CliRunner

import surficial
from surficial.cli.surficial import cli

def test_surficial():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
