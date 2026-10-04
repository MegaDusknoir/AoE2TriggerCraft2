import json
import jsonschema
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
    schema = {
        "type": "object",
        "properties": {
            "unitDuplicateMappings" : {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "mapping": {
                            "type": "array",
                            "items": {
                                "type": "integer"
                            },
                            "minItems": 2,
                            "maxItems": 8
                        }
                    }
                }
            },
            "tileDuplicateMappings" : {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "mapping": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "integer"
                                },
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "minItems": 2,
                            "maxItems": 8
                        }
                    }
                }
            },
            "areaDuplicateMappings" : {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "mapping": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "integer"
                                    },
                                    "minItems": 2,
                                    "maxItems": 2
                            },
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "minItems": 2,
                            "maxItems": 8
                        }
                    }
                }
            }
        },
        "required": [
            "unitDuplicateMappings",
            "tileDuplicateMappings",
            "areaDuplicateMappings"
        ]
    }

    def __init__(self):
        self.unitDuplicateMappings: list[dict] = []
        self.tileDuplicateMappings: list[dict] = []
        self.areaDuplicateMappings: list[dict] = []

    def load(self, file):
        with open(file, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        jsonschema.validate(cfg, self.schema)

        self.unitDuplicateMappings = []
        self.tileDuplicateMappings = []
        self.areaDuplicateMappings = []
        for mappingItem in cfg["unitDuplicateMappings"]:
            mappingItem["mapping"].extend([-1] * (8 - len(mappingItem["mapping"])))
            self.unitDuplicateMappings.append({"name": mappingItem["name"], "mapping": [-1] + mappingItem["mapping"]})
        for mappingItem in cfg["tileDuplicateMappings"]:
            mappingItem["mapping"].extend([[-1,-1]] * (8 - len(mappingItem["mapping"])))
            self.tileDuplicateMappings.append({"name": mappingItem["name"], "mapping": [[-1,-1]] + mappingItem["mapping"]})
        for mappingItem in cfg["areaDuplicateMappings"]:
            for i, area in enumerate(mappingItem["mapping"]):
                mappingItem["mapping"][i] = [*area[0], *area[1]]
            mappingItem["mapping"].extend([[-1,-1,-1,-1]] * (8 - len(mappingItem["mapping"])))
            self.areaDuplicateMappings.append({"name": mappingItem["name"], "mapping": [[-1,-1,-1,-1]] + mappingItem["mapping"]})
            
    def save(self, file):
        dump = {
            "unitDuplicateMappings": [],
            "tileDuplicateMappings": [],
            "areaDuplicateMappings": [],
        }
        for mappingItem in self.unitDuplicateMappings:
            dump["unitDuplicateMappings"].append({"name": mappingItem["name"], "mapping": mappingItem["mapping"][1:]})
        for mappingItem in self.tileDuplicateMappings:
            dump["tileDuplicateMappings"].append({"name": mappingItem["name"], "mapping": mappingItem["mapping"][1:]})
        for mappingItem in self.areaDuplicateMappings:
            dump["areaDuplicateMappings"].append({"name": mappingItem["name"],
                                                  "mapping": [[[a[0],a[1]],[a[2],a[3]]] for a in mappingItem["mapping"][1:]]})
        try:
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(dump, f, indent=4, ensure_ascii=False)
        except PermissionError:
            pass