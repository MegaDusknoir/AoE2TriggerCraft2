from _prebuild.CeAttributes import CONDITION_ATTRIBUTES_ALL_VERSION, EFFECT_ATTRIBUTES_ALL_VERSION
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

class CeAttributes:
    scenario_version = '.'.join(map(str, AoE2DEScenario.LATEST_VERSION))

    class CeAttributesVersionNotSupportedError(Exception):
        pass

    @classmethod
    def condition(cls):
        return CONDITION_ATTRIBUTES_ALL_VERSION[cls.scenario_version]

    @classmethod
    def effect(cls):
        return EFFECT_ATTRIBUTES_ALL_VERSION[cls.scenario_version]

    @classmethod
    def setVersion(cls, version):
        if cls.isSupportedVersion(version):
            cls.scenario_version = version
        else:
            raise cls.CeAttributesVersionNotSupportedError

    @classmethod
    def isSupportedVersion(cls, version):
        return version in cls.getAllSupportVersion()

    @classmethod
    def getAllSupportVersion(cls):
        return list(CONDITION_ATTRIBUTES_ALL_VERSION.keys())
