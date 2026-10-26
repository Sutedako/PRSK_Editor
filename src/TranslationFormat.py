"""Parser for the ID-based translation TXT v2 format."""
import re


def is_v2(text):
    return any(line.startswith('@') for line in text.splitlines())


def parse_v2(text, scenario_id, source):
    entries = {}
    version = False
    scenario = False
    current = None
    body = []
    required = {talk['translation_key'] for talk in source if 'translation_key' in talk}

    def fail(number, message):
        raise ValueError(f'翻译 TXT v2 第 {number} 行：{message}')

    def finish():
        if current is not None:
            lines = body[:]
            while lines and not lines[0]:
                lines.pop(0)
            while lines and not lines[-1]:
                lines.pop()
            entries[current]['text'] = '\n'.join(lines)

    if not scenario_id:
        raise ValueError('翻译 TXT v2：当前剧本缺少 ScenarioId')
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith('#'):
            continue
        if not version:
            if not line.strip():
                continue
            if line.rstrip(' \t') != '@version:2':
                fail(number, '第一条有效行必须为 @version:2（版本缺失或不支持）')
            version = True
            continue
        if line.startswith('@'):
            label = line.rstrip(' \t')
            if label.startswith('@scenario:'):
                if scenario or current is not None:
                    fail(number, '@scenario 重复或位置不合法')
                if label[len('@scenario:'):] != scenario_id:
                    fail(number, 'ScenarioId 与当前剧本不一致')
                scenario = True
                continue
            match = re.fullmatch(r'@(dialog|banner|marker):([0-9]+)(.*)', label)
            if not match:
                fail(number, '未知标签、重复版本或标记语法错误：' + label)
            if not scenario:
                fail(number, '翻译条目前缺少 @scenario')
            kind, identifier, suffix = match.groups()
            key = (kind, int(identifier))
            if key[1] == 0:
                fail(number, '编号必须大于零')
            if kind == 'dialog':
                if not suffix.startswith('[') or not suffix.endswith(']'):
                    fail(number, '对话说话人必须用方括号包围')
                speaker = suffix[1:-1]
            else:
                if suffix:
                    fail(number, '效果条目标记语法错误')
                speaker = '场景' if kind == 'banner' else '左上场景'
            if key in entries:
                fail(number, f'重复编号：@{kind}:{identifier}')
            if key not in required:
                fail(number, f'编号越界、类型不匹配或不属于当前剧本：@{kind}:{identifier}')
            finish()
            current = key
            entries[key] = {'speaker': speaker, 'text': ''}
            body = []
        elif current is None:
            if line.strip():
                fail(number, '第一条翻译之前存在无归属正文')
        else:
            if line.startswith(('\\@', '\\#', '\\\\')):
                line = line[1:]
            body.append(line.strip())
    finish()
    if not version or not scenario:
        raise ValueError('翻译 TXT v2：缺少 @version:2 或 @scenario')
    missing = required - entries.keys()
    if missing:
        labels = ', '.join(f'@{kind}:{number:03}' for kind, number in sorted(missing))
        raise ValueError('翻译 TXT v2：缺失条目 ' + labels)

    result = []
    for index, talk in enumerate(source, 1):
        entry = entries.get(talk.get('translation_key'), talk)
        lines = entry['text'].split('\n')
        for offset, line in enumerate(lines):
            result.append(dict(idx=index, speaker=entry['speaker'], text=line,
                               start=offset == 0, end=offset == len(lines) - 1,
                               checked=True, save=True, format_v2=True))
    return result
