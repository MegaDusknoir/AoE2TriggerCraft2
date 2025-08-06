from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from math import sqrt
from tkinter.constants import *
import ttkbootstrap as ttk

import PIL.Image
import PIL.ImageDraw
import PIL.ImageTk
from PIL.Image import Resampling

from AoE2ScenarioParser.objects.managers.map_manager import MapManager
from Localization import TEXT, UNIT_NAME
from TerrainPal import TERRAIN_PAL
from Util import ZoomImageViewer, fastAoERotate

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

        self.pointSelect = [(-1, -1), (-1, -1)]
        self.zvMapView = ZoomImageViewer(self,
                                        PIL.Image.new('RGB', (1,1)), bg="black",
                                        transform=self.__rotateMap)
        self.zvMapView.pack(fill=BOTH, expand=YES, anchor=CENTER)
        self.zvMapView.bind('<ButtonRelease-1>', lambda e: \
                            self.drawPoint(
                                self.__mapViewCoordinateConv(self.zvMapView.coords_conv(e.x,e.y))
                                ))
        self.zvMapView.bind('<Shift-ButtonRelease-1>', lambda e: \
                            self.drawArea(
                                self.__mapViewCoordinateConv(self.zvMapView.coords_conv(e.x,e.y))
                                ))
        self.zvMapView.bind('<Button-3>', lambda e: \
                            self.drawClear())
        self.zvMapView.bind('<Enter>', lambda e: self.app.statusBarMessage(TEXT['tooltipMapView'], layer='top'))
        self.zvMapView.bind('<Leave>', lambda e: self.app.statusBarMessage('', layer='top'))

        # The bottom layer shows terrain
        self.imgDotMapRaw: PIL.Image.Image = None

        # The top layer shows units
        self.imgUnitsDotLayer: PIL.Image.Image = None

        self.sizeMap: int = None
        self.background = self.app.style.colors.bg

    def loadMapView(self):
        self.sizeMap = self.mm.map_width
        self.imgDotMapRaw = PIL.Image.new('RGB', (self.sizeMap,self.sizeMap))
        for y in range(0, self.mm.map_height):
            for x in range(0, self.mm.map_width):
                tile = self.mm.get_tile(x, y)
                self.imgDotMapRaw.putpixel((x,y), TERRAIN_PAL[tile.terrain_id])
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
                    color = (*MapView.UNIT_DOT_PAL[unit.player], 255)
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
                        color = (*MapView.UNIT_DOT_PAL[unit.player], 255)
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
        self.pointSelect[0] = (-1, -1)
        self.pointSelect[1] = (-1, -1)
        imgDotBase = self.imgDotMapRaw.copy()
        self.zvMapView.set_image(imgDotBase)

    def drawClear(self) -> None:
        self.__redrawMap()

    def drawPoint(self, xy: tuple[int, int], see = False) -> None:
        self.pointSelect[0] = xy
        self.pointSelect[0] = self.__mapLocationFix(self.pointSelect[0])
        self.pointSelect[1] = (-1, -1)
        x, y = self.pointSelect[0]
        imgDotBase = self.imgDotMapRaw.copy()
        imgDotMask = PIL.Image.new('RGBA', (self.sizeMap,)*2, (0,0,0,0))
        imageDraw = PIL.ImageDraw.Draw(imgDotMask)
        imageDraw.point((x, y), (255, 255, 0, 176))
        imgDotBase.paste(imgDotMask, mask=imgDotMask)
        self.zvMapView.set_image(imgDotBase)
        if see:
            self.zvMapView.see(*self.__inverseMapViewCoordinateConv(xy))

    def drawArea(self, xy: tuple[int, int], see = False) -> None:
        if self.pointSelect[0] == (-1, -1):
            self.drawPoint(xy, see)
            return
        self.pointSelect[1] = self.__mapLocationFix(xy)
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
        x1, y1, x2, y2 = *self.pointSelect[0], *self.pointSelect[1]
        if self.pointSelect[1] == (-1, -1):
            x2, y2 = x1, y1
        else:
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1
        return (x1, y1, x2, y2)