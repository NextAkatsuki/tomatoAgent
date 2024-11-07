import sys

class ToolInfo:
    def __init__(self, alias, func, description, prompt):
        self.alias = alias
        self.func = func
        self.description = description
        self.prompt = prompt

    def to_dict(self):
        return {
            "alias":self.alias, 
            "func_name": self.func.__name__, 
            "desc": self.description,
            "prompt": self.prompt
        }

class ToolRegistry:
    def __init__(self):
        self._functions = {}

    def register(self, alias, description, prompt):
        def decorator(func):
            self._functions[alias] = ToolInfo(alias, func, description, prompt)
            return func
        return decorator

    def get_tool_info(self, aliases):
        if aliases == []:
            func_info = [func.to_dict() for func in self._functions.values()]
            return func_info
        else:
            func_info = [self._functions.get(alias).to_dict() for alias in aliases]
            return func_info

    def get_func(self, alias):
        return self._functions[alias].func

    def get_funcNames(self):
        return list(self._functions.keys())

