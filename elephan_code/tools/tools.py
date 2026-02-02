import os
import subprocess


class ToolManager:
    def __init__(self):
        self.tools = {}

        # 注册基础工具
        self.register_tool("read_file", self.read_file)
        self.register_tool("write_file", self.write_file)
        self.register_tool("excute_shell", self.excute_shell)

    def register_tool(self, name, func):
        self.tools[name] = func

    def call(self, name, params):
        if name not in self.tools:
            return f"Error Tool {name} not found."
        return self.tools[name](**params)

    def read_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return str(e)
    
    def write_file(self, path, content):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
                return "File write successfully."
        except Exception as e:
            return str(e)

    def excute_shell(self, command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return f"ExitCode: {result.returncode}\nStdout:{result.stdout}\nStderror: {result.stderr}"

