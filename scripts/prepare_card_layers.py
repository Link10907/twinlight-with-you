#!/usr/bin/env python3
"""Assemble untouched native images with separate typeset text and registered lineart."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twinlight_core.art import validate_layers
from twinlight_core.cardgen import card_spec, read_card_data
from twinlight_core.common import check, load, save
from twinlight_core.site import native_subject, open_card_image, ImageChops_safe
from twinlight_core.canvas_mapping import native_dimensions_allowed,mapping_for


def font_path(explicit: Path | None) -> Path:
    if explicit:
        check(explicit.is_file(), '找不到指定的字体')
        return explicit
    candidates = [
        '/System/Library/Fonts/Supplemental/Songti.ttc',
        '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/msyh.ttc',
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return Path(candidate)
    raise ValueError('需要中文字体：使用 --font 指定本机中文字体文件；主体与背景无需处理。')


def typography(data: dict, size: tuple[int, int], font: Path,
               composition: dict | None = None) -> Image.Image:
    w, h = size
    scale = w / 1080
    text = Image.new('RGBA', size)
    d = ImageDraw.Draw(text)
    gold = (237, 219, 171, 248)
    soft = (236, 229, 206, 242)
    footer_start, footer_end = .765, .961
    footer_width = .83
    footer_regions = [rect for rect in (composition or {}).get('text_safe_regions', [])
                      if rect[0] <= .35 and rect[2] >= .65 and rect[1] >= .6 and rect[3] >= .98]
    if footer_regions:
        region = min(footer_regions, key=lambda rect: rect[1])
        footer_width = min(footer_width, 2 * min(.5 - region[0], region[2] - .5))
        if region[1] > .76:
            footer_start = region[1] + .008
            footer_end = min(.977, region[3] - .02)
            check(footer_end - footer_start >= .10,
                  '底部文字空间不足以清楚排下当前文案；请调整构图或重新生成主体')
    footer_scale = (footer_end - footer_start) / (.961 - .765)

    def footer(value, y, n, color=soft):
        position = footer_start + (y - .765) * footer_scale
        center(value, position, round(n * min(1, footer_scale)), color, max_width=footer_width)

    def f(n):
        return ImageFont.truetype(str(font), max(1, round(n * scale)))

    def center(value, y, n, color=soft, max_width=.83):
        face = f(n)
        while d.textlength(value, font=face) > w * max_width and n > 14:
            n -= 1
            face = f(n)
        d.text((w / 2, y * h), value, font=face, anchor='mt', fill=color,
               stroke_width=max(1, round(scale)), stroke_fill=(15, 30, 30, 150))

    inset = round(18 * scale)
    d.rounded_rectangle((inset, inset, w-inset, h-inset), radius=round(24*scale),
                        outline=gold, width=max(1, round(2*scale)))
    d.rounded_rectangle((inset+9*scale, inset+9*scale, w-inset-9*scale, h-inset-9*scale),
                        radius=round(18*scale), outline=(211, 208, 159, 125), width=1)
    d.text((w*.055, h*.046), 'SSR', font=f(74), fill=gold,
           stroke_width=2, stroke_fill=(16, 28, 26, 180))
    author = data['summarizer']+' 眼中的你'
    d.text((w*.94, h*.05), author, font=f(23), anchor='rt', fill=soft,
           stroke_width=1, stroke_fill=(16, 28, 26, 180))
    # A transparent lower scrim belongs to text, never to the source images.
    scrim_start = max(.70, footer_start - .075)
    for y in range(round(h*scrim_start), h-inset):
        a = min(185, max(0, round((y/h-scrim_start)/(1-scrim_start)*185)))
        d.line((inset+2, y, w-inset-2, y), fill=(8, 24, 25, a))
    c = data['card']
    footer(c['title'], .765, 76, gold)
    footer(c['english_title'].upper(), .835, 25, gold)
    footer(' · '.join(c['keywords']), .877, 25)
    footer(c['tagline'], .916, 23)
    footer('T W I N L I G H T   ·   1 / 1', .961, 17, gold)
    return text


def prepare(data: dict, background: Path, subject: Path, effects: Path,
            out: Path, font: Path, *, composition: dict | None = None,
            prototype: Path | None = None, art_prompt: str | None = None, spirit: Path | None = None) -> dict:
    sub = native_subject(subject)
    bg, fx = open_card_image(background), open_card_image(effects)
    canvas = open_card_image(prototype).size if prototype else sub.size
    originals = {'background':bg,'subject':sub,'effects':fx}
    native_edit_roles=[]
    for role, im in originals.items():
        if im.size == canvas:continue
        check(prototype is not None and native_dimensions_allowed(im.size,canvas,native_edit=True),
              '图层尺寸差超过原生编辑允许的 1 像素取整范围；不能裁剪或移动修正')
        from twinlight_core.art_quality import checked_ref,read_json,sha256
        evidence=read_json(out/'art-evidence.json')
        entry=evidence.get('images',{}).get(role,{})
        source={'background':background,'subject':subject,'effects':effects}[role]
        check(entry.get('sha256')==sha256(source),'取整映射必须绑定已登记的原生编辑图层')
        call=read_json(checked_ref(out,entry.get('call')));request=call.get('request',{})
        check(request.get('operation')=='image_edit' and request.get('coordinate_policy')=='preserve_full_canvas'
              and request.get('canvas')==list(canvas) and call.get('response',{}).get('canvas')==list(im.size),
              '只有已登记的同原型原生编辑允许 1 像素显示采样')
        native_edit_roles.append(role)
    check(bg.getchannel('A').getextrema() == (255, 255), '背景必须完整且完全不透明')
    spec = card_spec(data, generated_at='2000-01-01T00:00:00Z', canvas=canvas, composition=composition, art_prompt=art_prompt)
    if composition and composition.get('source_prototype_sha256'):
        check(prototype is not None, '构图锁绑定了原型，请使用 --prototype 提供同一张参考图')
        check(hashlib.sha256(prototype.read_bytes()).hexdigest() == composition['source_prototype_sha256'],
              '构图锁对应另一张原型；请使用当前选定的原型')
    spirit_image = open_card_image(spirit) if spirit else None
    if spirit_image is not None:
        check(spirit_image.size == canvas, 'spirit 必须保留同一逻辑画布；不会裁切或移动')
    elif (out/'spirit.png').exists():
        check(open_card_image(out/'spirit.png').getchannel('A').getbbox() is None,
              '已有非空 spirit；请显式提供 --spirit，不能用空层覆盖')
    # Prepare text before modifying output files; an invalid layout must fail early.
    layout_report = None
    if art_prompt and art_prompt.lstrip().startswith('{'):
        from twinlight_core.art_quality import parse_json, validate_design
        from twinlight_core.art_typography import typeset
        design = validate_design(parse_json(art_prompt), spec['persona_digest'])
        text_image, layout_report = typeset(data, canvas, font, design['typography'], composition)
    else:
        text_image = typography(data, canvas, font, composition)
    out.mkdir(parents=True, exist_ok=True)
    # Copy files byte for byte. These are newly generated assets, not poster cutouts.
    paths = {}
    for role, source in [('background', background), ('subject', subject), ('effects', effects)]:
        target = out/(role+source.suffix.lower())
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        paths[role] = target.name
    if spirit:
        target = out/('spirit' + spirit.suffix.lower())
        if spirit.resolve() != target.resolve():
            shutil.copyfile(spirit, target)
        paths['spirit'] = target.name
    else:
        Image.new('RGBA', canvas).save(out/'spirit.png')
    text_image.save(out/'text.png')
    if layout_report is not None:
        save(out/'typography-report.json', layout_report)
        (out/'art-direction.json').write_text(art_prompt, encoding='utf-8')
    alpha = sub.getchannel('A')
    edge = ImageChops_safe(alpha.filter(ImageFilter.MaxFilter(5)), alpha.filter(ImageFilter.MinFilter(5)))
    ImageOps.invert(edge).convert('RGB').save(out/'lineart.png')
    manifest = spec['manifest_template']
    manifest['notes'] = 'Native independent layers assembled for this card; prototype is reference only. Visual review still required.'
    manifest['assets'].update(paths)
    mapping=mapping_for(canvas,originals,native_edit_roles)
    if mapping:manifest['canvas_mapping']=mapping
    save(out/'layers.json', manifest)
    save(out/'card-spec.json', spec)
    return validate_layers(out/'layers.json', spec['persona_digest'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', required=True, type=Path)
    p.add_argument('--background', required=True, type=Path)
    p.add_argument('--subject', required=True, type=Path)
    p.add_argument('--effects', required=True, type=Path)
    p.add_argument('--spirit', type=Path, help='Preserve an explicitly generated nonempty companion layer')
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--font', type=Path)
    p.add_argument('--prototype', type=Path)
    p.add_argument('--composition', type=Path)
    p.add_argument('--art-prompt-file', type=Path)
    a = p.parse_args()
    data = read_card_data(a.data)
    result = prepare(data, a.background, a.subject, a.effects, a.out, font_path(a.font),
                     composition=load(a.composition) if a.composition else None, prototype=a.prototype,
                     art_prompt=a.art_prompt_file.read_text(encoding='utf-8') if a.art_prompt_file else None, spirit=a.spirit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
