from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Literal
from math import sqrt
from tkinter.constants import *
from tkinter.ttk import Widget
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText

from AoE2ScenarioParser.objects.data_objects.condition import Condition
from AoE2ScenarioParser.objects.data_objects.effect import Effect
from AoE2ScenarioParser.objects.data_objects.effect import _is_float_quantity_effect as isFloatQuantityEffect
from Localization import TEXT
from TriggerAbstract import *
from Util import FilteredMappedCombobox, IntListVar, IntValueButton, ListValueButton, MappedCombobox, PairValueEntry, Tooltip, ValueSelectButton, ZoomImageViewer
from WidgetLayout import CONDITION_WIDGET_FORM, EFFECT_WIDGET_FORM
from _prebuild.CeAttributes import CONDITION_ATTRIBUTES, EFFECT_ATTRIBUTES
from views.UnitInfo import UnitConstSelectButton, UnitsSelectButton

if TYPE_CHECKING:
    from main import TCWindow

class CeInfoView(ttk.Frame):
    @property
    def tl(self):
        return self.app.fTEditor.tvTriggerList

    @property
    def tm(self):
        return self.app.triggerManager

    EFFECTS_OBJATTR_WITH_AA_QUANTITY = [51, 104, 105]
    EFFECTS_OBJATTR_ONLY_AA_CLASS = [79, 87, 106]
    EFFECTS_OBJATTR_WITH_AA_CLASS = EFFECTS_OBJATTR_WITH_AA_QUANTITY + EFFECTS_OBJATTR_ONLY_AA_CLASS
    ATTRIBUTES_WITH_AA = [8, 9]

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        def __createAttributeWidgets(formDict, attribute, ceType:Condition|Effect) -> None:
            def object_attributes_widget(var: ttk.IntVar):
                curItem = self.app.fTEditor.tvTriggerList.focus()
                effect = self.app.fTEditor.getEffect(curItem)
                if effect is not None and effect.effect_type in self.EFFECTS_OBJATTR_WITH_AA_QUANTITY:
                    value = var.get()
                    if value in self.ATTRIBUTES_WITH_AA:
                        self.effectWidgetPacks[Effect]['armour_attack_quantity'].gridAttribute(
                            EFFECT_WIDGET_FORM['armour_attack_quantity'][1],
                            EFFECT_WIDGET_FORM['armour_attack_quantity'][2]
                        )
                        self.effectWidgetPacks[Effect]['armour_attack_class'].gridAttribute(
                            EFFECT_WIDGET_FORM['armour_attack_class'][1],
                            EFFECT_WIDGET_FORM['armour_attack_class'][2]
                        )
                        self.effectWidgetPacks[Effect]['quantity'].label.grid_forget()
                        self.effectWidgetPacks[Effect]['quantity'].grid_forget()
                    else:
                        self.effectWidgetPacks[Effect]['armour_attack_quantity'].label.grid_forget()
                        self.effectWidgetPacks[Effect]['armour_attack_quantity'].grid_forget()
                        self.effectWidgetPacks[Effect]['armour_attack_class'].label.grid_forget()
                        self.effectWidgetPacks[Effect]['armour_attack_class'].grid_forget()
                        self.effectWidgetPacks[Effect]['quantity'].gridAttribute(
                            EFFECT_WIDGET_FORM['quantity'][1],
                            EFFECT_WIDGET_FORM['quantity'][2]
                        )
                elif effect is not None and effect.effect_type in self.EFFECTS_OBJATTR_WITH_AA_CLASS:
                    value = var.get()
                    if value in self.ATTRIBUTES_WITH_AA:
                        self.effectWidgetPacks[Effect]['armour_attack_class'].gridAttribute(
                            EFFECT_WIDGET_FORM['armour_attack_class'][1],
                            EFFECT_WIDGET_FORM['armour_attack_class'][2]
                        )
                    else:
                        self.effectWidgetPacks[Effect]['armour_attack_class'].label.grid_forget()
                        self.effectWidgetPacks[Effect]['armour_attack_class'].grid_forget()

            if attribute not in self.effectWidgetPacks[ceType]:
                # Create widget in first use, not app start
                match formDict[attribute][0]:
                    case 'Entry':
                        self.effectWidgetPacks[ceType][attribute] = self.AttributeEntry(self.app, self, attribute, ceType, formDict[attribute][3])
                    case 'Combobox':
                        self.effectWidgetPacks[ceType][attribute] = self.AttributeCombobox(self.app, self,
                                                                                self.__constructEffectComboboxDicts(attribute),
                                                                                attribute, ceType)
                        if ceType == Effect and attribute == 'object_attributes':
                            self.effectWidgetPacks[ceType][attribute].variable.trace_add(
                                'write',
                                lambda *args, var=self.effectWidgetPacks[ceType][attribute].variable:object_attributes_widget(var))
                    case 'Checkbutton':
                        self.effectWidgetPacks[ceType][attribute] = self.AttributeCheckbutton(self.app, self, attribute, ceType)
                    case 'TextOrEntry':
                        self.effectWidgetPacks[ceType][attribute] = self.AttributeText(self.app, self, attribute, ceType)
                        self.effectWidgetPacks[ceType]['__variant_' + attribute] = self.AttributeEntry(self.app, self,
                                                                                            '__variant_' + attribute, ceType, formDict[attribute][3])
                    case 'MultiUnitSelector':
                        self.effectWidgetPacks[ceType][attribute] = self.AttributeUnitsButton(self.app, self, attribute, ceType, multi=True)
                    case 'SingleUnitSelector':
                        self.effectWidgetPacks[ceType][attribute] = self.AttributeUnitsButton(self.app, self, attribute, ceType, multi=False)
                    case 'UnitConstSelector':
                        self.effectWidgetPacks[ceType][attribute] = self.AttributeUnitConstButton(self.app, self, attribute, ceType)
                    case 'AreaSelector':
                        self.effectWidgetPacks[ceType][attribute] = self.AttributeAreaButton(self.app, self, attribute, ceType)
                    case _:
                        pass

        def __showAttributeWidgets(effectTypeId: int, nodeType: Literal['effect', 'condition']) -> None:
            for ce in self.effectWidgetPacks:
                for widgetPack in self.effectWidgetPacks[ce].values():
                    widgetPack: CeInfoView.AttributeWidget
                    widgetPack.label.grid_forget()
                    widgetPack.grid_forget()
            if nodeType == 'effect':
                attributesDict = EFFECT_ATTRIBUTES
                attrWidgetFormDict = EFFECT_WIDGET_FORM
                ceType = Effect
            else:
                attributesDict = CONDITION_ATTRIBUTES
                attrWidgetFormDict = CONDITION_WIDGET_FORM
                ceType = Condition
            for attribute in attributesDict.get(effectTypeId, []):
                __createAttributeWidgets(attrWidgetFormDict, attribute, ceType)
                if attribute not in self.effectWidgetPacks[ceType]:
                    continue
                widgetRef: CeInfoView.AttributeWidget = self.effectWidgetPacks[ceType][attribute]
                column, row = attrWidgetFormDict[attribute][1], attrWidgetFormDict[attribute][2]
                if column != -1 and row != -1:
                    match attrWidgetFormDict[attribute][0]:
                        case 'Entry':
                            widgetRef.gridAttribute(column, row)
                            if attribute == 'string_id' and effectTypeId in [26, 59, 60, 65, 88]:
                                widgetRef.gridAttribute(1, 1)
                        case 'Combobox':
                            widgetRef: CeInfoView.AttributeCombobox
                            if attribute == 'trigger_id':
                                # Get trigger name mapping
                                widgetRef.update_mapping( \
                                    {trigger.trigger_id: trigger.name for trigger in self.tm.triggers})
                            elif attribute == 'source_player' or attribute == 'target_player':
                                # Get player amount
                                widgetRef.update_mapping( \
                                    {i:getPlayerAbstract(i) for i in range(0, self.app.activeScenario.player_manager.active_players + 1)})
                            widgetRef.gridAttribute(column, row)
                        case 'Checkbutton':
                            widgetRef.gridAttribute(column, row)
                        case 'TextOrEntry':
                            if effectTypeId in [26, 48, 51, 56, 59, 60, 65, 79, 81, 82, 83, 87, 88, 104, 105, 106]:
                                # These use single line entry
                                if effectTypeId in [26, 59, 60, 65, 88]:
                                    # These entry's grid occupied by other attribute so grid elsewhere
                                    self.effectWidgetPacks[ceType]['__variant_' + attribute].gridAttribute(1, 2, columnspan=2)
                                else:
                                    self.effectWidgetPacks[ceType]['__variant_' + attribute].gridAttribute(column, row)
                            else:
                                # Else use large text widget
                                widgetRef.gridAttribute(column, row,
                                                        columnspan=2, rowspan=3)
                        case 'MultiUnitSelector' | 'SingleUnitSelector':
                            widgetRef.gridAttribute(column, row)
                        case 'UnitConstSelector':
                            widgetRef.gridAttribute(column, row)
                        case 'AreaSelector':
                            if 'location_object_reference' in attributesDict.get(effectTypeId, []) and \
                                attribute == 'location_x':
                                widgetRef.gridAttributeWithUnitSel(column, row)
                            else:
                                widgetRef.gridAttribute(column, row)
                        case _:
                            pass

        def __loadConditionType(*args):
            """Event when load condition type from scenario."""
            newType = self.wCType.variable.get()
            __showAttributeWidgets(newType, 'condition')

        def __modifyConditionType(*args):
            """Event when set condition type from widget."""
            newType = self.wCType.variable.get()
            curItem = self.tl.focus()
            condition = self.app.fTEditor.getCondition(curItem)
            if condition is not None:
                condition.condition_type = newType
                # Todo: reset condition arg
                self.updateConditionTreeNode(curItem, condition)
            self.app.itemSelect(None)
            # __showAttributeWidgets(newType, 'condition')

        def __loadEffectType(*args):
            """Event when load effect type from scenario."""
            newType = self.wEType.variable.get()
            __showAttributeWidgets(newType, 'effect')

        def __modifyEffectType(*args):
            """Event when set effect type from widget."""
            newType = self.wEType.variable.get()
            curItem = self.tl.focus()
            effect = self.app.fTEditor.getEffect(curItem)
            if effect is not None:
                effect.effect_type = newType
                # Todo: reset effect arg
                self.updateEffectTreeNode(curItem, effect)
            self.app.itemSelect(None)
            # __showAttributeWidgets(newType, 'effect')

        self.grid_columnconfigure(0, minsize=self.app.dpi(100))
        self.grid_columnconfigure(1, minsize=self.app.dpi(100))
        self.grid_columnconfigure(2, minsize=self.app.dpi(100))
        self.grid_columnconfigure(3, minsize=self.app.dpi(100), weight=2)
        self.grid_columnconfigure(4, weight=1)
        self.grid_columnconfigure(5, weight=1)
        self.grid_columnconfigure(6, weight=1)
        self.grid_columnconfigure(7, weight=1)
        self.grid_rowconfigure(6,weight=1)
        self.grid_rowconfigure(10,minsize=self.app.dpi(10)) # Bottom padding

        self.wCType = self.CeTypeCombobox(self.app, self, self.__constructEffectComboboxDicts('condition_type'),
                                            'condition_type', Condition, style='ceTypes.TCombobox')
        self.wEType = self.CeTypeCombobox(self.app, self, self.__constructEffectComboboxDicts('effect_type'),
                                            'effect_type', Effect, style='ceTypes.TCombobox')
        self.wCType.set_display_event(__modifyConditionType)
        self.wCType.set_variable_event(__loadConditionType)
        self.wEType.set_display_event(__modifyEffectType)
        self.wEType.set_variable_event(__loadEffectType)
        
        self.effectWidgetPacks: dict[type, dict[str, CeInfoView.AttributeWidget]] = {Condition: {}, Effect: {}}

    # region CEWidgets

    class AttributeWidget(Widget):
        def __init__(self):
            self.outer: TCWindow
            self.label: ttk.Label
            self.variable: ttk.Variable

        def gridAttribute(self, column, row, columnspan=1, rowspan=1) -> None:
            padLeft = self.outer.dpi((10, 0)) if column == 0 else self.outer.dpi((20, 0))
            self.label.grid(column=column, row=row * 2, columnspan=1, rowspan=1,
                            sticky=EW, padx=padLeft, pady=self.outer.dpi((10, 0)))
            self.grid(column=column, row=row * 2+1, columnspan=columnspan, rowspan=rowspan * 2 - 1,
                            sticky=NSEW, padx=padLeft, pady=self.outer.dpi((10, 0)))

        @abstractmethod
        def load(self, value):
            pass

    class CeTypeCombobox(FilteredMappedCombobox, AttributeWidget):
        def __init__(self, outer: 'TCWindow', master, mapping: dict, attribute: str,
                     ceType: type, **kwargs):
            if ceType == Effect:
                title = TEXT['effectAttributeName'][attribute]
            else:
                title = TEXT['conditionAttributeName'][attribute]
            self.outer = outer
            self.variable = ttk.IntVar()
            self.label = ttk.Label(master, text=title)
            super().__init__(master, mapping, self.variable, **kwargs)

        def load(self, value: int):
            self.variable.set(value)

    class AttributeCombobox(MappedCombobox, AttributeWidget):
        def __init__(self, outer: 'TCWindow', master, mapping: dict, attribute: str,
                     ceType: type, **kwargs):
            if ceType == Effect:
                title = TEXT['effectAttributeName'][attribute]
            else:
                title = TEXT['conditionAttributeName'][attribute]
            self.outer = outer
            self.variable = ttk.IntVar()
            if attribute in ['armour_attack_class', 'armour_attack_quantity']:
                # may be set None or []
                self.variable = ttk.Variable()
            self.label = ttk.Label(master, text=title)
            super().__init__(master, mapping, self.variable, **kwargs)
            # super(CeInfoView.AttributeWidget, self).__init__()
            self.set_display_event( \
                lambda attr=attribute, var=self.variable, ce=ceType: \
                    self.__modifyCeAttributeCombobox(attr, var, ce))

        def load(self, value: int):
            self.variable.set(value)

        def __modifyCeAttributeCombobox(self, attribute: str, variable: ttk.IntVar, ceType: type):
            print(f'__modifyCeAttributeCombobox: {attribute} = {variable.get()}')
            curItem = self.outer.fTEditor.tvTriggerList.focus()
            if ceType == Effect:
                effect = self.outer.fTEditor.getEffect(curItem)
                if effect is not None:
                    setattr(effect, attribute, variable.get())
                    # For MODIFY_ATTRIBUTE
                    if attribute in ['object_attributes'] and effect.effect_type in self.outer.fCeInfo.EFFECTS_OBJATTR_WITH_AA_CLASS:
                        if variable.get() in self.outer.fCeInfo.ATTRIBUTES_WITH_AA:
                            if None in [effect.armour_attack_class, effect.armour_attack_quantity]:
                                effect.armour_attack_class = -1
                                effect.armour_attack_quantity = -1
                        else:
                            effect.armour_attack_class = None
                            effect.armour_attack_quantity = None
                        self.outer.fCeInfo.effectWidgetPacks[Effect]['armour_attack_class'].load(effect.armour_attack_class)
                        self.outer.fCeInfo.effectWidgetPacks[Effect]['armour_attack_quantity'].load(effect.armour_attack_quantity)

                    self.outer.fCeInfo.updateEffectTreeNode(curItem, effect)
            elif ceType == Condition:
                condition = self.outer.fTEditor.getCondition(curItem)
                if condition is not None:
                    setattr(condition, attribute, variable.get())
                    self.outer.fCeInfo.updateConditionTreeNode(curItem, condition)

    class AttributeEntry(PairValueEntry, AttributeWidget):
        def __init__(self, outer: 'TCWindow', master, attribute: str,
                     ceType: type, supportType: type, **kwargs):
            if ceType == Effect:
                title = TEXT['effectAttributeName'][attribute]
            else:
                title = TEXT['conditionAttributeName'][attribute]
            self.supportType = supportType
            self.outer = outer
            self.variable = ttk.StringVar()
            self.label = ttk.Label(master, text=title)
            super().__init__(master, self.variable, **kwargs)
            if attribute.startswith('__variant_'):
                attribute = attribute[len('__variant_') :]
            self.set_display_event( \
                lambda attr=attribute, var=self.variable, ce=ceType: \
                    self.__modifyCeAttributeEntry(attr, var, ce))

        def load(self, value: str):
            self.variable.set(value)

        def __modifyCeAttributeEntry(self, attribute: str, variable: ttk.StringVar, ceType: type):
            print(f'__modifyCeAttributeEntry: {attribute} = {variable.get()}')
            curItem = self.outer.fTEditor.tvTriggerList.focus()
            if ceType == Effect:
                effect = self.outer.fTEditor.getEffect(curItem)
                if effect is not None:
                    value = variable.get()
                    if self.supportType == int:
                        if isFloatQuantityEffect(effect.effect_type, effect.object_attributes):
                            try:
                                value = float(value)
                            except ValueError:
                                value = -1
                            setattr(effect, attribute, value)
                        else:
                            try:
                                value = int(value)
                            except ValueError:
                                value = -1
                            setattr(effect, attribute, value)
                    elif self.supportType == str:
                        setattr(effect, attribute, value.replace('\n', '\r'))
                    else:
                        raise NotImplementedError(f'{self.supportType} is not expected.')
                    self.outer.fCeInfo.updateEffectTreeNode(curItem, effect)
            elif ceType == Condition:
                condition = self.outer.fTEditor.getCondition(curItem)
                if condition is not None:
                    value = variable.get()
                    if self.supportType == int:
                        try:
                            value = int(value)
                        except ValueError:
                            value = -1
                        setattr(condition, attribute, value)
                    elif self.supportType == str:
                        setattr(condition, attribute, value.replace('\n', '\r'))
                    else:
                        raise NotImplementedError(f'{self.supportType} is not expected.')
                    self.outer.fCeInfo.updateConditionTreeNode(curItem, condition)

    class AttributeCheckbutton(ttk.Checkbutton, AttributeWidget):
        def __init__(self, outer: 'TCWindow', master, attribute: str,
                     ceType: type, **kwargs):
            if ceType == Effect:
                title = TEXT['effectAttributeName'][attribute]
            else:
                title = TEXT['conditionAttributeName'][attribute]
            self.outer = outer
            self.variable = ttk.BooleanVar()
            self.label = ttk.Label(master, text=title)
            super().__init__(master, bootstyle=(ttk.ROUND, ttk.TOGGLE), variable=self.variable,
                                 command=lambda attr=attribute, var=self.variable, ce=ceType: \
                                     self.__modifyCeAttributeCheckbutton(attr, var, ce), **kwargs)

        def load(self, value: bool):
            self.variable.set(value)

        def __modifyCeAttributeCheckbutton(self, attribute: str, variable: ttk.BooleanVar, ceType: type):
            print(f'__modifyCeAttributeCheckbutton: {attribute} = {variable.get()}')
            curItem = self.outer.fTEditor.tvTriggerList.focus()
            if ceType == Effect:
                effect = self.outer.fTEditor.getEffect(curItem)
                if effect is not None:
                    setattr(effect, attribute, variable.get())
                    self.outer.fCeInfo.updateEffectTreeNode(curItem, effect)
            elif ceType == Condition:
                condition = self.outer.fTEditor.getCondition(curItem)
                if condition is not None:
                    setattr(condition, attribute, variable.get())
                    self.outer.fCeInfo.updateConditionTreeNode(curItem, condition)

    class AttributeText(ScrolledText, AttributeWidget):
        def __init__(self, outer: 'TCWindow', master, attribute: str,
                     ceType: type, **kwargs):
            if ceType == Effect:
                title = TEXT['effectAttributeName'][attribute]
            else:
                title = TEXT['conditionAttributeName'][attribute]
            self.outer = outer
            self.label = ttk.Label(master, text=title)
            super().__init__(master, height=2, width=2, **kwargs)
            self.text.bind('<<Modified>>',
                           lambda e, attr=attribute: \
                               self.__modifyAttributeText(attr))

        def load(self, value: str):
            self.text.delete(1.0, END)
            self.text.insert(1.0, value.replace('\r', '\n'))
            self.text.edit_modified(False)

        def __modifyAttributeText(self, attribute: str) -> None:
            if self.text.edit_modified() == False:
                return
            self.text.edit_modified(False)
            curItem = self.outer.fTEditor.tvTriggerList.focus()
            match self.outer.fTEditor.tvTriggerList.itemType(curItem):
                case 'condition':
                    condition = self.outer.fTEditor.getCondition(curItem)
                    if condition is not None:
                        description = self.text.get(1.0, 'end-1c')
                        setattr(condition, attribute, description.replace('\n', '\r'))
                        self.outer.fCeInfo.updateConditionTreeNode(curItem, condition)
                case 'effect':
                    effect = self.outer.fTEditor.getEffect(curItem)
                    if effect is not None:
                        description = self.text.get(1.0, 'end-1c')
                        setattr(effect, attribute, description.replace('\n', '\r'))
                        self.outer.fCeInfo.updateEffectTreeNode(curItem, effect)
                case 'trigger':
                    pass
                case _:
                    raise ValueError

    class AttributeUnitsButton(UnitsSelectButton, AttributeWidget):
        def __init__(self, outer: 'TCWindow', master, attribute: str,
                     ceType: type, multi: bool, **kwargs):
            if ceType == Effect:
                title = TEXT['effectAttributeName'][attribute]
            else:
                title = TEXT['conditionAttributeName'][attribute]
            self.outer = outer
            self.label = ttk.Label(master, text=title)
            super().__init__(self.outer, master, multi,
                             **kwargs)
            self.set_internal_event( \
                lambda units, attr=attribute, ce=ceType: \
                    self.__modifyCeAttributeButton(units, attr, ce))

        def load(self, value: list):
            self.variable.set(value)

        def __modifyCeAttributeButton(self, units: list[int] | int, attribute: str, ceType: type):
            print(f'__modifyCeAttributeUnitsButton: {attribute} = {units}')
            curItem = self.outer.fTEditor.tvTriggerList.focus()
            if ceType == Effect:
                effect = self.outer.fTEditor.getEffect(curItem)
                if effect is not None:
                    value = units
                    setattr(effect, attribute, value)
                    self.outer.fCeInfo.updateEffectTreeNode(curItem, effect)
            elif ceType == Condition:
                condition = self.outer.fTEditor.getCondition(curItem)
                if condition is not None:
                    value = units
                    setattr(condition, attribute, value)
                    self.outer.fCeInfo.updateConditionTreeNode(curItem, condition)

    class AttributeUnitConstButton(UnitConstSelectButton, AttributeWidget):
        def __init__(self, outer: 'TCWindow', master, attribute: str,
                     ceType: type, **kwargs):
            if ceType == Effect:
                title = TEXT['effectAttributeName'][attribute]
            else:
                title = TEXT['conditionAttributeName'][attribute]
            self.outer = outer
            self.label = ttk.Label(master, text=title)
            super().__init__(self.outer, master, allowNone=True, **kwargs)
            self.set_internal_event( \
                lambda unitConst, attr=attribute, ce=ceType: \
                    self.__modifyCeUnitConstButton(unitConst, attr, ce))

        def load(self, value: int):
            self.variable.set(value)

        def __modifyCeUnitConstButton(self, unitConst: int, attribute: str, ceType: type):
            print(f'__modifyCeUnitConstButton: {attribute} = {unitConst}')
            curItem = self.outer.fTEditor.tvTriggerList.focus()
            if ceType == Effect:
                effect = self.outer.fTEditor.getEffect(curItem)
                if effect is not None:
                    value = unitConst
                    setattr(effect, attribute, value)
                    self.outer.fCeInfo.updateEffectTreeNode(curItem, effect)
            elif ceType == Condition:
                condition = self.outer.fTEditor.getCondition(curItem)
                if condition is not None:
                    value = unitConst
                    setattr(condition, attribute, value)
                    self.outer.fCeInfo.updateConditionTreeNode(curItem, condition)

    class AttributeAreaButton(ttk.Frame, AttributeWidget):
        def __init__(self, outer: 'TCWindow', master, attribute: str,
                     ceType: type, **kwargs):
            super().__init__(master, **kwargs)
            if attribute == 'location_x':
                title = TEXT['effectAttributeName']['location']
                encodeMethod = lambda pointList: getLocationAbstract(pointList[0], pointList[1],
                                                                     pointList[2])
            else:
                title = TEXT['effectAttributeName']['area']
                encodeMethod = lambda pointList: getAreaAbstract(pointList[0], pointList[1],
                                                                pointList[2], pointList[3])
            self.attribute = attribute
            self.outer = outer
            self.variable = IntListVar()
            self.label = ttk.Label(master, text=title)
            self.lvbtn = ListValueButton(self, variable=self.variable, style='ceWidgetButton.Outline.TButton', width=16,
                                        encodeMethod=encodeMethod)
            self.lvbtn.pack(side=LEFT, fill=BOTH, expand=True)
            self.lvbtn.set_command(self.__viewAttributeArea)
            self.lvbtn.set_internal_event(lambda ce=ceType: \
                                            self.__modifyAttributeArea(ce))
            self.btnSetUnit = ttk.Button(self, style='iconButton.Link.TButton', image=self.outer.imgCeSetLocationUnit,
                                        command=self.__setAttributeUnit)
            self.btnSetUnit.pack(side=LEFT, padx=0)
            Tooltip(self.btnSetUnit, TEXT['tooltipSetLocationUnit'])
            self.btnSetArea = ttk.Button(self, style='iconButton.Link.TButton', image=self.outer.imgCeSetArea,
                                        command=self.__setAttributeArea)
            self.btnSetArea.pack(side=RIGHT, padx=0)
            Tooltip(self.btnSetArea, TEXT['tooltipSetLocationArea'])

        def load(self, value: list):
            self.variable.set(value)

        def gridAttributeWithUnitSel(self, column, row, columnspan=1, rowspan=1):
            self.btnSetUnit.pack(side=LEFT, padx=0)
            return super().gridAttribute(column, row, columnspan, rowspan)

        def gridAttribute(self, column, row, columnspan=1, rowspan=1):
            self.btnSetUnit.pack_forget()
            return super().gridAttribute(column, row, columnspan, rowspan)

        def __setAttributeUnit(self) -> None:
            if self.outer.nTabsLeft.select() \
            and self.outer.nTabsLeft.index('current') == self.outer.nTabsLeft.index(self.outer.fUEditor):
                unitId = self.outer.fUEditor.tvUnitList.getUnitFocusRefId()
                if unitId == None:
                    unitId = -1
                location = [-1, -1, unitId]
                self.lvbtn.internal_var.set(location)
            else:
                self.outer.nTabsLeft.select(self.outer.fUEditor)

        def __setAttributeArea(self) -> None:
            x1, y1, x2, y2 = self.outer.fMapViewTab.pointSelect.get()
            if self.attribute == 'area_x1':
                if (x2, y2) == (-1, -1):
                    x2, y2 = x1, y1
                if x1 > x2:
                    x1, x2 = x2, x1
                if y1 > y2:
                    y1, y2 = y2, y1
                self.lvbtn.internal_var.set([x1, y1, x2, y2])
            elif self.attribute == 'location_x':
                location = [x1, y1, -1]
                self.lvbtn.internal_var.set(location)

        def __viewAttributeArea(self):
            coords = self.variable.get()
            if len(coords) != 0:
                if self.attribute == 'area_x1':
                    x1, y1, x2, y2 = coords
                    if (x1, y1) == (-1, -1):
                        self.outer.fMapViewTab.drawClear()
                    else:
                        self.outer.fMapViewTab.drawSetPoint1((x1, y1), draw=False)
                        self.outer.fMapViewTab.drawSetPoint2((x2, y2), see=True)
                elif self.attribute == 'location_x':
                    x1, y1, unit = coords
                    if unit != -1:
                        self.outer.nTabsLeft.select(self.outer.fUEditor)
                        self.outer.fUEditor.unitIdFilter([unit,])
                    elif (x1, y1) != (-1, -1):
                        self.outer.fMapViewTab.drawSetPoint1((x1, y1), see=True)
                    else:
                        self.outer.fMapViewTab.drawClear()

        def __modifyAttributeArea(self, ceType: type) -> None:
            curItem = self.outer.fTEditor.tvTriggerList.focus()
            if ceType == Condition:
                ce = self.outer.fTEditor.getCondition(curItem)
            elif ceType == Effect:
                ce = self.outer.fTEditor.getEffect(curItem)
            if ce is not None:
                if self.attribute == 'area_x1':
                    x1, y1, x2, y2 = self.variable.get()
                    setattr(ce, 'area_x1', x1)
                    setattr(ce, 'area_y1', y1)
                    setattr(ce, 'area_x2', x2)
                    setattr(ce, 'area_y2', y2)
                elif self.attribute == 'location_x':
                    x, y, unit = self.variable.get()
                    setattr(ce, 'location_x', x)
                    setattr(ce, 'location_y', y)
                    if hasattr(ce, 'location_object_reference'):
                        setattr(ce, 'location_object_reference', unit)
                if ceType == Condition:
                    self.outer.fCeInfo.updateConditionTreeNode(curItem, ce)
                elif ceType == Effect:
                    self.outer.fCeInfo.updateEffectTreeNode(curItem, ce)

    # endregion CEWidgets

    def __constructEffectComboboxDicts(self, attribute: str) -> dict[int, str]:
        match attribute:
            case 'effect_type':
                return EFFECT_NAME
            case 'armour_attack_class':
                return TEXT['datasetDamageClass']
            case 'tribute_list':
                return RESOURCE_NAME
            case 'diplomacy':
                return TEXT['datasetDiplomacyState']
            case 'source_player' | 'target_player':
                return {} # update later
            case 'technology':
                return TECH_NAME
            case 'local_technology':
                return {} # Todo: Fill what?
            case 'trigger_id':
                return {} # update later
            case 'object_group' | 'object_group2':
                return TEXT['datasetObjectClass']
            case 'object_type' | 'object_type2':
                return TEXT['datasetObjectType']
            case 'instruction_panel_position':
                return {v: TEXT['comboValueEffectInstructionPanelPosition'].format(v) for v in range(3)}
            case 'attack_stance':
                return TEXT['datasetAttackStance']
            case 'time_unit':
                return TEXT['datasetTimeUnit']
            case 'visibility_state':
                return TEXT['datasetVisibilityState']
            case 'operation':
                return TEXT['datasetOperation']
            case 'object_attributes':
                return TEXT['datasetObjectAttribute']
            case 'variable' | 'variable2':
                return {} # update later
            case 'timer':
                return {} # update later
            case 'facet' | 'facet2':
                return TEXT['dataUnitFaceToName']
            case 'player_color':
                return TEXT['datasetPlayerColorId']
            case 'color_mood':
                return TEXT['datasetColorMood']
            case 'object_state':
                return TEXT['datasetObjectState']
            case 'action_type':
                return TEXT['datasetActionType']
            case 'resource_1' | 'resource_2' | 'resource_3':
                return RESOURCE_NAME
            case 'condition_type':
                return CONDITION_NAME
            case 'attribute':
                return RESOURCE_NAME
            case 'comparison':
                return TEXT['datasetComparison']
            case 'unit_ai_action':
                return TEXT['datasetUnitAIAction']
            case 'timer_id':
                return {} # update later
            case 'victory_timer_type':
                return TEXT['datasetVictoryTimerType']
            case 'decision_option':
                return TEXT['datasetDecisionOption']
            case _:
                raise ValueError(f"Unknown effect attribute: {attribute}")

    def updateConditionTreeNode(self, item: str, condition:Condition) -> None:
        abstract = abstractCondition(condition)
        self.tl.item(item, text=' ' + abstract)
        self.app.statusBarMessage(abstract)

    def updateEffectTreeNode(self, item: str, effect:Effect) -> None:
        abstract = abstractEffect(effect)
        self.tl.item(item, text=' ' + abstract)
        self.app.statusBarMessage(abstract)

    def loadConditionAttributes(self, condition: Condition):
        abstract = abstractCondition(condition)
        self.wCType.variable.set(condition.condition_type)
        for attribute in CONDITION_ATTRIBUTES.get(condition.condition_type, []):
            try:
                match CONDITION_WIDGET_FORM[attribute][0]:
                    case 'null':
                        pass
                    case 'Checkbutton':
                        self.effectWidgetPacks[Condition][attribute].load(getattr(condition, attribute) == 1)
                    case 'Entry' | 'Combobox' | 'MultiUnitSelector' | 'UnitConstSelector':
                        self.effectWidgetPacks[Condition][attribute].load(getattr(condition, attribute))
                    case 'TextOrEntry':
                        self.effectWidgetPacks[Condition]['__variant_' + attribute].load(getattr(condition, attribute).replace('\r', '\n'))
                        self.effectWidgetPacks[Condition][attribute].load(getattr(condition, attribute))
                    case 'SingleUnitSelector':
                        self.effectWidgetPacks[Condition][attribute].load([getattr(condition, attribute),])
                    case 'AreaSelector':
                        if attribute == 'area_x1':
                            self.effectWidgetPacks[Condition][attribute].load([
                                    getattr(condition, 'area_x1'),
                                    getattr(condition, 'area_y1'),
                                    getattr(condition, 'area_x2'),
                                    getattr(condition, 'area_y2'),
                                ])
                    case _:
                        print(attribute, getattr(condition, attribute))
            except:
                print(f'Load {attribute} fail')
                raise
        self.app.statusBarMessage(abstract)

    def loadEffectAttributes(self, effect: Effect):
        abstract = abstractEffect(effect)
        self.wEType.load(effect.effect_type)
        for attribute in EFFECT_ATTRIBUTES.get(effect.effect_type, []):
            try:
                match EFFECT_WIDGET_FORM[attribute][0]:
                    case 'null':
                        pass
                    case 'Checkbutton':
                        self.effectWidgetPacks[Effect][attribute].load(getattr(effect, attribute) == 1)
                    case 'Entry' | 'Combobox' | 'MultiUnitSelector' | 'UnitConstSelector':
                        self.effectWidgetPacks[Effect][attribute].load(getattr(effect, attribute))
                    case 'TextOrEntry':
                        self.effectWidgetPacks[Effect]['__variant_' + attribute].load(getattr(effect, attribute).replace('\r', '\n'))
                        self.effectWidgetPacks[Effect][attribute].load(getattr(effect, attribute))
                    case 'SingleUnitSelector':
                        self.effectWidgetPacks[Effect][attribute].load([getattr(effect, attribute),])
                    case 'AreaSelector':
                        if attribute == 'location_x':
                            location = [
                                getattr(effect, 'location_x'),
                                getattr(effect, 'location_y'),
                                getattr(effect, 'location_object_reference', -1)
                            ]
                            self.effectWidgetPacks[Effect][attribute].load(location),
                        elif attribute == 'area_x1':
                            self.effectWidgetPacks[Effect][attribute].load([
                                    getattr(effect, 'area_x1'),
                                    getattr(effect, 'area_y1'),
                                    getattr(effect, 'area_x2'),
                                    getattr(effect, 'area_y2'),
                                ])
                    case _:
                        print(attribute, getattr(effect, attribute))
            except:
                print(f'Load {attribute} fail')
                raise
        self.app.statusBarMessage(abstract)
