from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from tkinter.constants import *
import ttkbootstrap as ttk

from AoE2ScenarioParser.objects.data_objects.trigger import Trigger

from Localization import TEXT
from Util import ReCompiled, Tooltip, ValueSelectButton

if TYPE_CHECKING:
    from main import TCWindow

class TriggerInfoView(ttk.Frame):
    @property
    def tl(self):
        return self.app.fTEditor.tvTriggerList

    @property
    def tm(self):
        return self.app.triggerManager

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        self.varTName = ttk.StringVar()
        self.varTEnable = ttk.BooleanVar()
        self.varTLoop = ttk.BooleanVar()
        self.varTDescriptionOrder = ttk.StringVar()
        self.varTDescriptionStringTable = ttk.StringVar()
        self.varTShortDescriptionStringTable = ttk.StringVar()
        self.varTAsObjective = ttk.BooleanVar()
        self.varTOnScreen = ttk.BooleanVar()
        self.varTMakeHeader = ttk.BooleanVar()
        self.varTMuteObjective = ttk.BooleanVar()
        ## Column 0
        lTName = ttk.Label(self, text=TEXT['labelTriggerName'])
        lTName.grid(column=0, row=0, sticky=EW, pady=self.app.dpi(10), padx=self.app.dpi(10))
        eTName = ttk.Entry(self, textvariable=self.varTName)
        self.varTName.trace_add('write', self.__modifyTriggerName)
        eTName.grid(column=0, row=1, sticky=EW, padx=self.app.dpi(10))
        cbTEnable = ttk.Checkbutton(self, text=TEXT['btnTriggerEnable'], bootstyle=(ttk.ROUND, ttk.TOGGLE),
                                        variable=self.varTEnable, command=self.__setTriggerEnableAndLoop)
        cbTEnable.grid(column=0, row=2, sticky=EW, padx=self.app.dpi(10), pady=self.app.dpi(10))
        cbTLoop = ttk.Checkbutton(self, text=TEXT['btnTriggerLoop'], bootstyle=(ttk.ROUND, ttk.TOGGLE),
                                    variable=self.varTLoop, command=self.__setTriggerEnableAndLoop)
        cbTLoop.grid(column=0, row=3, sticky=EW, padx=self.app.dpi(10))
        lTDscrOrder = ttk.Label(self, text=TEXT['labelTriggerDescriptionOrder'])
        lTDscrOrder.grid(column=0, row=4, sticky=EW, pady=self.app.dpi(10), padx=self.app.dpi(10))
        eTDscrOrder = ttk.Entry(self, textvariable=self.varTDescriptionOrder, validate="key",
                                    validatecommand=(self.register(lambda v: v.isdigit() or v == ''), '%P'))
        self.varTDescriptionOrder.trace_add('write', self.__modifyTriggerDescriptionOrder)
        eTDscrOrder.grid(column=0, row=5, sticky=EW, padx=self.app.dpi(10))
        fTOthers = ttk.Frame(self)
        fTOthers.grid(column=0, row=6, sticky=EW, pady=self.app.dpi(10), padx=self.app.dpi(10))
        cbTMakeHeader = ttk.Checkbutton(fTOthers, text=TEXT['btnTriggerMakeHeader'], bootstyle=(ttk.ROUND, ttk.TOGGLE),
                                            variable=self.varTMakeHeader, command=self.__setTriggerMakeHeader)
        cbTMakeHeader.pack(side=LEFT)
        cbTMuteObjective = ttk.Checkbutton(fTOthers, text=TEXT['btnTriggerMuteObjective'], bootstyle=(ttk.ROUND, ttk.TOGGLE),
                                                variable=self.varTMuteObjective, command=self.__setTriggerMuteObjective)
        cbTMuteObjective.pack(side=RIGHT)
        ## Column 1
        lTDescription = ttk.Label(self, text=TEXT['labelTriggerDescription'],width=self.app.dpi(30))
        lTDescription.grid(column=1, row=0, columnspan=2, sticky=EW)
        self.tTDescription = ttk.Text(self, height=2, width=2)
        self.tTDescription.bind('<<Modified>>', self.__modifyTriggerDescription)
        self.tTDescription.grid(column=1, row=1, columnspan=2, rowspan=7, sticky=NSEW)
        cbTAsObjective = ttk.Checkbutton(self, text=TEXT['btnTriggerAsObjective'], bootstyle=(ttk.ROUND, ttk.TOGGLE),
                                            variable=self.varTAsObjective, command=self.__setTriggerAsObjective)
        cbTAsObjective.grid(column=2, row=0, sticky=E, pady=self.app.dpi(10), padx=self.app.dpi(10))
        fTDescriptionStringTable = ttk.Frame(self)
        fTDescriptionStringTable.grid(column=1, row=8, columnspan=2, sticky=EW, pady=self.app.dpi(10))
        lTDescriptionStringTable = ttk.Label(fTDescriptionStringTable, text=TEXT['labelTriggerDescriptionStringTableID'])
        lTDescriptionStringTable.pack(side=LEFT, padx=(0, self.app.dpi(10)))
        eTDescriptionStringTable = ttk.Entry(
            fTDescriptionStringTable,
            textvariable=self.varTDescriptionStringTable,
            validate="key",
            validatecommand=(self.register(lambda v: ReCompiled.matchInputInteger(v) is not None), '%P')
        )
        self.varTDescriptionStringTable.trace_add('write', self.__modifyTriggerDescriptionStringTable)
        eTDescriptionStringTable.pack(side=RIGHT,fill=X,expand=YES)
        ## Column 2
        lTShortDscr = ttk.Label(self, text=TEXT['labelTriggerShortDescription'],width=self.app.dpi(30))
        lTShortDscr.grid(column=3, row=0, columnspan=2, sticky=EW, padx=self.app.dpi(10))
        self.tTShortDscr = ttk.Text(self, height=2, width=2)
        self.tTShortDscr.bind('<<Modified>>', self.__modifyTriggerShortDescription)
        self.tTShortDscr.grid(column=3, row=1, columnspan=2, rowspan=7, sticky=NSEW, padx=self.app.dpi(10))
        cbTOnScreen = ttk.Checkbutton(self, text=TEXT['btnTriggerOnScreen'], bootstyle=(ttk.ROUND, ttk.TOGGLE),
                                        variable=self.varTOnScreen, command=self.__setTriggerOnScreen)
        cbTOnScreen.grid(column=4, row=0, sticky=E, pady=self.app.dpi(10), padx=self.app.dpi(10))
        fTShortDscrStringTable = ttk.Frame(self)
        fTShortDscrStringTable.grid(column=3, row=8, columnspan=2, sticky=EW, padx=self.app.dpi(10), pady=self.app.dpi(10))
        lTShortDscrStringTable = ttk.Label(fTShortDscrStringTable, text=TEXT['labelTriggerShortDescriptionStringTableID'])
        lTShortDscrStringTable.pack(side=LEFT, padx=(0, self.app.dpi(10)))
        eTShortDscrStringTable = ttk.Entry(
            fTShortDscrStringTable, 
            textvariable=self.varTShortDescriptionStringTable, 
            validate="key", 
            validatecommand=(self.register(lambda v: ReCompiled.matchInputInteger(v) is not None), '%P')
        )
        self.varTShortDescriptionStringTable.trace_add('write', self.__modifyTriggerShortDescriptionStringTable)
        eTShortDscrStringTable.pack(side=RIGHT,fill=X,expand=YES)
        self.grid_rowconfigure(7,weight=1)
        self.grid_columnconfigure(0,weight=2)
        self.grid_columnconfigure(1,weight=3)
        self.grid_columnconfigure(2,weight=1)
        self.grid_columnconfigure(3,weight=3)
        self.grid_columnconfigure(4,weight=1)

    # region TriggerInfoMethods
    def __modifyTriggerName(self, *args):
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            newName = self.varTName.get()
            self.tl.item(curItem, text=' ' + newName)
            self.tm.get_trigger(triggerId).name = newName

    def __setTriggerEnableAndLoop(self):
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            if self.varTLoop.get() == True:
                if self.varTEnable.get() == True:
                    self.tl.item(curItem, image=self.app.imgTriggerEnabledLoop)
                    self.tm.get_trigger(triggerId).enabled = 1
                else:
                    self.tl.item(curItem, image=self.app.imgTriggerDisabledLoop)
                    self.tm.get_trigger(triggerId).enabled = 0
                self.tm.get_trigger(triggerId).looping = 1
            else:
                if self.varTEnable.get() == True:
                    self.tl.item(curItem, image=self.app.imgTriggerEnabled)
                    self.tm.get_trigger(triggerId).enabled = 1
                else:
                    self.tl.item(curItem, image=self.app.imgTriggerDisabled)
                    self.tm.get_trigger(triggerId).enabled = 0
                self.tm.get_trigger(triggerId).looping = 0

    def __setTriggerAsObjective(self):
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            if self.varTAsObjective.get() == True:
                self.tm.get_trigger(triggerId).display_as_objective = 1
            else:
                self.tm.get_trigger(triggerId).display_as_objective = 0

    def __setTriggerOnScreen(self):
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            if self.varTOnScreen.get() == True:
                self.tm.get_trigger(triggerId).display_on_screen = 1
            else:
                self.tm.get_trigger(triggerId).display_on_screen = 0

    def __setTriggerMakeHeader(self):
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            if self.varTMakeHeader.get() == True:
                self.tm.get_trigger(triggerId).header = 1
            else:
                self.tm.get_trigger(triggerId).header = 0

    def __setTriggerMuteObjective(self):
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            if self.varTMuteObjective.get() == True:
                self.tm.get_trigger(triggerId).mute_objectives = 1
            else:
                self.tm.get_trigger(triggerId).mute_objectives = 0

    def __modifyTriggerDescriptionOrder(self, *args):
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            descriptionOrder = self.varTDescriptionOrder.get()
            if descriptionOrder.isdigit():
                descriptionOrder = int(descriptionOrder)
            else:
                descriptionOrder = 0
            self.tm.get_trigger(triggerId).description_order = descriptionOrder

    def __modifyTriggerDescriptionStringTable(self, *args):
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            descriptionStringTable = self.varTDescriptionStringTable.get()
            if ReCompiled.matchInteger(descriptionStringTable) is not None:
                descriptionStringTable = int(descriptionStringTable)
            else:
                descriptionStringTable = -1
            self.tm.get_trigger(triggerId).description_stid = descriptionStringTable

    def __modifyTriggerShortDescriptionStringTable(self, *args):
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            shortDescriptionStringTable = self.varTShortDescriptionStringTable.get()
            if ReCompiled.matchInteger(shortDescriptionStringTable) is not None:
                shortDescriptionStringTable = int(shortDescriptionStringTable)
            else:
                shortDescriptionStringTable = -1
            self.tm.get_trigger(triggerId).short_description_stid = shortDescriptionStringTable

    def __modifyTriggerDescription(self, *args):
        if self.tTDescription.edit_modified() == False:
            return
        self.tTDescription.edit_modified(False)
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            description = self.tTDescription.get(1.0, 'end-1c')
            self.tm.get_trigger(triggerId).description = description.replace('\n', '\r')

    def __modifyTriggerShortDescription(self, *args):
        if self.tTShortDscr.edit_modified() == False:
            return
        self.tTShortDscr.edit_modified(False)
        curItem = self.tl.focus()
        if self.tl.itemType(curItem) == 'trigger':
            triggerId = self.tl.getNodeId(curItem)[0]
            shortDescription = self.tTShortDscr.get(1.0, 'end-1c')
            self.tm.get_trigger(triggerId).short_description = shortDescription.replace('\n', '\r')

    # endregion TriggerInfoMethods

    def loadTriggerAttributes(self, trigger: Trigger):
        self.varTName.set(trigger.name)
        self.varTEnable.set(True if trigger.enabled == 1 else False)
        self.varTLoop.set(True if trigger.looping == 1 else False)
        self.varTDescriptionOrder.set(trigger.description_order)
        self.varTDescriptionStringTable.set(trigger.description_stid)
        self.varTShortDescriptionStringTable.set(trigger.short_description_stid)
        self.varTAsObjective.set(True if trigger.display_as_objective == 1 else False)
        self.varTOnScreen.set(True if trigger.display_on_screen == 1 else False)
        self.varTMakeHeader.set(True if trigger.header == 1 else False)
        self.varTMuteObjective.set(True if trigger.mute_objectives == 1 else False)
        self.tTDescription.delete(1.0, END)
        self.tTDescription.insert(1.0, trigger.description.replace('\r', '\n'))
        self.tTShortDscr.delete(1.0, END)
        self.tTShortDscr.insert(1.0, trigger.short_description.replace('\r', '\n'))
        self.app.statusBarMessage(trigger.name)
