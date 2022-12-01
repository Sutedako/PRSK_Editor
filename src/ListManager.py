from __future__ import unicode_literals

import json
import logging
import os.path as osp
from os import environ
import requests

from Dictionary import unitDict, sekaiDict, characterDict, areaDict, greetDict

from urllib import request

proxy = request.getproxies()
if 'http' in proxy:
    environ['http_proxy'] = proxy['http']
    environ['https_proxy'] = proxy['http']
if 'https' in proxy:
    environ['https_proxy'] = proxy['https']


class ListManager():

    mainstory = []
    events = []
    festivals = []
    cards = []
    specialstory = []
    character2ds = []
    actions = []
    greets = []
    specials = []

    settingDir = ""
    DBUrl = ""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'}

    def __init__(self, settingDir):
        self.settingDir = settingDir

    def load(self):
        self.events = self.loadFile("events.json", "Event")
        self.festivals = self.loadFile("festivals.json", "Festival")
        self.cards = self.loadFile("cards.json", "Card")
        self.mainstory = self.loadFile("mainStory.json", "MainStory")
        self.areatalks = self.loadFile("areatalks.json", "Areatalks")
        self.greets = self.loadFile("greets.json", "Greets")
        self.specials = self.loadFile("specials.json", "Specials")

    def loadFile(self, fileName: str, content: str):
        data = []
        path = osp.join(self.settingDir, fileName)
        if osp.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.info(content + " Loaded")
        return data

    def update(self):
        self.chooseSite()
        self.updateEvents()
        self.updateCards()
        self.updateFestivals()
        self.updateMainstory()
        self.updateAreatalks()
        self.updateGreets()
        self.updateSpecials()

    def chooseSite(self):
        bestDBurl = "http://sekai-world.github.io/sekai-master-db-diff/{}"
        aiDBurl = "https://api.pjsek.ai/database/master/{}?$limit=999&$skip=0&"

        bestUrl = bestDBurl.format("events.json")
        bestData = json.loads(requests.get(bestUrl, headers=self.headers).text)

        aiUrl = aiDBurl.format("events.json")
        aiData = json.loads(requests.get(aiUrl, headers=self.headers).text)

        if len(bestData) > len(aiData):
            self.DBurl = bestDBurl
        else:
            self.DBurl = aiDBurl

    def updateEvents(self):
        url = self.DBurl.format("events.json")
        events = json.loads(requests.get(url, headers=self.headers).text)
        cardIdx = 0

        url = self.DBurl.format("eventStories.json")
        stories = json.loads(requests.get(url, headers=self.headers).text)

        url = self.DBurl.format("eventCards.json")
        cards = json.loads(requests.get(url, headers=self.headers).text)

        self.events = []
        for e, es in zip(events, stories):
            assert e['id'] == es['id']
            eventId = e['id']
            eventCards = []
            while cardIdx < len(cards) and cards[cardIdx]["eventId"] < eventId:
                cardIdx += 1
            while cardIdx < len(cards) and cards[cardIdx]["eventId"] == eventId:
                eventCards.append(cards[cardIdx]["cardId"])
                cardIdx += 1
            self.events.append({
                'id': e['id'],
                'title': e['name'],
                'name': e['assetbundleName'],
                'chapters': [{'title': ep['title'], 'assetName': ep['scenarioId']} for ep in es["eventStoryEpisodes"]],
                'cards': eventCards
            })

        eventsPath = osp.join(self.settingDir, "events.json")
        with open(eventsPath, 'w', encoding='utf-8') as f:
            json.dump(self.events, f, indent=2, ensure_ascii=False)
        logging.info("Events Updated")

    def updateCards(self):
        url = self.DBurl.format("cards.json")
        cards = json.loads(requests.get(url, headers=self.headers).text)

        self.cards = []
        cardCount = 0
        for idx, c in enumerate(cards):
            cardCount += 1
            while cardCount < c['id']:
                self.cards.append({
                    'id': cardCount,
                    'characterId': -1,
                    'cardNo': "000",
                    'birthday': False
                })
                cardCount += 1
            self.cards.append({
                'id': c['id'],
                'characterId': c['characterId'],
                'cardNo': c["assetbundleName"][-3:],
                'birthday': c["cardRarityType"] == "rarity_birthday"
            })

        cardsPath = osp.join(self.settingDir, "cards.json")
        with open(cardsPath, 'w', encoding='utf-8') as f:
            json.dump(self.cards, f, indent=2)
        logging.info("Cards Updated")

    def updateFestivals(self):
        self.festivals = []
        eventIdx = 0
        specialCards = []
        birthdatCards = []
        fesIdx = 1
        birthdayIdx = 1

        i = self.events[0]['cards'][0]
        while i < self.cards[-1]['id'] + 1:
            while eventIdx < len(self.events) and i in self.events[eventIdx]['cards']:
                while i < self.cards[-1]['id'] + 1 and i in self.events[eventIdx]['cards']:
                    i += 1
                eventIdx += 1
            if i < self.cards[-1]['id'] + 1 and self.cards[i - 1]['birthday']:
                birthdatCards.append(i)
                if birthdatCards and self.cards[i - 1]['characterId'] in [7, 16, 14, 23]:
                    self.festivals.append({
                        'id': birthdayIdx,
                        'isBirthday': True,
                        'cards': birthdatCards
                    })
                    birthdayIdx += 1
                    birthdatCards = []
                i += 1
                continue
            while i < self.cards[-1]['id'] + 1:
                if eventIdx < len(self.events):
                    if i in self.events[eventIdx]['cards'] or self.cards[i - 1]['birthday']:
                        break
                specialCards.append(i)
                i += 1
            if specialCards:
                self.festivals.append({
                    'id': fesIdx,
                    'isBirthday': False,
                    'cards': specialCards
                })
                if 335 in specialCards:
                    self.festivals[-1]['id'] = 1
                    self.festivals[-1]['collaboration'] = u'悪ノ大罪'
                    self.festivals[-1]['cards'].pop()
                else:
                    fesIdx += 1
                specialCards = []
        if specialCards:
            self.festivals.append({
                'id': fesIdx,
                'isBirthday': False,
                'cards': specialCards
            })
        if birthdatCards:
            self.festivals.append({
                'id': birthdayIdx,
                'isBirthday': True,
                'cards': birthdatCards
            })
        fesPath = osp.join(self.settingDir, "festivals.json")
        with open(fesPath, 'w', encoding='utf-8') as f:
            json.dump(self.festivals, f, indent=2)
        logging.info("Festivals Updated")

    def updateMainstory(self):
        mainStoryPath = osp.join(self.settingDir, "mainStory.json")
        if osp.exists(mainStoryPath):
            self.mainstory = self.loadFile("mainStory.json", "MainStory")
            return
        self.mainstory = []
        url = self.DBurl.format("unitStories.json")
        story = json.loads(requests.get(url, headers=self.headers).text)
        story = sorted(story, key=lambda x: x['seq'])
        for unitStory in story:
            self.mainstory.append({
                "unit": unitStory["unit"],
                "assetName": unitStory["assetbundleName"],
                "chapters": [{'title': e['title'], 'assetName': e['scenarioId']} for e in unitStory["chapters"][0]["episodes"]]
            })

        with open(mainStoryPath, 'w', encoding='utf-8') as f:
            json.dump(self.mainstory, f, indent=2, ensure_ascii=False)
        logging.info("MainStory Updated")

    def updateCharacter2ds(self):
        url = self.DBurl.format("character2ds.json")
        char2ds = json.loads(requests.get(url, headers=self.headers).text)

        self.char2ds = []
        char2dsCount = 0
        for c in char2ds[:-1]:
            while char2dsCount < c["id"]:
                self.char2ds.append({
                    "id": char2dsCount,
                    "characterType": "none",
                    "characterId": 0,
                    "unit": "none",
                    "assetName": "none"
                })
                char2dsCount += 1
            self.char2ds.append(c)
            char2dsCount += 1

    def updateAreatalks(self):
        url = self.DBurl.format("actionSets.json")
        actions = json.loads(requests.get(url, headers=self.headers).text)

        self.updateCharacter2ds()

        self.areatalks = []
        actionCount = 0
        addEventId = 1
        for action in actions:
            actionCount += 1
            while actionCount < action['id']:
                self.areatalks.append({
                    'id': actionCount,
                    'areaId': -1,
                    'characterIds': [],
                    'scenarioId': "none",
                    'type': 'none',
                    'addEventId': -1,
                    'releaseEventId': -1
                })
                actionCount += 1

            releaseEventId = action['releaseConditionId']
            if releaseEventId > 100000:
                releaseEventId = int((releaseEventId % 10000) / 100) + 1
            if releaseEventId > 1000:
                releaseEventId = -1
            if action['id'] == 618:
                releaseEventId = 1
            if releaseEventId > addEventId:
                addEventId = releaseEventId

            characterIds = []
            for characterId in action['characterIds']:
                characterIds.append(self.char2ds[characterId]["characterId"])
            self.areatalks.append({
                'id': actionCount,
                'areaId': action['areaId'],
                'characterIds': characterIds,
                'scenarioId': action['scenarioId'] if 'scenarioId' in action else 'none',
                'type': action['actionSetType'] if 'actionSetType' in action else 'none',
                'addEventId': addEventId,
                'releaseEventId': releaseEventId
            })

        areatalksPath = osp.join(self.settingDir, "areatalks.json")
        with open(areatalksPath, 'w', encoding='utf-8') as f:
            json.dump(self.areatalks, f, indent=2, ensure_ascii=False)
        logging.info("Areatalks Updated")

    def updateGreets(self):
        units = [key for key in unitDict.keys()]

        def getDetailCharId(greet):
            Id = greet["characterId"]
            unit = greet["unit"]
            if Id == 21 and unit != units[0]:
                return (26 + units.index(unit))
            return Id

        url = self.DBurl.format("systemLive2ds.json")
        greets = json.loads(requests.get(url, headers=self.headers).text)

        def greetAppend(start, end):
            self.greets.append([])
            for g in greets[start - 1: end - 1]:
                self.greets[-1].append({
                    "characterId": getDetailCharId(g),
                    "text": g["serif"]
                })

        def greetAddSingle(index, delay=0):
            self.greets[-1 - delay].append({
                "characterId": getDetailCharId(greets[index - 1]),
                "text": greets[index - 1]["serif"]
            })

        def greetAppendReleaseHoliday(index):
            self.greets.append([])
            for g in greets[index - 1: index + 123: 4]:
                self.greets[-1].append({
                    "characterId": getDetailCharId(g),
                    "text": g["serif"]
                })

        greetAppend(373, 466)  # 2020 秋
        greetAppend(598, 602)  # 2020 遥
        greetAppend(590, 594)
        greetAddSingle(638)  # 2020 穂波
        greetAppendReleaseHoliday(466)  # 2020 ハロウィーン
        greetAppend(632, 638)  # 2020 MEIKO
        greetAppend(606, 610)
        greetAddSingle(639)
        greetAddSingle(640)  # 2020 彰人
        greetAppend(94, 187)  # 2020 冬
        greetAppend(602, 606)
        greetAddSingle(641)
        greetAddSingle(642)  # 2020 雫
        greetAppend(614, 620)  # 2020 RIN
        greetAppend(620, 626)  # 2020 LEN
        greetAppendReleaseHoliday(467)  # 2020 サンタ
        greetAppendReleaseHoliday(468)  # 2020 年末
        greetAppendReleaseHoliday(469)  # 2021 年始
        greetAppend(594, 598)
        greetAddSingle(643)  # 2021 志歩
        greetAppend(610, 614)
        greetAddSingle(644)  # 2021 まふゆ
        greetAppend(626, 632)  # 2021 LUKA

        def greetPlusSingle(greet):
            self.greets[-1].append({
                "characterId": getDetailCharId(greet),
                "text": greet["serif"]
            })

        preCharId = 32
        greetDictIndex = 28
        seasons = ['spring', 'summer', 'autumn', 'winter']
        seasonDelay = False
        delay = 0
        for idx, g in enumerate(greets[644:]):
            index = idx + 645

            if index == 755:
                greetAppend(187, 280)  # 2020 春
            if index == 860:
                greetAppend(280, 373)  # 2020 夏

            if index in [680, 722, 723, 833, 834, 845, 902, 907, 908]:
                greetPlusSingle(g)
                continue

            if (g["characterId"] != 21 and g["characterId"] < preCharId) or index in [712, 829, 928]:
                if not ((867 < index < 898) or index == 1036):  # 2020 七夕, 2021 えむ
                    if not seasonDelay:
                        delay = 0
                    self.greets.append([])
                    if index >= 1036:
                        greetDictIndex = (greetDictIndex + 1) % len(greetDict)
                        greetType = greetDict[greetDictIndex].split("_")[-1]
                        voiceType = g['voice'].split('_')[1]
                        if greetType in seasons or voiceType in seasons:
                            if greetType in seasons and voiceType in seasons:
                                pass
                            elif seasonDelay:
                                print("pop", greetType, g['voice'])
                                self.greets.pop()
                                seasonDelay = False
                            else:
                                print("push", greetType, g['voice'])
                                self.greets.append([])
                                seasonDelay = True
                                delay += 1
                        elif seasonDelay:
                            delay += 1
            if seasonDelay:
                greetAddSingle(index)
            else:
                greetAddSingle(index, delay)
            preCharId = g["characterId"]

        greetsPath = osp.join(self.settingDir, "greets.json")
        with open(greetsPath, 'w', encoding='utf-8') as f:
            json.dump(self.greets, f, indent=2, ensure_ascii=False)
        logging.info("Greets Updated")

    def updateSpecials(self):
        url = self.DBurl.format("specialStories.json")
        stories = json.loads(requests.get(url, headers=self.headers).text)

        self.specials = []
        for story in stories[1:]:
            for ep in story["episodes"]:
                self.specials.append({
                    "title": ep["title"],
                    "dirName": ep["assetbundleName"],
                    "fileName": ep["scenarioId"]
                })

        specialsPath = osp.join(self.settingDir, "specials.json")
        with open(specialsPath, 'w', encoding='utf-8') as f:
            json.dump(self.specials, f, indent=2, ensure_ascii=False)
        logging.info("Specials Updated")

    def getStoryIndexList(self, storyType: str, sort: str):
        storyIndex = []

        if storyType == u"主线剧情":
            for unit in self.mainstory:
                storyIndex.append(unitDict[unit["unit"]])

        elif storyType in [u"活动剧情", u"活动卡面"]:
            eventSum = len(self.events)
            for idx, event in enumerate(self.events[::-1]):
                storyIndex.append(" ".join(
                    [str(eventSum - idx), event['title']]))

        elif storyType == u"特殊卡面":
            for f in self.festivals[::-1]:
                idx = f['id']
                if 'collaboration' in f:
                    storyIndex.append(f['collaboration'])
                elif f['isBirthday']:
                    year = 2021 + int((idx + 2) / 4)
                    month = (idx + 2) % 4 * 3 + 1
                    storyIndex.append("Birthday {} {}-{}".format(
                        year, str(month).zfill(2), str(month + 2).zfill(2)))
                else:
                    year = 2021 + int(idx / 4)
                    month = idx % 4 * 3 + 1
                    storyIndex.append("Festival {} {}".format(
                        year, str(month).zfill(2)))

        elif storyType == u"初始卡面":
            for idx, char in enumerate(characterDict[:26]):
                storyIndex.append(char['name_j'])
                if idx % 4 == 3 and idx < 20:
                    storyIndex.append("-")

        elif storyType == u"初始地图对话":
            if sort == u"按人物":
                for idx, char in enumerate(characterDict[:26]):
                    storyIndex.append(char['name_j'])
                    if idx % 4 == 3 and idx < 20:
                        storyIndex.append("-")
            elif sort == u"按地点":
                for area in areaDict:
                    if area != "":
                        storyIndex.append(area)

        elif storyType == u"追加地图对话":
            if sort == u"按人物":
                for idx, char in enumerate(characterDict[:26]):
                    storyIndex.append(char['name_j'])
                    if idx % 4 == 3 and idx < 20:
                        storyIndex.append("-")

            elif sort == u"按时间":
                self.areaTalkByTime = []

                preAddId = 0
                preReleaseId = 0
                inspecial = False
                for areatalk in self.areatalks:
                    if areatalk["addEventId"] < 0:
                        continue
                    if areatalk["addEventId"] == 1 and preAddId == 0:
                        continue

                    if inspecial:
                        if areatalk["type"] == "limited" or "monthly" in areatalk["scenarioId"]:
                            continue
                        else:
                            inspecial = False

                    if areatalk["type"] == "limited":
                        if "aprilfool" in areatalk["scenarioId"]:
                            year = areatalk["scenarioId"].split("_")[-2][-4:]
                            storyIndex.append(u"【限定】愚人节 {}".format(year))
                        else:
                            storyIndex.append(u"【限定】")
                        self.areaTalkByTime.append({
                            "addEventId": areatalk["addEventId"],
                            "releaseEventId": areatalk["releaseEventId"],
                            "limited": True,
                            "monthly": False
                        })
                        inspecial = True
                    elif "monthly" in areatalk["scenarioId"]:
                        ym = areatalk["scenarioId"].split("_")[-2][-4:]
                        year = ym[:2]
                        month = ym[2:]
                        storyIndex.append(u"【每月】20{} {}".format(year, month))
                        self.areaTalkByTime.append({
                            "addEventId": areatalk["addEventId"],
                            "releaseEventId": areatalk["releaseEventId"],
                            "limited": False,
                            "monthly": True
                        })
                        inspecial = True
                    else:
                        if areatalk["addEventId"] != preAddId:
                            eventId = areatalk["addEventId"]
                            eventTitle = self.events[eventId - 1]["title"]
                            storyIndex.append(u"{} {}".format(eventId, eventTitle))
                            self.areaTalkByTime.append({
                                "addEventId": areatalk["addEventId"],
                                "releaseEventId": areatalk["releaseEventId"],
                                "limited": False,
                                "monthly": False
                            })
                            preAddId = eventId
                        if areatalk["releaseEventId"] != areatalk["addEventId"] and areatalk["releaseEventId"] != preReleaseId:
                            eventId = areatalk["releaseEventId"]
                            if eventId <= 1:
                                storyIndex.append(u"【追加】初始")
                            elif eventId > 1:
                                eventTitle = self.events[eventId - 1]["title"]
                                storyIndex.append(u"【追加】{} {}".format(eventId, eventTitle))
                            self.areaTalkByTime.append({
                                "addEventId": areatalk["addEventId"],
                                "releaseEventId": areatalk["releaseEventId"],
                                "limited": False,
                                "monthly": False
                            })
                            preReleaseId = eventId
                storyIndex = storyIndex[::-1]

            elif sort == u"按地点":
                for area in areaDict:
                    if area != "":
                        storyIndex.append(area)

        elif storyType == u"主界面语音":
            if sort == u"按人物":
                for idx, char in enumerate(characterDict):
                    storyIndex.append(char['name_j'])
                    if (idx % 4 == 3 and idx < 20) or idx == 25:
                        storyIndex.append("-")
            elif sort == u"按时间":
                year = 2020
                idx = 27
                storyIndex.append(greetDict[idx].split("_")[0] + " " + str(year))
                idx += 2
                for g in self.greets[1:]:
                    storyIndex.append(greetDict[idx].split("_")[0] + " " + str(year))
                    idx += 1
                    if idx == len(greetDict):
                        idx = 0
                        year += 1
                storyIndex = storyIndex[::-1]

        elif storyType == u"特殊剧情":
            for ep in self.specials:
                storyIndex.append(ep["title"])
            storyIndex = storyIndex[::-1]

        return storyIndex

    def getStoryChapterList(self, storyType: str, sort: str, storyIndex: int):
        storyChapter = []
        self.chapterScenario = []

        if storyType == u"主线剧情":
            unitId = max(storyIndex, 0)
            for idx, chapter in enumerate(self.mainstory[unitId]["chapters"]):
                if unitId == 0:
                    epNo = idx % 4 + 1
                else:
                    epNo = idx
                storyChapter.append(str(epNo) + " " + chapter)
                if unitId == 0 and epNo == 4:
                    storyChapter.append("-")
            if unitId == 0:
                storyChapter.pop()

        elif storyType == u"活动剧情":
            eventId = len(self.events) - max(storyIndex, 0)
            for idx, chapter in enumerate(self.events[eventId - 1]['chapters']):
                storyChapter.append(str(idx + 1) + " " + chapter['title'])

        elif storyType in [u"活动卡面", u"特殊卡面"]:

            if storyType == u"活动卡面":
                content = self.events
            elif storyType == u"特殊卡面":
                content = self.festivals

            contentId = len(content) - max(storyIndex, 0)
            for cardId in content[contentId - 1]['cards']:
                char = characterDict[self.cards[cardId - 1]['characterId'] - 1]
                storyChapter.append(char['name_j'] + u" 前篇")
                storyChapter.append(char['name_j'] + u" 后篇")
                storyChapter.append("-")
            storyChapter.pop()

        elif storyType == u"初始卡面":
            storyChapter.append(u"一星 前篇")
            storyChapter.append(u"一星 后篇")
            storyChapter.append("-")

            # 二星MIKU
            if storyIndex != 25:
                storyChapter.append(u"二星 前篇")
                storyChapter.append(u"二星 后篇")
                storyChapter.append("-")
            else:
                for unit in sekaiDict:
                    storyChapter.append(u"{}二星 前篇".format(unit))
                    storyChapter.append(u"{}二星 前篇".format(unit))
                    storyChapter.append("-")

            storyChapter.append(u"三星 前篇")
            storyChapter.append(u"三星 后篇")
            storyChapter.append("-")

            # 四星一歌、MIKU、RIN、LEN
            if storyIndex in [0, 25, 26, 27]:
                storyChapter.append(u"四星 前篇")
                storyChapter.append(u"四星 后篇")

        elif storyType == u"初始地图对话":
            if sort == u"按人物":
                charId = int((storyIndex + 1) * 4 / 5) + 1
                if storyIndex == 30:
                    charId = 26

                areatalkCount = 0
                for areatalk in self.areatalks:
                    if areatalk["addEventId"] > 1:
                        break
                    if areatalk["type"] == "normal" and charId in areatalk["characterIds"] and areatalk["scenarioId"] != "none":
                        areatalkCount += 1
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"]))
                        if areatalkCount % 6 == 0:
                            storyChapter.append("-")
                            self.chapterScenario.append("")

            elif sort == u"按地点":
                areaId = storyIndex + 1 if storyIndex <= 5 else storyIndex + 2

                areatalkCount = 0
                for areatalk in self.areatalks:
                    if areatalk["addEventId"] > 1:
                        break
                    if areatalk["type"] == "normal" and areaId == areatalk["areaId"] and areatalk["scenarioId"] != "none":
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"]))
                        areatalkCount += 1
                        if areatalkCount % 10 == 0:
                            storyChapter.append("-")
                            self.chapterScenario.append("")

        elif storyType == u"追加地图对话":
            if sort == u"按人物":
                charId = int((storyIndex + 1) * 4 / 5) + 1
                if storyIndex == 30:
                    charId = 26

                isRelease = True
                areatalkCount = 0
                for areatalk in self.areatalks:
                    if areatalk["addEventId"] > 1:
                        isRelease = False
                    if areatalk["type"] == "normal" and charId in areatalk["characterIds"] and areatalk["scenarioId"] != "none":
                        areatalkCount += 1
                        if areatalk["addEventId"] == 1 and isRelease:
                            continue
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"]))
                        if areatalkCount % 6 == 0:
                            storyChapter.append("-")
                            self.chapterScenario.append("")

            elif sort == u"按时间":
                storyIndex = len(self.areaTalkByTime) - 1 - storyIndex
                areaTalksInfo = self.areaTalkByTime[storyIndex]
                if areaTalksInfo["limited"]:
                    foundStart = False
                    for areatalk in self.areatalks:
                        sameId = areatalk["addEventId"] == areaTalksInfo["addEventId"] and areatalk["releaseEventId"] == areaTalksInfo["releaseEventId"]
                        if not foundStart and not (areatalk["type"] == "limited" and sameId):
                            continue
                        foundStart = True
                        if areatalk["type"] != "limited":
                            break
                        if areatalk["scenarioId"] == "none":
                            continue
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"]))
                elif areaTalksInfo["monthly"]:
                    foundStart = False
                    for areatalk in self.areatalks:
                        sameId = areatalk["addEventId"] == areaTalksInfo["addEventId"] and areatalk["releaseEventId"] == areaTalksInfo["releaseEventId"]
                        if not foundStart and not ("monthly" in areatalk["scenarioId"] and sameId):
                            continue
                        foundStart = True
                        if "monthly" not in areatalk["scenarioId"]:
                            break
                        if areatalk["scenarioId"] == "none":
                            continue
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"]))
                else:
                    for areatalk in self.areatalks:
                        sameId = areatalk["addEventId"] == areaTalksInfo["addEventId"] and areatalk["releaseEventId"] == areaTalksInfo["releaseEventId"]
                        if not sameId or "monthly" in areatalk["scenarioId"] or areatalk["type"] == "limited":
                            continue
                        if areatalk["addEventId"] > areaTalksInfo["addEventId"]:
                            break
                        if areatalk["scenarioId"] == "none":
                            continue
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"]))

            elif sort == u"按地点":
                areaId = storyIndex + 1 if storyIndex <= 5 else storyIndex + 2

                isRelease = True
                areatalkCount = 0
                for areatalk in self.areatalks:
                    if areatalk["addEventId"] == 1 and isRelease:
                        continue
                    else:
                        isRelease = False
                    if areatalk["type"] == "normal" and areaId == areatalk["areaId"] and areatalk["scenarioId"] != "none":
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"]))
                        areatalkCount += 1
                        if areatalkCount % 10 == 0:
                            storyChapter.append("-")
                            self.chapterScenario.append("")

        return storyChapter

    def getJsonPath(self, storyType, sort, storyIdx, chapterIdx, source):
        jsonurl = ""
        bestBaseUrl = "https://minio.dnaroma.eu/sekai-assets/"
        aiBaseUrl = "https://assets.pjsek.ai/file/pjsekai-assets/"

        if storyType == u"主线剧情":
            unitIdx = storyIdx
            unit = self.mainstory[unitIdx]["assetName"]
            chapters = self.mainstory[unitIdx]["chapters"]
            if unitIdx == 0:
                chapterIdx = int((chapterIdx + 1) * 4 / 5)
            chapter = chapters[chapterIdx]['assetName']

            if source == "sekai.best":
                jsonurl = bestBaseUrl + "scenario/unitstory/" \
                    "{}-chapter_rip/{}.asset".format(unit, chapter)
            elif source == "pjsek.ai":
                jsonurl = aiBaseUrl + "startapp/scenario/unitstory/" \
                    "{}-chapter/{}.json".format(unit, chapter)

            preTitle = chapter
            jsonname = "mainStory_{}.json".format(chapter)

        elif storyType == u"活动剧情":
            eventId = len(self.events) - storyIdx
            event = self.events[eventId - 1]['name']
            chapters = self.events[eventId - 1]["chapters"]
            chapter = chapters[chapterIdx]['assetName']

            if source == "sekai.best":
                jsonurl = bestBaseUrl + "event_story/" \
                    "{}/scenario_rip/{}.asset".format(event, chapter)
            elif source == "pjsek.ai":
                jsonurl = aiBaseUrl + "ondemand/event_story/" \
                    "{}/scenario/{}.json".format(event, chapter)

            preTitle = chapter
            jsonname = chapter + ".json"

        elif storyType == u"活动卡面":
            eventId = len(self.events) - storyIdx
            cardId = self.events[eventId - 1]["cards"][int(chapterIdx / 3)]
            charId = self.cards[cardId - 1]["characterId"]

            cardNo = self.cards[cardId - 1]["cardNo"]
            chapter = str(chapterIdx % 3 + 1).zfill(2)
            eventId = str(eventId).zfill(2)
            charname = characterDict[charId - 1]['name']
            charId = str(charId).zfill(3)

            if source == "sekai.best":
                jsonurl = bestBaseUrl + "character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.asset".format(
                        charId, cardNo, charId, cardNo, charname, chapter)
            elif source == "pjsek.ai":
                jsonurl = aiBaseUrl + "startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.json".format(
                        charId, cardNo, charId, cardNo, charname, chapter)

            preTitle = "event{}-{}-{}".format(eventId, charname, chapter)
            jsonname = preTitle.replace("-", "_") + ".json"

        elif storyType == u"特殊卡面":
            fesId = len(self.festivals) - storyIdx
            cardId = self.festivals[fesId - 1]["cards"][int(chapterIdx / 3)]
            charId = self.cards[cardId - 1]["characterId"]

            cardNo = self.cards[cardId - 1]["cardNo"]
            chapter = str(chapterIdx % 3 + 1).zfill(2)
            charname = characterDict[charId - 1]['name']
            charId = str(charId).zfill(3)

            if source == "sekai.best":
                jsonurl = bestBaseUrl + "character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.asset".format(
                        charId, cardNo, charId, cardNo, charname, chapter)
            elif source == "pjsek.ai":
                jsonurl = aiBaseUrl + "startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.json".format(
                        charId, cardNo, charId, cardNo, charname, chapter)

            idx = self.festivals[fesId - 1]['id']
            if 'collaboration' in self.festivals[fesId - 1]:
                preTitle = "collabo{}_{}_{}".format(
                    idx, charname, chapter)
            elif self.festivals[fesId - 1]['isBirthday']:
                year = 2021 + int((idx + 2) / 4)
                preTitle = "birth{}_{}_{}".format(
                    year, charname, chapter)
            else:
                year = 2021 + int(idx / 4)
                month = str(idx % 4 * 3 + 1).zfill(2)
                preTitle = "fes{}{}_{}_{}".format(
                    year, month, charname, chapter)
            jsonname = preTitle.replace("-", "_") + ".json"

        elif storyType == u"初始卡面":
            currentIdx = storyIdx
            if currentIdx > 25:
                charId = currentIdx - 4
            else:
                charId = int(currentIdx / 5) * 4 + (currentIdx + 1) % 5
            charname = characterDict[charId - 1]['name']

            rarity = int(chapterIdx / 3) + 1
            if charname == "miku":
                realRarity = max(2, rarity - 4) if rarity > 2 else rarity
                if realRarity == 2:
                    unit = sekaiDict[rarity - 2]
                realRarity = str(realRarity).zfill(2)
            rarity = str(rarity).zfill(3)

            chapter = str(chapterIdx % 3 + 1).zfill(2)
            charId = str(charId).zfill(3)

            if source == "sekai.best":
                jsonurl = bestBaseUrl + "character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.asset".format(
                        charId, rarity, charId, rarity, charname, chapter)
            elif source == "pjsek.ai":
                jsonurl = aiBaseUrl + "startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.json".format(
                        charId, rarity, charId, rarity, charname, chapter)
            if charname == "miku" and realRarity == "02":
                preTitle = "release-miku-{}-02-{}".format(unit, chapter)
            else:
                preTitle = "release-{}-{}-{}".format(charname, rarity, chapter)
            jsonname = preTitle.replace("-", "_") + ".json"

        elif storyType in [u"初始地图对话", u"追加地图对话"]:
            group = int(self.chapterScenario[chapterIdx][0] / 100)
            jsonname = self.chapterScenario[chapterIdx][1]
            # titlename = jsonname.replace("areatalk", "as")

            if source == "sekai.best":
                jsonurl = bestBaseUrl + "scenario/actionset/" \
                    "group{}_rip/{}.asset".format(group, jsonname)
                # titleurl = bestBaseUrl + "actionset/" \
                #    "group{}_rip/{}.asset".format(group, titlename)
            elif source == "pjsek.ai":
                jsonurl = aiBaseUrl + "startapp/scenario/actionset/" \
                    "group{}/{}.json".format(group, jsonname)
                # titleurl = aiBaseUrl + "startapp/actionset/" \
                #     "group{}/{}.json".format(group, titlename)

            preTitle = jsonname
            jsonname = jsonname + ".json"

        elif storyType == u"主界面语音":
            if sort == u"按人物":
                currentIdx = storyIdx
                if currentIdx > 31:
                    charId = currentIdx - 5
                elif currentIdx > 25:
                    charId = currentIdx - 4
                else:
                    charId = int(currentIdx / 5) * 4 + (currentIdx + 1) % 5
                charname = characterDict[charId - 1]['name']

                preTitle = "greets_" + charname
                jsonname = preTitle + ".json"

            elif sort == u"按时间":
                storyIdx = len(self.greets) - 1 - storyIdx
                if storyIdx == 0:
                    idx = 27
                else:
                    idx = 28 + storyIdx
                year = 2020 + int(idx / len(greetDict))
                title = greetDict[idx % len(greetDict)]

                if "_" in title:
                    preTitle = title.split("_")[-1]
                else:
                    charName = title.split("　")[0]
                    for char in characterDict:
                        if charName == char["name_j"]:
                            preTitle = char["name"]
                            break
                    if title.split("　")[1] == "誕生日":
                        preTitle = preTitle + "_birthday"
                    elif title.split("　")[1] == "記念日":
                        preTitle = preTitle + "_anniversary"

                preTitle = preTitle + "_" + str(year)
                jsonname = preTitle + ".json"

        elif storyType == u"特殊剧情":
            storyIdx = len(self.specials) - 1 - storyIdx
            story = self.specials[storyIdx]

            if source == "sekai.best":
                jsonurl = bestBaseUrl + "scenario/special/" \
                    "{}_rip/{}.asset".format(story["dirName"], story["fileName"])
            elif source == "pjsek.ai":
                jsonurl = aiBaseUrl + "startapp/scenario/special/" \
                    "{}/{}.json".format(story["dirName"], story["fileName"])

            preTitle = story["title"]
            jsonname = story["fileName"] + ".json"

        return preTitle, jsonname, jsonurl

    def makeJson(self, sort, storyIdx, savepath):
        data = {'Snippets': [],
                'TalkData': []}

        def addGreet(speaker, text):
            data['Snippets'].append({
                'Action': 1,
                'ReferenceIndex': len(data['TalkData'])
            })
            data['TalkData'].append({
                'WindowDisplayName': speaker,
                'Body': text,
                'Voices': [],
                'WhenFinishCloseWindow': 0
            })

        if sort == u"按人物":
            currentIdx = storyIdx
            if currentIdx > 31:
                charId = currentIdx - 5
            elif currentIdx > 25:
                charId = currentIdx - 4
            else:
                charId = int(currentIdx / 5) * 4 + (currentIdx + 1) % 5

            for index, greets in enumerate(self.greets):
                idx = 27 if index == 0 else 28 + index
                title = greetDict[idx % len(greetDict)]
                if "_" in title:
                    title = title.split("_")[0]
                year = 2020 + int(idx / len(greetDict))
                title = title + " " + str(year)

                for greet in greets:
                    if greet["characterId"] == charId:
                        addGreet(title, greet["text"])

        elif sort == u"按时间":
            storyIdx = len(self.greets) - 1 - storyIdx
            for greet in self.greets[storyIdx]:
                addGreet(characterDict[greet["characterId"] - 1]["name_j"], greet["text"])

        with open(savepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("")

