from __future__ import annotations

from tkinter.messagebox import askokcancel
from typing import TYPE_CHECKING, Literal
import copy
from tkinter.constants import *
import ttkbootstrap as ttk

from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.objects.data_objects.condition import Condition
from AoE2ScenarioParser.objects.data_objects.effect import Effect
from AoE2ScenarioParser.objects.data_objects.trigger import Trigger
from AoE2ScenarioParser.objects.managers.trigger_manager import TriggerManager
from AoE2ScenarioParser.objects.support.trigger_ce_lock import TriggerCELock

from Localization import TEXT
from TriggerAbstract import *
from Util import Tooltip, ValueSelectButton
from _prebuild.CeAttributes import CONDITION_ATTRIBUTES, EFFECT_ATTRIBUTES

if TYPE_CHECKING:
    from main import TCWindow

def copyEffect(effect: Effect, parent: Trigger):
    trigger = parent
    srcEffect = effect
    newEffect = trigger.new_effect.none()
    newEffect.effect_type = srcEffect.effect_type
    for attribute in EFFECT_ATTRIBUTES.get(srcEffect.effect_type, []):
        setattr(newEffect, attribute, getattr(srcEffect, attribute))
    return newEffect

def copyCondition(condition: Condition, parent: Trigger):
    trigger = parent
    srcCondition = condition
    newCondition = trigger.new_condition.none()
    newCondition.condition_type = srcCondition.condition_type
    for attribute in CONDITION_ATTRIBUTES.get(srcCondition.condition_type, []):
        setattr(newCondition, attribute, getattr(srcCondition, attribute))
    return newCondition

def reorderCEs(parent: Trigger, reorderCondition=True, reorderEffect=True) -> None:
    if reorderCondition:
        newCeList = []
        for newId, id in enumerate(parent.condition_order):
            ce = parent.conditions[id]
            newCeList.append(ce)
        parent.conditions = newCeList

    if reorderEffect:
        newCeList = []
        for newId, id in enumerate(parent.effect_order):
            ce = parent.effects[id]
            newCeList.append(ce)
        parent.effects = newCeList

class TriggerTreeView(ttk.Treeview):
    """
    A Treeview holds Trigger/Condition/Effect.

    Trigger node is the parent of condition/effect nodes.
    Tags hold which type the node is.
    Values show and hold the id and display id of T/C/E.
    """
    def __init__(self, master=None, show=ttk.TREE, selectmode=BROWSE, columns=(0), **kwargs):
        super().__init__(master, show=show, selectmode=selectmode, columns=columns, **kwargs)

    def insert(self, parent, index, text, tceId:int, tceDisplayId:int,
                tceType:Literal['trigger', 'effect', 'condition']='trigger', **kwargs):
        return super().insert(parent, index, text=' ' + text,
                                values=(f'({tceId},{tceDisplayId})', ), tags='' if tceType == 'trigger' else tceType, **kwargs)

    def itemType(self, item:str) -> Literal['trigger', 'effect', 'condition', 'root']:
        if item == '':
            return 'root'
        elif self.parent(item) == '':
            return 'trigger'
        elif 'effect' in self.item(item)['tags']:
            return 'effect'
        elif 'condition' in self.item(item)['tags']:
            return 'condition'
        else:
            raise ValueError(f"Node {item} doesn't match any type")

    def getNodeId(self, item:str) -> tuple[int, int]:
        id, displayId = self.item(item)['values'][0][1:-1].split(',')
        return int(id), int(displayId)

    def setNodeId(self, item:str, ids:tuple[int, int]):
        self.item(item, values=(f'({ids[0]},{ids[1]})', ))

    def getTriggerNode(self, item:str) -> str:
        parent = self.parent(item)
        if parent == '':
            parent = item
        return parent

class TriggerView(ttk.Frame):
    @property
    def tm(self):
        return self.app.triggerManager

    @property
    def tl(self):
        return self.tvTriggerList

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        def createControlPanel():
            def __setCbDuplicateIncludeLimit(modifyed:Literal['includeSource','includeTarget']):
                # Should select one at least
                if modifyed == 'includeSource':
                    if self.app.options.includeSource.get() == False:
                        self.app.options.includeTarget.set(True)
                else:
                    if self.app.options.includeTarget.get() == False:
                        self.app.options.includeSource.set(True)

            def createDuplicateMenu():
                menuDuplicate = ttk.Menu(self)
                menuDuplicate.add_checkbutton(label=TEXT['menuDuplicateIncludeSource'], variable=self.app.options.includeSource,
                                            command=lambda: __setCbDuplicateIncludeLimit('includeSource'))
                menuDuplicate.add_checkbutton(label=TEXT['menuDuplicateIncludeTarget'], variable=self.app.options.includeTarget,
                                            command=lambda: __setCbDuplicateIncludeLimit('includeTarget'))
                menuDuplicate.add_checkbutton(label=TEXT['menuDuplicateIncludeStrict'], variable=self.app.options.changeFromPlayerOnly)
                menuDuplicate.add_separator()
                menuDuplicate.add_checkbutton(label=TEXT['menuDuplicateAddDuplicateMark'], variable=self.app.options.addDuplicateMark)
                menuDuplicate.add_separator()
                # Todo: complete two menu command
                menuDuplicate.add_command(label=TEXT['menuDuplicateDuplicateAllMarked'], state='disabled')
                menuDuplicate.add_command(label=TEXT['menuDuplicateAdvanced'], state='disabled')
                btnIDuplicateForAll.bind("<Button-3>",lambda e: menuDuplicate.post(e.x_root, e.y_root))
                btnTDuplicateMultiple.bind("<Button-3>",lambda e: menuDuplicate.post(e.x_root, e.y_root))

            def createDeduplicateMenu():
                menuDeduplicate = ttk.Menu(self)
                # menuDeduplicate.add_separator()
                # Todo: complete two menu command
                menuDeduplicate.add_command(label=TEXT['menuDeduplicateAllMarked'], state='disabled')
                menuDeduplicate.add_command(label=TEXT['menuDeduplicateAdvanced'], state='disabled')
                btnIUnduplicateForAll.bind("<Button-3>",lambda e: menuDeduplicate.post(e.x_root, e.y_root))
                btnTUnduplicateMultiple.bind("<Button-3>",lambda e: menuDeduplicate.post(e.x_root, e.y_root))

            def createSortMenu():
                menuSort = ttk.Menu(self)
                # menuSort.add_separator()
                menuSort.add_command(label=TEXT['menuReorderCEs'], command=self.itemSortCeByDisplay)
                btnTSort.bind("<Button-3>",lambda e: menuSort.post(e.x_root, e.y_root))

            def __buttonSelectTrigger(buttonVar: ttk.Variable):
                curItem = self.tl.focus()
                if self.tl.itemType(curItem) == 'trigger':
                    buttonVar.set(self.tl.getNodeId(curItem)[1])

            fTCommands = ttk.Frame(self)
            fTCommands.pack(fill=X, expand=NO, padx=self.app.dpi((10, 5)), pady=self.app.dpi((5, 0)))
            fTCommands.grid_columnconfigure(18,weight=1)
            btnTAdd = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnTAdd,
                                    command=self.triggerAdd)
            Tooltip(btnTAdd, TEXT['tooltipAddTrigger'])
            btnTAdd.grid(row=0, column=0, pady=self.app.dpi(2))
            btnCAdd = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnCAdd,
                                    command=self.conditionAdd)
            Tooltip(btnCAdd, TEXT['tooltipAddCondition'])
            btnCAdd.grid(row=1, column=0, pady=self.app.dpi(2))
            btnEAdd = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnEAdd,
                                    command=self.effectAdd)
            Tooltip(btnEAdd, TEXT['tooltipAddEffect'])
            btnEAdd.grid(row=1, column=1, pady=self.app.dpi(2))
            btnIDelete = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIDelete,
                                        command=self.itemDelete)
            Tooltip(btnIDelete, TEXT['tooltipDeleteItem'])
            btnIDelete.grid(row=0, column=1, pady=self.app.dpi(2))
            btnIDuplicate = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIDuplicate,
                                            command=self.itemDuplicate)
            Tooltip(btnIDuplicate, TEXT['tooltipDuplicateItem'])
            btnIDuplicate.grid(row=0, column=2, pady=self.app.dpi(2))
            btnIDuplicateForAll = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIDuplicateForAll,
                                                command=self.itemDuplicateForAll)
            Tooltip(btnIDuplicateForAll, TEXT['tooltipDuplicateItemForAll'])
            btnIDuplicateForAll.grid(row=0, column=3, pady=self.app.dpi(2))
            btnIUnduplicateForAll = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIUnduplicate,
                                                command=self.itemUnduplicateForAll)
            Tooltip(btnIUnduplicateForAll, TEXT['tooltipUnduplicateItemForAll'])
            btnIUnduplicateForAll.grid(row=0, column=4, pady=self.app.dpi(2))
            btnIMoveUp = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIMoveUp,
                                        command=self.itemMoveUp)
            Tooltip(btnIMoveUp, TEXT['tooltipMoveItemUp'])
            btnIMoveUp.grid(row=1, column=3, pady=self.app.dpi(2))
            btnIMoveDown = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIMoveDown,
                                        command=self.itemMoveDown)
            Tooltip(btnIMoveDown, TEXT['tooltipMoveItemDown'])
            btnIMoveDown.grid(row=1, column=4, pady=self.app.dpi(2))
            btnTSort = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnTSort,
                                    command=self.itemSortByDisplay)
            btnTSort.grid(row=0, column=20, pady=self.app.dpi(2))
            Tooltip(btnTSort, TEXT['tooltipSortTriggers'])

            ttk.Separator(fTCommands, orient='vertical').grid(row=0, column=9, rowspan=2, padx=self.app.dpi(2))
            ttk.Label(fTCommands, text=TEXT['labelFrom']).grid(row=0, column=10, pady=self.app.dpi(2))
            
            self.varTSelectFront = ttk.StringVar(value='-')
            self.varTSelectBack = ttk.StringVar(value='-')
            self.varTSelectTarget = ttk.StringVar(value='-')
            btnTSelectFront = ValueSelectButton(fTCommands, style='selectionButton.Link.TButton',
                                            textvariable=self.varTSelectFront,
                                            command=lambda: __buttonSelectTrigger(self.varTSelectFront))
            btnTSelectFront.grid(row=0, column=11, pady=self.app.dpi(2))
            btnTSelectBack = ValueSelectButton(fTCommands, style='selectionButton.Link.TButton',
                                            textvariable=self.varTSelectBack,
                                            command=lambda: __buttonSelectTrigger(self.varTSelectBack))
            btnTSelectBack.grid(row=0, column=12, pady=self.app.dpi(2))
            ttk.Label(fTCommands, text=TEXT['labelTo']).grid(row=1, column=10, pady=self.app.dpi(2))
            btnTSelectTarget = ValueSelectButton(fTCommands, style='selectionButton.Link.TButton',
                                            textvariable=self.varTSelectTarget,
                                            command=lambda: __buttonSelectTrigger(self.varTSelectTarget))
            btnTSelectTarget.grid(row=1, column=11, columnspan=2, pady=self.app.dpi(2))

            btnTDeleteMultiple = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIDelete,
                                                command=self.triggerDeleteMultiple)
            Tooltip(btnTDeleteMultiple, TEXT['tooltipDeleteMultiple'])
            btnTDeleteMultiple.grid(row=0, column=15, pady=self.app.dpi(2))
            btnTMoveMultiple = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIMove,
                                            command=self.triggerMoveMultiple)
            Tooltip(btnTMoveMultiple, TEXT['tooltipMoveMultipleTo'])
            btnTMoveMultiple.grid(row=1, column=13, pady=self.app.dpi(2))
            btnTDuplicateMultiple = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIDuplicateForAll,
                                                    command=self.triggerDuplicateMultiple)
            Tooltip(btnTDuplicateMultiple, TEXT['tooltipDuplicateMultipleForAll'])
            btnTDuplicateMultiple.grid(row=0, column=13, pady=self.app.dpi(2))
            btnTUnduplicateMultiple = ttk.Button(fTCommands, style='iconButton.Link.TButton', image=self.app.imgBtnIUnduplicate,
                                                    command=self.triggerUnduplicateMultiple)
            Tooltip(btnTUnduplicateMultiple, TEXT['tooltipUnduplicateMultipleForAll'])
            btnTUnduplicateMultiple.grid(row=0, column=14, pady=self.app.dpi(2))
            ttk.Separator(fTCommands, orient='vertical').grid(row=0, column=16, rowspan=2, padx=self.app.dpi(2))
            ttk.Separator(fTCommands, orient='vertical').grid(row=0, column=19, rowspan=2, padx=self.app.dpi(2))

            createDuplicateMenu()
            createDeduplicateMenu()
            createSortMenu()

        def createTriggerList():
            ## TriggerList
            lfTList = ttk.LabelFrame(self, text=TEXT['labelTriggerList'])
            lfTList.pack(fill=BOTH, expand=YES, padx=self.app.dpi((10, 5)), pady=self.app.dpi((0, 5)))
            self.tvTriggerList = TriggerTreeView(master=lfTList, style='Borderless.Treeview')
            self.tvTriggerList.bind('<<TreeviewSelect>>', self.app.itemSelect)
            tvsbTriggerList = ttk.Scrollbar(master=lfTList, command=self.tvTriggerList.yview)
            self.tvTriggerList.configure(yscrollcommand=tvsbTriggerList.set)
            self.tvTriggerList.column('#0', width=self.app.dpi(200))
            self.tvTriggerList.column('#1', width=self.app.dpi(100), anchor=E, stretch=False)

            tvsbTriggerList.pack(side=RIGHT, fill=Y)
            self.tvTriggerList.pack(side=RIGHT, fill=BOTH, expand=YES)

        self.varTSelectFront: ttk.StringVar
        self.varTSelectBack: ttk.StringVar
        self.varTSelectTarget: ttk.StringVar
        self.tvTriggerList: TriggerTreeView
        createControlPanel()
        createTriggerList()

    def getTrigger(self, item:str) -> Trigger:
        triggerNode = self.tl.getTriggerNode(item)
        if self.tl.itemType(item) == 'trigger':
            triggerId = self.tl.getNodeId(triggerNode)[0]
            return self.tm.get_trigger(triggerId)

    def getCondition(self, item:str) -> Condition:
        if self.tl.itemType(item) == 'condition':
            conditionId = self.tl.getNodeId(item)[0]
            triggerNode = self.tl.getTriggerNode(item)
            triggerId = self.tl.getNodeId(triggerNode)[0]
            return self.tm.get_trigger(triggerId).get_condition(conditionId)

    def getEffect(self, item:str) -> Effect:
        if self.tl.itemType(item) == 'effect':
            effectId = self.tl.getNodeId(item)[0]
            triggerNode = self.tl.getTriggerNode(item)
            triggerId = self.tl.getNodeId(triggerNode)[0]
            return self.tm.get_trigger(triggerId).get_effect(effectId)

    def loadTrigger(self):
        for item in self.tl.get_children():
            self.tl.delete(item)
        for displayId, id in enumerate(self.tm.trigger_display_order):
            trigger = self.tm.get_trigger(id)
            triggerImage = self.app.getTriggerIcon(trigger)
            itemTrigger = self.tl.insert("", END, text=trigger.name, tceId=id, tceDisplayId=displayId, image=triggerImage)
            for cDisplayId, cId in enumerate(trigger.condition_order):
                condition = trigger.conditions[cId]
                itemCE = self.tl.insert(itemTrigger, END, text=abstractCondition(condition),
                                                   tceId=cId, tceDisplayId=cDisplayId, image=self.app.imgConditionEnabled, tceType='condition')
            for eDisplayId, eId in enumerate(trigger.effect_order):
                effect = trigger.effects[eId]
                itemCE = self.tl.insert(itemTrigger, END, text=abstractEffect(effect),
                                                   tceId=eId, tceDisplayId=eDisplayId, image=self.app.imgEffectEnabled, tceType='effect')

    # region TriggerViewOperation
    def triggerAdd(self):
        """New a trigger after selected trigger, append if nothing selected."""
        triggerCount = len(self.tm.trigger_display_order)
        triggerName = TEXT['formatNewTriggerName'].format(triggerCount)

        curItem = self.tl.focus()
        if curItem == '':
            afterDisplayId = triggerCount - 1
        else:
            curItem = self.tl.getTriggerNode(curItem)
            afterDisplayId = self.tl.index(curItem)

        # Call AoE2SP
        newTrigger = self.tm.add_trigger(name=triggerName)
        self.tm.trigger_display_order.insert(afterDisplayId + 1, self.tm.trigger_display_order.pop())

        self.triggerNewAfter(afterDisplayId, newTrigger)
        # See if out of sight
        if not self.tl.bbox(self.tl.next(curItem)):
            self.tl.see(self.tl.next(curItem))

    def triggerNewAfter(self, afterIndex, trigger:Trigger, ignoreIndex=False):
        idNewTrigger = len(self.tl.get_children(""))
        triggerImage = self.app.getTriggerIcon(trigger)
        if ignoreIndex == False:
            itemTrigger = self.tl.insert("", afterIndex + 1, text=trigger.name,
                                                    tceId=idNewTrigger, tceDisplayId=afterIndex + 1, image=triggerImage)
        else:
            itemTrigger = self.tl.insert("", afterIndex + 1, text=trigger.name,
                                                    tceId=-1, tceDisplayId=-1, image=triggerImage)
        if ignoreIndex == False:
            next = self.tl.next(itemTrigger)
            while next != '':
                id, displayId = self.tl.getNodeId(next)
                self.tl.setNodeId(next, (id, displayId + 1))
                next = self.tl.next(next)
            self.tl.focus(itemTrigger)
            self.tl.selection_set(itemTrigger)

        for cDisplayId, cId in enumerate(trigger.condition_order):
            condition = trigger.conditions[cId]
            itemCE = self.tl.insert(itemTrigger, END, text=abstractCondition(condition),
                                               tceId=cId, tceDisplayId=cDisplayId, image=self.app.imgConditionEnabled, tceType='condition')
        for eDisplayId, eId in enumerate(trigger.effect_order):
            effect = trigger.effects[eId]
            itemCE = self.tl.insert(itemTrigger, END, text=abstractEffect(effect),
                                               tceId=eId, tceDisplayId=eDisplayId, image=self.app.imgEffectEnabled, tceType='effect')

    def ceAdd(self, parent: str, tag: str, obj: Effect|Condition):
        self.tl.item(parent, open=True)
        effectEndIndex = len(self.tl.get_children(parent))
        effectBeginIndex = effectEndIndex
        for child in self.tl.get_children(parent):
            if 'effect' in self.tl.item(child)['tags']:
                effectBeginIndex = self.tl.index(child)
                break
        if tag == 'effect':
            itemIndex = effectEndIndex
            ceIndex = itemIndex - effectBeginIndex
            ceName = abstractEffect(obj)
            ceImage = self.app.imgEffectEnabled
        else:
            itemIndex = effectBeginIndex
            ceIndex = itemIndex
            ceName = abstractCondition(obj)
            ceImage = self.app.imgConditionEnabled
        itemCE = self.tl.insert(parent, itemIndex, text=ceName,
                                           tceId=ceIndex,tceDisplayId=ceIndex, image=ceImage, tceType=tag)
        # See if out of sight
        if not self.tl.bbox(itemCE):
            self.tl.see(itemCE)
        self.tl.focus(itemCE)
        self.tl.selection_set(itemCE)

    def effectAdd(self):
        curItem = self.tl.focus()
        if curItem == '':
            return
        parent = self.tl.getTriggerNode(curItem)
        triggerId = self.tl.getNodeId(parent)[0]

        # Call AoE2SP
        newEffect = self.tm.get_trigger(triggerId).new_effect.none()
        # print(self.tm.get_trigger(triggerId).effect_order)

        self.ceAdd(parent, 'effect', newEffect)

    def conditionAdd(self):
        curItem = self.tl.focus()
        if curItem == '':
            return
        parent = self.tl.getTriggerNode(curItem)
        triggerId = self.tl.getNodeId(parent)[0]

        # Call AoE2SP
        newCondition = self.tm.get_trigger(triggerId).new_condition.none()
        # print(self.tm.get_trigger(triggerId).condition_order)

        self.ceAdd(parent, 'condition', newCondition)

    def itemDelete(self):
        curItem = self.tl.focus()
        if curItem == '':
            return
        nodeType = self.tl.itemType(curItem)
        parent = self.tl.getTriggerNode(curItem)
        triggerId = self.tl.getNodeId(parent)[0]
        idToDelete, displayIdToDelete = self.tl.getNodeId(curItem)
        nextSelection = self.tl.next(curItem)
        if nextSelection == '':
            nextSelection = self.tl.prev(curItem)
        if nodeType == 'trigger':
            # itemIterator = self.tl.
            for child in self.tl.get_children(''):
                if child == '':
                    break
                elif child == curItem:
                    continue
                else:
                    id, displayId = self.tl.getNodeId(child)
                    if id > idToDelete:
                        id -= 1
                    if displayId > displayIdToDelete:
                        displayId -= 1
                    self.tl.setNodeId(child, (id, displayId))

            # Call AoE2SP
            self.tm.remove_trigger(idToDelete)
            # print(self.tm.trigger_display_order)

        elif nodeType == 'condition':
            for child in self.tl.get_children(parent):
                if self.tl.itemType(child) == 'condition':
                    if child == curItem:
                        continue
                    else:
                        id, displayId = self.tl.getNodeId(child)
                        if id > idToDelete:
                            id -= 1
                        if displayId > displayIdToDelete:
                            displayId -= 1
                        self.tl.setNodeId(child, (id, displayId))
            # Call AoE2SP
            self.tm.get_trigger(triggerId).remove_condition(idToDelete)
            # print(self.tm.get_trigger(triggerId).condition_order)
        else:
            for child in self.tl.get_children(parent):
                if self.tl.itemType(child) == 'effect':
                    if child == curItem:
                        continue
                    else:
                        id, displayId = self.tl.getNodeId(child)
                        if id > idToDelete:
                            id -= 1
                        if displayId > displayIdToDelete:
                            displayId -= 1
                        self.tl.setNodeId(child, (id, displayId))
            # Call AoE2SP
            self.tm.get_trigger(triggerId).remove_effect(idToDelete)
            # print(self.tm.get_trigger(triggerId).effect_order)

        self.tl.delete(curItem)
        if nextSelection != '':
            self.tl.focus(nextSelection)
            self.tl.selection_set(nextSelection)
        elif nodeType != 'trigger':
            self.tl.focus(parent)
            self.tl.selection_set(parent)

    def itemMoveUp(self):
        curItem = self.tl.focus()
        if curItem == '':
            return
        prev = self.tl.prev(curItem)
        if prev != '':
            id, displayId = self.tl.getNodeId(curItem)
            prevId, prevDisplayId = self.tl.getNodeId(prev)
            if prevDisplayId + 1 == displayId:
                self.tl.move(curItem, self.tl.parent(curItem), self.tl.index(prev))
                displayId, prevDisplayId = prevDisplayId, displayId
                self.tl.setNodeId(curItem, (id, displayId))
                self.tl.setNodeId(prev, (prevId, prevDisplayId))
                if self.tl.itemType(curItem) == 'trigger':
                    # Call AoE2SP
                    self.tm.trigger_display_order[prevDisplayId], self.tm.trigger_display_order[displayId]\
                        = self.tm.trigger_display_order[displayId], self.tm.trigger_display_order[prevDisplayId]
                elif self.tl.itemType(curItem) == 'condition':
                    # Call AoE2SP
                    triggerId, triggerDisplayId = self.tl.getNodeId(self.tl.getTriggerNode(curItem))
                    trigger = self.tm.get_trigger(triggerId)
                    trigger.condition_order[prevDisplayId], trigger.condition_order[displayId]\
                        = trigger.condition_order[displayId], trigger.condition_order[prevDisplayId]
                elif self.tl.itemType(curItem) == 'effect':
                    # Call AoE2SP
                    triggerId, triggerDisplayId = self.tl.getNodeId(self.tl.getTriggerNode(curItem))
                    trigger = self.tm.get_trigger(triggerId)
                    trigger.effect_order[prevDisplayId], trigger.effect_order[displayId]\
                        = trigger.effect_order[displayId], trigger.effect_order[prevDisplayId]
                # See if out of sight
                if not self.tl.bbox(curItem):
                    self.tl.see(curItem)

    def itemMoveDown(self):
        curItem = self.tl.focus()
        if curItem == '':
            return
        next = self.tl.next(curItem)
        if next != '':
            id, displayId = self.tl.getNodeId(curItem)
            nextId, nextDisplayId = self.tl.getNodeId(next)
            if displayId + 1 == nextDisplayId:
                self.tl.move(curItem, self.tl.parent(curItem), self.tl.index(next))
                displayId, nextDisplayId = nextDisplayId, displayId
                self.tl.setNodeId(curItem, (id, displayId))
                self.tl.setNodeId(next, (nextId, nextDisplayId))
                if self.tl.itemType(curItem) == 'trigger':
                    # Call AoE2SP
                    self.tm.trigger_display_order[nextDisplayId], self.tm.trigger_display_order[displayId]\
                        = self.tm.trigger_display_order[displayId], self.tm.trigger_display_order[nextDisplayId]
                elif self.tl.itemType(curItem) == 'condition':
                    # Call AoE2SP
                    triggerId, triggerDisplayId = self.tl.getNodeId(self.tl.getTriggerNode(curItem))
                    trigger = self.tm.get_trigger(triggerId)
                    trigger.condition_order[nextDisplayId], trigger.condition_order[displayId]\
                        = trigger.condition_order[displayId], trigger.condition_order[nextDisplayId]
                elif self.tl.itemType(curItem) == 'effect':
                    # Call AoE2SP
                    triggerId, triggerDisplayId = self.tl.getNodeId(self.tl.getTriggerNode(curItem))
                    trigger = self.tm.get_trigger(triggerId)
                    trigger.effect_order[nextDisplayId], trigger.effect_order[displayId]\
                        = trigger.effect_order[displayId], trigger.effect_order[nextDisplayId]
                # See if out of sight
                if not self.tl.bbox(curItem):
                    self.tl.see(curItem)

    def itemDuplicate(self):
        curItem = self.tl.focus()
        if curItem == '':
            return
        nodeType = self.tl.itemType(curItem)
        parent = self.tl.getTriggerNode(curItem)
        triggerId = self.tl.getNodeId(parent)[0]
        idToDuplicate, displayIdToDuplicate = self.tl.getNodeId(curItem)
        next = self.tl.next(curItem)
        if nodeType == 'trigger':
            duplicatedTrigger = self.tm.copy_trigger(idToDuplicate, append_after_source=False, add_suffix=False)
            duplicatedTrigger.name = TEXT['formatDuplicatedTriggerName'].format(duplicatedTrigger.name)
            self.tm.trigger_display_order.insert(displayIdToDuplicate + 1, self.tm.trigger_display_order.pop())
            # print(self.tm.trigger_display_order)
            self.triggerNewAfter(displayIdToDuplicate, duplicatedTrigger)
        elif nodeType == 'condition':
            trigger = self.tm.get_trigger(triggerId)
            newCondition = copyCondition(trigger.conditions[idToDuplicate], trigger)
            self.ceAdd(parent, 'condition', newCondition)
        else:
            trigger = self.tm.get_trigger(triggerId)
            newEffect = copyEffect(trigger.effects[idToDuplicate], trigger)
            self.ceAdd(parent, 'effect', newEffect)

        # See if out of sight
        if not self.tl.bbox(self.tl.next(curItem)):
            self.tl.see(self.tl.next(curItem))

    def itemDuplicateForAll(self):
        curItem = self.tl.focus()
        if curItem == '':
            return
        nodeType = self.tl.itemType(curItem)
        parent = self.tl.getTriggerNode(curItem)
        triggerId = self.tl.getNodeId(parent)[0]
        idToDuplicate, displayIdToDuplicate = self.tl.getNodeId(curItem)
        next = self.tl.next(curItem)
        playerCount = self.app.activeScenario.player_manager.active_players
        create_copy_for_players = list(range(1, playerCount+1))
        if nodeType == 'trigger':
            trigger = self.tm.get_trigger(idToDuplicate)
            if self.app.options.addDuplicateMark.get():
                if trigger.description.endswith('<Copy>'):
                    return
                if trigger.description.endswith('<Original>'):
                    trigger.description = trigger.description[:-len('<Original>')]
            newTriggers = self.copyTriggerPerPlayer(PlayerId.ONE, trigger,
                                                    change_from_player_only = self.app.options.changeFromPlayerOnly.get(),
                                                    include_player_source = self.app.options.includeSource.get(),
                                                    include_player_target = self.app.options.includeTarget.get(),
                                                    create_copy_for_players = create_copy_for_players,
                                                    name_fix_format = self.app.options.nameFixFormat.get(),
                                                    name_gaia_fix = self.app.options.nameGaiaFix.get())
            if self.app.options.addDuplicateMark.get():
                if not trigger.description.endswith('<Original>'):
                    trigger.description += '<Original>'
            newTriggerCount = len(newTriggers)
            self.tm.trigger_display_order = \
                self.tm.trigger_display_order[0 : displayIdToDuplicate + 1] + \
                self.tm.trigger_display_order[-newTriggerCount:] + \
                self.tm.trigger_display_order[displayIdToDuplicate + 1 : -newTriggerCount]
            afterIndex = displayIdToDuplicate
            for newTrigger in newTriggers.values():
                if self.app.options.addDuplicateMark.get():
                    newTrigger.description += '<Copy>'
                self.triggerNewAfter(afterIndex, newTrigger)
                afterIndex += 1
            
        elif nodeType == 'condition':
            trigger = self.tm.get_trigger(triggerId)
            condition = trigger.conditions[idToDuplicate]
            newConditions = self.copyCePerPlayer(PlayerId.ONE, condition, trigger,
                                                change_from_player_only = self.app.options.changeFromPlayerOnly.get(),
                                                include_player_source = self.app.options.includeSource.get(),
                                                include_player_target = self.app.options.includeTarget.get(),
                                                create_copy_for_players = create_copy_for_players)
            for newCondition in newConditions.values():
                self.ceAdd(parent, 'condition', newCondition)
            # Todo: move to source
        else:
            trigger = self.tm.get_trigger(triggerId)
            effect = trigger.effects[idToDuplicate]
            newEffects = self.copyCePerPlayer(PlayerId.ONE, effect, trigger,
                                                change_from_player_only = self.app.options.changeFromPlayerOnly.get(),
                                                include_player_source = self.app.options.includeSource.get(),
                                                include_player_target = self.app.options.includeTarget.get(),
                                                create_copy_for_players = create_copy_for_players)
            for newEffect in newEffects.values():
                self.ceAdd(parent, 'effect', newEffect)

        # See if out of sight
        if not self.tl.bbox(next):
            self.tl.see(next)
        self.tl.focus(next)
        self.tl.selection_set(next)

    def triggerSimilarCheck(self, triggerIds: list[int]):
        # Todo: Check other attr
        srcTrigger = self.tm.get_trigger(triggerIds[0])
        srcConditionTypesChar = [condition.condition_type for condition in srcTrigger.conditions]
        srcEffectTypesChar = [effect.effect_type for effect in srcTrigger.effects]
        for i in range(1, len(triggerIds)):
            trigger = self.tm.get_trigger(triggerIds[i])
            conditionTypesChar = [condition.condition_type for condition in trigger.conditions]
            effectTypesChar = [effect.effect_type for effect in trigger.effects]
            if conditionTypesChar != srcConditionTypesChar \
                or effectTypesChar != srcEffectTypesChar:
                return False
        return True

    def conditionSimilarCheck(self, ceIds: list[int], trigger: Trigger):
        srcCe = trigger.conditions[ceIds[0]]
        for i in range(1, len(ceIds)):
            ce = trigger.conditions[ceIds[i]]
            if ce.condition_type != srcCe.condition_type:
                return False
        return True

    def effectSimilarCheck(self, ceIds: list[int], trigger: Trigger):
        srcCe = trigger.effects[ceIds[0]]
        for i in range(1, len(ceIds)):
            ce = trigger.effects[ceIds[i]]
            if ce.effect_type != srcCe.effect_type:
                return False
        return True

    def itemUnduplicateForAll(self):
        curItem = self.tl.focus()
        if curItem == '':
            return
        nodeType = self.tl.itemType(curItem)
        parent = self.tl.getTriggerNode(curItem)
        triggerId = self.tl.getNodeId(parent)[0]
        id, displayId = self.tl.getNodeId(curItem)
        next = self.tl.next(curItem)
        playerCount = self.app.activeScenario.player_manager.active_players
        if nodeType == 'trigger':
            if displayId + playerCount > len(self.tm.triggers):
                self.app.statusBarMessage(TEXT['noticeNotEnoughTriggersToDelete'])
                return
            else:
                check = self.triggerSimilarCheck([self.tm.trigger_display_order[i] for i in range(displayId, displayId + playerCount)])
                if check is False:
                    if not askokcancel(TEXT['messageTitleWarning'], TEXT['messageWarningDeduplicateNotMatch'], icon='warning'):
                        return
        elif nodeType == 'condition':
            trigger = self.tm.get_trigger(triggerId)
            if displayId + playerCount - 1 >= len(trigger.conditions):
                self.app.statusBarMessage(TEXT['noticeNotEnoughConditionsToDelete'])
                return
            else:
                check = self.conditionSimilarCheck([trigger.condition_order[i] for i in range(displayId, displayId + playerCount)], trigger)
                if check is False:
                    if not askokcancel(TEXT['messageTitleWarning'], TEXT['messageWarningDeduplicateNotMatch'], icon='warning'):
                        return
        else:
            trigger = self.tm.get_trigger(triggerId)
            if displayId + playerCount - 1 >= len(trigger.effects):
                self.app.statusBarMessage(TEXT['noticeNotEnoughEffectsToDelete'])
                return
            else:
                check = self.effectSimilarCheck([trigger.effect_order[i] for i in range(displayId, displayId + playerCount)], trigger)
                if check is False:
                    if not askokcancel(TEXT['messageTitleWarning'], TEXT['messageWarningDeduplicateNotMatch'], icon='warning'):
                        return
        self.tl.focus(next)
        for i in range(1, playerCount):
            self.itemDelete()
        # See if out of sight
        if not self.tl.bbox(curItem):
            self.tl.see(curItem)

    def __copyTriggerFast(self, trigger: Trigger) -> Trigger:
        """Call trigger reference directly for boost, than the same method in ASP"""

        deepcopy_trigger = copy.deepcopy(trigger)
        deepcopy_trigger.trigger_id = len(self.tm.triggers)

        self.tm.triggers.append(deepcopy_trigger)

        return deepcopy_trigger

    def copyTriggerPerPlayer(
            self,
            from_player: int,
            trigger: Trigger,
            change_from_player_only: bool = False,
            include_player_source: bool = True,
            include_player_target: bool = False,
            trigger_ce_lock: TriggerCELock | None = None,
            include_gaia: bool = False,
            create_copy_for_players: list[int] = None,
            name_fix_format: str = "(p{0})",
            name_gaia_fix: str = "(GAIA)"
    ) -> dict[PlayerId, Trigger]:
        """
        Copies a trigger for all or a selection of players. Every copy will change desired player attributes with it.

        Args:
            from_player: The central player this trigger is created for. This is the player that will not get
                a copy.
            trigger_select: The ID of the trigger or an object used to identify which trigger to select.
            change_from_player_only: If set to `True`,  only change player attributes in effects and conditions that
                are equal to the player defined using the `from_player` parameter.
            include_player_source: If set to `True`,  allow player source attributes to be changed while copying.
                Player source attributes are attributes where a player is defined to perform an action such as create an
                object. If set to `False` these attributes will remain unchanged.
            include_player_target: If set to `True`,  allow player target attributes to be changed while copying.
                Player target attributes are attributes where a player is defined as the target such as change ownership
                or sending resources. If set to `False` these attributes will remain unchanged.
            trigger_ce_lock: The TriggerCELock object. Used to lock certain (types) of conditions or
                effects from being changed while copying.
            include_gaia: If `True`,  GAIA is included in the copied list. (Also when `create_copy_for_players` is
                defined)
            create_copy_for_players: A list of Players to create a copy for. The `from_player` will be
                excluded from this list.

        Returns:
            A dict with all the new created triggers. The key is the player for which the trigger is
                created using the IntEnum associated with it. Example:
                `{PlayerId.TWO: Trigger, PlayerId.FIVE: Trigger}`

        Raises:
            ValueError: if more than one trigger selection is used. Any of (trigger_index, display_index or trigger)
                Or if Both `include_player_source` and `include_player_target` are `False`
        """
        if create_copy_for_players is None:
            create_copy_for_players = [
                PlayerId.ONE, PlayerId.TWO, PlayerId.THREE, PlayerId.FOUR,
                PlayerId.FIVE, PlayerId.SIX, PlayerId.SEVEN, PlayerId.EIGHT
            ]
        if include_gaia and PlayerId.GAIA not in create_copy_for_players:
            create_copy_for_players.append(PlayerId.GAIA)

        alter_conditions, alter_effects = TriggerManager._find_alterable_ce(trigger, trigger_ce_lock)

        return_dict: dict[PlayerId, Trigger] = {}
        for player in create_copy_for_players:
            if player == from_player:
                continue

            new_trigger = self.__copyTriggerFast(trigger)
            # new_trigger = self.tm.copy_trigger(TriggerSelect.trigger(trigger), append_after_source=False, add_suffix=False)
            new_trigger.name += " " + (name_gaia_fix if player == PlayerId.GAIA else name_fix_format.format(player))
            return_dict[player] = new_trigger

            for cond_x in alter_conditions:
                cond:Condition = new_trigger.conditions[cond_x]
                if cond.source_player == -1 and cond.target_player == -1:
                    continue

                if include_player_source:
                    if not change_from_player_only or (change_from_player_only and cond.source_player == from_player):
                        cond.source_player = PlayerId(player)
                if include_player_target:
                    if not change_from_player_only or (change_from_player_only and cond.target_player == from_player):
                        cond.target_player = PlayerId(player)

            for effect_x in alter_effects:
                effect:Effect = new_trigger.effects[effect_x]
                if effect.source_player == -1 and effect.target_player == -1:
                    continue

                if include_player_source:
                    if not change_from_player_only or (change_from_player_only and effect.source_player == from_player):
                        effect.source_player = PlayerId(player)
                if include_player_target:
                    if not change_from_player_only or (change_from_player_only and effect.target_player == from_player):
                        effect.target_player = PlayerId(player)

        return return_dict

    def copyCePerPlayer(
            self,
            from_player: int,
            srcCe: Condition | Effect,
            parent: Trigger,
            change_from_player_only: bool = False,
            include_player_source: bool = True,
            include_player_target: bool = False,
            include_gaia: bool = False,
            create_copy_for_players: list[int] = None
    ) -> dict[PlayerId, Trigger]:
        if type(srcCe) == Condition:
            copyCe = copyCondition
        else:
            copyCe = copyEffect

        if create_copy_for_players is None:
            create_copy_for_players = [
                PlayerId.ONE, PlayerId.TWO, PlayerId.THREE, PlayerId.FOUR,
                PlayerId.FIVE, PlayerId.SIX, PlayerId.SEVEN, PlayerId.EIGHT
            ]
        if include_gaia and PlayerId.GAIA not in create_copy_for_players:
            create_copy_for_players.append(PlayerId.GAIA)

        return_dict: dict[PlayerId, Condition | Effect] = {}
        for player in create_copy_for_players:
            if player == from_player:
                continue

            new_ce = copyCe(srcCe, parent)
            return_dict[player] = new_ce

            if new_ce.source_player == -1 and new_ce.target_player == -1:
                continue

            if include_player_source:
                if not change_from_player_only or (change_from_player_only and new_ce.source_player == from_player):
                    new_ce.source_player = PlayerId(player)
            if include_player_target:
                if not change_from_player_only or (change_from_player_only and new_ce.target_player == from_player):
                    new_ce.target_player = PlayerId(player)

        return return_dict

    def clearRangeValue(self) -> None:
        """Clear the range value on ValueSelectButton"""
        self.varTSelectFront.set('-')
        self.varTSelectBack.set('-')
        self.varTSelectTarget.set('-')

    def getRangeValue(self) -> tuple[int, int, int] | str:
        """Get the range selected by ValueSelectButton"""
        begin = self.varTSelectFront.get()
        end = self.varTSelectBack.get()
        target = self.varTSelectTarget.get()
        if begin.isdigit() == False or end.isdigit() == False:
            return TEXT['noticeValueRangeErrMsgValueMissing']
        begin = int(begin)
        end = int(end)

        if begin > end:
            return TEXT['noticeValueRangeErrMsgFrontLargerThanBack']
        end += 1

        triggerCount = len(self.tl.get_children(""))
        if begin >= triggerCount:
            return TEXT['noticeValueRangeErrMsgFrontLargerThanTotal']
        if end > triggerCount:
            end = triggerCount

        if target.isdigit() == True:
            target = int(target)
            if target > triggerCount:
                target = triggerCount
        else:
            target = None
        return begin, end, target

    def triggerDuplicateMultiple(self):
        valueRange = self.getRangeValue()
        if type(valueRange) == str:
            self.app.statusBarMessage(TEXT['noticeFormatValueRangeInvalid'].format(valueRange))
            return
        displayIdBegin, displayIdEnd, displayIdTarget = valueRange

        toDuplicateTriggersIdList = self.tm.trigger_display_order[displayIdBegin: displayIdEnd]
        newTriggerOrder = self.tm.trigger_display_order[0: displayIdBegin]
        newTriggerOrderTail = self.tm.trigger_display_order[displayIdEnd:]
        playerCount = self.app.activeScenario.player_manager.active_players
        create_copy_for_players = list(range(1, playerCount+1))
        for id in toDuplicateTriggersIdList:
            # Duplicate trigger
            trigger = self.tm.get_trigger(id)
            if self.app.options.addDuplicateMark.get():
                if trigger.description.endswith('<Copy>'):
                    continue
                if trigger.description.endswith('<Original>'):
                    trigger.description = trigger.description[:-len('<Original>')]
            newTriggers = self.copyTriggerPerPlayer(PlayerId.ONE, trigger,
                                                    change_from_player_only = self.app.options.changeFromPlayerOnly.get(),
                                                    include_player_source = self.app.options.includeSource.get(),
                                                    include_player_target = self.app.options.includeTarget.get(),
                                                    create_copy_for_players = create_copy_for_players,
                                                    name_fix_format = self.app.options.nameFixFormat.get(),
                                                    name_gaia_fix = self.app.options.nameGaiaFix.get())
            if self.app.options.addDuplicateMark.get():
                if not trigger.description.endswith('<Original>'):
                    trigger.description += '<Original>'
            newTriggerCount = len(newTriggers)
            newTriggerOrder.append(id)
            afterIndex = len(newTriggerOrder) - 1
            newTriggerOrder += self.tm.trigger_display_order[-newTriggerCount:]
            # Add nodes
            for newTrigger in newTriggers.values():
                if self.app.options.addDuplicateMark.get():
                    newTrigger.description += '<Copy>'
                self.triggerNewAfter(afterIndex, newTrigger, ignoreIndex=True)
                afterIndex += 1

        newTriggerOrder += newTriggerOrderTail
        self.tm.trigger_display_order = newTriggerOrder
        # Update IDs
        for displayId, child in enumerate(self.tl.get_children('')):
            if child == '':
                break
            else:
                self.tl.setNodeId(child, (self.tm.trigger_display_order[displayId], displayId))
        # self.tl.focus(self.tl.get_children("")[displayIdBegin])
        # self.tl.selection_set(next)
        self.clearRangeValue()
        self.app.statusBarMessage(TEXT['noticeDuplicateCompleted'])

    def triggerUnduplicateMultiple(self):
        valueRange = self.getRangeValue()
        if type(valueRange) == str:
            self.app.statusBarMessage(TEXT['noticeFormatValueRangeInvalid'].format(valueRange))
            return
        displayIdBegin, displayIdEnd, displayIdTarget = valueRange

        # Todo: remove marked only
        # if self.app.options.removeMarked.get():
        #     toRemoveTriggersIdList = []
        #     for i in range(displayIdBegin, displayIdEnd):
        #         trigger = self.tm.get_trigger(self.tm.trigger_display_order[i])
        #         if trigger.description.endswith('<Copy>'):
        #             toRemoveTriggersIdList.append(trigger.trigger_id)
        #     items = self.tl.get_children("")
        #     for i in range(displayIdEnd - 1, displayIdBegin - 1, -1):
        #         if self.tl.getNodeId(items[i])[0] in toRemoveTriggersIdList:
        #             self.tl.delete(items[i])
        #     next = ''

        playerCount = self.app.activeScenario.player_manager.active_players
        if (displayIdEnd - displayIdBegin) % playerCount != 0:
            self.app.statusBarMessage(TEXT['noticeFormatValueRangeInvalid'].format(TEXT['noticeValueRangeErrMsgMustBeMultiple']))
            return

        itemTrigger = self.tl.get_children("")[displayIdBegin]
        toRemoveTriggersIdList = [self.tm.trigger_display_order[i] \
                                for i in range(displayIdBegin, displayIdEnd) \
                                if (i - displayIdBegin) % playerCount != 0]
        # Delete nodes
        for i in range(displayIdBegin, displayIdEnd):
            next = self.tl.next(itemTrigger)
            if (i - displayIdBegin) % playerCount != 0:
                self.tl.delete(itemTrigger)
            itemTrigger = next
        # Delete triggers
        self.tm.remove_triggers(toRemoveTriggersIdList)
        # Update IDs
        for displayId, child in enumerate(self.tl.get_children('')):
            if child == '':
                break
            else:
                self.tl.setNodeId(child, (self.tm.trigger_display_order[displayId], displayId))
        self.tl.focus(next)
        self.tl.selection_set(next)
        self.clearRangeValue()
        self.app.statusBarMessage(TEXT['noticeDeduplicateCompleted'])

    def triggerDeleteMultiple(self):
        valueRange = self.getRangeValue()
        if type(valueRange) == str:
            self.app.statusBarMessage(TEXT['noticeFormatValueRangeInvalid'].format(valueRange))
            return
        displayIdBegin, displayIdEnd, displayIdTarget = valueRange

        itemTrigger = self.tl.get_children("")[displayIdBegin]
        toRemoveTriggersIdList = self.tm.trigger_display_order[displayIdBegin: displayIdEnd]
        # Delete nodes
        for i in range(displayIdBegin, displayIdEnd):
            next = self.tl.next(itemTrigger)
            self.tl.delete(itemTrigger)
            itemTrigger = next
        # Delete triggers
        self.tm.remove_triggers(toRemoveTriggersIdList)
        # Update IDs
        for displayId, child in enumerate(self.tl.get_children('')):
            if child == '':
                break
            else:
                self.tl.setNodeId(child, (self.tm.trigger_display_order[displayId], displayId))
        self.tl.focus(next)
        self.tl.selection_set(next)
        self.clearRangeValue()
        self.app.statusBarMessage(TEXT['noticeDeleteDuplicateCompleted'])

    def triggerMoveMultiple(self):
        valueRange = self.getRangeValue()
        if type(valueRange) == str:
            self.app.statusBarMessage(TEXT['noticeFormatValueRangeInvalid'].format(valueRange))
            return
        displayIdBegin, displayIdEnd, displayIdTarget = valueRange

        if displayIdTarget == None:
            self.app.statusBarMessage(TEXT['noticeFormatValueRangeInvalid'].format(TEXT['noticeValueRangeErrMsgTargetMissing']))
            return

        if not (displayIdTarget < displayIdBegin or displayIdTarget > displayIdEnd):
            self.app.statusBarMessage(TEXT['noticeFormatValueRangeInvalid'].format(TEXT['noticeValueRangeErrMsgTargetInRange']))
            return

        if displayIdTarget > displayIdEnd:
            displayIdBegin, displayIdEnd, displayIdTarget = displayIdEnd, displayIdTarget, displayIdBegin
        # Fix displayID between target and begin
        itemFix = self.tl.get_children("")[displayIdTarget]
        for i in range(displayIdTarget, displayIdBegin):
            nextFix = self.tl.next(itemFix)
            id, dId = self.tl.getNodeId(itemFix)
            self.tl.setNodeId(itemFix, (id, dId + (displayIdEnd - displayIdBegin)))
            itemFix = nextFix
        # Move and fix displayID
        itemMove = self.tl.get_children("")[displayIdEnd-1]
        for i in range(displayIdEnd-1, displayIdBegin-1, -1):
            nextMove = self.tl.prev(itemMove)
            id, dId = self.tl.getNodeId(itemMove)
            self.tl.move(itemMove, '', displayIdTarget)
            self.tl.setNodeId(itemMove, (id, dId - (displayIdBegin - displayIdTarget)))
            itemMove = nextMove
        # Move scen display order
        self.tm.trigger_display_order = \
            self.tm.trigger_display_order[0 : displayIdTarget] + \
            self.tm.trigger_display_order[displayIdBegin : displayIdEnd] + \
            self.tm.trigger_display_order[displayIdTarget : displayIdBegin] + \
            self.tm.trigger_display_order[displayIdEnd :]

    def itemSortByDisplay(self):
        if len(self.tm.triggers) == 0:
            return
        self.tm.reorder_triggers(self.tm.trigger_display_order)
        # Update IDs
        for displayId, child in enumerate(self.tl.get_children('')):
            if child == '':
                break
            else:
                self.tl.setNodeId(child, (self.tm.trigger_display_order[displayId], displayId))
        self.app.statusBarMessage(TEXT['noticeSortCompleted'])

    def itemSortCeByDisplay(self):
        for trigger in self.tm.triggers:
            reorderCEs(trigger, True, True)
        # Update IDs
        for displayId, child in enumerate(self.tl.get_children('')):
            if child == '':
                break
            else:
                triggerId = self.tm.trigger_display_order[displayId]
                trigger = self.tm.get_trigger(triggerId)
                conditionAmount = len(trigger.conditions)
                for ceDisplayId, ceChild in enumerate(self.tl.get_children(child)):
                    if ceDisplayId < conditionAmount:
                        cDId = ceDisplayId
                        self.tl.setNodeId(ceChild, (trigger.condition_order[cDId], cDId))
                    else:
                        eDId = ceDisplayId - conditionAmount
                        self.tl.setNodeId(ceChild, (trigger.effect_order[eDId], eDId))

        self.app.statusBarMessage(TEXT['noticeSortCompleted'])

    # endregion TriggerViewOperation
