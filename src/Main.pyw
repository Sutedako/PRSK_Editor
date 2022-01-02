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
import platform

loggingPath = ""

class mainForm(qw.QMainWindow, Ui_SekaiText):

    chars = chrs
    saved = True
    editormode = 0

    srcText = Loader()
    dstText = Editor()
    preTitle = ""
    dstfilename = ""
    dstfilepath = ""

    def __init__(self, root):
        super().__init__()

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
        self.dstText = Editor(self.tableWidgetDst)

        self.tableWidgetDst.currentCellChanged.connect(self.trackSrc)
        self.tableWidgetDst.itemActivated.connect(self.editText)
        self.tableWidgetDst.itemDoubleClicked.connect(self.editText)
        self.tableWidgetDst.itemChanged.connect(self.changeText)

        qw.QShortcut(QKeySequence(self.tr("Ctrl+S")), self, self.saveText)

    def load(self, jsonname):
        try:
            jsonpath = "data"
            if getattr(sys, 'frozen', False):
                jsonpath = osp.join(sys._MEIPASS, jsonpath)
            if self.editormode == 0:
                jsonpath = osp.join(jsonpath, jsonname)
            elif self.editormode == 1:
                jsonpath = osp.join(jsonpath, jsonname)
            self.srcText = Loader(jsonpath, self.tableWidgetSrc)
            logging.info("Json Loaded")

            self.dstText.loadJson(0, self.srcText.talks)

            if osp.exists("result.txt"):
                self.dstText.loadFile(1, "result.txt")
                logging.info("Result Loaded")
            elif osp.exists("answer.txt"):
                self.dstText.loadFile(0, "answer.txt")
                logging.info("Answer Loaded")
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
        self.load("translate.json")

    def proofreadMode(self):
        self.load("proofread.json")


if __name__ == '__main__':
    app = qw.QApplication(sys.argv)

    root, _ = osp.split(osp.abspath(sys.argv[0]))
    if not getattr(sys, 'frozen', False):
        root = osp.join(root, "../")

    if platform.system() == "Darwin":
        root = osp.join(root, '../../../')

    loggingPath = osp.join(root, "log.txt")

    logging.basicConfig(level=logging.INFO,
                        filename=loggingPath,
                        filemode='w')
    try:
        modeSelectWinodw = qw.QMessageBox()
        modeSelectWinodw.setWindowTitle("Sekai Test")
        modeSelectWinodw.setText("请阅读题干与格式规范\n建议对照视频进行翻译")
        if platform.system() == "Darwin":
            proofreadButton = modeSelectWinodw.addButton(u"校对", 2)
            translateButton = modeSelectWinodw.addButton(u"翻译", 2)
        else:
            translateButton = modeSelectWinodw.addButton(u"翻译", 2)
            proofreadButton = modeSelectWinodw.addButton(u"校对", 2)

        mainform = mainForm(root)
        translateButton.clicked.connect(mainform.translateMode)
        proofreadButton.clicked.connect(mainform.proofreadMode)

        modeSelectWinodw.exec_()
        mainform.show()
        app.exec_()
    except BaseException:
        exc_type, exc_value, exc_traceback_obj = sys.exc_info()
        with open(loggingPath, 'a') as f:
            traceback.print_exception(
                exc_type, exc_value, exc_traceback_obj, file=f)
