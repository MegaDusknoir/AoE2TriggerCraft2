import base64
import importlib.util
import json
import os

def createDummyVersion(path):
    with open(path, "w") as f:
        f.write(f'VERSION_STRING = ""\n')
        f.write(f'VERSION_TUPLE = (0,0,0,0)\n')

def createIcon(iconPath, outPath):
    with open(outPath, "w") as f:
        f.write('class Icon(object):\n')
        f.write('\tdef __init__(self):\n')
        f.write("\t\tself.ig='")
    with open(iconPath, "rb") as i:
        b64str = base64.b64encode(i.read())
    with open(outPath, "ab+") as f:
        f.write(b64str)
    with open(outPath, "a") as f:
        f.write("'")

def createCeAttributeDict(outPath):
    def getPackagePath(package_name):
        spec = importlib.util.find_spec(package_name)
        if spec and spec.origin:
            package_dir = os.path.dirname(spec.origin)
            return package_dir
        else:
            raise ImportError(f"Package {package_name} not found")

    package_path = getPackagePath("AoE2ScenarioParser")

    with open(f'{package_path}/versions/DE/v1.54/effects.json', 'r', encoding='utf-8') as f:
        effectStruct = json.load(f)
    with open(f'{package_path}/versions/DE/v1.54/conditions.json', 'r', encoding='utf-8') as f:
        conditionStruct = json.load(f)

    effectAttributes = {}
    for effect in effectStruct:
        if 'attributes' in effectStruct[effect]:
            attributes = effectStruct[effect]['attributes']
            if 'effect_type' in attributes:
                attributes.remove('effect_type')
            effectAttributes[int(effect)] = attributes

    conditionAttributes = {}
    for condition in conditionStruct:
        if 'attributes' in conditionStruct[condition]:
            attributes = conditionStruct[condition]['attributes']
            if 'condition_type' in attributes:
                attributes.remove('condition_type')
            conditionAttributes[int(condition)] = attributes

    with open(outPath, 'w', encoding='utf-8') as f:
        f.write('EFFECT_ATTRIBUTES = ' + str(effectAttributes) + '\n')
        f.write('CONDITION_ATTRIBUTES = ' + str(conditionAttributes) + '\n')

if __name__ == '__main__':
    if os.path.isdir(f'_prebuild') == False:
        os.makedirs(f'_prebuild')
    createDummyVersion('_prebuild/version.py')
    createIcon(iconPath='AoE2TC.ico', outPath='_prebuild/AoE2TC_icon.py')
    createCeAttributeDict(outPath='_prebuild/CeAttributes.py')