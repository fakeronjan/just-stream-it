# Week 11 edition builder (11/24/2026), kept as a template for writing the current panel from data + prose.
"""Write the Week 11 Recap / Week 12 Preview into the current panel of docs/index.html."""
import json, re
R = '/Users/ronjan/code/fakeronjan/games/just-stream-it/'
P = R + 'docs/index.html'
src = open(P).read()

# ================= HTML =================
h_start = src.index('  <!-- ================= CURRENT EDITION: Week 10 Recap / Week 11 Preview ================= -->')
h_stat = src.index('    <div class="section-label" id="sec-statbook">')
LEDE1 = ("Three weeks are left, and the top two already have their tickets punched. Lisette and Melinda both won to reach 9-2 "
         "and clinched playoff spots, so the only thing left for them to fight over is the two byes. Behind them, Joe climbed to "
         "7-4, and mariss's third straight win dragged him into a three-way tie at 6-5 with Ronjan and Cara. Ronjan holds "
         "fourth place over Cara by 0.46 points. Mike fell to seventh, one game out, and Ben, Karl, and Pete are stuck two back at 4-7.")
LEDE2 = ("Week 11 was brutal on benches. Mike's twelve reserves scored exactly zero, Melinda won anyway with 82.3 points sitting "
         "on hers, and Pete's best possible lineup would have managed 60.6. He settled for 59.2, the lowest score of the season. "
         "Now the stakes come early. Thanksgiving week kicks off Wednesday night, and eight owners will watch their favorite NFL "
         "teams play before Sunday. Kris and Imran are eliminated with a loss. Lisette clinches a bye by beating Joe, and Joe "
         "locks up a playoff spot if he beats her and Mike loses.")
INJ_INTRO = ("Puka Nacua's season is over. Ben's star receiver had MCL surgery and will miss four to five months, and Justin Herbert "
             "is in the concussion protocol. Thanksgiving puts a clock on every questionable tag, since Saquon Barkley, Sam LaPorta, "
             "and Kenneth Walker III all play Thursday.")
BB = ("Nobody blew a game in Week 11. mariss and Mike both started their best possible lineups, and only mariss "
      "won. Melinda captured just 81.3% of her possible points, the "
      "worst of the week, and won anyway. Joe still leads the season in efficiency at 93.7%, and Karl's best lineups would have him "
      "at 7-4 instead of 4-7.")
html_new = f'''  <!-- ================= CURRENT EDITION: Week 11 Recap / Week 12 Preview ================= -->
  <section class="edition" id="panel-current">
    <nav class="section-nav" aria-label="Sections"><a href="#sec-results">Week 11 Results</a><a href="#sec-standings">Standings</a><a href="#sec-week12">Week 12 Preview</a><a href="#sec-injuries">Injuries</a><a href="#sec-statbook">Statbook</a></nav>
    <p class="kicker">Week 11 Recap</p>
    <h2 class="edition-head">Bye Bye Bye!</h2>
    <p class="dateline">2026 Season &middot; Week 11 Complete &middot; Week 12 Preview Below</p>
    <p class="lede">{LEDE1}</p>
    <p class="lede">{LEDE2}</p>

    <div class="section-label" id="sec-results">Week 11 Results</div>
    <div class="matchup-grid" id="recap-matchup-grid"></div>

    <div class="section-label" id="sec-standings">Playoff Picture</div>
    <p class="section-sublabel">Standings through eleven weeks</p>
    <div class="standings-list" id="standings-list"></div>
    <p class="standings-caption">Top 6 make the playoffs &middot; back column shown only when tied in wins</p>

    <div class="section-label" id="sec-week12">Week 12 Matchups</div>
    <p class="section-sublabel">Rosters, 2025 head-to-head, and Familiar Faces</p>
    <div class="matchup-grid" id="week12-matchup-grid"></div>

    <div class="section-label" id="sec-injuries">The Injury Report</div>
    <p class="section-sublabel">Who's hurt heading into Week 12</p>
    <p class="lede" style="font-size:0.95rem;">{INJ_INTRO}</p>
    <div id="injury-list"></div>

'''
src = src[:h_start] + html_new + src[h_stat:]
bb_old = re.search(r'(<h3 class="stat-subhead">Best Ball</h3>\n    <p class="lede" style="font-size:0.95rem;">)(.*?)(</p>)', src[h_start:], re.S)
a = h_start + bb_old.start(2); b = h_start + bb_old.end(2)
src = src[:a] + BB + src[b:]
src = src.replace('<button class="edition-tab active" data-panel="panel-current" type="button">Week 10 Recap</button>',
                  '<button class="edition-tab active" data-panel="panel-current" type="button">Week 11 Recap</button>', 1)
src = src.replace('      <span>Week 10 Edition</span>', '      <span>Week 11 Edition</span>', 1)
src = re.sub(r'<meta name="description" content="The Nielson News Week \d+ Recap with standings, the injury report, and every Week \d+ matchup.">',
             '<meta name="description" content="The Nielson News Week 11 Recap with standings, the injury report, and every Week 12 matchup.">', src, 1)

# ================= JS =================
j_start = src.index('/* ============================================================\n   CURRENT EDITION: Week 10 Recap / Week 11 Preview')
j_end = src.index('/* ============================================================\n   STATBOOK')
js = src[j_start:j_end]
js = js.replace('CURRENT EDITION: Week 10 Recap / Week 11 Preview', 'CURRENT EDITION: Week 11 Recap / Week 12 Preview', 1)

def repl_block(js, start_marker, end_marker, new):
    s = js.index(start_marker); e = js.index(end_marker, s) + len(end_marker)
    return js[:s] + new + js[e:]

def bt(s):
    assert '`' not in s and '${' not in s
    return '`' + s + '`'

RESULTS = [
 dict(a=2, aScore=139.88, b=4, bScore=130.92, tag='Game of the Week', text=
  "Mednis Madness (mariss) edged Conquering Heroes (Ben) 139.9-130.9 with a perfect lineup, and Chuba Hubbard did the heavy "
  "lifting with 120 yards and 2 touchdowns (26.0). Geno Smith threw 3 more (19.4). Ben's reverse jinx half worked. After he "
  "trashed his own quarterback play in the group chat, Justin Herbert (22.4) and Baker Mayfield (19.1) both crushed their "
  "projections, but his receivers vanished. Emeka Egbuka and Jordyn Tyson combined for 4.3, Jacksonville lost a challenge on a "
  "Parker Washington catch that Ben swears was a touchdown, and Will Reichard missed from 55 and on a 71-yard fair-catch kick. "
  "mariss has won three straight and moved into the top six."),
 dict(a=12, aScore=115.90, b=3, bScore=59.16, tag='Blowout of the Week', text=
  "Buffalo Abusement Park (Melinda) beat Beard Al (Pete) 115.9-59.2, and she even helped him set his lineup. On Thursday night "
  "Melinda warned her own opponent that he had three players on bye, a lineup Kris dubbed \"an NSYNC.\" Pete fixed it and "
  "posted 59.2 anyway, a new season low. Bills fan Pete got 2 interceptions from Josh Allen (12.2), and Rachaad White "
  "and the Vikings defense put up zeros. Melinda barely needed to show up. Ja'Marr Chase managed 5.6, while Ted Hurst III (20.1) "
  "and Khalil Shakir (12.8) sat on her bench. Pete has seen enough: \"I've officially given up on NFL and moving on to NBA.\""),
 dict(a=10, aScore=148.54, b=11, bScore=92.54, tag='Stud of the Week', text=
  "The Aristocrats (Karl) won the annual El &Aacute;ssico, as Kris calls it, 148.5-92.5 with the week's top score. Dak Prescott, "
  "who scored 282.1 points for Kris last season, threw 4 touchdowns and ran in another (35.9) in Dallas's 51-30 rout of "
  "Tennessee. Chiefs fan Kris got beaten by a Chief, too. Travis Kelce caught 2 touchdowns (22.4), and Raider Ashton Jeanty piled "
  "up 169 yards (25.4). Kris's lineup came in 29.8 under its projection, with Luther Burden III, Dalton Schultz, and Seth "
  "McGowan combining for 5.2. Karl has won two straight."),
 dict(a=9, aScore=146.46, b=7, bScore=102.76, tag=None, text=
  "Gibbs-n Them the Business (Ronjan) beat Terrible Towels (Mike) 146.5-102.8 in a Bengals Bowl nobody asked for. Steelers fan "
  "Mike started four Bengals against Bengals fan Ronjan, picking up Mike Gesicki that week to complete the set. They combined for "
  "39.3 in Cincinnati's 22-20 loss in Washington. Ronjan got 25.8 from Jahmyr Gibbs, 22.2 from Cam Ward, and 2 touchdowns from "
  "Ladd McConkey (18.2). Mike started his best possible lineup and still lost by 43.7, because his twelve bench players scored "
  "exactly 0.00. Every one of them was on bye, hurt, or held without a stat. Mike drops out of the top six."),
 dict(a=6, aScore=134.76, b=5, bScore=99.42, tag=None, text=
  "Mahomes is where the heart is (Lisette) beat Team Kantastrophe (Cara) 134.8-99.4 and clinched her playoff spot. The namesake "
  "threw 3 touchdowns (25.0), George Kittle caught 2 (16.9), and Justice Hill more than doubled his projection (15.6). Cara's "
  "lineup fell 31.1 short of ESPN's projection. DK Metcalf got ejected against Philadelphia with 0.7, so Eagles fan Cara lost a "
  "starter to her own team. Jonathan Taylor ran for 21 yards (4.7) in Indianapolis's 26-3 loss, and Kirk Cousins threw no "
  "touchdowns (7.4)."),
 dict(a=8, aScore=129.06, b=1, bScore=116.72, tag=None, text=
  "Olave Oyl (Joe) beat Sophomore Slump (Imran) 129.1-116.7 because Joe's whole lineup showed up. Jared Goff (20.4), DJ Moore "
  "(19.1), Breece Hall (17.5), and Derrick Henry (17.1) all beat their projections. Imran got a monster day from Jonah Coleman, "
  "who ran for 3 touchdowns (32.9) in Denver's backfield, and Javonte Williams scored twice (22.6) against the team that traded "
  "him. With Sam Darnold hurt and Seattle on bye, though, Imran had to start Joe Milton at OP, and Milton managed 6.3. Joe is 7-4 "
  "and can clinch a playoff spot this week."),
]
lines = []
for r in RESULTS:
    lines.append(f"  {{ a: {r['a']}, aScore: {r['aScore']:.2f}, b: {r['b']}, bScore: {r['bScore']:.2f}, tag: {repr(r['tag']) if r['tag'] else 'null'},\n    text: {bt(r['text'])} }},")
res_js = ('''// ---------- All 6 Week 11 results. Every number checked against
// docs/data/2026/weekly_boxscores.json (actual + ESPN's pregame
// projected_points), season_moments.json's best_ball weeks, and ESPN's
// Week 11 game summaries (stat lines, injury blocks, play-by-play:
// Metcalf disqualification, Reichard's 55- and 71-yard misses, the
// upheld Parker Washington challenge). Tags from build_weekly_recap.py's
// features. Fandom notes from league_rules/owner_nfl_fandom.json. Group
// chat (WhatsApp, 11/19-11/23): Melinda's bye warning, Kris's "NSYNC"
// and "El Assico", Pete's NBA line, Ben's reverse jinx, Ronjan on Mike's
// Bengals and zero-point bench. No trades since the Week 10 edition
// (rosters.json owner diff); Mike added Mike Gesicki and Tommy DeVito.
const MATCHUP_RESULTS = [
''' + '\n'.join(lines) + '\n];')
js = repl_block(js, "// ---------- All 6 Week 10 results.", "\n];", res_js)

# ---------- injuries from rosters.json, standings order
ros = json.load(open(R + 'docs/data/2026/rosters.json'))
pp = json.load(open(R + 'docs/data/2026/weekly_recap.json'))[-1]['playoff_picture']
assert pp and len(pp) == 12
ST = {'INJURY_RESERVE': 'Injured Reserve', 'QUESTIONABLE': 'Questionable', 'OUT': 'Out', 'DOUBTFUL': 'Doubtful', 'DAY_TO_DAY': 'Day-to-Day'}
inj = []
for p in pp:
    for x in ros[str(p['team_id'])]:
        if x['position'] == 'D/ST' or x['injury_status'] in ('ACTIVE', None, 'NORMAL'):
            continue
        inj.append(f"  {{ name: {json.dumps(x['name'])}, pos: '{x['position']}', team: {p['team_id']}, status: '{ST[x['injury_status']]}' }},")
inj_js = ('''// ---------- Leaguewide injury audit: every rostered player (D/ST
// excluded) whose injury_status in docs/data/2026/rosters.json (pulled
// 11/24/2026) is anything other than ACTIVE, any team, any position.
// Teams in standings order.
const INJURIES = [
''' + '\n'.join(inj) + '\n];')
js = repl_block(js, "// ---------- Leaguewide injury audit", "\n];", inj_js)

NOTES = {
 12: "Dallas Goedert is questionable for Thursday's game in Dallas.",
 8: "Jalen Hurts and Malik Willis are both still on injured reserve, so Jared Goff remains Joe's only starting quarterback.",
 9: "Saquon Barkley was limited Monday with neck and illness issues, and Sam LaPorta with an ankle. Both play Thursday. A.J. Brown is doubtful, and the Colts released Daniel Jones on Friday.",
 5: "Mike Vrabel doesn't expect Drake Maye back this week.",
 2: "Kyler Murray (hamstring) and Jordan Addison (thumb) are still out.",
 7: "Tommy DeVito, Mike's newest quarterback, starts for New England in Maye's place. Brock Bowers is still out with his ankle injury, and Jaxson Dart remains on injured reserve.",
 4: "Puka Nacua is out for the season after MCL surgery. If Justin Herbert can't clear the concussion protocol, DJ Uiagalelei would likely start. Kenneth Walker III didn't practice Monday, and Emmett Johnson starts Thursday night if Walker can't go. Ben has both.",
 10: "Josh Jacobs is still out after finger surgery.",
 11: "Woody Marks is still out after his concussion, and Lamar Jackson and Jeremiyah Love remain on injured reserve.",
 1: "Sam Darnold returned to practice Monday and is on track to start Sunday against San Francisco.",
}
order = [p['team_id'] for p in pp]
notes_js = ('''// Forward-looking note per team, rendered as a full-width row closing
// that team's group. Only teams with something to say get one. Sources:
// ESPN (Nacua, Darnold, Herbert), CBS and NFL.com (Maye, Walker,
// DeVito), Eagles and Lions Monday reports (Barkley, LaPorta), the Colts
// (Jones), all as of 11/24.
const INJ_NOTES = {
''' + '\n'.join(f"  {t}: {bt(NOTES[t])}," for t in order if t in NOTES) + '\n};')
js = repl_block(js, "// Forward-looking note per team", "\n};", notes_js)

std = []
for p in pp:
    back = f"{p['points_back']:.1f}" if p['points_back'] is not None else 'null'
    std.append(f"  {{ team: {p['team_id']},{' ' if p['team_id'] < 10 else ''} wins: {p['wins']}, losses: {p['losses']}, pf: {p['points_for']:.1f}, back: {back} }},")
std_js = ('''// ---------- Current playoff picture, straight from
// docs/data/2026/weekly_recap.json's playoff_picture after Week 11.
const STANDINGS = [
''' + '\n'.join(std) + '\n];')
js = repl_block(js, "// ---------- Current playoff picture", "\n];", std_js)

# ---------- Week 12 preview
ppg_sorted = sorted(pp, key=lambda p: -p['points_for'])
PPG = {p['team_id']: (p['points_for'] / 11, i + 1) for i, p in enumerate(ppg_sorted)}
RK = {p['team_id']: (p['rank'], p['wins'], p['losses']) for p in pp}
def tag(t):
    r, w, l = RK[t]; v, k = PPG[t]
    return f"#{r} &middot; {w}-{l}<span class=\"tag-ppg\">{v:.1f} PPG (#{k})</span>"
W12 = [
 dict(a=6, b=8, tag='Game of the Week', games=[(1, 108.26, 153.52), (12, 122.62, 163.36)], swaps=[]),
 dict(a=12, b=5, tag=None, games=[(1, 134.00, 122.28), (12, 104.72, 132.08)],
      swaps=[("Juwan Johnson (TE)", 12, 5, "round: 15"), ("Dallas Goedert (TE)", 5, 12, "round: 8")]),
 dict(a=7, b=4, tag=None, games=[(1, 86.88, 100.44), (12, 67.26, 137.04)],
      swaps=[("Parker Washington (WR)", 7, 4, "round: 7"), ("Brock Bowers (TE)", 4, 7, "round: 4"), ("Tee Higgins (WR)", 4, 7, "round: 5")]),
 dict(a=10, b=3, tag=None, games=[(1, 111.88, 159.04), (12, 116.50, 119.26)], swaps=[]),
 dict(a=9, b=11, tag=None, games=[(1, 115.90, 143.04), (12, 189.40, 120.78)],
      swaps=[("Sam LaPorta (TE)", 11, 9, "round: 6"), ("DeVonta Smith (WR)", 9, 11, "round: 4")]),
 dict(a=2, b=1, tag=None, games=[(1, 111.92, 139.98), (12, 171.34, 103.66)],
      swaps=[("Elic Ayomanor (WR)", 2, 1, "how: 'waivers'"), ("Isaiah Likely (TE)", 1, 2, "round: 6")]),
]
NOTE = {
 6: "Lisette clinches a first-round bye with a win. Joe clinches a playoff spot by winning if Mike also loses. This is a Week 1 rematch, and Joe won that one 201.6-107.3, still the highest score of 2026. Lisette's namesake plays at Buffalo on Thanksgiving night, and Packers fan Joe gets his team Wednesday night against the Rams.",
 12: "Melinda clinches a bye if she and Lisette both win. Seven of her Week 11 starters play Thursday or Friday, so her week could be over before Cara's starts. Eagles fan Cara gets CeeDee Lamb against her own team on Thanksgiving. Dallas Goedert scored 86.3 points for Cara last season and now plays for Melinda. Melinda won the Week 1 meeting 123.5-98.0.",
 7: "Ben is eliminated with a loss if Ronjan, Cara, and mariss all win. A Mike win plus an Imran upset of mariss would put Mike back in the top six, as long as he stays ahead of mariss on total points. Tee Higgins scored 148.0 points for Ben last season and ranks sixth among receivers for Mike, and Parker Washington went the other way and ranks 10th. Ben has both Chiefs backs for Thursday night in Buffalo. Mike won the Week 1 meeting 156.4-127.6.",
 10: "If Ronjan, Cara, and mariss all win, the loser here is eliminated. Cowboys fan Karl has Dak Prescott and Brandon Aubrey on Thanksgiving against the Eagles, and Bills fan Pete has Josh Allen hosting the Chiefs that night. Karl won the Week 1 meeting 140.9-133.5.",
 9: "A loss ends Kris's season. Chiefs fan Kris has Rashee Rice at Buffalo on Thanksgiving night, and Ronjan has Jahmyr Gibbs and Sam LaPorta against the Bears that afternoon. Kris won the Week 1 meeting 134.9-121.9.",
 2: "A loss ends Imran's season, too. mariss would stay in the top six with a win. Sam Darnold could return for Imran against San Francisco and Isaiah Likely, a former Imran tight end, ranks second at the position for mariss. mariss won the Week 1 meeting 147.1-92.6.",
}
wl = []
for m in W12:
    m['note'] = NOTE[m['a']]
    g = ', '.join(f"{{ week: {w}, aScore: {x:.2f}, bScore: {y:.2f} }}" for w, x, y in m['games'])
    sw = ',\n             '.join(f"{{ player: {json.dumps(p)}, from: {f}, to: {t}, {k} }}" for p, f, t, k in m['swaps'])
    tg = f"tag: '{m['tag']}', " if m['tag'] else ''
    wl.append(f"  {{ a: {m['a']}, {tg}aTag: '{tag(m['a'])}', b: {m['b']}, bTag: '{tag(m['b'])}',\n    games: [{g}],\n    swaps: [ {sw} ],\n    note: {bt(m['note'])} }},")
w_js = ('''// ---------- Week 12 preview. 2025 head-to-head from
// docs/data/2025/matchups.json: every pair met twice in the 2025 regular
// season (Weeks 1 and 12), and every Week 12 game is a rematch of 2026
// Week 1. Swaps by player_id, 2025 final rosters vs current 2026
// rosters, D/ST and K excluded; `round` = 2026 draft round, `how`
// replaces it when the player arrived another way. No NFL byes in Week
// 12; GB-LAR plays Wednesday, CHI-DET, PHI-DAL, and KC-BUF Thursday,
// DEN-PIT Friday (ESPN scoreboard). Ordered by stakes, Game of the Week
// first. Stakes from enumerating all 64 Week 12 outcomes, plus all 4,096
// Week 13-14 outcomes for clinching and elimination. PPG = points_for /
// 11, rank among 12. Position ranks are 2026 season points.
const WEEK12_MATCHUPS = [
''' + '\n'.join(wl) + '\n];')
js = repl_block(js, "// ---------- Week 11 preview.", "\n];", w_js)
js = js.replace('function renderWeek11Matchup(m)', 'function renderWeek12Matchup(m)')
js = js.replace("document.getElementById('week11-matchup-grid').innerHTML = WEEK11_MATCHUPS.map(renderWeek11Matchup).join('');",
                "document.getElementById('week12-matchup-grid').innerHTML = WEEK12_MATCHUPS.map(renderWeek12Matchup).join('');")
assert 'WEEK11' not in js and 'Week11' not in js and 'week11' not in js, [l for l in js.splitlines() if 'eek11' in l.replace('Week 11', '')]
src = src[:j_start] + js + src[j_end:]
open(P, 'w').write(src)
print('ok')
