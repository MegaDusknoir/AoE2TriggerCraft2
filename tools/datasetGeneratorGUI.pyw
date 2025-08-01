
import ctypes
import json
import os
from tkinter import messagebox
from tkinter.filedialog import askdirectory
from tkinter.constants import *
import ttkbootstrap as ttk
import datasetGenerator as gen

workDir = os.path.dirname(__file__)

class DatasetGeneratorWindow():

    languages = [
        ('en_US', 'en'),
        ('zh_CN', 'zh'),
        ('ja_JP', 'jp'),
        ('ko_KR', 'ko'),
        ('zh_TW', 'tw'),
        ('pt-BR', 'br'),
        ('de_DE', 'de'),
        ('es_ES', 'es'),
        ('fr_FR', 'fr'),
        ('hi-IN', 'hi'),
        ('it_IT', 'it'),
        ('ms_MY', 'ms'),
        ('es-MX', 'mx'),
        ('pl_PL', 'pl'),
        ('ru_RU', 'ru'),
        ('tr_TR', 'tr'),
        ('vi_VN', 'vi'),
    ]

    def __init__(self) -> None:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        self.scaleFactor=ctypes.windll.shcore.GetScaleFactorForDevice(0)

        self.root = ttk.Window('Dataset Generator', iconphoto=None)
        self.root.withdraw()
        self.root.iconbitmap(default=f'{workDir}/../AoE2TC.ico')
        self.style = ttk.Style()
        self.style.theme_use('litera')

        self.main = ttk.Frame(self.root, padding=self.dpi((10,10,10,5)))

        ttk.Label(self.main, text='1. Select languages of dataset to generate:', justify='left').pack(side=TOP, anchor=W, pady=self.dpi(0))
        fLangSelect = ttk.Frame(self.main)
        self.checks: dict[str, tuple[str, ttk.BooleanVar, ttk.Checkbutton]] = {}
        for i, langTuple in enumerate(DatasetGeneratorWindow.languages):
            variant, langFolder = langTuple
            var = ttk.BooleanVar(value=False)
            btn = ttk.Checkbutton(fLangSelect, text=f'{variant}', variable=var)
            btn.grid(column=i%5, row=i//5, padx=self.dpi(10), pady=self.dpi(10), sticky=W)
            self.checks[variant] = (langFolder, var, btn)
        self.checks['en_US'][1].set(True)
        self.checks['zh_CN'][1].set(True)
        fLangSelect.pack(side=TOP, fill=X)
        ttk.Separator(self.main).pack(side=TOP, fill=X)

        ttk.Label(self.main, text='2. Select the path of AoE2DE:', justify='left').pack(side=TOP, anchor=W, pady=self.dpi((10, 0)))
        fPath = ttk.Frame(self.main)
        self.varPath = ttk.StringVar()
        self.ePath = ttk.Entry(fPath, textvariable=self.varPath)
        self.ePath.pack(side=LEFT, expand=True, fill=X)
        btnBrowse = ttk.Button(fPath, text='...', command=self.__browsePath)
        self.varPath.trace_add('write', self.__verifyPath)
        btnBrowse.pack(side=RIGHT)
        fPath.pack(fill=X, pady=self.dpi(10))
        ttk.Separator(self.main).pack(side=TOP, fill=X)

        self.dstPath = os.path.realpath(f'{workDir}/../resources')
        dstPathExample = os.path.realpath(f'{self.dstPath}/<Language>')
        ttk.Label(self.main, text=f'3. Dataset json will be generated in:\n\n{dstPathExample}', justify='left').pack(side=TOP, anchor=W, pady=self.dpi(10))
        self.btnExecute = ttk.Button(self.main, text='Generate', command=self.__executeGenerate, state='disabled')
        self.btnExecute.pack(side=TOP, pady=self.dpi(10))
        self.main.pack(fill=BOTH, expand=YES)

    def mainloop(self):
        self.root.update_idletasks()
        self.centerWindowGeometry(self.root, self.root.winfo_width(), self.root.winfo_height())
        self.root.resizable(False, False)
        self.root.deiconify()
        self.root.mainloop()

    def dpi(self, value:int | tuple[int, ...]):
        if type(value) == tuple:
            return tuple(int(self.scaleFactor / 100 * v) for v in value)
        elif type(value) == int:
            return int(self.scaleFactor / 100 * value)

    def centerWindowGeometry(self, window: ttk.Toplevel, width, height, location=0.5):
        ws = self.main.winfo_screenwidth()
        hs = self.main.winfo_screenheight()
        x = (ws - width) * location
        y = (hs - height) * location
        window.geometry('%dx%d+%d+%d' % (width, height, x, y))

    def __verifyPath(self, *args):
        path = self.varPath.get()
        if os.path.isfile(f'{path}/AoE2DE_s.exe'):
            self.ePath.config(bootstyle=(ttk.PRIMARY))
            self.btnExecute.config(state='normal')
        else:
            self.ePath.config(bootstyle=(ttk.WARNING))
            self.btnExecute.config(state='disabled')

    def __browsePath(self):
        path = askdirectory(title='Select Folder')
        if path:
            self.varPath.set(path)

    def __executeGenerate(self):
        rootPath = self.varPath.get()
        dataPath = f'{rootPath}/resources/_common/dat/empires2_x2_p1.dat'
        dataObj = gen.parseDataFile(dataPath)
        for key, check in self.checks.items():
            if check[1].get():
                langPath = f'{rootPath}/resources/{check[0]}/strings/key-value/key-value-strings-utf8.txt'
                destPath = f'{self.dstPath}/{key}'
                langDict = gen.parseLanguageText(langPath)
                unitName = gen.getUnitName(dataObj, langDict)
                techName = gen.getTechName(dataObj, langDict)
                tributeName = gen.getTributeName(dataObj, langDict)
                if os.path.isdir(destPath) == False:
                    os.makedirs(destPath)
                with open(f'{destPath}/UnitsName.json', 'w', encoding='utf-8') as f:
                    json.dump(unitName, f, indent=4, ensure_ascii=False)
                with open(f'{destPath}/TechsName.json', 'w', encoding='utf-8') as f:
                    json.dump(techName, f, indent=4, ensure_ascii=False)
                with open(f'{destPath}/TributesName.json', 'w', encoding='utf-8') as f:
                    json.dump(tributeName, f, indent=4, ensure_ascii=False)
        messagebox.showinfo(title='Note', message='Generate done.')

if __name__ == '__main__':
    window = DatasetGeneratorWindow()
    window.mainloop()