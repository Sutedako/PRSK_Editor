from __future__ import unicode_literals

import atexit
import sys

import PyQt5.QtWidgets as qw
from mainGUI import Ui_SekaiText
from PyQt5.QtWidgets import QTableWidgetSelectionRange
from PyQt5.QtGui import QKeySequence, QIcon

from Editor import Editor
from Loader import Loader

import json
import requests
import os.path as osp

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

class mainForm(qw.QMainWindow, Ui_SekaiText):

    chars = []
    events = []
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

    root = osp.join(osp.dirname(__file__), "../")
    datadir = osp.join(root, "data")
    settingdir = osp.join(root, "setting")

    setting = {}
    preStoryType = ""

    def __init__(self):
        super().__init__()
        iconpath = osp.join(self.root, "image/icon/32.ico")
        if osp.exists(iconpath):
            self.setWindowIcon(QIcon(iconpath))

        settingpath = osp.join(self.settingdir, "setting.json")
        if osp.exists(settingpath):
            with open(settingpath, 'r', encoding='utf-8') as f:
                self.setting = json.load(f)
        if 'textdir' not in self.setting:
            self.setting['textdir'] = self.datadir

        self.setupUi(self)
        self.dstText = Editor(self.tableWidgetDst)

        chrspath = osp.join(self.settingdir, "chr.json")
        with open(chrspath, 'r', encoding='utf-8') as f:
            self.chars = json.load(f)
        eventspath = osp.join(self.settingdir, "events.json")
        if osp.exists(eventspath):
            with open(eventspath, 'r', encoding='utf-8') as f:
                self.events = json.load(f)
        cardspath = osp.join(self.settingdir, "cards.json")
        if osp.exists(cardspath):
            with open(cardspath, 'r', encoding='utf-8') as f:
                self.cards = json.load(f)
        mainstorypath = osp.join(self.settingdir, "mainStory.json")
        if osp.exists(mainstorypath):
            with open(mainstorypath, 'r', encoding='utf-8') as f:
                self.mainstory = json.load(f)

        if 'storyType' in self.setting:
            self.comboBoxStoryType.setCurrentIndex(self.setting['storyType'])
        self.setComboBox(True)

        self.comboBoxStoryType.activated.connect(lambda: self.setComboBox(False))
        self.comboBoxStoryIndex.activated.connect(lambda: self.setComboBox(False))
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
        if not self.event:
            return
        storyType = self.comboBoxStoryType.currentText()
        source = self.comboBoxDataSource.currentText()

        if storyType == u"主线剧情":
            unitIdx = self.comboBoxStoryIndex.currentIndex()
            unit = self.mainstory[unitIdx]["unit"].replace("_", "-")
            chapterIdx = self.comboBoxStoryChapter.currentIndex()
            if unitIdx == 0:
                sekai = "vs" + sekaiDict[int((chapterIdx + 1)/ 5)]
            else:
                sekai = sekaiDict[unitIdx - 1]
            if unitIdx == 0:
                chapter = str(chapterIdx % 4).zfill(2)
            else:
                chapter = str(chapterIdx).zfill(2)
            jsonname = "mainStory_{}_{}.json".format(sekai, chapter)
            jsonurl = "https://assets.pjsek.ai/file/" \
                "pjsekai-assets/startapp/scenario/unitstory/" \
                "{}-story-chapter/{}_01_{}.json".format(unit, sekai, chapter)
            self.preTitle = "{}-{}".format(sekai, chapter)

        elif storyType == u"活动剧情":
            eventId = len(self.events) - self.comboBoxStoryIndex.currentIndex()
            event = self.events[int(eventId) - 1]['name']
            eventId = str(eventId).zfill(2)
            chapter = str(self.comboBoxStoryChapter.currentIndex() + 1).zfill(2)

            jsonname = "event_{}_{}.json".format(eventId, chapter)
            jsonurl = "https://assets.pjsek.ai/file/" \
                "pjsekai-assets/ondemand/event_story/" \
                "{}/scenario/event_{}_{}.json".format(event, eventId, chapter)
            self.preTitle = "{}-{}".format(eventId, chapter)

        elif storyType == u"活动卡面":
            eventId = len(self.events) - self.comboBoxStoryIndex.currentIndex()
            cardId = self.events[eventId - 1]["cards"][int(self.comboBoxStoryChapter.currentIndex() / 3)]
            charId = self.cards[cardId - 1]["characterId"]
            count = str(self.cards[cardId - 1]["cardCount"]).zfill(3)
            chapter = str(self.comboBoxStoryChapter.currentIndex() % 3 + 1).zfill(2)
            eventId = str(eventId).zfill(2)
            charname = self.chars[charId - 1]['name']
            jsonname = "event_{}_{}_{}.json".format(eventId, charname, chapter)
            charId = str(charId).zfill(3)
            jsonurl = "https://assets.pjsek.ai/file/" \
                "pjsekai-assets/startapp/character/member/" \
                "res{}_no{}/{}{}_{}{}.json".format(charId, count, charId, count, charname, chapter)
            self.preTitle = "{}-{}-{}".format(eventId, charname, chapter)

        elif storyType == u"初始卡面":
            currentIdx = self.comboBoxStoryIndex.currentIndex()
            charId = currentIdx - 4 if currentIdx > 25 else int(currentIdx / 5) * 4 + (currentIdx + 1) % 5
            charname = self.chars[charId - 1]['name']
            rarity = str(int(self.comboBoxStoryChapter.currentIndex() / 3) + 1).zfill(3)
            chapter = str(self.comboBoxStoryChapter.currentIndex() % 3 + 1).zfill(2)
            jsonname = "release_{}_{}_{}.json".format(charname, rarity, chapter)
            charId = str(charId).zfill(3)
            jsonurl = "https://assets.pjsek.ai/file/" \
                "pjsekai-assets/startapp/character/member/" \
                "res{}_no{}/{}{}_{}{}.json".format(charId, rarity, charId, rarity, charname, chapter)
            self.preTitle = "00-{}-{}-{}".format(charname, rarity, chapter)

        jsonpath = osp.join(self.datadir, jsonname)

        if source == "sekai.best(暂不支持)":
            return
        elif source == "pjsek.ai":
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
        self.setting['storyIdx'] = self.comboBoxStoryIndex.currentIndex()
        self.setting['storyChapter'] = self.comboBoxStoryChapter.currentIndex()
        save(self)

        if storyType[-2:] != u"卡面":
            title = self.comboBoxStoryChapter.currentText().split(" ")[-1]
            self.plainTextEditTitle.setPlainText(title)

        if not self.dstText.talks:
            self.createText()
        else:
            self.dstText.loadJson(self.srcText.talks)

    # create new text for json 
    def createText(self):
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

    def openText(self, editormode):
        self.checkSave()
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
            if self.loadText(textpath, 0):
                return

            relpy = qw.QMessageBox.question(
                self, "", u"是否从头开始？", 
                qw.QMessageBox.Yes | qw.QMessageBox.No,
                qw.QMessageBox.Yes)

            if relpy == qw.QMessageBox.No:
                textpath, _ = qw.QFileDialog.getOpenFileName(
                    self, u"选取校对文本", self.setting['textdir'], "Text Files (*.txt)")
                if self.loadText(textpath, 1):
                    return
                self.dstfilename = osp.basename(textpath)
                self.dstfilepath = textpath
                self.saved = True
                self.isNewFile = False
                self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

            else:
                self.getDstFileName()
                self.dstfilepath = osp.join(osp.dirname(textpath), self.dstfilename)
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
                    self, u"选取翻译文本", self.setting['textdir'], "Text Files (*.txt)")
                if self.loadText(textpath, 0):
                    return

                relpy = qw.QMessageBox.question(
                    self, "", u"是否从头开始？", 
                    qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                    qw.QMessageBox.Yes)

                if relpy == qw.QMessageBox.Yes:
                    textpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取校对文本", self.setting['textdir'], "Text Files (*.txt)")
                    if self.loadText(textpath, 2):
                        return
                    self.getDstFileName()
                    self.dstfilepath = osp.join(osp.dirname(textpath), self.dstfilename)
                    self.saved = False
                    self.isNewFile = False
                    self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

                elif relpy == qw.QMessageBox.No:
                    textpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取合意文本", self.setting['textdir'], "Text Files (*.txt)")
                    if self.loadText(textpath, 2):
                        return
                    self.dstfilename = osp.basename(textpath)
                    self.dstfilepath = textpath
                    self.saved = True
                    self.isNewFile = False
                    self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

            elif relpy == qw.QMessageBox.No:
                textpath, _ = qw.QFileDialog.getOpenFileName(
                    self, u"选取校对文本", self.setting['textdir'], "Text Files (*.txt)")
                if self.loadText(textpath, 0):
                    return

                relpy = qw.QMessageBox.question(
                    self, "", u"是否从头开始？", 
                    qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                    qw.QMessageBox.Yes)

                if relpy == qw.QMessageBox.No:
                    textpath, _ = qw.QFileDialog.getOpenFileName(
                        self, u"选取合意文本", self.setting['textdir'], "Text Files (*.txt)")
                    if self.loadText(textpath, 1):
                        return
                    self.dstfilename = osp.basename(textpath)
                    self.dstfilepath = textpath
                    self.saved = True
                    self.isNewFile = False
                    self.setWindowTitle("{} Sekai Text".format(self.dstfilename))

                else:
                    self.getDstFileName()
                    self.dstfilepath = osp.join(osp.dirname(textpath), self.dstfilename)
                    self.saved = False
                    self.isNewFile = True
                    self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))

    def loadText(self, textpath, editormode):
        if not textpath:
            return False
        self.setting['textdir'] = osp.dirname(textpath)

        self.dstText.loadFile(
            editormode, textpath)
        self.dstText.showDiff(self.checkBoxShowDiff.isChecked())

        title = osp.basename(textpath).split(" ")[-1].split(".")[0]
        if title:
            self.plainTextEditTitle.setPlainText(title)
        return True

    def checkLines(self):
        self.dstText.checkLines(self.dstText.talks)

    def changeTitle(self):
        self.plainTextEditTitle.blockSignals(True)
        self.getDstFileName()
        if self.dstfilepath:
            self.dstfilepath = osp.join(osp.dirname(self.dstfilepath), self.dstfilename)
        self.isNewFile = True
        self.setWindowTitle("*{} Sekai Text".format(self.dstfilename))
        self.plainTextEditTitle.blockSignals(False)

    def getDstFileName(self):
        storyType = self.comboBoxStoryType.currentText()
        idx = self.comboBoxStoryIndex.currentText().split(" ")[0].zfill(2)
        chapter = self.comboBoxStoryChapter.currentText().zfill(2)

        self.dstfilename = u"【{}】{}.txt".format(
            EditorMode[self.editormode], self.preTitle)
        title = self.plainTextEditTitle.toPlainText()
        if not title and storyType[-2:] != u"卡面":
            title = "Untitled"
        if title:
            self.dstfilename = self.dstfilename[:-4] + " {}.txt".format(title)
        self.plainTextEditTitle.setPlainText(title)

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
            self.saveText()

    def saveText(self):
        if not self.dstfilepath:
            self.dstfilepath = osp.join(self.setting['textdir'], self.dstfilename)
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
        self.dstText.saveFile(self.dstfilepath)
        self.saved = True
        self.dstfilename = osp.basename(self.dstfilepath)
        self.plainTextEditTitle.setPlainText(self.dstfilename)
        if " " in self.dstfilename:
            title = self.dstfilename.split(".")[0].split(" ")[-1]
            if title:
                self.plainTextEditTitle.setPlainText(title)
        self.plainTextEditTitle.blockSignals(False)
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

    def setComboBox(self, isInit=False):
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
            unitId = self.comboBoxStoryIndex.currentIndex()
            for idx, chapter in enumerate(self.mainstory[unitId]["chapters"]):
                epNo = idx - 1
                if unitId == 0:
                    epNo = idx % 4
                self.comboBoxStoryChapter.addItem(str(epNo + 1) + " " + chapter)
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
            eventId = len(self.events) - self.comboBoxStoryIndex.currentIndex()
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
            eventId = len(self.events) - self.comboBoxStoryIndex.currentIndex()
            for cardId in self.events[eventId - 1]['cards']:
                self.comboBoxStoryChapter.addItem(u"前篇  " + 
                    self.chars[self.cards[cardId - 1]['characterId'] - 1]['name_j'])
                self.comboBoxStoryChapter.addItem(u"后篇  " + 
                    self.chars[self.cards[cardId - 1]['characterId'] - 1]['name_j'])

            for i in range(2, 12, 3):
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
            self.comboBoxStoryChapter.addItem(u"前篇  一星")
            self.comboBoxStoryChapter.addItem(u"后篇  一星")
            self.comboBoxStoryChapter.addItem(u"前篇  二星")
            self.comboBoxStoryChapter.addItem(u"后篇  二星")
            self.comboBoxStoryChapter.addItem(u"前篇  三星")
            self.comboBoxStoryChapter.addItem(u"后篇  三星")
            self.comboBoxStoryChapter.insertSeparator(2)
            self.comboBoxStoryChapter.insertSeparator(5)
            if self.comboBoxStoryIndex.currentText() in [u"一歌", u"ミク", u"リン", u"レン"]:
                self.comboBoxStoryChapter.addItem(u"前篇  四星")
                self.comboBoxStoryChapter.addItem(u"后篇  四星")
                self.comboBoxStoryChapter.insertSeparator(8)

            if storyChapter:
                self.comboBoxStoryChapter.setCurrentIndex(storyChapter)

        self.preStoryType = storyType

    def updateComboBox(self):
        self.events, self.cards, mainstory = self.srcText.update(self.settingdir)
        if mainstory:
            self.mainstory = mainstory
        self.setComboBox()

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
        
    def judgeMode(self):
        self.radioButtonJudge.setChecked(True)
        self.editormode = 3
        self.dstText.isProofReading = False

def save(self):
    settingpath = osp.join(self.settingdir, "setting.json")
    with open(settingpath, 'w', encoding='utf-8') as f:
        json.dump(self.setting, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    app = qw.QApplication(sys.argv)
    modeSelectWinodw = qw.QMessageBox()
    modeSelectWinodw.setWindowTitle("Sekai Text")
    translateButton = modeSelectWinodw.addButton(u"翻译", 2)
    proofreadButton = modeSelectWinodw.addButton(u"校对", 2)
    checkButton = modeSelectWinodw.addButton(u"合意", 2)
    # judgeButton = modeSelectWinodw.addButton(u"审核", 2)

    mainform = mainForm()
    translateButton.clicked.connect(mainform.translateMode)
    proofreadButton.clicked.connect(mainform.proofreadMode)
    checkButton.clicked.connect(mainform.checkMode)
    # judgeButton.clicked.connect(mainform.judgeMode())

    modeSelectWinodw.exec_()
    mainform.show()
    atexit.register(save, mainform)
    app.exec_()
