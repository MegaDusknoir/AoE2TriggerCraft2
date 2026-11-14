from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from tkinter.constants import *
import ttkbootstrap as ttk

from Localization import TERRAIN_NAME, TEXT
from Util import Tooltip

if TYPE_CHECKING:
    from main import TCWindow

# class TerrainTypeTreeView(ttk.Treeview):
#     pass

class TerrainPanel(ttk.Frame):
    TOOL_SELECT = "select"
    TOOL_PENCIL = "pencil"
    TOOL_BUCKET = "bucket"
    TOOL_ELEVATION = "elevation"
    TOOL_RECTANGLE = "rectangle"
    TOOL_REPLACE = "replace"

    @property
    def mm(self):
        return self.app.mm

    @property
    def active_tool(self) -> str:
        return self.varTool.get()

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        self.fToolbar = ttk.Frame(self)
        self.fToolbar.pack(fill=X, expand=NO, padx=self.app.dpi((10, 5)), pady=self.app.dpi((5, 0)))
        self.varTool = ttk.StringVar(value=self.TOOL_SELECT)
        for tool, label, icon in (
            (self.TOOL_SELECT, "terrainToolSelect", self.app.imgToolSelect),
            (self.TOOL_PENCIL, "terrainToolPencil", self.app.imgToolPencil),
            # (self.TOOL_BUCKET, "terrainToolBucket", self.app.imgToolBucket),
            # (self.TOOL_ELEVATION, "terrainToolElevation", self.app.imgToolElevation),
            # (self.TOOL_RECTANGLE, "terrainToolRectangle", self.app.imgToolRectangle),
            # (self.TOOL_REPLACE, "terrainToolreplace", self.app.imgToolReplace),
        ):
            button = ttk.Radiobutton(
                self.fToolbar, text='', variable=self.varTool, value=tool,
                image=icon,
                style="toolbarButton.Toolbutton",
                command=self.__onToolChanged,
            )
            button.pack(side=LEFT, padx=self.app.dpi((0,2)))
            Tooltip(button, TEXT[label])
        ttk.Separator(self, orient=HORIZONTAL).pack(fill=X, padx=self.app.dpi((10, 5)), pady=self.app.dpi((5, 5)))
        lfTrList = ttk.LabelFrame(self, text=TEXT['labelTerrainList'])
        lfTrList.pack(side=TOP, fill=BOTH, expand=YES, padx=self.app.dpi((10, 5)), pady=self.app.dpi((0, 5)))
        self.tvTerrain = ttk.Treeview(lfTrList, style='Borderless.Treeview', show=ttk.TREE, selectmode=BROWSE, columns=(0))
        self.tvTerrain.insert('', END, text=str(-1), values=(TEXT['comboValueNone']))
        for tId, terrain in TERRAIN_NAME.items():
            self.tvTerrain.insert('', END, text=f'{tId}', values=(terrain,))
        tvsbTerrain = ttk.Scrollbar(lfTrList, command=self.tvTerrain.yview)
        self.tvTerrain.configure(yscrollcommand=tvsbTerrain.set)
        self.tvTerrain.column('#0', width=self.app.dpi(40), stretch=False)
        self.tvTerrain.column('#1', width=self.app.dpi(100))
        tvsbTerrain.pack(side=RIGHT, fill=Y)
        self.tvTerrain.pack(side=RIGHT, fill=BOTH, expand=YES)

    def __onToolChanged(self) -> None:
        self.app.fMapViewTab.setTerrainTool(self.active_tool)

    def getTerrainSelection(self) -> int:
        sel = self.tvTerrain.focus()
        if sel:
            return int(self.tvTerrain.item(sel)['text'])
        else:
            return -1