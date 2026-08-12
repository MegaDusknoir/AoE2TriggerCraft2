import base64
import importlib.util
import json
import os

INCLUDING_VERSION = ['1.58', '1.57', '1.56', '1.55', '1.54', '1.53', '1.51', '1.49', '1.48', '1.47', '1.46', '1.45', '1.44', '1.43', '1.42', '1.41', '1.40', '1.37', '1.36']

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

    effectAttributesAllVersion = {}
    conditionAttributesAllVersion = {}
    for version in INCLUDING_VERSION:
        with open(f'{package_path}/versions/DE/v{version}/effects.json', 'r', encoding='utf-8') as f:
            effectStruct = json.load(f)
        with open(f'{package_path}/versions/DE/v{version}/conditions.json', 'r', encoding='utf-8') as f:
            conditionStruct = json.load(f)

        effectAttributes = {}
        for effect in effectStruct:
            if 'attributes' in effectStruct[effect]:
                attributes = effectStruct[effect]['attributes']
                if 'effect_type' in attributes:
                    attributes.remove('effect_type')
                if 'quantity_float' in attributes:
                    # quantity_float is a hidden attr in ASP
                    attributes.remove('quantity_float')
                effectAttributes[int(effect)] = attributes
        effectAttributesAllVersion[version] = effectAttributes

        conditionAttributes = {}
        for condition in conditionStruct:
            if 'attributes' in conditionStruct[condition]:
                attributes = conditionStruct[condition]['attributes']
                if 'condition_type' in attributes:
                    attributes.remove('condition_type')
                conditionAttributes[int(condition)] = attributes
        conditionAttributesAllVersion[version] = conditionAttributes

    with open(outPath, 'w', encoding='utf-8') as f:
        f.write('EFFECT_ATTRIBUTES_ALL_VERSION = ' + str(effectAttributesAllVersion) + '\n')
        f.write('CONDITION_ATTRIBUTES_ALL_VERSION = ' + str(conditionAttributesAllVersion) + '\n')

if __name__ == '__main__':
    workDir = os.path.dirname(__file__)

    if os.path.isdir(f'{workDir}/_prebuild') == False:
        os.makedirs(f'{workDir}/_prebuild')
    createDummyVersion(f'{workDir}/_prebuild/version.py')
    print('Created ' + '_prebuild/version.py')
    createIcon(iconPath='AoE2TC.ico', outPath=f'{workDir}/_prebuild/AoE2TC_icon.py')
    print('Created ' + '_prebuild/AoE2TC_icon.py')
    createCeAttributeDict(outPath=f'{workDir}/_prebuild/CeAttributes.py')
    print('Created ' + '_prebuild/CeAttributes.py')
    print('prebuild done.')