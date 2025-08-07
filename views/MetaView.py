from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from tkinter.constants import *
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText

from Localization import TEXT
from Util import PairValueEntry, ReCompiled, int32_cast, uint32_cast

if TYPE_CHECKING:
    from main import TCWindow

class MetaView(ttk.Frame):

    @property
    def scen(self):
        return self.app.activeScenario

    @property
    def fh(self):
        return self.scen.sections['FileHeader']

    @property
    def msgm(self):
        return self.app.activeScenario.message_manager

    def __init__(self, app: TCWindow, master = None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app

        # Metadata
        lMetas = ttk.Frame(self)
        lVersionTitle = ttk.Label(lMetas, anchor=W, text=TEXT['labelScenVersion'])
        self.lVersion = ttk.Label(lMetas, anchor=W)

        lAuthorTitle = ttk.Label(lMetas, anchor=W, text=TEXT['labelScenAuthor'])
        self.lAuthor = ttk.Label(lMetas, anchor=W)

        lLastSaveTimeTitle = ttk.Label(lMetas, anchor=W, text=TEXT['labelScenSaveDate'])
        self.lLastSaveTime = ttk.Label(lMetas, anchor=W)

        lTriggerVersionTitle = ttk.Label(lMetas, anchor=W, text=TEXT['labelScenTriggerVersion'])
        self.lTriggerVersion = ttk.Label(lMetas, anchor=W)

        lVersionTitle.grid(column=0, row=0, sticky=NW)
        self.lVersion.grid(column=1, row=0, sticky=NW)
        lAuthorTitle.grid(column=2, row=0, sticky=NW)
        self.lAuthor.grid(column=3, row=0, sticky=NW)
        lLastSaveTimeTitle.grid(column=0, row=1, sticky=NW)
        self.lLastSaveTime.grid(column=1, row=1, sticky=NW)
        lTriggerVersionTitle.grid(column=2, row=1, sticky=NW)
        self.lTriggerVersion.grid(column=3, row=1, sticky=NW)

        lMetas.grid_columnconfigure(0, pad=self.app.dpi(10))
        lMetas.grid_columnconfigure(1, pad=self.app.dpi(40), weight=1)
        lMetas.grid_columnconfigure(2, pad=self.app.dpi(10))
        lMetas.grid_columnconfigure(3, pad=self.app.dpi(40), weight=1)
        lMetas.grid_rowconfigure(0, pad=self.app.dpi(10))
        lMetas.grid_rowconfigure(1, pad=self.app.dpi(10))
        lMetas.pack(side=TOP, anchor=W, padx=self.app.dpi((10, 10)), pady=self.app.dpi((10, 0)))

        # Messages
        fMessageLine1 = ttk.Frame(self)
        self.varMessageSelect = ttk.StringVar()
        self.cbMessages = ttk.Combobox(fMessageLine1, textvariable=self.varMessageSelect,
                                        values=[i for i in TEXT['messageNames'].values()],
                                        state="readonly", width=14)
        self.cbMessages.pack(side=LEFT, anchor=W)
        self.cbMessages.current(0)
        self.cbMessages.bind("<<ComboboxSelected>>", lambda e: (self.cbMessages.selection_clear(), self.__showMessage()))
        self.invertedMsgNamesDict: dict[str, str] = {v:k for k, v in TEXT['messageNames'].items()}

        self.varMessageStringId = ttk.StringVar()
        lMessageStringId = ttk.Label(fMessageLine1, text=TEXT['labelMsgStringTableId'])
        eMessageStringId = PairValueEntry(
            fMessageLine1, self.varMessageStringId,
            validate="key",
            validatecommand=(self.register(lambda v: ReCompiled.matchInputInteger(v) is not None), '%P')
        )
        eMessageStringId.set_display_event(lambda: self.__msgStrIdModified(self.getMsgAttrSelect()))
        eMessageStringId.pack(side=RIGHT, padx=self.app.dpi((10, 10)))
        lMessageStringId.pack(side=RIGHT, padx=self.app.dpi((10, 0)))
        fMessageLine1.pack(side=TOP, fill=X, padx=self.app.dpi((10, 10)), pady=self.app.dpi((10, 10)))
        self.tMessage = ScrolledText(self, height=2, width=2)
        self.tMessage.text.bind('<<Modified>>',
                        lambda e: \
                            self.__msgModified(self.getMsgAttrSelect()))
        self.tMessage.pack(side=TOP, anchor=W, fill=BOTH, expand=True, padx=self.app.dpi((8, 8)), pady=self.app.dpi((0, 10)))

        self.grid_rowconfigure(3, weight=1)

    def getMsgAttrSelect(self) -> str:
        msgSelValue = self.varMessageSelect.get()
        msgAttr = self.invertedMsgNamesDict[msgSelValue]
        return msgAttr

    def __showMessage(self):
        msgAttr = self.getMsgAttrSelect()
        self.msgload(msgAttr)
        self.varMessageStringId.set(int32_cast(getattr(self.msgm, msgAttr + '_string_table_id')))

    def loadMeta(self):
        self.lVersion.config(text=self.scen.scenario_version)
        self.lAuthor.config(text=self.fh.creator_name)
        date = datetime.fromtimestamp(self.fh.timestamp_of_last_save)
        self.lLastSaveTime.config(text=date.strftime(r"%Y/%m/%d, %H:%M:%S"))
        self.lTriggerVersion.config(text=str(self.scen.sections['Triggers'].trigger_version))
        self.__showMessage()

    def msgload(self, msgAttr: str):
        msg:str = getattr(self.msgm, msgAttr)
        self.tMessage.text.delete(1.0, END)
        self.tMessage.text.insert(1.0, msg.replace('\r', '\n'))
        self.tMessage.text.edit_modified(False)

    def __msgModified(self, msgAttr: str):
        if self.tMessage.text.edit_modified() == False:
            return
        self.tMessage.text.edit_modified(False)
        msg = self.tMessage.text.get(1.0, 'end-1c')
        setattr(self.msgm, msgAttr, msg.replace('\n', '\r'))

    def __msgStrIdModified(self, msgAttr: str):
        try:
            value = uint32_cast(int(self.varMessageStringId.get()))
        except ValueError:
            return
        setattr(self.msgm, msgAttr + '_string_table_id', value)