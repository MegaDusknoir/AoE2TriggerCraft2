from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from tkinter.constants import *
import ttkbootstrap as ttk

from Localization import TEXT, TECH_NAME, UNIT_NAME
from TriggerAbstract import getPlayerAbstract
from Util import MappedCombobox

if TYPE_CHECKING:
    from main import TCWindow

class DisablesTreeView(ttk.Treeview):
    """
    A Treeview shows Disables or Availables.

    Node text holds the id, and values[0] holds the name.
    """
    def __init__(self, master=None, show=ttk.TREE, selectmode=EXTENDED, columns=(0), **kwargs):
        super().__init__(master, show=show, selectmode=selectmode, columns=columns, **kwargs)

    def clear(self):
        for item in self.get_children():
            self.delete(item)

    def insert(self, index, id:int, name: str, **kwargs):
        return super().insert('', index, text=str(id),
                              values=(name, ), **kwargs)

    def getNodeId(self, item:str) -> int:
        return int(self.item(item)['text'])

class DisablesView(ttk.Frame):
    def currentNameDict(self) -> dict | None:
        if self.varCategory.get() == 'unit':
            return self.unitDict
        elif self.varCategory.get() == 'building':
            return self.buildingDict
        elif self.varCategory.get() == 'tech':
            return TECH_NAME

    def currentDisablesList(self) -> list[int] | None:
        player = self.varPlayer.get()
        return self.getDisablesList(player, self.varCategory.get())

    def getDisablesList(self, player: int, category: str) -> list[int] | None:
        if category == 'unit':
            return self.app.activeScenario.player_manager.players[player].disabled_units
        elif category == 'building':
            return self.app.activeScenario.player_manager.players[player].disabled_buildings
        elif category == 'tech':
            return self.app.activeScenario.player_manager.players[player].disabled_techs

    def updateTree(self):
        self.tvDisabled.clear()
        self.tvAvailable.clear()
        self.varAvailableFilter.set(self.varAvailableFilter.get())
        self.varDisabledFilter.set(self.varDisabledFilter.get())

    def loadScen(self):
        playerDict = {i:getPlayerAbstract(i) \
            for i in range(1, self.app.activeScenario.player_manager.active_players + 1)}
        self.cbPlayer.update_mapping(playerDict)
        self.cbPlayer.current(0)

    def _copy(self):
        self.disablesClipboard = (self.varCategory.get(), self.currentDisablesList().copy())

    def _paste(self):
        if self.disablesClipboard:
            player = self.varPlayer.get()
            category, disableList = self.disablesClipboard
            self.getDisablesList(player, category)[:] = disableList
            if category == self.varCategory.get():
                self.updateTree()
            else:
                self.varCategory.set(category)

    def _copyToAll(self):
        sourcePlayer = self.varPlayer.get()
        sourceList = self.currentDisablesList()
        for p in [i for i in range(1, self.app.activeScenario.player_manager.active_players + 1) if i != sourcePlayer]:
            self.getDisablesList(p, self.varCategory.get())[:] = sourceList

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        padding = self.app.dpi(10)

        self.unitDict = {id:UNIT_NAME[id]["name"] \
            for id in UNIT_NAME \
                if UNIT_NAME[id]["type"] == 70 and UNIT_NAME[id]["hero_mode"]&1 == 0}
        self.buildingDict = {id:UNIT_NAME[id]["name"] \
                for id in UNIT_NAME \
                    if UNIT_NAME[id]["type"] == 80 and UNIT_NAME[id]["hero_mode"]&1 == 0}
        self.disablesClipboard: tuple[str, list[int]] = None

        # Player, category, methods
        fOptions = ttk.Frame(self)
        fOptions.grid(row=0, column=0, sticky=N, padx=(padding, padding // 2), pady=padding)

        self.varPlayer = ttk.IntVar()
        self.cbPlayer = MappedCombobox(fOptions, {}, # Load later
                                        self.varPlayer,
                                        state="readonly")
        self.cbPlayer.bind("<<ComboboxSelected>>", lambda e: self.cbPlayer.selection_clear())
        self.cbPlayer.pack(fill=X, pady=(0, padding))
        self.varPlayer.trace_add('write', lambda *args: self.updateTree())

        self.varCategory = ttk.StringVar(value='unit')
        for category, label in (
            ('unit', TEXT['labelUnitDisables']),
            ('building', TEXT['labelBuildingDisables']),
            ('tech', TEXT['labelTechDisables']),
        ):
            ttk.Radiobutton(
                fOptions,
                text=label,
                variable=self.varCategory,
                value=category,
            ).pack(anchor=W, pady=self.app.dpi(4))
        self.varCategory.trace_add('write', lambda *args: self.updateTree())
        ttk.Button(
            fOptions, text=TEXT['btnCopy'], bootstyle=ttk.OUTLINE,
            command=lambda: self._copy(),
        ).pack(anchor=W, fill=X, pady=self.app.dpi(4))
        ttk.Button(
            fOptions, text=TEXT['btnPaste'], bootstyle=ttk.OUTLINE,
            command=lambda: self._paste(),
        ).pack(anchor=W, fill=X, pady=self.app.dpi(4))
        ttk.Button(
            fOptions, text=TEXT['btnCopyToAll'], bootstyle=ttk.OUTLINE,
            command=lambda: self._copyToAll(),
        ).pack(anchor=W, fill=X, pady=self.app.dpi(4))

        # Disabled
        self.varDisabledFilter = ttk.StringVar()
        self.tvDisabled = self._createListFrame(
            column=1,
            title=TEXT['titleDisablesList'],
            var=self.varDisabledFilter,
            padx=(padding // 2, padding // 2),
        )

        # Transfer controls
        fTransfer = ttk.Frame(self)
        fTransfer.grid(row=0, column=2, sticky=NS, padx=padding // 2, pady=padding+self.app.dpi(30))
        ttk.Button(
            fTransfer, text='<',
            command=lambda: self._moveSelected(self.tvAvailable, self.tvDisabled, 'left'),
        ).pack(fill=X, pady=self.app.dpi(3))
        ttk.Button(
            fTransfer, text='>',
            command=lambda: self._moveSelected(self.tvDisabled, self.tvAvailable, 'right'),
        ).pack(fill=X, pady=self.app.dpi(3))
        ttk.Button(
            fTransfer, text='<<',
            command=lambda: self._moveAll(self.tvAvailable, self.tvDisabled, 'left'),
        ).pack(fill=X, pady=self.app.dpi(3))
        ttk.Button(
            fTransfer, text='>>',
            command=lambda: self._moveAll(self.tvDisabled, self.tvAvailable, 'right'),
        ).pack(fill=X, pady=self.app.dpi(3))

        # Available
        self.varAvailableFilter = ttk.StringVar()
        self.tvAvailable = self._createListFrame(
            column=3,
            title=TEXT['titleAvailablesList'],
            var=self.varAvailableFilter,
            padx=(padding // 2, padding),
        )

        self.varDisabledFilter.trace_add('write', lambda *arg: self._disableFilter(self.varDisabledFilter.get()))
        self.varAvailableFilter.trace_add('write', lambda *arg: self._availableFilter(self.varAvailableFilter.get()))

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _availableFilter(self, sstr: str):
        names = self.currentNameDict()
        disabled = self.currentDisablesList()
        self.tvAvailable.clear()
        if sstr == '':
            for id in names:
                if id not in disabled:
                    self.tvAvailable.insert(END, id, names[id])
        elif sstr.isdigit():
            sId = int(sstr)
            if sId not in names and sId not in disabled:
                self.tvAvailable.insert(END, sId, f'<{sId}>')
            for id in names:
                if id not in disabled and sstr in str(id):
                    self.tvAvailable.insert(END, id, names[id])
        else:
            for id in names:
                if id not in disabled and sstr.lower() in names[id].lower():
                    self.tvAvailable.insert(END, id, names[id])

    def _disableFilter(self, sstr: str):
        names = self.currentNameDict()
        disabled = self.currentDisablesList()
        self.tvDisabled.clear()
        if sstr == '':
            for id in disabled:
                self.tvDisabled.insert(END, id, names.get(id, f'<{id}>'))
        elif sstr.isdigit():
            for id in disabled:
                if sstr in str(id):
                    self.tvDisabled.insert(END, id, names.get(id, f'<{id}>'))
        else:
            for id in disabled:
                name = names.get(id, f'<{id}>')
                if sstr.lower() in name.lower():
                    self.tvDisabled.insert(END, id, name)

    def _createListFrame(self, column: int, title: str, var: ttk.StringVar, padx: tuple[int, int]) -> DisablesTreeView:
        fList = ttk.Frame(self)
        fList.grid(row=0, column=column, sticky=NSEW, padx=padx, pady=self.app.dpi(10))

        eFilter = ttk.Entry(fList, textvariable=var)
        eFilter.pack(side=TOP,fill=X)
        lfList = ttk.LabelFrame(fList, text=title)
        lfList.pack(side=TOP,fill=BOTH,expand=YES)

        tree = DisablesTreeView(lfList, style='Borderless.Treeview')
        tree.column('#0', width=self.app.dpi(50), stretch=False)
        scrollbar = ttk.Scrollbar(lfList, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        tree.pack(side=RIGHT, fill=BOTH, expand=YES)

        return tree

    def _moveSelected(self, source: DisablesTreeView, target: DisablesTreeView,
                      direction: Literal['left', 'right']) -> None:
        roots = source.selection()
        disabled = self.currentDisablesList()
        if direction == 'left':
            for item in roots:
                disabled.append(source.getNodeId(item))
        else:
            for item in roots:
                disabled.remove(source.getNodeId(item))
        DisablesView._transferItems(source, target, roots)

    def _moveAll(self, source: DisablesTreeView, target: DisablesTreeView,
                 direction: Literal['left', 'right']) -> None:
        roots = source.get_children('')
        disabled = self.currentDisablesList()
        if direction == 'left':
            for item in roots:
                disabled.append(source.getNodeId(item))
        else:
            for item in roots:
                disabled.remove(source.getNodeId(item))
        DisablesView._transferItems(source, target, roots)

    @staticmethod
    def _transferItems(source: DisablesTreeView, target: DisablesTreeView, items: list[str]) -> None:
        for item in items:
            details = source.item(item)
            copy = target.insert(END, details['text'], details['values'][0])
            source.delete(item)
