from conhead import main


def test_main(cli_runner):
    result = cli_runner.invoke(main.main)
    assert result.exit_code == 0
