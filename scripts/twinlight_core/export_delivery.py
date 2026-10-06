"""Export only the actual hash-bound public delivery; never silently select base HTML."""
from __future__ import annotations
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from urllib.parse import quote
from .delivery import host_interaction_verified, request_outcome

REQUIRED = {'html':('html',), 'card':('card_front','card_preview','card_pack'),
            'both':('html_with_card','card_front','card_preview','card_pack')}
NAMES = {'html':'Twinlight.html','html_with_card':'Twinlight.html','card_front':'card-front.png',
         'card_preview':'card-preview.html','card_pack':'card-pack.json'}
LABELS = {'html':'个人星系 HTML','html_with_card':'完整星系与闪卡 HTML','card_front':'闪卡正面图',
          'card_preview':'独立闪卡互动预览','card_pack':'便携卡包 JSON','archive':'全部文件 ZIP'}


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


def _attachment(key: str, path: Path, link_style: str) -> dict:
    target = ('sandbox:' if link_style == 'sandbox' else '') + quote(str(path), safe='/:')
    entry={'key':key, 'label':LABELS[key], 'path':str(path), 'sha256':_sha(path),
           'bytes':path.stat().st_size, 'markdown':f'[{LABELS[key]}](<{target}>)'}
    if key=='card_front':
        entry['preview_markdown']=f'![闪卡正面](<{target}>)'
    return entry


def export(workspace: Path, destination: Path, *, link_style: str = 'local') -> dict:
    workspace,destination=Path(workspace).resolve(),Path(destination).resolve()
    if link_style not in ('local', 'sandbox'):
        raise ValueError('Unknown delivery link style')
    if link_style == 'sandbox' and not destination.is_relative_to(Path('/mnt/data')):
        raise ValueError('Sandbox links require actual exported files under /mnt/data; do not invent attachment paths')
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
    requirements=run.get('delivery_requirements',{'in_chat_preview':False})
    if (not isinstance(requirements,dict) or type(requirements.get('in_chat_preview')) is not bool
            or requirements!=receipt.get('delivery_requirements',{'in_chat_preview':False})):
        raise ValueError('Inconsistent delivery requirements; resume the public run')
    host=run.get('host_preview',{'status':'not_tested'})
    if not isinstance(host,dict) or host!=receipt.get('host_preview',{'status':'not_tested'}):
        raise ValueError('Inconsistent host observation; resume the public run')
    interaction_verified=host_interaction_verified(host,mode,_sha(Path(expected_primary)))
    satisfied,request_status=request_outcome(True,requirements['in_chat_preview'],host,interaction_verified)
    for record in (run,receipt):
        for key,value in (('request_satisfied',satisfied),('request_status',request_status),
                          ('in_chat_interaction_verified',interaction_verified)):
            if key in record and (type(record[key]) is not type(value) or record[key]!=value):
                raise ValueError('Inconsistent '+key+'; resume the public run')
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
        status=host.get('status','not_tested')
        contents=('Twinlight.html 是已内嵌本次闪卡的单文件。\n' if mode=='both' else
                  'Twinlight.html 是本次个人星系单文件。\n' if mode=='html' else '')
        if mode!='html':
            contents+='card-preview.html 是同一张原生分层卡的独立预览；card-front.png 为正面卡图，card-pack.json 为便携卡包。\n'
        note=('Twinlight 私人草稿\n\n'+contents+
              '在现代浏览器打开 HTML；不需要安装 Node、Python 或上传个人资料。\n'
              f'聊天宿主的直接预览状态：{status}。本地浏览器检查不能证明聊天窗口允许执行脚本。\n'
              f'本次明确交付要求的验证状态：{request_status}。文件完成不表示附件已发送到聊天。\n'
              '本包不含字体文件、原始聊天、原型评审或工具响应。不要未经本人审阅自动公开。\n')
        (destination/'READ-ME.txt').write_text(note,encoding='utf-8');created.append(destination/'READ-ME.txt')
        # The portable receipt excludes private tool observations and host-specific entry-point paths.
        host_summary={key:host[key] for key in ('version','status','html_sha256','surface') if key in host}
        result={'version':'delivery-export-2','mode':mode,'complete':True,'draft':True,'share_allowed':False,
                'host_preview':host_summary, 'delivery_requirements':requirements,
                'request_satisfied':satisfied,'request_status':request_status,
                'in_chat_preview_verified':run.get('in_chat_preview_verified') is True,
                'in_chat_interaction_verified':interaction_verified,
                'files':{key:{'file':NAMES[key],'sha256':fingerprint} for key,_,fingerprint in planned},
                'primary_file':NAMES[{'html':'html','card':'card_preview','both':'html_with_card'}[mode]],
                'scope':'Export of existing current public-run outputs; not new image generation or new browser validation.'}
        (destination/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        created.append(destination/'delivery.json')
        pack=destination/'Twinlight-delivery.zip'
        with zipfile.ZipFile(pack,'w',zipfile.ZIP_DEFLATED) as archive:
            for file in created: archive.write(file,file.name)
        result['archive']=str(pack);result['output_directory']=str(destination)
        # Local handoff files deliberately stay outside the portable ZIP: they contain host-specific paths.
        primary_key={'html':'html','card':'card_preview','both':'html_with_card'}[mode]
        ordered=[primary_key]+[key for key in required if key!=primary_key]
        attachments=[_attachment(key,destination/NAMES[key],link_style) for key in ordered]
        attachments.append(_attachment('archive',pack,link_style))
        preview_label=('已在聊天内观察所需交互' if interaction_verified else
                       {'unsupported':'当前宿主不支持','blocked':'当前宿主入口受阻'}.get(status,'尚未验证'))
        reply='文件已生成，本地动态检查通过。聊天内交互：'+preview_label+'。\n'
        if requirements['in_chat_preview'] and not satisfied:
            reply+='你要求的聊天内直接交互尚未完成；以下是已完成的文件。\n'
        reply+='\n'+'\n'.join('- '+item['markdown'] for item in attachments)+'\n\n私人未确认草稿，未公开。\n'
        for item in attachments:
            if item.get('preview_markdown'):
                reply+='\n'+item['preview_markdown']+'\n'
        reply_path=destination/'delivery-reply.md'
        reply_path.write_text(reply,encoding='utf-8');created.append(reply_path)
        handoff={'version':'delivery-handoff-1','request_satisfied':satisfied,'request_status':request_status,
                 'reply_file':str(reply_path),'link_style':link_style,'attachments':attachments,
                 'delivery_sent':False,
                 'host_action':'Present these actual files together in the first final response. Verify attachments resolve on this host; this script cannot send them or control when the host ends its turn.'}
        handoff_path=destination/'handoff.json'
        handoff_path.write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');created.append(handoff_path)
        result['reply_file']=str(reply_path);result['handoff_file']=str(handoff_path)
        result['attachments']=attachments;result['delivery_sent']=False
        return result
    except Exception:
        for file in created: file.unlink(missing_ok=True)
        (destination/'Twinlight-delivery.zip').unlink(missing_ok=True)
        raise
