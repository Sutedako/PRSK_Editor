from __future__ import unicode_literals

import atexit
import sys
import time
import traceback

import PyQt5.QtCore as qc
import PyQt5.QtWidgets as qw
from mainGUI import Ui_SekaiText
from PyQt5.QtGui import QKeySequence, QIcon, QBrush, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

from Editor import Editor
from JsonLoader import JsonLoader
from ListManager import ListManager
from Dictionary import unitDict, sekaiDict, characterDict
import Flashback as flashback

import json
import logging
import os.path as osp
from os import environ, mkdir, _exit, remove, listdir
import platform
from urllib import request
from enum import Enum

import requests

from playsound import playsound

EditorMode = [u'翻译', u'校对', u'合意', u'审核']

loggingPath = ""
settings = None

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
        self.dstText = Editor(realignHook = self.alignRowsHeight)
        self.preTitle = ""
        self.dstfilename = ""
        self.dstfilepath = ""

        self.setting = {}

        self.downloadState = DownloadState.NOT_STARTED

        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'}
        self.voiceUrls = {
            "bestVoice" : "https://storage.sekai.best/sekai-jp-assets/sound/scenario/voice/{}.mp3",
            "harukiVoice": "https://sekai-assets-bdf29c81.seiunx.net/jp-assets/ondemand/sound/scenario/voice/{}.mp3",
        }
        self.nowDownloadVoiceURL = ""
        self.mediaPlayer = QMediaPlayer()

        settingpath = osp.join(self.settingdir, "setting.json")
        if osp.exists(settingpath):
            with open(settingpath, 'r', encoding='utf-8') as f:
                self.setting = json.load(f)
                logging.info("Setting File Loaded: {}".format(settingpath))
        else:
            logging.warning("Setting File not Exists: {}".format(settingpath))
        if 'textdir' not in self.setting:
            self.setting['textdir'] = self.datadir
        if 'syncScroll' not in self.setting:
            self.setting['syncScroll'] = False
        if 'showFlashback' not in self.setting:
            self.setting['showFlashback'] = True
        if 'saveVoice' not in self.setting:
            self.setting['saveVoice'] = False
        if 'disabelSSLcheck' not in self.setting:
            self.setting['disabelSSLcheck'] = False
        if 'downloadTarget' not in self.setting:
            self.setting['downloadTarget'] = "Haruki"
        if 'fontSize' not in self.setting:
            self.setting['fontSize'] = 18

        save(self)

        self.tempVoicePath = osp.join(root, "temp")
        if not osp.exists(self.tempVoicePath):
            mkdir(self.tempVoicePath)

        logging.info("Text Folder Path: {}".format(self.setting['textdir']))
        self.fontSize = self.setting['fontSize']

        self.createSettingWindow()

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
        
        self.flashback = flashback.FlashbackAnalyzer(listManager = self.ListManager)

        self.setupUi(self)
        self.spinBoxFontSize.setValue(self.fontSize)
        self.dstText = Editor(self.tableWidgetDst, fontSize=self.fontSize, realignHook = self.alignRowsHeight)
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
        self.voiceEnableButton.clicked.connect(self.enableVoice)
        self.pushButtonCount.clicked.connect(self.countSpeaker)

        self.radioButtonTranslate.clicked.connect(self.translateMode)
        self.radioButtonProofread.clicked.connect(self.proofreadMode)
        self.radioButtonCheck.clicked.connect(self.checkMode)

        self.pushButtonOpen.clicked.connect(self.openText)
        self.pushButtonSave.clicked.connect(self.saveText)
        self.pushButtonClear.clicked.connect(self.clearText)
        # self.pushButtonDebug.clicked.connect(self.alignRowsHeight)
        self.checkBoxSyncScroll.stateChanged.connect(self.toggleSyncedMode)
        self.checkBoxShowFlashback.stateChanged.connect(self.toggleFlashback)

        self.lineEditTitle.textChanged.connect(self.changeTitle)
        self.pushButtonSpeaker.clicked.connect(self.setSpeaker)
        self.pushButtonCheck.clicked.connect(self.checkLines)
        # self.spinBoxFontSize.valueChanged.connect(self.setFontSize)

        self.checkBoxShowDiff.stateChanged.connect(self.showDiff)
        # self.checkBoxSaveN.stateChanged.connect(self.saveN)

        self.settingButton.clicked.connect(self.openSettingWindow)

        self.tableWidgetDst.currentCellChanged.connect(self.trackSrc)
        self.tableWidgetDst.itemActivated.connect(self.editText)
        self.tableWidgetDst.itemClicked.connect(self.editText)
        self.tableWidgetDst.itemDoubleClicked.connect(self.editText)
        self.tableWidgetDst.itemChanged.connect(self.changeText)

        # Scroll link
        self.srcScrollLinkedDstPositionPrev = 0
        self.tableWidgetSrcScroll.valueChanged.connect(
            lambda idx: self.moveScrollBars(idx, 'source'))
        self.tableWidgetDstScroll.valueChanged.connect(
            lambda idx: self.moveScrollBars(idx, 'destination'))

        qw.QShortcut(QKeySequence(self.tr("Ctrl+S")), self, self.saveText)

        self.checkBoxShowFlashback.setChecked(self.setting['showFlashback'])
        self.checkBoxSyncScroll.setChecked(self.setting['syncScroll'])

        self.tempWindow = qw.QMessageBox(self)
        self.tempWindow.setStandardButtons(qw.QMessageBox.No)
        self.tempWindow.setWindowTitle("Sekai Text")
        self.tempWindow.button(qw.QMessageBox.No).setText("取消")
        self.tempWindow.buttonClicked.connect(self.downloadFailed)

        self.isFirstUseVoice = True
        self.voiceDownloadingWindow = qw.QMessageBox(self)
        self.voiceDownloadingWindow.setWindowTitle("Sekai Text")
        self.voiceDownloadingWindow.setStandardButtons(qw.QMessageBox.No)
        self.voiceDownloadingWindow.button(qw.QMessageBox.No).setText("取消")
        self.voiceDownloadingWindow.buttonClicked.connect(self.downloadFailed)

        if not self.checkIfSettingFileExists(root):
            settingFilesMissingWindow = qw.QMessageBox(self)
            settingFilesMissingWindow.setWindowTitle("Sekai Text")
            settingFilesMissingWindow.setText(u"检查到setting文件夹中缺少必要文件\n自动更新...")
            confirmButton = settingFilesMissingWindow.addButton("确认", qw.QMessageBox.AcceptRole)
            settingFilesMissingWindow.exec_()
            if settingFilesMissingWindow.clickedButton() == confirmButton:
                self.updateComboBox()

    def openSettingWindow(self):
        if self.settingDialog.isVisible():
            self.settingDialog.close()
        else:
            self.settingDialog.open()

    def createSettingWindow(self):
        self.settingDialog = qw.QDialog(self)
        self.settingDialog.setWindowTitle("设置")
        self.settingDialog.setMinimumSize(400, 300)
        
        # Main layout
        mainLayout = qw.QVBoxLayout()
        mainLayout.setSpacing(10)
        
        # Display settings group
        displayGroup = qw.QGroupBox("显示设置")
        displayLayout = qw.QVBoxLayout()
        
        # Font size setting
        fontSizeLayout = qw.QHBoxLayout()
        labelFontSize = qw.QLabel("字号：")
        labelFontSize.setFixedWidth(80)
        
        self.spinBoxFontSize = qw.QSpinBox()
        self.spinBoxFontSize.setMinimum(12)
        self.spinBoxFontSize.setMaximum(30)
        self.spinBoxFontSize.setSingleStep(2)
        self.spinBoxFontSize.setValue(self.fontSize)
        self.spinBoxFontSize.valueChanged.connect(self.setFontSize)
        
        fontSizeLayout.addWidget(labelFontSize)
        fontSizeLayout.addWidget(self.spinBoxFontSize)
        fontSizeLayout.addStretch(1)
        displayLayout.addLayout(fontSizeLayout)
        
        displayGroup.setLayout(displayLayout)
        
        # Text settings group
        textGroup = qw.QGroupBox("文本设置")
        textLayout = qw.QVBoxLayout()
        
        # Save linebreak setting
        saveNLayout = qw.QHBoxLayout()
        self.checkBoxSaveN = qw.QCheckBox("保存\\N")
        self.checkBoxSaveN.setChecked(True)
        self.checkBoxSaveN.stateChanged.connect(self.saveN)
        self.checkBoxSaveN.setToolTip("启用时，保存文件时会保留\\N换行符")
        
        saveNLayout.addWidget(self.checkBoxSaveN)
        saveNLayout.addStretch(1)
        textLayout.addLayout(saveNLayout)
        
        textGroup.setLayout(textLayout)
        
        # Network settings group
        networkGroup = qw.QGroupBox("网络设置")
        networkLayout = qw.QVBoxLayout()
        
        # Save voice setting
        saveVoiceLayout = qw.QHBoxLayout()
        self.settingSaveVoice = qw.QCheckBox("保存语音文件")
        self.settingSaveVoice.setChecked(self.setting.get('saveVoice', False))
        self.settingSaveVoice.stateChanged.connect(lambda state: self.updateSaveVoiceSetting(state))
        self.settingSaveVoice.setToolTip("启用时，下载的语音文件将被保存")
        
        saveVoiceLayout.addWidget(self.settingSaveVoice)
        saveVoiceLayout.addStretch(1)
        networkLayout.addLayout(saveVoiceLayout)
        
        # SSL check setting
        sslCheckLayout = qw.QHBoxLayout()
        self.settingDisableSSL = qw.QCheckBox("禁用SSL验证")
        self.settingDisableSSL.setChecked(self.setting.get('disabelSSLcheck', False))
        self.settingDisableSSL.stateChanged.connect(lambda state: self.updateSSLSetting(state))
        self.settingDisableSSL.setToolTip("如果持续链接失败，请尝试启用此选项")
        
        sslCheckLayout.addWidget(self.settingDisableSSL)
        sslCheckLayout.addStretch(1)
        networkLayout.addLayout(sslCheckLayout)
        
        # Download source selection
        downloadSourceLayout = qw.QHBoxLayout()
        labelDownloadSource = qw.QLabel("下载源：")
        labelDownloadSource.setFixedWidth(80)
        
        self.comboDownloadTarget = qw.QComboBox()
        self.comboDownloadTarget.addItems(["Haruki", "best", "ai", "Auto"])
        current_target = self.setting.get('downloadTarget', "Haruki")
        self.comboDownloadTarget.setCurrentText(current_target)
        self.comboDownloadTarget.currentTextChanged.connect(self.updateDownloadTarget)
        
        downloadSourceLayout.addWidget(labelDownloadSource)
        downloadSourceLayout.addWidget(self.comboDownloadTarget)
        downloadSourceLayout.addStretch(1)
        networkLayout.addLayout(downloadSourceLayout)

        labelVoiceDownloadTooltipL1 = qw.QLabel("🛈 语音将仅从best源（选择best项时）")
        labelVoiceDownloadTooltipL2 = qw.QLabel("　 或Haruki源（选择其它选项时）下载")
        networkLayout.addWidget(labelVoiceDownloadTooltipL1)
        networkLayout.addWidget(labelVoiceDownloadTooltipL2)
        
        networkGroup.setLayout(networkLayout)
        
        # Add groups to main layout
        mainLayout.addWidget(displayGroup)
        mainLayout.addWidget(textGroup)
        mainLayout.addWidget(networkGroup)
        mainLayout.addStretch(1)
        
        # Buttons
        buttonLayout = qw.QHBoxLayout()
        okButton = qw.QPushButton("确定")
        okButton.clicked.connect(self.settingDialog.accept)
        
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(okButton)
        
        mainLayout.addLayout(buttonLayout)
        
        self.settingDialog.setLayout(mainLayout)
        
        self.settingDialog.close()

    def updateSaveVoiceSetting(self, state):
        self.setting['saveVoice'] = bool(state)
        save(self)

    def updateSSLSetting(self, state):
        self.setting['disabelSSLcheck'] = bool(state)
        save(self)
        
    def updateDownloadTarget(self, target):
        self.setting['downloadTarget'] = target
        save(self)
    
    def playVoice(self, voice, volume, scenario_id):

        if self.setting['downloadTarget'] == "best":
            voiceUrl = self.voiceUrls["bestVoice"].format(scenario_id + "_rip/" + voice[0])
        else:
            voiceUrl = self.voiceUrls["harukiVoice"].format(scenario_id + "/" + voice[0])

        self.nowDownloadVoiceURL = voiceUrl
        voicePath = osp.join(self.tempVoicePath, voice[0] + ".mp3")

        if not osp.exists(voicePath):
            downloadVoiceTask = downloadVoiceThread(
                voiceUrl = voiceUrl,
                voicePath = voicePath,
                header = self.headers
            )
            downloadVoiceTask.trigger.connect(self.checkVoiceDownload)
            self.downloadState = DownloadState.DOWNLOADING
            downloadVoiceTask.start()

            self.voiceDownloadingWindow.setText(u"语音下载中...")
            self.voiceDownloadingWindow.show()

            while self.downloadState == DownloadState.DOWNLOADING:
                time.sleep(0.1)
                qw.QApplication.processEvents()

            if self.downloadState == DownloadState.FAILED:
                self.downloadState = DownloadState.NOT_STARTED
                if osp.exists(voicePath):
                    remove(voicePath)
                return

            self.downloadState = DownloadState.NOT_STARTED

        # Qt's mediaPlayer requires GStreamer plugins to work here on my MacOS
        # It's way too complicated so use playsound instead
        if platform.system() == "Darwin":
            try:
                playsound(voicePath, False)
            except Exception as e:
                logging.error("Fail to Load Audio File: " + voicePath)
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                with open(loggingPath, 'a') as f:
                    traceback.print_exception(
                        exc_type, exc_value, exc_traceback_obj, file=f)

                # Download seems invalid so remove it to avoid caching
                if osp.exists(voicePath):
                    remove(voicePath)

        # Unfortunately, despite playsound claims itself being cross-platform, I never get it work on my Windows PC.
        # I have no idea what is going on after investigation and installing a fork named playsound3 ...
        # So we shall just use Qt here for platforms other than Darwin I guess ...
        # However I am not sure how do we detect errors when the download is invalid and audio cannot be played.
        # Qt's functions (e.g., self.mediaPlayer.error()) seems no use here.
        # - sad yktr
        else:
            if self.mediaPlayer is None:
                self.mediaPlayer = QMediaPlayer()

            self.mediaPlayer.setVolume(int(volume[0] * 100))
            self.mediaPlayer.setMedia(QMediaContent(qc.QUrl.fromLocalFile(voicePath)))
            self.mediaPlayer.play()

    def checkIfSettingFileExists(self, root):
        requiredFiles = [
            "setting.json",
            "areatalks.json",
            "cards.json",
            "events.json",
            "festivals.json",
            "greets.json",
            "mainStory.json",
            "specials.json"
        ]

        for file in requiredFiles:
            if not osp.exists(osp.join(root, "setting", file)):
                # print(osp.join(root, "setting", file))
                return False
        return True


    def downloadJson(self, jsonname, jsonurl):
        jsonpath = osp.join(self.datadir, jsonname)
        download = downloadJsonThread(jsonpath, jsonurl)
        download.trigger.connect(self.checkDownload)

        urlText = u"下载中...<br>若耗时过长可自行前往下方地址下载" + \
            "<br><a href=\"{}\">{}</a>".format(jsonurl, jsonname) + \
            "<br><br>下载时将文件名命名为{}，替换SekaiText同目录的data文件夹中的同名文件".format(jsonname) + \
            "<br><br>若没有自动开始下载，则将打开的网页中的内容全部复制(Ctrl+A全选，Ctrl+C复制)，" + \
            "替换data文件夹中{}的内容(替换时用记事本打开即可)".format(jsonname) +\
            "<br><br>轴机用json请从pjsek.ai复制"

        self.tempWindow.setText(urlText)
        self.tempWindow.open()

        self.downloadState = DownloadState.DOWNLOADING
        download.start()
        while self.downloadState == DownloadState.DOWNLOADING:
            time.sleep(0.1)
            qw.QApplication.processEvents()
        if self.downloadState == DownloadState.FAILED:
            self.downloadState = DownloadState.NOT_STARTED
            return False
        
        self.downloadState = DownloadState.NOT_STARTED
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
                self.srcText = JsonLoader(
                    jsonpath, 
                    self.tableWidgetSrc, 
                    fontSize=self.fontSize, 
                    flashbackAnalyzer=self.flashback, 
                    playVoiceCallback=self.playVoice
                )
                self.toggleFlashback(self.checkBoxShowFlashback.isChecked())
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
                self.checkSave()
                
                relpy = qw.QMessageBox.question(
                    self, "", u"是否清除现有翻译内容？",
                    qw.QMessageBox.Yes | qw.QMessageBox.No | qw.QMessageBox.Cancel,
                    qw.QMessageBox.No)
                if relpy == qw.QMessageBox.Yes:
                    self.createText()
                    self.dstText.loadedtalks = []
                if relpy == qw.QMessageBox.No:
                    self.dstText.loadJson(self.editormode, self.srcText.talks)

                    self.dstText.dsttalks = self.dstText.checkLines(self.dstText.loadedtalks)
                    self.dstText.resetTalk(self.editormode, self.dstText.dsttalks)
            
            # Not sure why when calling setFontSize() to resize tables,
            # only a different fontSize will properly resize table headers ...
            v = self.spinBoxFontSize.value()

            # Set it to 12
            self.spinBoxFontSize.setValue(12)
            self.setFontSize()

            # Then back to actual value to properly align header heights
            self.spinBoxFontSize.setValue(v)
            self.setFontSize()

            self.alignRowsHeight()
        except BaseException:
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            qw.QMessageBox.warning(
                self, "", u"loadJson错误\n请将“setting\\log.txt发给弃子”")

    def enableVoice(self):
        if self.isFirstUseVoice:
            voiceNotionWindow = qw.QMessageBox(self)
            voiceNotionWindow.setWindowTitle("Sekai Text")
            voiceNotionWindow.setText(u"原则上，翻译，校对与合意时\n应在有音画对照的条件下进行\n如看游戏内，或者对照录制视频\n播放语音的功能只是为了方便\n请勿依赖语音进行翻译")
            voiceNotionWindow.setStandardButtons(qw.QMessageBox.Ok)
            voiceNotionWindow.button(qw.QMessageBox.Ok).setText("好的")
            voiceNotionWindow.exec_()
            self.isFirstUseVoice = False

        if not self.voiceEnableButton.isChecked():
            self.tableWidgetSrc.hideColumn(2)
        else:
            self.tableWidgetSrc.showColumn(2)

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
            
            self.alignRowsHeight()
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

            if self.checkBoxSyncScroll.isChecked():
                self.alignRowsHeight()
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
        event.accept()

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
            self.alignWithDstRowChanged(self.tableWidgetDst.currentRow() - 1)
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

            if self.checkBoxSyncScroll.isChecked():
                self.alignRowsHeight()

                # This won't work. Why?
                self.moveScrollBars(self.tableWidgetSrcScroll.value(), 'source')
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

    # Align rowHeight for 1 srcRow (srcIdx) and corresponding set of all dstRows
    # Assumes we always have sum(dstRow.height) > srcRow.height
    # Otherwise won't work
    def alignRowHeight(self, srcIdx, dstRows):
        # Reset rows to their initial state
        # arrangeRow(self.tableWidgetSrc, srcRow, self.fontSize)
        # for dstRow in dstRows: arrangeRow(self.tableWidgetDst, dstRow, self.fontSize)

        # Compute dst row heights 
        dstRowHeights = [self.tableWidgetDst.rowHeight(r) for r in dstRows]
        dstRowTotalHeight = sum(dstRowHeights)

        # targetHeight = max(
        #     self.tableWidgetSrc.rowHeight(srcRow),
        #     dstRowTotalHeight
        # )

        self.tableWidgetSrc.setRowHeight(srcIdx - 1, dstRowTotalHeight)
        # self.tableWidgetDst.setRowHeight(dstRows[-1], targetHeight - dstRowTotalHeight + dstRowHeights[-1])

    # Align rowHeight for specific dstRow
    # Assumes dstRowIdx is the only modified row in the dst text
    def alignWithDstRowChanged(self, dstRowIdx):
        dstRows = []
        srcIdx = self.dstText.talks[dstRowIdx]['idx']

        if srcIdx < 1 or srcIdx > self.tableWidgetSrc.rowCount():
            return

        # before + id
        for row in range(dstRowIdx, -1, -1):
            if self.dstText.talks[row]['idx'] != srcIdx:
                break
            dstRows.append(row) 

        # after
        for row in range(dstRowIdx + 1, len(self.dstText.talks), 1):
            if self.dstText.talks[row]['idx'] != srcIdx:
                break
            dstRows.append(row) 

        self.alignRowHeight(srcIdx, dstRows)

    # Aligns rowHeight for all possible lines (that both exists in src & dst)
    # Assumes src / dst text has continuous + monotone increasing line numbers
    def alignRowsHeight(self):
        try:
            if not self.checkBoxSyncScroll.isChecked(): return
            if len(self.dstText.talks) == 0: return
            
            lineNum = min(self.tableWidgetSrc.rowCount(), self.dstText.talks[-1]['idx'])

            dstRowPtr = 0
            for row in range(lineNum):

                dstRows = []
                srcIdx = row + 1

                # Collect all rows in the destination that connects to current source row
                while dstRowPtr < len(self.dstText.talks) and self.dstText.talks[dstRowPtr]['idx'] == (srcIdx):
                    dstRows.append(dstRowPtr)
                    dstRowPtr += 1

                self.alignRowHeight(srcIdx, dstRows)
        except BaseException:
            logging.error("Failed to align row heights. Sync disabled.")
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            self.toggleSyncedMode(False)
            return

    def prevSrcIdx(self):
        return self.dstText.talks[self.srcScrollLinkedDstPositionPrev]['idx'] - 1

    def moveScrollBars(self, idx, bar, offset = 0):

        # print("%s current: %d" % (bar, idx))
        # print("Src maximum: %d" % self.tableWidgetSrcScroll.maximum())
        # print("Dst maximum: %d" % self.tableWidgetDstScroll.maximum())
        # return
        
        if not self.checkBoxSyncScroll.isChecked(): return

        if idx < 0: return

        try:

            # Seems PyQt handles scrollbar indices differently in MacOS ...
            if platform.system() == "Darwin":
                
                self.tableWidgetSrcScroll.setValue(idx)
                self.tableWidgetDstScroll.setValue(idx)
                return

            if bar == 'source':

                # Special case - will be triggered on a complete reload etc.
                # Simply set everything to 0
                if idx == 0:
                    self.srcScrollLinkedDstPositionPrev = 0
                    self.tableWidgetDstScroll.setValue(0)
                    return
                
                # We get to the bottom
                if idx == self.tableWidgetSrcScroll.maximum():
                    self.srcScrollLinkedDstPositionPrev = self.tableWidgetDstScroll.maximum()
                    self.tableWidgetDstScroll.setValue(self.tableWidgetDstScroll.maximum())
                    return

                dirc = 0
                if self.prevSrcIdx() == idx: return
                elif self.prevSrcIdx() > idx: dirc = -1
                elif self.prevSrcIdx() < idx: dirc = +1

                for _i in range(20):
                    
                    self.srcScrollLinkedDstPositionPrev += dirc
                    
                    if self.srcScrollLinkedDstPositionPrev <= 0: break
                    if self.srcScrollLinkedDstPositionPrev >= len(self.dstText.talks): break

                    if dirc < 0:
                        # Backwards; Move to the last line of previous talk row
                        if self.prevSrcIdx() < idx:
                            # and move 1 row forward to get the correct position
                            self.srcScrollLinkedDstPositionPrev += 1
                            break
                    elif dirc > 0:
                        # Forwards; Move to the first line of next talk row
                        if self.prevSrcIdx() == idx:
                            break
                    else:
                        # print("??")
                        return

                if self.prevSrcIdx() != idx:
                    # print("??")
                    return

                if self.checkBoxShowDiff.isChecked():
                    self.tableWidgetDstScroll.setValue(self.srcScrollLinkedDstPositionPrev)
                else:
                    self.tableWidgetDstScroll.setValue(self.dstText.compressRowMap[self.srcScrollLinkedDstPositionPrev])

            elif bar == 'destination':

                # We get to the bottom
                if idx == self.tableWidgetDstScroll.maximum():
                    self.tableWidgetSrcScroll.setValue(self.tableWidgetSrcScroll.maximum())
                    return

                # TODO: Set dst scroll to next heading line to ensure sync?

                if self.checkBoxShowDiff.isChecked():
                    # print("Attempt to set src -> %d" % (self.dstText.talks[idx]['idx'] - 1))
                    self.tableWidgetSrcScroll.setValue(self.dstText.talks[idx]['idx'] - 1)
                else:
                    # print("Attempt to set src -> %d" % (self.dstText.talks[self.dstText.decompressRowMap[idx]]['idx'] - 1))
                    self.tableWidgetSrcScroll.setValue(self.dstText.talks[self.dstText.decompressRowMap[idx]]['idx'] - 1)
        
        # If we had any problem syncing scroll bars, disable the sync
        except BaseException:
            
            logging.error("Failed to sync scrollbars. Sync disabled.")
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)

            self.checkBoxSyncScroll.setCheckState(0)
            self.toggleSyncedMode(False)

    def toggleSyncedMode(self, state):

        if state != self.setting['syncScroll']:
            self.setting['syncScroll'] = state
            save(self)

        if state:
            self.alignRowsHeight()
        else:
            # This resets table row heights
            self.setFontSize()
    
    def toggleFlashback(self, state):

        if state != self.setting['showFlashback']:
            self.setting['showFlashback'] = state
            save(self)
        
        if state:
            try:
                self.srcText.showFlashback()

                # Show partial check mark when failed to analyze
                if self.srcText.major_clue is None:
                    self.checkBoxShowFlashback.blockSignals(True)
                    self.checkBoxShowFlashback.setEnabled(False)
                    self.checkBoxShowFlashback.setCheckState(1)
                    self.checkBoxShowFlashback.blockSignals(False)
                    self.checkBoxShowFlashback.setToolTip(u"无法判断本话是否包含闪回。")
                else:
                    self.checkBoxShowFlashback.blockSignals(True)
                    self.checkBoxShowFlashback.setEnabled(True)
                    self.checkBoxShowFlashback.setCheckState(2)
                    self.checkBoxShowFlashback.blockSignals(False)
                    self.checkBoxShowFlashback.setToolTip(u"推测的剧情id: %s" % self.srcText.major_clue)

            except BaseException:

                logging.error("Failed to check flashbacks. Feature disabled.")
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                with open(loggingPath, 'a') as f:
                    traceback.print_exception(
                        exc_type, exc_value, exc_traceback_obj, file=f)

                self.checkBoxShowFlashback.setCheckState(0)
                self.setting['showFlashback'] = False
                save(self)
                self.srcText.hideFlashback()
        else:
            self.srcText.hideFlashback()

    def setComboBoxStoryType(self, isInit=False):
        if 'storyType' in self.setting:
            self.comboBoxStoryType.setCurrentIndex(self.setting['storyType'])

        if self.ListManager.events == []:
            return

        self.setComboBoxStoryTypeSort(isInit)

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
                # self.comboBoxDataSource.addItem(u"pjsek.ai")
                self.comboBoxDataSource.addItem(u"haruki (CN)")
                self.comboBoxDataSource.addItem(u"haruki (JP)")
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
        self.tempWindow.setWindowTitle(u"SeKai Text")
        self.tempWindow.setText(u"选择源网站中...")
        self.tempWindow.open()
        self.downloadState = DownloadState.DOWNLOADING

        update.start()
        while self.downloadState == DownloadState.DOWNLOADING:
            time.sleep(0.1)
            qw.QApplication.processEvents()
        if self.downloadState == DownloadState.FAILED:
            self.downloadState = DownloadState.NOT_STARTED
            return False
        
        self.downloadState = DownloadState.NOT_STARTED

        logging.info("Story List Updated")
        self.setComboBoxStoryIndex()

        try:
            self.flashback = flashback.FlashbackAnalyzer(listManager = self.ListManager)
        except BaseException:
            logging.error("Fail to update flashback info from updated chapter infomation.")
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)

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
            self.downloadState = DownloadState.SUCCESSED
        else:
            urlText = self.tempWindow.text().replace(
                "下载中...<br>若耗时过长",
                "下载失败，请确认代理与VPN关闭<br>随后点击下方链接确认Json文件是否存在<br>也")
            self.tempWindow.setStandardButtons(qw.QMessageBox.Ok)
            self.tempWindow.setText(urlText)
            self.tempWindow.close()
            self.tempWindow.exec()
            self.downloadState = DownloadState.FAILED

    def checkUpdated(self, output):
        if type(output) == list:
            self.tempWindow.setText(u"使用{}网站<br>下载{}列表...   ".format(output[0], output[1]))
            return
        if type(output) == ListManager and output.events:
            self.ListManager = output
            self.downloadState = DownloadState.SUCCESSED
        if type(output) == str and output == "No site selected":
            networkErrorWindow = qw.QMessageBox(self)
            networkErrorWindow.setWindowTitle(u"SeKai Text")
            networkErrorWindow.setText(u"更新失败\n请确认能正常访问sekai.best，且关闭代理与VPN\n"
                                       u"若反复尝试仍无法更新，请试试重启Sekai Text")
            confirmButton = networkErrorWindow.addButton(u"确认", qw.QMessageBox.AcceptRole)
            networkErrorWindow.exec()
            if networkErrorWindow.clickedButton() == confirmButton:
                self.tempWindow.close()
                self.downloadState = DownloadState.FAILED
        else:
            self.downloadState = DownloadState.FAILED
        self.tempWindow.close()

    def checkVoiceDownload(self, successed):
        if successed:
            self.voiceDownloadingWindow.close()
            self.downloadState = DownloadState.SUCCESSED
        else:
            msgBox = qw.QMessageBox(self)
            msgBox.setWindowTitle("Sekai Text")
            
            label = qw.QLabel(
                u"语音下载失败<br>请确认代理与VPN关闭<br>"
                "如仍无法下载，请到以下网址自行查看：<br>"
                "<a href=\"" + self.nowDownloadVoiceURL + "\">" + "请点这里" + "</a>"
            )
            label.setTextFormat(qc.Qt.RichText)
            label.setTextInteractionFlags(qc.Qt.TextBrowserInteraction)
            label.setOpenExternalLinks(True)
            
            layout = msgBox.layout()
            layout.addWidget(label, 0, 0, 1, layout.columnCount(), qc.Qt.AlignCenter)
            
            msgBox.setStandardButtons(qw.QMessageBox.Ok)
            msgBox.button(qw.QMessageBox.Ok).setText(u"确认")
            
            msgBox.exec()
            self.voiceDownloadingWindow.close()

            self.downloadState = DownloadState.FAILED

    def downloadFailed(self):
        self.downloadState = DownloadState.FAILED


class downloadJsonThread(qc.QThread):
    trigger = qc.pyqtSignal(bool)
    path = ""
    url = ""

    def __init__(self, jsonpath, jsonurl):
        super(downloadJsonThread, self).__init__()
        self.path = jsonpath
        self.url = jsonurl

    def run(self):
        try:
            r = requests.get(self.url, stream=True, timeout=5, proxies=request.getproxies())
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


class downloadVoiceThread(qc.QThread):
    trigger = qc.pyqtSignal(bool)
    path = ""
    url = ""

    def __init__(self, voicePath, voiceUrl, header):
        super(downloadVoiceThread, self).__init__()
        self.path = voicePath
        self.url = voiceUrl
        self.header = header

    def run(self):
        try:
            r = requests.get(
                self.url, 
                headers=self.header,
                proxies=request.getproxies()
            )
            with open(self.path, 'wb') as f:
                f.write(r.content)
            logging.info("Voice File Saved: " + self.path)
            self.trigger.emit(True)
        except BaseException:
            logging.error("Fail to Download Voice File.")
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            self.trigger.emit(False)
            return


class updateThread(qc.QThread):
    trigger = qc.pyqtSignal(object)
    path = ""

    def __init__(self, settingpath):
        super(updateThread, self).__init__()
        self.ListManager = ListManager(settingpath)

    def run(self):
        try:
            site = self.ListManager.chooseSite()
            if site == "":  # No site selected
                # print("No site selected")
                logging.error("Fail to Download Setting File from best.")
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                with open(loggingPath, 'a') as f:
                    traceback.print_exception(
                        exc_type, exc_value, exc_traceback_obj, file=f)
                self.trigger.emit("No site selected")
                return
                
            self.trigger.emit([site, "活动"])
            self.ListManager.updateEvents()
            self.trigger.emit([site, "卡面"])
            self.ListManager.updateCards()
            self.trigger.emit([site, "特殊卡面"])
            self.ListManager.updateFestivals()
            self.trigger.emit([site, "主线"])
            self.ListManager.updateMainstory()
            self.trigger.emit([site, "地图对话"])
            self.ListManager.updateAreatalks()
            self.trigger.emit([site, "主界面语音"])
            self.ListManager.updateGreets()
            self.trigger.emit([site, "特殊剧情"])
            self.ListManager.updateSpecials()
            self.trigger.emit([site, "推断语音ID"])
            self.ListManager.inferVoiceEventID()
            self.trigger.emit(self.ListManager)
            logging.info("Chapter Information Update Successed.")
        except BaseException:
            logging.error("Fail to Update Chapter Information.")
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            with open(loggingPath, 'a') as f:
                traceback.print_exception(
                    exc_type, exc_value, exc_traceback_obj, file=f)
            self.trigger.emit("No site selected")
            return


class DownloadState(Enum):
    DOWNLOADING = 0
    SUCCESSED = 1
    FAILED = 2
    NOT_STARTED = 3


def onExit():
    if not mainform.setting['saveVoice']:
        for file in listdir(mainform.tempVoicePath):
            remove(osp.join(mainform.tempVoicePath, file))

    save(mainform)


def save(self):
    settingpath = osp.join(self.settingdir, "setting.json")
    with open(settingpath, 'w', encoding='utf-8') as f:
        json.dump(self.setting, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    # if hasattr(qc.Qt, 'AA_EnableHighDpiScaling'):
    #     qw.QApplication.setAttribute(qc.Qt.AA_EnableHighDpiScaling, True)
    # if hasattr(qc.Qt, 'AA_UseHighDpiPixmaps'):
    #     qw.QApplication.setAttribute(qc.Qt.AA_UseHighDpiPixmaps, True)
    # environ["QT_ENABLE_HIGHDPI_SCALING"]   = "1"
    # environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    # environ["QT_SCALE_FACTOR"]             = "1"

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
        modeSelectWindow = qw.QMessageBox()
        modeSelectWindow.setWindowTitle("Sekai Text")
        modeSelectWindow.setText("校对与合意时\n强烈建议在有音画对照的条件下进行\n如看游戏内，或者对照录制视频")
        if platform.system() == "Darwin":
            checkButton = modeSelectWindow.addButton(u"合意", 2)
            proofreadButton = modeSelectWindow.addButton(u"校对", 2)
            translateButton = modeSelectWindow.addButton(u"翻译", 2)
        else:
            translateButton = modeSelectWindow.addButton(u"翻译", 2)
            proofreadButton = modeSelectWindow.addButton(u"校对", 2)
            checkButton = modeSelectWindow.addButton(u"合意", 2)

        mainform = mainForm(root)
        translateButton.clicked.connect(mainform.translateMode)
        proofreadButton.clicked.connect(mainform.proofreadMode)
        checkButton.clicked.connect(mainform.checkMode)

        modeSelectWindow.exec_()
        mainform.show()
        atexit.register(onExit)
        app.exec_()
    except BaseException:
        exc_type, exc_value, exc_traceback_obj = sys.exc_info()
        with open(loggingPath, 'a') as f:
            traceback.print_exception(
                exc_type, exc_value, exc_traceback_obj, file=f)
