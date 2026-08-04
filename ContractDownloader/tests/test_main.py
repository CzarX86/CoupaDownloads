import asyncio


def test_frozen_cli_entrypoint_consumes_cancelled_error(monkeypatch, capsys):
    import src.main as main_module

    def cancel_run(coro):
        coro.close()
        raise asyncio.CancelledError

    monkeypatch.setattr(main_module.asyncio, "run", cancel_run)

    main_module._run_cli_pipeline()

    assert "Run interrupted safely" in capsys.readouterr().out
