from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from tkinter.constants import *
import ttkbootstrap as ttk

from AoE2ScenarioParser.objects.managers.unit_manager import UnitManager
from AoE2ScenarioParser.objects.data_objects.unit import Unit

from Localization import TEXT
from Util import MappedCombobox
from TriggerAbstract import getPlayerAbstract, getUnitListName

if TYPE_CHECKING:
    from main import TCWindow

class UnitKey():
    """
    The unit's owner ID and list index are its primary key.
    NOT reference_id because of the possibility of duplication in some scenarios.
    """
    def __init__(self, player: int, index: int):
        self.player = player
        self.index = index

    def __eq__(self, rhs: UnitKey) -> bool:
        return self.player == rhs.player and self.index == rhs.index

    @classmethod
    def fromTuple(cls, keyTuple: tuple[int, int]):
        return cls(keyTuple[0], keyTuple[1])

    def getUnit(self, um: UnitManager) -> Unit:
        return um.units[self.player][self.index]

class UnitTreeView(ttk.Treeview):
    """
    A Treeview shows units.

    Node text holds the unit id, and values[0] holds the name.
    values[1:] holds the UnitKey.
    """
    def __init__(self, master=None, show=ttk.TREE, selectmode=EXTENDED, columns=(0), **kwargs):
        super().__init__(master, show=show, selectmode=selectmode, columns=columns, **kwargs)

    def insert(self, parent, index, uId:int, ulId:int, pId:int, listId:int, **kwargs):
        return super().insert(parent, index, text=f'{uId}',
                              values=(getUnitListName(ulId), pId, listId), **kwargs)

    def getNodeUnitKey(self, item:str) -> UnitKey:
        return UnitKey(*self.item(item)['values'][1:3])

    def getUnitFocusKey(self) -> UnitKey | None:
        focusUnit = self.focus()
        if focusUnit == '' or len(self.selection()) == 0:
            return None
        return self.getNodeUnitKey(focusUnit)

    def getNodeRefId(self, item:str) -> int:
        return int(self.item(item)['text'])

    def setNodeRefId(self, item:str, uId: int):
        self.item(item, text=f'{uId}')

    def getUnitFocusRefId(self) -> int | None:
        focusUnit = self.focus()
        if focusUnit == '' or len(self.selection()) == 0:
            return None
        return int(self.item(focusUnit)['text'])

    def getUnitsSelectionRefId(self) -> list[int]:
        selectedUnits = self.selection()
        return [int(self.item(unitItem)['text']) for unitItem in selectedUnits]

    def setNodeConst(self, item:str, ulId: int):
        key = self.getNodeUnitKey(item)
        self.item(item, values=(getUnitListName(ulId), key.player, key.index))

class UnitView(ttk.Frame):
    @property
    def tm(self):
        return self.app.triggerManager

    @property
    def tl(self):
        return self.app.fTEditor.tvTriggerList

    @property
    def um(self):
        return self.app.activeScenario.unit_manager

    @property
    def pm(self):
        return self.app.activeScenario.player_manager

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        self.fUListPanel = ttk.Frame(self)
        self.fUListPanel.pack(side=TOP, anchor=W)
        self.varUPlayerFilter = ttk.IntVar()
        self.cbUPlayerFilter = MappedCombobox(self.fUListPanel, {},
                                   self.varUPlayerFilter,
                                   state="readonly",
                                   width=10)
        self.cbUPlayerFilter.pack(side=LEFT, anchor=W, padx=self.app.dpi((10, 0)), pady=self.app.dpi((10, 10)))
        self.cbUPlayerFilter.set_display_event(self.__modifyUnitFilter)
        self.cbUPlayerFilter.bind("<<ComboboxSelected>>", lambda e: self.cbUPlayerFilter.selection_clear())
        self.cbUAreaFilter = ttk.Combobox(self.fUListPanel,
                                    values=[TEXT['comboValueFullMap'], TEXT['comboValueSelectedArea']],
                                    state="readonly", width=14)
        self.cbUAreaFilter.pack(side=LEFT, anchor=W, padx=self.app.dpi((10, 0)), pady=self.app.dpi((10, 10)))
        self.cbUAreaFilter.bind("<<ComboboxSelected>>", lambda e: (self.cbUAreaFilter.selection_clear(), self.__modifyUnitFilter()))
        self.cbUAreaFilter.current(0)

        ## UnitList
        lfUList = ttk.LabelFrame(self, text=TEXT['labelUnitList'])
        lfUList.pack(fill=BOTH, expand=YES, padx=self.app.dpi((10, 5)), pady=self.app.dpi((0, 5)))
        self.tvUnitList = UnitTreeView(master=lfUList, style='Borderless.Treeview')
        # self.tvUnitList.bind('<<TreeviewSelect>>', self.__selectUnit)
        self.tvUnitList.bind('<Double-1>', self.__selectUnit)
        self.tvUnitList.bind('<Return>', self.__selectUnit)
        tvsbUnitList = ttk.Scrollbar(master=lfUList, command=self.tvUnitList.yview)
        self.tvUnitList.configure(yscrollcommand=tvsbUnitList.set)
        self.tvUnitList.column('#0', width=self.app.dpi(60), stretch=False)
        self.tvUnitList.column('#1', width=self.app.dpi(100))

        tvsbUnitList.pack(side=RIGHT, fill=Y)
        self.tvUnitList.pack(side=RIGHT, fill=BOTH, expand=YES)

    def updatePlayerList(self):
        playerDict = {i:getPlayerAbstract(i) for i in range(0, self.pm.active_players + 1)}
        playerDictEx = {-1:TEXT['comboValueNone']}
        playerDictEx.update(playerDict)
        playerDictEx.update({-2:TEXT['comboValueAllPlayer']})
        self.cbUPlayerFilter.update_mapping(playerDictEx)
        self.cbUPlayerFilter.current(0)
        self.app.fUnitInfo.cbUPlayer.update_mapping(playerDict)
        self.app.fUnitInfo.unitFocus = None

    def getUnitById(self, id, firstSearchPlayer=0) -> Unit:
        """Get Unit object by reference_id, search every player to find the unit."""
        # Search from selected player first
        playerList = [firstSearchPlayer, ] + \
            [i for i in range(0, self.pm.active_players + 1) if i != firstSearchPlayer]
        for p in playerList:
            unit = next((i for i in self.um.units[p] if i.reference_id == id), None)
            if unit != None:
                break
        return unit

    def __selectUnit(self, e):
        key = self.tvUnitList.getUnitFocusKey()
        self.app.fUnitInfo.unitFocus = key
        if key is not None:
            self.app.fUnitInfo.unitSelected(key.getUnit(self.um))
            self.app.nTabsRightBottom.select(self.app.fUnitInfo)

    def __modifyUnitFilter(self, *args):
        playerFilter = self.varUPlayerFilter.get()
        areaFilter = True if self.cbUAreaFilter.current() == 1 else False
        if areaFilter:
            x1, y1, x2, y2 = self.app.fMapViewTab.getArea()
            x2 += 1
            y2 += 1
        
        for item in self.tvUnitList.get_children():
            self.tvUnitList.delete(item)
        if playerFilter >= 0:
            playerList = [playerFilter, ]
        elif playerFilter == -2:
            playerList = [p for p in range(0, self.pm.active_players + 1)]
        else:
            return
        for player in playerList:
            for listId, unit in enumerate(self.um.units[player]):
                if areaFilter:
                    if unit.x >= x1 and unit.x < x2 and unit.y >= y1 and unit.y < y2:
                        self.tvUnitList.insert('', END, unit.reference_id, unit.unit_const, player, listId)
                else:
                    self.tvUnitList.insert('', END, unit.reference_id, unit.unit_const, player, listId)

    def unitIdFilter(self, refIds: list[int]):
        if refIds == []:
            return
        for item in self.tvUnitList.get_children():
            self.tvUnitList.delete(item)
        playerList = [p for p in range(0, self.pm.active_players + 1)]
        for player in playerList:
            for listId, unit in enumerate(self.um.units[player]):
                if unit.reference_id in refIds:
                    self.tvUnitList.insert('', END, unit.reference_id, unit.unit_const, player, listId)
        items = self.tvUnitList.get_children()
        if items:
            self.tvUnitList.focus(items[0])
            self.tvUnitList.selection_set(items)
