from _prebuild.CeAttributes import (
    CONDITION_ATTRIBUTES_ALL_VERSION,
    CONDITION_ATTRIBUTE_DEFAULT_VALUE_ALL_VERSION,
    EFFECT_ATTRIBUTES_ALL_VERSION,
    EFFECT_ATTRIBUTE_DEFAULT_VALUE_ALL_VERSION,
)
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from Util import ScenarioVersion

class CeAttributes:
    scenarioVersion = ScenarioVersion(AoE2DEScenario.LATEST_VERSION)

    class CeAttributesVersionNotSupportedError(Exception):
        pass

    @classmethod
    def condition(cls) -> dict[int, list]:
        return CONDITION_ATTRIBUTES_ALL_VERSION[str(cls.scenarioVersion)]

    @classmethod
    def conditionDefaults(cls) -> dict[int, dict]:
        return CONDITION_ATTRIBUTE_DEFAULT_VALUE_ALL_VERSION[str(cls.scenarioVersion)]

    @classmethod
    def effectDefaults(cls) -> dict[int, dict]:
        return EFFECT_ATTRIBUTE_DEFAULT_VALUE_ALL_VERSION[str(cls.scenarioVersion)]

    @classmethod
    def effect(cls) -> dict[int, list]:
        return EFFECT_ATTRIBUTES_ALL_VERSION[str(cls.scenarioVersion)]

    @classmethod
    def setVersion(cls, version: ScenarioVersion):
        if cls.isSupportedVersion(version):
            cls.scenarioVersion = version
        else:
            raise cls.CeAttributesVersionNotSupportedError

    @classmethod
    def isSupportedVersion(cls, version: ScenarioVersion) -> bool:
        return str(version) in cls.getAllSupportVersion()

    @classmethod
    def getAllSupportVersion(cls):
        return list(CONDITION_ATTRIBUTES_ALL_VERSION.keys())
