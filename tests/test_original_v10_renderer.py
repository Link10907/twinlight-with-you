"""Preserve the user's original V10 optical renderer, independently of our lock.

Hashes were measured from /Users/link/Downloads/twinlight-v10 on 2026-10-05.
The original personal artwork is deliberately not a production dependency.
The revised finale vertex timing is outside this byte-identity assertion.
"""
import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADERS = {
    'holo-card.js': {
        'HOLO_VERT': '1acb06a6be3c7a8991174234305e4ace3b054a2721e1aa0b1d8eac9a4b6e14d9',
        'HOLO_FRAG': '1a7b7b310bb396dd6404ad478510bfda87ec343e6bb3330ad55c07f7f24805ea',
    },
    'render.js': {
        'VERTEX': '14cd1aa0792c7c158d66661889116e76f99ffef8ae7e5b1082fa3edb0ea11a1a',
        'FRAGMENT': 'bdce108807e5b3500d7c93e0a0f5a2c1d6446e314da997ffe1d4501dfdaecbf3',
        'POINT_VERTEX': '58cf252468f642d978750aaf42803a1e234da847f6f666022d3cbf02380b2912',
        'POINT_FRAGMENT': '682914b11bb473e51060814699229a6919b53ea979a3530991465e09da4dc35f',
        'STAR_VERTEX': '0ab1d5d93ff4f7a8be1e60a6fcdbc65453737e3493f21f122a82623a0d763928',
        'STAR_FRAGMENT': '8e08db4cc3432d921e0bb3284940cb33e71fd3ef9ea70cc25ccedec784ab1894',
        'RING_VERTEX': '09aaf00b75e3acb7972f5b9000c72ed5102893195b5ad944b2a70407f84c1ed1',
        'DISK_FRAGMENT': 'f06313823b445498dc42f21e66663a1a8a71d1bb3c1977a6e12c664514e1d3dd',
    },
    'finale.js': {
        'FX_F': 'b5dee320bcbbc4563007e71e8a6fff9cc4dc7df55698cb847e954f7cf20fc85e',
        'FX_BLUR': 'c693164be4481ec7481c543fd417af1b83a0586b381ceb51351e1c2dfc7e1b39',
        'FX_COMPOSITE': '783741329a7e12b4cb5c45ccb8e76cf1698030c864488189dd82222cdb27e24a',
    },
}


class OriginalV10Renderer(unittest.TestCase):
    def test_original_card_galaxy_planet_and_finale_optics_are_preserved(self):
        for filename, shaders in SHADERS.items():
            source = (ROOT / 'assets/template/src' / filename).read_text()
            for name, expected in shaders.items():
                with self.subTest(file=filename, shader=name):
                    match = re.search(r'(?:const|let)\s+' + re.escape(name) + r'\s*=\s*`([^`]+)`', source)
                    self.assertIsNotNone(match, 'Original renderer program disappeared')
                    shader = match.group(1)
                    for token, depth in [('BG', '-.25'), ('SUBJECT', '.40'), ('EFFECTS', '.50')]:
                        shader = shader.replace('float(__DEPTH_' + token + '__)', depth)
                    self.assertEqual(hashlib.sha256(shader.encode()).hexdigest(), expected)

    def test_original_music_and_galaxy_textures_are_preserved(self):
        expected = {
            'another-light.mp3': '30104df43eaa3868297e34aa0775bafd04fc1fedb53ffbb0d687de2dd7058d51',
            'dust-disc.jpg': 'bcc321fa8d39b6bca850200e3cc19c6b5c6990dec246e920ab3e5fea48a13916',
            'stellar-atlas.jpg': '00ffa58027fa390b5321806f961d19e23b9dac079f70c332055482c41dbd228c',
        }
        for name, fingerprint in expected.items():
            with self.subTest(asset=name):
                self.assertEqual(hashlib.sha256((ROOT / 'assets/template/assets' / name).read_bytes()).hexdigest(), fingerprint)


if __name__ == '__main__':
    unittest.main()
