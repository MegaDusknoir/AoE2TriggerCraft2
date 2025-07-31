
from math import sqrt
import os
import sys
import re
import json
import base64
import datetime
import time
from typing import Literal, TextIO
import ctypes
import tempfile

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
from TerrainPal import TERRAIN_PAL
from TriggerAbstract import *
from views.TriggerView import TriggerView
from views.UnitInfo import UnitInfoView
from views.UnitView import UnitView
from views.MapView import MapView
from views.TriggerInfo import TriggerInfoView
from views.CeInfo import CeInfoView
from Util import IntListVar, MappedCombobox, ListValueButton, PairValueEntry, Tooltip, ValueSelectButton, ZoomImageViewer
from Util import DebugTimeCount
from _prebuild.version import VERSION_STRING
from _prebuild.AoE2TC_icon import Icon
from _prebuild.CeAttributes import CONDITION_ATTRIBUTES, EFFECT_ATTRIBUTES
from WidgetLayout import CONDITION_WIDGET_FORM, EFFECT_WIDGET_FORM

workDir = os.path.dirname(sys.argv[0])
# ASPSettings.ENABLE_XS_CHECK_INTEGRATION = False

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

        loadLocalizedText(workDir)

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

        self.options = GlobalOptions()
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
        except FileNotFoundError:
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
        # Right pw is T-B layout
        self.nTabsRightTop = ttk.Notebook(self.fPwRight, width=400, height=200)
        self.nTabsRightBottom = ttk.Notebook(self.fPwRight)

        self.fMapViewTab = MapView(self, self.nTabsRightTop)
        self.nTabsRightTop.add(self.fMapViewTab, text=TEXT['tabMapView'])

        self.triggerManager: TriggerManager
        self.fTriggerInfo = TriggerInfoView(self, self.nTabsRightBottom)
        self.fCeInfo = CeInfoView(self, self.nTabsRightBottom)
        self.fUnitInfo = UnitInfoView(self, self.nTabsRightBottom)
        self.nTabsRightBottom.add(self.fTriggerInfo, text=TEXT['tabTriggerInfo'])
        self.nTabsRightBottom.add(self.fCeInfo, text=TEXT['tabEffectInfo'], state="disabled")
        self.nTabsRightBottom.add(self.fUnitInfo, text=TEXT['tabUnitInfo'])

        self.nTabsRightTop.grid(column=0, row=0, sticky=NSEW, padx=(self.dpi(5), 0), pady=(0, self.dpi(10)))
        self.nTabsRightBottom.grid(column=0, row=1, sticky=NSEW, padx=(self.dpi(5), 0), pady=(self.dpi(10), 0))
        self.fPwRight.grid_rowconfigure(0,weight=2)
        self.fPwRight.grid_rowconfigure(1,weight=1)
        self.fPwRight.grid_columnconfigure(0,weight=1)

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
        self.menuEdit.add_command(label=TEXT['menuExportTriggerToText'], command=self.exportTriggerToText, state='disabled')
        self.menuEdit.add_command(label=TEXT['menuImportTriggerFromText'], command=self.importTriggerFromText, state='disabled')
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
        self.readScenario()

    def changeLanguage(self, lang: str) -> None:
        """Change language setting and apply"""
        loadLocalizedText(workDir, lang)
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
        print('exportTriggerToText')

    def importTriggerFromText(self):
        print('importTriggerFromText')

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
            self.activeScenario.write_to_file(path)
            self.statusBarMessage(TEXT['noticeScenarioSaved'])

    def saveAsScenario(self) -> str:
        saveFilePath = asksaveasfilename(title=TEXT['titleSelectSaveScenario'],
                                         filetypes=[(TEXT['typeNameScenario'], '*.aoe2scenario')])
        if saveFilePath != '':
            scenName, scenExt = os.path.splitext(saveFilePath)
            if scenExt == '' and os.path.isfile(saveFilePath) == False:
                saveFilePath += '.aoe2scenario'
            self.activeScenario.write_to_file(saveFilePath)
            self.statusBarMessage(TEXT['noticeScenarioSaved'])
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