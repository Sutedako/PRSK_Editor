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
                charIdx = -1
                for idx, c in enumerate(chrtable):
                    if c["name_j"] == speaker:
                        charIdx = idx
                if charIdx >= 0:
                    iconpath = "image/icon/chr/chr_{}.png".format(charIdx + 1)
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

    def update(self, settingdir):
        bestDBurl = "https://sekai-world.github.io/sekai-master-db-diff/"

        eventsUrl = bestDBurl + "events.json"
        eventsData = json.loads(requests.get(eventsUrl).text)

        eventStoriesUrl = bestDBurl + "eventStories.json"
        eventStoriesData = json.loads(requests.get(eventStoriesUrl).text)

        eventCardsUrl = bestDBurl + "eventCards.json"
        eventCardsData = json.loads(requests.get(eventCardsUrl).text)

        eventCardIdx = 0
        events = []
        for e, es in zip(eventsData, eventStoriesData):
            assert e['id'] == es['id']
            eventId = e['id']
            eventCards = []
            while eventCardIdx < len(eventCardsData) and eventCardsData[eventCardIdx]["eventId"] < eventId:
                eventCardIdx += 1
            while eventCardIdx < len(eventCardsData) and eventCardsData[eventCardIdx]["eventId"] == eventId:
                eventCards.append(eventCardsData[eventCardIdx]["cardId"])
                eventCardIdx += 1
            events.append({
                'id': e['id'],
                'title':e['name'],
                'name': e['assetbundleName'],
                'chapters': [ep['title'] for ep in es["eventStoryEpisodes"]],
                'cards': eventCards
                })

        eventsPath = osp.join(settingdir, "events.json")
        with open(eventsPath, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)

        cardsUrl = bestDBurl + "cards.json"
        cardsData = json.loads(requests.get(cardsUrl).text)

        chrCardCount = [0 for i in range(27)]
        cards = []
        for idx, c in enumerate(cardsData):
            while idx + chrCardCount[0] + 1 < c['id']:
                cards.append({
                    'id': idx + 1,
                    'characterId': 0,
                    'cardCount': 0
                    })
                chrCardCount[0] += 1
            chrCardCount[c["characterId"]] += 1
            cards.append({
                'id': c['id'],
                'characterId': c['characterId'],
                'cardCount': chrCardCount[c["characterId"]]
                })

        cardsPath = osp.join(settingdir, "cards.json")
        with open(cardsPath, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2)

        mainStoryPath = osp.join(settingdir, "mainStory.json")
        mainstory = []
        if not osp.exists(mainStoryPath):
            storyUrl = bestDBurl + "unitStories.json"
            storyData = json.loads(requests.get(storyUrl).text)
            storyData = sorted(storyData, key=lambda x: x['seq'])
            for unitStory in storyData:
                mainstory.append({
                    "unit": unitStory["unit"],
                    "chapters": [e['title'] for e in unitStory["chapters"][0]["episodes"]]
                    })

            with open(mainStoryPath, 'w', encoding='utf-8') as f:
                json.dump(mainstory, f, indent=2, ensure_ascii=False)

        return events, cards, mainstory
