from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
from PyQt5.QtGui import QIcon
import PyQt5.QtMultimedia as media
from PyQt5.QtCore import QUrl

import json
import os.path as osp
import sys

from Dictionary import characterDict


class JsonLoader():
    if getattr(sys, 'frozen', False):
        root = sys._MEIPASS
    else:
        root, _ = osp.split(osp.abspath(sys.argv[0]))
        root = osp.join(root, "../")

    def __init__(self, path="", table=None, fontSize=18):
        self.talks = []
        self.table = table
        if not path:
            return
        self.talks = []
        self.table.setRowCount(0)
        self.setFontSize(fontSize)

        with open(path, 'r', encoding='UTF-8') as f:
            fulldata = json.load(f)

        for snippet in fulldata['Snippets']:
            # TalkData
            if snippet['Action'] == 1:
                talkdata = fulldata['TalkData'][snippet['ReferenceIndex']]
                speaker = talkdata['WindowDisplayName'].split("_")[0]
                text = talkdata['Body']
                voices = []
                for voice in talkdata['Voices']:
                    # TODO download voice file and play
                    voices.append(voice['VoiceId'])
                close = talkdata['WhenFinishCloseWindow']

                self.talks.append({
                    'speaker': speaker,
                    'text': text.rstrip()
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
                self.table.setItem(row, 1, QTableWidgetItem(text))
                # buttonPlay = QPushButton("")
                # buttonPlay.clicked.connect(self.play)
                # self.table.setCellWidget(row, 2, buttonPlay)
                height = len(text.split('\n'))
                self.table.setRowHeight(row, 20 + (15 + self.fontSize) * height)

                if close:
                    self.talks.append({
                        'speaker': '',
                        'text': ''
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
                        'text': text
                    })

                    row = self.table.rowCount()
                    self.table.setRowCount(row + 1)
                    self.table.setItem(row, 1, QTableWidgetItem(text))
                    self.table.setRowHeight(row, 20 + (15 + self.fontSize))

                    self.talks.append({
                        'speaker': '',
                        'text': ''
                    })

                    row = self.table.rowCount()
                    self.table.setRowCount(row + 1)
                    splitstr = "".join(['-' for i in range(60)])
                    self.table.setItem(row, 1, QTableWidgetItem(splitstr))
                    self.table.setRowHeight(row, 20 + (15 + self.fontSize))

        if self.talks[-1]["speaker"] == '':
            self.talks.pop()
            self.table.removeRow(self.table.rowCount() - 1)
        self.table.setCurrentCell(0, 0)

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
