from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
from PyQt5.QtGui import QIcon, QColor
import PyQt5.QtMultimedia as media
from PyQt5.QtCore import QUrl
from PyQt5 import QtCore

import json
import os.path as osp
import sys

from Dictionary import characterDict
from collections import Counter

class JsonLoader():
    if getattr(sys, 'frozen', False):
        root = sys._MEIPASS
    else:
        root, _ = osp.split(osp.abspath(sys.argv[0]))
        root = osp.join(root, "../")

    def __init__(self, path="", table=None, fontSize=18, flashbackAnalyzer=None):

        self.talks = []
        self.table = table

        self.major_clue = None
        self.flashback_color = QColor(150, 255, 200, 100)
        self.normal_color = QColor(255, 255, 255)

        self.fb = flashbackAnalyzer

        if not path:
            return

        self.talks = []
        self.table.setRowCount(0)
        self.setFontSize(fontSize)

        with open(path, 'r', encoding='UTF-8') as f:
            fulldata = json.load(f)
        
        self.scenario_id = fulldata['ScenarioId']

        for snippet in fulldata['Snippets']:
            # TalkData
            if snippet['Action'] == 1:
                talkdata = fulldata['TalkData'][snippet['ReferenceIndex']]
                speaker = talkdata['WindowDisplayName'].split("_")[0]
                text = talkdata['Body']
                voices = []
                flashback_clue = []
                is_in_event = True

                for voice in talkdata['Voices']:

                    # TODO download voice file and play
                    voices.append(voice['VoiceId']) 
                
                close = talkdata['WhenFinishCloseWindow']

                self.talks.append({
                    'speaker': speaker,
                    'text': text.rstrip(),
                    'voices': voices,
                })

                row = self.table.rowCount()
                self.table.setRowCount(row + 1)
                charIdx = -1
                for idx, c in enumerate(characterDict):
                    if c["name_j"] == talkdata['WindowDisplayName']:
                        charIdx = idx
                        break
                if charIdx >= 0:
                    iconpath = "image/icon/chr/chr_{}.png".format(charIdx + 1)
                    iconpath = osp.join(self.root, iconpath)
                    icon = QTableWidgetItem(QIcon(iconpath), speaker)
                    self.table.setItem(row, 0, icon)
                else:
                    self.table.setItem(row, 0, QTableWidgetItem(speaker))
                
                textItem = QTableWidgetItem(text)
                self.table.setItem(row, 1, textItem)

                # buttonPlay = QPushButton("")
                # buttonPlay.clicked.connect(self.play)
                # self.table.setCellWidget(row, 2, buttonPlay)
                height = len(text.split('\n'))
                self.table.setRowHeight(row, 20 + (15 + self.fontSize) * height)

                if close:
                    self.talks.append({
                        'speaker': '',
                        'text': '',
                    })

                    row = self.table.rowCount()
                    self.table.setRowCount(row + 1)
                    splitstr = "".join(['-' for i in range(60)])
                    self.table.setItem(row, 1, QTableWidgetItem(splitstr))

            # EffectData
            elif snippet['Action'] == 6:
                effectdata = fulldata['SpecialEffectData'][snippet['ReferenceIndex']]
                # Center Location or Time
                if effectdata['EffectType'] in [8, 18, 23]:
                    text = effectdata['StringVal']

                    speaker = u'场景'
                    if effectdata['EffectType'] == 18:
                        speaker = u'左上场景'
                    elif effectdata['EffectType'] == 23:
                        speaker = u'选项'
                    
                    self.talks.append({
                        'speaker': speaker,
                        'text': text,
                    })

                    row = self.table.rowCount()
                    self.table.setRowCount(row + 1)
                    self.table.setItem(row, 1, QTableWidgetItem(text))
                    self.table.setRowHeight(row, 20 + (15 + self.fontSize))

                    self.talks.append({
                        'speaker': '',
                        'text': '',
                    })

                    row = self.table.rowCount()
                    self.table.setRowCount(row + 1)
                    splitstr = "".join(['-' for i in range(60)])
                    self.table.setItem(row, 1, QTableWidgetItem(splitstr))
                    self.table.setRowHeight(row, 20 + (15 + self.fontSize))

        if self.talks[-1]["speaker"] == '':
            self.talks.pop()
            self.table.removeRow(self.table.rowCount() - 1)
        
        self.checkFlashback(self.talks)
        self.table.setCurrentCell(0, 0)

    def checkFlashback(self, talkdata):

        # Collect all clues
        clues = []
        for talk in talkdata:
            if 'voices' in talk:
                talk_clues = {}
                for voiceId in talk['voices']:
                    clue = self.fb.getClueFromVoiceID(voiceId)
                    talk_clues[clue] = ''
                talk['clues'] = list(talk_clues.keys())
                clues += filter(lambda x : x is not True, talk['clues'])
        
        # Get the most common clue
        # This result is not guranteed reliable but should work at most times
        interpreted_scenario_voice_id = Counter(clues).most_common(1)
        if len(interpreted_scenario_voice_id) >= 1:
            interpreted_scenario_voice_id = interpreted_scenario_voice_id[0][0]
        else:
            interpreted_scenario_voice_id = None
        
        self.major_clue = interpreted_scenario_voice_id
    
    def showFlashback(self):

        if self.major_clue is None:
            # for rowi, talk in enumerate(self.talks):
            #     if 'clues' in talk:
            #         textItem = self.table.item(rowi, 1)
            #         textItem.setToolTip(u"无法判断是否为闪回。\n%s\n\nNo idea about scenarioID.\nvoice ids: %s" % (str(talk['clues']), str(talk['voices'])))
            self.hideFlashback()
            return
        
        # debug 
        # self.major_clue = "no"

        for rowi, talk in enumerate(self.talks):

            is_flashback = False

            if 'clues' in talk:

                for clue in talk['clues']:
                    if clue is not True and clue != self.major_clue:
                        is_flashback = True
                        
                textItem = QTableWidgetItem(talk['text'])
                hints = ""
                if is_flashback:
                    textItem.setBackground(self.flashback_color)
                    for clue in talk['clues']:
                        hints += '\n'.join(self.fb.getClueHints(clue))
                    # if hints != "":
                    #     hints = "\n" + hints
                    # textItem.setToolTip("major clue: %s\nthis sentence: %s" % (self.major_clue, str(talk['clues'])))
                # else:
                    textItem.setToolTip(u"闪回：%s\n\n%s" % (hints, str(talk['voices'])))
                    # textItem.setToolTip(u"闪回：%s\n\n%s\nInferred major clue: %s\nvoice ids: %s" % (hints, str(talk['clues']), self.major_clue, str(talk['voices'])))
                else:
                    textItem.setToolTip(None)
                    # textItem.setToolTip(u"%s\nInferred major clue: %s\nvoice ids: %s" % (str(talk['clues']), self.major_clue, str(talk['voices'])))
                self.table.setItem(rowi, 1, textItem)
    
    def hideFlashback(self):
        for rowi, talk in enumerate(self.talks):
            textItem = self.table.item(rowi, 1)
            # textItem.setBackground(self.normal_color)
            textItem.setData(QtCore.Qt.BackgroundRole, None)
            textItem.setToolTip(None)
            # self.table.setItem(rowi, 1, textItem)

    def setFontSize(self, fontSize):
        self.fontSize = fontSize
        if(not self.table):
            return
        font = self.table.font()
        font.setPixelSize(self.fontSize)
        self.table.setFont(font)
        self.table.horizontalHeader().resizeSection(0, self.fontSize * 7)

        for row in range(self.table.rowCount()):
            text = self.table.item(row, 1).text()
            height = len(text.split('\n'))
            self.table.setRowHeight(row, 20 + (15 + self.fontSize) * height)
