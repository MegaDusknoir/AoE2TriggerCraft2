
import json
import locale
import os

class LanguageDict(dict):
    def __missing__(self, key):
        return f'<{key}>' if key not in self.PREDEFINE_DICT_NAMES else LanguageDict()

    PREDEFINE_DICT_NAMES = [
        'noticeValueAspSectionName',
        'conditionAttributeName',
        'conditionName',
        'conditionDescriptionFormat',
        'conditionDescriptionInvertFormat',
        'effectAttributeName',
        'effectName',
        'effectDescriptionFormatShift',
        'effectDescriptionFormat',
        'datasetObjectClass',
        'datasetObjectType',
        'datasetObjectState',
        'datasetDifficultyLevel',
        'datasetTechnologyState',
        'datasetComparison',
        'datasetDiplomacyState',
        'datasetUnitAIAction',
        'datasetVictoryTimerType',
        'datasetDecisionOption',
        'datasetActionType',
        'datasetOperation',
        'datasetDamageClass',
        'datasetAttackStance',
        'datasetVisibilityState',
        'datasetPlayerColorId',
        'dataUnitFaceToName',
        'datasetColorMood',
        'datasetTimeUnit',
        'datasetObjectAttribute'
    ]

TEXT = LanguageDict()

CONDITION_NAME = LanguageDict()
EFFECT_NAME = LanguageDict()

TECH_NAME = LanguageDict()
UNIT_NAME = LanguageDict()
RESOURCE_NAME = LanguageDict()

LOCALIZATION_DEFINES: list[dict[str,str]] = []

def keys_to_int(obj):
    if isinstance(obj, dict):
        return LanguageDict({int(k) if k.lstrip('-').isdigit() else k: v for k, v in obj.items()})
    return obj

def loadLocalizationDefines(workDir: str):
    if not os.path.isfile(f'{workDir}/resources/Localization.json'):
        raise FileNotFoundError(f"Localization defines file not found.")
    with open(f'{workDir}/resources/Localization.json', 'r', encoding='utf-8') as config:
        definesDict = json.load(config)
    if isinstance(definesDict, dict):
        defines = definesDict.get('languages', [])
        if len(defines) != 0:
            for define in defines:
                if isinstance(define, dict):
                    if isinstance(define.get('name'), str) \
                        and isinstance(define.get('code'), str):
                        LOCALIZATION_DEFINES[:] = defines
                    else:
                        raise TypeError(f"Localization defines format illegal.")
                else:
                    raise TypeError(f"Localization defines format illegal.")
        else:
            raise FileNotFoundError(f"Nothing in localization defines file.")
    else:
        raise TypeError(f"Localization defines format illegal.")

def loadLocalizedText(workDir: str, lang: str='auto') -> None:
    """Load localized text based on the system locale."""

    loadLocalizationDefines(workDir)

    localizedText = {}
    if lang == 'auto':
        lang = locale.getdefaultlocale()[0]
    if os.path.isfile(f'{workDir}/resources/{lang}/{lang}.json') == False:
        lang = LOCALIZATION_DEFINES[0]['code']
        if os.path.isfile(f'{workDir}/resources/{lang}/{lang}.json') == False:
            raise FileNotFoundError(f"Localization file not found.")

    with open(f'{workDir}/resources/{lang}/{lang}.json', 'r', encoding='utf-8') as config:
        localizedText[lang] = json.load(config, object_hook=keys_to_int)
    TEXT.clear()
    TEXT.update(localizedText[lang])

    localizationPath = f'{workDir}/resources/{lang}'

    for key in TEXT['conditionName']:
        CONDITION_NAME[int(key)] = TEXT['conditionName'][key]
    for key in TEXT['effectName']:
        EFFECT_NAME[int(key)] = TEXT['effectName'][key]
    if os.path.isfile(f'{localizationPath}/TechsName.json'):
        with open(f'{localizationPath}/TechsName.json', 'r', encoding='utf-8') as config:
            TECH_NAME.update(json.load(config, object_hook=keys_to_int))
    if os.path.isfile(f'{localizationPath}/UnitsName.json'):
        with open(f'{localizationPath}/UnitsName.json', 'r', encoding='utf-8') as config:
            UNIT_NAME.update(json.load(config, object_hook=keys_to_int))
    if os.path.isfile(f'{localizationPath}/ResourcesName.json'):
        with open(f'{localizationPath}/ResourcesName.json', 'r', encoding='utf-8') as config:
            RESOURCE_NAME.update(json.load(config, object_hook=keys_to_int))

def getConditionName(conditionType: int) -> str:
    """Get the localized name of a condition type."""
    if conditionType in CONDITION_NAME:
        return CONDITION_NAME[conditionType]
    else:
        return TEXT['conditionNameFormatForUnknown'].format(conditionType)

def getEffectName(effectType: int) -> str:
    """Get the localized name of an effect type."""
    if effectType in EFFECT_NAME:
        return EFFECT_NAME[effectType]
    else:
        return TEXT['effectNameFormatForUnknown'].format(effectType)
