import json
import os
import ttkbootstrap as ttk
from _prebuild.OptionsDefine import OPTIONS_DEFINE

class GlobalOptions():
    def __init__(self, workDir: str):
        self._baseDir = workDir
        self._configPath = f'{self._baseDir}/config.json'
        for option, args in OPTIONS_DEFINE.items():
            match args['type']:
                case 'string':
                    optionType = ttk.StringVar
                case 'boolean':
                    optionType = ttk.BooleanVar
                case 'integer':
                    optionType = ttk.IntVar
                case 'float':
                    optionType = ttk.DoubleVar
                case _:
                    optionType = ttk.Variable
            setattr(self, option, optionType(value=args['default']))
        self.load(self._configPath)

    def saveAll(self):
        self.dump(self._configPath)

    def load(self, file):
        jsonValid = False
        try:
            with open(file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if 'GlobalOptions' in cfg:
                    jsonValid = True
        except (FileNotFoundError, PermissionError, json.decoder.JSONDecodeError, UnicodeDecodeError):
            cfg = {'GlobalOptions':{}}
        if jsonValid:
            for attr in cfg['GlobalOptions']:
                if hasattr(self, attr):
                    getattr(self, attr).set(cfg['GlobalOptions'][attr])
        else:
            self.dump(file)

    def dump(self, file):
        dump = {'GlobalOptions': {}}
        for attr in OPTIONS_DEFINE.keys():
            dump['GlobalOptions'][attr] = getattr(self, attr).get()
        try:
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(dump, f, indent=4, ensure_ascii=False)
        except PermissionError:
            pass

    def setOption(self, attr: str, value):
        if hasattr(self, attr):
            getattr(self, attr).set(value)
            self.dump(self._configPath)

class ScenarioOptions():
    def __init__(self):
        self.unitDuplicateMappings: list[list[int]] = []
        self.tileDuplicateMappings: list[list[tuple[int, int]]] = []
