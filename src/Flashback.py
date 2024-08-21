from Dictionary import *
import re

class Words:
    def __init__(self, words):
        self.words = words
    
    def pick(self, id):
        try:
            w = self.words[id]
            del self.words[id]
            return w
        except IndexError:
            return ''

    def insert(self, id, word):
        self.words.insert(id, word)

    def __getitem__(self, id):
        return self.words[id]

    def __len__(self):
        return len(self.words)
    
    def __str__(self) -> str:
        return '_'.join(self.words)

class FlashbackAnalyzer:

    def __init__(self, listManager = None):

        # Flashback
        pattern = r'voice_(.+)_\d+[a-z]?_\d+(?:_?.*)?$'
        self.flashback_re = re.compile(pattern)

        # Areatalk match string; used for extract event ids
        pattern = r'areatalk_(ev|wl)_(.+)_\d+$'
        self.areatalk_re = re.compile(pattern)

        # Matcher for mainstory etc.
        self.mainstory_ep_re = re.compile(r'(.*?)(\d+)$')
        self.cardrarityep_re = re.compile(r'(\d+)(.*?)$')

        self.listManager = listManager

        # "night_15" -> events.json objects (from self.events)
        # "wl_band_01" -> events.json objects
        self.clue_dict = {}
        
        # "band" -> mainStory.json objects
        self.mainstory = {}
        
        # eventId: int -> events.json objects (necessary info only)
        self.events = {}

        self.noClue = {
            'id': -1,
            'title': u"未知剧情",
            'choffset': 0,
            'chapters': [],
        }

        self.voice_ms_to_mainstory_id = {
            'band': 'light_sound',
            'idol': 'idol',
            'street': 'street',
            'wonder': 'theme_park',
            'night': 'school_refusal',
            'piapro': 'piapro'
        }

        if self.listManager:

            for ms in self.listManager.mainstory:
                self.mainstory[ms['unit']] = ms

            for event in self.listManager.events:

                if 'id' not in event:
                    continue
                
                if 'title' not in event:
                    continue

                event_desc = {
                    'id': event['id'],
                    'title': event['title'],
                    'choffset': 0, # Some event stories start from Ep. "00" instead of "01", e.g., #9
                    'chapters': [],
                }
                self.events[event['id']] = event_desc

                if 'chapters' not in event:
                    continue

                event_desc['chapters'] = [c['title'] for c in event['chapters']]
                self.events[event['id']] = event_desc

            try:
                # Hard-coded event properties
                self.events[9]['choffset'] = 1
            except:
                pass

            # Obtain event id clue from areatalks
            for areatalk in self.listManager.areatalks:
                
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

                    if event_clue in self.clue_dict:

                        prev_id = self.clue_dict[event_clue]['id']

                        # Use the earliest event
                        if prev_id >= 0 and prev_id > areatalk['addEventId']:
                            add_to_dict = True

                    else:
                        add_to_dict = True

                    if add_to_dict:
                        self.clue_dict[event_clue] = self.events.get(areatalk['addEventId'], self.noClue)
            
            # Hard-coded patterns
            self.clue_dict['band_01'] = self.events.get(1, self.noClue)
            self.clue_dict['night__'] = self.events.get(53, self.noClue)
            self.clue_dict['shuffle_03'] = self.events.get(9, self.noClue)

    '''
    Infer clue (some scenarioID) from voice id

      VoiceId examples:                         Matched Clue:                   Interpretation:
    - voice_op_band0_15_03                      op_band0                        Leo/Need opening
    - voice_card_18_3a_27_18                    card_18_3a                      Card: (18)Mafuyu (3)3Star (a)Part1
    - voice_ms_night13_28_18                    ms_night13                      (ms)Main Story - (night)Niigo - (13)Ep.13
    - voice_ev_wl_band_01_05_28_03              ev_wl_band_01_05                (ev)Event Story - (wl)World Link - (band)Leo/Need - (01)1st World Link?? - (05)Ep.5
    - voice_ev_street_18_06_98b_67              ev_street_18_06                 ev - (street)Vivid BAD SQUAD - (18)18th Unit Event (i.e., #135 OVER RAD SQUAD!!) - (06)Ep.6
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

    # TODO: Automaton / FSM?
    def getClueHints(self, clue, lang = 'zh-cn'):

        if lang != 'zh-cn':
            raise NotImplementedError

        words = Words(clue.split('_'))
        first_indicator = words.pick(0)

        # Skip 'sc' for 'sc_ev_xxxx'
        if first_indicator == 'sc':
            first_indicator = words.pick(0)

        hints = []
        
        # Sometimes cards will be labeled "ev_xxxxxxxxx_chID_rarityEp", without "card"
        if first_indicator == 'ev' and (words[-1][-1] == 'a' or words[-1][-1] == 'b'):
            first_indicator = 'card'

        # Event Story
        if first_indicator == 'ev':

            # hints.append("\n活动剧情 - 格式通常为ev_[活动种类]_[第X次]_话数。\n- X以活动种类（混合(shuffle) or 各团团队活动等）分别计数。\n- X可能为空（如第53期活动的X就为空）。")
            
            ep = -1
            try:
                ep = int(words.pick(-1))
                # hints.append("第%02d话" % ep)
            except ValueError:
                pass

            eventInfo = self.getEventInfo(words)
            if ep >= 0:
                ep += eventInfo['choffset']

            hints.append("%d-%02d" % (eventInfo['id'], ep))
            hints.append("%s" % (eventInfo['title']))
            epName = eventInfo['chapters'][ep-1] if (ep > 0 and ep <= len(eventInfo['chapters'])) else u"未知章节"
            hints.append("%s" % (epName))

        # Main Story
        elif first_indicator == 'ms' or first_indicator == 'op' or first_indicator == 'unit':

            w = words.pick(0) # Something like "band0"
            match = self.mainstory_ep_re.search(w)

            if match:

                team, ep = match.groups() # team = "band", ep = "0"
                try:
                    ep = int(ep)
                except ValueError:
                    ep = -1

                if team in self.voice_ms_to_mainstory_id:
                    hints.append(u"%s 主线剧情 - %02d话" % (unitDict[self.voice_ms_to_mainstory_id[team]], ep))
                    listmgr_team = self.voice_ms_to_mainstory_id[team] # "light_sound"
                    chapters = self.mainstory[listmgr_team]['chapters']

                    # No openings for 'piapro'
                    if first_indicator == 'unit':
                        if (ep > 0 and ep <= len(chapters)):
                            epHint = ['ln', 'mmj', 'vbs', 'ws', u"25时"][(ep-1) // 4] + '-%d' % (((ep-1) % 4) + 1)
                            epName = ("(%s) " % epHint) + chapters[ep-1]['title']
                        else:
                            epName = u"未知章节"
                    else:
                        epName = chapters[ep]['title'] if (ep >= 0 and ep < len(chapters)) else u"未知章节"

                    hints.append(epName)
                else:
                    hints.append(u"未知主线剧情")

            else:
                hints.append(u"未知主线剧情")
        
        # Opening
        # elif first_indicator == 'op':
        #     hints.append("主线剧情 - 序章")
        
        # elif first_indicator == 'unit':
        #     hints.append("\n推测为主线剧情VSinger部分\n- 序号为话数，所有团一起计算话数")
        
        elif first_indicator == 'card':
            
            starsep = words.pick(-1)
            stars = "?"
            ep = u"未知章节"
            match = self.cardrarityep_re.search(starsep)
            if match:
                try:
                    stars = int(match.group(1))
                except:
                    pass
                ep = match.group(2)
            
            if ep == 'a':
                ep = u"前篇"
            elif ep == 'b':
                ep = u"后篇"
            
            character_id = words.pick(-1)
            try:
                character_name = characterDict[int(character_id)-1]['name_j']
            except:
                character_name = character_id

            event_id = str(words)

            event_hints = u"卡面来自 %s" % event_id
            if event_id == '':
                event_hints = u"初期卡面"
            else:
                event_info = self.getEventInfo(words)
                if event_info['id'] > 0:
                    event_hints = "%s - %s" % (event_info['id'], event_info['title'])
            
            hints.append(event_hints)
            hints.append("%s ☆%s %s" % (character_name, stars, ep))

#             hints.append("""\n卡面剧情\n格式通常为card_[卡面所属活动/事件]_[角色ID]_[星数和前后篇]。
# - 所属活动/事件可能为空，此时推测为初始卡面；ev_开头为活动卡面，见下"关于活动ID"
# - 角色ID: 1-一歌 2-咲希 ... 5-实乃里 ... 9-心羽 ... 21-MIKU 22-RIN ...
# - 星数和前后篇：4a = 4星前篇, 2b = 2星后篇 etc.
# - 活动ID: 格式通常为ev_[活动种类]_[第X次]_话数。
#   - X以活动种类（混合(shuffle) or 各团团队活动等）分别计数。
#   - X可能为空（如第53期活动的X就为空）。""")

        else:
            hints.append(u"闪回：未知来源")
        
        return hints

    def getEventInfo(self, words):

        # Skip "sc"
        if words[0] == 'sc':
            words.pick(0)

        # Skip "ev"
        if words[0] == 'ev':
            words.pick(0)

        return self.clue_dict.get(str(words), self.noClue)
