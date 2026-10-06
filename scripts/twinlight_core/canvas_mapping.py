"""Explicit display sampling for one-pixel native tool rounding; never rewrite assets."""
from __future__ import annotations
from PIL import Image
from .common import ContractError

POLICY = 'native-rounding-1'
NATIVE_ROLES = frozenset(('background', 'subject', 'effects', 'spirit'))


def native_dimensions_allowed(actual, canvas, *, native_edit=False) -> bool:
    if (not isinstance(actual, (tuple,list)) or not isinstance(canvas,(tuple,list))
            or len(actual) != 2 or len(canvas) != 2
            or any(type(n) is not int or n < 256 for n in (*actual,*canvas))):
        return False
    return tuple(actual) == tuple(canvas) or (native_edit is True and all(abs(a-b) <= 1 for a,b in zip(actual,canvas)))


def rounding_diagnostic(actual, canvas) -> dict:
    return {'policy':POLICY,'native_canvas':list(actual),'logical_canvas':list(canvas),
            'delta_px':[a-b for a,b in zip(actual,canvas)],'max_delta_px':1,
            'source_pixels_modified':False,'display_sampling':'full_uv_bilinear',
            'visual_registration_verified':False}


def logical_canvas(manifest: dict, images: dict) -> tuple[int,int]:
    mapping = manifest.get('canvas_mapping')
    if mapping is None:
        sizes = {im.size for im in images.values()}
        if len(sizes) != 1:
            raise ContractError('All layers must use the same canvas unless explicit native rounding mapping is recorded')
        return next(iter(sizes))
    if not isinstance(mapping,dict) or mapping.get('version') != POLICY or mapping.get('sampling') != 'full_uv_bilinear':
        raise ContractError('Unsupported native canvas mapping policy')
    canvas = mapping.get('canvas')
    if not native_dimensions_allowed(canvas,canvas) or canvas[0]*canvas[1] > 16_000_000 or abs(canvas[0]/canvas[1]-.75) >= .01:
        raise ContractError('The logical canvas must remain the approved native 3:4 prototype canvas')
    roles = mapping.get('native_edit_roles')
    if not isinstance(roles,list) or not roles or len(roles) != len(set(roles)) or not set(roles).issubset(NATIVE_ROLES):
        raise ContractError('Declare only actual native image-edit roles in the canvas mapping')
    for role, im in images.items():
        allowed = role in roles
        if role == 'lineart' and 'subject' in roles and 'subject' in images:
            allowed = im.size == images['subject'].size
        if not native_dimensions_allowed(im.size,canvas,native_edit=allowed):
            raise ContractError(role + ': native layer mismatch exceeds the explicit one-pixel rounding policy')
    return tuple(canvas)


def mapping_for(canvas, images: dict, native_edit_roles) -> dict | None:
    if all(im.size == tuple(canvas) for im in images.values()):
        return None
    mapping = {'version':POLICY,'canvas':list(canvas),'sampling':'full_uv_bilinear',
               'native_edit_roles':sorted(set(native_edit_roles))}
    logical_canvas({'canvas_mapping':mapping},images)
    return mapping


def render_layers(manifest: dict, images: dict) -> dict:
    """Sample full UVs into a temporary render target; input images/files are intact."""
    canvas = logical_canvas(manifest,images)
    return {role:im.convert('RGBA') if im.size == canvas else im.convert('RGBA').resize(canvas,Image.Resampling.BILINEAR)
            for role,im in images.items()}


display_layers = render_layers


def compose_layers(manifest: dict, images: dict, *, include_text=False) -> Image.Image:
    displayed = render_layers(manifest,images)
    result = displayed['background'].copy()
    roles = ('spirit','subject','effects','text') if include_text else ('spirit','subject','effects')
    for role in roles:
        result = Image.alpha_composite(result,displayed[role])
    return result
