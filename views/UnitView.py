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

class UnitTreeView(ttk.Treeview):
    """
    A Treeview shows units.

    Node text holds the unit id, and values[0] holds the name.
    """
    def __init__(self, master=None, show=ttk.TREE, selectmode=EXTENDED, columns=(0), **kwargs):
        super().__init__(master, show=show, selectmode=selectmode, columns=columns, **kwargs)

    def insert(self, parent, index, uId:int, ulId:int, **kwargs):
        return super().insert(parent, index, text=f'{uId}',
                              values=(getUnitListName(ulId), ), **kwargs)

    def getNodeId(self, item:str) -> int:
        return int(self.item(item)['text'])

    def setNodeConst(self, item:str, ulId: int):
        self.item(item, values=(getUnitListName(ulId), ))

    def getUnitFocusId(self) -> int | None:
        focusUnit = self.focus()
        if focusUnit == '' or len(self.selection()) == 0:
            return None
        return int(self.item(focusUnit)['text'])

    def getUnitsSelectionId(self) -> list[int]:
        selectedUnits = self.selection()
        return [int(self.item(unitItem)['text']) for unitItem in selectedUnits]

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
        playerDict = {i:getPlayerAbstract(i) for i in range(0, self.app.activeScenario.player_manager.active_players + 1)}
        playerDictEx = {-1:TEXT['comboValueNone']}
        playerDictEx.update(playerDict)
        playerDictEx.update({-2:TEXT['comboValueAllPlayer']})
        self.cbUPlayerFilter.update_mapping(playerDictEx)
        self.cbUPlayerFilter.current(0)
        self.app.fUnitInfo.cbUPlayer.update_mapping(playerDict)

    def getUnitById(self, id, firstSearchPlayer=0) -> Unit:
        """Get Unit object by reference_id, search every player to find the unit."""
        # Search from selected player first
        playerList = [firstSearchPlayer, ] + \
            [i for i in range(0, self.app.activeScenario.player_manager.active_players + 1) if i != firstSearchPlayer]
        for p in playerList:
            unit = next((i for i in self.um.units[p] if i.reference_id == id), None)
            if unit != None:
                break
        return unit

    def getUnitFocus(self) -> Unit:
        unitId = self.tvUnitList.getUnitFocusId()
        if unitId == None:
            return None
        playerFilter = self.varUPlayerFilter.get()
        return self.getUnitById(unitId, playerFilter if playerFilter >= 0 else 0)

    def __selectUnit(self, e):
        unit = self.getUnitFocus()
        self.app.fUnitInfo.unitFocus = unit
        if unit == None:
            return
        if unit is not None:
            self.app.fUnitInfo.unitSelected(unit)
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
            units = self.um.get_player_units(playerFilter)
        elif playerFilter == -2:
            units = self.um.get_all_units()
        else:
            return
        for unit in units:
            if areaFilter:
                if unit.x >= x1 and unit.x < x2 and unit.y >= y1 and unit.y < y2:
                    self.tvUnitList.insert('', END, unit.reference_id, unit.unit_const)
            else:
                self.tvUnitList.insert('', END, unit.reference_id, unit.unit_const)
