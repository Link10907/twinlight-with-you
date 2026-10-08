"""Browser diagnostics only. No art approval, model dispatch or template mutation."""
from __future__ import annotations

def launch_flags(gpu_mode: str = 'auto') -> list[str]:
    # Preserve the existing headless container compatibility flag. Normal graphics
    # driver selection is left to Chromium unless software rendering is explicit.
    flags = ['--no-sandbox']
    if gpu_mode == 'swiftshader':
        flags += ['--disable-gpu-sandbox', '--ignore-gpu-blocklist',
                  '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']
    elif gpu_mode != 'auto':
        raise ValueError('Unknown graphics mode: ' + gpu_mode)
    return flags

def runtime_snapshot(page) -> dict:
    return page.evaluate('''()=>({webgl:state.gl===true,reduced:state.reduced===true,
      requested_reduced_motion:matchMedia('(prefers-reduced-motion: reduce)').matches,
      hidden:document.hidden,testing:testing===true,ready:state.ready===true,
      time:v10.time,phase:v10.phase,playing:state.mergePlaying===true,
      card:v8.cardOpen===true,frame:state.frame,wall_ms:performance.now()})''')

def finale_route(snapshot: dict) -> dict:
    """Choose a valid check from observed runtime facts, never assume autoplay."""
    base = {'status': 'not_verified', 'autoplay_verified': False}
    if snapshot.get('hidden') is not False:
        return {**base, 'route': 'unavailable', 'reason': 'page_not_visible'}
    if snapshot.get('testing') is not False:
        return {**base, 'route': 'unavailable', 'reason': 'debug_animation_frozen'}
    if snapshot.get('reduced') is True:
        reason = 'webgl_fallback_forces_reduced_motion' if snapshot.get('webgl') is False else 'reduced_motion_active'
        return {**base, 'route': 'manual_reduced_motion', 'reason': reason}
    if snapshot.get('webgl') is not True:
        return {**base, 'route': 'unavailable', 'reason': 'galaxy_webgl_unavailable'}
    if snapshot.get('ready') is not True:
        return {**base, 'route': 'unavailable', 'reason': 'scene_not_ready'}
    return {**base, 'route': 'autoplay', 'reason': 'normal_rendering_path'}
