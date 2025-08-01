
from __future__ import annotations

import json
import os
import re
from genieutils.datfile import DatFile

def parseLanguageText(filepath: str) -> dict[int, str]:
    lang_dict = {}
    # 匹配形如 213 "60" 或 1001 "Age of Empires II"
    pattern = re.compile(r'^(\d+)\s+"(.*)"$')

    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            # 忽略空行和注释
            if not line or line.startswith('//'):
                continue
            match = pattern.match(line)
            if match:
                key = int(match.group(1))
                value = match.group(2)
                lang_dict[key] = value
    return lang_dict

def getUnitName(data: DatFile, langStrings: dict[int, str]):
    unitsName = {}
    for id, unit in enumerate(data.civs[0].units):
        try:
            langDllKey = unit.language_dll_name
        except AttributeError:
            unitsName[id] = f'<None{id}>'
        else:
            if langDllKey in langStrings:
                unitsName[id] = langStrings[langDllKey]
            else:
                unitsName[id] = unit.name
                if unit.name.strip() in ['', 'None']:
                    unitsName[id] = f'<Unit{id}>'
    return unitsName

def getTechName(data: DatFile, langStrings: dict[int, str]):
    techsName = {}
    for id, tech in enumerate(data.techs):
        try:
            langDllKey = tech.language_dll_name
        except AttributeError:
            techsName[id] = f'<None{id}>'
        else:
            if langDllKey in langStrings:
                techsName[id] = langStrings[langDllKey]
            else:
                techsName[id] = tech.name
                if tech.name.strip() in ['', 'None']:
                    techsName[id] = f'<Tech{id}>'
    return techsName

def getTributeName(data: DatFile, langStrings: dict[int, str]):
    tributesName = {i:langStrings.get(i + 15000, f'<Tribute{i}>') for i in range(0, 500)}
    return tributesName

def parseDataFile(path):
    data = DatFile.parse(path)
    return data

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('datFile', help='Path of the AoE2DE dat file')
    parser.add_argument('languageFile', help='Path of the AoE2DE language string file')
    args = parser.parse_args()

    workDir = os.path.dirname(__file__)

    dataPath = args.datFile
    langPath = args.languageFile

    data = parseDataFile(dataPath)
    language_data = parseLanguageText(langPath)

    unitsName = getUnitName(data, language_data)
    with open(f'{workDir}/UnitsName.json', 'w', encoding='utf-8') as f:
        json.dump(unitsName, f, indent=4, ensure_ascii=False)

    techsName = getTechName(data, language_data)
    with open(f'{workDir}/TechsName.json', 'w', encoding='utf-8') as f:
        json.dump(techsName, f, indent=4, ensure_ascii=False)

    tributesName = getTributeName(data, language_data)
    with open(f'{workDir}/TributesName.json', 'w', encoding='utf-8') as f:
        json.dump(tributesName, f, indent=4, ensure_ascii=False)
