"""Small, deterministic image/review inputs. No narrative or site imports.

Field checks prevent common accidental task leakage, not arbitrary semantic
prompt injection. Actual images still require independent visual inspection.
"""
from __future__ import annotations
import copy
import json
import re
from pathlib import Path
from jsonschema import Draft202012Validator
from .visual_contract import ROOT, VisualContractError, _json, sha256, style_for, style_references, validate_design, validate_subject

VERSION = 'card-image-input-1'
SUBJECT_KEYS = ('kind','species','gender_presentation','age_impression','appearance',
                'clothing','expression','pose','main_prop','representation')
MAX_PROMPT = {'prototype':2200, 'background':1200, 'subject':1200, 'effects':1200, 'spirit':160}
# Reject untyped page instructions rather than quietly deleting pieces of intent.
OFF_TOPIC = re.compile(r'https?://|file://|```|<\s*/?\s*[a-z][^>]*>|\b(?:html|css|javascript|iframe|system\s*:|assistant\s*:)\b|'
                       r'#(?:galaxy|card|finale)\b|首页|主页|网页|网站|官网|导航栏|终章|交融|全站|栏目|落地页|'
                       r'聊天记录|系统提示|忽略.{0,8}(?:指令|要求)|ignore\s+(?:all\s+)?(?:previous|instructions)', re.I)


def _error(code: str, message: str):
    raise VisualContractError(code, message)


def visible_text(text: str, field: str, limit: int=240) -> str:
    if not isinstance(text,str) or not text.strip() or len(text)>limit:
        _error('card_text_budget', field+': use a short concrete visual description; do not truncate silently')
    if OFF_TOPIC.search(text):
        _error('card_context_leak', field+': page/history/instruction text is not a drawing attribute')
    return text.strip()


def preset(style: dict) -> dict:
    style_for(style['id'],style['version'])
    table=_json(ROOT/'assets/art-styles/image-presets.json')
    if table.get('version')!='card-image-presets-1' or style['id'] not in table.get('presets',{}):
        _error('image_preset_missing','The selected style has no maintained drawing-only preset')
    item=table['presets'][style['id']]
    if set(item)!= {'drawing','materials','palette'}:
        _error('image_preset_fields','Image presets contain only drawing, materials and palette')
    for key,value in item.items(): visible_text(value,'preset.'+key,240)
    return copy.deepcopy(item)


def validate_input(value: dict) -> dict:
    errors=sorted(Draft202012Validator(_json(ROOT/'schemas/card-image-input.schema.json')).iter_errors(value),key=lambda e:str(list(e.path)))
    if errors:
        e=errors[0];_error('card_image_schema',('.'.join(map(str,e.path)) or '$')+': '+e.message[:200])
    def walk(node,path):
        if isinstance(node,dict):
            for key,item in node.items():walk(item,path+'.'+key)
        elif isinstance(node,list):
            for i,item in enumerate(node):walk(item,path+'.'+str(i))
        elif isinstance(node,str):visible_text(node,path,240)
    validate_subject(value['subject'])
    walk(value['subject'],'subject');walk(value['scene'],'scene');preset(value['style'])
    if len(json.dumps(value,ensure_ascii=False,separators=(',',':')))>2800:
        _error('card_input_budget','Drawing input exceeds 2800 characters; simplify concrete features instead of truncating')
    return value


def image_input(design: dict) -> dict:
    validate_design(design)
    # No title, keywords, selection_basis, preferences, user name or persona hash.
    value={'version':VERSION,'style':copy.deepcopy(design['style']),
           'subject':{key:copy.deepcopy(design['subject'][key]) for key in SUBJECT_KEYS},
           'scene':{key:copy.deepcopy(design['scene'][key]) for key in ('setting','lighting','composition','foreground')}}
    return validate_input(value)


def expand_input(value: dict, persona: str) -> dict:
    """Attach host-only binding/typography. Never send this envelope to the model."""
    validate_input(value)
    style=style_for(value['style']['id'],value['style']['version'])
    design={'version':'art-direction-2','persona_digest':persona,'style':copy.deepcopy(value['style']),
            'subject':{**copy.deepcopy(value['subject']),'selection_basis':'来自本次冻结的具体形象说明，不包含人物经历或页面叙事。'},
            'scene':copy.deepcopy(value['scene']),
            'preferences':{'keep':[],'avoid':[],'basis':'本次仅依照冻结的形象与选定绘画风格。','rejected_asset_sha256':[]},
            'selection_reason':'本次使用已确定的单主体、单动作和场景，不另行推断人物经历。',
            'reference_basis':'text_only','references':[],'reference_consent':False,
            'typography':copy.deepcopy(style.get('typography_default',style_for()['typography_default']))}
    if value['subject']['representation']=='user_reference':
        _error('likeness_reference','A likeness needs explicitly staged consented reference images in the private design; use the documented reference path')
    return validate_design(design,persona)


def render_prompt(value: dict, role: str, canvas: tuple[int,int], *, repair: str|None=None) -> str:
    validate_input(value)
    w,h=canvas
    if any(type(n) is not int for n in (w,h)) or min(w,h)<256 or w*h>16000000 or abs(w/h-.75)>=.01:
        _error('canvas','Use one native 3:4 canvas, without cropping or resampling')
    if role not in MAX_PROMPT:_error('layer_role','Unsupported image role')
    s=value['subject'];scene=value['scene'];sty=preset(value['style'])
    gender={'male':'男性','female':'女性','androgynous':'中性呈现','unspecified':'不强调性别','not_applicable':'物件'}[s['gender_presentation']]
    prop=s['main_prop'] or '无接触道具'
    fg='；'.join(scene['foreground'])
    if role=='prototype':
        parts={'hair':'头发','face':'面部','body':'体型','ears':'耳朵','eyes':'眼睛','surface':'表面','shape':'形状','color':'颜色'}
        features='；'.join(parts[x['part']]+'：'+x['description'] for x in s['appearance'])
        kind={'human':'人类角色','object':'非动物器物'}[s['kind']]
        ref_count=len(style_references(style_for(value['style']['id'],value['style']['version'])))
        refs=(f'按附件顺序，前{ref_count}张仅借画风完成度，不借角色、场景或道具。' if ref_count else '无画风图片，以选定绘画语言为准。')
        if s['representation']=='user_reference':refs+='其余附件仅为授权人物外貌参考。'
        refs+='形象、动作和环境以文字为准。'
        lines=[f'仅画一幅无字连续插画，竖版 {w}×{h}；一个主体、一个动作。',
               f'主体：一个{kind}，{s["species"]}，{gender}，{s["age_impression"]}。',
               '特征：'+features+'。','服装或表面：'+s['clothing']+'。',
               '神情或结构：'+s['expression']+'。','动作：'+s['pose']+'；主要道具：'+prop+'。',
               '画法：'+sty['drawing']+'\n材质与光感：'+sty['materials']+'\n配色：'+sty['palette'],
               '环境：'+scene['setting']+'。光线：'+scene['lighting']+'。',
               '少量独立近景：'+fg+'。构图：'+scene['composition']+'。',
               '主体是视觉焦点；环境可以精细，但必须与指定场景一致。脸、手和关键动作避开底部28%，上下排字区保持连续环境与低对比。',
               refs]
        if s['representation']=='original_concept':lines.append('原创角色，不复原本人长相；不添加同伴或额外道具。')
        else:lines.append('人物参考仅用于授权外貌；场景与动作以文字为准。')
        lines.append('不使用动物、拟人动物、兽耳兽尾或动物同伴；参考图中的动物不进入画面。')
        lines.append('不透明 PNG；不画文字、边框、界面拼贴或固定反光。')
    elif role=='spirit':
        lines=['不调用生图；由程序建立同画布全透明空层，不添加第二主体。']
    else:
        ownership={
            'background':f'移除主角及接触道具（{prop}），移除近景（{fg}）；原位补全被遮挡的中远景。不得留人影或重复近景。输出完全不透明 PNG。',
            'subject':f'只保留主角及接触道具（{prop}）；移除环境与近景（{fg}）。仅补全原被近景遮挡的少量主体，其他区域原生 alpha 透明。',
            'effects':f'只保留指定近景（{fg}）的原位置与轮廓；移除主角、接触道具和中远景，其余区域原生 alpha 透明。不要新造装饰。'}
        lines=[f'仅原生编辑 Image1，输出一张 {role} 图层，画布 {w}×{h}。',
               'Image1 是唯一已审查原型；保持原构图、姿态、位置、大小、材质和光线，不重新创作。',ownership[role],
               '保留完整画布和透明边距，不裁切、缩放、居中或移动。透明层不画棋盘或底色。不画文字、边框或固定反光。']
    text='\n'.join(lines)
    if repair:
        text+='\n本轮仅修：'+visible_text(repair,'repair',240)
    if len(text)>MAX_PROMPT[role]:_error('card_prompt_budget','Prompt exceeds '+str(MAX_PROMPT[role])+' characters; shorten the visual fields')
    return text


def validate_job(plan: dict, root: Path, job: dict) -> None:
    """Recompute final payload at dispatch: a re-hashed handwritten prompt is not canonical."""
    from .art_quality import checked_ref, read_json
    spec=read_json(checked_ref(root,plan.get('image_input')))
    if spec!=image_input(read_json(checked_ref(root,plan['design']))):
        _error('card_input_changed','Drawing-only input no longer matches the private design')
    expected=render_prompt(spec,job['role'],tuple(plan['canvas']),repair=job.get('repair_instruction'))+'\n'
    if checked_ref(root,job['prompt']).read_text(encoding='utf-8')!=expected:
        _error('card_prompt_changed','Use the canonical short prompt; do not append history, manuals or ad-hoc instructions')
    # References are a whitelist too; a valid prompt cannot excuse extra images.
    design=read_json(checked_ref(root,plan['design']))
    refs=job.get('reference_images',[])
    if job['role']=='prototype':
        from .visual_contract import style_references
        expected_refs=[(r['sha256'],'style_only') for r in style_references(style_for(design['style']['id'],design['style']['version']))]
        expected_refs += [(r['sha256'],'user_reference') for r in design['references']]
        if [(r.get('sha256'),r.get('purpose')) for r in refs]!=expected_refs:
            _error('card_reference_scope','Prototype accepts only the selected style anchors and consented likeness references')
        if job.get('operation')!='image_generation' or job.get('transparent') is not False:
            _error('card_operation','Prototype must generate one opaque unlettered image')
    else:
        expected_ref={**(plan.get('prototype') or {}),'purpose':'composition'}
        if refs!=[expected_ref] or job.get('edit_base')!=plan.get('prototype') or job.get('operation')!='image_edit':
            _error('card_reference_scope','Native edits accept only the approved prototype, not extra style or site images')
        if job.get('transparent') is not (job['role'] in ('subject','effects')):
            _error('card_operation','Native layer transparency differs from its role')
    from PIL import Image
    for ref in refs:
        path=checked_ref(root,ref)
        with Image.open(path) as im:
            if im.format not in ('PNG','JPEG','WEBP'):_error('card_reference_format','References must be actual images')
            im.verify()
