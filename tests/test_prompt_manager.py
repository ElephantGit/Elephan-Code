from elephan_code.llm.prompt_manager import PromptManager


def test_compose_includes_tools_examples_and_schema():
    examples = [
        '{"thought": "check", "action": {"name": "finish", "parameters": {}}}'
    ]
    pm = PromptManager(tools=["read_file", "write_file"], examples=examples)
    schema = '{"schema": "dummy"}'
    prompt = pm.compose(task="do X", schema_constraint=schema)

    assert "read_file" in prompt
    assert "write_file" in prompt
    assert "do X" in prompt
    assert "dummy" in prompt


if __name__ == "__main__":
    test_compose_includes_tools_examples_and_schema()
    print("test_prompt_manager: OK")
