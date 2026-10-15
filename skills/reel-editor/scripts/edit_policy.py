"""Shared render guardrails. No media or network side effects."""
import copy
import math

SFX_ALIASES = {'sparkle':'chime','coin':'chime','mouse-click':'snap','click':'snap','keyboard':'typing','woosh':'whoosh'}

def prepare_edit(edit, brand):
    result = copy.deepcopy(edit)
    style = result.setdefault('captionStyle', {})
    style.setdefault('fixedPosition', brand.get('captions', {}).get('fixed_position', True))
    if style['fixedPosition']:
        for caption in result.get('captions', []):
            for key in ('x', 'y', 'width', 'size'):
                caption.pop(key, None)
    for card in result.get('cards', []):
        a, b = card.get('start', 0), card.get('end')
        if not math.isfinite(a) or a < 0 or (b is not None and (not math.isfinite(b) or b <= a)):
            raise ValueError('Card start/end must be finite, positive and ordered')
        if card.get('subject_style'):
            raise ValueError('Manual subject CSS masks can cut hair/face. Refine the alpha media instead; preview the whole head throughout the shot.')
        if card['type'] == 'title' and card.get('single_line'):
            card['text'] = ' '.join(card['text'].replace('/', ' ').split())
            card['size'] = min(card.get('size', 230), max(24, int(900 / (max(len(card['text']), 1) * .66))))
        for word in card.get('layout', []):
            if not 60 <= word['x'] <= 1020 or not 60 <= word['y'] <= 1700:
                raise ValueError('Hook words must start inside the safe frame (x 60–1020, y 60–1700)')
            available = 1020 - word['x']
            # Conservative advance estimate; actual font geometry is checked in the preview.
            word['size'] = min(word['size'], max(12, int(available/(max(len(word['text']),1)*.55))))
    return result

def sound_name(name):
    return SFX_ALIASES.get(name, name)
