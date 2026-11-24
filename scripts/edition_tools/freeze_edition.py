# Template from the Week 10 freeze (11/24/2026). For the next freeze, bump the week numbers, WK10R_ prefix, wk10 logo folder, and the published date.
"""Freeze the current Week 10 Recap edition into panel-week10-recap (WK10R_ prefix, logos/2026-wk11/).
Purely structural: no text content changes. Verifies by de-prefixing."""
import re, sys, shutil, os
P = '/Users/ronjan/code/fakeronjan/games/just-stream-it/docs/index.html'
src = open(P).read()

# ---------- HTML ----------
h_start = src.index('  <!-- ================= CURRENT EDITION: Week 10 Recap / Week 11 Preview ================= -->')
h_stat = src.index('    <div class="section-label" id="sec-statbook">')
h_frozen9 = src.index('  <!-- ================= FROZEN EDITION: Week 9 Recap')
html_cur = src[h_start:h_stat]
ids = ['sec-watch', 'sec-results', 'sec-standings', 'sec-week11', 'sec-injuries', 'sec-statbook',
       'recap-matchup-grid', 'standings-list', 'week11-matchup-grid', 'injury-list']
fh = html_cur.replace('  <!-- ================= CURRENT EDITION: Week 10 Recap / Week 11 Preview ================= -->',
                      '  <!-- ================= FROZEN EDITION: Week 10 Recap / Week 11 Preview (published 11/17/2026) ================= -->')
fh = fh.replace('<section class="edition" id="panel-current">', '<section class="edition" id="panel-week10-recap" hidden>')
# drop the Statbook nav link (statbook moves to the new current panel)
fh = fh.replace('<a href="#sec-statbook">Statbook</a>', '')
for i in ids:
    fh = fh.replace(f'id="{i}"', f'id="wk10r-{i}"').replace(f'href="#{i}"', f'href="#wk10r-{i}"')
fh = fh.rstrip() + '\n  </section>\n\n'
assert 'id="sec-' not in fh and 'href="#sec-' not in fh

# ---------- JS ----------
j_start = src.index('/* ============================================================\n   CURRENT EDITION: Week 10 Recap / Week 11 Preview')
j_end = src.index('/* ============================================================\n   STATBOOK')
js_cur = src[j_start:j_end]
names = ['LOGO', 'TEAMS', 'crestImg', 'MATCHUP_RESULTS', 'INJURIES', 'INJ_NOTES', 'INJ_SHORT', 'renderInjuryTable',
         'STANDINGS', 'WEEK11_MATCHUPS', 'recordAfterWeek', 'renderMatchupResult', 'renderStandingsRow',
         'renderWeek11Matchup']

def split_literals(s):
    """Yield (is_literal, chunk) splitting on '...', "...", `...` and // comments."""
    out, i, buf = [], 0, ''
    while i < len(s):
        c = s[i]
        if c in '\'"`':
            out.append((False, buf)); buf = ''
            j = i + 1
            while s[j] != c:
                j += 2 if s[j] == '\\' else 1
            out.append((True, s[i:j + 1])); i = j + 1
        elif s.startswith('//', i):
            out.append((False, buf)); buf = ''
            j = s.index('\n', i); out.append((True, s[i:j])); i = j
        else:
            buf += c; i += 1
    out.append((False, buf))
    return out

def rename(s):
    for n in names:
        s = re.sub(rf'(?<![\w.$-]){n}(?![\w$-])', 'WK10R_' + n, s)
    return s

body = js_cur.split('\n', 3)[3]  # drop 3-line header comment
fbody = rename(body)
# render function
fbody = fbody.replace('function renderCurrentEdition()', 'function WK10R_renderEdition()')
for i in ['recap-matchup-grid', 'injury-list', 'standings-list', 'week11-matchup-grid']:
    fbody = fbody.replace(f"getElementById('{i}')", f"getElementById('wk10r-{i}')")
fbody = fbody.replace("'logos/2026/", "'logos/2026-wk11/")
header = ('/* ============================================================\n'
          '   FROZEN PANEL: Week 10 Recap / Week 11 Preview (published 11/17/2026)\n'
          '   WK10R_-prefixed throughout. WK10R_LOGO points at the locked\n'
          '   logos/2026-wk11/ snapshot, not the live logos/2026/ path.\n'
          '   ============================================================ */\n')
fjs = header + fbody

# ---------- verify: de-prefix must reproduce original ----------
back = fjs.split('\n', 5)[5].replace('WK10R_renderEdition', 'renderCurrentEdition').replace('WK10R_', '')
back = back.replace("'logos/2026-wk11/", "'logos/2026/").replace("getElementById('wk10r-", "getElementById('")
if back != body:
    import difflib
    sys.stdout.writelines(list(difflib.unified_diff(body.splitlines(1), back.splitlines(1)))[:60]); sys.exit('JS diff')
# literal equality of all string literals except logo paths / element ids
la = [c for l, c in split_literals(body) if l]
lb = [c for l, c in split_literals(fbody) if l]
assert len(la) == len(lb)
diffs = [(a, b) for a, b in zip(la, lb) if a != b]
for a, b in diffs:
    assert a.startswith('//') or 'logos/2026' in a or a.strip("'") in ['recap-matchup-grid', 'injury-list', 'standings-list', 'week11-matchup-grid'] or '${' in a, (a[:80], b[:80])
    assert re.sub(r'WK10R_', '', b).replace('logos/2026-wk11/', 'logos/2026/').replace("'wk10r-", "'") == a, (a[:80], b[:80])
hb = fh.replace('wk10r-', '')
print('html check: lede text identical =', re.findall(r'<p class="lede".*?</p>', hb, re.S) == re.findall(r'<p class="lede".*?</p>', html_cur, re.S))

# ---------- assemble ----------
out = src[:h_frozen9] + fh + src[h_frozen9:]
k = out.index('/* ============================================================\n   FROZEN PANEL: Week 9 Recap')
out = out[:k] + fjs + '\n' + out[k:]
out = out.replace('    <button class="edition-tab" data-panel="panel-week9-recap" type="button">Week 9 Recap</button>',
                  '    <button class="edition-tab" data-panel="panel-week10-recap" type="button">Week 10 Recap</button>\n'
                  '    <button class="edition-tab" data-panel="panel-week9-recap" type="button">Week 9 Recap</button>', 1)
out = out.replace('  WK9R_renderEdition();', '  WK10R_renderEdition();\n  WK9R_renderEdition();', 1)
open(P, 'w').write(out)
d = '/Users/ronjan/code/fakeronjan/games/just-stream-it/docs/logos/'
if not os.path.exists(d + '2026-wk11'):
    shutil.copytree(d + '2026', d + '2026-wk11')
print('frozen ok; literal diffs', len(diffs))
