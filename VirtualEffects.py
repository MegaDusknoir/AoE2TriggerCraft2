from __future__ import annotations

import base64
import json
import re
import secrets
import string
import zlib
from binascii import Error as Base64DecodeError
from dataclasses import dataclass
from typing import Callable

VIRTUAL_EFFECT_TYPE_ID_BASE = 100000
TRIGGER_CRAFT_METADATA_HEADER = '<TriggerCraftMetadata>'

_VIRTUAL_EFFECT_MARKER_RE = re.compile(
    r'\A/\*<TriggerCraftVirtualType:(?P<virtual_type_id>\d+)>\*/'
)
_VIRTUAL_EFFECT_FUNCTION_RE = re.compile(
    r'\A/\*<TriggerCraftVirtualType:(?P<virtual_type_id>\d+)>\*/'
    r'(?:/\*(?P<metadata>(?:(?!\*/)[\s\S])*)\*/)?'
    r'void (?P<function_name>VE_[A-Za-z0-9]+)\(\)\{(?P<body>.*)\}\Z',
    re.DOTALL,
)
_VIRTUAL_EFFECT_HEADER_RE = re.compile(
    r'\A/\*<TriggerCraftVirtualType:(?P<virtual_type_id>\d+)>\*/'
    r'(?:/\*(?P<metadata>(?:(?!\*/)[\s\S])*)\*/)?'
    r'void (?P<function_name>VE_[A-Za-z0-9]+)\(\)\{'
)
_FUNCTION_NAME_RE = re.compile(r'VE_[A-Za-z0-9]+\Z')
_RANDOM_NAME_ALPHABET = string.ascii_letters + string.digits
_XS_TEXT_EXPRESSION = (
    r'(?:"(?:\\.|[^"\\])*"|chr\(\s*\d+\s*\))'
    r'(?:\s*\+\s*(?:"(?:\\.|[^"\\])*"|chr\(\s*\d+\s*\)))*'
)
_XS_TEXT_TOKEN_RE = re.compile(
    r'"(?:\\.|[^"\\])*"|chr\(\s*(\d+)\s*\)'
)
_XS_STRING_LITERAL_RE = re.compile(r'"(?:\\.|[^"\\])*"', re.DOTALL)
_LOCALIZED_SEND_CHAT_ARGUMENTS_RE = re.compile(
    r'\bxsSendChat\s*\(\s*(?:m|""),\s*'
    r'(?P<source_player>-?\d+)\s*,\s*'
    r'(?P<play_sound>true|false)\s*\)\s*;',
    re.IGNORECASE,
)
_LOCALIZED_DISPLAY_INSTRUCTIONS_ARGUMENTS_RE = re.compile(
    r'\bxsDisplayInstructions\s*\(\s*(?:m|""),\s*'
    r'(?P<display_time>-?\d+)\s*,\s*'
    r'(?P<source_player>-?\d+)\s*,\s*'
    r'(?P<object_list_unit_id>-?\d+)\s*,\s*'
    r'(?P<instruction_panel_position>-?\d+)\s*,\s*'
    r'(?P<use_tag_color_for_icon>true|false)\s*,\s*'
    r'(?P<play_sound>true|false)\s*,\s*'
    r'(?P<sound_name>' + _XS_TEXT_EXPRESSION + r')\s*,\s*-1\s*\)\s*;',
    re.IGNORECASE,
)
_LOCALIZED_UNIT_NAME_ID_RE = re.compile(
    r'\bxsSetUnitName\s*\(\s*(?P<unit_id>-?\d+)\s*,\s*m\s*\)\s*;',
    re.IGNORECASE,
)
_LOCALIZED_TECH_NAME_ARGUMENTS_RE = re.compile(
    r'\bxsSetTechName\s*\(\s*(?P<technology>-?\d+)\s*,\s*'
    r'(?P<source_player>-?\d+)\s*,\s*m\s*\)\s*;',
    re.IGNORECASE,
)


def _reject_nonstandard_json_constant(value: str):
    raise ValueError(f'Invalid JSON constant: {value}')


def strict_json_loads(json_text: str) -> object:
    return json.loads(
        json_text,
        parse_constant=_reject_nonstandard_json_constant,
    )


@dataclass(frozen=True)
class DisplayInstructionsAttributes:
    message: str
    display_time: int
    source_player: int
    object_list_unit_id: int
    instruction_panel_position: int
    use_tag_color_for_icon: bool
    play_sound: bool
    sound_name: str


@dataclass(frozen=True)
class SendChatAttributes:
    source_player: int
    play_sound: bool


@dataclass(frozen=True)
class UnitNameAttributes:
    unit_id: int


@dataclass(frozen=True)
class TechNameAttributes:
    technology: int
    source_player: int


DEFAULT_DISPLAY_INSTRUCTIONS_ATTRIBUTES = DisplayInstructionsAttributes(
    message='',
    display_time=10,
    source_player=1,
    object_list_unit_id=-1,
    instruction_panel_position=0,
    use_tag_color_for_icon=False,
    play_sound=False,
    sound_name='',
)


def virtual_effect_type_id(virtual_type_id: int) -> int:
    return VIRTUAL_EFFECT_TYPE_ID_BASE + virtual_type_id


def virtual_type_id(effect_type_id: int) -> int | None:
    if effect_type_id < VIRTUAL_EFFECT_TYPE_ID_BASE:
        return None
    return effect_type_id - VIRTUAL_EFFECT_TYPE_ID_BASE


def get_virtual_effect_marker_id(code: str | None) -> int | None:
    if not isinstance(code, str):
        return None
    match = _VIRTUAL_EFFECT_MARKER_RE.match(code)
    return int(match.group('virtual_type_id')) if match else None


def has_virtual_effect_marker(code: str | None) -> bool:
    return get_virtual_effect_marker_id(code) is not None


def build_virtual_effect_script(
    marker_id: int,
    function_name: str,
    body: str,
    metadata: str | None = None,
) -> str:
    if _FUNCTION_NAME_RE.fullmatch(function_name) is None:
        raise ValueError(f'Invalid virtual effect function name: {function_name!r}')
    metadata_comment = f'/*{metadata}*/' if metadata is not None else ''
    return (
        f'/*<TriggerCraftVirtualType:{marker_id}>*/'
        f'{metadata_comment}void {function_name}(){{{body}}}'
    )


def parse_virtual_effect_header(
    code: str | None,
) -> tuple[int, str | None, str] | None:
    if not isinstance(code, str):
        return None
    match = _VIRTUAL_EFFECT_HEADER_RE.match(code)
    if match is None:
        return None
    return (
        int(match.group('virtual_type_id')),
        match.group('metadata'),
        match.group('function_name'),
    )


def rename_virtual_effect_function(
    code: str | None,
    function_name: str,
) -> str | None:
    if not isinstance(code, str) or _FUNCTION_NAME_RE.fullmatch(function_name) is None:
        return None
    header_match = _VIRTUAL_EFFECT_HEADER_RE.match(code)
    if header_match is None:
        return None
    current_name = header_match.group('function_name')
    function_name_start = code.rfind(current_name, 0, header_match.end())
    if function_name_start < 0:
        return None
    return (
        code[:function_name_start]
        + function_name
        + code[function_name_start + len(current_name):]
    )


def invert_localized_send_chat_silent(code: str | None) -> str | None:
    header = parse_virtual_effect_header(code)
    if header is None or header[0] != 0:
        return None
    match = _find_xs_call_arguments(
        _LOCALIZED_SEND_CHAT_ARGUMENTS_RE,
        code,
    )
    if match is None:
        return None
    silent_start, silent_end = match.span('play_sound')
    silent_value = match.group('play_sound').lower()
    replacement = 'false' if silent_value == 'true' else 'true'
    return code[:silent_start] + replacement + code[silent_end:]


def ensure_unique_virtual_effect_function_names(trigger_manager) -> int:
    virtual_effects = []
    all_names = set()
    for trigger in trigger_manager.triggers:
        for effect in trigger.effects:
            if effect.effect_type != 55:
                continue
            header = parse_virtual_effect_header(effect.message)
            if header is None:
                continue
            virtual_effects.append((effect, header[2]))
            all_names.add(header[2])

    used_names = set()
    renamed_count = 0
    for effect, function_name in virtual_effects:
        if function_name in used_names:
            replacement = create_unique_function_name(all_names | used_names)
            renamed_message = rename_virtual_effect_function(
                effect.message,
                replacement,
            )
            if renamed_message is None:
                raise ValueError(
                    f'Could not rename virtual effect function {function_name!r}'
                )
            effect.message = renamed_message
            all_names.add(replacement)
            function_name = replacement
            renamed_count += 1
        used_names.add(function_name)
    return renamed_count


def encode_virtual_effect_json(data: object) -> str:
    json_bytes = json.dumps(
        data,
        ensure_ascii=False,
        separators=(',', ':'),
    ).encode('utf-8')
    return base64.b64encode(zlib.compress(json_bytes, wbits=-15)).decode('ascii')


def decode_virtual_effect_json(
    metadata: str | None,
) -> tuple[bool, object | None]:
    if not isinstance(metadata, str):
        return False, None
    try:
        compressed = base64.b64decode(metadata, validate=True)
        decompressor = zlib.decompressobj(wbits=-15)
        json_bytes = decompressor.decompress(compressed, 1_048_577)
        if len(json_bytes) > 1_048_576 or decompressor.unconsumed_tail:
            return False, None
        json_bytes += decompressor.flush()
        if len(json_bytes) > 1_048_576 or not decompressor.eof or decompressor.unused_data:
            return False, None
        return True, strict_json_loads(json_bytes.decode('utf-8'))
    except (
        Base64DecodeError,
        UnicodeDecodeError,
        ValueError,
        RecursionError,
        zlib.error,
    ):
        return False, None


def encode_trigger_metadata_description(data: object) -> str:
    return (
        TRIGGER_CRAFT_METADATA_HEADER
        + '<'
        + encode_virtual_effect_json(data)
        + '>'
    )


def decode_trigger_metadata_description(
    description: str | None,
) -> tuple[bool, object | None]:
    if not isinstance(description, str) or not description.startswith(
        TRIGGER_CRAFT_METADATA_HEADER
    ):
        return False, None

    payload = description[len(TRIGGER_CRAFT_METADATA_HEADER):]
    if not payload.startswith('<') or not payload.endswith('>'):
        return False, None

    return decode_virtual_effect_json(payload[1:-1])


def parse_virtual_effect_script(
    code: str | None,
) -> tuple[int, str, str] | None:
    if not isinstance(code, str):
        return None
    match = _VIRTUAL_EFFECT_FUNCTION_RE.fullmatch(code)
    if match is None:
        return None
    return (
        int(match.group('virtual_type_id')),
        match.group('function_name'),
        match.group('body'),
    )


def validate_localized_effect_json(
    data: object,
) -> bool:
    if not isinstance(data, dict) or not isinstance(data.get('default'), str):
        return False

    groups = data.get('group', {})
    if not isinstance(groups, dict):
        return False
    for group_name, locales in groups.items():
        if (
            not isinstance(group_name, str)
            or group_name in ('default', 'group')
            or group_name.isascii() and group_name.isdecimal()
            or not isinstance(locales, list)
            or not locales
        ):
            return False
        if any(
            isinstance(locale_id, bool)
            or not isinstance(locale_id, int)
            or locale_id < 0
            for locale_id in locales
        ):
            return False

    for language_key, text in data.items():
        if not isinstance(language_key, str):
            return False
        if language_key in ('default', 'group'):
            continue
        if not isinstance(text, str):
            return False
        if language_key.isascii() and language_key.isdecimal():
            continue
        if language_key not in groups:
            return False
    return True


def _create_localized_message_body(
    data: object,
    create_call: Callable[[str], str],
    json_text_valid: bool = True,
) -> str:
    if not validate_localized_effect_json(data):
        return create_call('""')
    if not json_text_valid:
        return create_call('""')

    locale_branches = []
    groups = data.get('group', {})
    for language_key, text in data.items():
        if language_key in ('default', 'group'):
            continue
        if language_key in groups:
            locale_ids = groups[language_key]
        else:
            locale_ids = [int(language_key)]
        locale_branches.append(
            f'if(loc=={locale_ids[0]}' +
            ''.join(f'||loc=={locale_id}' for locale_id in locale_ids[1:]) +
            f'){{m={_xs_text_expression(text)};}}'
        )

    if not locale_branches:
        return (
            f'string m={_xs_text_expression(data["default"])};'
            f'{create_call("m")}'
        )
    branches = locale_branches[0] + ''.join(
        branch.replace('if(', 'else if(', 1)
        for branch in locale_branches[1:]
    )
    fallback = f'else{{m={_xs_text_expression(data["default"])};}}'
    return (
        'int loc=xsGetLocale();'
        'string m="";'
        f'{branches}{fallback}{create_call("m")}'
    )


def create_localized_display_instructions_body(
    data: object,
    display_time: int,
    source_player: int,
    object_list_unit_id: int,
    instruction_panel_position: int,
    use_tag_color_for_icon: bool,
    play_sound: bool,
    sound_name: str,
    json_text_valid: bool = True,
) -> str:
    def create_call(message_expression: str) -> str:
        return (
            'xsDisplayInstructions('
            f'{message_expression},'
            f'{display_time},'
            f'{source_player},'
            f'{object_list_unit_id},'
            f'{instruction_panel_position},'
            f'{"true" if use_tag_color_for_icon else "false"},'
            f'{"true" if play_sound else "false"},'
            f'{_xs_text_expression(sound_name)},'
            '-1);'
        )

    return _create_localized_message_body(data, create_call, json_text_valid)


def create_localized_send_chat_body(
    data: object,
    source_player: int,
    play_sound: bool,
    json_text_valid: bool = True,
) -> str:
    def create_call(message_expression: str) -> str:
        return (
            f'xsSendChat({message_expression},{source_player},'
            f'{"false" if play_sound else "true"});'
        )

    return _create_localized_message_body(data, create_call, json_text_valid)


def create_localized_unit_name_body(
    data: object,
    unit_id: int,
    json_text_valid: bool = True,
) -> str:
    def create_call(message_expression: str) -> str:
        return f'xsSetUnitName({unit_id},{message_expression});'

    return _create_localized_message_body(data, create_call, json_text_valid)


def create_localized_tech_name_body(
    data: object,
    technology: int,
    source_player: int,
    json_text_valid: bool = True,
) -> str:
    def create_call(message_expression: str) -> str:
        return (
            f'xsSetTechName({technology},{source_player},'
            f'{message_expression});'
        )

    return _create_localized_message_body(data, create_call, json_text_valid)


def _xs_text_expression(text: str) -> str:
    def _escapeXsString(text: str) -> str:
        return (
            text.replace('\\', '\\\\')
            .replace('"', '\\"')
        )

    if text == '':
        return '""'
    parts = re.findall(r'[\x20-\x7E]+|[^\x20-\x7E]+', text)

    result = '+'.join(
        f'"{_escapeXsString(part)}"' if all('\x20' <= c <= '\x7E' for c in part)
        else '+'.join(f'chr({x})' for x in part.encode('utf-8'))
        for part in parts
    )
    return result



def create_localized_display_instructions_script(
    function_name: str,
    data: object,
    display_time: int,
    source_player: int,
    object_list_unit_id: int,
    instruction_panel_position: int,
    use_tag_color_for_icon: bool,
    play_sound: bool,
    sound_name: str,
    json_text_valid: bool = True,
) -> str:
    body = create_localized_display_instructions_body(
        data,
        display_time,
        source_player,
        object_list_unit_id,
        instruction_panel_position,
        use_tag_color_for_icon,
        play_sound,
        sound_name,
        json_text_valid,
    )
    return build_virtual_effect_script(
        1,
        function_name,
        body,
        encode_virtual_effect_json(data),
    )


def create_localized_send_chat_script(
    function_name: str,
    data: object,
    source_player: int,
    play_sound: bool,
    json_text_valid: bool = True,
) -> str:
    body = create_localized_send_chat_body(
        data,
        source_player,
        play_sound,
        json_text_valid,
    )
    return build_virtual_effect_script(
        0,
        function_name,
        body,
        encode_virtual_effect_json(data),
    )


def create_localized_unit_name_script(
    function_name: str,
    data: object,
    unit_id: int,
    json_text_valid: bool = True,
) -> str:
    body = create_localized_unit_name_body(data, unit_id, json_text_valid)
    return build_virtual_effect_script(
        2,
        function_name,
        body,
        encode_virtual_effect_json(data),
    )


def create_localized_tech_name_script(
    function_name: str,
    data: object,
    technology: int,
    source_player: int,
    json_text_valid: bool = True,
) -> str:
    body = create_localized_tech_name_body(
        data,
        technology,
        source_player,
        json_text_valid,
    )
    return build_virtual_effect_script(
        3,
        function_name,
        body,
        encode_virtual_effect_json(data),
    )


def parse_virtual_effect_json_metadata(
    code: str | None,
) -> tuple[int, str, bool, object | None] | None:
    parsed_header = parse_virtual_effect_header(code)
    if parsed_header is None:
        return None
    virtual_type, metadata, function_name = parsed_header
    decoded, data = decode_virtual_effect_json(metadata)
    return virtual_type, function_name, decoded, data


def parse_localized_send_chat(
    code: str | None,
) -> tuple[str, bool, object | None] | None:
    parsed = parse_virtual_effect_json_metadata(code)
    if parsed is None or parsed[0] != 0:
        return None
    return parsed[1], parsed[2], parsed[3]


def parse_localized_display_instructions(
    code: str | None,
) -> tuple[str, bool, object | None] | None:
    parsed = parse_virtual_effect_json_metadata(code)
    if parsed is None or parsed[0] != 1:
        return None
    return parsed[1], parsed[2], parsed[3]


def parse_localized_unit_name(
    code: str | None,
) -> tuple[str, bool, object | None] | None:
    parsed = parse_virtual_effect_json_metadata(code)
    if parsed is None or parsed[0] != 2:
        return None
    return parsed[1], parsed[2], parsed[3]


def parse_localized_tech_name(
    code: str | None,
) -> tuple[str, bool, object | None] | None:
    parsed = parse_virtual_effect_json_metadata(code)
    if parsed is None or parsed[0] != 3:
        return None
    return parsed[1], parsed[2], parsed[3]


def _parse_xs_text_expression(expression: str) -> str | None:
    if re.fullmatch(_XS_TEXT_EXPRESSION, expression) is None:
        return None

    value = bytearray()
    for token in _XS_TEXT_TOKEN_RE.finditer(expression):
        if token.group(1) is not None:
            char_code = int(token.group(1))
            if char_code > 255:
                return None
            value.append(char_code)
        else:
            try:
                literal = json.loads(token.group(0))
            except json.JSONDecodeError:
                return None
            if not isinstance(literal, str):
                return None
            value.extend(literal.encode('utf-8'))
    try:
        return value.decode('utf-8')
    except UnicodeDecodeError:
        return None


def _find_xs_call_arguments(
    pattern: re.Pattern,
    code: str,
) -> re.Match | None:
    masked_code = _XS_STRING_LITERAL_RE.sub(
        lambda match: '"' + ' ' * (len(match.group(0)) - 2) + '"',
        code,
    )
    masked_match = pattern.search(masked_code)
    if masked_match is None:
        return None
    return pattern.match(code, masked_match.start())


def parse_localized_send_chat_attributes(
    code: str | None,
) -> SendChatAttributes | None:
    if not isinstance(code, str):
        return None
    match = _find_xs_call_arguments(_LOCALIZED_SEND_CHAT_ARGUMENTS_RE, code)
    if match is None:
        return None
    return SendChatAttributes(
        source_player=int(match.group('source_player')),
        play_sound=match.group('play_sound').lower() == 'false',
    )


def parse_localized_display_instructions_attributes(
    code: str | None,
) -> DisplayInstructionsAttributes | None:
    if not isinstance(code, str):
        return None
    match = _find_xs_call_arguments(
        _LOCALIZED_DISPLAY_INSTRUCTIONS_ARGUMENTS_RE,
        code,
    )
    if match is None:
        return None
    sound_name = _parse_xs_text_expression(match.group('sound_name'))
    if sound_name is None:
        return None
    return DisplayInstructionsAttributes(
        message='',
        display_time=int(match.group('display_time')),
        source_player=int(match.group('source_player')),
        object_list_unit_id=int(match.group('object_list_unit_id')),
        instruction_panel_position=int(match.group('instruction_panel_position')),
        use_tag_color_for_icon=match.group('use_tag_color_for_icon').lower() == 'true',
        play_sound=match.group('play_sound').lower() == 'true',
        sound_name=sound_name,
    )


def parse_localized_unit_name_attributes(
    code: str | None,
) -> UnitNameAttributes | None:
    if not isinstance(code, str):
        return None
    match = _LOCALIZED_UNIT_NAME_ID_RE.search(code)
    if match is None:
        return None
    return UnitNameAttributes(unit_id=int(match.group('unit_id')))


def transform_virtual_effect_all_in_one(
    code: str | None,
    from_player: int,
    to_player: int,
    include_player_source: bool = False,
    change_from_player_only: bool = False,
    change_self_excluding: bool = False,
    color_tag_mapping: list[str] = None,
    unit_mappings: list[list[int]] = [],
) -> str | None:
    def change_color_tag(data:dict[str,str]) -> bool:
        modified = False
        for language_key, text in data.items():
            if language_key in ('group',):
                continue
            if text.startswith(color_tag_mapping[from_player]):
                data[language_key] = text.replace(
                    color_tag_mapping[from_player],
                    color_tag_mapping[to_player],
                    count=1
                )
                modified = True
        return modified

    parsed_script = parse_virtual_effect_script(code)
    parsed_header = parse_virtual_effect_header(code)
    if parsed_script is None or parsed_header is None:
        return None

    virtual_type_id, function_name, _ = parsed_script
    header_type_id, metadata, _ = parsed_header
    if virtual_type_id != header_type_id:
        return None

    if not (
        color_tag_mapping
        or (virtual_type_id in (0, 1, 3) and include_player_source)
        or (virtual_type_id in (2,) and unit_mappings)
    ):
        return None

    decoded, data = decode_virtual_effect_json(metadata)
    if not decoded or not validate_localized_effect_json(data):
        return None

    recreate = False
    if virtual_type_id == 0:
        attributes = parse_localized_send_chat_attributes(code)
        if attributes is None:
            return None
        source_player = attributes.source_player
        if include_player_source and (
            not change_from_player_only or attributes.source_player == from_player
        ):
            source_player = to_player
            recreate = True
        elif change_self_excluding and source_player == to_player:
            source_player = from_player
            recreate = True
        if color_tag_mapping:
            if change_color_tag(data):
                recreate = True
        if recreate:
            return create_localized_send_chat_script(
                function_name,
                data,
                source_player,
                attributes.play_sound,
            )

    if virtual_type_id == 1:
        attributes = parse_localized_display_instructions_attributes(code)
        if attributes is None:
            return None
        source_player = attributes.source_player
        if include_player_source and (
            not change_from_player_only or attributes.source_player == from_player
        ):
            source_player = to_player
            recreate = True
        elif change_self_excluding and source_player == to_player:
            source_player = from_player
            recreate = True
        if color_tag_mapping:
            if change_color_tag(data):
                recreate = True
        if recreate:
            return create_localized_display_instructions_script(
                function_name,
                data,
                attributes.display_time,
                source_player,
                attributes.object_list_unit_id,
                attributes.instruction_panel_position,
                attributes.use_tag_color_for_icon,
                attributes.play_sound,
                attributes.sound_name,
            )

    if virtual_type_id == 2:
        attributes = parse_localized_unit_name_attributes(code)
        if attributes is None:
            return None

        unit_id = attributes.unit_id
        if unit_mappings:
            for unit_mapping in unit_mappings:
                if attributes.unit_id == unit_mapping[from_player]:
                    unit_id = unit_mapping[to_player]
                    recreate = True
                    break
        if color_tag_mapping:
            if change_color_tag(data):
                recreate = True
        if recreate:
            return create_localized_unit_name_script(
                function_name,
                data,
                unit_id,
            )

    if virtual_type_id == 3:
        attributes = parse_localized_tech_name_attributes(code)
        if attributes is None:
            return None
        source_player = attributes.source_player
        if include_player_source and (
            not change_from_player_only or attributes.source_player == from_player
        ):
            source_player = to_player
            recreate = True
        elif change_self_excluding and source_player == to_player:
            source_player = from_player
            recreate = True
        if color_tag_mapping:
            if change_color_tag(data):
                recreate = True
        if recreate:
            return create_localized_tech_name_script(
                function_name,
                data,
                attributes.technology,
                source_player,
            )

    return None


def parse_localized_tech_name_attributes(
    code: str | None,
) -> TechNameAttributes | None:
    if not isinstance(code, str):
        return None
    match = _find_xs_call_arguments(
        _LOCALIZED_TECH_NAME_ARGUMENTS_RE,
        code,
    )
    if match is None:
        return None
    return TechNameAttributes(
        technology=int(match.group('technology')),
        source_player=int(match.group('source_player')),
    )


def generate_virtual_effect_function_name(random_length: int = 12) -> str:
    suffix = ''.join(
        secrets.choice(_RANDOM_NAME_ALPHABET)
        for _ in range(random_length)
    )
    return f'VE_{suffix}'


def create_unique_function_name(existing_names: set[str], random_length: int = 12) -> str:
    while True:
        function_name = generate_virtual_effect_function_name(random_length)
        if function_name not in existing_names:
            return function_name
