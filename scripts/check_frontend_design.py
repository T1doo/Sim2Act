"""Calculate solid-token contrast; this is not a browser/accessibility audit."""
import json
import re
from pathlib import Path

css = Path('src/sim2act/web/app.css').read_text()
base, dark = [dict(re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{3,6})\s*;', block))
              for block in (re.search(r':root\s*\{([^}]+)', css)[1],
                            re.search(r':root\[data-theme=dark\]\s*\{([^}]+)', css)[1])]

def luminance(value):
    value = value.lstrip('#')
    if len(value) == 3:
        value = ''.join(x * 2 for x in value)
    rgb = [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)]
    linear = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in rgb]
    return sum(x * w for x, w in zip(linear, (.2126, .7152, .0722), strict=True))

rows = []
for theme, values in [('light', base), ('dark', {**base, **dark})]:
    pairs = [(text, background, 4.5) for text in ['ink', 'muted', 'error', 'success', 'warning']
             for background in ['canvas', 'surface']]
    pairs += [('accent-ink', 'accent', 4.5), ('accent-ink', 'accent-hover', 4.5),
              ('ink', 'accent-soft', 4.5), ('disabled-ink', 'disabled', 4.5)]
    pairs += [(text, background, 3) for text in ['control', 'focus']
              for background in ['canvas', 'surface']]
    for foreground, background, minimum in pairs:
        a, b = sorted([luminance(values[foreground]), luminance(values[background])])
        ratio = (b + .05) / (a + .05)
        assert ratio >= minimum, (theme, foreground, background, ratio)
        rows.append(dict(theme=theme, foreground=foreground, background=background,
                         ratio=round(ratio, 3), minimum=minimum))
print(json.dumps(dict(status='PASS', scope='SOLID_CSS_TOKENS_ONLY_NOT_PIXEL_ACCESSIBILITY',
                     checks=rows), indent=2))
