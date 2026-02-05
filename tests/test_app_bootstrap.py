from elephan_code.app import AppConfig, build_runtime


class _FakeLLM:
    def ask(self, messages):
        raise RuntimeError("not used")


def test_build_runtime_creates_agent_tools(monkeypatch):
    from elephan_code import app as app_pkg

    def _fake_get_llm(provider, **kwargs):
        assert provider == "openrouter"
        assert kwargs["api_key"] == "k"
        assert kwargs["model_id"] == "m"
        return _FakeLLM()

    monkeypatch.setattr(app_pkg.bootstrap.LLMFactory, "get_llm", _fake_get_llm)

    config = AppConfig(api_key="k", model_id="m", mode="auto", max_steps=3)
    runtime = build_runtime(config)

    assert runtime.llm is not None
    assert runtime.tools is not None
    assert runtime.agent is not None
    assert runtime.agent.max_steps == 3
