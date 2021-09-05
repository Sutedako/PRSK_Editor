from __future__ import unicode_literals

import atexit
import sys

import PyQt5.QtWidgets as qw
from mainGUI import Ui_SekaiText
from PyQt5.QtWidgets import QTableWidgetSelectionRange
from PyQt5.QtGui import QKeySequence

from Editor import Editor
from Loader import Loader

import json
import requests
import os.path as osp

EditorMode = [u'翻译', u'校对', u'合意', u'审核']

class mainForm(qw.QMainWindow, Ui_SekaiText):

    chars = []
    events = []
    saved = True
    editormode = 0

    srcText = Loader()
    dstText = Editor()
    dstfilename = ""
    dstfilepath = ""

    root = osp.join(osp.dirname(__file__), "../")
    datadir = osp.join(root, "data")
    settingdir = osp.join(root, "setting")

    setting = {}

    def __init__(self):
        super().__init__()

        settingpath = osp.join(self.settingdir, "setting.json")
        if osp.exists(settingpath):
            with open(settingpath, 'r', encoding='utf-8') as f:
                self.setting = json.load(f)
        if 'textdir' not in self.setting:
            self.setting['textdir'] = self.datadir

        self.setupUi(self)
        self.dstText = Editor(self.tableWidgetDst)

        chrpath = osp.join(self.settingdir, "chr.json")
        with open(chrpath, 'r', encoding='utf-8') as f:
            self.chars = json.load(f)
        eventpath = osp.join(self.settingdir, "events.json")
        with open(eventpath, 'r', encoding='utf-8') as f:
            self.events = json.load(f)

        self.setComboBox()

        if 'storyType' in self.setting:
            self.comboBoxStoryType.setCurrentIndex(self.setting['storyType'])
        if 'storyIdx' in self.setting:
            self.comboBoxStoryIndex.setCurrentIndex(self.setting['storyIdx'])
        if 'storyChapter' in self.setting:
            self.comboBoxStoryChapter.setCurrentIndex(self.setting['storyChapter'])


        self.comboBoxStoryType.activated.connect(self.setComboBox)
        self.pushButtonRefresh.clicked.connect(self.updateComboBox)

        self.pushButtonLoad.clicked.connect(self.loadJson)
        self.pushButtonCreate.clicked.connect(self.createText)

        self.radioButtonTranslate.clicked.connect(self.translateMode)
        self.radioButtonProofread.clicked.connect(self.proofreadMode)
        self.radioButtonCheck.clicked.connect(self.checkMode)
        self.radioButtonJudge.clicked.connect(self.judgeMode)
        
        self.pushButtonOpen.clicked.connect(self.openText)
        self.pushButtonSave.clicked.connect(self.saveText)
        self.pushButtonCheck.clicked.connect(self.checkLines)
        self.plainTextEditTitle.textChanged.connect(self.changeTitle)
        self.checkBoxShowDiff.stateChanged.connect(self.showDiff)

        self.tableWidgetDst.currentCellChanged.connect(self.trackSrc)
        self.tableWidgetDst.itemActivated.connect(self.editText)
        self.tableWidgetDst.itemChanged.connect(self.changeText)

        qw.QShortcut(QKeySequence(self.tr("Ctrl+S")), self, self.saveText)

    def loadJson(self):
        # TODO only for event now
        storyType = self.comboBoxStoryType.currentText()
        source = self.comboBoxDataSource.currentText()
        idx = self.comboBoxStoryIndex.currentText().split(" ")[0]
        event = self.events[int(idx) - 1]
        idx = idx.zfill(2)
        chapter = self.comboBoxStoryChapter.currentText().zfill(2)

        jsonname = "event_{}_{}.json".format(idx, chapter)
        jsonpath = osp.join(self.datadir, jsonname)

        if source == "pjsek.ai":
            jsonurl = "https://assets.pjsek.ai/file/" \
                "pjsekai-assets/ondemand/event_story/" \
                "{}/scenario/event_{}_{}.json".format(event, idx, chapter)
            jsondata = json.loads(requests.get(jsonurl).text)
            with open(jsonpath, 'w', encoding='utf-8') as f:
                json.dump(jsondata, f, indent=2, ensure_ascii=False)
            self.comboBoxDataSource.setCurrentText(u"本地文件")
        elif source == u"本地文件":
            if not osp.exists(jsonpath):
                jsonpath, _ = qw.QFileDialog.getOpenFileName(
                    self, u"选取文件", self.datadir, "Json Files (*.json)")

        if not jsonpath:
            return

        self.srcText = Loader(jsonpath, self.tableWidgetSrc)

        self.setting['storyType'] = self.comboBoxStoryType.currentIndex()
        self.setting['storyidx'] = self.comboBoxStoryIndex.currentIndex()
        self.setting['storyChapter'] = self.comboBoxStoryChapter.currentIndex()

        if not self.dstText.talks:
            self.createText()
        else:
            self.dstText.loadJson(self.srcText.talks)

    def createText(self):
        self.dstText.createFile(self.srcText.talks)
        self.getDstFileName()
        self.saved = True
        self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

    def openText(self, editormode):
        self.checkSave()
        if self.editormode == 0:
            textpath, _ = qw.QFileDialog.getOpenFileName(
                self, u"选取翻译文本", self.setting['textdir'], "Text Files (*.txt)")
            self.loadText(textpath, 0)
            self.dstfilename = osp.basename(textpath)
            self.dstfilepath = textpath
            self.saved = True
            self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

        elif self.editormode == 1:
            textpath, _ = qw.QFileDialog.getOpenFileName(
                self, u"选取翻译文本", self.setting['textdir'], "Text Files (*.txt)")
            self.loadText(textpath, 0)
            if not textpath:
                return

            relpy = qw.QMessageBox.question(
                self, "", u"是否从头开始？", 
                qw.QMessageBox.Yes | qw.QMessageBox.No,
                qw.QMessageBox.Yes)

            if relpy == qw.QMessageBox.No:
                textpath, _ = qw.QFileDialog.getOpenFileName(
                    self, u"选取校对文本", self.setting['textdir'], "Text Files (*.txt)")
                self.loadText(textpath, 1)
                self.dstfilename = osp.basename(textpath)
                self.dstfilepath = textpath
                self.saved = True
                self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

            else:
                self.getDstFileName()
                self.dstfilepath = osp.join(osp.dirname(textpath), self.dstfilename)
                self.saved = False
                self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

        elif self.editormode == 2:
            relpy = qw.QMessageBox.question(
                self, "", u"是否与翻译文件对比？", 
                qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                qw.QMessageBox.Yes)

            if relpy == qw.QMessageBox.Yes:
                textpath, _ = qw.QFileDialog.getOpenFileName(
                    self, u"选取翻译文本", self.setting['textdir'], "Text Files (*.txt)")
                self.loadText(textpath, 0)
                if not textpath:
                    return

                relpy = qw.QMessageBox.question(
                    self, "", u"是否从头开始？", 
                    qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                    qw.QMessageBox.Yes)

                if relpy == qw.QMessageBox.Yes:
                    textpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取校对文本", self.setting['textdir'], "Text Files (*.txt)")
                    self.loadText(textpath, 2)
                    self.getDstFileName()
                    self.dstfilepath = osp.join(osp.dirname(textpath), self.dstfilename)
                    self.saved = False
                    self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

                elif relpy == qw.QMessageBox.No:
                    textpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取合意文本", self.setting['textdir'], "Text Files (*.txt)")
                    self.loadText(textpath, 2)
                    self.dstfilename = osp.basename(textpath)
                    self.dstfilepath = textpath
                    self.saved = True
                    self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

            elif relpy == qw.QMessageBox.No:
                textpath, _ = qw.QFileDialog.getOpenFileName(
                    self, u"选取校对文本", self.setting['textdir'], "Text Files (*.txt)")
                self.loadText(textpath, 0)
                if not textpath:
                    return

                relpy = qw.QMessageBox.question(
                    self, "", u"是否从头开始？", 
                    qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                    qw.QMessageBox.Yes)

                if relpy == qw.QMessageBox.No:
                    textpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取合意文本", self.setting['textdir'], "Text Files (*.txt)")
                    self.loadText(textpath, 1)
                    self.dstfilename = osp.basename(textpath)
                    self.dstfilepath = textpath
                    self.saved = True
                    self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

                else:
                    self.getDstFileName()
                    self.dstfilepath = osp.join(osp.dirname(textpath), self.dstfilename)
                    self.saved = False
                    self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

    def loadText(self, textpath, editormode):
        if not textpath:
            return
        self.setting['textdir'] = osp.dirname(textpath)

        self.dstText.loadFile(
            editormode, textpath, self.srcText.talks)
        self.dstText.showDiff(self.checkBoxShowDiff.isChecked())

        title = osp.basename(textpath).split(" ")[-1].split(".")[0]
        if title:
            self.plainTextEditTitle.setPlainText(title)

    def checkLines(self):
        self.dstText.checkLines(self.dstText.talks)

    def changeTitle(self):
        self.getDstFileName()
        if self.dstfilepath:
            self.dstfilepath = osp.join(osp.dirname(self.dstfilepath), self.dstfilename)
        self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

    def getDstFileName(self):
        idx = self.comboBoxStoryIndex.currentText().split(" ")[0].zfill(2)
        chapter = self.comboBoxStoryChapter.currentText().zfill(2)
        self.dstfilename = u"【{}】{}-{}.txt".format(
            EditorMode[self.editormode], idx, chapter)
        title = self.plainTextEditTitle.toPlainText()
        if title:
            self.dstfilename = self.dstfilename[:-4] + " {}.txt".format(title)

    def checkSave(self):
        if self.saved:
            return

        relpy = qw.QMessageBox.question(
            self, "", u"修改尚未保存，是否保存？", 
            qw.QMessageBox.Yes | qw.QMessageBox.No,
            qw.QMessageBox.Yes)

        if relpy == qw.QMessageBox.No:
            return

        elif relpy == qw.QMessageBox.Yes:
            if not self.dstfilepath:
                self.dstfilepath = osp.join(self.setting['textdir'], self.dstfilename)
                self.dstfilepath, _ = qw.QFileDialog.getSaveFileName(
                    self, u"保存文件", self.dstfilepath, "Text Files (*.txt)")
                if not self.dstfilepath:
                    return
                self.setting['textdir'] = osp.dirname(self.dstfilepath)

            self.saveText()

    def saveText(self):
        self.dstText.saveFile(self.dstfilepath)
        self.saved = True
        self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

    def closeEvent(self, event):
        self.checkSave()

    def editText(self, item):
        self.tableWidgetDst.editItem(item)

    def changeText(self, item):
        self.dstText.changeText(item, self.editormode)
        self.saved = False
        self.setWindowTitle(u"*{} Sekai Text".format(self.dstfilename))

    def showDiff(self, state):
        self.dstText.showDiff(state)

    def trackSrc(self, currentRow, currentColumn, previousRow, previousColumn):
        if currentColumn >= 3:
            return
        srcrow = self.tableWidgetSrc.rowCount()
        if currentRow < len(self.dstText.talks):
            srcrow = min(srcrow, self.dstText.talks[currentRow]['idx'])
            srcItem = self.tableWidgetSrc.item(srcrow - 1, 1)
            self.tableWidgetSrc.setCurrentItem(srcItem)

    def setComboBox(self):
        storyType = self.comboBoxStoryType.currentText()
        self.comboBoxStoryIndex.clear()
        self.comboBoxStoryChapter.clear()
        if storyType == u"主线剧情":
            self.comboBoxStoryIndex.addItems(
                ["LeoN", "MMJ!", "VBS", "WS", "25", "VS"])
            # TODO
            self.comboBoxStoryChapter.addItem(u"未完成")
        elif storyType == u"活动剧情":
            for idx, event in enumerate(self.events[::-1]):
                self.comboBoxStoryIndex.addItem(" ".join(
                    [str(len(self.events) - idx), event.split("_")[1]]))
            self.comboBoxStoryChapter.addItems(
                [str(i + 1) for i in range(8)])
            # TODO
        elif storyType == u"卡牌剧情":
            for char in self.chars:
                self.comboBoxStoryIndex.addItem(char)
            self.comboBoxStoryIndex.insertSeparator(4)
            self.comboBoxStoryIndex.insertSeparator(9)
            self.comboBoxStoryIndex.insertSeparator(14)
            self.comboBoxStoryIndex.insertSeparator(19)
            self.comboBoxStoryIndex.insertSeparator(24)
            # TODO which card
            self.comboBoxStoryChapter.addItem([u"未完成"])

    def updateComboBox(self):
        self.events = self.srcText.update()
        eventpath = osp.join(self.settingdir, "events.json")
        with open(eventpath, 'w', encoding='utf-8') as f:
            json.dump(self.events, f)
        self.setComboBox()

    def translateMode(self):
        self.editormode = 0
        self.dstText.isProofReading = False

    def proofreadMode(self):
        self.editormode = 1
        self.dstText.isProofReading = True
        
    def checkMode(self):
        self.editormode = 2
        self.dstText.isProofReading = True
        
    def judgeMode(self):
        self.editormode = 3
        self.dstText.isProofReading = False

def save(self):
    settingpath = osp.join(self.settingdir, "setting.json")
    with open(settingpath, 'w', encoding='utf-8') as f:
        json.dump(self.setting, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    app = qw.QApplication(sys.argv)
    mainform = mainForm()
    mainform.show()
    atexit.register(save, mainform)
    app.exec_()
