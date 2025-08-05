import re
from Localization import *

from AoE2ScenarioParser.objects.data_objects.trigger import Trigger
from AoE2ScenarioParser.objects.data_objects.effect import Effect
from AoE2ScenarioParser.objects.data_objects.condition import Condition
from AoE2ScenarioParser.datasets.conditions import ConditionId
from AoE2ScenarioParser.datasets.effects import EffectId
from AoE2ScenarioParser.exceptions.asp_exceptions import UnsupportedAttributeError, UnsupportedVersionError


class FindCFunction():
    FUNC_NAME_RE = None
    @classmethod
    def findFirstCFunctionName(cls, code: str) -> str | None:
        """提取字符串中首个 C 语言函数定义的函数名"""
        if cls.FUNC_NAME_RE == None:
            cls.FUNC_NAME_RE = re.compile(
                r'''
                \b                                  # 单词边界
                ([\w\*\s]+?)                        # 返回类型部分（非贪婪）
                \s+                                 # 至少一个空格
                (?P<name>\w+)                       # 函数名
                \s*                                 # 可选空格
                \([^)]*\)                           # 参数列表（不处理嵌套括号）
                \s*                                 # 可选空格
                \{                                  # 函数体开始
                ''',
                re.VERBOSE | re.DOTALL
            )
        match = cls.FUNC_NAME_RE.search(code)
        if match:
            return match.group("name")
        return None

def getMessageAbstract(message: str) -> str:
    default_limit: int = TEXT.get('fmtMessageLengthLimit', 16)
    if len(message) > default_limit:
        return repr(message[0 : default_limit - 3] + '...')[1:-1]
    else:
        return repr(message)[1:-1]

def getAttributesAbstract(attribute: int, attackClass: int) -> str:
    if attribute == 8:
        return TEXT['fmtStringAttackTypeCombine'].format(TEXT['datasetDamageClass'][attackClass])
    elif attribute == 9:
        return TEXT['fmtStringArmorTypeCombine'].format(TEXT['datasetDamageClass'][attackClass])
    else:
        return TEXT['datasetObjectAttribute'][attribute]

def getConditionInverted(inverted:int) -> str:
    if inverted == 0:
        return TEXT['fmtStringIf']
    elif inverted == 1:
        return TEXT['fmtStringNot']
    
def getUnitAbstract(unit: int) -> str:
    if unit == -1:
        return TEXT['comboValueNone']
    else:
        return f'<U{unit}>'

def getUnitsAbstract(units: list[int], max: int | None=None) -> str:
    if len(units) == 0:
        return TEXT['comboValueNone']
    elif len(units) == 1:
        return getUnitAbstract(units[0])
    else:
        abstractList = []
        for i, unit in enumerate(units):
            if max != None and i >= max:
                abstractList.append('...')
                break
            abstractList.append(getUnitAbstract(unit))
        return f'[{",".join(abstractList)}]'

def getUnitListName(unitList: int) -> str:
    """Get the localized name of a unit based on its ID."""
    if unitList == -1:
        return TEXT['comboValueNone']
    else:
        return UNIT_NAME.get(unitList, {'name': f'<UL{unitList}>'})['name']

def getUnitListGroupTypeAbstract(unitList: int, unitGroup: int,
                                 unitType: int) -> str:
    if unitList != -1:
        return getUnitListName(unitList)
    elif unitGroup != -1:
        return TEXT['datasetObjectClass'].get(unitGroup, f'<UG{unitGroup}>')
    elif unitType != -1:
        return TEXT['datasetObjectType'].get(unitType, f'<UT{unitType}>')
    else:
        return TEXT['fmtStringAnyUnit']
def getNonSpecificUnitAbstract(unitList: int, unitGroup: int,
                               unitType: int, unitPlayer: int=None,
                               unit: int | list[int]=None,
                               area_x1: int=None, area_y1: int=None,
                               area_x2: int=None, area_y2: int=None,
                               allowAreaEmpty: bool=False,
                               unitState: int=None) -> str:
    if unit != None:
        # 指定特定单位优先级最高
        if type(unit) == list:
            if len(unit) != 0:
                return getUnitsAbstract(unit)
        else:
            if unit != -1:
                return getUnitAbstract(unit)
    unitPLGTAbstract = getUnitListGroupTypeAbstract(unitList, unitGroup, unitType)
    if unitState != None and unitState != 2:
        # 检查是否可以指定状态
        unitPLGTAbstract = TEXT['fmtStringStateUnitCombineFormat'] \
            .format(TEXT['datasetObjectState'][unitState],
                    unitPLGTAbstract)
    if unitPlayer != None:
        # 检查是否可以指定玩家
        unitPLGTAbstract = TEXT['fmtStringPlayerUnitCombineFormat']\
            .format(getPlayerAbstract(unitPlayer),
                    unitPLGTAbstract)
    if area_x1 != None and area_y1 != None:
        # 检查是否可以指定区域
        areaAbstract = getAreaAbstract(area_x1, area_y1, area_x2, area_y2, allowAreaEmpty)
        unitPLGTAbstract = TEXT['fmtStringAreaUnitCombineFormat']\
            .format(areaAbstract,
                    unitPLGTAbstract)
    return unitPLGTAbstract

def getPlayerAbstract(playerId: int) -> str:
    if playerId == 0:
        return TEXT['fmtStringGaia']
    else:
        return TEXT['fmtStringPlayerN'].format(playerId)

def getResourceAbstract(resourceId: int) -> str:
    return RESOURCE_NAME.get(resourceId, f'<R{resourceId}>')

def getTechnologyAbstract(techId: int) -> str:
    return TECH_NAME.get(techId, f'<T{techId}>')

def getCostAbstract(costList: list[tuple[int, int]]) -> int:
    costAbstractList = []
    for cost in costList:
        if cost[1] != 0 and cost[1] != -1:
            costAbstractList.append('{1}{0}'.format(getResourceAbstract(cost[0]), cost[1]))
    if costAbstractList == []:
        return TEXT['fmtCostFree']
    else:
        return ','.join(costAbstractList)

def getLocationAbstract(location_x: int, location_y: int,
                        location_object_reference: int=None,
                        allowEmpty=False) -> str:
    if location_object_reference != None and location_object_reference != -1:
        return getUnitAbstract(location_object_reference)
    else:
        return getAreaAbstract(location_x, location_y, allowEmpty=allowEmpty)

def getAreaAbstract(area_x1: int, area_y1: int,
                    area_x2: int=None, area_y2: int=None,
                    allowEmpty=False) -> str:
    if area_x1 == -1 and area_y1 == -1 and allowEmpty == True:
        return TEXT['fmtStringFullMap']
    if (area_x2 == None and area_y2 == None) or (area_x2 == area_x1 and area_y2 == area_y1):
        return f'({area_x1},{area_y1})'
    else:
        return f'({area_x1},{area_y1})~({area_x2},{area_y2})'

def abstractCondition(condition: Condition) -> str:
    typeKey = condition.condition_type
    if typeKey in TEXT['conditionDescriptionFormat']:
        if condition.inverted == 0 or condition.inverted == -1:
            formatString = TEXT['conditionDescriptionFormat'][typeKey]
        else:
            formatString = TEXT['conditionDescriptionInvertFormat'][typeKey]
            if typeKey not in TEXT['conditionDescriptionInvertFormat']:
                formatString = TEXT['fmtStringNot'] + ' ' + TEXT['conditionDescriptionFormat'][typeKey]
        try:
            match condition.condition_type:
                case ConditionId.NONE:
                    return formatString
                case ConditionId.BRING_OBJECT_TO_AREA:
                    return formatString.format(getUnitAbstract(condition.unit_object),
                                            getAreaAbstract(condition.area_x1, condition.area_y1,
                                                            condition.area_x2, condition.area_y2))
                case ConditionId.BRING_OBJECT_TO_OBJECT:
                    return formatString.format(getUnitAbstract(condition.unit_object),
                                            getUnitAbstract(condition.next_object))
                case ConditionId.OWN_OBJECTS:
                    includeCWO = TEXT['fmtStringIncludeCWO'] \
                        if condition.include_changeable_weapon_objects == 1 else ''
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getNonSpecificUnitAbstract(
                                                condition.object_list,
                                                condition.object_group,
                                                condition.object_type),
                                            condition.quantity,
                                            includeCWO)
                case ConditionId.OWN_FEWER_OBJECTS:
                    includeCWO = TEXT['fmtStringIncludeCWO'] \
                        if condition.include_changeable_weapon_objects == 1 else ''
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getNonSpecificUnitAbstract(
                                                condition.object_list,
                                                condition.object_group,
                                                condition.object_type
                                                ),
                                            condition.quantity,
                                            getAreaAbstract(condition.area_x1, condition.area_y1,
                                                            condition.area_x2, condition.area_y2,
                                                            allowEmpty=True),
                                            includeCWO)
                case ConditionId.OBJECTS_IN_AREA:
                    includeCWO = TEXT['fmtStringIncludeCWO'] \
                        if condition.include_changeable_weapon_objects == 1 else ''
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getNonSpecificUnitAbstract(
                                                condition.object_list,
                                                condition.object_group,
                                                condition.object_type
                                                ),
                                            condition.quantity,
                                            getAreaAbstract(condition.area_x1, condition.area_y1,
                                                            condition.area_x2, condition.area_y2,
                                                            allowEmpty=True),
                                            TEXT['datasetObjectState'][condition.object_state],
                                            includeCWO)
                case ConditionId.DESTROY_OBJECT:
                    return formatString.format(getUnitAbstract(condition.unit_object))
                case ConditionId.CAPTURE_OBJECT:
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getUnitAbstract(condition.unit_object))
                case ConditionId.ACCUMULATE_ATTRIBUTE:
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getResourceAbstract(condition.attribute), condition.quantity)
                case ConditionId.RESEARCH_TECHNOLOGY:
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getTechnologyAbstract(condition.technology))
                case ConditionId.TIMER:
                    return formatString.format(condition.timer)
                case ConditionId.OBJECT_SELECTED:
                    return formatString.format(getUnitAbstract(condition.unit_object))
                case ConditionId.AI_SIGNAL:
                    return formatString.format(condition.ai_signal)
                case ConditionId.PLAYER_DEFEATED:
                    return formatString.format(getPlayerAbstract(condition.source_player))
                case ConditionId.OBJECT_HAS_TARGET:
                    return formatString.format(getUnitAbstract(condition.unit_object), 
                                            getNonSpecificUnitAbstract(
                                                condition.object_list,
                                                condition.object_group,
                                                condition.object_type,
                                                unit=condition.next_object
                                                ))
                case ConditionId.OBJECT_VISIBLE:
                    return formatString.format(getUnitAbstract(condition.unit_object))
                case ConditionId.OBJECT_NOT_VISIBLE:
                    return formatString.format(getUnitAbstract(condition.unit_object))
                case ConditionId.RESEARCHING_TECH:
                    return formatString.format(getPlayerAbstract(condition.source_player), getTechnologyAbstract(condition.technology))
                case ConditionId.UNITS_GARRISONED:
                    return formatString.format(getUnitAbstract(condition.unit_object), condition.quantity)
                case ConditionId.DIFFICULTY_LEVEL:
                    return formatString.format(TEXT['datasetDifficultyLevel'][condition.quantity])
                case ConditionId.CHANCE:
                    return formatString.format(condition.quantity)
                case ConditionId.TECHNOLOGY_STATE:
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getTechnologyAbstract(condition.technology),
                                            TEXT['datasetTechnologyState'][condition.quantity])
                case ConditionId.VARIABLE_VALUE:
                    return formatString.format(condition.variable,
                                            condition.quantity,
                                            TEXT['datasetComparison'][condition.comparison])
                case ConditionId.OBJECT_HP:
                    return formatString.format(getUnitAbstract(condition.unit_object),
                                            condition.quantity,
                                            TEXT['datasetComparison'][condition.comparison])
                case ConditionId.DIPLOMACY_STATE:
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getPlayerAbstract(condition.target_player),
                                            TEXT['datasetDiplomacyState'][condition.quantity])
                case ConditionId.SCRIPT_CALL:
                    return formatString
                case ConditionId.OBJECT_SELECTED_MULTIPLAYER:
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getUnitAbstract(condition.unit_object))
                case ConditionId.OBJECT_VISIBLE_MULTIPLAYER:
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getUnitAbstract(condition.unit_object))
                case ConditionId.OBJECT_HAS_ACTION:
                    return formatString.format(getUnitAbstract(condition.unit_object),
                                            getNonSpecificUnitAbstract(
                                                condition.object_list,
                                                condition.object_group,
                                                condition.object_type,
                                                unit=condition.next_object
                                                ),
                                            TEXT['datasetUnitAIAction'][condition.unit_ai_action])
                case ConditionId.OR:
                    return formatString
                case ConditionId.AI_SIGNAL_MULTIPLAYER:
                    return formatString.format(condition.ai_signal)
                case ConditionId.BUILDING_IS_TRADING:
                    return formatString.format(getUnitAbstract(condition.unit_object))
                case ConditionId.DISPLAY_TIMER_TRIGGERED:
                    return formatString.format(condition.timer_id)
                case ConditionId.VICTORY_TIMER:
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            TEXT['datasetVictoryTimerType'][condition.victory_timer_type],
                                            condition.quantity,
                                            TEXT['datasetComparison'][condition.comparison])
                case ConditionId.AND:
                    return formatString
                case ConditionId.DECISION_TRIGGERED:
                    return formatString.format(condition.decision_id,
                                            TEXT['datasetDecisionOption'][condition.decision_option])
                case ConditionId.OBJECT_ATTACKED:
                    return formatString.format(getPlayerAbstract(condition.source_player),
                                            getNonSpecificUnitAbstract(
                                                condition.object_list,
                                                condition.object_group,
                                                condition.object_type
                                                ),
                                            getUnitAbstract(condition.unit_object),
                                            condition.quantity)
                case ConditionId.HERO_POWER_CAST:
                    return formatString.format(getPlayerAbstract(condition.source_player))
                case ConditionId.COMPARE_VARIABLES:
                    return formatString.format(condition.variable,
                                            condition.variable2,
                                            TEXT['datasetComparison'][condition.comparison])
                case ConditionId.TRIGGER_ACTIVE:
                    if condition.trigger_id >= 0 and condition.trigger_id < len(condition.get_scenario().trigger_manager.triggers):
                        triggerName = condition.get_scenario().trigger_manager.get_trigger(condition.trigger_id).name
                    else:
                        triggerName = '<-1>'
                    return formatString.format(triggerName)
                case _:
                    return CONDITION_NAME[condition.condition_type]
        except UnsupportedAttributeError as e:
            print(f"Unsupported attribute: {e}")
            return CONDITION_NAME[condition.condition_type]
        except TypeError as e:
            print(f"Python TypeError at {condition.condition_type}: {e}")
            return CONDITION_NAME[condition.condition_type]
    else:
        return CONDITION_NAME[condition.condition_type]

def abstractEffect(effect: Effect) -> str:
    typeKey = effect.effect_type
    if typeKey in TEXT['effectDescriptionFormat']:
        formatString = TEXT['effectDescriptionFormat'][typeKey]
        try:
            match effect.effect_type:
                case EffectId.NONE:
                    return formatString
                case EffectId.CHANGE_DIPLOMACY:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getPlayerAbstract(effect.target_player),
                                            TEXT['datasetDiplomacyState'][effect.diplomacy])
                case EffectId.RESEARCH_TECHNOLOGY:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            TEXT['fmtStringForceResearch'] \
                                                if effect.force_research_technology else '')
                case EffectId.SEND_CHAT:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getMessageAbstract(effect.message))
                case EffectId.PLAY_SOUND:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getLocationAbstract(effect.location_x,
                                                                effect.location_y,
                                                                effect.location_object_reference,
                                                                allowEmpty=True),
                                            effect.sound_name)
                case EffectId.TRIBUTE:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getPlayerAbstract(effect.target_player),
                                            effect.quantity,
                                            getResourceAbstract(effect.tribute_list))
                case EffectId.UNLOCK_GATE:
                    return formatString.format(getUnitsAbstract(effect.selected_object_ids))
                case EffectId.LOCK_GATE:
                    return formatString.format(getUnitsAbstract(effect.selected_object_ids))
                case EffectId.ACTIVATE_TRIGGER:
                    if effect.trigger_id >= 0 and effect.trigger_id < len(effect.get_scenario().trigger_manager.triggers):
                        triggerName = effect.get_scenario().trigger_manager.get_trigger(effect.trigger_id).name
                    else:
                        triggerName = '<-1>'
                    return formatString.format(triggerName)
                case EffectId.DEACTIVATE_TRIGGER:
                    if effect.trigger_id >= 0 and effect.trigger_id < len(effect.get_scenario().trigger_manager.triggers):
                        triggerName = effect.get_scenario().trigger_manager.get_trigger(effect.trigger_id).name
                    else:
                        triggerName = '<-1>'
                    return formatString.format(triggerName)
                case EffectId.AI_SCRIPT_GOAL:
                    return formatString.format(effect.ai_script_goal)
                case EffectId.CREATE_OBJECT:
                    if effect.facet == -1:
                        faceTo = ''
                    else:
                        faceTo = TEXT['fmtStringFaceTo'].format(TEXT['dataUnitFaceToName'].get(effect.facet, f'<{effect.facet}>'))
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id),
                                            getLocationAbstract(effect.location_x, effect.location_y),
                                            faceTo)
                case EffectId.TASK_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getLocationAbstract(effect.location_x,
                                                                effect.location_y,
                                                                effect.location_object_reference),
                                            TEXT['datasetActionType'][effect.action_type])
                case EffectId.DECLARE_VICTORY:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            TEXT['fmtStringVictory'] if effect.enabled == 1 \
                                                else TEXT['fmtStringDefeat'])
                case EffectId.KILL_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.REMOVE_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True,
                                                                        unitState=effect.object_state))
                case EffectId.CHANGE_VIEW:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getLocationAbstract(effect.location_x, effect.location_y),
                                            TEXT['fmtStringViewScroll'] if effect.scroll == 1 \
                                                else TEXT['fmtStringViewSwitch'],
                                            TEXT['fmtChangeViewTime'].format(effect.quantity) \
                                                    if effect.quantity > 0 else '')
                case EffectId.UNLOAD:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getLocationAbstract(effect.location_x,
                                                                effect.location_y,
                                                                effect.location_object_reference))
                case EffectId.CHANGE_OWNERSHIP:
                    if effect.flash_object == 1:
                        return TEXT['effectDescriptionFormatShift']['1'].format(\
                            getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                            effect.object_type, effect.source_player,
                                                                            effect.selected_object_ids,
                                                                            effect.area_x1, effect.area_y1,
                                                                            effect.area_x2, effect.area_y2,
                                                                            allowAreaEmpty=True),
                            getPlayerAbstract(effect.target_player))
                    else:
                        return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                            effect.object_type, effect.source_player,
                                                                            effect.selected_object_ids,
                                                                            effect.area_x1, effect.area_y1,
                                                                            effect.area_x2, effect.area_y2,
                                                                            allowAreaEmpty=True),
                                                getPlayerAbstract(effect.target_player))
                case EffectId.PATROL:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getLocationAbstract(effect.location_x,
                                                                effect.location_y))
                case EffectId.DISPLAY_INSTRUCTIONS:
                    return formatString.format(getMessageAbstract(effect.message))
                case EffectId.CLEAR_INSTRUCTIONS:
                    return formatString.format(effect.instruction_panel_position)
                case EffectId.FREEZE_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.USE_ADVANCED_BUTTONS:
                    return formatString
                case EffectId.DAMAGE_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            effect.quantity)
                case EffectId.PLACE_FOUNDATION:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id),
                                            getLocationAbstract(effect.location_x,
                                                                effect.location_y))
                case EffectId.CHANGE_OBJECT_NAME:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getMessageAbstract(effect.message))
                case EffectId.CHANGE_OBJECT_HP:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            effect.quantity,
                                            TEXT['datasetOperation'][effect.operation])
                case EffectId.CHANGE_OBJECT_ATTACK:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            effect.armour_attack_quantity,
                                            TEXT['datasetOperation'][effect.operation],
                                            TEXT['datasetDamageClass'].get(effect.armour_attack_class,
                                                                            f'<A{effect.armour_attack_class}>'))
                case EffectId.STOP_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.ATTACK_MOVE:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getLocationAbstract(effect.location_x,
                                                                effect.location_y,
                                                                effect.location_object_reference))
                case EffectId.CHANGE_OBJECT_ARMOR:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            effect.armour_attack_quantity,
                                            TEXT['datasetOperation'][effect.operation],
                                            TEXT['datasetDamageClass'].get(effect.armour_attack_class,
                                                                            f'<A{effect.armour_attack_class}>'))
                case EffectId.CHANGE_OBJECT_RANGE:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            effect.quantity,
                                            TEXT['datasetOperation'][effect.operation])
                case EffectId.CHANGE_OBJECT_SPEED:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            effect.quantity*10)
                case EffectId.HEAL_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            effect.quantity)
                case EffectId.TELEPORT_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getLocationAbstract(effect.location_x,
                                                                effect.location_y))
                case EffectId.CHANGE_OBJECT_STANCE:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            TEXT['datasetAttackStance'][effect.attack_stance])
                case EffectId.DISPLAY_TIMER:
                    return formatString.format(effect.timer,
                                            effect.display_time,
                                            TEXT['datasetTimeUnit'].get(effect.time_unit,
                                                                            f'<{effect.time_unit}>'),
                                            TEXT['fmtTimerReset'] if effect.reset_timer == 1 \
                                                else TEXT['fmtTimerCreate'],
                                            getMessageAbstract(effect.message))
                case EffectId.ENABLE_DISABLE_OBJECT:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id),
                                            TEXT['fmtDisable'] if effect.enabled == 0 else TEXT['fmtEnable'])
                case EffectId.ENABLE_DISABLE_TECHNOLOGY:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            TEXT['fmtDisable'] if effect.enabled == 0 else TEXT['fmtEnable'])
                # checked to here
                case EffectId.CHANGE_OBJECT_COST:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id),
                                            getCostAbstract([
                                                (effect.resource_1, effect.resource_1_quantity),
                                                (effect.resource_2, effect.resource_2_quantity),
                                                (effect.resource_3, effect.resource_3_quantity)
                                                ]))
                case EffectId.SET_PLAYER_VISIBILITY:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getPlayerAbstract(effect.target_player),
                                            TEXT['datasetVisibilityState'][effect.visibility_state])
                case EffectId.CHANGE_OBJECT_ICON:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getUnitListName(effect.object_list_unit_id_2))
                case EffectId.REPLACE_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getPlayerAbstract(effect.target_player),
                                            getUnitListName(effect.object_list_unit_id_2))
                case EffectId.CHANGE_OBJECT_DESCRIPTION:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id),
                                            getMessageAbstract(effect.message))
                case EffectId.CHANGE_PLAYER_NAME:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getMessageAbstract(effect.message))
                case EffectId.CHANGE_TRAIN_LOCATION:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id),
                                            getUnitListName(effect.object_list_unit_id_2),
                                            effect.button_location)
                case EffectId.CHANGE_TECHNOLOGY_LOCATION:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            getUnitListName(effect.object_list_unit_id_2),
                                            effect.button_location)
                case EffectId.CHANGE_CIVILIZATION_NAME:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getMessageAbstract(effect.message))
                case EffectId.CREATE_GARRISONED_OBJECT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id_2))
                case EffectId.ACKNOWLEDGE_AI_SIGNAL:
                    return formatString.format(effect.ai_signal_value)
                case EffectId.MODIFY_ATTRIBUTE:
                    effect.armour_attack_quantity, effect.item_id
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id),
                                            getAttributesAbstract(effect.object_attributes,
                                                                    effect.armour_attack_class),
                                            effect.quantity,
                                            TEXT['datasetOperation'][effect.operation],
                                            getMessageAbstract(effect.message))
                case EffectId.MODIFY_RESOURCE:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getResourceAbstract(effect.tribute_list),
                                            effect.quantity,
                                            TEXT['datasetOperation'][effect.operation])
                case EffectId.MODIFY_RESOURCE_BY_VARIABLE:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getResourceAbstract(effect.tribute_list),
                                            effect.variable,
                                            TEXT['datasetOperation'][effect.operation])
                case EffectId.SET_BUILDING_GATHER_POINT:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getLocationAbstract(effect.location_x,
                                                                effect.location_y))
                case EffectId.SCRIPT_CALL:
                    scriptAbstract = FindCFunction.findFirstCFunctionName(effect.message)
                    if scriptAbstract == None:
                        scriptAbstract = getMessageAbstract(effect.message)
                    return formatString.format(scriptAbstract)
                    # return formatString.format(effect.message[0:effect.message.find('{')].strip('void ').strip() + '...')
                case EffectId.CHANGE_VARIABLE:
                    return formatString.format(effect.variable,
                                            effect.quantity,
                                            TEXT['datasetOperation'][effect.operation])
                case EffectId.CLEAR_TIMER:
                    return formatString.format(effect.timer)
                case EffectId.CHANGE_OBJECT_PLAYER_COLOR:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            TEXT['datasetPlayerColorId'][effect.player_color])
                case EffectId.CHANGE_OBJECT_CIVILIZATION_NAME:
                    return formatString.format(getNonSpecificUnitAbstract(-1, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getMessageAbstract(effect.message))
                case EffectId.CHANGE_OBJECT_PLAYER_NAME:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getMessageAbstract(effect.message))
                case EffectId.DISABLE_UNIT_TARGETING:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.ENABLE_UNIT_TARGETING:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.CHANGE_TECHNOLOGY_COST:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            getCostAbstract([
                                                (effect.resource_1, effect.resource_1_quantity),
                                                (effect.resource_2, effect.resource_2_quantity),
                                                (effect.resource_3, effect.resource_3_quantity)
                                                ]))
                case EffectId.CHANGE_TECHNOLOGY_RESEARCH_TIME:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            effect.quantity)
                case EffectId.CHANGE_TECHNOLOGY_NAME:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            getMessageAbstract(effect.message))
                case EffectId.CHANGE_TECHNOLOGY_DESCRIPTION:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            getMessageAbstract(effect.message))
                case EffectId.ENABLE_TECHNOLOGY_STACKING:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            effect.quantity if effect.quantity != -1 \
                                                else TEXT['fmtUnlimitedTimes'])
                case EffectId.DISABLE_TECHNOLOGY_STACKING:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology))
                case EffectId.ACKNOWLEDGE_MULTIPLAYER_AI_SIGNAL:
                    return formatString.format(effect.ai_signal_value)
                case EffectId.DISABLE_OBJECT_SELECTION:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.ENABLE_OBJECT_SELECTION:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.CHANGE_COLOR_MOOD:
                    return formatString.format(TEXT['datasetColorMood'].get(effect.color_mood,
                                                                            f'<{effect.color_mood}>'),
                                            TEXT['fmtChangeViewTime'].format(effect.quantity) \
                                                    if effect.quantity > 0 else '')
                case EffectId.ENABLE_OBJECT_DELETION:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.DISABLE_OBJECT_DELETION:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.TRAIN_UNIT:
                    getPlayerAbstract(effect.source_player)
                    if effect.selected_object_ids != []:
                        getUnitsAbstract(effect.selected_object_ids)
                    else:
                        getAreaAbstract(effect.area_x1, effect.area_y1,
                                        effect.area_x2, effect.area_y2)
                    effect.object_list_unit_id,
                    getLocationAbstract(effect.location_x, effect.location_y)
                    # Todo
                    return formatString
                case EffectId.INITIATE_RESEARCH:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getUnitsAbstract(effect.selected_object_ids),
                                            getTechnologyAbstract(effect.technology))
                case EffectId.CREATE_OBJECT_ATTACK:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            effect.armour_attack_quantity,
                                            TEXT['datasetOperation'][effect.operation],
                                            TEXT['datasetDamageClass'].get(effect.armour_attack_class,
                                                                            f'<A{effect.armour_attack_class}>'))
                case EffectId.CREATE_OBJECT_ARMOR:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, effect.object_group,
                                                                        effect.object_type, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            effect.armour_attack_quantity,
                                            TEXT['datasetOperation'][effect.operation],
                                            TEXT['datasetDamageClass'].get(effect.armour_attack_class,
                                                                            f'<A{effect.armour_attack_class}>'))
                case EffectId.MODIFY_ATTRIBUTE_BY_VARIABLE:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id),
                                            getAttributesAbstract(effect.object_attributes,
                                                                    effect.armour_attack_class),
                                            effect.variable,
                                            TEXT['datasetOperation'][effect.operation],
                                            getMessageAbstract(effect.message))
                case EffectId.SET_OBJECT_COST:
                    # Todo
                    return formatString
                case EffectId.LOAD_KEY_VALUE:
                    # Todo
                    return formatString
                case EffectId.STORE_KEY_VALUE:
                    # Todo
                    return formatString
                case EffectId.DELETE_KEY:
                    # Todo
                    return formatString
                case EffectId.CHANGE_TECHNOLOGY_ICON:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            effect.quantity)
                case EffectId.CHANGE_TECHNOLOGY_HOTKEY:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            getTechnologyAbstract(effect.technology),
                                            effect.quantity)
                case EffectId.MODIFY_VARIABLE_BY_RESOURCE:
                    return formatString.format(effect.variable,
                                            getPlayerAbstract(effect.source_player),
                                            getResourceAbstract(effect.tribute_list),
                                            TEXT['datasetOperation'][effect.operation])
                case EffectId.MODIFY_VARIABLE_BY_ATTRIBUTE:
                    getMessageAbstract(effect.message)
                    return formatString.format(effect.variable,
                                            getPlayerAbstract(effect.source_player),
                                            getUnitListName(effect.object_list_unit_id),
                                            getAttributesAbstract(effect.object_attributes,
                                                                    effect.armour_attack_class),
                                            TEXT['datasetOperation'][effect.operation])
                case EffectId.CHANGE_OBJECT_CAPTION:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True),
                                            getMessageAbstract(effect.message))
                case EffectId.CHANGE_PLAYER_COLOR:
                    return formatString.format(getPlayerAbstract(effect.source_player),
                                            TEXT['datasetPlayerColorId'][effect.player_color])
                case EffectId.CREATE_DECISION:
                    # Todo
                    return formatString
                # 91 ~ 97 reserved
                case EffectId.DISABLE_UNIT_ATTACKABLE:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.ENABLE_UNIT_ATTACKABLE:
                    return formatString.format(getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case EffectId.MODIFY_VARIABLE_BY_VARIABLE:
                    return formatString.format(effect.variable,
                                            effect.variable2,
                                            TEXT['datasetOperation'][effect.operation])
                case EffectId.COUNT_UNITS_INTO_VARIABLE:
                    return formatString.format(effect.variable2,
                                            getNonSpecificUnitAbstract(effect.object_list_unit_id, -1,
                                                                        -1, effect.source_player,
                                                                        effect.selected_object_ids,
                                                                        effect.area_x1, effect.area_y1,
                                                                        effect.area_x2, effect.area_y2,
                                                                        allowAreaEmpty=True))
                case _:
                    return EFFECT_NAME[effect.effect_type]
        except UnsupportedAttributeError as e:
            print(f"Unsupported attribute: {e}")
            return EFFECT_NAME[effect.effect_type]
        except TypeError as e:
            print(f"Python TypeError at {effect.effect_type}: {e}")
            return EFFECT_NAME[effect.effect_type]
    else:
        return EFFECT_NAME[effect.effect_type]
