from __future__ import unicode_literals

import atexit
import sys
import time
import traceback

import PyQt5.QtCore as qc
import PyQt5.QtWidgets as qw
from mainGUI import Ui_SekaiText
from PyQt5.QtGui import QKeySequence, QIcon, QBrush, QColor

from Editor import Editor
from Loader import Loader
from chr import chrs

import json
import logging
import os.path as osp
from os import mkdir
import platform
import requests

EditorMode = [u'翻译', u'校对', u'合意', u'审核']

unitDict = {
    "piapro": u"VIRTUAL SINGER",
    "light_sound": u"Leo/need",
    'idol': u"MORE MORE JUMP！",
    "street": u"Vivid BAD SQUAD",
    "theme_park": u"ワンダーランズ×ショウタイム",
    "school_refusal": u"25時、ナイトコードで。"
}
sekaiDict = ['leo', 'mmj', 'street', 'wonder', 'nightcode']

loggingPath = ""

class mainForm(qw.QMainWindow, Ui_SekaiText):

    chars = chrs
    events = []
    fes = []
    cards = []
    mainstory = []
    saved = True
    isNewFile = False
    editormode = 0

    srcText = Loader()
    dstText = Editor()
    preTitle = ""
    dstfilename = ""
    dstfilepath = ""

    datadir = ""
    settingdir = ""

    setting = {}
    preStoryType = ""

    downloadState = 1

    def __init__(self, root):
        super().__init__()

        self.datadir = osp.join(root, "data")
        self.settingdir = osp.join(root, "setting")

        if not osp.exists(self.settingdir):
            mkdir(self.settingdir)
            logging.warning("Setting Folder not Exists")
            logging.info("Setting Folder Created")
        if not osp.exists(self.datadir):
            logging.warning("Data Folder not Exists")
            mkdir(self.datadir)
            logging.info("Data Folder Created")

        settingpath = osp.join(self.settingdir, "setting.json")
        if osp.exists(settingpath):
            with open(settingpath, 'r', encoding='utf-8') as f:
                self.setting = json.load(f)
                logging.info("Setting File Loaded: {}".format(settingpath))
        else:
            logging.warning("Setting File not Exists: {}".format(settingpath))
        if 'textdir' not in self.setting:
            self.setting['textdir'] = self.datadir
        logging.info("Text Folder Path: {}".format(self.setting['textdir']))

        self.iconpath = "image/icon"
        if getattr(sys, 'frozen', False):
            self.iconpath = osp.join(sys._MEIPASS, self.iconpath)
        titleIcon = osp.join(self.iconpath, "32.ico")
        if osp.exists(titleIcon):
            self.setWindowIcon(QIcon(titleIcon))
            logging.info("Icon Loaded")

        self.setupUi(self)
        self.dstText = Editor(self.tableWidgetDst)
        '''
        chrspath = osp.join(self.settingdir, "chr.json")
        if osp.exists(chrspath):
            with open(chrspath, 'r', encoding='utf-8') as f:
                self.chars = json.load(f)
                logging.info("Character Loaded")
        '''
        eventspath = osp.join(self.settingdir, "events.json")
        if osp.exists(eventspath):
            with open(eventspath, 'r', encoding='utf-8') as f:
                self.events = json.load(f)
                logging.info("Event Loaded")
        fespath = osp.join(self.settingdir, "festivals.json")
        if osp.exists(fespath):
            with open(fespath, 'r', encoding='utf-8') as f:
                self.fes = json.load(f)
                logging.info("Festival Loaded")
        cardspath = osp.join(self.settingdir, "cards.json")
        if osp.exists(cardspath):
            with open(cardspath, 'r', encoding='utf-8') as f:
                self.cards = json.load(f)
                logging.info("Card Loaded")
        mainstorypath = osp.join(self.settingdir, "mainStory.json")
        if osp.exists(mainstorypath):
            with open(mainstorypath, 'r', encoding='utf-8') as f:
                self.mainstory = json.load(f)
                logging.info("Main Story Loaded")

        if 'storyType' in self.setting:
            self.comboBoxStoryType.setCurrentIndex(self.setting['storyType'])
        self.setComboBox(True)

        self.comboBoxStoryType.activated.connect(lambda: self.setComboBox(False))
        self.comboBoxStoryIndex.activated.connect(lambda: self.setComboBox(False))
        self.pushButtonRefresh.clicked.connect(self.updateComboBox)

        self.pushButtonLoad.clicked.connect(self.loadJson)
        self.pushButtonCount.clicked.connect(self.countSpeaker)

        self.radioButtonTranslate.clicked.connect(self.translateMode)
        self.radioButtonProofread.clicked.connect(self.proofreadMode)
        self.radioButtonCheck.clicked.connect(self.checkMode)
        # self.radioButtonJudge.clicked.connect(self.judgeMode)

        self.plainTextEditTitle.textChanged.connect(self.changeTitle)
        self.pushButtonOpen.clicked.connect(self.openText)
        self.pushButtonSave.clicked.connect(self.saveText)
        self.pushButtonClear.clicked.connect(self.clearText)
        self.pushButtonCheck.clicked.connect(self.checkLines)
        self.checkBoxShowDiff.stateChanged.connect(self.showDiff)
        self.checkBoxSaveN.stateChanged.connect(self.saveN)

        self.tableWidgetDst.currentCellChanged.connect(self.trackSrc)
        self.tableWidgetDst.itemActivated.connect(self.editText)
        self.tableWidgetDst.itemDoubleClicked.connect(self.editText)
        self.tableWidgetDst.itemChanged.connect(self.changeText)

        qw.QShortcut(QKeySequence(self.tr("Ctrl+S")), self, self.saveText)

        self.tempWindow = qw.QMessageBox(self)
        self.tempWindow.setIcon(qw.QMessageBox.Information)
        self.tempWindow.setWindowTitle("")

    def downloadJson(self, jsonname, jsonurl):
        jsonpath = osp.join(self.datadir, jsonname)
        download = downloadThread(jsonpath, jsonurl)
        download.start()
        download.trigger.connect(self.checkDownload)

        urlText = u"下载中...<br>若耗时过长可自行前往下方地址下载" + \
            "<br><a href=\"{}\">{}</a>".format(jsonurl, jsonname) + \
            "<br><br>下载时将文件名命名为{}，替换SekaiText同目录的data文件夹中的同名文件".format(jsonname) + \
            "<br><br>若没有自动开始下载，则将打开的网页中的内容全部复制(Ctrl+A全选，Ctrl+C复制)，" + \
            "替换data文件夹中{}的内容(替换时用记事本打开即可)".format(jsonname) +\
            "<br><br>轴机用json请从pjsek.ai复制"

        self.tempWindow.setStandardButtons(qw.QMessageBox.Cancel)
        self.tempWindow.setText(urlText)
        self.tempWindow.open()
        self.downloadState = 0
        while not self.downloadState:
            time.sleep(0.1)
            qw.QApplication.processEvents()
        if self.downloadState == 2:
            return False
        return True

    def loadJson(self):
        try:
            if not self.event:
                return
            storyType = self.comboBoxStoryType.currentText()
            storyIdx = self.comboBoxStoryIndex.currentIndex()
            chapterIdx = self.comboBoxStoryChapter.currentIndex()
            source = self.comboBoxDataSource.currentText()
            self.preTitle, jsonname, jsonurl = self.getJsonPath(storyType, storyIdx, chapterIdx, source)

            jsonpath = osp.join(self.datadir, jsonname)

            if source in ["sekai.best", "pjsek.ai"]:
                logging.info("Downloading Json File from: " + jsonurl)
                if not self.downloadJson(jsonname, jsonurl):
                    return
                self.comboBoxDataSource.setCurrentText(u"本地文件")
            elif source == u"本地文件":
                if not osp.exists(jsonpath):
                    jsonpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取文件", self.datadir, "Json Files (*.json)")

            if not jsonpath:
                return
            try:
                self.srcText = Loader(jsonpath, self.tableWidgetSrc)
            except BaseException as e:
                logging.error("Fail to Load Json File: " + jsonpath)
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                with open(loggingPath, 'a') as f:
                    traceback.print_exception(
                        exc_type, exc_value, exc_traceback_obj, file=f)
                qw.QMessageBox.warning(
                    self, "", u"读取Json失败\n{}\n请检查文件或重新下载".format(jsonpath))
                return
            else:
                logging.info("Json File Loaded: " + jsonpath)

            self.setting['storyType'] = self.comboBoxStoryType.currentIndex()
            self.setting['storyIdx'] = self.comboBoxStoryIndex.currentIndex()
            self.setting['storyChapter'] = self.comboBoxStoryChapter.currentIndex()
            save(self)

            if storyType[-2:] != u"卡面":
                title = self.comboBoxStoryChapter.currentText().split(" ")[-1]
                self.plainTextEditTitle.setPlainText(title)

            if not self.dstText.talks:
                self.clearText()
            else:
                self.dstText.loadJson(self.editormode, self.srcText.talks)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"loadJson错误\n请将“setting\\log.txt发给弃子”")

    def countSpeaker(self):
        try:
            chapterList = [self.comboBoxStoryChapter.currentIndex()]
            if self.checkBoxAll.isChecked():
                chapterList = []
                for idx in range(self.comboBoxStoryChapter.count()):
                    if self.comboBoxStoryChapter.itemText(idx):
                        chapterList.append(idx)

            countList = [{'name': self.chars[i]["name_j"], "count": [0 for i in range(len(chapterList) + 1)]} for i in range(26)]
            storyType = self.comboBoxStoryType.currentText()
            storyIdx = self.comboBoxStoryIndex.currentIndex()
            source = "sekai.best"
            for idx, chapterIdx in enumerate(chapterList):
                _, jsonname, jsonurl = self.getJsonPath(storyType, storyIdx, chapterIdx, source)

                jsonpath = osp.join(self.datadir, jsonname)
                if not osp.exists(jsonpath):
                    logging.info("Downloading Json File from: " + jsonurl)
                    if not self.downloadJson(jsonname, jsonurl):
                        return
                with open(jsonpath, 'r', encoding='UTF-8') as f:
                    fulldata = json.load(f)
                for talkdata in fulldata['TalkData']:
                    counted = False
                    speaker = talkdata['WindowDisplayName']
                    for c in countList:
                        if c["name"] == speaker:
                            c["count"][idx] += 1
                            c["count"][-1] += 1
                            counted = True
                            break
                    if not counted:
                        countList.append({"name": speaker, "count": [0 for i in range(len(chapterList) + 1)]})
                        countList[-1]["count"][idx] += 1
                        countList[-1]["count"][-1] += 1

            self.countTable = qw.QTableWidget()
            self.countTable.verticalHeader().hide()
            self.countTable.setIconSize(qc.QSize(48, 48))
            columnCount = len(chapterList) + 2
            self.countTable.setColumnCount(columnCount)
            self.countTable.setRowCount(0)
            self.countTable.horizontalHeader().resizeSection(0, 120)
            self.countTable.setHorizontalHeaderItem(0, qw.QTableWidgetItem(" "))
            for idx, chapterIdx in enumerate(chapterList):
                text = self.comboBoxStoryChapter.itemText(chapterIdx)
                if self.comboBoxStoryType.currentText()[-2:] != u"卡面":
                    text = text.split(" ")[0]
                self.countTable.setHorizontalHeaderItem(idx + 1, qw.QTableWidgetItem(text))
                self.countTable.horizontalHeader().resizeSection(idx + 1, 60)
                if self.comboBoxStoryType.currentText()[-2:] == u"卡面":
                    self.countTable.horizontalHeader().resizeSection(idx + 1, 100)
            self.countTable.setHorizontalHeaderItem(len(chapterList) + 1, qw.QTableWidgetItem(u"总计"))
            self.countTable.horizontalHeader().resizeSection(len(chapterList) + 1, 60)

            totalHeight = 0
            totalWidth = 0

            for idx, c in enumerate(countList):
                if c["count"][-1] == 0:
                    continue
                row = self.countTable.rowCount()
                self.countTable.setRowCount(row + 1)
                if (idx < 26):
                    charIcon = "chr/chr_{}.png".format(idx + 1)
                    charIcon = osp.join(self.iconpath, charIcon)
                    icon = qw.QTableWidgetItem(QIcon(charIcon), c["name"])
                    self.countTable.setItem(row, 0, icon)
                    self.countTable.setRowHeight(row, 60)
                    totalHeight += 60
                else:
                    self.countTable.setItem(row, 0, qw.QTableWidgetItem(c["name"]))
                    self.countTable.setRowHeight(row, 30)
                    totalHeight += 30
                for idx, count in enumerate(c["count"]):
                    if count == 0:
                        self.countTable.setItem(row, idx + 1, qw.QTableWidgetItem(" "))
                        self.countTable.item(row, idx + 1).setBackground(QBrush(QColor(127, 127, 127)))
                    else:
                        self.countTable.setItem(row, idx + 1, qw.QTableWidgetItem(str(count)))
            row = self.countTable.rowCount()
            col = self.countTable.columnCount()

            totalWidth = 66 + col * 60
            if self.comboBoxStoryType.currentText()[-2:] == u"卡面":
                totalWidth = col * 100
            self.countTable.setFixedSize(qc.QSize(min(800, totalWidth), min(800, 45 + totalHeight)))
            self.countTable.show()


        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"countSpeaker错误\n请将“setting\\log.txt发给弃子”")

    # create new text from json
    def clearText(self):
        try:
            if self.dstText.talks:
                relpy = qw.QMessageBox.question(
                    self, "", u"将清除现有翻译内容，是否继续？",
                    qw.QMessageBox.Yes | qw.QMessageBox.No,
                    qw.QMessageBox.No)
                if relpy == qw.QMessageBox.No:
                    return
            self.dstText.createFile(self.srcText.talks)
            self.getDstFileName()
            self.saved = True
            self.isNewFile = True
            self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"clearText错误\n请将“setting\\log.txt发给弃子”")

    def openText(self, editormode):
        try:
            if not self.checkSave():
                return
            if self.editormode == 0:
                textpath, _ = qw.QFileDialog.getOpenFileName(
                    self, u"选取翻译文本", self.setting['textdir'], "Text Files (*.txt)")
                if not self.loadText(textpath, 0):
                    return
                self.dstfilename = osp.basename(textpath)
                self.dstfilepath = textpath
                self.saved = True
                self.isNewFile = False
                self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

            elif self.editormode == 1:
                textpath, _ = qw.QFileDialog.getOpenFileName(
                    self, u"选取翻译文本", self.setting['textdir'], "Text Files (*.txt)")
                if not self.loadText(textpath, 0):
                    return

                relpy = qw.QMessageBox.question(
                    self, "", u"是否从头开始？",
                    qw.QMessageBox.Yes | qw.QMessageBox.No,
                    qw.QMessageBox.Yes)

                if relpy == qw.QMessageBox.No:
                    textpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取校对文本",
                        self.setting['textdir'], "Text Files (*.txt)")
                    if not self.loadText(textpath, 1):
                        return
                    self.dstfilename = osp.basename(textpath)
                    self.dstfilepath = textpath
                    self.saved = True
                    self.isNewFile = False
                    self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

                else:
                    self.getDstFileName()
                    self.dstfilepath = osp.join(
                        osp.dirname(textpath), self.dstfilename)
                    self.saved = False
                    self.isNewFile = True
                    self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

            elif self.editormode == 2:
                relpy = qw.QMessageBox.question(
                    self, "", u"是否与翻译文件对比？",
                    qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                    qw.QMessageBox.Yes)

                if relpy == qw.QMessageBox.Yes:
                    textpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取翻译文本",
                        self.setting['textdir'], "Text Files (*.txt)")
                    if not self.loadText(textpath, 0):
                        return

                    relpy = qw.QMessageBox.question(
                        self, "", u"是否从头开始？",
                        qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                        qw.QMessageBox.Yes)

                    if relpy == qw.QMessageBox.Yes:
                        textpath, _ = qw.QFileDialog.getOpenFileName(
                            self, u"选取校对文本",
                            self.setting['textdir'], "Text Files (*.txt)")
                        if not self.loadText(textpath, 2):
                            return
                        self.getDstFileName()
                        self.dstfilepath = osp.join(
                            osp.dirname(textpath), self.dstfilename)
                        self.saved = False
                        self.isNewFile = False
                        self.setWindowTitle(
                            "*{} Sekai Text".format(self.dstfilename))

                    elif relpy == qw.QMessageBox.No:
                        textpath, _ = qw.QFileDialog.getOpenFileName(
                            self, u"选取合意文本",
                            self.setting['textdir'], "Text Files (*.txt)")
                        if not self.loadText(textpath, 2):
                            return
                        self.dstfilename = osp.basename(textpath)
                        self.dstfilepath = textpath
                        self.saved = True
                        self.isNewFile = False
                        self.setWindowTitle(
                            "{} Sekai Text".format(self.dstfilename))

                elif relpy == qw.QMessageBox.No:
                    textpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取校对文本",
                        self.setting['textdir'], "Text Files (*.txt)")
                    if not self.loadText(textpath, 0):
                        return

                    relpy = qw.QMessageBox.question(
                        self, "", u"是否从头开始？",
                        qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                        qw.QMessageBox.Yes)

                    if relpy == qw.QMessageBox.No:
                        textpath, _ = qw.QFileDialog.getOpenFileName(
                            self, u"选取合意文本",
                            self.setting['textdir'], "Text Files (*.txt)")
                        if not self.loadText(textpath, 1):
                            return
                        self.dstfilename = osp.basename(textpath)
                        self.dstfilepath = textpath
                        self.saved = True
                        self.isNewFile = False
                        self.setWindowTitle(
                            "{} Sekai Text".format(self.dstfilename))

                    else:
                        self.getDstFileName()
                        self.dstfilepath = osp.join(
                            osp.dirname(textpath), self.dstfilename)
                        self.saved = False
                        self.isNewFile = True
                        self.setWindowTitle(
                            "*{} Sekai Text".format(self.dstfilename))
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"openText错误\n请将“setting\\log.txt发给弃子”")

    def loadText(self, textpath, editormode):
        if not textpath:
            return False
        self.setting['textdir'] = osp.dirname(textpath)

        self.dstText.loadFile(editormode, textpath)
        self.dstText.showDiff(self.checkBoxShowDiff.isChecked())

        title = osp.basename(textpath).split(" ")[-1].split(".")[0]
        if title:
            self.plainTextEditTitle.setPlainText(title)
        return True

    def checkLines(self):
        try:
            self.dstText.resetTalk(self.editormode, self.dstText.dsttalks)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"checkLines错误\n请将“setting\\log.txt发给弃子”")

    def changeTitle(self):
        try:
            self.plainTextEditTitle.blockSignals(True)
            self.getDstFileName()
            if self.dstfilepath:
                self.dstfilepath = osp.join(
                    osp.dirname(self.dstfilepath), self.dstfilename)
            self.isNewFile = True
            self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))
            self.plainTextEditTitle.blockSignals(False)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"changeTitle错误\n请将“setting\\log.txt发给弃子”")

    def getDstFileName(self):
        storyType = self.comboBoxStoryType.currentText()

        self.dstfilename = u"【{}】{}.txt".format(
            EditorMode[self.editormode], self.preTitle)
        title = self.plainTextEditTitle.toPlainText()
        if not title and storyType[-2:] != u"卡面":
            title = "Untitled"
        if title:
            self.dstfilename = self.dstfilename[:-4] + " {}.txt".format(title)

    def checkSave(self):
        if self.saved:
            return True

        relpy = qw.QMessageBox.question(
            self, "", u"修改尚未保存，是否保存？",
            qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
            qw.QMessageBox.Yes)

        if relpy == qw.QMessageBox.No:
            return True

        elif relpy == qw.QMessageBox.Yes:
            self.saveText()

        elif relpy == qw.QMessageBox.Cancel:
            return False

    def saveText(self):
        try:
            if not self.dstfilepath:
                self.dstfilepath = osp.join(
                    self.setting['textdir'], self.dstfilename)
                self.dstfilepath, _ = qw.QFileDialog.getSaveFileName(
                    self, u"保存文件", self.dstfilepath, "Text Files (*.txt)")
                if not self.dstfilepath:
                    return
                self.setting['textdir'] = osp.dirname(self.dstfilepath)
                self.isNewFile = False

            if self.isNewFile and osp.exists(self.dstfilepath):
                relpy = qw.QMessageBox.question(
                    self, "", u"文件已存在，是否覆盖？",
                    qw.QMessageBox.Yes | qw.QMessageBox.No,
                    qw.QMessageBox.No)

                if relpy == qw.QMessageBox.No:
                    return

            self.plainTextEditTitle.blockSignals(True)
            saveN = self.checkBoxSaveN.isChecked()
            self.dstText.saveFile(self.dstfilepath, saveN)
            self.saved = True
            self.isNewFile = False
            self.dstfilename = osp.basename(self.dstfilepath)
            self.plainTextEditTitle.setPlainText(self.dstfilename)
            if " " in self.dstfilename:
                title = self.dstfilename.split(".")[0].split(" ")[-1]
                if title:
                    self.plainTextEditTitle.setPlainText(title)
            self.plainTextEditTitle.blockSignals(False)
            self.setWindowTitle("{} Sekai Text".format(self.dstfilename))
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"saveText错误\n请将“setting\\log.txt发给弃子”")

    def closeEvent(self, event):
        if not self.checkSave():
            event.ignore()

    def editText(self, item):
        try:
            self.tableWidgetDst.editItem(item)
            self.tableWidgetDst.blockSignals(True)
            item.setText(item.text().split("\n")[0].rstrip().lstrip())
            self.tableWidgetDst.blockSignals(False)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"editText错误\n请将“setting\\log.txt发给弃子”")

    def changeText(self, item):
        try:
            self.dstText.changeText(item, self.editormode)
            self.saved = False
            self.setWindowTitle(u"*{} Sekai Text".format(self.dstfilename))
            self.dstText.saveFile(osp.join(osp.dirname(self.dstfilepath), "[AutoSave].txt"), self.saveN)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"changeText错误\n请将“setting\\log.txt发给弃子”")

    def showDiff(self, state):
        try:
            self.dstText.showDiff(state)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"showDiff错误\n请将“setting\\log.txt发给弃子”")

    def saveN(self, state):
        self.saved = False
        self.setWindowTitle(
            "*{} Sekai Text".format(self.dstfilename))

    def trackSrc(self, currentRow, currentColumn, previousRow, previousColumn):
        try:
            if currentColumn >= 3:
                return
            srcrow = self.tableWidgetSrc.rowCount()
            if currentRow < len(self.dstText.talks):
                srcrow = min(srcrow, self.dstText.talks[currentRow]['idx'])
                srcItem = self.tableWidgetSrc.item(srcrow - 1, 1)
                self.tableWidgetSrc.setCurrentItem(srcItem)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"trackSrc错误\n请将“setting\\log.txt发给弃子”")

    def setComboBox(self, isInit=False):
        try:
            if not self.preStoryType:
                self.preStoryType = self.comboBoxStoryType.currentText()

            storyType = self.comboBoxStoryType.currentText()

            if isInit and 'storyIdx' in self.setting:
                storyIndex = self.setting['storyIdx']
            else:
                storyIndex = self.comboBoxStoryIndex.currentIndex()

            if isInit and 'storyChapter' in self.setting:
                storyChapter = self.setting['storyChapter']
            else:
                storyChapter = 0

            self.comboBoxStoryIndex.clear()
            self.comboBoxStoryChapter.clear()

            if storyType == u"主线剧情":
                if not self.mainstory:
                    return
                for unit in self.mainstory:
                    self.comboBoxStoryIndex.addItem(unitDict[unit["unit"]])
                if (storyType == self.preStoryType) and (storyIndex >= 0):
                    self.comboBoxStoryIndex.setCurrentIndex(storyIndex)
                unitId = max(self.comboBoxStoryIndex.currentIndex(), 0)
                for idx, chapter in enumerate(self.mainstory[unitId]["chapters"]):
                    epNo = idx - 1
                    if unitId == 0:
                        epNo = idx % 4
                    self.comboBoxStoryChapter.addItem(
                        str(epNo + 1) + " " + chapter)
                if unitId == 0:
                    for i in range(4, 25, 5):
                        self.comboBoxStoryChapter.insertSeparator(i)

            elif storyType == u"活动剧情":
                if not self.events:
                    return
                for idx, event in enumerate(self.events[::-1]):
                    self.comboBoxStoryIndex.addItem(" ".join(
                        [str(len(self.events) - idx), event['title']]))
                if (storyType == self.preStoryType) and (storyIndex >= 0):
                    self.comboBoxStoryIndex.setCurrentIndex(storyIndex)
                eventId = len(self.events) - max(self.comboBoxStoryIndex.currentIndex(), 0)
                for idx, chapter in enumerate(self.events[eventId - 1]['chapters']):
                    self.comboBoxStoryChapter.addItem(str(idx + 1) + " " + chapter)
                if storyChapter:
                    self.comboBoxStoryChapter.setCurrentIndex(storyChapter)

            elif storyType == u"活动卡面":
                if not self.events:
                    return
                for idx, event in enumerate(self.events[::-1]):
                    self.comboBoxStoryIndex.addItem(" ".join(
                        [str(len(self.events) - idx), event['title']]))
                if (storyType == self.preStoryType) and (storyIndex >= 0):
                    self.comboBoxStoryIndex.setCurrentIndex(storyIndex)
                eventId = len(self.events) - max(self.comboBoxStoryIndex.currentIndex(), 0)
                for cardId in self.events[eventId - 1]['cards']:
                    self.comboBoxStoryChapter.addItem( 
                        self.chars[self.cards[cardId - 1]['characterId'] - 1]['name_j'] + u" 前篇")
                    self.comboBoxStoryChapter.addItem(
                        self.chars[self.cards[cardId - 1]['characterId'] - 1]['name_j'] + u" 后篇")
                lastSeparator = int(self.comboBoxStoryChapter.count() / 2 * 3 - 3)
                for i in range(2, lastSeparator, 3):
                    self.comboBoxStoryChapter.insertSeparator(i)
                if storyChapter:
                    self.comboBoxStoryChapter.setCurrentIndex(storyChapter)

            elif storyType == u"特殊卡面":
                if not self.fes:
                    return
                for f in self.fes[::-1]:
                    idx = f['id']
                    if 'collaboration' in f:
                        self.comboBoxStoryIndex.addItem(f['collaboration'])
                    elif f['isBirthday']:
                        year = 2021 + int((idx + 2) / 4)
                        month = (idx + 2) % 4 * 3 + 1
                        self.comboBoxStoryIndex.addItem("Birthday {} {}-{}".format(
                            year, str(month).zfill(2), str(month + 2).zfill(2)))
                    else:
                        year = 2021 + int(idx / 4)
                        month = idx % 4 * 3 + 1
                        self.comboBoxStoryIndex.addItem("Festival {} {}".format(
                            year, str(month).zfill(2)))
                if (storyType == self.preStoryType) and (storyIndex >= 0):
                    self.comboBoxStoryIndex.setCurrentIndex(storyIndex)
                fesId = len(self.fes) - max(self.comboBoxStoryIndex.currentIndex(), 0)
                for cardId in self.fes[fesId - 1]['cards']:
                    self.comboBoxStoryChapter.addItem(
                        self.chars[self.cards[cardId - 1]['characterId'] - 1]['name_j'] + u" 前篇")
                    self.comboBoxStoryChapter.addItem(
                        self.chars[self.cards[cardId - 1]['characterId'] - 1]['name_j'] + u" 后篇")
                lastSeparator = int(self.comboBoxStoryChapter.count() / 2 * 3 - 3)
                for i in range(2, lastSeparator, 3):
                    self.comboBoxStoryChapter.insertSeparator(i)
                if storyChapter:
                    self.comboBoxStoryChapter.setCurrentIndex(storyChapter)

            elif storyType == u"初始卡面":
                for char in self.chars:
                    self.comboBoxStoryIndex.addItem(char['name_j'])
                for i in range(4, 25, 5):
                    self.comboBoxStoryIndex.insertSeparator(i)
                if (storyType == self.preStoryType) and (storyIndex >= 0):
                    self.comboBoxStoryIndex.setCurrentIndex(storyIndex)
                self.comboBoxStoryChapter.addItem(u"一星 前篇")
                self.comboBoxStoryChapter.addItem(u"一星 后篇")
                if self.comboBoxStoryIndex.currentText() != u"ミク":
                    self.comboBoxStoryChapter.addItem(u"二星 前篇")
                    self.comboBoxStoryChapter.addItem(u"二星 后篇")
                else:
                    for unit in sekaiDict:
                        self.comboBoxStoryChapter.addItem(u"{}二星 前篇".format(unit))
                        self.comboBoxStoryChapter.addItem(u"{}二星 后篇".format(unit))
                self.comboBoxStoryChapter.addItem(u"三星 前篇")
                self.comboBoxStoryChapter.addItem(u"三星 后篇")
                if self.comboBoxStoryIndex.currentText() in [u"一歌", u"ミク", u"リン", u"レン"]:
                    self.comboBoxStoryChapter.addItem(u"四星 前篇")
                    self.comboBoxStoryChapter.addItem(u"四星 后篇")
                lastSeparator = int(self.comboBoxStoryChapter.count() / 2 * 3 - 3)
                for i in range(2, lastSeparator, 3):
                    self.comboBoxStoryChapter.insertSeparator(i)
                if storyChapter:
                    self.comboBoxStoryChapter.setCurrentIndex(storyChapter)

            self.preStoryType = storyType
            logging.info("Choose Story {} {}".format(storyType, self.comboBoxStoryIndex.currentText()))
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"setComboBox错误\n请将“setting\\log.txt发给弃子”")

    def updateComboBox(self):
        try:
            self.events, self.cards, self.fes, mainstory = self.srcText.update(self.settingdir)
        except BaseException as e:
            logging.error("Fail to Download Settingg File from best.")
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"更新失败\n请确认能正常访问sekai.best，且关闭代理与VPN")
            return
        else:
            logging.info("Chapter Information Update Successed.")
        if mainstory:
            self.mainstory = mainstory
        logging.info("Story List Updated")
        self.setComboBox()

    def getJsonPath(self, storyType, storyIdx, chapterIdx, source):
        jsonurl = ""
        if storyType == u"主线剧情":
            unitIdx = storyIdx
            self.comboBoxStoryIndex.currentIndex()
            unit = self.mainstory[unitIdx]["unit"].replace("_", "-")
            if unitIdx == 0:
                sekai = "vs" + sekaiDict[int((chapterIdx + 1) / 5)]
            else:
                sekai = sekaiDict[unitIdx - 1]
            if unitIdx == 0:
                chapter = str(chapterIdx % 4).zfill(2)
            else:
                chapter = str(chapterIdx).zfill(2)
            jsonname = "mainStory_{}_{}.json".format(sekai, chapter)
            if source == "sekai.best":
                jsonurl = "http://sekai-res.dnaroma.eu/" \
                    "file/sekai-assets/scenario/unitstory/" \
                    "{}-story-chapter_rip/{}_01_{}.asset".format(unit, sekai, chapter)
            elif source == "pjsek.ai":
                jsonurl = "http://assets.pjsek.ai/file/" \
                    "pjsekai-assets/startapp/scenario/unitstory/" \
                    "{}-story-chapter/{}_01_{}.json".format(unit, sekai, chapter)
            preTitle = "{}-{}".format(sekai, chapter)

        elif storyType == u"活动剧情":
            eventId = len(self.events) - storyIdx
            event = self.events[int(eventId) - 1]['name']
            eventId = str(eventId).zfill(2)
            chapter = str(chapterIdx + 1).zfill(2)

            jsonname = "event_{}_{}.json".format(eventId, chapter)
            if source == "sekai.best":
                jsonurl = "http://sekai-res.dnaroma.eu/" \
                    "file/sekai-assets/event_story/" \
                    "{}/scenario_rip/event_{}_{}.asset".format(event, eventId, chapter)
            elif source == "pjsek.ai":
                jsonurl = "http://assets.pjsek.ai/file/" \
                    "pjsekai-assets/ondemand/event_story/" \
                    "{}/scenario/event_{}_{}.json".format(event, eventId, chapter)
            preTitle = "{}-{}".format(eventId, chapter)

        elif storyType == u"活动卡面":
            eventId = len(self.events) - storyIdx
            cardId = self.events[eventId - 1]["cards"][int(chapterIdx / 3)]
            charId = self.cards[cardId - 1]["characterId"]
            count = str(self.cards[cardId - 1]["cardCount"]).zfill(3)
            chapter = str(chapterIdx % 3 + 1).zfill(2)
            eventId = str(eventId).zfill(2)
            charname = self.chars[charId - 1]['name']
            jsonname = "event_{}_{}_{}.json".format(eventId, charname, chapter)
            charId = str(charId).zfill(3)
            if source == "sekai.best":
                jsonurl = "http://sekai-res.dnaroma.eu/" \
                    "file/sekai-assets/character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.asset".format(
                        charId, count, charId, count, charname, chapter)
            elif source == "pjsek.ai":
                jsonurl = "http://assets.pjsek.ai/file/" \
                    "pjsekai-assets/startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.json".format(
                        charId, count, charId, count, charname, chapter)
            preTitle = "{}-{}-{}".format(eventId, charname, chapter)

        elif storyType == u"特殊卡面":
            fesId = len(self.fes) - storyIdx
            cardId = self.fes[fesId - 1]["cards"][int(chapterIdx / 3)]
            charId = self.cards[cardId - 1]["characterId"]
            count = str(self.cards[cardId - 1]["cardCount"]).zfill(3)
            chapter = str(chapterIdx % 3 + 1).zfill(2)
            charname = self.chars[charId - 1]['name']

            idx = self.fes[fesId - 1]['id']
            if 'collaboration' in self.fes[fesId - 1]:
                jsonname = "collabo_{}_{}_{}.json".format(
                    idx, charname, chapter)
            elif self.fes[fesId - 1]['isBirthday']:
                year = 2021 + int((idx + 2) / 4)
                jsonname = "birth_{}_{}_{}.json".format(
                    year, charname, chapter)
            else:
                year = 2021 + int(idx / 4)
                month = str(idx % 4 * 3 + 1).zfill(2)
                jsonname = "fes_{}{}_{}_{}.json".format(
                    year, month, charname, chapter)

            charId = str(charId).zfill(3)
            if source == "sekai.best":
                jsonurl = "http://sekai-res.dnaroma.eu/" \
                    "file/sekai-assets/character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.asset".format(
                        charId, count, charId, count, charname, chapter)
            elif source == "pjsek.ai":
                jsonurl = "http://assets.pjsek.ai/file/" \
                    "pjsekai-assets/startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.json".format(
                        charId, count, charId, count, charname, chapter)
            if 'collaboration' in self.fes[fesId - 1]:
                preTitle = "collabo{}_{}_{}.json".format(
                    idx, charname, chapter)
            elif self.fes[fesId - 1]['isBirthday']:
                preTitle = "birth{}_{}_{}.json".format(
                    year, charname, chapter)
            else:
                preTitle = "fes{}{}_{}_{}.json".format(
                    year, month, charname, chapter)

        elif storyType == u"初始卡面":
            currentIdx = storyIdx
            if currentIdx > 25:
                charId = currentIdx - 4
            else:
                charId = int(currentIdx / 5) * 4 + (currentIdx + 1) % 5
            charname = self.chars[charId - 1]['name']
            rarity = int(chapterIdx / 3) + 1
            if charname == "miku":
                realRarity = max(2, rarity - 4) if rarity > 2 else rarity
                if realRarity == 2:
                    unit = sekaiDict[rarity - 2]
                realRarity = str(realRarity).zfill(3)
            rarity = str(rarity).zfill(3)
            chapter = str(chapterIdx % 3 + 1).zfill(2)
            jsonname = "release_{}_{}_{}.json".format(
                charname, rarity, chapter)
            if charname == "miku":
                if realRarity == "02":
                    jsonname = "release_{}_{}_02_{}.json".format(
                        charname, unit, chapter)
                else:
                    jsonname = "release_{}_{}_{}.json".format(
                        charname, realRarity, chapter)
            charId = str(charId).zfill(3)
            if source == "sekai.best":
                jsonurl = "http://sekai-res.dnaroma.eu/" \
                    "file/sekai-assets/character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.asset".format(
                        charId, count, charId, count, charname, chapter)
            elif source == "pjsek.ai":
                jsonurl = "http://assets.pjsek.ai/file/" \
                    "pjsekai-assets/startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.json".format(
                        charId, rarity, charId, rarity, charname, chapter)
            if charname == "miku" and realRarity == "02":
                preTitle = "00-miku-{}-02-{}".format(unit, chapter)
            else:
                preTitle = "00-{}-{}-{}".format(charname, rarity, chapter)
        return preTitle, jsonname, jsonurl

    def translateMode(self):
        self.radioButtonTranslate.setChecked(True)
        self.editormode = 0
        self.dstText.isProofReading = False

    def proofreadMode(self):
        self.radioButtonProofread.setChecked(True)
        self.editormode = 1
        self.dstText.isProofReading = True

    def checkMode(self):
        self.radioButtonCheck.setChecked(True)
        self.editormode = 2
        self.dstText.isProofReading = True
    '''
    def judgeMode(self):
        self.radioButtonJudge.setChecked(True)
        self.editormode = 3
        self.dstText.isProofReading = False
    '''

    def checkDownload(self, successed):
        while self.downloadState:
            time.sleep(0.1)
            qw.QApplication.processEvents()
        if successed:
            self.tempWindow.close()
            self.downloadState = 1
        else:
            urlText = self.tempWindow.text().replace(
                "下载中...<br>若耗时过长",
                "下载失败，请确认代理与VPN关闭<br>随后点击下方链接确认Json文件是否存在<br>也")
            self.tempWindow.setStandardButtons(qw.QMessageBox.Ok)
            self.tempWindow.setText(urlText)
            self.tempWindow.close()
            self.tempWindow.exec()
            self.downloadState = 2



class downloadThread(qc.QThread):
    trigger = qc.pyqtSignal(bool)
    path = ""
    url = ""

    def __init__(self, jsonpath, jsonurl):
        super(downloadThread, self).__init__()
        self.path = jsonpath
        self.url = jsonurl

    def run(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'}
            r = requests.get(self.url, headers=headers, stream=True)
            r.encoding = 'utf-8'
            jsondata = json.loads(r.text)

            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(jsondata, f, indent=2, ensure_ascii=False)
            logging.info("Json File Saved: " + self.path)

            if "code" in jsondata and jsondata["code"] == "not_found":
                logging.info("Download Failed, Json File not Exist.")
                self.trigger.emit(False)
            else:
                logging.info("Download Successed.")
                self.trigger.emit(True)
        except BaseException:
            logging.error("Fail to Download Json File.")
            self.trigger.emit(False)


def save(self):
    settingpath = osp.join(self.settingdir, "setting.json")
    with open(settingpath, 'w', encoding='utf-8') as f:
        json.dump(self.setting, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    app = qw.QApplication(sys.argv)

    root, _ = osp.split(osp.abspath(sys.argv[0]))
    if not getattr(sys, 'frozen', False):
        root = osp.join(root, "../")

    if platform.system() == "Darwin":
        root = osp.join(root, '../../../')

    loggingPath = osp.join(root, "setting", "log.txt")
    logging.basicConfig(level=logging.INFO,
                        filename=loggingPath,
                        filemode='w')
    try:
        modeSelectWinodw = qw.QMessageBox()
        modeSelectWinodw.setWindowTitle("Sekai Text")
        modeSelectWinodw.setText("校对与合意时\n强烈建议在有音画对照的条件下进行\n如看游戏内，或者对照录制视频")
        translateButton = modeSelectWinodw.addButton(u"翻译", 2)
        proofreadButton = modeSelectWinodw.addButton(u"校对", 2)
        checkButton = modeSelectWinodw.addButton(u"合意", 2)
        # judgeButton = modeSelectWinodw.addButton(u"审核", 2)

        mainform = mainForm(root)
        translateButton.clicked.connect(mainform.translateMode)
        proofreadButton.clicked.connect(mainform.proofreadMode)
        checkButton.clicked.connect(mainform.checkMode)
        # judgeButton.clicked.connect(mainform.judgeMode())

        modeSelectWinodw.exec_()
        mainform.show()
        atexit.register(save, mainform)
        app.exec_()
    except BaseException:
        exc_type, exc_value, exc_traceback_obj = sys.exc_info()
        with open(loggingPath, 'a') as f:
            traceback.print_exception(
                exc_type, exc_value, exc_traceback_obj, file=f)
