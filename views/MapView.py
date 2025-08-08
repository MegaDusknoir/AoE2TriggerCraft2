from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from math import sqrt
from tkinter.constants import *
import ttkbootstrap as ttk

import PIL.Image
import PIL.ImageDraw
import PIL.ImageTk
from PIL.Image import Resampling
from PIL import ImageColor

from AoE2ScenarioParser.objects.managers.map_manager import MapManager
from Localization import TEXT, UNIT_NAME
from TerrainPal import TERRAIN_PAL
from CommonPalette import AOE_PAL
from TriggerAbstract import getAreaAbstract
from Util import IntListVar, PairValueEntry, ZoomImageViewer, fastAoERotate

if TYPE_CHECKING:
    from main import TCWindow

SQRT_8 = sqrt(8)
class MapView(ttk.Frame):
    @property
    def mm(self):
        return self.app.activeScenario.map_manager

    @property
    def um(self):
        return self.app.activeScenario.unit_manager

    UNIT_DOT_PAL = [
        (255, 255, 255),
        (0, 0, 255),
        (255, 0, 0),
        (0, 255, 0),
        (255, 255, 0),
        (0, 255, 255),
        (255, 0, 255),
        (64, 64, 64),
        (255, 128, 0),
    ]

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        # [x1,y1,x2,y2]
        self.pointSelect = IntListVar(value=[-1,]*4)

        self.zvMapView = ZoomImageViewer(self,
                                        PIL.Image.new('RGB', (1,1)), bg="black",
                                        transform=self.__rotateMap)
        self.zvMapView.pack(side=LEFT, fill=BOTH, expand=YES, anchor=CENTER)
        self.zvMapView.bind('<ButtonRelease-1>', lambda e: \
                            self.drawSetPoint1(
                                self.__mapViewCoordinateConv(self.zvMapView.coords_conv(e.x,e.y))
                                ))
        self.zvMapView.bind('<Shift-ButtonRelease-1>', lambda e: \
                            self.drawSetPoint2(
                                self.__mapViewCoordinateConv(self.zvMapView.coords_conv(e.x,e.y))
                                ))
        self.zvMapView.bind('<Button-3>', lambda e: \
                            self.drawClear())
        self.zvMapView.bind('<Enter>', lambda e: self.app.statusBarMessage(TEXT['tooltipMapView'], layer='top'))
        self.zvMapView.bind('<Leave>', lambda e: self.app.statusBarMessage('', layer='top'))

        cfPanel = CollapsibleFrame(self.app, self, ipadx=self.app.dpi(10))
        cfPanel.pack(side=RIGHT,fill=Y)
        fPanel = cfPanel.frame

        # Panel
        """point1, point2, realArea"""
        lPoint1 = ttk.Label(fPanel, text=TEXT['labelPoint1'])
        lPoint1.grid(column=0, row=0, sticky=EW)
        self.fPoint1 = self.CoordEntryPair(self.app, fPanel)
        self.fPoint1.grid(column=0, row=1, sticky=EW)
        self.fPoint1.set_display_event(lambda x,y: self.__eventEntryCoord(x,y,point=0))
        lPoint2 = ttk.Label(fPanel, text=TEXT['labelPoint2'])
        lPoint2.grid(column=0, row=2, sticky=EW)
        self.fPoint2 = self.CoordEntryPair(self.app, fPanel)
        self.fPoint2.grid(column=0, row=3, sticky=EW)
        self.fPoint2.set_display_event(lambda x,y: self.__eventEntryCoord(x,y,point=1))
        lAreaValue = ttk.Label(fPanel, text=TEXT['labelRealArea'])
        lAreaValue.grid(column=0, row=4, sticky=EW)
        self.varAreaValue = ttk.StringVar()
        eAreaValue = ttk.Label(fPanel, textvariable=self.varAreaValue, justify='center', anchor=CENTER)
        eAreaValue.grid(column=0, row=5, sticky=EW)
        fPanel.grid_columnconfigure(0, pad=self.app.dpi(10))
        fPanel.grid_columnconfigure(1, pad=self.app.dpi(10))
        fPanel.grid_rowconfigure(list(range(6)), pad=self.app.dpi(10))

        self._updatingCoords = False
        self.pointSelect.trace_add('write', lambda *args: self.modifyPoint())

        # The bottom layer shows terrain
        self.imgDotMapRaw: PIL.Image.Image = None

        # The top layer shows units
        self.imgUnitsDotLayer: PIL.Image.Image = None

        self.sizeMap: int = None
        self.background = self.app.style.colors.bg

    def modifyPoint(self):
        if not self._updatingCoords:
            x1, y1, x2, y2 = self.pointSelect.get()
            self.fPoint1.eX.variable.set(x1)
            self.fPoint1.eY.variable.set(y1)
            self.fPoint2.eX.variable.set(x2)
            self.fPoint2.eY.variable.set(y2)
        self.varAreaValue.set(getAreaAbstract(*self.getArea()))

    def areaCoordNormalize(self, area: list[int]):
        if -1 in area[:2]:
            area[:2] = [-1,-1]
        else:
            area[:2] = self.__mapLocationFix(area[:2])
        if -1 in area[2:]:
            area[2:] = [-1,-1]
        else:
            area[2:] = self.__mapLocationFix(area[2:])

    def updateAreaLayerLater(self):
        def __updateAreaLayer():
            del self._areaLayerUpdate
            self._updatingCoords = True
            self.drawArea()
            self._updatingCoords = False

        if not hasattr(self, '_areaLayerUpdate'):
            self._areaLayerUpdate = self.after(120, __updateAreaLayer)
        else:
            self.after_cancel(self._areaLayerUpdate)
            self._areaLayerUpdate = self.after(120, __updateAreaLayer)

    def __eventEntryCoord(self, x, y, point):
        coords = self.pointSelect.get()
        coords[point*2: point*2+2] = [x, y]
        self.areaCoordNormalize(coords)
        self._updatingCoords = True
        self.pointSelect.set(coords)
        self._updatingCoords = False
        self.updateAreaLayerLater()

    class CoordEntryPair(ttk.Frame):
        def __init__(self, outer: 'TCWindow', master,
                    **kwargs):
            super().__init__(master, **kwargs)
            self.varX = ttk.StringVar()
            self.eX = PairValueEntry(self, self.varX, width=6)
            self.eX.pack(side=LEFT, fill=BOTH, expand=True)
            self.eX.set_display_event(self.display_event)
            self.varY = ttk.StringVar()
            self.eY = PairValueEntry(self, self.varY, width=6)
            self.eY.pack(side=LEFT, fill=BOTH, expand=True)
            self.eY.set_display_event(self.display_event)
            self._display_event = None
            self.eX.bind('<MouseWheel>', lambda e:self.__wheelHandler(self.eX, e.delta))
            self.eY.bind('<MouseWheel>', lambda e:self.__wheelHandler(self.eY, e.delta))

        def __wheelHandler(self, entry: PairValueEntry, direction, multiplying=1):
            try:
                intValue = int(entry.display_var.get())
            except ValueError:
                pass
            else:
                if direction > 0:
                    dst = intValue + multiplying
                else:
                    dst = intValue - multiplying
                entry.display_var.set(str(dst))

        def set_display_event(self, event):
            self._display_event = event

        def display_event(self):
            try:
                x, y = int(self.varX.get()), int(self.varY.get())
            except ValueError:
                pass
            else:
                if self._display_event:
                    self._display_event(x, y)

    def loadMapView(self):
        self.sizeMap = self.mm.map_width
        self.imgDotMapRaw = PIL.Image.new('RGB', (self.sizeMap,self.sizeMap))
        for y in range(0, self.mm.map_height):
            for x in range(0, self.mm.map_width):
                tile = self.mm.get_tile(x, y)
                self.imgDotMapRaw.putpixel((x,y), TERRAIN_PAL[tile.terrain_id][tile.elevation])
        self.loadUnitLayer()
        self.__redrawMap()
        self.zvMapView.see(*self.__inverseMapViewCoordinateConv((self.sizeMap // 2, self.sizeMap // 2)))

    def loadUnitLayer(self):
        self.imgUnitsDotLayer = PIL.Image.new('RGBA', (self.sizeMap * 2 + 1, self.sizeMap * 2 + 1), (0,0,0,0))
        for unit in self.um.get_all_units():
            if UNIT_NAME[unit.unit_const]['minimap_mode'] in [1, 4]:
                if 0 <= unit.x < self.sizeMap and 0 <= unit.y < self.sizeMap:
                    x = int(unit.x * 2 + 0.5)
                    y = int(unit.y * 2 + 0.5)
                    if UNIT_NAME[unit.unit_const]['minimap_color'] == 0:
                        color = (*MapView.UNIT_DOT_PAL[unit.player], 255)
                    else:
                        color = (*ImageColor.getcolor(
                            AOE_PAL[UNIT_NAME[unit.unit_const]['minimap_color']],
                            "RGB"), 255)
                    self.imgUnitsDotLayer.putpixel((x,y), color)

    def updateUnitLayer(self):
        def __updateUnitLayer():
            del self._unitLayerUpdate
            self.zvMapView.set_image(self.zvMapView.original_image)

        if not hasattr(self, '_unitLayerUpdate'):
            self._unitLayerUpdate = self.after(200, __updateUnitLayer)

    def updateUnitLayerDot(self, ux: float, uy: float):
        if not (0 <= ux < self.sizeMap and 0 <= uy < self.sizeMap):
            return
        dot_x = int(ux * 2 + 0.5)
        dot_y = int(uy * 2 + 0.5)
        self.imgUnitsDotLayer.putpixel((dot_x,dot_y), (0,0,0,0))
        for unit in self.um.get_all_units():
            if UNIT_NAME[unit.unit_const]['minimap_mode'] in [1, 4]:
                if 0 <= unit.x < self.sizeMap and 0 <= unit.y < self.sizeMap:
                    if int(unit.x * 2 + 0.5) == dot_x and int(unit.y * 2 + 0.5) == dot_y:
                        if UNIT_NAME[unit.unit_const]['minimap_color'] == 0:
                            color = (*MapView.UNIT_DOT_PAL[unit.player], 255)
                        else:
                            color = (*ImageColor.getcolor(
                                AOE_PAL[UNIT_NAME[unit.unit_const]['minimap_color']],
                                "RGB"), 255)
                        self.imgUnitsDotLayer.putpixel((dot_x,dot_y), color)
        self.updateUnitLayer()

    def __mapViewCoordinateConv(self, rhombus_xy: tuple[int, int]) -> tuple[int, int]:
        """Transpose the rhombus view coords to map coords"""
        rx, ry = rhombus_xy[0], rhombus_xy[1]
        x, y = ((rx - 2 * (ry - self.sizeMap / SQRT_8) ) / 4,
                (rx + 2 * (ry - self.sizeMap / SQRT_8) ) / 4)
        x = round(x * SQRT_8 - 0.5)
        y = round(y * SQRT_8 - 0.5)
        return (x,y)

    def __inverseMapViewCoordinateConv(self, map_xy: tuple[int, int]) -> tuple[float, float]:
        """Transpose the map coords to rhombus view coords"""
        mx, my = map_xy

        x = (mx + 0.5) / SQRT_8
        y = (my + 0.5) / SQRT_8

        rx = 2 * x + 2 * y
        ry = self.sizeMap / SQRT_8 + y - x
        return (rx, ry)

    def __mapLocationFix(self, xy: tuple[int, int]) -> tuple[int, int]:
        """Force location inside the map"""
        fixed = [0, 0]
        for i, d in enumerate(xy):
            if d < 0:
                d = 0
            if d >= self.sizeMap:
                d = self.sizeMap - 1
            fixed[i] = d
        return tuple(fixed)

    def __rotateMap(self, image:PIL.Image.Image, zoom: float) -> PIL.Image.Image:
        """Transform a dot map to zoomed rhombus view"""
        image = image.resize((image.width * 4,)*2, resample=Resampling.NEAREST)
        unitLayer = self.imgUnitsDotLayer.resize((self.imgUnitsDotLayer.width * 2,)*2,
                                                  resample=Resampling.NEAREST)
        image.paste(unitLayer, (-int(1),)*2, unitLayer)
        image = fastAoERotate(image, zoom / 4, fillcolor=self.background)
        return image

    def __redrawMap(self):
        self.pointSelect.set([-1,]*4)
        imgDotBase = self.imgDotMapRaw.copy()
        self.zvMapView.set_image(imgDotBase)

    def drawClear(self) -> None:
        self.__redrawMap()

    def drawSetPoint1(self, xy: tuple[int, int], see = False, draw=True) -> None:
        xy = self.__mapLocationFix(xy)
        self.pointSelect.set([*xy, -1, -1])
        if draw:
            self.drawArea(see)

    def drawSetPoint2(self, xy: tuple[int, int], see = False) -> None:
        xy = self.__mapLocationFix(xy)
        coords = self.pointSelect.get()
        if -1 in coords[:2]:
            self.drawSetPoint1(xy, see)
            return
        coords[2:] = xy
        self.pointSelect.set(coords)
        self.drawArea(see)

    def drawArea(self, see = False) -> None:
        coords = self.pointSelect.get()
        if -1 in coords[:2] and -1 in coords[2:]:
            self.drawClear()
        else:
            if -1 in coords[:2]:
                x1, y1 = x2, y2 = coords[2:]
            elif -1 in coords[2:]:
                x1, y1 = x2, y2 = coords[:2]
            else:
                x1, y1, x2, y2 = self.getArea()
            imgDotBase = self.imgDotMapRaw.copy()
            imgDotMask = PIL.Image.new('RGBA', (self.sizeMap,self.sizeMap), (0,0,0,0))
            imageDraw = PIL.ImageDraw.Draw(imgDotMask)
            imageDraw.rectangle((x1, y1, x2, y2), (255, 255, 0, 176))
            imgDotBase.paste(imgDotMask, mask=imgDotMask)
            self.zvMapView.set_image(imgDotBase)
            if see:
                self.zvMapView.see(*self.__inverseMapViewCoordinateConv(((x1 + x2) / 2, (y1 + y2) / 2)))

    def getArea(self) -> tuple[int, int, int, int]:
        """Return (x1, y1, x2, y2), making sure x1 <= x2, y1 <= y2"""
        x1, y1, x2, y2 = self.pointSelect.get()
        if -1 in (x2, y2):
            x2, y2 = x1, y1
        elif -1 in (x1, y1):
            x1, y1 = x2, y2
        else:
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1
        return (x1, y1, x2, y2)

class CollapsibleFrame(ttk.Frame):
    def __init__(self, app: TCWindow, master = None, ipadx=0, ipady=0, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        self.ipadx = ipadx
        self.ipady = ipady

        self.frame_status = False
        self.frame = ttk.Frame(self)

        ttk.Separator(self, orient='vertical').pack(side=LEFT, fill=Y)

        self.btnToggle = ttk.Button(self, style='sideBarExpand.secondary.TButton', command=self.toggle_frame)
        self.btnToggle.pack(side=LEFT, fill=Y)
        self.set_frame(False)

    def toggle_frame(self):
        self.set_frame(not self.frame_status)

    def set_frame(self, show=True):
        if not show:
            self.frame.pack_forget()
            self.frame_status = False
            self.btnToggle.config(text="◀")
        else:
            self.frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=self.ipadx, pady=self.ipady)
            self.frame_status = True
            self.btnToggle.config(text="▶")