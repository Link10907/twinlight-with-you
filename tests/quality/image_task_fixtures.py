"""SYNTHETIC pixels and observations for task tests; NEVER real art provenance."""
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageOps
from quality_fixtures import design
from split_fixtures import person
from twinlight_core import portable, portable_images as jobs, style_selection
from twinlight_core.card_context import image_input
from twinlight_core.common import load, save
from twinlight_core.portable_layers import sha
from twinlight_core.lite import persona_digest
from twinlight_core.cardgen import DEPTHS

TOOL='SYNTHETIC fixture, NOT a real tool invocation'
NOTE='SYNTHETIC observed-result fixture only; not an actual image generation or art approval.'


def capabilities():
    return {'image':{'status':'available','context_isolation':'contextual_native_tool','canvas':[600,800]},
            'image_edit':{k:'available' for k in ('status','reference_binding','transparent_output')},
            'layer_processing':{'status':'available'},'files':{'status':'available'},
            'reviewer':{'mode':'self'},'browser':{'status':'unavailable'}}


def start(workspace,source=None,style='paper-craft-story'):
    source=source or workspace.parent/'person.json';save(source,person())
    portable.run(source,workspace,capabilities())
    value=image_input(design(style=style));value['version']=style_selection.REQUEST_VERSION
    style_selection.select(workspace,value)
    return source


def picture(path,role,size=(600,800),variant=0):
    im=Image.new('RGBA',size,(22+variant,33,44,255) if role in ('prototype','background') else (0,0,0,0))
    d=ImageDraw.Draw(im)
    if role in ('prototype','subject'):d.ellipse((size[0]*.3,size[1]*.12,size[0]*.7,size[1]*.75),fill=(110+variant,145,185,255))
    if role in ('prototype','effects'):d.ellipse((size[0]*.78,size[1]*.68,size[0]*.87,size[1]*.77),fill=(230,195+variant,120,255 if role=='prototype' else 240))
    im.save(path);return path


def reserve(workspace):
    task=jobs.next_task(workspace,load(workspace/'capabilities.json'))
    return task,jobs.reserve(workspace,task['task_id'],TOOL)


def accepted(workspace,source=None,variant=0):
    task,reserved=reserve(workspace);path=Path(reserved['output_directory'])/'return.png'
    if source:shutil.copyfile(source,path)
    else:picture(path,task['role'],tuple(task['canvas']),variant)
    result={'task_id':task['task_id'],'outcome':'success','disposition':'accepted','reason':NOTE,
            'review_method':'self','output':path.relative_to(workspace).as_posix()}
    jobs.record(workspace,result);return path


def layers(workspace):
    assets=jobs._accepted(jobs._read(workspace)[1]);out=workspace/'layers';out.mkdir(exist_ok=True)
    size=tuple(jobs._primary(assets['prototype'])['canvas'])
    for role in jobs.ROLES[1:]:shutil.copyfile(workspace/jobs._primary(assets[role])['file'],out/(role+'.png'))
    from prepare_card_layers import typography,font_path
    typography(person(),size,font_path(None)).save(out/'text.png')
    Image.new('RGBA',size).save(out/'spirit.png')
    with Image.open(out/'subject.png') as im:alpha=im.getchannel('A')
    edge=ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(5)),alpha.filter(ImageFilter.MinFilter(5)))
    ImageOps.invert(edge).convert('RGB').save(out/'lineart.png')
    save(out/'layers.json',{'schema_version':'1.0','persona_digest':persona_digest(person()),'art_status':'generated',
         'reference_consent':False,'depths':dict(DEPTHS),'assets':{r:r+'.png' for r in (*jobs.ROLES[1:],'text','spirit','lineart')},
         'notes':'SYNTHETIC test pixels, no real art approval or image provider invocation.'})
    return out/'layers.json'


def generation(workspace,manifest,method='native_layers'):
    a=jobs._accepted(jobs._read(workspace)[1])['prototype'];p=jobs._primary(a);m=load(manifest)
    g={'origin':'native_image_tool','tool':TOOL,'prototype_file':p['file'],'prototype_sha256':p['sha256'],
       'prototype_review':'self','prototype_verdict':'accept','prototype_observations':NOTE,'layer_method':method,
       'layers_sha256':{r:sha(manifest.parent/m['assets'][r]) for r in jobs.ROLES[1:]},
       'context_isolation':'contextual_native_tool','verdict':'accept','layer_observations':NOTE}
    if method=='assisted_layers':g['assembly_record_file']=(manifest.parent/'layer-process.json').relative_to(workspace).as_posix()
    save(workspace/'generation.json',g);return portable.generation_check(workspace/'generation.json',manifest)


def native(workspace):
    for _ in jobs.ROLES:accepted(workspace)
    manifest=layers(workspace);return manifest,generation(workspace,manifest)
