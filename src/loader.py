from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtGui import QIcon

import json
import requests
import os.path as osp

class Loader():

    root = osp.join(osp.dirname(__file__), "../")
    talks = []

    def __init__(self, path="", table=None):

        if not path:
            return
        self.talks = []
        table.setRowCount(0)

        with open(path, 'r', encoding='UTF-8') as f:
            fulldata = json.load(f)

        chrpath = osp.join(self.root, "setting/chr.json")
        with open(chrpath, 'r', encoding='UTF-8') as f:
            chrtable = json.load(f)

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

                row = table.rowCount()
                table.setRowCount(row + 1)
                if speaker in chrtable:
                    iconpath = "image/icon/chr/chr_{}.png".format(
                        chrtable.index(speaker) + 1)
                    iconpath = osp.join(self.root, iconpath)
                    icon = QTableWidgetItem(QIcon(iconpath), speaker)
                    table.setItem(row, 0, icon)
                else:
                    table.setItem(row, 0, QTableWidgetItem(speaker))
                table.setItem(row, 1, QTableWidgetItem(text))
                height = len(text.split('\n')) - 1
                table.setRowHeight(row, 60 + 20 * height)

                if close:
                    self.talks.append({
                        'speaker': '',
                        'text': ''
                    })

                    row = table.rowCount()
                    table.setRowCount(row + 1)
                    splitstr = "".join(['-' for i in range(60)])
                    table.setItem(row, 1, QTableWidgetItem(splitstr))

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

                    row = table.rowCount()
                    table.setRowCount(row + 1)
                    table.setItem(row, 1, QTableWidgetItem(text))

                    self.talks.append({
                        'speaker': '',
                        'text': ''
                    })

                    row = table.rowCount()
                    table.setRowCount(row + 1)
                    splitstr = "".join(['-' for i in range(60)])
                    table.setItem(row, 1, QTableWidgetItem(splitstr))

        self.talks.pop()
        table.removeRow(table.rowCount() - 1)
        table.setCurrentCell(0, 0)

    def update(self):
        eventurl = "https://api.pjsek.ai/assets?" \
            "parent=ondemand/event_story&$limit=1000"
        eventsdata = json.loads(requests.get(eventurl).text)["data"]
        events = [{'name':e['path'].split('/')[-1], 'version':e['assetVersion']} for e in sorted(
            eventsdata, key=lambda k: k['datetime'])]
        # TODO add title

        # TODO
        # cardurl = ""

        return events
