"""Versioned art language + explicit subject + simple scene + role-specific drawing.

This is a prompt contract, not an image generator, an identity classifier or an
art judge. It never imports personal card keywords or mutates narrative data.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
STYLE_DIR = ROOT / 'assets/art-styles'
SCHEMA = ROOT / 'schemas/art-direction-v2.schema.json'
VERSION = 'art-direction-2'
ROLES = ('prototype', 'background', 'subject', 'effects', 'spirit')
# Reject known abstract-only labels, not sentences that describe visible actions.
ABSTRACT = frozenset(('拆解', '验证', '构建', '迭代', '共创', '成长', '探索', '可能性',
                     '系统织星者', '工程创作者气质', '文艺气质', 'curiosity', 'growth',
                     'iteration', 'co-creation', 'builder', 'potential', 'exploration'))
PLACEHOLDERS = re.compile(r'\{\{|\}\}|\$\{|<[^>]{1,80}>|待填写|待补充|自行发挥|三选一|二选一|TODO|TBD', re.I)
PART_NAMES = {'hair':'发型','face':'面部','body':'体态','fur':'毛发','feathers':'羽毛',
              'scales':'鳞片','ears':'耳朵','eyes':'眼睛','horns':'角','surface':'表面材质',
              'shape':'形状','color':'颜色'}
PRESENTATION = {'male':'男性呈现','female':'女性呈现','androgynous':'中性呈现',
                'unspecified':'不强调性别','not_applicable':'性别不适用'}
KINDS = {'human':'人类原创角色','animal':'动物角色','anthropomorphic':'拟人动物角色','object':'物件主体'}


class VisualContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> Any:
    if not path.is_file() or path.stat().st_size > 256 * 1024:
        raise VisualContractError('resource_missing', 'Missing or oversized visual resource: ' + path.name)
    def pairs(values):
        out = {}
        for k, v in values:
            if k in out: raise VisualContractError('duplicate_key', 'Duplicate visual field: ' + k)
            out[k] = v
        return out
    def bad(value):
        raise VisualContractError('nonfinite_number', 'Non-finite value: ' + value)
    result = json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs, parse_constant=bad)
    if not isinstance(result, dict):
        raise VisualContractError('object_required', 'Visual resources and records must be JSON objects')
    return result


def catalog() -> list[dict]:
    cat = _json(STYLE_DIR / 'catalog.json')
    if cat.get('version') != 'style-catalog-1' or len(cat.get('styles', [])) != 4:
        raise VisualContractError('style_catalog', 'Exactly four versioned styles must be registered')
    ids = [s['id'] for s in cat['styles']]
    if len(set(ids)) != 4: raise VisualContractError('style_catalog', 'Style identifiers must be unique')
    result = []
    for entry in cat['styles']:
        id = entry['id']
        if not re.fullmatch(r'[a-z][a-z0-9-]{2,60}', id) or entry['file'] != id + '.json':
            raise VisualContractError('style_path', 'Unsafe style catalog entry')
        path = STYLE_DIR / entry['file']
        if not path.resolve().is_relative_to(STYLE_DIR.resolve()):
            raise VisualContractError('style_path', 'Style file leaves the style library')
        style = _json(path)
        if style.get('id') != id or not re.fullmatch(r'\d+\.\d+\.\d+', str(style.get('version', ''))):
            raise VisualContractError('style_version', 'Style identifier/version mismatch')
        for field in ('name', 'visual_language', 'materials_and_light', 'palette'):
            if not isinstance(style.get(field), str) or not style[field].strip():
                raise VisualContractError('style_content', 'Style needs concrete ' + field)
        for field in ('keep', 'avoid'):
            if not isinstance(style.get(field), list) or not all(isinstance(x, str) and x.strip() for x in style[field]):
                raise VisualContractError('style_content', 'Invalid style rules: ' + field)
        result.append({**style, 'sha256':sha256(path), 'path':str(path.resolve())})
    return result


def style_for(id: str, version: str | None = None) -> dict:
    for style in catalog():
        if style['id'] == id:
            if version is not None and style['version'] != version:
                raise VisualContractError('style_version', 'Selected style version is not installed; do not silently change it')
            return style
    raise VisualContractError('style_unknown', 'Select an installed style_id, not a free-form style label')


def _visible(value: str, field: str) -> None:
    if PLACEHOLDERS.search(value):
        raise VisualContractError('unresolved_subject', field + ' contains an unresolved choice or placeholder')
    fragments = [p.strip().casefold() for p in re.split(r'[,，、/|·;；\s]+', value) if p.strip()]
    if fragments and all(f in ABSTRACT for f in fragments):
        raise VisualContractError('abstract_visual_term', field + ' must describe something visible, not identity keywords')


def validate_design(design: dict, persona: str | None = None) -> dict:
    errors = sorted(Draft202012Validator(_json(SCHEMA)).iter_errors(design), key=lambda e: str(list(e.path)))
    if errors:
        path = '.'.join(map(str, errors[0].absolute_path)) or '$'
        raise VisualContractError('visual_schema', path + ': ' + errors[0].message[:250])
    if persona is not None and design['persona_digest'] != persona:
        raise VisualContractError('wrong_persona', 'This visual subject belongs to a different person')
    style_for(design['style']['id'], design['style']['version'])
    subject = design['subject']
    if subject['kind'] == 'human' and subject['species'].casefold() not in ('human', '人', '人类', '人類'):
        raise VisualContractError('subject_species', 'Human subject must explicitly use species=人类 or human')
    if subject['kind'] in ('animal', 'anthropomorphic') and subject['species'].casefold() in ('animal','动物','動物','human','人类','人類'):
        raise VisualContractError('subject_species', 'Name the actual animal species, not just "animal"')
    if subject['kind'] == 'object' and subject['gender_presentation'] != 'not_applicable':
        raise VisualContractError('object_gender', 'An object must not be assigned a human gender by default')
    if subject['kind'] != 'object' and subject['gender_presentation'] == 'not_applicable':
        raise VisualContractError('subject_presentation', 'Use an explicit presentation or unspecified for a living subject')
    if subject['kind'] == 'object' and subject['main_prop'] is not None:
        raise VisualContractError('prop_budget', 'The object is already the sole main prop')
    parts = [t['part'] for t in subject['appearance']]
    if len(set(parts)) != len(parts):
        raise VisualContractError('duplicate_trait', 'Use one resolved description per appearance feature')
    for field in ('species','age_impression','clothing','expression','pose'):
        _visible(subject[field], 'subject.' + field)
    for trait in subject['appearance']:
        _visible(trait['description'], 'subject.appearance.' + trait['part'])
    if subject['main_prop'] is not None:
        _visible(subject['main_prop'], 'subject.main_prop')
        if re.search(r'[/|]|三选一|二选一|或者|(?:\bor\b)|[、;；]', subject['main_prop'], re.I):
            raise VisualContractError('prop_budget', 'Resolve exactly one main prop; do not supply a list of alternatives')
    for field in ('setting','lighting','composition'):
        _visible(design['scene'][field], 'scene.' + field)
    for item in design['scene']['foreground']:
        _visible(item, 'scene.foreground')
    if bool(design['references']) != (design['reference_basis'] == 'visible_images'):
        raise VisualContractError('reference_basis', 'Do not claim an unseen image as a reference')
    if subject['representation'] == 'user_reference' and not (design['reference_consent'] is True and design['references']):
        raise VisualContractError('likeness_reference', 'A likeness requires an actual supplied image and consent; otherwise use original_concept')
    return design


def presentation_for(subject: dict) -> str:
    value = subject['gender_presentation']
    if subject['kind'] == 'animal' and value in ('male', 'female'):
        return '雄性' if value == 'male' else '雌性'
    return PRESENTATION[value]


def visual_keywords(design: dict) -> list[str]:
    """Deterministic visible descriptors, never card.keywords or selection_basis."""
    validate_design(design)
    s = design['subject']
    return [s['species'], presentation_for(s), s['age_impression'],
            *(x['description'] for x in s['appearance']), s['clothing'], s['expression'], s['pose'],
            *([s['main_prop']] if s['main_prop'] else [])]


def subject_prompt(design: dict) -> str:
    validate_design(design)
    s = design['subject']
    lines = ['主体：' + KINDS[s['kind']] + '，物种：' + s['species'] + '；' + presentation_for(s) + '；' + s['age_impression'] + '。']
    lines += [PART_NAMES[t['part']] + '：' + t['description'] + '。' for t in s['appearance']]
    lines += ['服装或覆盖物：' + s['clothing'] + '。', '神情或主要结构：' + s['expression'] + '。', '唯一动作与姿态：' + s['pose'] + '。']
    lines.append('唯一主要道具：' + s['main_prop'] + '；与主体接触的道具、手、衣料保留在同一层。' if s['main_prop'] else '不添加手持物、宠物或第二主体。')
    if s['representation'] == 'original_concept': lines.append('这是原创概念形象，不声称复原本人的真实长相。')
    return '\n'.join(lines)


def visual_brief(design: dict, role: str = 'prototype') -> str:
    """Background/effects never receive hair, species, props or personal keywords."""
    validate_design(design)
    if role not in ROLES: raise VisualContractError('layer_role', 'Unsupported image role')
    style = style_for(design['style']['id'], design['style']['version'])
    scene = design['scene']
    lines = ['固定画风：' + style['name'] + '。' + style['visual_language'],
             '材质与绘画光感：' + style['materials_and_light'], '固定配色语言：' + style['palette'],
             '本次光线：' + scene['lighting'], '共同构图与文字留白：' + scene['composition']]
    if role in ('prototype','subject'):
        lines.append(subject_prompt(design))
    if role in ('prototype','background'):
        lines.append('场景：' + scene['setting'])
    if role in ('prototype','effects'):
        lines.append('少量前景：' + '；'.join(scene['foreground']))
    lines.append('风格保留：' + '；'.join(style['keep']))
    lines.append('风格排除：' + '；'.join(style['avoid']))
    # Preferences are review inputs. Do not inject untyped personal text into background calls.
    if role == 'prototype':
        if design['preferences']['keep']: lines.append('本次视觉偏好：' + '；'.join(design['preferences']['keep']))
        if design['preferences']['avoid']: lines.append('本次否决方向：' + '；'.join(design['preferences']['avoid']))
    return '\n'.join(lines)


def layer_prompt(design: dict, role: str, canvas: tuple[int, int], composition: dict | None = None) -> str:
    w,h = canvas
    if type(w) is not int or type(h) is not int or min(w,h) < 256 or w*h>16_000_000 or abs(w/h-.75)>=.01:
        raise VisualContractError('canvas', 'Use one actual native 3:4 canvas, without cropping or resampling')
    tasks = {
      'prototype':'只生成一张无字原型插画，不生成网页、导航、面板、屏幕截图或卡片展示场景。一个主体、一个清楚动作，至多一个主要道具。',
      'background':'只生成完整不透明空场景，补齐原型中被遮挡的环境；不画任何主体、替身、残影、面孔或手持物。',
      'subject':'只生成参考原型中的完整主体及其接触道具，不画背景或独立前景。保持原型的朝向、大小、位置、姿态和光照。',
      'effects':'只生成指定的少量近景元素，避开主要焦点和文字区；不画主体、手持物、场景或第二张海报。',
      'spirit':'本简洁构图不设置第二主体；此任务不调用图像模型，由程序创建同尺寸全透明层。'}
    if role not in tasks: raise VisualContractError('layer_role', 'Unsupported image role')
    lines = [visual_brief(design, role), '本次任务：' + tasks[role], f'全画布 {w}×{h}，竖版 3:4；不得自动裁切、缩放或重摆主体。']
    if role != 'prototype': lines.append('使用同一张已审查原型作为真实图像参考，沿用共同坐标；不是只在文字里提及参考图。')
    if role in ('subject','effects'): lines.append('启用工具真实 alpha 透明输出；主体外完全透明，不画棋盘、纯色幕布或假透明。')
    if role in ('prototype','background'): lines.append('输出完全不透明的场景 PNG。')
    if composition:
        for key in ('subject_bounds','subject_center_region','text_safe_regions'):
            if key in composition: lines.append(key + '=' + json.dumps(composition[key],ensure_ascii=False))
    lines.append('不要生成文字、SSR、签名、边框、网页 UI 或预烘焙镭射；文字由程序排版，闪光由渲染器产生。')
    return '\n'.join(lines)


def style_binding(design: dict) -> dict:
    validate_design(design)
    s = style_for(design['style']['id'], design['style']['version'])
    return {'id':s['id'],'version':s['version'],'sha256':s['sha256']}


def review_checks(design: dict, stage: str, base: tuple[str,...]) -> tuple[str,...]:
    if design.get('version') != VERSION: return base
    extras = {'prototype':('concrete_subject','style_fidelity','simple_composition'),
              'composite':('style_fidelity','single_subject'),
              'final':('style_fidelity','fixed_text','touch_keyboard_reduced_motion')}
    return tuple(dict.fromkeys((*base,*extras.get(stage,()))))
