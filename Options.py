import json
import os
import ttkbootstrap as ttk

class GlobalOptions():
    def __init__(self):
        self.enableOverwritingSource = ttk.BooleanVar(value=False)
        self.createBackupWhenOverwritingSource = ttk.BooleanVar(value=True)

        self.includeSource = ttk.BooleanVar(value=True)
        self.includeTarget = ttk.BooleanVar(value=True)
        self.changeFromPlayerOnly = ttk.BooleanVar(value=True)
        self.nameFixFormat = ttk.StringVar(value="(p{0})")
        self.nameGaiaFix = ttk.StringVar(value="(GAIA)")

        self.addDuplicateMark = ttk.BooleanVar(value=False)
        self.load('config.json')

    def load(self, file):
        jsonValid = False
        if os.path.isfile(file):
            with open(file, 'r') as f:
                try:
                    cfg = json.load(f)
                except json.decoder.JSONDecodeError:
                    cfg = {'GlobalOptions':{}}
                else:
                    if 'GlobalOptions' in cfg:
                        jsonValid = True
        if jsonValid:
            for attr in cfg['GlobalOptions']:
                if hasattr(self, attr):
                    getattr(self, attr).set(cfg['GlobalOptions'][attr])
        else:
            self.dump(file)

    def dump(self, file):
        attrs = [member for member in dir(self) if not callable(getattr(self, member)) and not member.startswith("__")]
        dump = {'GlobalOptions': {}}
        for attr in attrs:
            dump['GlobalOptions'][attr] = getattr(self, attr).get()
        with open(file, 'w') as f:
            json.dump(dump, f, indent=4)

class ScenarioOptions():
    def __init__(self):
        self.unitDuplicateMappings: list[list[int]] = []
        self.tileDuplicateMappings: list[list[tuple[int, int]]] = []
