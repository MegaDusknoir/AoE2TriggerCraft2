
import json
import locale
import os

from Util import OpenResourcesFile, ResourcesFileError

class LanguageDict(dict):
    def __missing__(self, key):
        return f'<{key}>' if key not in self.PREDEFINE_DICT_NAMES else LanguageDict()

    PREDEFINE_DICT_NAMES = [
        'messageNames',
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

    def definesDictCheck(dic: dict) -> bool:
        if not isinstance(dic, dict):
            return False
        defines = dic.get('languages', [])
        if len(defines) == 0:
            return False
        for define in defines:
            if not isinstance(define, dict):
                return False
            if not isinstance(define.get('name', None), str) \
                or not isinstance(define.get('code', None), str):
                return False
        LOCALIZATION_DEFINES[:] = defines
        return True

    with OpenResourcesFile(f'{workDir}/resources/Localization.json', encoding='utf-8') as fp:
        if fp:
            try:
                definesDict = json.load(fp)
            except json.decoder.JSONDecodeError:
                raise ResourcesFileError(f"Localization defines format illegal.") from None
        else:
            raise ResourcesFileError(f"Localization defines file not found / can not be accessed.")

    if not definesDictCheck(definesDict):
        raise ResourcesFileError(f"Localization defines format illegal.")

def loadLocalizedText(workDir: str, lang: str='auto') -> None:
    """Load localized text based on the system locale."""

    loadLocalizationDefines(workDir)

    localizedText = {}
    if lang == 'auto':
        lang = locale.getdefaultlocale()[0]
    if os.path.isfile(f'{workDir}/resources/{lang}/{lang}.json') == False:
        lang = LOCALIZATION_DEFINES[0]['code']

    with OpenResourcesFile(f'{workDir}/resources/{lang}/{lang}.json', encoding='utf-8') as fp:
        if fp:
            localizedText[lang] = json.load(fp, object_hook=keys_to_int)
        else:
            raise ResourcesFileError(f"Localization file not found.")
    TEXT.clear()
    TEXT.update(localizedText[lang])

    localizationPath = f'{workDir}/resources/{lang}'

    for key in TEXT['conditionName']:
        CONDITION_NAME[int(key)] = TEXT['conditionName'][key]
    for key in TEXT['effectName']:
        EFFECT_NAME[int(key)] = TEXT['effectName'][key]
    with OpenResourcesFile(f'{localizationPath}/TechsName.json', encoding='utf-8') as fp:
        if fp:
            TECH_NAME.update(json.load(fp, object_hook=keys_to_int))
    with OpenResourcesFile(f'{localizationPath}/UnitsName.json', encoding='utf-8') as fp:
        if fp:
            UNIT_NAME.update(json.load(fp, object_hook=keys_to_int))
    with OpenResourcesFile(f'{localizationPath}/TributesName.json', encoding='utf-8') as fp:
        if fp:
            RESOURCE_NAME.update(json.load(fp, object_hook=keys_to_int))

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
