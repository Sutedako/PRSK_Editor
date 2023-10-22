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
from JsonLoader import JsonLoader
from ListManager import ListManager
from Dictionary import unitDict, sekaiDict, characterDict

import json
import logging
import os.path as osp
from os import environ, mkdir, _exit, remove
import platform
import requests
from urllib import request

EditorMode = [u'翻译', u'校对', u'合意', u'审核']

loggingPath = ""

localProxy = request.getproxies()


class mainForm(qw.QMainWindow, Ui_SekaiText):
    def __init__(self, root):
        super().__init__()

        self.chars = characterDict
        self.saved = True
        self.isNewFile = False
        self.editormode = 0

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

        self.ListManager = ListManager(self.settingdir)
        self.ListManager.load()
        self.srcText = JsonLoader()
        self.dstText = Editor()
        self.preTitle = ""
        self.dstfilename = ""
        self.dstfilepath = ""

        self.setting = {}

        self.downloadState = 1

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
        self.fontSize = self.setting['fontSize'] if 'fontSize' in self.setting else 18

        self.iconpath = "image/icon"
        if getattr(sys, 'frozen', False):
            self.iconpath = osp.join(sys._MEIPASS, self.iconpath)
        if platform.system() == "Darwin":
            titleIcon = osp.join(self.iconpath, "32.icns")
        else:
            titleIcon = osp.join(self.iconpath, "32.ico")
        if osp.exists(titleIcon):
            self.setWindowIcon(QIcon(titleIcon))
            logging.info("Icon Loaded")

        self.setupUi(self)
        self.spinBoxFontSize.setValue(self.fontSize)
        self.dstText = Editor(self.tableWidgetDst, fontSize=self.fontSize)
        '''
        chrspath = osp.join(self.settingdir, "chr.json")
        if osp.exists(chrspath):
            with open(chrspath, 'r', encoding='utf-8') as f:
                self.chars = json.load(f)
                logging.info("Character Loaded")
        '''

        self.setComboBoxStoryType(True)
        self.comboBoxStoryType.activated.connect(lambda: self.setComboBoxStoryTypeSort(False))
        self.comboBoxStoryTypeSort.activated.connect(lambda: self.setComboBoxStoryIndex(False))
        self.comboBoxStoryIndex.activated.connect(lambda: self.setComboBoxStoryChapter(False))
        self.pushButtonRefresh.clicked.connect(self.updateComboBox)

        self.pushButtonLoad.clicked.connect(self.loadJson)
        self.pushButtonCount.clicked.connect(self.countSpeaker)

        self.radioButtonTranslate.clicked.connect(self.translateMode)
        self.radioButtonProofread.clicked.connect(self.proofreadMode)
        self.radioButtonCheck.clicked.connect(self.checkMode)

        self.pushButtonOpen.clicked.connect(self.openText)
        self.pushButtonSave.clicked.connect(self.saveText)
        self.pushButtonClear.clicked.connect(self.clearText)

        self.lineEditTitle.textChanged.connect(self.changeTitle)
        self.pushButtonSpeaker.clicked.connect(self.setSpeaker)
        self.pushButtonCheck.clicked.connect(self.checkLines)
        self.spinBoxFontSize.valueChanged.connect(self.setFontSize)

        self.checkBoxShowDiff.stateChanged.connect(self.showDiff)
        self.checkBoxSaveN.stateChanged.connect(self.saveN)

        self.tableWidgetDst.currentCellChanged.connect(self.trackSrc)
        self.tableWidgetDst.itemActivated.connect(self.editText)
        self.tableWidgetDst.itemClicked.connect(self.editText)
        self.tableWidgetDst.itemDoubleClicked.connect(self.editText)
        self.tableWidgetDst.itemChanged.connect(self.changeText)

        qw.QShortcut(QKeySequence(self.tr("Ctrl+S")), self, self.saveText)

        self.tempWindow = qw.QMessageBox(self)
        self.tempWindow.setStandardButtons(qw.QMessageBox.No)
        self.tempWindow.setWindowTitle("")
        self.tempWindow.button(qw.QMessageBox.No).setText("取消")
        self.tempWindow.buttonClicked.connect(self.downloadFailed)

    def downloadJson(self, jsonname, jsonurl):
        jsonpath = osp.join(self.datadir, jsonname)
        download = downloadThread(jsonpath, jsonurl)
        download.trigger.connect(self.checkDownload)

        urlText = u"下载中...<br>若耗时过长可自行前往下方地址下载" + \
            "<br><a href=\"{}\">{}</a>".format(jsonurl, jsonname) + \
            "<br><br>下载时将文件名命名为{}，替换SekaiText同目录的data文件夹中的同名文件".format(jsonname) + \
            "<br><br>若没有自动开始下载，则将打开的网页中的内容全部复制(Ctrl+A全选，Ctrl+C复制)，" + \
            "替换data文件夹中{}的内容(替换时用记事本打开即可)".format(jsonname) +\
            "<br><br>轴机用json请从pjsek.ai复制"

        self.tempWindow.setText(urlText)
        self.tempWindow.open()
        self.downloadState = 0

        download.start()
        while not self.downloadState:
            time.sleep(0.1)
            qw.QApplication.processEvents()
        if self.downloadState == 2:
            return False
        return True

    def loadJson(self):
        try:
            if not self.ListManager.events:
                qw.QMessageBox.information(self, "", u"请先刷新")
                return
            storyType = self.comboBoxStoryType.currentText()
            storyTypesort = self.comboBoxStoryTypeSort.currentText()
            storyIdx = self.comboBoxStoryIndex.currentIndex()
            chapterIdx = self.comboBoxStoryChapter.currentIndex()
            source = self.comboBoxDataSource.currentText()
            jsonpath = ""
            if storyType != u"自定义":
                self.preTitle, jsonname, jsonurl = self.ListManager.getJsonPath(
                    storyType, storyTypesort, storyIdx, chapterIdx, source)

                jsonpath = osp.join(self.datadir, jsonname)

            if storyType == u"主界面语音":
                self.ListManager.makeJson(storyTypesort, storyIdx, jsonpath)
            elif source != u"本地文件":
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
                self.srcText = JsonLoader(jsonpath, self.tableWidgetSrc, fontSize=self.fontSize)
                logging.info("Json File Loaded: " + jsonpath)
            except BaseException:
                logging.error("Fail to Load Json File: " + jsonpath)
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                with open(loggingPath, 'a') as f:
                    traceback.print_exception(
                        exc_type, exc_value, exc_traceback_obj, file=f)
                qw.QMessageBox.warning(
                    self, "", u"读取Json失败\n{}\n请检查文件或重新下载".format(jsonpath))
                return

            self.setting['storyType'] = self.comboBoxStoryType.currentIndex()
            self.setting['storyTypeSort'] = self.comboBoxStoryTypeSort.currentIndex()
            self.setting['storyIdx'] = self.comboBoxStoryIndex.currentIndex()
            self.setting['storyChapter'] = self.comboBoxStoryChapter.currentIndex()
            save(self)

            if storyType[-2:] == u"剧情" and storyType != u"特殊剧情":
                title = self.comboBoxStoryChapter.currentText().split(" ")[-1]
            elif storyType[-2:] == u"卡面":
                chapter = int(self.preTitle[-2:])
                self.preTitle = self.preTitle[:-3]
                if chapter == 1:
                    title = u"前篇"
                elif chapter == 2:
                    title = u"后篇"
                else:
                    title = u"特殊篇"
            else:
                title = u"无"
            self.lineEditTitle.setText(title)

            self.getDstFileName()
            self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

            if not self.dstText.talks:
                self.createText()
            else:
                relpy = qw.QMessageBox.question(
                    self, "", u"是否清除现有翻译内容？",
                    qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                    qw.QMessageBox.No)
                if relpy == qw.QMessageBox.Yes:
                    self.createText()
                if relpy == qw.QMessageBox.No:
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
            if not self.ListManager.events:
                qw.QMessageBox.information(self, "", u"请先刷新")
                return
            chapterList = [self.comboBoxStoryChapter.currentIndex()]
            if self.checkBoxAll.isChecked():
                chapterList = []
                for idx in range(self.comboBoxStoryChapter.count()):
                    if self.comboBoxStoryChapter.itemText(idx):
                        chapterList.append(idx)

            countList = [{'name': self.chars[i]["name_j"], "count": [0 for i in range(len(chapterList) + 1)]} for i in range(26)]
            storyType = self.comboBoxStoryType.currentText()
            storyTypesort = self.comboBoxStoryTypeSort.currentText()
            storyIdx = self.comboBoxStoryIndex.currentIndex()
            source = self.comboBoxDataSource.currentText()
            for idx, chapterIdx in enumerate(chapterList):
                _, jsonname, jsonurl = self.ListManager.getJsonPath(
                    storyType, storyTypesort, storyIdx, chapterIdx, source)

                jsonpath = osp.join(self.datadir, jsonname)
                if osp.exists(jsonpath):
                    with open(jsonpath, 'r', encoding='UTF-8') as f:
                        fulldata = json.load(f)
                    if 'TalkData' not in fulldata:
                        f.close()
                        remove(jsonpath)
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
    def createText(self):
        self.dstText.createFile(self.srcText.talks, self.checkBoxJapanese.isChecked())
        self.getDstFileName()
        self.saved = True
        self.isNewFile = True
        self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

    def clearText(self):
        try:
            if self.dstText.talks:
                relpy = qw.QMessageBox.question(
                    self, "", u"将清除现有翻译内容，是否继续？",
                    qw.QMessageBox.Yes | qw.QMessageBox.No,
                    qw.QMessageBox.No)
                if relpy == qw.QMessageBox.No:
                    return
            self.createText()
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
        save(self)

        self.dstText.loadFile(editormode, textpath)
        self.dstText.showDiff(self.checkBoxShowDiff.isChecked())

        title = osp.basename(textpath).split(".")[0]
        title = title[title.find(" ") + 1:]
        if title and title != "[AutoSave]":
            self.lineEditTitle.setText(title)
        return True

    def setFontSize(self):
        try:
            self.fontSize = self.spinBoxFontSize.value()
            self.srcText.setFontSize(self.fontSize)
            self.dstText.setFontSize(self.fontSize)
            self.setting['fontSize'] = self.fontSize
            save(self)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"setFontsize错误\n请将“setting\\log.txt发给弃子”")

    def setSpeaker(self):
        try:
            self.dstText.showSpeakers()
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"setSpeaker错误\n请将“setting\\log.txt发给弃子”")

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
            self.lineEditTitle.blockSignals(True)
            self.getDstFileName()
            if self.dstfilepath:
                self.dstfilepath = osp.join(
                    osp.dirname(self.dstfilepath), self.dstfilename)
            self.isNewFile = True
            self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))
            self.lineEditTitle.blockSignals(False)
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
        title = self.lineEditTitle.text().replace("\\", "、").replace("/", "、")
        if title == u"无":
            return
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

                self.dstfilename = osp.basename(self.dstfilepath)
                self.lineEditTitle.blockSignals(True)
                self.lineEditTitle.setText(self.dstfilename.split(".")[0])
                self.lineEditTitle.blockSignals(False)

            if self.isNewFile and osp.exists(self.dstfilepath):
                relpy = qw.QMessageBox.question(
                    self, "", u"文件已存在，是否覆盖？",
                    qw.QMessageBox.Yes | qw.QMessageBox.No,
                    qw.QMessageBox.No)

                if relpy == qw.QMessageBox.No:
                    return

            saveN = self.checkBoxSaveN.isChecked()
            self.dstText.saveFile(self.dstfilepath, saveN)
            self.setWindowTitle("{} Sekai Text".format(self.dstfilename))
            self.saved = True
            self.isNewFile = False

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
        _exit(0)

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
            if(item.column() == 1):
                self.dstText.changeSpeaker(item, self.editormode)
            elif(item.column() == 2):
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

            currentItem = self.tableWidgetDst.item(currentRow, currentColumn)
            self.tableWidgetDst.editItem(currentItem)
            self.tableWidgetDst.blockSignals(True)
            if currentItem:
                currentItem.setText(currentItem.text().split("\n")[0].rstrip().lstrip())
            self.tableWidgetDst.blockSignals(False)
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"trackSrc错误\n请将“setting\\log.txt发给弃子”")

    def setComboBoxStoryType(self, isInt=False):
        if 'storyType' in self.setting:
            self.comboBoxStoryType.setCurrentIndex(self.setting['storyType'])

        if self.ListManager.events == []:
            return

        self.setComboBoxStoryTypeSort(isInt)

    def setComboBoxStoryTypeSort(self, isInit=False):
        storyType = self.comboBoxStoryType.currentText()
        self.comboBoxStoryIndex.setMaximumSize(qc.QSize(450, 30))
        self.comboBoxStoryChapter.setMaximumSize(qc.QSize(500, 30))
        if storyType in [u"初始地图对话", u"升级地图对话", u"追加地图对话", u"主界面语音"]:
            self.comboBoxStoryTypeSort.setVisible(True)
            self.comboBoxStoryTypeSort.clear()
            self.comboBoxStoryTypeSort.addItem(u"按人物")
            if storyType not in [u"初始地图对话", u"升级地图对话"]:
                self.comboBoxStoryTypeSort.addItem(u"按时间")
            if storyType != u"主界面语音":
                self.comboBoxStoryTypeSort.addItem(u"按地点")
                self.comboBoxStoryIndex.setMaximumSize(qc.QSize(400, 30))
                self.comboBoxStoryChapter.setMaximumSize(qc.QSize(450, 30))
            else:
                self.comboBoxStoryIndex.setMaximumSize(qc.QSize(800, 30))
        else:
            self.comboBoxStoryTypeSort.setVisible(False)
            self.comboBoxStoryTypeSort.clear()
            if storyType == u"特殊剧情":
                self.comboBoxStoryIndex.setMaximumSize(qc.QSize(1000, 30))

        if isInit and 'storyTypeSort' in self.setting:
            self.comboBoxStoryTypeSort.setCurrentIndex(self.setting['storyTypeSort'])

        self.setComboBoxStoryIndex(isInit)

        return

    def setComboBoxStoryIndex(self, isInit=False):
        storyType = self.comboBoxStoryType.currentText()
        sort = self.comboBoxStoryTypeSort.currentText()

        if u"卡面" in storyType:
            self.comboBoxStoryIndex.setMinimumSize(qc.QSize(280, 30))
        elif sort == u"按人物":
            self.comboBoxStoryIndex.setMinimumSize(qc.QSize(100, 30))
        else:
            self.comboBoxStoryIndex.setMinimumSize(qc.QSize(150, 30))

        if storyType in [u"初始地图对话", u"升级地图对话", u"追加地图对话"]:
            if sort != u"按时间":
                self.comboBoxStoryIndex.setMaximumSize(qc.QSize(200, 30))
                self.comboBoxStoryChapter.setMaximumSize(qc.QSize(650, 30))
            else:
                self.comboBoxStoryIndex.setMaximumSize(qc.QSize(400, 30))
                self.comboBoxStoryChapter.setMaximumSize(qc.QSize(450, 30))

        self.comboBoxStoryIndex.clear()
        storyIndexList = self.ListManager.getStoryIndexList(storyType, sort)
        for idx, si in enumerate(storyIndexList):
            if si == "-":
                self.comboBoxStoryIndex.insertSeparator(idx)
            else:
                self.comboBoxStoryIndex.addItem(si)

        if isInit and 'storyIdx' in self.setting:
            self.comboBoxStoryIndex.setCurrentIndex(self.setting['storyIdx'])

        self.setComboBoxStoryChapter(isInit)

        self.comboBoxDataSource.clear()
        if storyType != u"主界面语音":
            if storyType != u"自定义":
                self.comboBoxDataSource.addItem(u"sekai.best")
                self.comboBoxDataSource.addItem(u"pjsek.ai")
                self.comboBoxDataSource.addItem(u"unipjsk.com")
            self.comboBoxDataSource.addItem(u"本地文件")
            self.comboBoxDataSource.setCurrentText(u"本地文件")
        else:
            self.comboBoxDataSource.addItem(u"-")
            self.comboBoxDataSource.setCurrentText(u"-")

        return

    def setComboBoxStoryChapter(self, isInit=False):
        storyType = self.comboBoxStoryType.currentText()
        sort = self.comboBoxStoryTypeSort.currentText()
        storyIndex = self.comboBoxStoryIndex.currentIndex()

        if storyType in [u"主界面语音", u"特殊剧情"]:
            self.comboBoxStoryChapter.setVisible(False)
        else:
            self.comboBoxStoryChapter.setVisible(True)

        self.comboBoxStoryChapter.clear()
        storyChapterList = self.ListManager.getStoryChapterList(storyType, sort, storyIndex)
        for idx, sc in enumerate(storyChapterList):
            if sc == "-":
                self.comboBoxStoryChapter.insertSeparator(idx)
            else:
                self.comboBoxStoryChapter.addItem(sc)

        if isInit and 'storyChapter' in self.setting:
            self.comboBoxStoryChapter.setCurrentIndex(self.setting['storyChapter'])

        logging.info("Choose Story {} {}".format(storyType, self.comboBoxStoryIndex.currentText()))

        return

    def updateComboBox(self):
        update = updateThread(self.settingdir)
        update.trigger.connect(self.checkUpdated)

        self.tempWindow.setText(u"更新中...")
        self.tempWindow.open()
        self.downloadState = 0

        update.start()
        while not self.downloadState:
            time.sleep(0.1)
            qw.QApplication.processEvents()
        if self.downloadState == 2:
            return False

        logging.info("Story List Updated")
        self.setComboBoxStoryIndex()
        return True

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

    def checkDownload(self, successed):
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

    def checkUpdated(self, output):
        if type(output) == str:
            self.tempWindow.setText(u"下载{}列表...   ".format(output))
            return
        if type(output) == ListManager and output.events:
            self.ListManager = output
            self.downloadState = 1
        else:
            self.downloadState = 2
        self.tempWindow.close()

    def downloadFailed(self):
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
            r = requests.get(self.url, stream=True, timeout=5, proxies=localProxy)
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


class updateThread(qc.QThread):
    trigger = qc.pyqtSignal(object)
    path = ""

    def __init__(self, settingpath):
        super(updateThread, self).__init__()
        self.ListManager = ListManager(settingpath)

    def run(self):
        try:
            self.ListManager.chooseSite()
            self.trigger.emit("活动")
            self.ListManager.updateEvents()
            self.trigger.emit("卡面")
            self.ListManager.updateCards()
            self.trigger.emit("特殊卡面")
            self.ListManager.updateFestivals()
            self.trigger.emit("主线")
            self.ListManager.updateMainstory()
            self.trigger.emit("地图对话")
            self.ListManager.updateAreatalks()
            self.trigger.emit("主界面语音")
            self.ListManager.updateGreets()
            self.trigger.emit("特殊剧情")
            self.ListManager.updateSpecials()
            self.trigger.emit(self.ListManager)
            logging.info("Chapter Information Update Successed.")
        except BaseException:
            logging.error("Fail to Download Settingg File from best.")
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"更新失败\n请确认能正常访问sekai.best，且关闭代理与VPN")
            self.trigger.emit([], [], [], [])


def save(self):
    settingpath = osp.join(self.settingdir, "setting.json")
    with open(settingpath, 'w', encoding='utf-8') as f:
        json.dump(self.setting, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    app = qw.QApplication(sys.argv)

    root, _ = osp.split(osp.abspath(sys.argv[0]))
    if not getattr(sys, 'frozen', False):
        root = osp.join(root, "../")

    elif platform.system() == "Darwin":
        root = osp.join(root, '../../../')

    loggingPath = osp.join(root, "setting", "log.txt")
    if not osp.exists(osp.join(root, "setting")):
        mkdir(osp.join(root, "setting"))

    logging.basicConfig(level=logging.INFO,
                        filename=loggingPath,
                        filemode='w')
    try:
        modeSelectWinodw = qw.QMessageBox()
        modeSelectWinodw.setWindowTitle("Sekai Text")
        modeSelectWinodw.setText("校对与合意时\n强烈建议在有音画对照的条件下进行\n如看游戏内，或者对照录制视频")
        if platform.system() == "Darwin":
            checkButton = modeSelectWinodw.addButton(u"合意", 2)
            proofreadButton = modeSelectWinodw.addButton(u"校对", 2)
            translateButton = modeSelectWinodw.addButton(u"翻译", 2)
        else:
            translateButton = modeSelectWinodw.addButton(u"翻译", 2)
            proofreadButton = modeSelectWinodw.addButton(u"校对", 2)
            checkButton = modeSelectWinodw.addButton(u"合意", 2)

        mainform = mainForm(root)
        translateButton.clicked.connect(mainform.translateMode)
        proofreadButton.clicked.connect(mainform.proofreadMode)
        checkButton.clicked.connect(mainform.checkMode)

        modeSelectWinodw.exec_()
        mainform.show()
        atexit.register(save, mainform)
        app.exec_()
    except BaseException:
        exc_type, exc_value, exc_traceback_obj = sys.exc_info()
        with open(loggingPath, 'a') as f:
            traceback.print_exception(
                exc_type, exc_value, exc_traceback_obj, file=f)
