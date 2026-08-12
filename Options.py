import json
import os
import ttkbootstrap as ttk

class GlobalOptions():
    def __init__(self, workDir: str):
        self._baseDir = workDir
        self._configPath = f'{self._baseDir}/config.json'
        self.language = ttk.StringVar(value="auto")
        self.enableOverwritingSource = ttk.BooleanVar(value=False)
        self.createBackupWhenOverwritingSource = ttk.BooleanVar(value=True)

        self.includeSource = ttk.BooleanVar(value=True)
        self.includeTarget = ttk.BooleanVar(value=True)
        self.changeFromPlayerOnly = ttk.BooleanVar(value=True)
        self.nameFixFormat = ttk.StringVar(value="(p{0})")
        self.nameGaiaFix = ttk.StringVar(value="(GAIA)")

        self.addDuplicateMark = ttk.BooleanVar(value=False)
        self.load(self._configPath)

    def load(self, file):
        jsonValid = False
        try:
            with open(file, 'r') as f:
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
        attrs = [member for member in dir(self) if not callable(getattr(self, member)) and not member.startswith("_")]
        dump = {'GlobalOptions': {}}
        for attr in attrs:
            dump['GlobalOptions'][attr] = getattr(self, attr).get()
        try:
            with open(file, 'w') as f:
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
