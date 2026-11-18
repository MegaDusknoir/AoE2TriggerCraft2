from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal
from math import sqrt
from tkinter.constants import *
import ttkbootstrap as ttk

import PIL.Image
import PIL.ImageDraw
import PIL.ImageTk
from PIL.Image import Resampling
from PIL import ImageColor

from AoE2ScenarioParser.objects.managers.map_manager import MapManager, TerrainTile
from Localization import TEXT, UNIT_NAME
from TerrainPal import getTileColor
from CommonPalette import AOE_PAL
from TriggerAbstract import getAreaAbstract
from Util import IntListVar, PairValueEntry, Tooltip, ZoomImageViewer, fastAoERotate
from CeAttributesManager import CeAttributes

if TYPE_CHECKING:
    from main import TCWindow

logger = logging.getLogger(__name__.split('.')[-1])

SQRT_8 = sqrt(8)
class MapView(ttk.Frame):
    @property
    def mm(self):
        return self.app.mm

    @property
    def um(self):
        return self.app.um

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
    TRIGGER_AREA_COLOR = ImageColor.getcolor('#FFFF66CA', "RGBA")
    TRIGGER_TILE_COLOR = ImageColor.getcolor('#FFFF66CA', "RGBA")
    TRIGGER_LINE_COLOR = ImageColor.getcolor('#FFFFFFB5', "RGBA")
    CHECKBOARD_COLOR_LIGHT = ImageColor.getcolor("#FFFFFF08", "RGBA")
    CHECKBOARD_COLOR_DARK = ImageColor.getcolor("#00000008", "RGBA")
    LAYER_MASK_COLOR = ImageColor.getcolor("#000000CC", "RGBA")

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.rhombusViewScale: Literal[4, 8] = 4

        # [x1,y1,x2,y2]
        self.pointSelect = IntListVar(value=[-1,]*4)
        self.drawAreaUpdateUnitList = False

        self.zvMapView = ZoomImageViewer(self,
                                        PIL.Image.new('RGB', (1,1)), bg="black",
                                        viewport_transform=self.__rotateMapViewport)
        self.zvMapView.drag_enabled = self.app.fTPanel.active_tool == "select"
        self.zvMapView.pack(side=LEFT, fill=BOTH, expand=YES, anchor=CENTER)
        self.zvMapView.bind('<ButtonRelease-1>', self.__eventMapViewSetPoint1)
        self.zvMapView.bind('<Shift-ButtonRelease-1>', self.__eventMapViewSetPoint2)
        self.zvMapView.bind('<Button-3>', self.__eventMapViewClear)
        self.zvMapView.bind('<Enter>', self.__eventShowTooltipMapView)
        self.zvMapView.bind('<Leave>', lambda e: self.app.statusBarMessage('', layer='top'))
        self.zvMapView.bind_drag(self.__eventMapViewDrag)

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

        ttk.Separator(fPanel, orient=HORIZONTAL).grid(column=0, row=6, sticky=EW)
        self.varTriggerLayerVisible = ttk.BooleanVar(value=False)
        self.btnTriggerLayerVisible = ttk.Checkbutton(
            fPanel, text=TEXT['labelTriggerLayer'],
            bootstyle=(ttk.ROUND, ttk.TOGGLE),
            variable=self.varTriggerLayerVisible,
            command=self.__toggleTriggerLayer)
        self.btnTriggerLayerVisible.grid(
            column=0, row=9, columnspan=2, sticky=W,
            pady=self.app.dpi((10, 0)))
        Tooltip(self.btnTriggerLayerVisible, TEXT['tooltipTriggerLayer'])
        self.varCheckerboardLayerVisible = ttk.BooleanVar(value=False)
        self.btnCheckerboardLayerVisible = ttk.Checkbutton(
            fPanel, text=TEXT['labelCheckerboardLayer'],
            bootstyle=(ttk.ROUND, ttk.TOGGLE),
            variable=self.varCheckerboardLayerVisible,
            command=self.__toggleCheckerboardLayer)
        self.btnCheckerboardLayerVisible.grid(
            column=0, row=7, columnspan=2, sticky=W,
            pady=self.app.dpi((10, 0)))
        Tooltip(self.btnCheckerboardLayerVisible, TEXT['tooltipCheckerboardLayer'])
        self.varUpperTerrainLayerVisible = ttk.BooleanVar(value=False)
        self.btnUpperTerrainLayerVisible = ttk.Checkbutton(
            fPanel, text=TEXT['labelUpperTerrainLayer'],
            bootstyle=(ttk.ROUND, ttk.TOGGLE),
            variable=self.varUpperTerrainLayerVisible,
            command=self.__toggleUpperTerrainLayer)
        self.btnUpperTerrainLayerVisible.grid(
            column=0, row=8, columnspan=2, sticky=W,
            pady=self.app.dpi((10, 0)))
        Tooltip(self.btnUpperTerrainLayerVisible, TEXT['tooltipUpperTerrainLayer'])

        fPanel.grid_columnconfigure(0, pad=self.app.dpi(10))
        fPanel.grid_columnconfigure(1, pad=self.app.dpi(10))
        fPanel.grid_rowconfigure(list(range(6)), pad=self.app.dpi(10))

        self._updatingCoords = False
        self.pointSelect.trace_add('write', lambda *args: self.modifyPoint())

        # The bottom layer shows terrain
        self.imgDotMapRaw: PIL.Image.Image = None
        self.imgLayerDotMapRaw: PIL.Image.Image = None
        self.imgCheckerboardLayer: PIL.Image.Image = None
        self._upperTerrainLayerVisible = False
        self._checkerboardLayerVisible = False

        # The top layer shows units
        self.imgUnitsDotLayer: PIL.Image.Image = None
        self._unitLayerVersion = 0
        self._terrainLayerVersion = 0
        self.imgTriggerDotLayer: PIL.Image.Image = None
        self._triggerLayerVisible = False
        self._triggerLayerDirty = True
        self._triggerLayerVersion = 0
        self._mapTransformCacheSource = None
        self._mapTransformCacheVersion = -1
        self._mapTransformCacheTriggerVersion = -1
        self._mapTransformCacheTriggerVisible = None
        self._mapTransformCacheCheckerboardVisible = None
        self._mapTransformCacheUpperTerrainVisible = None
        self._mapTransformCacheImage = None

        self.sizeMap: int = None
        self.background = self.app.style.colors.bg

    def updateDarkMode(self):
        self.background = self.app.style.colors.bg
        self.zvMapView.set_image(self.zvMapView.original_image)

    def setTerrainTool(self, tool: str) -> None:
        self.zvMapView.drag_enabled = tool == "select"

    def __eventMapViewSetPoint1(self, event) -> None:
        if (self.app.fTPanel.active_tool == "select"
            or self.app.nTabsLeft.index('current') != self.app.nTabsLeft.index(self.app.fTPanel)):
            self.drawSetPoint1(
                self.__mapViewCoordinateConv(self.zvMapView.coords_conv(event.x, event.y))
            )
        elif self.app.fTPanel.active_tool == "pencil":
            terrain = self.app.fTPanel.getTerrainSelection()
            if terrain >= 0:
                x, y = self.__mapViewCoordinateConv(self.zvMapView.coords_conv(event.x, event.y))
                tile = self.app.mm.get_tile_safe(x,y)
                if tile:
                    if self._upperTerrainLayerVisible:
                        tile.layer = terrain if terrain != tile.terrain_id else -1
                    else:
                        tile.terrain_id = terrain
                    self.app.modified = True
                    self.updateTerrainLayerDot(x,y,tile)

    def __eventMapViewSetPoint2(self, event) -> None:
        if (self.app.fTPanel.active_tool == "select"
            or self.app.nTabsLeft.index('current') != self.app.nTabsLeft.index(self.app.fTPanel)):
            self.drawSetPoint2(
                self.__mapViewCoordinateConv(self.zvMapView.coords_conv(event.x, event.y))
            )

    def __eventShowTooltipMapView(self, _event) -> None:
        if (self.app.fTPanel.active_tool == "select"
            or self.app.nTabsLeft.index('current') != self.app.nTabsLeft.index(self.app.fTPanel)):
            self.app.statusBarMessage(TEXT['tooltipMapView'], layer='top')
        elif self.app.fTPanel.active_tool == "pencil":
            self.app.statusBarMessage(TEXT['tooltipMapViewPencil'], layer='top')

    def __eventMapViewClear(self, _event) -> None:
        if (self.app.fTPanel.active_tool == "select"
            or self.app.nTabsLeft.index('current') != self.app.nTabsLeft.index(self.app.fTPanel)):
            self.drawClear()
        elif self.app.fTPanel.active_tool == "pencil":
            self.varUpperTerrainLayerVisible.set(not self._upperTerrainLayerVisible)
            self.__toggleUpperTerrainLayer()

    def __eventMapViewDrag(self, event) -> None:
        if (self.app.fTPanel.active_tool == "select"
            or self.app.nTabsLeft.index('current') != self.app.nTabsLeft.index(self.app.fTPanel)):
            pass
        elif self.app.fTPanel.active_tool == "pencil":
            terrain = self.app.fTPanel.getTerrainSelection()
            if terrain >= 0:
                x, y = self.__mapViewCoordinateConv(self.zvMapView.coords_conv(event.x, event.y))
                tile = self.app.mm.get_tile_safe(x,y)
                if tile:
                    if self._upperTerrainLayerVisible:
                        tile.layer = terrain if terrain != tile.terrain_id else -1
                    else:
                        tile.terrain_id = terrain
                    self.app.modified = True
                    self.updateTerrainLayerDot(x,y,tile)

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
        self.__cancelTriggerLayerUpdate()
        self.sizeMap = self.mm.map_width
        if (self.imgCheckerboardLayer is None
                or self.imgCheckerboardLayer.size != (self.sizeMap, self.sizeMap)):
            self.imgCheckerboardLayer = self.__buildCheckerboardLayer(self.sizeMap, self.sizeMap)
        self.loadTerrainLayer()
        self.loadUnitLayer()
        self._triggerLayerDirty = True
        if self._triggerLayerVisible:
            self.__rebuildTriggerLayer()
        else:
            self.imgTriggerDotLayer = None
        self.__redrawMap()
        self.zvMapView.see(*self.__inverseMapViewCoordinateConv((self.sizeMap // 2, self.sizeMap // 2)))

    def loadTerrainLayer(self):
        self.imgDotMapRaw = PIL.Image.new('RGB', (self.sizeMap,self.sizeMap))
        self.imgLayerDotMapRaw = PIL.Image.new('RGBA', (self.sizeMap,self.sizeMap))
        self._terrainLayerVersion += 1
        for y in range(0, self.mm.map_height):
            for x in range(0, self.mm.map_width):
                tile = self.mm.get_tile(x, y)
                self.imgDotMapRaw.putpixel((x,y), getTileColor(tile.terrain_id, tile.elevation))
                self.imgLayerDotMapRaw.putpixel((x,y), getTileColor(tile.layer, 1)
                                                if tile.layer >= 0
                                                else self.LAYER_MASK_COLOR)

    def loadUnitLayer(self):
        self.imgUnitsDotLayer = PIL.Image.new('RGBA', (self.sizeMap * 2 + 1, self.sizeMap * 2 + 1), (0,0,0,0))
        self._unitLayerVersion += 1
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

    def updateTerrainLayer(self):
        def __updateTerrainLayer():
            del self._terrainLayerUpdate
            self.drawArea()

        if not hasattr(self, '_terrainLayerUpdate'):
            self._terrainLayerUpdate = self.after(25, __updateTerrainLayer)

    def updateTerrainLayerDot(self, dot_x: int, dot_y: int, tile: TerrainTile):
        if not (0 <= dot_x < self.sizeMap and 0 <= dot_y < self.sizeMap):
            return
        self._terrainLayerVersion += 1
        self.imgDotMapRaw.putpixel((dot_x,dot_y), getTileColor(tile.terrain_id, tile.elevation))
        self.imgLayerDotMapRaw.putpixel((dot_x,dot_y), getTileColor(tile.layer, 1)
                                        if tile.layer >= 0
                                        else self.LAYER_MASK_COLOR)
        self.updateTerrainLayer()

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
        self._unitLayerVersion += 1
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

    def __mapViewCoordinateConv(self, rhombus_xy: tuple[float, float]) -> tuple[int, int]:
        """Transpose the rhombus view coords to map coords"""
        rx, ry = rhombus_xy
        scale = SQRT_8 / self.rhombusViewScale
        x = round(scale * (rx - 2 * ry) + self.sizeMap / 2 - 0.5)
        y = round(scale * (rx + 2 * ry) - self.sizeMap / 2 - 0.5)
        return (x,y)

    def __inverseMapViewCoordinateConv(self, map_xy: tuple[int, int]) -> tuple[float, float]:
        """Transpose the map coords to rhombus view coords"""
        mx, my = map_xy

        rx = self.rhombusViewScale * (mx + my + 1) / (2 * SQRT_8)
        ry = self.rhombusViewScale * (self.sizeMap + my - mx) / (4 * SQRT_8)
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

    def markTriggerLayerDirty(self):
        self._triggerLayerDirty = True
        if not self._triggerLayerVisible or self.imgDotMapRaw is None:
            return
        self.__cancelTriggerLayerUpdate()
        self._triggerLayerUpdate = self.after(
            100, self.__runScheduledTriggerLayerRefresh)

    def __cancelTriggerLayerUpdate(self):
        if hasattr(self, '_triggerLayerUpdate'):
            self.after_cancel(self._triggerLayerUpdate)
            del self._triggerLayerUpdate

    def __runScheduledTriggerLayerRefresh(self):
        if hasattr(self, '_triggerLayerUpdate'):
            del self._triggerLayerUpdate
        self.__refreshTriggerLayer()

    def __toggleTriggerLayer(self):
        self.__cancelTriggerLayerUpdate()
        self._triggerLayerVisible = self.varTriggerLayerVisible.get()
        if self._triggerLayerVisible:
            self.rhombusViewScale = 8
            self.zvMapView.zoom_factor /= 2
            self.zvMapView.min_zoom /= 2
            self.zvMapView.max_zoom /= 2
            self._triggerLayerDirty = True
            self.__refreshTriggerLayer()
        else:
            self.rhombusViewScale = 4
            self.zvMapView.zoom_factor *= 2
            self.zvMapView.min_zoom *= 2
            self.zvMapView.max_zoom *= 2
            self.imgTriggerDotLayer = None
            self._triggerLayerVersion += 1
            if self.imgDotMapRaw is not None:
                self.zvMapView.set_image(self.zvMapView.original_image)

    def __refreshTriggerLayer(self):
        if (not self._triggerLayerVisible or self.imgDotMapRaw is None
                or not self._triggerLayerDirty):
            return
        self.__rebuildTriggerLayer()
        self.zvMapView.set_image(self.zvMapView.original_image)

    def __rebuildTriggerLayer(self):
        if not self._triggerLayerVisible or self.imgDotMapRaw is None:
            return
        self.imgTriggerDotLayer = self.__buildTriggerLayer()
        self._triggerLayerDirty = False
        self._triggerLayerVersion += 1

    def __toggleCheckerboardLayer(self):
        self._checkerboardLayerVisible = self.varCheckerboardLayerVisible.get()
        if self.imgDotMapRaw is not None:
            self.zvMapView.set_image(self.zvMapView.original_image)

    def __toggleUpperTerrainLayer(self):
        self._upperTerrainLayerVisible = self.varUpperTerrainLayerVisible.get()
        if self.imgLayerDotMapRaw is not None:
            self.zvMapView.set_image(self.zvMapView.original_image)

    def __buildCheckerboardLayer(self, width, height) -> PIL.Image.Image:
        row_size = (width + 7) // 8

        row0 = (b'\x55' * row_size)[:row_size]
        row1 = (b'\xAA' * row_size)[:row_size]

        white = bytes(self.CHECKBOARD_COLOR_LIGHT)
        black = bytes(self.CHECKBOARD_COLOR_DARK)

        row0 = b''.join(
            white if (x & 1) else black
            for x in range(width)
        )
        row1 = b''.join(
            black if (x & 1) else white
            for x in range(width)
        )

        data = (row0 + row1) * (height // 2)
        if height & 1:
            data += row0

        return PIL.Image.frombytes('RGBA', (width, height), data)

    def __mapPoint(self, x: int, y: int) -> tuple[int, int] | None:
        if not isinstance(x, int) or not isinstance(y, int):
            return None
        if not (0 <= x < self.sizeMap and 0 <= y < self.sizeMap):
            return None
        return x, y

    def __drawTriggerPoint(self, draw: PIL.ImageDraw.ImageDraw,
                       point: tuple[int, int], color: tuple[int, int, int, int]):
        x, y = point
        left, top = x * 4, y * 4
        draw.rectangle((left, top, left + 2, top + 2), outline=color, width=1)

    def __drawTriggerArea(self, draw: PIL.ImageDraw.ImageDraw,
                      area: tuple[int, int, int, int],
                      color: tuple[int, int, int, int]) -> tuple[int, int]:
        x1, y1, x2, y2 = area
        left, top = min(x1, x2) * 4, min(y1, y2) * 4
        full_right = (max(x1, x2) + 1) * 4 - 1
        full_bottom = (max(y1, y2) + 1) * 4 - 1
        draw.rectangle((left, top, full_right - 1, full_bottom - 1),
                       outline=color, width=1)
        return (round((left + full_right - 1) / 2),
                round((top + full_bottom - 1) / 2))

    def __drawTriggerDashedLine(self, draw: PIL.ImageDraw.ImageDraw,
                         start: tuple[int, int], end: tuple[int, int],
                         color: tuple[int, int, int, int]):
        x, y = start
        end_x, end_y = end
        dx, dy = abs(end_x - x), abs(end_y - y)
        step_x = 1 if x < end_x else -1
        step_y = 1 if y < end_y else -1
        error = dx - dy
        step = 0
        while True:
            if step % 3 != 0:
                draw.point((x, y), fill=color)
            if x == end_x and y == end_y:
                break
            doubled_error = error * 2
            if doubled_error > -dy:
                error -= dy
                x += step_x
            if doubled_error < dx:
                error += dx
                y += step_y
            step += 1

    def __buildTriggerLayer(self) -> PIL.Image.Image:
        layer = PIL.Image.new(
            'RGBA', (self.sizeMap * 4, self.sizeMap * 4), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(layer)
        condition_attributes = CeAttributes.condition()
        effect_attributes = CeAttributes.effect()

        for trigger in self.app.tm.triggers:
            for condition in trigger.conditions:
                attributes = condition_attributes.get(condition.condition_type, ())
                if 'area_x1' in attributes:
                    area = self.__mapArea(condition)
                    if area is not None:
                        self.__drawTriggerArea(draw, area, self.TRIGGER_AREA_COLOR)

            for effect in trigger.effects:
                attributes = effect_attributes.get(effect.effect_type, ())
                area = self.__mapArea(effect) if 'area_x1' in attributes else None
                area_center = self.__drawTriggerArea(draw, area, self.TRIGGER_AREA_COLOR) if area is not None else None

                if 'location_x' in attributes:
                    unit_reference = getattr(effect, 'location_object_reference', -1)
                    location = None if unit_reference != -1 else self.__mapPoint(
                        effect.location_x, effect.location_y)
                    if location is not None:
                        self.__drawTriggerPoint(draw, location, self.TRIGGER_TILE_COLOR)
                        if area_center is not None:
                            target_center = (location[0] * 4 + 1, location[1] * 4 + 1)
                            self.__drawTriggerDashedLine(draw, area_center, target_center, self.TRIGGER_LINE_COLOR)

                for wall_attribute in ('wall_x1', 'wall_x2'):
                    if wall_attribute in attributes:
                        wall_point = self.__mapPoint(
                            getattr(effect, wall_attribute),
                            getattr(effect, wall_attribute.replace('_x', '_y')))
                        if wall_point is not None:
                            self.__drawTriggerPoint(draw, wall_point, self.TRIGGER_TILE_COLOR)

        return layer

    def __mapArea(self, ce) -> tuple[int, int, int, int] | None:
        x1 = getattr(ce, 'area_x1', -1)
        y1 = getattr(ce, 'area_y1', -1)
        x2 = getattr(ce, 'area_x2', -1)
        y2 = getattr(ce, 'area_y2', -1)
        point1 = self.__mapPoint(x1, y1)
        point2 = self.__mapPoint(x2, y2)
        if point1 is None or point2 is None:
            return None
        return (*point1, *point2)

    def __rotateMapViewport(self, image: PIL.Image.Image, zoom: float,
                            viewport: tuple[int, int, int, int]
                            ) -> tuple[PIL.Image.Image, tuple[int, int], tuple[int, int]]:
        """Transform only the visible portion of the rhombus map."""
        if self.imgUnitsDotLayer is None:
            return (PIL.Image.new('RGBA', (1, 1), (0, 0, 0, 0)),
                    (0, 0), (1, 1))

        if (self._mapTransformCacheSource is not image
                or self._mapTransformCacheTerrainVersion != self._terrainLayerVersion
                or self._mapTransformCacheVersion != self._unitLayerVersion
                or self._mapTransformCacheTriggerVersion != self._triggerLayerVersion
                or self._mapTransformCacheTriggerVisible != self._triggerLayerVisible
                or self._mapTransformCacheCheckerboardVisible != self._checkerboardLayerVisible
                or self._mapTransformCacheUpperTerrainVisible != self._upperTerrainLayerVisible):
            if self._upperTerrainLayerVisible:
                scaled_map = image.convert('RGBA')
                scaled_map.alpha_composite(self.imgLayerDotMapRaw)
                scaled_map = scaled_map.resize((image.width * self.rhombusViewScale,) * 2,
                                               resample=Resampling.NEAREST)
            else:
                scaled_map = image.resize((image.width * self.rhombusViewScale,) * 2,
                                          resample=Resampling.NEAREST).convert('RGBA')
            if (self._checkerboardLayerVisible
                    and self.imgCheckerboardLayer is not None):
                checkerboard_layer = self.imgCheckerboardLayer.resize(
                    (self.imgCheckerboardLayer.width * self.rhombusViewScale,) * 2,
                    resample=Resampling.NEAREST)
                scaled_map.alpha_composite(checkerboard_layer)
            if self._triggerLayerVisible and self.imgTriggerDotLayer is not None:
                trigger_layer = self.imgTriggerDotLayer.resize(
                    (self.imgTriggerDotLayer.width * (self.rhombusViewScale // 4),) * 2,
                    resample=Resampling.NEAREST)
                scaled_map.paste(trigger_layer, (self.rhombusViewScale // 8, ) * 2, trigger_layer)
            unit_layer = self.imgUnitsDotLayer.resize(
                (self.imgUnitsDotLayer.width * (self.rhombusViewScale // 2),) * 2,
                resample=Resampling.NEAREST)
            scaled_map.paste(unit_layer, (-self.rhombusViewScale // 4, ) * 2, unit_layer)
            self._mapTransformCacheSource = image
            self._mapTransformCacheVersion = self._unitLayerVersion
            self._mapTransformCacheTerrainVersion = self._terrainLayerVersion
            self._mapTransformCacheTriggerVersion = self._triggerLayerVersion
            self._mapTransformCacheTriggerVisible = self._triggerLayerVisible
            self._mapTransformCacheCheckerboardVisible = self._checkerboardLayerVisible
            self._mapTransformCacheUpperTerrainVisible = self._upperTerrainLayerVisible
            self._mapTransformCacheImage = scaled_map

        rotated_width = (image.width * self.rhombusViewScale) * (zoom / 4) * sqrt(2)
        full_width = round(rotated_width)
        full_height = round(rotated_width / 2)
        left, top, right, bottom = viewport
        crop_box = (max(0, left), max(0, top),
                    min(full_width, right), min(full_height, bottom))
        if crop_box[0] >= crop_box[2] or crop_box[1] >= crop_box[3]:
            return (PIL.Image.new('RGBA', (1, 1), (0, 0, 0, 0)),
                    (left, top), (full_width, full_height))
        crop = fastAoERotate(self._mapTransformCacheImage, zoom / 4,
                             fillcolor=self.background, crop_box=crop_box)
        return crop, (crop_box[0], crop_box[1]), (full_width, full_height)

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
        if self.drawAreaUpdateUnitList:
            self.app.fUEditor.refreshFilteredUnit(self.getArea())

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