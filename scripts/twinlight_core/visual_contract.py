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
DEFAULT_STYLE = 'twinlight-collector'
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
    if cat.get('version') != 'style-catalog-1' or not cat.get('styles'):
        raise VisualContractError('style_catalog', 'Register at least one versioned style')
    ids = [s['id'] for s in cat['styles']]
    if len(set(ids)) != len(ids): raise VisualContractError('style_catalog', 'Style identifiers must be unique')
    if cat.get('default_style') not in ids:
        raise VisualContractError('style_catalog', 'The default style must be installed')
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


def style_for(id: str | None = None, version: str | None = None) -> dict:
    if id is None:
        id = _json(STYLE_DIR / 'catalog.json')['default_style']
    for style in catalog():
        if style['id'] == id:
            if version is not None and style['version'] != version:
                raise VisualContractError('style_version', 'Selected style version is not installed; do not silently change it')
            return style
    raise VisualContractError('style_unknown', 'Select an installed style_id, not a free-form style label')


def default_style() -> dict:
    """One installed visual family; never a default person or animal."""
    return style_for()


def style_references(style: dict) -> list[dict]:
    """Read privacy-scoped, byte-bound examples. These are never output layers."""
    if not style.get('reference_manifest'):
        return []
    manifest_path = (ROOT / style['reference_manifest']).resolve()
    if not manifest_path.is_relative_to((ROOT / 'assets/art-references').resolve()):
        raise VisualContractError('style_reference_path', 'Style references must stay in the bundled reference library')
    manifest = _json(manifest_path)
    if (manifest.get('version') != 'art-reference-1' or manifest.get('style_id') != style['id']
            or manifest.get('style_version') != style['version'] or manifest.get('usage') != 'style_only'
            or manifest.get('no_persona') is not True or manifest.get('no_subject_copy') is not True):
        raise VisualContractError('style_reference_scope', 'The reference must be explicitly fictional, style-only and not a subject-copy instruction')
    refs = manifest.get('references')
    if not isinstance(refs, list) or not refs or len(refs) > 3:
        raise VisualContractError('style_reference_missing', 'The selected style needs its bundled visible reference images')
    result = []
    for ref in refs:
        path = (manifest_path.parent / ref['file']).resolve()
        if (not path.is_relative_to(manifest_path.parent) or not path.is_file()
                or ref.get('purpose') != 'style_only' or sha256(path) != ref.get('sha256')):
            raise VisualContractError('style_reference_hash', 'A bundled style reference is missing or changed')
        result.append({'file': str(path), 'sha256': ref['sha256'], 'purpose': 'style_only'})
    return result


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
    style_references(style_for(design['style']['id'], design['style']['version']))
    if design['style']['id'] == DEFAULT_STYLE and design['typography'].get('layout') != 'collector':
        raise VisualContractError('collector_typography', 'Use the collector typography profile from the selected style; do not silently fall back to compact lettering')
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
    if style.get('geometry'):
        lines.append('典藏卡共同几何约束：' + json.dumps(style['geometry'], ensure_ascii=False))
    if style.get('reference_manifest') and role == 'prototype':
        lines.append('工具同时提供的 style_only 图像是必须查看的画风与完成度基准：只借鉴绘制品质、材质、光照、深度和主次关系。不得复制参考人物、动物、身份、场景、道具或任何参考像素作为本次输出。')
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
    validate_design(design)
    w,h = canvas
    if type(w) is not int or type(h) is not int or min(w,h) < 256 or w*h>16_000_000 or abs(w/h-.75)>=.01:
        raise VisualContractError('canvas', 'Use one actual native 3:4 canvas, without cropping or resampling')
    tasks = {
      'prototype':'只生成一张无字原型插画，不生成网页、导航、面板、屏幕截图或卡片展示场景。一个主体、一个清楚动作，至多一个主要道具。',
      'background':'原生编辑 Image1：删除原图中的主体及其接触道具，同时删除下文指定归属 effects 的全部独立近景元素。保留原有中远景位置、透视与光照，只在删除区域补绘合理连续的环境。输出完整不透明空场景；不得留下主体、替身、残影、手持物，也不得重复保留 effects 前景。',
      'subject':'原生编辑 Image1：只保留原图中的主体及其接触道具，保持所有现有可见细节的原位置、原尺度、原朝向和原光照。移除全部中远景和独立近景，其他区域改为真实 alpha 透明。若指定前景遮住少量衣料，只在该遮挡位置补全同一衣料。不要重新生成角色立绘、缩放至填满画布或把人物居中；头顶到上缘、道具到左右边缘的距离必须与原图相同。',
      'effects':'原生编辑 Image1：仅保留下文指定的独立近景元素，严格保持每块元素的原位置、原大小、原景深与原遮挡轮廓，其余整个画布改为真实 alpha 透明。不得保留主体、接触道具或中远景，也不得把前景重新摆放成装饰边框或覆盖满屏。',
      'spirit':'本简洁构图不设置第二主体；此任务不调用图像模型，由程序创建同尺寸全透明层。'}
    if role not in tasks: raise VisualContractError('layer_role', 'Unsupported image role')
    if role == 'prototype':
        lines = [visual_brief(design, role), '本次任务：' + tasks[role]]
    else:
        style = style_for(design['style']['id'], design['style']['version'])
        lines = ['唯一输入 Image1 是当前已审查原型，也是本次 composition 编辑画布与唯一坐标权威。执行图像工具原生编辑，不是参考图再创作；没有其他 style_only 图，也不要追加品牌示范图或用户照片。',
                 '本次任务：' + tasks[role],
                 '沿用 Image1 已审查通过的' + style['name'] + '精绘风格、表面材质与光照，不重新设计人物、场景或配色。',
                 '典藏卡共同几何约束以 Image1 的实际画布为准：保留完整画幅、视野、位置、大小、透视和透明空白，禁止自动紧边裁切、缩放放大、居中、重新取景或补出画布外的身体；不得重新设计或换姿势。',
                 '指定 effects 独立前景（本层只按上述保留或移除任务处理）：' + '；'.join(design['scene']['foreground'])]
    lines.append(f'全画布 {w}×{h}，竖版 3:4；必须与 Image1 相同原生像素尺寸，不能靠之后裁切、缩放或平移修正。' if role != 'prototype' else f'全画布 {w}×{h}，竖版 3:4；不得自动裁切、缩放或重摆主体。')
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
    result = {'id':s['id'],'version':s['version'],'sha256':s['sha256']}
    refs = style_references(s)
    if refs:
        result['reference_sha256'] = [r['sha256'] for r in refs]
    return result


def review_checks(design: dict, stage: str, base: tuple[str,...]) -> tuple[str,...]:
    if design.get('version') != VERSION: return base
    extras = {'prototype':('concrete_subject','style_fidelity','simple_composition'),
              'composite':('style_fidelity','single_subject'),
              'final':('style_fidelity','fixed_text','touch_keyboard_reduced_motion')}
    collector = ('visual_hierarchy','material_finish','spatial_depth','reference_quality_parity') if design['style']['id'] == DEFAULT_STYLE and stage in ('prototype','composite','final') else ()
    return tuple(dict.fromkeys((*base,*extras.get(stage,()),*collector)))
