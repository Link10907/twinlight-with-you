"""Two explicit task entry points, one existing renderer and delivery gate."""
from __future__ import annotations
from pathlib import Path
from .common import check, save, load
from .cardgen import read_card_data
from .lite import persona_digest


def freeze_card_input(source: Path, out: Path) -> dict:
    data=read_card_data(source)
    frozen={'twinlight':'card-1',**{key:data[key] for key in ('name','summarizer','card')}}
    check(source.resolve()!=out.resolve(), 'Do not replace the authorized person source')
    check(not out.exists() or load(out)==frozen, 'Frozen card input differs; use a new revision path')
    save(out,frozen)
    check(persona_digest(read_card_data(out))==persona_digest(data), 'Card projection changed identity binding')
    return {'ok':True,'out':str(out.resolve()),'persona_digest':persona_digest(data),'contains_galaxy':False}


def _retarget(action: dict | None) -> None:
    if not isinstance(action,dict):return
    cmd=action.get('resume')
    if isinstance(cmd,list) and 'run' in cmd and '--mode' in cmd:
        at=cmd.index('--mode')
        if cmd[at+1]=='card':
            del cmd[at:at+2];cmd[cmd.index('run')]='task-card'
    for nested in action.get('pending_actions',[]):_retarget(nested)


def card(input_path: Path, workspace: Path, **options) -> dict:
    from .run import run
    from .card_handoff import seal
    result=run(input_path,workspace,mode='card',**options)
    result['task']='card'
    _retarget(result.get('next_action'))
    # Save all A state before sealing. The handoff binds these exact bytes.
    save(Path(workspace)/'run-report.json',result)
    if result.get('complete'):
        result={**result,'card_handoff':seal(workspace)}
    return result


def site(input_path: Path, workspace: Path, *, card_handoff: Path | None=None, **options) -> dict:
    from .run import run
    from .card_handoff import validate
    previous=load(Path(workspace)/'run-state.json') if (Path(workspace)/'run-state.json').is_file() else {}
    source=card_handoff or previous.get('card_handoff_source')
    try:
        check(source is not None, 'Task B needs the independently released task A/card-handoff.json')
        imported=validate(Path(source),persona_digest(read_card_data(input_path)))
        check(not Path(workspace).resolve().is_relative_to(Path(imported['source_workspace']))
              and not Path(imported['source_workspace']).is_relative_to(Path(workspace).resolve()),
              'Task A and B require separate non-nested workspaces')
    except (OSError,ValueError,TypeError,KeyError) as exc:
        return {'ok':False,'complete':False,'status':'card_handoff_blocked','task':'site',
                'error':str(exc),'image_calls_performed':0,
                'next_action':{'type':'provide_current_released_card','user_confirmation_required':False,
                               'constraints':['Finish or repair only task A; task B never substitutes an unreviewed card.']}}
    return run(input_path,workspace,mode='both',card_handoff=Path(source),**options)
