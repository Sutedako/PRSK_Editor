from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
from PyQt5.QtGui import QIcon
import PyQt5.QtMultimedia as media
from PyQt5.QtCore import QUrl

import json
import logging
import os.path as osp
import requests
import sys

from chr import chrs


class Loader():
    if getattr(sys, 'frozen', False):
        root = sys._MEIPASS
    else:
        root, _ = osp.split(osp.abspath(sys.argv[0]))
        root = osp.join(root, "../")

    def __init__(self, path="", table=None):
        self.talks = []
        self.table = table
        if not path:
            return
        self.talks = []
        self.table.setRowCount(0)

        with open(path, 'r', encoding='UTF-8') as f:
            fulldata = json.load(f)
        '''
        chrpath = osp.join(self.root, "setting/chr.json")
        with open(chrpath, 'r', encoding='UTF-8') as f:
            chrtable = json.load(f)
        '''
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


def update(settingdir):
    headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'}
    bestDBurl = "http://sekai-world.github.io/sekai-master-db-diff/"
    #aiDBurl = "https://api.pjsek.ai/database/master/eventCards?$limit=20&$skip=0&"

    eventsUrl = bestDBurl + "events.json"
    eventsData = json.loads(requests.get(eventsUrl, headers=headers).text)

    eventStoriesUrl = bestDBurl + "eventStories.json"
    eventStoriesData = json.loads(requests.get(eventStoriesUrl, headers=headers).text)

    eventCardsUrl = bestDBurl + "eventCards.json"
    eventCardsData = json.loads(requests.get(eventCardsUrl, headers=headers).text)

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
            'title': e['name'],
            'name': e['assetbundleName'],
            'chapters': [ep['title'] for ep in es["eventStoryEpisodes"]],
            'cards': eventCards
        })

    eventsPath = osp.join(settingdir, "events.json")
    with open(eventsPath, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    logging.info("Events Updated")

    cardsUrl = bestDBurl + "cards.json"
    cardsData = json.loads(requests.get(cardsUrl, headers=headers).text)

    chrCardCount = [0 for i in range(27)]
    preCharacterId = 0
    cards = []
    for idx, c in enumerate(cardsData):
        while idx + chrCardCount[0] + 1 < c['id']:
            chrCardCount[0] += 1
            chrCardCount[preCharacterId] += 1
            cards.append({
                'id': idx + chrCardCount[0],
                'characterId': preCharacterId,
                'cardCount': chrCardCount[preCharacterId]
            })
            if preCharacterId == 14 or preCharacterId == 26:
                chrCardCount[preCharacterId] += 1
        chrCardCount[c["characterId"]] += 1
        cards.append({
            'id': c['id'],
            'characterId': c['characterId'],
            'cardCount': chrCardCount[c["characterId"]],
        })
        if c["cardRarityType"] == "rarity_birthday":
            cards[-1]['birthday'] = True
        preCharacterId = c['characterId']

    cardsPath = osp.join(settingdir, "cards.json")
    with open(cardsPath, 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2)
    logging.info("Cards Updated")

    eventIdx = 0
    festivals = []
    specialCards = []
    birthdatCards = []
    fesIdx = 1
    birthdayIdx = 1

    i = events[0]['cards'][0]
    while i < cards[-1]['id'] + 1:
        while eventIdx < len(events) and i in events[eventIdx]['cards']:
            while i < cards[-1]['id'] + 1 and i in events[eventIdx]['cards']:
                i += 1
            eventIdx += 1
        if i < cards[-1]['id'] + 1 and 'birthday' in cards[i - 1]:
            birthdatCards.append(i)
            if birthdatCards and cards[i - 1]['characterId'] in [7, 16, 14, 23]:
                festivals.append({
                    'id': birthdayIdx,
                    'isBirthday': True,
                    'cards': birthdatCards
                })
                birthdayIdx += 1
                birthdatCards = []
            i += 1
            continue
        while i < cards[-1]['id'] + 1:
            if eventIdx < len(events):
                if i in events[eventIdx]['cards'] or 'birthday' in cards[i - 1]:
                    break
            specialCards.append(i)
            i += 1
        if specialCards:
            festivals.append({
                'id': fesIdx,
                'isBirthday': False,
                'cards': specialCards
            })
            if 335 in specialCards:
                festivals[-1]['id'] = 1
                festivals[-1]['collaboration'] = u'悪ノ大罪'
                festivals[-1]['cards'].pop()
            else:
                fesIdx += 1
            specialCards = []
    if specialCards:
        festivals.append({
            'id': fesIdx,
            'isBirthday': False,
            'cards': specialCards
        })
    if birthdatCards:
        festivals.append({
            'id': birthdayIdx,
            'isBirthday': True,
            'cards': birthdatCards
        })
    fesPath = osp.join(settingdir, "festivals.json")
    with open(fesPath, 'w', encoding='utf-8') as f:
        json.dump(festivals, f, indent=2)
    logging.info("Festivals Updated")

    mainStoryPath = osp.join(settingdir, "mainStory.json")
    mainstory = []
    if not osp.exists(mainStoryPath):
        storyUrl = bestDBurl + "unitStories.json"
        storyData = json.loads(requests.get(storyUrl, headers=headers).text)
        storyData = sorted(storyData, key=lambda x: x['seq'])
        for unitStory in storyData:
            mainstory.append({
                "unit": unitStory["unit"],
                "chapters": [e['title'] for e in unitStory["chapters"][0]["episodes"]]
            })

        with open(mainStoryPath, 'w', encoding='utf-8') as f:
            json.dump(mainstory, f, indent=2, ensure_ascii=False)
        logging.info("MainStory Updated")

    return events, cards, festivals, mainstory
