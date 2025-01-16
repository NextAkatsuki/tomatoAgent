import sys


class ToolRegistry:
    def __init__(self):
        self._funcInfos = {}
        self._funcObjs = {}

    def register(self, alias, funcInfo):
        def decorator(func):
            self._funcInfos[alias] = funcInfo
            self._funcObjs[alias] = func
            return func
        return decorator


    def get_funcInfos(self, aliases):
        return [self._funcInfos[key] for key in aliases if key in self._funcInfos]


    def get_funcObjs(self, aliases):
        return {key: self._funcObjs[key] for key in aliases if key in self._funcObjs}

