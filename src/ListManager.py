from __future__ import unicode_literals

import json
import logging
import os.path as osp
from os import environ
import requests
import time
import math

from Dictionary import unitDict, sekaiDict, characterDict, areaDict
from Dictionary import greetDict_season, greetDict_celebrate, greetDict_holiday

from urllib import request
import re

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
    setting = {}

    settingDir = ""
    DBurl = ""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'}

    urls = {
        'bestDBurl' : "https://raw.githubusercontent.com/Sekai-World/sekai-master-db-diff/main/{}.json",
        'aiDBurl' : "https://api.pjsek.ai/database/master/{}?$limit=9999&$skip=0&",
        'harukiDBurl' : "https://bot-assets.haruki.seiunx.com/master-jp/{}.json?t=0",

        'bestBaseUrl' : "https://minio.dnaroma.eu/sekai-jp-assets/",
        'uniBaseUrl' : "https://assets.unipjsk.com/",
        'harukiJPBaseUrl' : "https://sekai-assets-bdf29c81.seiunx.net/jp-assets/",
        'harukiCNBaseUrl' : "https://bot-assets.haruki.seiunx.com/assets/",
    }

    def __init__(self, settingDir):
        self.settingDir = settingDir
        settingPath = osp.join(self.settingDir, "setting.json")
        if osp.exists(settingPath):
            with open(settingPath, 'r', encoding='utf-8') as f:
                self.setting = json.load(f)

    def load(self):
        self.events = self.loadFile("events.json", "Event")
        self.festivals = self.loadFile("festivals.json", "Festival")
        self.cards = self.loadFile("cards.json", "Card")
        self.mainstory = self.loadFile("mainStory.json", "MainStory")
        self.areatalks = self.loadFile("areatalks.json", "Areatalks")
        self.greets = self.loadFile("greets.json", "Greets")
        self.specials = self.loadFile("specials.json", "Specials")

        self.urls = self.loadFile("../urls.json", "DB URLs", self.urls)
        self.voiceClues = self.buildVoiceIDClues()

    def loadFile(self, fileName: str, content: str, default: object = None):
        if default is None:
            default = []
        data = default
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

        self.inferVoiceEventID()

    def chooseSite(self):
        bestDBurl = self.urls['bestDBurl']
        aiDBurl = self.urls['aiDBurl']
        harukiDBurl = self.urls['harukiDBurl'] + str(int(time.time()))
        
        sites = {
            "Haruki": harukiDBurl,
            "best": bestDBurl,
            "ai": aiDBurl
        }

        minDownloadTime = 100000
        maxEventsLength = 0
        result = ""

        target = self.setting["downloadTarget"]

        if target is not None and target != "Auto":
            if target not in sites:
                logging.warning(f"Invalid target {target}, force using Haruki")
                target = "Haruki"

            try:
                logging.info("Force using %s" % (target))
                data = requests.get(sites[target].format("events"), headers=self.headers, timeout=minDownloadTime, verify=not self.setting["disabelSSLcheck"]).text
                self.DBurl = sites[target]
                result = target

            except BaseException as e:
                logging.warning("Failed to connect to %s cause %s" % (target, e))
                data = []
                downloadTime = math.inf
        else:
            for name, site in sites.items():
                try:
                    logging.info("[ListManager] Trying to connect to %s" % (name))
                    startTime = time.time()
                    data = requests.get(site.format("events"), headers=self.headers, timeout=minDownloadTime, verify=not self.setting["disabelSSLcheck"]).text
                    endTime = time.time()
                    downloadTime = endTime - startTime
                    data = json.loads(data)
                    if name == "ai":
                        data = data['data']
                except BaseException as e:
                    logging.warning("[ListManager] Failed to connect to %s cause %s" % (name, e))
                    data = []
                    downloadTime = math.inf             

                if len(data) >= maxEventsLength and downloadTime < minDownloadTime:
                    maxEventsLength = len(data)
                    minDownloadTime = downloadTime
                    self.DBurl = site
                    result = name

        logging.info("[ListManager] self.DBurl = %s" % (self.DBurl))
        return result

    def updateEvents(self):
        url = self.DBurl.format("events")
        events = json.loads(requests.get(url, headers=self.headers, proxies=request.getproxies(), verify=not self.setting["disabelSSLcheck"]).text)
        if("data" in events):
            events = events["data"]
        cardIdx = 0

        url = self.DBurl.format("eventStories")
        stories = json.loads(requests.get(url, headers=self.headers, proxies=request.getproxies(), verify=not self.setting["disabelSSLcheck"]).text)
        if("data" in stories):
            stories = stories["data"]

        url = self.DBurl.format("eventCards")
        cards = json.loads(requests.get(url, headers=self.headers, proxies=request.getproxies(), verify=not self.setting["disabelSSLcheck"]).text)
        if("data" in cards):
            cards = cards["data"]

        self.all_events = {}
        self.events = []

        for e in events:
            eventId = e['id']
            eventCards = []
            while cardIdx < len(cards) and cards[cardIdx]["eventId"] < eventId:
                cardIdx += 1
            while cardIdx < len(cards) and cards[cardIdx]["eventId"] == eventId:
                eventCards.append(cards[cardIdx]["cardId"])
                cardIdx += 1
            self.all_events[e['id']] = {
                'kdyicr_id': e['id'],
                'id': -1,
                'title': e['name'],
                'name': e['assetbundleName'],
                'chapters': [],
                'cards': eventCards
            }


        for es in stories:
            assert es['id'] <= len(self.all_events)
            e = self.all_events[es['id']]
            self.all_events[es['id']]['chapters'] =\
                [{'title': ep['title'], 'assetName': ep['scenarioId']} for ep in es["eventStoryEpisodes"]]
        
        # Make events entry
        sorted_all_events = sorted(self.all_events.values(), key = lambda e: e['kdyicr_id'])
        for e in sorted_all_events:
            if len(e['chapters']) == 0:
                continue
            e['id'] = len(self.events) + 1
            self.all_events[e['kdyicr_id']]['id'] = e['id']
            self.events.append(e)

        eventsPath = osp.join(self.settingDir, "events.json")
        with open(eventsPath, 'w', encoding='utf-8') as f:
            json.dump(self.events, f, indent=2, ensure_ascii=False)
        logging.info("Events Updated")

    def updateCards(self):
        url = self.DBurl.format("cards")
        cards = json.loads(requests.get(url, headers=self.headers, proxies=request.getproxies(), verify=not self.setting["disabelSSLcheck"]).text)
        if("data" in cards):
            cards = cards["data"]

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
            if 724 <= cardCount <= 759:
                self.cards[-1]["levelup"] = True

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
                elif 724 in specialCards:
                    self.festivals[-1]['id'] = 1
                    self.festivals[-1]['levelup'] = True
                    self.festivals[-1]['cards'].pop()
                    self.festivals[-1]['cards'].pop()

                    self.festivals.append({
                        'id': fesIdx,
                        'isBirthday': False,
                        'cards': specialCards[-2:]
                    })
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
        url = self.DBurl.format("unitStories")
        story = json.loads(requests.get(url, headers=self.headers, proxies=request.getproxies(), verify=not self.setting["disabelSSLcheck"]).text)
        if("data" in story):
            story = story["data"]
        story = sorted(story, key=lambda x: x['seq'])
        for unitStory in story:
            for chapter in unitStory["chapters"]:
                self.mainstory.append({
                    "unit": chapter["unit"],
                    "assetName": chapter["assetbundleName"],
                    "chapters": [{'title': e['title'], 'assetName': e['scenarioId']} for e in chapter["episodes"]]
                })

        with open(mainStoryPath, 'w', encoding='utf-8') as f:
            json.dump(self.mainstory, f, indent=2, ensure_ascii=False)
        logging.info("MainStory Updated")

    def updateCharacter2ds(self):
        url = self.DBurl.format("character2ds")
        char2ds = json.loads(requests.get(url, headers=self.headers, proxies=request.getproxies(), verify=not self.setting["disabelSSLcheck"]).text)
        if("data" in char2ds):
            char2ds = char2ds["data"]

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
        url = self.DBurl.format("actionSets")
        actions = json.loads(requests.get(url, headers=self.headers, proxies=request.getproxies(), verify=not self.setting["disabelSSLcheck"]).text)
        if("data" in actions):
            actions = actions["data"]

        self.updateCharacter2ds()

        self.areatalks = []
        actionCount = 0
        areatalkCount = 0
        specialAreatalkCount = 0
        addEventId = 1
        for action in actions:
            actionCount += 1
            while actionCount < action['id']:
                self.areatalks.append({
                    'id': actionCount,
                    'talkid': -1,
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
                releaseEventId = int((releaseEventId % 100000) / 100) + 1
            if releaseEventId > 1000:
                releaseEventId = -1
            if releaseEventId in self.all_events:
                releaseEventId = self.all_events[releaseEventId]['id'] # Map kdyicr_id to PJSId
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
            if self.areatalks[-1]['scenarioId'] != 'none':
                if self.areatalks[-1]['type'] == "normal":
                    areatalkCount += 1
                    self.areatalks[-1]['talkid'] = str(areatalkCount).zfill(4)
                elif self.areatalks[-1]['type'] != "none":
                    specialAreatalkCount += 1
                    self.areatalks[-1]['talkid'] = "S" + str(specialAreatalkCount).zfill(4)

        areatalksPath = osp.join(self.settingDir, "areatalks.json")
        with open(areatalksPath, 'w', encoding='utf-8') as f:
            json.dump(self.areatalks, f, indent=2, ensure_ascii=False)
        logging.info("Areatalks Updated")

    def updateGreets(self):
        units = [key for key in unitDict.keys()]

        seasonIdx = 1
        celebrateIdx = 18
        holidayIdx = 6
        year_season = 2020
        year_celebrate = 2020
        year_holiday = 2020

        def getDetailCharId(greet):
            Id = greet["characterId"]
            unit = greet["unit"]
            if Id == 21 and unit != units[0]:
                return (26 + units.index(unit))
            return Id

        def getGreetCharContent(idx):
            character = characterDict[greetDict_celebrate[idx]]
            if greetDict_celebrate[idx] < 20:
                content = {
                    "ch": character["name_j"] + "-誕生日",
                    "en": character["name"] + "_birthday"
                }
            else:
                content = {
                    "ch": character["name_j"] + "-記念日",
                    "en": character["name"] + "_anniversary"
                }
            return content

        url = self.DBurl.format("systemLive2ds")
        greets = json.loads(requests.get(url, headers=self.headers, proxies=request.getproxies(), verify=not self.setting["disabelSSLcheck"]).text)
        if("data" in greets):
            greets = greets["data"]

        def greetAppend(greetType, start, end):
            if greetType == "season":
                nonlocal seasonIdx, year_season
                if seasonIdx == 0:
                    year_season += 1
                seasonIdx = (seasonIdx + 1) % len(greetDict_season)
                self.greets.append({"theme": greetDict_season[seasonIdx], "year": year_season, "greets": []})
                for g in greets[start - 1: end - 1]:
                    self.greets[-1]["greets"].append({
                        "characterId": getDetailCharId(g),
                        "text": g["serif"]
                    })
                return
            elif greetType == "celebrate":
                nonlocal celebrateIdx, year_celebrate
                celebrateIdx = (celebrateIdx + 1) % len(greetDict_celebrate)
                if celebrateIdx == 0:
                    year_celebrate += 1
                self.greets.append({"theme": getGreetCharContent(celebrateIdx), "year": year_celebrate, "greets": []})
                for g in greets[start - 1: end - 1]:
                    self.greets[-1]["greets"].append({
                        "characterId": getDetailCharId(g),
                        "text": g["serif"]
                    })

        def greetAddSingle(index):
            self.greets[-1]["greets"].append({
                "characterId": getDetailCharId(greets[index - 1]),
                "text": greets[index - 1]["serif"]
            })

        def greetAppendReleaseHoliday(index):
            nonlocal holidayIdx, year_holiday
            holidayIdx = (holidayIdx + 1) % len(greetDict_holiday)
            if holidayIdx == 0:
                year_holiday += 1
            self.greets.append({"theme": greetDict_holiday[holidayIdx], "year": year_holiday, "greets": []})
            for g in greets[index - 1: index + 123: 4]:
                self.greets[-1]["greets"].append({
                    "characterId": getDetailCharId(g),
                    "text": g["serif"]
                })

        greetAppend("season", 373, 466)  # 2020 秋
        greetAppend("celebrate", 598, 602)  # 2020 遥
        greetAppend("celebrate", 590, 594)
        greetAddSingle(638)  # 2020 穂波
        greetAppendReleaseHoliday(466)  # 2020 ハロウィーン
        greetAppend("celebrate", 632, 638)  # 2020 MEIKO
        greetAppend("celebrate", 606, 610)
        greetAddSingle(639)
        greetAddSingle(640)  # 2020 彰人
        greetAppend("season", 94, 187)  # 2020 冬
        greetAppend("celebrate", 602, 606)
        greetAddSingle(641)
        greetAddSingle(642)  # 2020 雫
        greetAppendReleaseHoliday(467)  # 2020 クリスマス
        greetAppend("celebrate", 614, 620)  # 2020 RIN
        greetAppend("celebrate", 620, 626)  # 2020 LEN
        greetAppendReleaseHoliday(468)  # 2020 年末
        greetAppendReleaseHoliday(469)  # 2021 年始
        greetAppend("celebrate", 594, 598)
        greetAddSingle(643)  # 2021 志歩
        greetAppend("celebrate", 610, 614)
        greetAddSingle(644)  # 2021 まふゆ
        greetAppend("celebrate", 626, 632)  # 2021 LUKA

        def greetPlusSingle(greet):
            self.greets[-1]["greets"].append({
                "characterId": getDetailCharId(greet),
                "text": greet["serif"]
            })

        preCharId = 32
        for idx, g in enumerate(greets[644:]):
            index = idx + 645

            if index == 755:
                greetAppend("season", 187, 280)  # 2020 春
            if index == 860:
                greetAppend("season", 280, 373)  # 2020 夏

            if index in [680, 722, 723, 833, 834, 845, 902, 907, 908]:
                greetPlusSingle(g)
                continue

            if (g["characterId"] != 21 and g["characterId"] < preCharId) or index in [712, 829, 928]:
                if not ((867 < index < 898) or index == 1036):  # 2020 七夕, 2021 えむ
                    if g["characterId"] > 20 or g['voice'].split('_')[1] in ["birthday", "anniversary"]:
                        celebrateIdx = (celebrateIdx + 1) % len(greetDict_celebrate)
                        if celebrateIdx == 0:
                            year_celebrate += 1
                        self.greets.append({"theme": getGreetCharContent(celebrateIdx), "year": year_celebrate, "greets": []})
                    elif g['voice'].split('_')[1] in ["spring", "summer", "autumn", "winter"]:
                        seasonIdx = (seasonIdx + 1) % len(greetDict_season)
                        if seasonIdx == 0:
                            year_season += 1
                        self.greets.append({"theme": greetDict_season[seasonIdx], "year": year_season, "greets": []})
                    else:
                        holidayIdx = (holidayIdx + 1) % len(greetDict_holiday)
                        if holidayIdx == 0:
                            year_holiday += 1
                        self.greets.append({"theme": greetDict_holiday[holidayIdx], "year": year_holiday, "greets": []})
            greetAddSingle(index)
            preCharId = g["characterId"]

        greetsPath = osp.join(self.settingDir, "greets.json")
        with open(greetsPath, 'w', encoding='utf-8') as f:
            json.dump(self.greets, f, indent=2, ensure_ascii=False)
        logging.info("Greets Updated")

    def updateSpecials(self):
        url = self.DBurl.format("specialStories")
        stories = json.loads(requests.get(url, headers=self.headers, proxies=request.getproxies(), verify=not self.setting["disabelSSLcheck"]).text)
        if("data" in stories):
            stories = stories["data"]

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
    
    # Infer voice eventID (clue) from areatalks then store them into events.json
    def inferVoiceEventID(self):

        events_dict = {}
        clues = {}

        # Areatalk match string; used for extract event ids
        pattern = r'areatalk_(ev|wl)_(.+)_\d+$'
        self.areatalk_re = re.compile(pattern)

        # Event basic info etc.
        for ei, event in enumerate(self.events):

            if 'id' not in event:
                continue
            
            if 'title' not in event:
                continue

            event_desc = {
                'array_index': ei,
                'id': event['id'],
                'kdyicr_id': event['kdyicr_id'],
                'choffset': 0, # Some event stories start from Ep. "00" instead of "01", e.g., #9
            }
            events_dict[event['id']] = event_desc

        try:
            # Hard-coded event properties
            events_dict[9]['choffset'] = 1
        except:
            pass

        # Obtain event id clue from areatalks
        for areatalk in self.areatalks:
            
            if 'scenarioId' not in areatalk:
                continue

            if 'addEventId' not in areatalk:
                continue

            match = self.areatalk_re.search(areatalk['scenarioId'])
            if match:
                event_type = match.group(1)
                event_clue = match.group(2)

                if event_type == 'wl':
                    event_clue = "wl_" + event_clue
                
                add_to_dict = False

                if event_clue in clues:

                    prev_id = clues[event_clue]['id']

                    # Use the earliest event
                    if prev_id >= 0 and prev_id > areatalk['addEventId']:
                        add_to_dict = True

                else:
                    add_to_dict = True

                if add_to_dict:
                    clues[event_clue] = events_dict.get(areatalk['addEventId'], None)
        
        # Hard-coded patterns as the inference is not perfect
        clues['band_01'] = events_dict.get(1, None)
        clues['night__'] = events_dict.get(53, None)
        clues['shuffle_03'] = events_dict.get(9, None)

        # Store info into self.events
        for clue in clues:

            if clues[clue] == None:
                continue

            event_desc = clues[clue]
            self.events[event_desc['array_index']]['inferredVoiceIDs'] = {
                'prefix': clue,
                'choffset': event_desc['choffset']
            }
        
        # Store to file
        eventsPath = osp.join(self.settingDir, "events.json")
        with open(eventsPath, 'w', encoding='utf-8') as f:
            json.dump(self.events, f, indent=2, ensure_ascii=False)
        logging.info("Events Updated with VoiceID Information")

        self.voiceClues = self.buildVoiceIDClues()
    
    def buildVoiceIDClues(self):

        voiceClues = {}

        for event in self.events:
            if 'inferredVoiceIDs' in event:
                ev_clue_info = event['inferredVoiceIDs']
                voiceClues[ev_clue_info['prefix']] = event
        
        return voiceClues

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
                elif 'levelup' in f:
                    continue
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

        elif storyType in [u"初始卡面", u"升级卡面"]:
            for idx, char in enumerate(characterDict[:26]):
                storyIndex.append(char['name_j'])
                if idx % 4 == 3 and idx < 20:
                    storyIndex.append("-")

        elif storyType in [u"初始地图对话", u"升级地图对话"]:
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
                inmonthly = False
                for areatalk in self.areatalks:
                    if areatalk["scenarioId"] == "none":
                        continue
                    if areatalk["addEventId"] < 0:
                        continue
                    if areatalk["addEventId"] == 1 and preAddId == 0:
                        continue

                    if areatalk["type"] == "none":
                        continue
                    if inspecial:
                        if areatalk["type"] == "limited":
                            continue
                        else:
                            inspecial = False
                    if inmonthly:
                        if "monthly" in areatalk["scenarioId"]:
                            continue
                        else:
                            inmonthly = False

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
                        inmonthly = True
                    else:
                        eventId = areatalk["addEventId"]
                        if eventId != preAddId:
                            eventTitle = self.events[eventId - 1]["title"]
                            storyIndex.append(u"{} {}".format(eventId, eventTitle))
                            self.areaTalkByTime.append({
                                "addEventId": areatalk["addEventId"],
                                "releaseEventId": areatalk["releaseEventId"],
                                "limited": False,
                                "monthly": False
                            })
                            preAddId = eventId
                            preReleaseId = areatalk["releaseEventId"]
                        eventId = areatalk["releaseEventId"]
                        if eventId != areatalk["addEventId"] and eventId != preReleaseId:
                            if eventId <= 1:
                                if "3rdaniv" in areatalk["scenarioId"]:
                                    storyIndex.append(u"【追加】3周年升级")
                                else:
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
                for g in self.greets:
                    storyIndex.append(g["theme"]["ch"] + " " + str(g["year"]))
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
                storyChapter.append(str(epNo) + " " + chapter["title"])
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
            try:
                storyChapter.pop()
            except IndexError:
                pass

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
        
        elif storyType == u"升级卡面":
            storyChapter.append(u"前篇")
            storyChapter.append(u"后篇")

            # MIKU
            if storyIndex == 25:
                storyChapter.append("-")
                for unit in sekaiDict:
                    storyChapter.append(u"{} 前篇".format(unit))
                    storyChapter.append(u"{} 后篇".format(unit))
                    storyChapter.append("-")
            
            # SEKAI VS
            elif storyIndex > 25:
                storyChapter.append("-")
                storyChapter.append(u"SEKAI ver 前篇")
                storyChapter.append(u"SEKAI ver 后篇")

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
                        storyChapter.append(areatalk["talkid"] + " " + u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"], areatalk["talkid"]))
                        if areatalkCount % 6 == 0:
                            storyChapter.append("-")
                            self.chapterScenario.append("")

            elif sort == u"按地点":
                areaId = storyIndex + 1 if storyIndex <= 5 else storyIndex + 2

                areatalkCount = 0
                for areatalk in self.areatalks:
                    if areatalk["addEventId"] > 1:
                        continue
                    if areatalk["type"] == "normal" and areaId == areatalk["areaId"] and areatalk["scenarioId"] != "none":
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(areatalk["talkid"] + " " + u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"], areatalk["talkid"]))
                        areatalkCount += 1
                        if areatalkCount % 10 == 0:
                            storyChapter.append("-")
                            self.chapterScenario.append("")
        
        elif storyType == u"升级地图对话":
            if sort == u"按人物":
                charId = int((storyIndex + 1) * 4 / 5) + 1
                if storyIndex == 30:
                    charId = 26

                areatalkCount = 0
                for areatalk in self.areatalks:
                    if "3rdaniv" not in areatalk["scenarioId"]:
                        continue
                    if areatalk["type"] == "normal" and charId in areatalk["characterIds"] and areatalk["scenarioId"] != "none":
                        areatalkCount += 1
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(areatalk["talkid"] + " " + u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"], areatalk["talkid"]))
                        if areatalkCount % 6 == 0:
                            storyChapter.append("-")
                            self.chapterScenario.append("")

            elif sort == u"按地点":
                areaId = storyIndex + 1 if storyIndex <= 5 else storyIndex + 2

                areatalkCount = 0
                for areatalk in self.areatalks:
                    if "3rdaniv" not in areatalk["scenarioId"]:
                        break
                    if areatalk["type"] == "normal" and areaId == areatalk["areaId"] and areatalk["scenarioId"] != "none":
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(areatalk["talkid"] + " " + u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"], areatalk["talkid"]))
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
                        storyChapter.append(areatalk["talkid"] + " " + u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"], areatalk["talkid"]))
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
                        storyChapter.append(areatalk["talkid"] + " " + u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"], areatalk["talkid"]))
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
                        storyChapter.append(areatalk["talkid"] + " " + u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"], areatalk["talkid"]))
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
                        storyChapter.append(areatalk["talkid"] + " " + u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"], areatalk["talkid"]))

            elif sort == u"按地点":
                areaId = storyIndex + 1 if storyIndex <= 5 else storyIndex + 2

                isRelease = True
                areatalkCount = 0
                for areatalk in self.areatalks:
                    if areatalk["addEventId"] > 1:
                        isRelease = False
                    if areatalk["addEventId"] == 1 and isRelease:
                        continue
                    if areatalk["type"] == "normal" and areaId == areatalk["areaId"] and areatalk["scenarioId"] != "none":
                        charnames = []
                        for cId in areatalk["characterIds"]:
                            charnames.append(characterDict[cId - 1]["name_j"])
                        storyChapter.append(areatalk["talkid"] + " " + u"·".join(charnames))
                        self.chapterScenario.append((areatalk["id"], areatalk["scenarioId"], areatalk["talkid"]))
                        areatalkCount += 1
                        if areatalkCount % 10 == 0:
                            storyChapter.append("-")
                            self.chapterScenario.append("")

        return storyChapter

    def getJsonPath(self, storyType, sort, storyIdx, chapterIdx, source):
        jsonurl = ""
        
        extension = "asset"
        format = 'uni'
        if source == "sekai.best":
            format = 'best'
        
        baseUrl = None
        if source == "sekai.best":
            baseUrl = self.urls['bestBaseUrl']
        elif source == "haruki (CN) 无小对话":
            baseUrl = self.urls['harukiCNBaseUrl']
        elif source == "haruki (JP)":
            baseUrl = self.urls['harukiJPBaseUrl']
        elif source == "unipjsk.com":
            baseUrl = self.urls['uniBaseUrl']
            extension = "json"
        else:
            logging.error("Unknown source. Using sekai.best instead.")
            baseUrl = self.urls['bestBaseUrl']

        if storyType == u"主线剧情":
            unitIdx = storyIdx
            unit = self.mainstory[unitIdx]["assetName"]
            chapters = self.mainstory[unitIdx]["chapters"]
            if unitIdx == 0:
                chapterIdx = int((chapterIdx + 1) * 4 / 5)
            chapter = chapters[chapterIdx]['assetName']

            if format == "best":
                jsonurl = baseUrl + "scenario/unitstory/" \
                    "{}_rip/{}.{}".format(unit, chapter, extension)
            if format == "uni":
                jsonurl = baseUrl + "startapp/scenario/unitstory/" \
                    "{}/{}.{}".format(unit, chapter, extension)
            # print(jsonurl)

            preTitle = chapter.replace("_", "-")
            jsonname = "mainStory_{}.json".format(chapter)

        elif storyType == u"活动剧情":
            eventId = len(self.events) - storyIdx
            event = self.events[eventId - 1]['name']
            chapters = self.events[eventId - 1]["chapters"]
            chapter = chapters[chapterIdx]['assetName']

            if format == "best":
                jsonurl = baseUrl + "event_story/" \
                    "{}/scenario_rip/{}.{}".format(event, chapter, extension)
            if format == "uni":
                jsonurl = baseUrl + "ondemand/event_story/" \
                    "{}/scenario/{}.{}".format(event, chapter, extension)

            preTitle = "-".join(chapter.split("_")[1:])
            jsonname = chapter + ".json"

        elif storyType == u"活动卡面":
            eventId = len(self.events) - storyIdx
            cardId = self.events[eventId - 1]["cards"][int(chapterIdx / 3)]
            charId = self.cards[cardId - 1]["characterId"]

            cardNo = self.cards[cardId - 1]["cardNo"]
            chapter = str(chapterIdx % 3 + 1).zfill(2)
            eventId = str(self.events[eventId - 1]['id']).zfill(3)
            charname = characterDict[charId - 1]['name']
            charId = str(charId).zfill(3)

            if format == "best":
                jsonurl = baseUrl + "character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.{}".format(
                        charId, cardNo, charId, cardNo, charname, chapter, extension)
            elif format == "uni":
                jsonurl = baseUrl + "startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.{}".format(
                        charId, cardNo, charId, cardNo, charname, chapter, extension) 

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

            if format == "best":
                jsonurl = baseUrl + "character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.{}".format(
                        charId, cardNo, charId, cardNo, charname, chapter, extension)
            elif format == "uni":
                jsonurl = baseUrl + "startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.{}".format(
                        charId, cardNo, charId, cardNo, charname, chapter, extension)

            idx = self.festivals[fesId - 1]['id']
            if 'collaboration' in self.festivals[fesId - 1]:
                preTitle = "collabo{}-{}-{}".format(
                    idx, charname, chapter)
            elif self.festivals[fesId - 1]['isBirthday']:
                year = 2021 + int((idx + 2) / 4)
                preTitle = "birth{}-{}-{}".format(
                    year, charname, chapter)
            else:
                year = 2021 + int(idx / 4)
                month = str(idx % 4 * 3 + 1).zfill(2)
                preTitle = "fes{}{}-{}-{}".format(
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

            if format == "best":
                jsonurl = baseUrl + "character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.{}".format(
                        charId, rarity, charId, rarity, charname, chapter, extension)
            elif format == "uni":
                jsonurl = baseUrl + "startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.{}".format(
                        charId, rarity, charId, rarity, charname, chapter, extension)

            if charname == "miku" and realRarity == "02":
                preTitle = "release-miku-{}-02-{}".format(unit, chapter)
            else:
                preTitle = "release-{}-{}-{}".format(charname, rarity[1:], chapter)
            jsonname = preTitle.replace("-", "_") + ".json"

        elif storyType == u"升级卡面":
            currentIdx = storyIdx
            if currentIdx > 25:
                charId = currentIdx - 4
            else:
                charId = int(currentIdx / 5) * 4 + (currentIdx + 1) % 5
            charname = characterDict[charId - 1]['name']

            for f in self.festivals:
                if 'levelup' in f:
                    levelupcards = f['cards']
                    break
            cardId = levelupcards[charId - 1]
            # SEKAI VS
            if charId == 21 and chapterIdx > 2:
                cardId = levelupcards[len(characterDict) - 6 + int(chapterIdx / 3)]
            elif charId == 22 and chapterIdx > 2:
                cardId = levelupcards[-4]
            elif charId == 23 and chapterIdx > 2:
                cardId = levelupcards[-3]
            elif charId == 24 and chapterIdx > 2:
                cardId = levelupcards[-5]
            elif charId == 25 and chapterIdx > 2:
                cardId = levelupcards[-2]
            elif charId == 26 and chapterIdx > 2:
                cardId = levelupcards[-1]

            cardNo = self.cards[cardId - 1]["cardNo"]
            chapter = str(chapterIdx % 3 + 1).zfill(2)
            charname = characterDict[charId - 1]['name']
            charId = str(charId).zfill(3)

            if format == "best":
                jsonurl = baseUrl + "character/member/" \
                    "res{}_no{}_rip/{}{}_{}{}.{}".format(
                        charId, cardNo, charId, cardNo, charname, chapter, extension)
            elif format == "uni":
                jsonurl = baseUrl + "startapp/character/member/" \
                    "res{}_no{}/{}{}_{}{}.{}".format(
                        charId, cardNo, charId, cardNo, charname, chapter, extension)
            
            preTitle = "lvelup2023-{}-{}".format(charname, chapter)
            jsonname = preTitle.replace("-", "_") + ".json"


        elif storyType in [u"初始地图对话", u"升级地图对话", u"追加地图对话"]:
            group = int(self.chapterScenario[chapterIdx][0] / 100)
            jsonname = self.chapterScenario[chapterIdx][1]

            if format == "best":
                jsonurl = baseUrl + "scenario/actionset/" \
                    "group{}_rip/{}.{}".format(group, jsonname, extension)
            elif format == "uni":
                jsonurl = baseUrl + "startapp/scenario/actionset/" \
                    "group{}/{}.{}".format(group, jsonname, extension)

            preTitle = "areatalk-" + self.chapterScenario[chapterIdx][2]
            jsonname = self.chapterScenario[chapterIdx][2] + "_" + jsonname + ".json"

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

                preTitle = "greets-" + charname
                jsonname = preTitle.replace("-", "_") + ".json"

            elif sort == u"按时间":
                greetIdx = len(self.greets) - 1 - storyIdx
                greet = self.greets[greetIdx]
                preTitle = greet["theme"]["ch"] + str(greet["year"])
                jsonname = greet["theme"]["en"] + "_" + str(greet["year"]) + ".json"

        elif storyType == u"特殊剧情":
            storyIdx = len(self.specials) - 1 - storyIdx
            story = self.specials[storyIdx]

            if format == "best":
                jsonurl = baseUrl + "scenario/special/" \
                    "{}_rip/{}.{}".format(story["dirName"], story["fileName"], extension)
            elif format == "uni":
                jsonurl = baseUrl + "startapp/scenario/special/" \
                    "{}/{}.{}".format(story["dirName"], story["fileName"], extension)

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
                title = greets["theme"]["ch"] + str(greets["year"])
                for greet in greets["greets"]:
                    if greet["characterId"] == charId:
                        addGreet(title, greet["text"])

        elif sort == u"按时间":
            storyIdx = len(self.greets) - 1 - storyIdx
            for greet in self.greets[storyIdx]["greets"]:
                addGreet(characterDict[greet["characterId"] - 1]["name_j"], greet["text"])

        with open(savepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("")
