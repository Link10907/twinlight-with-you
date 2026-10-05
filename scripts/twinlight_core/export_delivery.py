"""Export only the actual hash-bound public delivery; never silently select base HTML."""
from __future__ import annotations
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

REQUIRED = {'html':('html',), 'card':('card_front','card_preview','card_pack'),
            'both':('html_with_card','card_front','card_preview','card_pack')}
NAMES = {'html':'Twinlight.html','html_with_card':'Twinlight.html','card_front':'card-front.png',
         'card_preview':'card-preview.html','card_pack':'card-pack.json'}


def _load(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > 4*1024*1024:
        raise ValueError('Missing or oversized public report: '+path.name)
    def pairs(values):
        out={}
        for k,v in values:
            if k in out: raise ValueError('Duplicate report field: '+k)
            out[k]=v
        return out
    value=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=pairs)
    if not isinstance(value,dict): raise ValueError('Report must be an object')
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(workspace: Path, destination: Path) -> dict:
    workspace,destination=Path(workspace).resolve(),Path(destination).resolve()
    run=_load(workspace/'run-report.json');receipt=_load(workspace/'delivery-report.json')
    mode=run.get('mode');required=REQUIRED.get(mode)
    if required is None or receipt.get('mode')!=mode: raise ValueError('Invalid or inconsistent requested mode')
    if not (run.get('complete') is True and receipt.get('complete') is True
            and run.get('status')==receipt.get('status')=='files_ready'
            and run.get('dynamic_verified') is True and receipt.get('dynamic_verified') is True):
        raise ValueError('The public run is incomplete. Preserve successful/candidate modules, but do not export them as a complete native-card delivery.')
    if mode=='both' and not (run.get('embedded_card_verified') is True and receipt.get('embedded_card_verified') is True):
        raise ValueError('Both-mode export requires verified native card bytes in the final HTML')
    if receipt.get('draft') is not True or receipt.get('share_allowed') is not False:
        raise ValueError('Default delivery exports are private unconfirmed drafts, not publication permission')
    expected_primary=run.get('outputs',{}).get({'html':'html','card':'card_preview','both':'html_with_card'}[mode])
    if not expected_primary or run.get('primary_output')!=expected_primary or receipt.get('primary_output')!=expected_primary:
        raise ValueError('Primary output does not match the requested mode; base HTML cannot replace integrated HTML')
    planned=[]
    for key in required:
        source_value=run.get('outputs',{}).get(key)
        if not isinstance(source_value,str): raise ValueError('Missing delivery output: '+key)
        source=Path(source_value).resolve()
        if not source.is_relative_to(workspace) or not source.is_file():
            raise ValueError('Output is missing or leaves this private workspace: '+key)
        if source.stat().st_size>128*1024*1024: raise ValueError('Output exceeds export size limit: '+key)
        if _sha(source)!=receipt.get('outputs_sha256',{}).get(key):
            raise ValueError('Output changed after public validation: '+key)
        planned.append((key,source,_sha(source)))
    if destination==workspace or workspace.is_relative_to(destination) or destination.is_relative_to(workspace):
        raise ValueError('Use a separate export directory, not the run workspace or its parent')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Export destination must be new or empty; never overwrite another delivery')
    destination.mkdir(parents=True,exist_ok=True)
    created=[]
    try:
        for key,source,fingerprint in planned:
            target=destination/NAMES[key];shutil.copyfile(source,target);created.append(target)
            if _sha(target)!=fingerprint or _sha(source)!=fingerprint:
                raise ValueError('Output changed during export: '+key)
        status=run.get('host_preview',{}).get('status','not_tested')
        note=('Twinlight 私人草稿\n\nTwinlight.html 是已内嵌本次闪卡的单文件（仅 HTML 模式除外）。\n'
              'card-preview.html 是同一张原生分层卡的独立预览。\n'
              '在现代浏览器打开 HTML；不需要安装 Node、Python 或上传个人资料。\n'
              f'聊天宿主的直接预览状态：{status}。本地浏览器检查不能证明聊天窗口允许执行脚本。\n'
              '本包不含字体文件、原始聊天、原型评审或工具响应。不要未经本人审阅自动公开。\n')
        (destination/'READ-ME.txt').write_text(note,encoding='utf-8');created.append(destination/'READ-ME.txt')
        result={'version':'delivery-export-1','mode':mode,'complete':True,'draft':True,'share_allowed':False,
                'host_preview':run.get('host_preview',{'status':'not_tested'}),
                'in_chat_preview_verified':run.get('in_chat_preview_verified') is True,
                'files':{key:{'file':NAMES[key],'sha256':fingerprint} for key,_,fingerprint in planned},
                'primary_file':NAMES[{'html':'html','card':'card_preview','both':'html_with_card'}[mode]],
                'scope':'Export of existing current public-run outputs; not new image generation or new browser validation.'}
        (destination/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        created.append(destination/'delivery.json')
        pack=destination/'Twinlight-delivery.zip'
        with zipfile.ZipFile(pack,'w',zipfile.ZIP_DEFLATED) as archive:
            for file in created: archive.write(file,file.name)
        result['archive']=str(pack);result['output_directory']=str(destination)
        return result
    except Exception:
        for file in created: file.unlink(missing_ok=True)
        (destination/'Twinlight-delivery.zip').unlink(missing_ok=True)
        raise
