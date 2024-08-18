from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
from PyQt5.QtGui import QIcon, QColor
import PyQt5.QtMultimedia as media
from PyQt5.QtCore import QUrl
from PyQt5 import QtCore

import json
import os.path as osp
import sys

from Dictionary import characterDict
import re
from collections import Counter


class JsonLoader():
    if getattr(sys, 'frozen', False):
        root = sys._MEIPASS
    else:
        root, _ = osp.split(osp.abspath(sys.argv[0]))
        root = osp.join(root, "../")

    def __init__(self, path="", table=None, fontSize=18, listManager=None):

        self.talks = []
        self.table = table

        self.major_clue = None
        self.flashback_color = QColor(150, 255, 200, 100)
        self.normal_color = QColor(255, 255, 255)

        if not path:
            return

        self.talks = []
        self.table.setRowCount(0)
        self.setFontSize(fontSize)
        
        # Flashback
        pattern = r'voice_(.+)_\d+[a-z]?_\d+(?:_?.*)?$'
        self.flashback_re = re.compile(pattern)

        with open(path, 'r', encoding='UTF-8') as f:
            fulldata = json.load(f)
        
        self.scenario_id = fulldata['ScenarioId']
        self.listManager = listManager # Not used, but perhaps keep here for future use?

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

    '''
    Infer clue (some scenarioID) from voice id

      VoiceId examples:                         Matched Clue:                   Interpretation:
    - voice_op_band0_15_03                      op_band0                        Leo/Need opening
    - voice_card_18_3a_27_18                    card_18_3a                      Card: (18)Mafuyu (3)3Star (a)Part1
    - voice_ms_night13_28_18                    ms_night13                      (ms)Main Story - (night)Niigo - (13)Ep.13
    - voice_ev_wl_band_01_05_28_03              ev_wl_band_01_05                (ev)Event Story - (wl)World Link - (band)Leo/Need - (01)1st World Link?? - (05)Ep.5
    - voice_ev_street_18_06_98b_67              ev_street_18_06                 ev - (street)VIVID Bad SQUAD - (18)18th Unit Event (i.e., #135 OVER RAD SQUAD!!) - (06)Ep.6
                                                                                (98b)Variation? of voice used in line 98 (this one is at line 383) - (67)Character ID = Ken Shiraishi
    - voice_card_3rdaniv_20_2b_06_20            card_3rdaniv_20_2b              Card: (3rdaniv)Brand New Style - (20)Mizuki - (2)2Star (b)Part2
    - voice_card_ev_wl_wonder_01_15_4a_20_15    card_ev_wl_wonder_01_15_4a      Card: (ev_wl_wonder_01)WxS 1st WL - (15)Nene - (4)4Star (a)Part1
    - voice_ev_night__06_20_19                  ev_night__06                    (ev_night)Niigo event - *appearently two underscores* - (06)Ep.6 (Event ID MISSING, this is from #53)
    - voice_sc_ev_shuffle_10_01_14_03           sc_ev_shuffle_10_01             (sc)?? - (ev)Event - (shuffle)Mixed Event - (10)#10 Mixed (#30 - The BEST Summer Ever!) - (01)Ep.1
    - areatalk_ev_band_02_004_006
    - 3rd_anniversary_login_band_05_01
    - partvoice_28_021_band                     True (Ignored)                  (partvoice)General short voice for VSingers - (28)Voice No.28? - (021)MIKU - (band)Sub-unit: Leo/Need

    returns: clue
    - None: No idea
    - True: Should be ignored
    - str : clue string, usually indicates scenarioID (for flashbacks, this will refer previous scenarioID)
    '''
    def getClueFromVoiceID(self, voiceId):
        
        #    partvoice - general partial voices (mainly vsinger in card stories etc.)
        if 'partvoice' in voiceId:
            return True

        match = self.flashback_re.search(voiceId)
        if match:
            scenarioId = match.group(1)
            clue = scenarioId
            return clue
        else:
            return None # No idea what is this

    def checkFlashback(self, talkdata):

        # Collect all clues
        clues = []
        for talk in talkdata:
            if 'voices' in talk:
                talk_clues = []
                for voiceId in talk['voices']:
                    clue = self.getClueFromVoiceID(voiceId)
                    talk_clues.append(clue)
                talk['clues'] = talk_clues
                clues += filter(lambda x : x is not True, talk_clues)
        
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
            for rowi, talk in enumerate(self.talks):
                if 'clues' in talk:
                    textItem = self.table.item(rowi, 1)
                    textItem.setToolTip("%s\n\nNo idea about scenarioID.\nvoice ids: %s" % (str(talk['clues']), str(talk['voices'])))
            return

        for rowi, talk in enumerate(self.talks):

            is_flashback = False

            if 'clues' in talk:

                for clue in talk['clues']:
                    if clue is not True and clue != self.major_clue:
                        is_flashback = True
                        
                textItem = QTableWidgetItem(talk['text'])
                if is_flashback:
                    textItem.setBackground(self.flashback_color)
                    # textItem.setToolTip("major clue: %s\nthis sentence: %s" % (self.major_clue, str(talk['clues'])))
                # else:
                textItem.setToolTip("%s\n\nInferred major clue: %s\nvoice ids: %s" % (str(talk['clues']), self.major_clue, str(talk['voices'])))
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
