
from math import sqrt
import os
import sys
import re
import json
import jsonschema
import base64
import datetime
import time
from typing import Literal, TextIO
import ctypes
import tempfile
from parse import parse

import tkinter as tk
import tkinter.font as tkfont
from tkinter.constants import *
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter import messagebox
from tkinter.ttk import Widget
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText

import PIL.Image
import PIL.ImageTk
from webbrowser import open as webOpen

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.objects.managers.map_manager import MapManager
from AoE2ScenarioParser.objects.managers.trigger_manager import TriggerManager
from AoE2ScenarioParser.objects.support.trigger_select import TriggerSelect
from AoE2ScenarioParser.objects.data_objects.trigger import Trigger
from AoE2ScenarioParser.objects.data_objects.effect import Effect
from AoE2ScenarioParser.objects.data_objects.condition import Condition
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.objects.support.trigger_ce_lock import TriggerCELock
from AoE2ScenarioParser.exceptions.asp_exceptions import UnknownScenarioStructureError
from AoE2ScenarioParser.datasets.effects import EffectId
import AoE2ScenarioParser.settings as ASPSettings

from Localization import *
from Options import GlobalOptions, ScenarioOptions
from TriggerAbstract import *
from views.TriggerView import TriggerView
from views.UnitInfo import UnitInfoView
from views.UnitView import UnitView
from views.MapView import MapView
from views.MetaView import MetaView
from views.TriggerInfo import TriggerInfoView
from views.CeInfo import CeInfoView
from Util import IntListVar, MappedCombobox, ListValueButton, PairValueEntry, Tooltip, ValueSelectButton, ZoomImageViewer
from Util import DebugTimeCount
from _prebuild.version import VERSION_STRING
from _prebuild.AoE2TC_icon import Icon
from _prebuild.CeAttributes import CONDITION_ATTRIBUTES, EFFECT_ATTRIBUTES
from WidgetLayout import CONDITION_WIDGET_FORM, EFFECT_WIDGET_FORM

if getattr(sys, 'frozen', False): # True if PyInstaller packed
    workDir = os.path.dirname(sys.executable)
else:
    workDir = os.path.dirname(os.path.abspath(__file__))

ASPSettings.ENABLE_XS_CHECK_INTEGRATION = False
ASPSettings.ALLOW_OVERWRITING_SOURCE = True

class CreateIcon():
    def __init__(self):
        self.path = None

    def __enter__(self):
        self.file, self.path = tempfile.mkstemp()
        with os.fdopen(self.file, 'wb') as tmp:
            tmp.write(base64.b64decode(Icon().ig))
        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.remove(self.path)

class RedirectIO(TextIO):
    def __init__(self):
        super().__init__()
        self.write = super().write

class TriggerJsonIO():
    triggerAttributesSet = [
        'name',
        'trigger_id',
        'description_stid',
        'description',
        'display_as_objective',
        'description_order',
        'short_description_stid',
        'short_description',
        'display_on_screen',
        'enabled',
        'looping',
        'header',
        'mute_objectives',
        'condition_order',
        'effect_order',
        # 'conditions',
        # 'effects',
    ]

    class TriggerJsonNotRestorableError(Exception):
        pass

    class TriggerJsonInvalidError(Exception):
        pass

    @classmethod
    def export(cls, tm: TriggerManager, begin:int=None, end:int=None) -> dict:
        if begin is None:
            begin = 0
        if end is None:
            end = len(tm.triggers)

        exportTriggerOrder = tm.trigger_display_order[begin:end]
        selectTriggersId: list[int] = []
        for id in exportTriggerOrder:
            selectTriggersId.append(id)
        selectTriggersId.sort()
        triggersList = []
        for i in selectTriggersId:
            trigger = tm.triggers[i]
            triggerDict = {}
            for attr in cls.triggerAttributesSet:
                triggerDict[attr] = getattr(trigger, attr)
            triggerDict['conditions'] = []
            triggerDict['effects'] = []
            for condition in trigger.conditions:
                conditionDict = {'condition_type': condition.condition_type}
                for attr in CONDITION_ATTRIBUTES.get(condition.condition_type, []):
                    conditionDict[attr] = getattr(condition, attr)
                triggerDict['conditions'].append(conditionDict)
            for effect in trigger.effects:
                effectDict = {'effect_type': effect.effect_type}
                for attr in EFFECT_ATTRIBUTES.get(effect.effect_type, []):
                    effectDict[attr] = getattr(effect, attr)
                triggerDict['effects'].append(effectDict)
            triggersList.append(triggerDict)
        triggersDump = {
            'trigger_display_order':exportTriggerOrder,
            'triggers': triggersList
        }
        return triggersDump

    @classmethod
    def append(cls, tm: TriggerManager, obj: dict):
        if not cls.__validate(obj):
            raise cls.TriggerJsonInvalidError("Trigger JSON invalid")
        importTriggerOriginalIds = []
        importTriggerIdMap = {}
        importedTriggers = []
        lengthBefore = len(tm.triggers)
        newOrder = tm.trigger_display_order.copy()

        for i, triggerDict in enumerate(obj['triggers']):
            # ID in its source scenario
            oldId = triggerDict['trigger_id']
            importTriggerOriginalIds.append(oldId)
            trigger:Trigger = tm.add_trigger(triggerDict['name'])
            importedTriggers.append(trigger)
            for attr in cls.triggerAttributesSet:
                setattr(trigger, attr, triggerDict[attr])
            # ID in current scenario
            newId = i + lengthBefore
            importTriggerIdMap[oldId] = newId
            trigger.trigger_id = newId
            for conditionDict in triggerDict['conditions']:
                condition = trigger.new_condition.none()
                condition.condition_type = conditionDict['condition_type']
                for attr in CONDITION_ATTRIBUTES.get(condition.condition_type, []):
                    setattr(condition, attr, conditionDict[attr])
            for effectDict in triggerDict['effects']:
                effect = trigger.new_effect.none()
                effect.effect_type = effectDict['effect_type']
                for attr in EFFECT_ATTRIBUTES.get(effect.effect_type, []):
                    setattr(effect, attr, effectDict[attr])
            trigger.condition_order = triggerDict['condition_order']
            trigger.effect_order = triggerDict['effect_order']

        # Redirect CEs in imported triggers, set to -1 if the target trigger not imported.
        for trigger in importedTriggers:
            for condition in trigger.conditions:
                if condition.trigger_id in importTriggerOriginalIds:
                    condition.trigger_id = importTriggerIdMap[condition.trigger_id]
                else:
                    condition.trigger_id = -1
            for effect in trigger.effects:
                if effect.trigger_id in importTriggerOriginalIds:
                    effect.trigger_id = importTriggerIdMap[effect.trigger_id]
                else:
                    effect.trigger_id = -1

        # Import trigger order for imported triggers
        for id in obj['trigger_display_order']:
            newOrder.append(importTriggerIdMap[id])
        tm.trigger_display_order = newOrder

    @classmethod
    def restore(cls, tm: TriggerManager, obj: dict):
        if not cls.__validate(obj):
            raise cls.TriggerJsonInvalidError("Trigger JSON invalid")
        if set(obj['trigger_display_order']) != set(range(len(obj['trigger_display_order']))):
            raise cls.TriggerJsonNotRestorableError("Not a restorable Trigger JSON")
        tm.remove_triggers([i for i in range(len(tm.triggers))])

        for triggerDict in obj['triggers']:
            trigger:Trigger = tm.add_trigger(triggerDict['name'])
            for attr in cls.triggerAttributesSet:
                setattr(trigger, attr, triggerDict[attr])
            for conditionDict in triggerDict['conditions']:
                condition = trigger.new_condition.none()
                condition.condition_type = conditionDict['condition_type']
                for attr in CONDITION_ATTRIBUTES.get(condition.condition_type, []):
                    setattr(condition, attr, conditionDict[attr])
            for effectDict in triggerDict['effects']:
                effect = trigger.new_effect.none()
                effect.effect_type = effectDict['effect_type']
                for attr in EFFECT_ATTRIBUTES.get(effect.effect_type, []):
                    setattr(effect, attr, effectDict[attr])
            trigger.condition_order = triggerDict['condition_order']
            trigger.effect_order = triggerDict['effect_order']
        tm.trigger_display_order = obj['trigger_display_order']

    schema = {
        "type": "object",
        "properties": {
            "trigger_display_order": {
                "type": "array",
                "items": {
                    "type": "integer"
                }
            },
            "triggers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "condition_order": {
                            "type": "array",
                            "items": {
                                "type": "integer"
                            }
                        },
                        "effect_order": {
                            "type": "array",
                            "items": {
                                "type": "integer"
                            }
                        },
                        "conditions": {
                            "type": "array",
                            "items": {
                                "type": "object"
                            }
                        },
                        "effects": {
                            "type": "array",
                            "items": {
                                "type": "object"
                            }
                        }
                    }
                }
            }
        },
        "required": [
            "trigger_display_order",
            "triggers"
        ],
        "additionalProperties": False
    }

    @classmethod
    def __validate(cls, obj: dict) -> bool:
        try:
            jsonschema.validate(obj, cls.schema)
        except jsonschema.ValidationError:
            return False
        length = len(obj['triggers'])
        if len(obj['trigger_display_order']) != length:
            return False
        return True

class TCWindow():

    def __init__(self, theme='darkly') -> None:
        start_init = time.time()

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        self.scaleFactor=ctypes.windll.shcore.GetScaleFactorForDevice(0)

        # Packed script has no console, redirect IO first
        self.tLog = None
        self.logCatch = None
        self.ioAgent = RedirectIO()
        self.ioAgent.write = self.writeLog
        self.stdoutBack = sys.stdout
        sys.stdout = self.ioAgent

        try:
            loadLocalizedText(workDir)
        except ResourcesFileError as e:
            messagebox.showerror('File Error', 'The application can not startup due to:\n\n{0}'.format(e.args[0]), icon='error')
            sys.exit()

        self.root = ttk.Window(TEXT['titleMainWindow'], iconphoto=None)
        self.root.geometry(f'{self.dpi(1280)}x{self.dpi(720)}')
        self.root.protocol('WM_DELETE_WINDOW', self.windowClose)
        self.theme = theme
        self.style = ttk.Style()
        self.style.theme_use(self.theme)
        if self.theme in ('darkly'):
            self.tvLineColoring = self.style.colors.inputbg
        else:
            self.tvLineColoring = self.style.colors.active

        self.__loadImages()

        self.options = GlobalOptions(workDir)
        self.wndLog = None
        self.__createMainWindow()

        end_init = time.time()
        print(f'Initialize used {end_init - start_init:.3f} seconds')

    def windowClose(self):
        if self.openedScenPath == '':
            self.root.destroy()
        elif self.askSaveScenario():
            self.root.destroy()

    def mainloop(self):
        """Call the mainloop."""
        with CreateIcon() as iconPath:
            self.root.iconbitmap(default=iconPath)

        # Show window before take time to load a scenario
        self.root.update()
        self.openedScenPath = ''
        self.generateDefaultScenario()
        with CreateIcon() as iconPath:
            self.imgAbout = self.__loadImage(iconPath, self.dpi((128, 128)))

        self.root.mainloop()

    def generateDefaultScenario(self):
        self.openedScenPath = ''
        ASPSettings.PRINT_STATUS_UPDATES = False
        self.activeScenario = AoE2DEScenario.from_default()
        ASPSettings.PRINT_STATUS_UPDATES = True
        print('Loaded default scenario')
        self.windowTitleTail = "default"
        self.triggerManager: TriggerManager = self.activeScenario.trigger_manager
        self.readScenario()

    def __catchScenLoadProgress(self, s: str) -> None:
        start = s.find('🔄 Gathering ')
        if start != -1:
            start += len('🔄 Gathering ')
            end = s.find(' data...')
            if end > start:
                self.statusBarMessage(TEXT['noticeFormatAspLoadingSection'].format(TEXT['noticeValueAspSectionName'][s[start : end]]), True)

    def writeLog(self, s:str, /) -> int:
        if self.stdoutBack != None:
            self.stdoutBack.write(s)
        if self.tLog != None and self.tLog.winfo_exists() == True:
            self.tLog.text.configure(state='normal')
            self.tLog.text.insert(END, s)
            self.tLog.text.configure(state='disabled')
            if s == '\n':
                self.tLog.see(END)
                self.tLog.update_idletasks()
        if self.logCatch != None:
            self.logCatch(s)
        return len(s)

    # region Creation

    def __createMainWindow(self):
        # tkfont.nametofont('TkDefaultFont').config(family='Segoe UI')
        defaultFont = tkfont.nametofont('TkDefaultFont')
        self.style.configure('Borderless.Treeview', borderwidth=0,
                             background=self.style.colors.bg, font=(defaultFont.cget('family'), 9), rowheight=self.dpi(20))
        self.style.configure('sideBarExpand.secondary.TButton', borderwidth=0, font=(defaultFont.cget('family'), 8),
                             foreground=self.style.colors.secondary,
                             background=self.style.colors.bg,
                             focuscolor=self.style.colors.bg,
                             padding=(0,0,0,0))
        self.style.map('sideBarExpand.secondary.TButton',
                       foreground=[('disabled', self.style.colors.secondary), ('active', self.style.colors.bg)],
                       focuscolor=[('disabled', self.style.colors.bg), ('active', self.style.colors.secondary)])
        self.style.configure('iconButton.Link.TButton', shiftrelief=1, padding=(2,2,1,1))
        self.style.configure('selectionButton.Link.TButton', shiftrelief=1, padding=(2,2,1,1), width=5, background=self.style.colors.active)
        self.style.configure('ceWidgetButton.Outline.TButton',)
        self.style.configure('ceWindowWidgetButton.success.Outline.TButton',)

        self.main = ttk.Frame(self.root, padding=self.dpi((10,10,10,5)))
        self.__createPanedWindow()
        self.__createStatusBar()
        self.__createMenu()
        self.__bindGlobalKeys()

        self.main.pack(fill=BOTH, expand=YES)

    def __loadImage(self, path, resize:tuple[int, int]) -> PIL.ImageTk.PhotoImage:
        try:
            with PIL.Image.open(path) as imgf:
                return PIL.ImageTk.PhotoImage(imgf.resize(resize))
        except (FileNotFoundError, PermissionError):
            return PIL.ImageTk.PhotoImage(PIL.Image.new('RGB', resize))

    def __loadImages(self):
        self.imgBtnDefault = self.__loadImage(f'{workDir}/images/btnDefault.png', self.dpi((20, 20)))
        self.imgBtnTAdd = self.__loadImage(f'{workDir}/images/btnTAdd.png', self.dpi((20, 20)))
        self.imgBtnCAdd = self.__loadImage(f'{workDir}/images/btnCAdd.png', self.dpi((20, 20)))
        self.imgBtnEAdd = self.__loadImage(f'{workDir}/images/btnEAdd.png', self.dpi((20, 20)))
        self.imgBtnIDelete = self.__loadImage(f'{workDir}/images/btnIDelete.png', self.dpi((20, 20)))
        self.imgBtnIDuplicate = self.__loadImage(f'{workDir}/images/btnIDuplicate.png', self.dpi((20, 20)))
        self.imgBtnIUnduplicate = self.__loadImage(f'{workDir}/images/btnIUnduplicate.png', self.dpi((20, 20)))
        self.imgBtnIDuplicateForAll = self.__loadImage(f'{workDir}/images/btnIDuplicateForAll.png', self.dpi((20, 20)))
        self.imgBtnIMoveUp = self.__loadImage(f'{workDir}/images/btnIMoveUp.png', self.dpi((20, 20)))
        self.imgBtnIMoveDown = self.__loadImage(f'{workDir}/images/btnIMoveDown.png', self.dpi((20, 20)))
        self.imgBtnIMove = self.__loadImage(f'{workDir}/images/btnIMove.png', self.dpi((20, 20)))
        self.imgBtnTSort = self.__loadImage(f'{workDir}/images/btnTSort.png', self.dpi((20, 20)))

        self.imgTriggerEnabled = self.__loadImage(f'{workDir}/images/tvTEnabledNoLoop.png', self.dpi((18, 18)))
        self.imgTriggerEnabledLoop = self.__loadImage(f'{workDir}/images/tvTEnabledLoop.png', self.dpi((18, 18)))
        self.imgTriggerDisabled = self.__loadImage(f'{workDir}/images/tvTDisabledNoLoop.png', self.dpi((18, 18)))
        self.imgTriggerDisabledLoop = self.__loadImage(f'{workDir}/images/tvTDisabledLoop.png', self.dpi((18, 18)))
        self.imgConditionEnabled = self.__loadImage(f'{workDir}/images/tvCondition.png', self.dpi((18, 18)))
        self.imgEffectEnabled = self.__loadImage(f'{workDir}/images/tvEffect.png', self.dpi((18, 18)))

        self.imgCeSetLocationUnit = self.__loadImage(f'{workDir}/images/btnCeSetLocUnit.png', self.dpi((20, 20)))
        self.imgCeSetArea = self.__loadImage(f'{workDir}/images/btnCeSetArea.png', self.dpi((20, 20)))

        # load later for start boost
        self.imgAbout = None

    def __createPanedWindow(self):
        # Divide the window by L-R layout
        self.pwMain = ttk.PanedWindow(self.main, orient=HORIZONTAL)
        self.fPwLeft = ttk.Frame(self.pwMain)
        self.fPwRight = ttk.Frame(self.pwMain)
        self.pwMain.add(self.fPwLeft)
        self.pwMain.add(self.fPwRight)
        self.pwMain.pack(fill=BOTH, expand=True)

        self.__createPanedWindowLeft()
        self.__createPanedWindowRight()

    def __createPanedWindowLeft(self):
        # Left pw is a single frame
        self.nTabsLeft = ttk.Notebook(self.fPwLeft)
        self.fTEditor = TriggerView(self, self.nTabsLeft)
        self.fTEditor.pack(fill=BOTH, expand=True, padx=(0, self.dpi(5)))
        self.fUEditor = UnitView(self, self.nTabsLeft)
        self.fUEditor.pack(fill=BOTH, expand=True, padx=(0, self.dpi(5)))
        self.nTabsLeft.add(self.fTEditor, text=TEXT['tabTriggerEditor'])
        self.nTabsLeft.add(self.fUEditor, text=TEXT['tabUnitEditor'])
        self.nTabsLeft.pack(fill=BOTH, expand=True, padx=(0, self.dpi(5)))

    def __createPanedWindowRight(self):
        # Divide the right window by T-B layout
        self.pwRight = ttk.PanedWindow(self.fPwRight, orient=VERTICAL)
        self.fPwRT = ttk.Frame(self.pwRight)
        self.fPwRB = ttk.Frame(self.pwRight)
        self.pwRight.add(self.fPwRT, weight=3)
        self.pwRight.add(self.fPwRB, weight=1)
        self.pwRight.pack(fill=BOTH, expand=True, padx=self.dpi((5, 0)))

        # Right pw is T-B layout
        self.nTabsRightTop = ttk.Notebook(self.fPwRT, width=400, height=200)
        self.nTabsRightBottom = ttk.Notebook(self.fPwRB)

        self.fMetaViewTab = MetaView(self, self.nTabsRightTop)
        self.fMapViewTab = MapView(self, self.nTabsRightTop)
        self.nTabsRightTop.add(self.fMetaViewTab, text=TEXT['tabMetaView'])
        self.nTabsRightTop.add(self.fMapViewTab, text=TEXT['tabMapView'])
        self.nTabsRightTop.select(self.fMapViewTab)

        self.triggerManager: TriggerManager
        self.fTriggerInfo = TriggerInfoView(self, self.nTabsRightBottom)
        self.fCeInfo = CeInfoView(self, self.nTabsRightBottom)
        self.fUnitInfo = UnitInfoView(self, self.nTabsRightBottom)
        self.nTabsRightBottom.add(self.fTriggerInfo, text=TEXT['tabTriggerInfo'])
        self.nTabsRightBottom.add(self.fCeInfo, text=TEXT['tabEffectInfo'], state="disabled")
        self.nTabsRightBottom.add(self.fUnitInfo, text=TEXT['tabUnitInfo'])

        self.nTabsRightTop.pack(fill=BOTH, expand=True, padx=0, pady=self.dpi((0, 5)))
        self.nTabsRightBottom.pack(fill=BOTH, expand=True, padx=0, pady=self.dpi((5, 0)))

    def __createMenu(self):
        self.menuRoot = ttk.Menu(self.root)
        self.menuFile = ttk.Menu(self.menuRoot, tearoff=0)
        self.menuRoot.add_cascade(label=TEXT['menuFile'], menu=self.menuFile)
        self.menuFile.add_command(label=TEXT['menuNew'], command=self.newScenario)
        self.menuFile.add_command(label=TEXT['menuOpen'], accelerator='Ctrl+O', command=self.openScenarioAskFile)
        self.menuFile.add_command(label=TEXT['menuReload'], accelerator='Ctrl+R', command=self.openScenario)
        self.menuFile.add_command(label=TEXT['menuSave'], accelerator='Ctrl+S', command=self.saveScenario)
        self.menuFile.entryconfig(TEXT['menuSave'], state='normal' if self.options.enableOverwritingSource.get() else 'disabled')
        self.menuFile.add_command(label=TEXT['menuSaveAs'], accelerator='Ctrl+Shift+S', command=self.saveAsScenario)
        self.menuFile.add_command(label=TEXT['menuClose'], command=self.closeScenario)
        self.menuFile.add_separator()
        self.menuFile.add_command(label=TEXT['menuExit'], command=self.windowClose)
        self.menuEdit = ttk.Menu(self.menuRoot, tearoff=0)
        self.menuRoot.add_cascade(label=TEXT['menuEdit'], menu=self.menuEdit)
        self.menuEdit.add_command(label=TEXT['menuExportAllTriggerToText'], command=self.exportTriggerToText)
        self.menuEdit.add_command(label=TEXT['menuImportAllTriggerFromText'], command=self.importTriggerFromText)
        self.menuEdit.add_separator()
        self.menuEdit.add_command(label=TEXT['menuExportTriggerToText'], command=self.exportSelTriggerToText)
        self.menuEdit.add_command(label=TEXT['menuImportTriggerFromText'], command=self.addTriggerFromText)
        self.menuEdit.add_separator()
        self.menuEdit.add_command(label=TEXT['menuExportAllText'], command=lambda: print('ExportAllText'), state='disabled')
        self.menuEdit.add_command(label=TEXT['menuImportText'], command=lambda: print('ImportText'), state='disabled')
        self.menuLanguage = ttk.Menu(self.menuRoot, tearoff=0)
        self.menuRoot.add_cascade(label=TEXT['menuLanguage'], menu=self.menuLanguage)
        for language in LOCALIZATION_DEFINES:
            self.menuLanguage.add_command(label=language['name'], command=lambda code=language['code']: self.changeLanguage(code))
        self.menuAbout = ttk.Menu(self.menuRoot, tearoff=0)
        self.menuRoot.add_cascade(label=TEXT['menuHelp'], menu=self.menuAbout)
        self.menuAbout.add_command(label=TEXT['menuLogs'], command=self.__showLogs)
        self.menuAbout.add_separator()
        self.menuAbout.add_command(label=TEXT['menuHomePage'], command=self.__accessHomepage)
        self.menuAbout.add_command(label=TEXT['menuAbout'], command=self.__showAbout)

        self.root.config(menu=self.menuRoot)

    def __createStatusBar(self):
        self.fStatusBar = ttk.Frame(self.main)
        self.fStatusBar.pack(side=BOTTOM, fill=X)
        self.varStatusBarText = ttk.StringVar()
        self.lStatusBar = ttk.Label(self.fStatusBar, textvariable=self.varStatusBarText, anchor=W)
        self.lStatusBar.pack(side=LEFT, fill=Y)
        self.statusBarMsgBottom = ''
        self.statusBarMsgTop = ''

    def __bindGlobalKeys(self):
        self.root.bind_all("<Control-o>", lambda e: self.openScenarioAskFile())
        self.root.bind_all("<Control-O>", lambda e: self.openScenarioAskFile())
        self.root.bind_all("<Control-r>", lambda e: self.openScenario())
        self.root.bind_all("<Control-R>", lambda e: self.openScenario())
        self.root.bind_all("<Control-s>", lambda e: self.saveScenario())
        self.root.bind_all("<Control-S>", lambda e: self.saveScenario())
        self.root.bind_all("<Control-Shift-s>", lambda e: self.saveAsScenario())
        self.root.bind_all("<Control-Shift-S>", lambda e: self.saveAsScenario())

    # endregion Creation

    # region Methods

    def dpi(self, value:int | tuple[int, ...]):
        if type(value) == tuple:
            return tuple(int(self.scaleFactor / 100 * v) for v in value)
        elif type(value) == int:
            return int(self.scaleFactor / 100 * value)

    def reinitialize(self):
        """Reinitialize the main frame to apply language changes"""
        self.main.destroy()
        self.__createMainWindow()

        self.root.title(f"{TEXT['titleMainWindow']} - [{self.windowTitleTail}]")
        self.main.update_idletasks()
        self.readScenario()

    def changeLanguage(self, lang: str) -> None:
        """Change language setting and apply"""
        try:
            loadLocalizedText(workDir, lang)
        except ResourcesFileError as e:
            messagebox.showerror('File Error', 'Fail to change language due to:\n\n{0}'.format(e.args[0]), icon='error')
        else:
            self.reinitialize()

    def statusBarMessage(self, msg: str, update=False, layer: Literal['bottom', 'top'] = 'bottom') -> None:
        if layer == 'bottom':
            self.statusBarMsgBottom = msg
        else:
            self.statusBarMsgTop = msg
        if self.statusBarMsgTop == '':
            self.varStatusBarText.set(self.statusBarMsgBottom)
        else:
            self.varStatusBarText.set(self.statusBarMsgTop)
        if update == True:
            self.lStatusBar.update_idletasks()

    def __accessHomepage(self):
        webOpen('https://github.com/MegaDusknoir/AoE2TriggerCraft2')

    def __clearLogWidget(self):
        self.tLog.text.configure(state='normal')
        self.tLog.text.delete(1.0, END)
        self.tLog.text.configure(state='disabled')

    def __createLogWindow(self):
        self.tLog = ScrolledText(self.wndLog)
        self.tLog.text.configure(state='disabled')
        self.tLog.pack(side=TOP, fill=BOTH, expand=True, padx=self.dpi(10), pady=self.dpi(10))
        btnClrLog = ttk.Button(self.wndLog, text=TEXT['btnClearLogs'], width=self.dpi(40), command=self.__clearLogWidget)
        btnClrLog.pack(side=TOP, anchor=E, expand=False, padx=self.dpi(20), pady=self.dpi(10))

    def __showLogs(self):
        if self.wndLog is not None and ttk.Toplevel.winfo_exists(self.wndLog):
            self.wndLog.lift()
            self.wndLog.focus_set()
        else:
            self.wndLog = ttk.Toplevel(TEXT['titleLogs'], master=self.main)
            self.wndLog.geometry(f'{self.dpi(1200)}x{self.dpi(800)}')
            self.__createLogWindow()
            self.wndLog.focus_set()

    def centerWindowGeometry(self, window: ttk.Toplevel, width, height, location=0.5):
        ws = self.main.winfo_screenwidth()
        hs = self.main.winfo_screenheight()
        x = (ws - width) * location
        y = (hs - height) * location
        window.geometry('%dx%d+%d+%d' % (width, height, x, y))

    def __showAbout(self):
        self.wndAbout = ttk.Toplevel(TEXT['titleAbout'], master=self.main, transient=self.main)
        self.centerWindowGeometry(self.wndAbout, self.dpi(460), self.dpi(140), location=0.3)
        self.wndAbout.resizable(False, False)
        lblAboutImage = ttk.Label(self.wndAbout, image=self.imgAbout)
        lblAboutImage.pack(side=LEFT, padx=self.dpi((10, 0)))
        lblAboutTitle = ttk.Label(self.wndAbout, text=TEXT['textAboutTitle'],
                                  font=(tkfont.nametofont('TkDefaultFont').cget('family'), 16, 'bold'))
        lblAboutTitle.pack(padx=self.dpi(20), pady=self.dpi((10, 10)))
        lblAbout = ttk.Label(self.wndAbout, text=TEXT['textAbout'])
        lblAbout.pack(side=TOP, pady=self.dpi((0, 6)))
        lblAboutRelease = ttk.Label(self.wndAbout, text=TEXT['textAboutRelease'].format(VERSION_STRING))
        lblAboutRelease.pack(side=TOP)
        lblAboutPoweredBy = ttk.Label(self.wndAbout, text=TEXT['textAboutPoweredBy'])
        lblAboutPoweredBy.pack(side=BOTTOM, pady=(0, self.dpi(10)))
        self.wndAbout.grab_set()

    def exportTriggerToText(self):
        if not self.openedScenPath:
            initialFile = 'default.json'
        else:
            scenFolder, scenName = os.path.split(self.openedScenPath)
            scenStem, scenExt = os.path.splitext(scenName)
            initialFile = scenStem + '.json'
        saveFilePath = asksaveasfilename(title=TEXT['titleSelectSaveTriggerJson'],
                                         initialfile=initialFile,
                                         filetypes=[('JSON', '*.json')])
        if not saveFilePath:
            return
        jsonName, jsonExt = os.path.splitext(saveFilePath)
        if not jsonExt and not os.path.isfile(saveFilePath):
            saveFilePath += '.json'

        tDump = TriggerJsonIO.export(self.triggerManager)
        with open(saveFilePath, 'w', encoding='utf-8') as fp:
            json.dump(tDump, fp, indent=4, ensure_ascii=False)
        self.statusBarMessage(TEXT['noticeTriggerJsonSaved'])

    def importTriggerFromText(self):
        openFilePath = askopenfilename(title=TEXT['titleSelectTriggerJson'],
                                       filetypes=[('JSON', '*.json'), (TEXT['typeNameAll'], '*')])
        triggersDump = None
        if openFilePath == '':
            return
        with open(openFilePath, 'r', encoding='utf-8') as f:
            try:
                triggersDump = json.load(f)
            except (json.decoder.JSONDecodeError, UnicodeDecodeError) as e:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageJsonDecodeError'])
            except Exception as e:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageError'].format(e))
                raise e
        if triggersDump:
            try:
                TriggerJsonIO.restore(self.triggerManager, triggersDump)
            except TriggerJsonIO.TriggerJsonInvalidError:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageJsonSchemaError'])
            except TriggerJsonIO.TriggerJsonNotRestorableError:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageJsonNotRestorableError'])
            except Exception as e:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageError'].format(e))
                raise e
            else:
                self.fTEditor.loadTrigger()
                self.statusBarMessage(TEXT['noticeTriggerJsonRestored'])

    def exportSelTriggerToText(self):
        valueRange = self.fTEditor.getRangeValue()
        if type(valueRange) == str:
            messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageValueRangeInvalid'].format(valueRange))
            return
        displayIdBegin, displayIdEnd, displayIdTarget = valueRange

        if not self.openedScenPath:
            initialFile = 'default.json'
        else:
            scenFolder, scenName = os.path.split(self.openedScenPath)
            scenStem, scenExt = os.path.splitext(scenName)
            initialFile = scenStem + '.json'
        saveFilePath = asksaveasfilename(title=TEXT['titleSelectSaveTriggerJson'],
                                         initialfile=initialFile,
                                         filetypes=[('JSON', '*.json')])
        if not saveFilePath:
            return
        jsonName, jsonExt = os.path.splitext(saveFilePath)
        if not jsonExt and not os.path.isfile(saveFilePath):
            saveFilePath += '.json'

        tDump = TriggerJsonIO.export(self.triggerManager, displayIdBegin, displayIdEnd)
        with open(saveFilePath, 'w', encoding='utf-8') as fp:
            json.dump(tDump, fp, indent=4, ensure_ascii=False)
        self.statusBarMessage(TEXT['noticeTriggerJsonSaved'])

    def addTriggerFromText(self):
        openFilePath = askopenfilename(title=TEXT['titleSelectTriggerJson'],
                                       filetypes=[('JSON', '*.json'), (TEXT['typeNameAll'], '*')])
        triggersDump = None
        if openFilePath == '':
            return
        with open(openFilePath, 'r', encoding='utf-8') as f:
            try:
                triggersDump = json.load(f)
            except (json.decoder.JSONDecodeError, UnicodeDecodeError) as e:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageJsonDecodeError'])
            except Exception as e:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageError'].format(e))
                raise e
        if triggersDump:
            try:
                TriggerJsonIO.append(self.triggerManager, triggersDump)
            except TriggerJsonIO.TriggerJsonInvalidError:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageJsonSchemaError'])
            except Exception as e:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageError'].format(e))
                raise e
            else:
                self.fTEditor.loadTrigger()
                self.statusBarMessage(TEXT['noticeTriggerJsonAdded'])

    def itemSelect(self, event):
        curItem = self.fTEditor.tvTriggerList.focus()
        nodeType = self.fTEditor.tvTriggerList.itemType(curItem)
        if nodeType == 'trigger':
            self.nTabsRightBottom.tab(self.fCeInfo, state="disabled")
            self.nTabsRightBottom.tab(self.fTriggerInfo, state="normal")
            self.nTabsRightBottom.select(self.fTriggerInfo)
            triggerId = self.fTEditor.tvTriggerList.getNodeId(curItem)[0]
            trigger = self.triggerManager.get_trigger(triggerId)
            self.fTriggerInfo.loadTriggerAttributes(trigger)
        elif nodeType == 'condition' or nodeType == 'effect':
            self.nTabsRightBottom.tab(self.fTriggerInfo, state="disabled")
            self.nTabsRightBottom.tab(self.fCeInfo, state="normal")
            self.nTabsRightBottom.select(self.fCeInfo)
            parent = self.fTEditor.tvTriggerList.parent(curItem)
            triggerId = self.fTEditor.tvTriggerList.getNodeId(parent)[0]
            trigger = self.triggerManager.get_trigger(triggerId)
            if nodeType == 'condition':
                self.nTabsRightBottom.tab(self.fCeInfo, text=TEXT['tabConditionInfo'])
                self.fCeInfo.wEType.label.grid_forget()
                self.fCeInfo.wEType.grid_forget()
                self.fCeInfo.wCType.gridAttribute(0, 0)
                condition = trigger.conditions[self.fTEditor.tvTriggerList.getNodeId(curItem)[0]]
                self.fCeInfo.loadConditionAttributes(condition)
            else:
                self.nTabsRightBottom.tab(self.fCeInfo, text=TEXT['tabEffectInfo'])
                self.fCeInfo.wCType.label.grid_forget()
                self.fCeInfo.wCType.grid_forget()
                self.fCeInfo.wEType.gridAttribute(0, 0)
                effect = trigger.effects[self.fTEditor.tvTriggerList.getNodeId(curItem)[0]]
                self.fCeInfo.loadEffectAttributes(effect)

    def askSaveScenario(self) -> bool:
        """Return True if operation continue, False if break"""
        replySave =  messagebox.askyesnocancel(title=TEXT['titleAskSaveScenario'],
                                               message=TEXT['messageAskSaveScenario'].format(),
                                               icon='question',
                                               default='cancel')
        if replySave is True:
            if self.saveAsScenario() != '':
                return True
            else:
                return False
        elif replySave is False:
            return True
        else:
            return False

    def __saveScen(self, path):
        try:
            self.activeScenario.write_to_file(path)
        except OverflowError as e:
            if isinstance(e.args[0], str) and e.args[0] == 'int too big to convert':
                messagebox.showerror(title=TEXT['titleSavefailed'],
                                     message=TEXT['messageSavefailed'].format(TEXT['messageSavefailedByBadInteger']))
            else:
                messagebox.showerror(title=TEXT['titleSavefailed'], message=TEXT['messageSavefailed'].format(e))
                raise e
        except Exception as e:
            messagebox.showerror(title=TEXT['titleSavefailed'], message=TEXT['messageSavefailed'].format(e))
            raise e
        else:
            self.statusBarMessage(TEXT['noticeScenarioSaved'])

    def saveScenario(self, path=None):
        if path == None:
            path = self.openedScenPath
        if path == '':
            newFile = self.saveAsScenario()
            if newFile != '':
                self.openedScenPath = newFile
                scenFolder, scenName = os.path.split(self.openedScenPath)
                self.windowTitleTail = scenName
                self.root.title(f"{TEXT['titleMainWindow']} - [{self.windowTitleTail}]")
        else:
            self.__saveScen(path)

    def saveAsScenario(self) -> str:
        saveFilePath = asksaveasfilename(title=TEXT['titleSelectSaveScenario'],
                                         filetypes=[(TEXT['typeNameScenario'], '*.aoe2scenario')])
        if saveFilePath != '':
            scenName, scenExt = os.path.splitext(saveFilePath)
            if scenExt == '' and os.path.isfile(saveFilePath) == False:
                saveFilePath += '.aoe2scenario'
            self.__saveScen(saveFilePath)
        return saveFilePath

    def openScenario(self, path=None):
        if path == None:
            path = self.openedScenPath
        if path == '':
            return
        scenFolder, scenName = os.path.split(path)
        scenStem, scenExt = os.path.splitext(scenName)
        print(scenFolder, scenStem, scenExt)
        self.statusBarMessage(TEXT['noticeScenarioLoading'], update=True)
        try:
            self.logCatch = self.__catchScenLoadProgress
            self.activeScenario:AoE2DEScenario = AoE2DEScenario.from_file(path)
        except UnknownScenarioStructureError as e:
            def checkVersionNotSupportedRaise(e: UnknownScenarioStructureError):
                """Catch ASP version not supported exception."""
                if not isinstance(e.args[0], str):
                    return False
                parsed = parse("The version {0}:{1} is not supported by AoE2ScenarioParser. :(", e.args[0])
                if not parsed:
                    return False
                strScenVer: str = parsed.fixed[1]
                strToolVer = f'{AoE2DEScenario.LATEST_VERSION[0]}.{AoE2DEScenario.LATEST_VERSION[1]}'
                vMain, vSub = ((int(i) if i.isdigit() else 0) for i in strScenVer.split('.'))
                vscen = vMain * 65536 + vSub
                vtool = AoE2DEScenario.LATEST_VERSION[0] * 65536 + AoE2DEScenario.LATEST_VERSION[1]
                if vscen > vtool:
                    messagebox.showerror(title=TEXT['titleOpenfailed'],
                                        message=TEXT['messageOpenfailed'].format( \
                                            TEXT['messageOpenfailedByNewerVersion'].format(strScenVer, strToolVer)))
                else:
                    messagebox.showerror(title=TEXT['titleOpenfailed'],
                                        message=TEXT['messageOpenfailed'].format( \
                                            TEXT['messageOpenfailedByEarlyVersion'].format(strScenVer, strToolVer)))
                return True

            if not checkVersionNotSupportedRaise(e):
                messagebox.showerror(title=TEXT['titleOpenfailed'], message=TEXT['messageOpenfailed'].format(e))
        except UnsupportedVersionError as e:
            def checkTriggerNotSupportedRaise(e: UnsupportedVersionError):
                """Catch ASP trigger not supported exception."""
                if not isinstance(e.args[0], str):
                    return False
                parsed = parse(
                    "\n\nScenario version: [{0}] with trigger version: [{1}] cannot be supported. :(\n"
                    "More context on Discord: https://discord.com/channels/866955546182942740/877085102201536553/1372708645711777843",
                    e.args[0])
                if not parsed:
                    return False
                strScenVer: str = parsed.fixed[0]
                strTriggerVer: str = parsed.fixed[1]
                messagebox.showerror(title=TEXT['titleOpenfailed'],
                                     message=TEXT['messageOpenfailed'].format( \
                                         TEXT['messageOpenfailedByEarlyTrigger'].format(strScenVer, strTriggerVer)))
                return True

            if not checkTriggerNotSupportedRaise(e):
                messagebox.showerror(title=TEXT['titleOpenfailed'], message=TEXT['messageOpenfailed'].format(e))
        except Exception as e:
            messagebox.showerror(title=TEXT['titleOpenfailed'], message=TEXT['messageOpenfailed'].format(e))
            raise e
        else:
            self.windowTitleTail = scenName
            self.openedScenPath = path
            self.triggerManager = self.activeScenario.trigger_manager
            self.readScenario()
        finally:
            self.logCatch = None

    def openScenarioAskFile(self):
        openFilePath = askopenfilename(title=TEXT['titleSelectScenario'],
                                       filetypes=[(TEXT['typeNameScenario'], '*.aoe2scenario'), (TEXT['typeNameAll'], '*')])
        self.openScenario(openFilePath)

    def readScenario(self):
        self.root.title(f"{TEXT['titleMainWindow']} - [{self.windowTitleTail}]")
        self.fMetaViewTab.loadMeta()
        self.fTEditor.loadTrigger()
        self.fMapViewTab.loadMapView()
        self.fUEditor.updatePlayerList()
        self.statusBarMessage(TEXT['noticeScenarioLoaded'])

    def newScenario(self):
        if self.openedScenPath == '':
            self.generateDefaultScenario()
        elif self.askSaveScenario():
            self.generateDefaultScenario()

    def closeScenario(self):
        if self.openedScenPath == '':
            self.generateDefaultScenario()
        elif self.askSaveScenario():
            self.generateDefaultScenario()

    def getTriggerIcon(self, trigger:Trigger) -> PIL.ImageTk.PhotoImage:
        if trigger.enabled == 1:
            if trigger.looping == 0:
                triggerImage = self.imgTriggerEnabled
            else:
                triggerImage = self.imgTriggerEnabledLoop
        else:
            if trigger.looping == 0:
                triggerImage = self.imgTriggerDisabled
            else:
                triggerImage = self.imgTriggerDisabledLoop
        return triggerImage

    # endregion Methods


import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dark', help='Darkly mode', nargs='?', default=False)
    args = parser.parse_args()
    if args.dark != False:
        theme = 'darkly'
    else:
        theme = 'litera'
    window = TCWindow(theme)
    window.mainloop()