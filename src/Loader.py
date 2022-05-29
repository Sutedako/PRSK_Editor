from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
from PyQt5.QtGui import QIcon
import PyQt5.QtMultimedia as media
from PyQt5.QtCore import QUrl

import json
import os.path as osp
import sys

from chr import chrs


class Loader():
    if getattr(sys, 'frozen', False):
        root = sys._MEIPASS
    else:
        root, _ = osp.split(osp.abspath(sys.argv[0]))
        root = osp.join(root, "../")
    talks = []

    def __init__(self, path="", table=None):
        self.table = table
        if not path:
            return
        self.talks = []
        self.table.setRowCount(0)

        with open(path, 'r', encoding='UTF-8') as f:
            fulldata = json.load(f)
        chrtable = chrs

        for snippet in fulldata['Snippets']:
            # TalkData
            if snippet['Action'] == 1:
                talkdata = fulldata['TalkData'][snippet['ReferenceIndex']]
                speaker = talkdata['WindowDisplayName']
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
                for idx, c in enumerate(chrtable):
                    if c["name_j"] == speaker:
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
                height = len(text.split('\n')) - 1
                self.table.setRowHeight(row, 60 + 20 * height)

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
                if effectdata['EffectType'] == 8:
                    text = effectdata['StringVal']

                    self.talks.append({
                        'speaker': '场景',
                        'text': text
                    })

                    row = self.table.rowCount()
                    self.table.setRowCount(row + 1)
                    self.table.setItem(row, 1, QTableWidgetItem(text))

                    self.talks.append({
                        'speaker': '',
                        'text': ''
                    })

                    row = self.table.rowCount()
                    self.table.setRowCount(row + 1)
                    splitstr = "".join(['-' for i in range(60)])
                    self.table.setItem(row, 1, QTableWidgetItem(splitstr))

        self.talks.pop()
        self.table.removeRow(self.table.rowCount() - 1)
        self.table.setCurrentCell(0, 0)
