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

    def __getitem__(self, id):
        return self.words[id]

    def __len__(self):
        return len(self.words)

class FlashbackAnalyzer:

    def __init__(self):

        # Flashback
        pattern = r'voice_(.+)_\d+[a-z]?_\d+(?:_?.*)?$'
        self.flashback_re = re.compile(pattern)

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

        hints = []

        if first_indicator == 'ev':

            hints.append("活动剧情 - 格式通常为ev_[团队名]_[第X次]_话数。\n- X以活动种类（混合 or 各团团队活动等）分别计数。\n- X可能为空。")
            
            try:
                ep = int(words.pick(-1))
                hints.append("第%02d话" % ep)
            except ValueError:
                pass

            # hints += self.getClueHintsFromEvent(words, lang)

        elif first_indicator == 'ms':
            hints.append("主线剧情")
        
        elif first_indicator == 'op':
            hints.append("主线剧情 - 序章")
        
        elif first_indicator == 'unit':
            hints.append("推测为主线剧情VSinger部分 - 序号为话数，所有团一起计算话数")
        
        elif first_indicator == 'card':
            hints.append("""卡面剧情 - 格式通常为card_[卡面所属活动/事件]_[角色ID]_[星数和前后篇]。
- 所属活动/事件可能为空，此时推测为初始卡面；ev_开头为活动卡面，见下"关于活动ID"
- 角色ID: 1-一歌 2-咲希 ... 5-实乃里 ... 9-心羽 ... 21-MIKU 22-RIN ...
- 星数和前后篇：4a = 4星前篇, 2b = 2星后篇 etc.
- 活动ID: 格式通常为ev_[团队名]_[第X次]_话数。
  - X以活动种类（混合 or 各团团队活动等）分别计数。
  - X可能为空。""")
        
        return hints

    # Too hard
    def getClueHintsFromEvent(self, words, lang = 'zh-cn'):

        if lang != 'zh-cn':
            raise NotImplementedError
        
        hints = []

        w = words.pick(0)
        if w == 'wl':
            hints.append("World Link活动")
            w = words.pick(0)
        
        teams = {
            'band': "Leo/Need 团队活动",
            'idol': "MORE MORE JUMP! 团队活动",
            'street': "Vivid BAD SQUAD 团队活动",
            'wonder': "Wonderlands x Showtime 团队活动",
            'night': "25时，在nightcord 团队活动",
            'piapro': "VIRTUAL SINGER 团队活动",
            'shuffle': "混合活动"
        }
