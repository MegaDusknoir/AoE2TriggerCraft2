
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
from Util import DebugTimeCount, ScenarioVersion
from _prebuild.version import VERSION_STRING
from _prebuild.AoE2TC_icon import Icon
from _prebuild.OptionsDefine import OPTIONS_DEFINE
from CeAttributesManager import CeAttributes

if getattr(sys, 'frozen', False): # True if PyInstaller packed
    workDir = os.path.dirname(sys.executable)
else:
    workDir = os.path.dirname(os.path.abspath(__file__))

ASPSettings.ENABLE_XS_CHECK_INTEGRATION = False
ASPSettings.ALLOW_OVERWRITING_SOURCE = True
# ASPSettings.ALLOW_DIRTY_RETRIEVER_OVERWRITE = True

DEFAULT_VERSION = ScenarioVersion(AoE2DEScenario.LATEST_VERSION)

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
        'execute_on_load',
        # 'conditions',
        # 'effects',
    ]

    effectTextAttributesSet = [
        'message',
        'message_option1',
        'message_option2',
    ]

    class TriggerJsonNotRestorableError(Exception):
        pass

    class TriggerJsonInvalidError(Exception):
        pass

    @classmethod
    def assignVersion(cls, version: ScenarioVersion):
        if version < ScenarioVersion('1.55') and 'execute_on_load' in cls.triggerAttributesSet:
            cls.triggerAttributesSet.remove('execute_on_load')

    @classmethod
    def export(cls, tm: TriggerManager, begin:int=None, end:int=None) -> dict:
        if begin is None:
            begin = 0
        if end is None:
            end = len(tm.triggers)

        exportTriggerOrder = tm.trigger_display_order[begin:end]
        selectTriggersId = exportTriggerOrder.copy()
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
                for attr in CeAttributes.condition().get(condition.condition_type, []):
                    conditionDict[attr] = getattr(condition, attr)
                triggerDict['conditions'].append(conditionDict)
            for effect in trigger.effects:
                effectDict = {'effect_type': effect.effect_type}
                for attr in CeAttributes.effect().get(effect.effect_type, []):
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
                for attr in CeAttributes.condition().get(condition.condition_type, []):
                    setattr(condition, attr, conditionDict[attr])
            for effectDict in triggerDict['effects']:
                effect = trigger.new_effect.none()
                effect.effect_type = effectDict['effect_type']
                for attr in CeAttributes.effect().get(effect.effect_type, []):
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
                for attr in CeAttributes.condition().get(condition.condition_type, []):
                    setattr(condition, attr, conditionDict[attr])
            for effectDict in triggerDict['effects']:
                effect = trigger.new_effect.none()
                effect.effect_type = effectDict['effect_type']
                for attr in CeAttributes.effect().get(effect.effect_type, []):
                    setattr(effect, attr, effectDict[attr])
            trigger.condition_order = triggerDict['condition_order']
            trigger.effect_order = triggerDict['effect_order']
        tm.trigger_display_order = obj['trigger_display_order']

    @classmethod
    def textExport(cls, tm: TriggerManager) -> list:
        triggersList = []
        for t_display_id in range(len(tm.triggers)):
            trigger = tm.triggers[tm.trigger_display_order[t_display_id]]
            triggerDict = {}
            if trigger.display_as_objective != 0:
                triggerDict['description'] = getattr(trigger, 'description')
            if trigger.display_on_screen != 0:
                triggerDict['short_description'] = getattr(trigger, 'short_description')
            effectsList = []
            for e_display_id in range(len(trigger.effects)):
                effect = trigger.effects[trigger.effect_order[e_display_id]]
                effectDict = {}
                for attr in cls.effectTextAttributesSet:
                    if attr in CeAttributes.effect().get(effect.effect_type, []) \
                        and effect.effect_type not in (55, 56, 81, 82, 83) \
                        and getattr(effect, attr).strip() != '':
                            effectDict[attr] = getattr(effect, attr)
                if len(effectDict) != 0:
                    effectsList.append({'effect_id': trigger.effect_order[e_display_id]} | effectDict)
            if len(effectsList) != 0:
                triggerDict['effects'] = effectsList
            if len(triggerDict) != 0:
                triggersList.append({'trigger_id': trigger.trigger_id, 'name': trigger.name} | triggerDict)
        return triggersList

    @classmethod
    def textPreimportCheck(cls, tm: TriggerManager, obj: list[dict]) -> bool:
        # expecting obj is validated
        for tDict in obj:
            if tDict['trigger_id'] >= len(tm.triggers):
                return False
            trigger: Trigger = tm.triggers[tDict['trigger_id']]
            for effectDict in tDict.get('effects', []):
                if effectDict['effect_id'] >= len(trigger.effects):
                    return False
                effect: Effect = trigger.effects[effectDict['effect_id']]
                for attr in cls.effectTextAttributesSet:
                    if attr in effectDict:
                        if attr not in CeAttributes.effect().get(effect.effect_type, []):
                            return False
        return True

    @classmethod
    def textImport(cls, tm: TriggerManager, obj: list[dict]):
        # expecting obj is validated
        for tDict in obj:
            trigger: Trigger = tm.triggers[tDict['trigger_id']]
            for attr in ('description', 'short_description'):
                if attr in tDict:
                    setattr(trigger, attr, tDict[attr])
            for effectDict in tDict.get('effects', []):
                effect: Effect = trigger.effects[effectDict['effect_id']]
                for attr in cls.effectTextAttributesSet:
                    if attr in effectDict:
                        setattr(effect, attr, effectDict[attr])

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

    def __init__(self, scen='', theme='darkly') -> None:
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

        self.root = ttk.Window('', iconphoto=None)
        self.options = GlobalOptions(workDir)
        try:
            loadLocalizedText(workDir, self.options.language.get())
        except ResourcesFileError as e:
            messagebox.showerror('File Error', 'The application can not startup due to:\n\n{0}'.format(e.args[0]), icon='error')
            sys.exit()

        self.root.title(TEXT['titleMainWindow'])
        self.root.geometry(f'{self.dpi(1280)}x{self.dpi(720)}')
        self.root.protocol('WM_DELETE_WINDOW', self.windowClose)
        self.theme = theme
        if scen != '':
            self.initialOpen = os.path.normpath(scen)
        else:
            self.initialOpen = ''
        self.activeScenario: AoE2DEScenario = None
        self.restartToLoad = None
        if self.initialOpen == '':
            self.editorVersion = DEFAULT_VERSION
        else:
            try:
                self.editorVersion = ScenarioVersion(self.readScenarioVersion(self.initialOpen))
            except:
                self.editorVersion = DEFAULT_VERSION

        self.style = ttk.Style()
        self.style.theme_use(self.theme)
        if self.theme in ('darkly'):
            self.tvLineColoring = self.style.colors.inputbg
        else:
            self.tvLineColoring = self.style.colors.active

        self.__loadImages()

        self.wndLog = None
        self.__createMainWindow()

        end_init = time.time()
        print(f'Initialize used {end_init - start_init:.3f} seconds')

    def windowClose(self):
        if self.openedScenPath == '':
            self.root.destroy()
        elif self.askSaveScenario():
            self.root.destroy()

    class LoadingDifferentVersionException(Exception):
        pass

    def mainloop(self):
        """Call the mainloop."""
        with CreateIcon() as iconPath:
            self.root.iconbitmap(default=iconPath)

        # Show window before take time to load a scenario
        self.root.update()
        if self.initialOpen == '':
            self.generateDefaultScenario()
        else:
            self.openScenario(self.initialOpen)
            if self.activeScenario == None:
                if DEFAULT_VERSION != self.editorVersion:
                    self.restartToLoad = ''
                    self.root.destroy()
                    raise self.LoadingDifferentVersionException(self.restartToLoad)
                self.generateDefaultScenario()
        with CreateIcon() as iconPath:
            self.imgAbout = self.__loadImage(iconPath, self.dpi((128, 128)))

        self.root.mainloop()
        if self.restartToLoad != None:
            raise self.LoadingDifferentVersionException(self.restartToLoad)

    def generateDefaultScenario(self):
        if DEFAULT_VERSION != self.editorVersion:
            self.restartToLoad = ''
            self.root.destroy()
            return
        ASPSettings.PRINT_STATUS_UPDATES = False
        self.activeScenario = AoE2DEScenario.from_default()
        ASPSettings.PRINT_STATUS_UPDATES = True
        print('Loaded default scenario')
        CeAttributes.setVersion(self.activeScenario.scenario_version)
        TriggerJsonIO.assignVersion(self.editorVersion)
        self.openedScenPath = ''
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
        self.style.configure('ceTypes.TCombobox', postoffset=self.dpi((0, 0, 80, 0)))
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
        self.style.configure('cbWithDescription.TCheckbutton', font=(defaultFont.cget('family'), 8))

        self.main = ttk.Frame(self.root, padding=self.dpi((10,10,10,5)))
        self.__createStatusBar()
        self.__createPanedWindow()
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
        self.options.enableOverwritingSource.trace_add('write', lambda *_: \
            self.menuFile.entryconfig(TEXT['menuSave'], state='normal' if self.options.enableOverwritingSource.get() else 'disabled'))
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
        self.menuEdit.add_command(label=TEXT['menuExportAllText'], command=self.exportAllText)
        self.menuEdit.add_command(label=TEXT['menuImportText'], command=self.importText)
        self.menuEdit.add_separator()
        self.menuEdit.add_command(label=TEXT['menuPreferences'], command=self.__modifyPreferences)
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

    def __modifyPreferences(self):
        def on_confirm():
            for option in self.varPreferences:
                getattr(self.options, option).set(self.varPreferences[option].get())
            self.options.saveAll()
            _close_dialog(wndPref)

        def _close_dialog(dialog: ttk.Toplevel):
            dialog.grab_release()
            dialog.destroy()
            del self.varPreferences

        wndPref = ttk.Toplevel(TEXT['titlePreferences'], master=self.main)
        wndPref.withdraw()
        wndPref.grab_set()
        wndPref.protocol("WM_DELETE_WINDOW", lambda: _close_dialog(wndPref))

        fSettings = ttk.Frame(wndPref)
        self.varPreferences = {}
        for option, args in OPTIONS_DEFINE.items():
            if args['showInPreferences']:
                VType = type(getattr(self.options, option))
                self.varPreferences[option] = VType(value=getattr(self.options, option).get())
                fOption = ttk.Frame(fSettings)
                match args['type']:
                    case 'string' | 'integer' | 'float':
                        lDescription = ttk.Label(fOption, text=TEXT['descPreferences'][option],
                                                 font=(tkfont.nametofont('TkDefaultFont').cget('family'), 8))
                        lDescription.pack(side=TOP, anchor=W)
                        wOption = ttk.Entry(fOption, textvariable=self.varPreferences[option])
                        wOption.pack(side=TOP, anchor=W)
                    case 'boolean':
                        wOption = ttk.Checkbutton(fOption, text=TEXT['descPreferences'][option], variable=self.varPreferences[option],
                                                  style='cbWithDescription.TCheckbutton')
                        wOption.pack(side=TOP, anchor=W)
                    case _:
                        continue
                lOption = ttk.Label(fSettings, text=TEXT['namePreferences'][option])
                lOption.grid(column=args['grid'][0], row=args['grid'][1]*2, columnspan=args['columnSpan'], sticky=W,
                             pady=self.dpi((0,4)))
                fOption.grid(column=args['grid'][0], row=args['grid'][1]*2+1, columnspan=args['columnSpan'], sticky=W,
                             padx=self.dpi((10,0)), pady=self.dpi((0,14)))
        fSettings.pack(padx=self.dpi(10), pady=self.dpi(10), fill=X)

        fConfirmCancel = ttk.Frame(wndPref)
        ttk.Button(fConfirmCancel, text=TEXT['btnConfirm'], command=on_confirm) \
            .pack(side=LEFT, fill=X, expand=YES, padx=self.dpi(40))
        ttk.Button(fConfirmCancel, text=TEXT['btnCancel'], bootstyle=ttk.SECONDARY, command=lambda: _close_dialog(wndPref)) \
            .pack(side=LEFT, fill=X, expand=YES, padx=self.dpi(40))
        fConfirmCancel.pack(side=BOTTOM, fill=X, pady=self.dpi((0,10)))

        wndPref.update_idletasks()
        self.centerWindowGeometry(wndPref, wndPref.winfo_width(), wndPref.winfo_height(), 0.4)
        wndPref.resizable(False, False)
        wndPref.deiconify()
        wndPref.transient(self.main)

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
        self.root.bind_all("<Control-s>", lambda e: self.saveScenario() if self.options.enableOverwritingSource.get() else None)
        self.root.bind_all("<Control-S>", lambda e: self.saveScenario() if self.options.enableOverwritingSource.get() else None)
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
            self.options.setOption('language', lang)
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

    def exportAllText(self):
        if not self.openedScenPath:
            initialFile = 'default.json'
        else:
            scenFolder, scenName = os.path.split(self.openedScenPath)
            scenStem, scenExt = os.path.splitext(scenName)
            initialFile = scenStem + '.json'
        initialFile = 'text_' + initialFile
        saveFilePath = asksaveasfilename(title=TEXT['titleSelectSaveTextJson'],
                                         initialfile=initialFile,
                                         filetypes=[('JSON', '*.json')])
        if not saveFilePath:
            return
        _, fileExt = os.path.splitext(saveFilePath)
        if not fileExt and not os.path.isfile(saveFilePath):
            saveFilePath += '.json'

        tTrigger = TriggerJsonIO.textExport(self.triggerManager)
        tPName = []
        for p in range(1, self.activeScenario.player_manager.active_players + 1):
            tPName.append(self.activeScenario.player_manager.players[p].tribe_name)
        tMsgs = {}
        for m in TEXT['messageNames'].keys():
            tMsgs[m] = getattr(self.activeScenario.message_manager, m)
        tDump = {'messages': tMsgs, 'players': tPName, 'triggers': tTrigger}
        try:
            with open(saveFilePath, 'w', encoding='utf-8') as fp:
                json.dump(tDump, fp, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageError'].format(e))
        else:
            self.statusBarMessage(TEXT['noticeTextJsonSaved'])

    def importText(self):
        schema = {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "object",
                    "properties": {
                        "instructions": {
                            "type": "string"
                        },
                        "hints": {
                            "type": "string"
                        },
                        "scouts": {
                            "type": "string"
                        },
                        "victory": {
                            "type": "string"
                        },
                        "loss": {
                            "type": "string"
                        },
                        "history": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "instructions",
                        "hints",
                        "scouts",
                        "victory",
                        "loss",
                        "history"
                    ],
                    "additionalProperties": False
                },
                "players": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "minItems": 1,
                    "maxItems": 8
                },
                "triggers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "trigger_id": {
                                "type": "integer"
                            },
                            "name": {
                                "type": "string"
                            },
                            "description": {
                                "type": "string"
                            },
                            "short_description": {
                                "type": "string"
                            },
                            "effects": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "effect_id": {
                                            "type": "integer"
                                        },
                                        "message": {
                                            "type": "string"
                                        },
                                        "message_option1": {
                                            "type": "string"
                                        },
                                        "message_option2": {
                                            "type": "string"
                                        }
                                    },
                                    "required": [
                                        "effect_id"
                                    ],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": [
                            "trigger_id"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            "required": [
                "messages",
                "players",
                "triggers"
            ],
            "additionalProperties": False
        }

        openFilePath = askopenfilename(title=TEXT['titleSelectTextJson'],
                                       filetypes=[('JSON', '*.json'), (TEXT['typeNameAll'], '*')])
        textDump = None
        if openFilePath == '':
            return
        with open(openFilePath, 'r', encoding='utf-8') as f:
            try:
                textDump = json.load(f)
            except (json.decoder.JSONDecodeError, UnicodeDecodeError) as e:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageJsonDecodeError'])
            except Exception as e:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageError'].format(e))
        if textDump:
            try:
                jsonschema.validate(textDump, schema)
            except jsonschema.ValidationError as e:
                messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageJsonSchemaError'])
            else:
                if not TriggerJsonIO.textPreimportCheck(self.triggerManager, textDump['triggers']):
                    messagebox.showerror(title=TEXT['titleError'], message=TEXT['messageTextJsonNotMatchError'])
                    return
                for k, v in textDump['messages'].items():
                    setattr(self.activeScenario.message_manager, k, v)
                for i, name in enumerate(textDump['players']):
                    self.activeScenario.player_manager.players[i + 1].tribe_name = name
                TriggerJsonIO.textImport(self.triggerManager, textDump['triggers'])
                self.fTEditor.loadTrigger()
                self.statusBarMessage(TEXT['noticeTextJsonImported'])

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

    def readScenarioVersion(self, path):
        with open(path, 'rb') as f:
            version = f.read(4).decode('ASCII')
        return version

    def unsupportedVersionHelper(self, versionStr: str):
        try:
            version = ScenarioVersion(versionStr)
        except ValueError:
            return None
        if version > DEFAULT_VERSION:
            return 'Newer'
        else:
            return 'Early'

    def openScenario(self, path=None):
        if path == None:
            path = self.openedScenPath
        if path == '':
            return
        scenFolder, scenName = os.path.split(path)
        scenStem, scenExt = os.path.splitext(scenName)
        # print(scenFolder, scenStem, scenExt)
        try:
            scenVersion = self.readScenarioVersion(path)
        except (FileNotFoundError, PermissionError) as e:
            messagebox.showerror(title=TEXT['titleOpenfailed'], message=TEXT['messageOpenfailed'].format(e))
            return
        if not CeAttributes.isSupportedVersion(scenVersion):
            v = self.unsupportedVersionHelper(scenVersion)
            if v == 'Newer':
                messagebox.showerror(title=TEXT['titleOpenfailed'],
                                    message=TEXT['messageOpenfailed'].format( \
                                        TEXT['messageOpenfailedByNewerVersion'].format(scenVersion, DEFAULT_VERSION)))
            elif v == 'Early':
                messagebox.showerror(title=TEXT['titleOpenfailed'],
                                    message=TEXT['messageOpenfailed'].format( \
                                        TEXT['messageOpenfailedByEarlyVersion'].format(scenVersion)))
            else:
                messagebox.showerror(title=TEXT['titleOpenfailed'],
                                    message=TEXT['messageOpenfailed'].format( \
                                        TEXT['messageOpenfailedByUnknownVersion'].format(repr(scenVersion))))
            return
        self.statusBarMessage('', layer='top')
        self.statusBarMessage(TEXT['noticeScenarioLoading'], update=True)
        if self.activeScenario != None and scenVersion != self.activeScenario.scenario_version:
            self.restartToLoad = path
            self.root.destroy()
            return
        try:
            self.logCatch = self.__catchScenLoadProgress
            self.activeScenario = AoE2DEScenario.from_file(path)
        except UnknownScenarioStructureError as e:
            def checkVersionNotSupportedRaise(e: UnknownScenarioStructureError):
                """Catch ASP version not supported exception."""
                if not isinstance(e.args[0], str):
                    return False
                parsed = parse("The version {0}:{1} is not supported by AoE2ScenarioParser. :(", e.args[0])
                if not parsed:
                    return False
                strScenVer: str = parsed.fixed[1]
                v = self.unsupportedVersionHelper(strScenVer)
                if v == 'Newer':
                    messagebox.showerror(title=TEXT['titleOpenfailed'],
                                        message=TEXT['messageOpenfailed'].format( \
                                            TEXT['messageOpenfailedByNewerVersion'].format(strScenVer, DEFAULT_VERSION)))
                elif v == 'Early':
                    messagebox.showerror(title=TEXT['titleOpenfailed'],
                                        message=TEXT['messageOpenfailed'].format( \
                                            TEXT['messageOpenfailedByEarlyVersion'].format(strScenVer)))
                else:
                    messagebox.showerror(title=TEXT['titleOpenfailed'],
                                        message=TEXT['messageOpenfailed'].format( \
                                            TEXT['messageOpenfailedByUnknownVersion'].format(strScenVer)))
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
        else:
            self.editorVersion = ScenarioVersion(self.activeScenario.scenario_version)
            CeAttributes.setVersion(self.editorVersion)
            TriggerJsonIO.assignVersion(self.editorVersion)
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

if __name__ == '__main__':
    print('can not start, use Launcher.py')
