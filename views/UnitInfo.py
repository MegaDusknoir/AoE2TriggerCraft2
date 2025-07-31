from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Literal
from math import pi as PI
from tkinter.constants import *
import ttkbootstrap as ttk

from AoE2ScenarioParser.objects.data_objects.trigger import Trigger
from AoE2ScenarioParser.objects.data_objects.unit import Unit

from Localization import TEXT, UNIT_NAME
from TriggerAbstract import getUnitListName, getUnitsAbstract
from Util import IntListVar, IntValueButton, ListValueButton, MappedCombobox, PairValueEntry, ReCompiled, Tooltip, ValueSelectButton

if TYPE_CHECKING:
    from main import TCWindow

class UnitInfoView(ttk.Frame):
    @property
    def ul(self):
        return self.app.fUEditor.tvUnitList

    @property
    def um(self):
        return self.app.activeScenario.unit_manager

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.unitFocus: Unit = None

        #region Column 0
        """const, player, garrison"""
        lUConst = ttk.Label(self, text=TEXT['labelUnitConst'])
        lUConst.grid(column=0, row=0, sticky=EW, padx=self.app.dpi((10, 0)), pady=self.app.dpi((10, 0)))
        self.btnUConst = UnitConstSelectButton(self.app, self)
        self.btnUConst.set_internal_event(self.__modifyUnitConst)
        self.btnUConst.grid(column=0, row=1, sticky=EW, padx=self.app.dpi((10, 0)), pady=self.app.dpi((10, 0)))

        lUPlayer = ttk.Label(self, text=TEXT['labelUnitPlayer'])
        lUPlayer.grid(column=0, row=2, sticky=EW, padx=self.app.dpi((10, 0)), pady=self.app.dpi((10, 0)))
        self.varUPlayer = ttk.IntVar()
        self.cbUPlayer = MappedCombobox(self, {}, # Load later
                                        self.varUPlayer,
                                        state="readonly")
        self.cbUPlayer.set_display_event(self.__modifyUnitPlayer)
        self.cbUPlayer.bind("<<ComboboxSelected>>", lambda e: self.cbUPlayer.selection_clear())
        self.cbUPlayer.grid(column=0, row=3, sticky=EW, padx=self.app.dpi((10, 0)), pady=self.app.dpi((10, 0)))

        lUGarrison = ttk.Label(self, text=TEXT['labelUnitGarrison'])
        lUGarrison.grid(column=0, row=4, sticky=EW, padx=self.app.dpi((10, 0)), pady=self.app.dpi((10, 0)))
        self.btnUGarrison = UnitsSelectButton(self.app, self, multiple=False)
        self.btnUGarrison.set_internal_event(self.__modifyUnitGarrison)
        self.btnUGarrison.grid(column=0, row=5, sticky=EW, padx=self.app.dpi((10, 0)), pady=self.app.dpi((10, 0)))

        #endregion Column 0

        #region Column 1
        """x,y, z, rotation"""
        lULocation = ttk.Label(self, text=TEXT['labelUnitLocation'])
        lULocation.grid(column=1, row=0, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        fULocation = ttk.Frame(self)
        fULocation.grid(column=1, row=1, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        self.eUXLocation = self.__FloatAttributeEntry(self.app, fULocation, 'x', width=4)
        self.eUXLocation.pack(side=LEFT, fill=BOTH, expand=True)
        self.eUYLocation = self.__FloatAttributeEntry(self.app, fULocation, 'y', width=4)
        self.eUYLocation.pack(side=LEFT, fill=BOTH, expand=True)
        lUZLocation = ttk.Label(self, text=TEXT['labelUnitZLocation'])
        lUZLocation.grid(column=1, row=2, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        self.eUZLocation = self.__FloatAttributeEntry(self.app, self, 'z')
        self.eUZLocation.grid(column=1, row=3, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        lURotation = ttk.Label(self, text=TEXT['labelUnitRotation'])
        lURotation.grid(column=1, row=4, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        self.eURotation = self.__FloatAttributeEntry(self.app, self, 'rotation')
        self.eURotation.grid(column=1, row=5, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        # Todo:
        # self.eURotation = self.__RotationEntryCombobox(self.app, self)
        # self.eURotation.grid(column=1, row=5, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        #endregion Column 1

        #region Column 2
        """initial_animation_frame, status, reference_id"""
        lUFrame = ttk.Label(self, text=TEXT['labelUnitInitialFrame'])
        lUFrame.grid(column=2, row=0, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        self.eUInitFrame = self.__IntAttributeEntry(self.app, self, 'initial_animation_frame')
        self.eUInitFrame.grid(column=2, row=1, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        lUStatus = ttk.Label(self, text=TEXT['labelUnitStatus'])
        lUStatus.grid(column=2, row=2, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        self.eUStatus = self.__IntAttributeEntry(self.app, self, 'status')
        self.eUStatus.grid(column=2, row=3, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        lUReferenceId = ttk.Label(self, text=TEXT['labelUnitReferenceId'])
        lUReferenceId.grid(column=2, row=4, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        self.eURefId = self.__IntAttributeEntry(self.app, self, 'reference_id', state='disabled')
        self.eURefId.grid(column=2, row=5, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        #endregion Column 2

        #region Column 3
        """caption_string_id"""
        lUCaption = ttk.Label(self, text=TEXT['labelUnitCaptionStringID'])
        lUCaption.grid(column=3, row=0, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        self.eUCaption = self.__IntAttributeEntry(self.app, self, 'caption_string_id')
        self.eUCaption.grid(column=3, row=1, sticky=EW, padx=self.app.dpi((20, 0)), pady=self.app.dpi((10, 0)))
        #endregion Column 3

        self.grid_columnconfigure(0,weight=1)
        self.grid_columnconfigure(1,weight=1)
        self.grid_columnconfigure(2,weight=1)
        self.grid_columnconfigure(3,weight=1)
        self.grid_columnconfigure(4,minsize=self.app.dpi(10))

    class __IntAttributeEntry(PairValueEntry):
        def __init__(self, outer: 'TCWindow', master, attribute: str, **kwargs):
            self.outer = outer
            self.variable = ttk.StringVar()
            super().__init__(master, self.variable, **kwargs)
            self.set_display_event(lambda attr=attribute: self.modifyAttribute(attr))

        def modifyAttribute(self, attribute: str):
            try:
                floatValue = int(self.variable.get())
            except ValueError:
                floatValue = -1
            else:
                print(f'modifyAttribute {attribute} = {floatValue}')
                unit = self.outer.fUnitInfo.unitFocus
                if unit is not None:
                    setattr(unit, attribute, floatValue)

    class __FloatAttributeEntry(PairValueEntry):
        def __init__(self, outer: 'TCWindow', master, attribute: str, **kwargs):
            self.outer = outer
            self.variable = ttk.StringVar()
            super().__init__(master, self.variable, **kwargs)
            self.set_display_event(lambda attr=attribute: self.modifyAttribute(attr))

        def modifyAttribute(self, attribute: str):
            try:
                floatValue = float(self.variable.get())
            except ValueError:
                floatValue = -1
            else:
                print(f'modifyAttribute {attribute} = {floatValue}')
                unit = self.outer.fUnitInfo.unitFocus
                if unit is not None:
                    setattr(unit, attribute, floatValue)

    def __modifyUnitPlayer(self):
        if self.unitFocus is not None:
            self.unitFocus.player = self.varUPlayer.get()

    def __modifyUnitGarrison(self, garrison: int):
        if self.unitFocus is not None:
            self.unitFocus.garrisoned_in_id = garrison

    def __modifyUnitConst(self, value: int):
        print(f'modifyAttribute unit_const = {value}')
        if self.unitFocus is not None:
            self.unitFocus.unit_const = value
            for item in self.ul.get_children(""):
                if self.ul.getNodeId(item) == self.unitFocus.reference_id:
                    self.ul.setNodeConst(item, self.unitFocus.unit_const)


    def __modifyAttribute(self, attribute: str, value: int):
        floatValue = value
        print(f'modifyAttribute {attribute} = {floatValue}')
        if self.unitFocus is not None:
            setattr(self.unitFocus, attribute, floatValue)

    def unitSelected(self, unit: Unit):
        self.btnUConst.variable.set(unit.unit_const)
        self.varUPlayer.set(unit.player)
        self.btnUGarrison.variable.set([unit.garrisoned_in_id, ])
        self.eUXLocation.variable.set(unit.x)
        self.eUYLocation.variable.set(unit.y)
        self.eUZLocation.variable.set(unit.z)
        self.eURotation.variable.set(unit.rotation)
        self.eUInitFrame.variable.set(unit.initial_animation_frame)
        self.eUStatus.variable.set(unit.status)
        self.eURefId.variable.set(unit.reference_id)
        self.eUCaption.variable.set(unit.caption_string_id)

class UnitsSelectButton(ttk.Frame):
    def __init__(self, outer: 'TCWindow', master, multiple: bool,
                 **kwargs):
        super().__init__(master, **kwargs)
        encodeMethod = lambda unitListId: getUnitsAbstract(unitListId, 3)
        self._multiple = multiple
        self.outer = outer
        self.variable = IntListVar()
        self.lvbtn = ListValueButton(self, variable=self.variable, style='ceWidgetButton.Outline.TButton', width=16,
                                    encodeMethod=encodeMethod)
        self.lvbtn.pack(side=LEFT, fill=BOTH, expand=True)
        # self.lvbtn.set_command(self.__viewAttributeArea)
        self.lvbtn.set_internal_event(self.__modifyValue)
        self._internalSetEvent: Callable[[int], None] | Callable[[list[int]], None] = None
        self.btnSetUnit = ttk.Button(self, style='iconButton.Link.TButton', image=self.outer.imgCeSetLocationUnit,
                                    command=self.__setMultipleUnits if multiple else self.__setSingleUnits)
        self.btnSetUnit.pack(side=LEFT, padx=0)
        Tooltip(self.btnSetUnit, TEXT['tooltipSetLocationUnit'])

    def __setMultipleUnits(self) -> None:
        if self.outer.nTabsLeft.select() \
        and self.outer.nTabsLeft.index('current') == self.outer.nTabsLeft.index(self.outer.fUEditor):
            unitsId = self.outer.fUEditor.tvUnitList.getUnitsSelectionId()
            self.lvbtn.internal_var.set(unitsId)
        else:
            self.outer.nTabsLeft.select(self.outer.fUEditor)

    def __setSingleUnits(self) -> None:
        if self.outer.nTabsLeft.select() \
        and self.outer.nTabsLeft.index('current') == self.outer.nTabsLeft.index(self.outer.fUEditor):
                unitId = self.outer.fUEditor.tvUnitList.getUnitFocusId()
                if unitId == None:
                    unitId = -1
                self.lvbtn.internal_var.set([unitId, ])
        else:
            self.outer.nTabsLeft.select(self.outer.fUEditor)

    def __modifyValue(self):
        units = self.variable.get()
        if self._multiple == False:
            if len(units) == 0:
                units = -1
            else:
                units = units[0]
        if self._internalSetEvent is not None:
            self._internalSetEvent(units)

    def set_internal_event(self, event: Callable[[int], None] | Callable[[list[int]], None]) -> None:
        self._internalSetEvent = event

class UnitConstTreeView(ttk.Treeview):
    """
    A Treeview shows unit const list.

    Node text holds the unit const id, and values[0] holds the name.
    Give a filter to list unit consts.
    """
    unitConstMax = 2382

    def __init__(self, master=None, show=ttk.TREE, selectmode=BROWSE, columns=(0, 1), **kwargs):
        super().__init__(master, show=show, selectmode=selectmode, columns=columns, **kwargs)

    def insert(self, parent, index, ulId:int, **kwargs):
        return super().insert(parent, index, text=f'{ulId}',
                              values=(getUnitListName(ulId), ), **kwargs)

    def clear(self):
        for item in self.get_children():
            self.delete(item)

    def listUnit(self, filter: Callable[[int], bool] = None):
        self.clear()
        for id in range(-1, UnitConstTreeView.unitConstMax):
            if filter is not None and filter(id):
                self.insert("", END, id,)
        if len(self.get_children("")) == 1:
            first = self.get_children("")[0]
            self.focus(first)
            self.selection_set((first, ))

class UnitConstSelectButton(IntValueButton):
    def __init__(self, outer: 'TCWindow', master, allowNone=False,
                 **kwargs):
        encodeMethod = lambda unitConst: getUnitListName(unitConst)
        self.outer = outer
        self.variable = ttk.IntVar()
        self.allowNone = allowNone
        super().__init__(master, variable=self.variable,
                         style='ceWindowWidgetButton.success.Outline.TButton', width=20,
                         encodeMethod=encodeMethod)
        self.set_command(self.__openSelectWindow)
        super().set_internal_event(self.__modifyValue)
        self._internalSetEvent: Callable[[int], None] = None

    def __modifyValue(self):
        units = self.variable.get()
        if self._internalSetEvent is not None:
            self._internalSetEvent(units)

    def set_internal_event(self, event: Callable[[int], None]) -> None:
        self._internalSetEvent = event

    def __openSelectWindow(self):
        def _close_dialog(dialog: ttk.Toplevel):
            dialog.grab_release()
            dialog.destroy()

        def on_confirm():
            focus = tvUnitConst.focus()
            text = varFilter.get()
            if focus != '':
                id = int(tvUnitConst.item(focus)['text'])
                self.internal_var.set(id)
            elif text.isdigit():
                self.internal_var.set(int(text))
            _close_dialog(wndSelect)

        def on_tv_confirm(*args):
            focus = tvUnitConst.focus()
            if focus != '':
                id = int(tvUnitConst.item(focus)['text'])
                self.internal_var.set(id)
                _close_dialog(wndSelect)

        def on_entry_confirm(*args):
            focus = tvUnitConst.focus()
            text = varFilter.get()
            if focus != '':
                id = int(tvUnitConst.item(focus)['text'])
                self.internal_var.set(id)
            elif text.isdigit():
                self.internal_var.set(int(text))
            else:
                return
            _close_dialog(wndSelect)

        def listFilter(id) -> bool:
            if not self.allowNone and id < 0:
                return False
            text = varFilter.get()
            if text == '':
                return True
            elif text.isdigit():
                if int(text) == id:
                    return True
                else:
                    return False
            elif text.lower() in getUnitListName(id).lower():
                return True
            else:
                return False

        wndSelect = ttk.Toplevel(master=self.outer.main, title=TEXT['titleUnitConst'])
        self.outer.centerWindowGeometry(wndSelect, self.outer.dpi(400), self.outer.dpi(500))
        wndSelect.grab_set()
        wndSelect.protocol("WM_DELETE_WINDOW", lambda: _close_dialog(wndSelect))

        varFilter = ttk.StringVar()
        eFilter = ttk.Entry(wndSelect, textvariable=varFilter)
        eFilter.bind('<Return>', on_entry_confirm)
        eFilter.pack(padx=self.outer.dpi(10), pady=self.outer.dpi(5), fill=X)

        fUnitConst = ttk.Labelframe(wndSelect, text=TEXT['titleUnitConst'])
        tvUnitConst = UnitConstTreeView(fUnitConst, style='Borderless.Treeview')
        tvsbUnitConst = ttk.Scrollbar(fUnitConst, command=tvUnitConst.yview)
        tvUnitConst.configure(yscrollcommand=tvsbUnitConst.set)
        tvUnitConst.column('#0', width=self.outer.dpi(50), stretch=False)
        tvUnitConst.column('#2', width=self.outer.dpi(20), stretch=False)
        tvUnitConst.bind('<Double-1>', on_tv_confirm)
        tvUnitConst.bind('<Return>', on_tv_confirm)
        varFilter.trace_add('write', lambda *args: tvUnitConst.listUnit(listFilter))
        varFilter.set('')
        tvsbUnitConst.pack(side=RIGHT, fill=Y)
        tvUnitConst.pack(side=RIGHT, fill=BOTH, expand=YES)
        fUnitConst.pack(fill=BOTH, expand=YES, padx=self.outer.dpi(10))

        fConfirmCancel = ttk.Frame(wndSelect)
        ttk.Button(fConfirmCancel, text=TEXT['btnConfirm'], command=on_confirm) \
            .pack(side=LEFT, fill=X, expand=YES, padx=self.outer.dpi(10))
        ttk.Button(fConfirmCancel, text=TEXT['btnCancel'], bootstyle=ttk.SECONDARY, command=lambda: _close_dialog(wndSelect)) \
            .pack(side=LEFT, fill=X, expand=YES, padx=self.outer.dpi(10))
        fConfirmCancel.pack(side=BOTTOM, fill=X, pady=self.outer.dpi(10))

        wndSelect.transient(self)
        eFilter.focus()

