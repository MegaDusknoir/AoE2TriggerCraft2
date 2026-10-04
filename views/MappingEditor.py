from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Literal
from math import pi as PI
from tkinter.constants import *
import ttkbootstrap as ttk

from Localization import TEXT
from TriggerAbstract import *
from Util import IntListVar, ListValueButton, Tooltip

if TYPE_CHECKING:
    from main import TCWindow

class MappingTreeView(ttk.Treeview):
    def __init__(self, master=None, show=ttk.TREE, selectmode=BROWSE, columns=(), **kwargs):
        super().__init__(master, show=show, selectmode=selectmode, columns=columns, **kwargs)

    def insert(self, index: int | Literal['end'], text: str, id: int, **kwargs):
        return super().insert("", index, text=text, values=(str(id), ), **kwargs)

    def move(self, item: str | int, index: int | Literal['end']):
        return super().move(item, "", index)

    def getNodeId(self, item:str) -> int:
        id = self.item(item)['values'][0]
        return int(id)

    def setNodeId(self, item:str, id: int):
        self.item(item, values=(str(id), ))

class MappingEditor(ttk.Frame):
    @property
    def ml(self):
        return self.tvMappingList

    @property
    def mappingsRef(self):
        if self.mappingType == 'unit':
            return self.app.scenOptions.unitDuplicateMappings
        elif self.mappingType == 'tile':
            return self.app.scenOptions.tileDuplicateMappings
        elif self.mappingType == 'area':
            return self.app.scenOptions.areaDuplicateMappings

    def loadConfig(self):
        self.loadMappingList()
        self.varMappingName.set('')
        for btn in self.btnValues:
            btn.clear()

    def newMapping(self):
        newId = len(self.mappingsRef)
        if self.mappingType == 'unit':
            self.mappingsRef.append({"name": TEXT['formatNewMappingName'].format(newId), "mapping": [-1] * 9})
        elif self.mappingType == 'tile':
            self.mappingsRef.append({"name": TEXT['formatNewMappingName'].format(newId), "mapping": [[-1, -1],] * 9})
        elif self.mappingType == 'area':
            self.mappingsRef.append({"name": TEXT['formatNewMappingName'].format(newId), "mapping": [[-1, -1, -1, -1],] * 9})
        newItem = self.ml.insert(END, id=newId, text=self.mappingsRef[-1]["name"])
        self.ml.focus(newItem)
        self.ml.selection_set(newItem)

    def delMapping(self):
        curItem = self.ml.focus()
        if not curItem:
            return
        idToDel = self.ml.getNodeId(curItem)
        nextSelection = self.ml.next(curItem)
        if nextSelection == '':
            nextSelection = self.ml.prev(curItem)
        for child in self.ml.get_children(''):
            id = self.ml.getNodeId(child)
            if id > idToDel:
                id -= 1
                self.ml.setNodeId(child, id)
        self.ml.delete(curItem)
        del self.mappingsRef[idToDel]
        if nextSelection != '':
            self.ml.focus(nextSelection)
            self.ml.selection_set(nextSelection)

    def moveUpMapping(self):
        curItem = self.ml.focus()
        if not curItem:
            return
        prev = self.ml.prev(curItem)
        if prev == '':
            return
        id = self.ml.getNodeId(curItem)
        prevId = self.ml.getNodeId(prev)
        self.ml.move(curItem, self.ml.index(prev))
        id, prevId = prevId, id
        self.ml.setNodeId(curItem, id)
        self.ml.setNodeId(prev, prevId)
        self.mappingsRef[prevId], self.mappingsRef[id] = self.mappingsRef[id], self.mappingsRef[prevId]
        if not self.ml.bbox(curItem):
            self.ml.see(curItem)

    def moveDownMapping(self):
        curItem = self.ml.focus()
        if not curItem:
            return
        next = self.ml.next(curItem)
        if next == '':
            return
        id = self.ml.getNodeId(curItem)
        nextId = self.ml.getNodeId(next)
        self.ml.move(curItem, self.ml.index(next))
        id, nextId = nextId, id
        self.ml.setNodeId(curItem, id)
        self.ml.setNodeId(next, nextId)
        self.mappingsRef[nextId], self.mappingsRef[id] = self.mappingsRef[id], self.mappingsRef[nextId]
        if not self.ml.bbox(curItem):
            self.ml.see(curItem)

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        #region Head
        fHead = ttk.Frame(self)
        fHead.pack(side=TOP, fill=X, expand=NO)
        fRbGroup = ttk.Frame(fHead)
        fRbGroup.pack(side=LEFT, anchor=W, padx=self.app.dpi((10,10)), pady=self.app.dpi((10,0)))
        self.varRbMapping = ttk.StringVar()
        self.mappingType = ''
        for i, item in enumerate(['unit', 'tile', 'area']):
            rbMapping = ttk.Radiobutton(fRbGroup, text=TEXT[f'label{item.capitalize()}Mapping'],
                                        variable=self.varRbMapping, value=item)
            rbMapping.pack(side=LEFT, padx=self.app.dpi((0,10)))
        fLoadSave = ttk.Frame(fHead)
        ttk.Button(fLoadSave, text=TEXT['btnLoad'], bootstyle=ttk.OUTLINE, command=self.app.loadDuplicateMappings) \
            .pack(side=LEFT, fill=X, expand=YES, padx=self.app.dpi((0,8)), pady=self.app.dpi((6,0)))
        ttk.Button(fLoadSave, text=TEXT['btnSaveAs'], bootstyle=ttk.OUTLINE, command=self.app.saveDuplicateMappings) \
            .pack(side=LEFT, fill=X, expand=YES, pady=self.app.dpi((6,0)))
        fLoadSave.pack(side=RIGHT, anchor=E, padx=self.app.dpi((10,10)))
        #endregion

        #region Left
        ttk.Separator(self, orient=HORIZONTAL).pack(side=TOP, fill=X, padx=self.app.dpi(6), pady=self.app.dpi(8))
        fBottom = ttk.Frame(self)
        fBottom.pack(side=TOP, fill=BOTH, expand=YES, padx=self.app.dpi((10,10)), pady=self.app.dpi((0,10)))
        fBottomLeft = ttk.Frame(fBottom)
        fBottomLeft.pack(side=LEFT, fill=Y, padx=self.app.dpi((0,10)))
        lfMappingList = ttk.Labelframe(fBottomLeft, text=TEXT['labelMappingList'])
        lfMappingList.pack(side=TOP, fill=Y, expand=YES)
        self.tvMappingList = MappingTreeView(lfMappingList, style='Borderless.Treeview')
        self.tvMappingList.bind('<<TreeviewSelect>>', lambda e: self.mappingSelect())
        self.tvMappingList.column('#0', width=self.app.dpi(160))
        tvsbMappingList = ttk.Scrollbar(lfMappingList, command=self.tvMappingList.yview)
        tvsbMappingList.pack(side=RIGHT, fill=Y)
        self.tvMappingList.pack(side=RIGHT, fill=Y, expand=YES)
        fPanel = ttk.Frame(fBottomLeft)
        fPanel.pack(side=TOP, fill=X)
        btnAdd = ttk.Button(fPanel, style='iconButton.Link.TButton', image=self.app.imgBtnAdd, command=self.newMapping)
        btnAdd.pack(side=LEFT)
        btnDelete = ttk.Button(fPanel, style='iconButton.Link.TButton', image=self.app.imgBtnIDelete, command=self.delMapping)
        btnDelete.pack(side=LEFT)
        btnMoveDown = ttk.Button(fPanel, style='iconButton.Link.TButton', image=self.app.imgBtnIMoveDown, command=self.moveDownMapping)
        btnMoveDown.pack(side=RIGHT)
        btnMoveUp = ttk.Button(fPanel, style='iconButton.Link.TButton', image=self.app.imgBtnIMoveUp, command=self.moveUpMapping)
        btnMoveUp.pack(side=RIGHT)
        #endregion

        #region Right
        lfMappingContent = ttk.Frame(fBottom)
        lfMappingContent.pack(side=LEFT, fill=BOTH, expand=YES, padx=self.app.dpi((10,0)))
        ttk.Label(lfMappingContent, text=TEXT['labelMappingName']).pack(side=TOP, anchor=W)
        self.varMappingName = ttk.StringVar()
        self.varMappingName.trace_add('write', lambda *args: self.__changeMappingName())
        ttk.Entry(lfMappingContent, width=40, textvariable=self.varMappingName).pack(side=TOP, anchor=W, pady=self.app.dpi((10,10)))
        lValues = ttk.Labelframe(lfMappingContent, text=TEXT['labelMappingValue'])
        lValues.pack(side=TOP, anchor=W, fill=BOTH, expand=YES)
        self.btnValues: list[MappingEditor.MappingValueButton] = []
        for i in range(0,8):
            lPlayer = ttk.Label(lValues, text=getPlayerAbstract(i+1))
            lPlayer.grid(row=i % 4, column=i // 4 * 2, padx=self.app.dpi((6,4)), pady=self.app.dpi(6))
            btnValue = self.MappingValueButton(self.app, lValues, player=i+1,
                                               style='ceWidgetButton.Outline.TButton', width=16)
            btnValue.grid(row=i % 4, column=i // 4 * 2 + 1, sticky=EW,
                          padx=self.app.dpi((0,20)), pady=self.app.dpi(6))
            self.btnValues.append(btnValue)
        self.varRbMapping.trace_add('write', lambda *args: self.__selectType())
        self.varRbMapping.set('unit')
        #endregion

    def mappingSelect(self):
        curItem = self.ml.focus()
        if not curItem:
            self.varMappingName.set('')
            for i, btn in enumerate(self.btnValues):
                btn.clear()
            return
        mappingId = self.ml.getNodeId(curItem)
        mapping = self.mappingsRef[mappingId]
        self.varMappingName.set(mapping["name"])
        for i, btn in enumerate(self.btnValues):
            btn.load(mapping["mapping"][i+1])

    def loadMappingList(self):
        for item in self.ml.get_children():
            self.ml.delete(item)
        for i, mapping in enumerate(self.mappingsRef):
            self.ml.insert(END, id=i, text=mapping["name"])

    def __selectType(self):
        mappingType = self.varRbMapping.get()
        if self.mappingType == mappingType:
            return
        self.mappingType = mappingType
        self.loadMappingList()
        self.varMappingName.set('')
        for btn in self.btnValues:
            btn.setType(mappingType)

    def __changeMappingName(self):
        curItem = self.ml.focus()
        if not curItem:
            return
        id = self.ml.getNodeId(curItem)
        self.mappingsRef[id]["name"] = self.varMappingName.get()
        self.ml.item(curItem, text=self.varMappingName.get())

    class MappingValueButton(ttk.Frame):
        @property
        def ml(self):
            return self.outer.fMappingEditor.tvMappingList

        def __init__(self, outer: 'TCWindow', master, player: int,
                     **kwargs):
            super().__init__(master, **kwargs)
            self.mappingType: Literal['unit', 'tile', 'area'] = ''
            self.outer = outer
            self.variable = IntListVar()
            self.player = player
            self.lvbtn = ListValueButton(self, variable=self.variable, style='ceWidgetButton.Outline.TButton', width=16,
                                         encodeMethod=lambda pointList: self.__encodeMethod(pointList))
            self.lvbtn.pack(side=LEFT, fill=BOTH, expand=True)
            self.btnSetUnit = ttk.Button(self, style='iconButton.Link.TButton', image=self.outer.imgCeSetLocationUnit,
                                        command=self.__setUnit)
            Tooltip(self.btnSetUnit, TEXT['tooltipSetLocationUnit'])
            self.btnSetArea = ttk.Button(self, style='iconButton.Link.TButton', image=self.outer.imgCeSetArea,
                                        command=self.__setArea)
            Tooltip(self.btnSetArea, TEXT['tooltipSetLocationArea'])

        def load(self, value: list | int):
            if isinstance(value, int):
                value = [value,]
            self.variable.set(value)

        def clear(self):
            if self.mappingType == 'unit':
                self.variable.set([-1,])
            elif self.mappingType == 'tile':
                self.variable.set([-1,-1])
            elif self.mappingType == 'area':
                self.variable.set([-1,-1,-1,-1])

        def __encodeMethod(self, pointList):
            if self.mappingType == 'unit':
                return getUnitAbstract(pointList[0])
            elif self.mappingType == 'tile':
                return getLocationAbstract(pointList[0],pointList[1])
            elif self.mappingType == 'area':
                return getAreaAbstract(pointList[0],pointList[1],pointList[2],pointList[3])

        def setType(self, mappingType: Literal['unit', 'tile', 'area']):
            if self.mappingType != mappingType:
                self.mappingType = mappingType
                self.clear()
            if self.mappingType == 'unit':
                self.btnSetUnit.pack(side=LEFT, padx=0)
                self.btnSetArea.pack_forget()
                self.lvbtn.set_command(self.__viewUnits)
                self.lvbtn.set_internal_event(self.__modifyUnit)
            else:
                self.btnSetUnit.pack_forget()
                self.btnSetArea.pack(side=LEFT, padx=0)
                self.lvbtn.set_command(self.__viewArea)
                self.lvbtn.set_internal_event(self.__modifyArea)

        def __viewArea(self):
            coords = self.variable.get()
            if len(coords) != 0:
                if self.mappingType == 'area':
                    x1, y1, x2, y2 = coords
                    if (x1, y1) == (-1, -1):
                        self.outer.fMapViewTab.drawClear()
                    else:
                        self.outer.fMapViewTab.drawSetPoint1((x1, y1), draw=False)
                        self.outer.fMapViewTab.drawSetPoint2((x2, y2), see=True)
                elif self.mappingType == 'tile':
                    x1, y1 = coords
                    if (x1, y1) != (-1, -1):
                        self.outer.fMapViewTab.drawSetPoint1((x1, y1), see=True)
                    else:
                        self.outer.fMapViewTab.drawClear()

        def __viewUnits(self):
            units = self.variable.get()
            if units != [] and units[0] != -1:
                self.outer.nTabsLeft.select(self.outer.fUEditor)
                self.outer.fUEditor.unitIdFilter(units)

        def __setArea(self) -> None:
            x1, y1, x2, y2 = self.outer.fMapViewTab.pointSelect.get()
            if self.mappingType == 'area':
                if (x2, y2) == (-1, -1):
                    x2, y2 = x1, y1
                if x1 > x2:
                    x1, x2 = x2, x1
                if y1 > y2:
                    y1, y2 = y2, y1
                self.lvbtn.internal_var.set([x1, y1, x2, y2])
            elif self.mappingType == 'tile':
                location = [x1, y1]
                self.lvbtn.internal_var.set(location)

        def __setUnit(self) -> None:
            if self.outer.nTabsLeft.select() \
            and self.outer.nTabsLeft.index('current') == self.outer.nTabsLeft.index(self.outer.fUEditor):
                    unitId = self.outer.fUEditor.tvUnitList.getUnitFocusRefId()
                    if unitId == None:
                        unitId = -1
                    self.lvbtn.internal_var.set([unitId, ])
            else:
                self.outer.nTabsLeft.select(self.outer.fUEditor)

        def __modifyArea(self) -> None:
            curItem = self.ml.focus()
            if not curItem:
                return
            id = self.ml.getNodeId(curItem)
            if self.mappingType == 'area':
                self.outer.scenOptions.areaDuplicateMappings[id]["mapping"][self.player] = self.variable.get()
            elif self.mappingType == 'tile':
                self.outer.scenOptions.tileDuplicateMappings[id]["mapping"][self.player] = self.variable.get()

        def __modifyUnit(self):
            curItem = self.ml.focus()
            if not curItem:
                return
            id = self.ml.getNodeId(curItem)
            self.outer.scenOptions.unitDuplicateMappings[id]["mapping"][self.player] = self.variable.get()[0]
