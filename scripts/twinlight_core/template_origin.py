"""Read-only reconstruction verifies fixed CLI sites against maintained templates.

A receipt is local traceability, not a signed attestation or visual approval.
Browser viewer exports and historical sites without these inputs are outside
this verifier's scope. Private render inputs stay beside the private site;
receipts and verification reports contain only hashes and logical paths.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from .common import VERSION, ContractError, digest, load, save

RECEIPT='template-receipt.json'
RENDER_INPUTS='render-inputs.json'
RECEIPT_SCHEMA='template-origin-1'
INPUT_SCHEMA='template-render-1'


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record_site(out: Path, profile: dict, layer_uris: dict, card_image_uri: str,
                depths: dict, template: str, sources: dict[str,str]) -> None:
    """Record actual saved inputs, without modifying the rendered HTML or JS."""
    save(out/'profile.json',profile)
    inputs={'schema_version':INPUT_SCHEMA,'layer_uris':layer_uris,
            'card_image_uri':card_image_uri,'depths':depths}
    save(out/RENDER_INPUTS,inputs)
    save(out/RECEIPT,{
        'schema_version':RECEIPT_SCHEMA,'coverage':'fixed_cli_site',
        'builder_version':VERSION,'template_name':'Twinlight V10-derived',
        'template_sha256':sha256(template.encode('utf-8')),
        'template_source_files_sha256':sources,
        'persona_digest':profile['persona']['persona_digest'],
        'render_inputs_sha256':digest({'profile':profile,'render':inputs}),
        'input_files_sha256':{name:sha256((out/name).read_bytes())
                              for name in ('profile.json',RENDER_INPUTS)},
        'output_files':{name:{'sha256':sha256((out/name).read_bytes()),
                              'bytes':(out/name).stat().st_size}
                        for name in ('index.html','compiled-check.js')},
        'limits':['Local traceability; not a signed attestation.',
                  'Does not establish illustration quality or browser rendering.',
                  'Browser viewer exports are not covered.'],
    })


def verify_site(target: Path) -> dict:
    """Rebuild expected bytes from the current template, profile and saved art.

    File names and reported paths are fixed by this verifier, never taken from
    the receipt. No inputs, outputs, receipt or reports are rewritten.
    """
    from .site import fill, personal_values, template_parts, template_source_hashes
    folder=target if target.is_dir() else target.parent
    errors=[]
    checks=[]
    result={'ok':False,'coverage':'fixed_cli_site','checks':checks,'errors':errors,
            'limits':['Local traceability; not a signed attestation.',
                      'Visual fidelity and browser behavior require separate checks.',
                      'Browser viewer exports and sites without receipts are not covered.']}

    def record(name: str, passed: bool, path: str, code: str) -> None:
        checks.append({'name':name,'passed':bool(passed)})
        if not passed:
            errors.append({'path':path,'code':code})

    def read(name: str):
        try:
            return load(folder/name)
        except (OSError,ValueError,TypeError):
            record('Readable '+name,False,name,'missing_or_invalid')
            return None

    if not target.is_dir() and target.name!='index.html':
        record('Fixed site target',False,'index.html','unsupported_target')
        return result
    receipt=read(RECEIPT)
    if not isinstance(receipt,dict):
        if receipt is not None:record('Receipt object',False,RECEIPT,'invalid_receipt')
        return result
    record('Supported receipt scope',receipt.get('schema_version')==RECEIPT_SCHEMA and
           receipt.get('coverage')=='fixed_cli_site',RECEIPT,'unsupported_receipt')
    record('Builder version unchanged',receipt.get('builder_version')==VERSION,RECEIPT,'builder_version_changed')
    try:
        html_template,js_template=template_parts()
        sources=template_source_hashes()
    except (OSError,ValueError,TypeError):
        record('Readable maintained template',False,'assets/template','missing_or_invalid_template')
        return result
    recorded_sources=receipt.get('template_source_files_sha256')
    record('Template source set unchanged',isinstance(recorded_sources,dict) and
           set(recorded_sources)==set(sources),'assets/template','template_source_set_changed')
    for path,sha in sources.items():
        record('Template source unchanged: '+path,isinstance(recorded_sources,dict) and
               recorded_sources.get(path)==sha,path,'template_source_changed')
    record('Assembled template unchanged',receipt.get('template_sha256')==sha256(html_template.encode('utf-8')),
           'assets/template','template_changed')
    profile=read('profile.json')
    render=read(RENDER_INPUTS)
    input_hashes=receipt.get('input_files_sha256')
    for name in ('profile.json',RENDER_INPUTS):
        try:
            actual=sha256((folder/name).read_bytes())
        except OSError:
            actual=None
        record('Saved input unchanged: '+name,actual is not None and isinstance(input_hashes,dict) and
               input_hashes.get(name)==actual,name,'input_changed')
    valid_inputs=(isinstance(profile,dict) and isinstance(profile.get('persona'),dict) and
                  isinstance(profile['persona'].get('persona_digest'),str) and
                  isinstance(render,dict) and set(render)=={'schema_version','layer_uris','card_image_uri','depths'} and
                  render.get('schema_version')==INPUT_SCHEMA and isinstance(render.get('layer_uris'),dict) and
                  all(isinstance(v,str) for v in render['layer_uris'].values()) and
                  isinstance(render.get('card_image_uri'),str) and isinstance(render.get('depths'),dict))
    record('Reconstructable saved inputs',valid_inputs,RENDER_INPUTS,'invalid_render_inputs')
    if not valid_inputs:return result
    record('Persona binding unchanged',receipt.get('persona_digest')==profile['persona']['persona_digest'],
           'profile.json','persona_binding_changed')
    record('Complete render input unchanged',receipt.get('render_inputs_sha256')==digest({'profile':profile,'render':render}),
           RENDER_INPUTS,'render_input_changed')
    try:
        values=personal_values(profile,render['layer_uris'],render['card_image_uri'],render['depths'])
        expected={'index.html':fill(html_template,values).encode('utf-8'),
                  'compiled-check.js':fill(js_template,values).encode('utf-8')}
    except (KeyError,TypeError,ValueError,ContractError):
        record('Reconstructable saved inputs',False,RENDER_INPUTS,'invalid_render_inputs')
        return result
    output_files=receipt.get('output_files')
    for name,expected_bytes in expected.items():
        try:
            actual_bytes=(folder/name).read_bytes()
        except OSError:
            record('Readable output: '+name,False,name,'missing_output')
            continue
        saved=output_files.get(name) if isinstance(output_files,dict) else None
        record('Output matches receipt: '+name,isinstance(saved,dict) and
               saved.get('sha256')==sha256(actual_bytes) and saved.get('bytes')==len(actual_bytes),
               name,'output_changed')
        # Receipt hashes alone cannot make a rewritten/custom HTML pass.
        record('Output equals independent reconstruction: '+name,actual_bytes==expected_bytes,
               name,'reconstruction_mismatch')
    result['ok']=not errors
    return result
