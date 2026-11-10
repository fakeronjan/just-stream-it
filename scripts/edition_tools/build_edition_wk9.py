# Week 9 edition builder (11/10/2026), kept as a template for writing the current panel from data + prose.
"""Write the Week 9 Recap / Week 10 Preview into the current panel of docs/index.html."""
import json, re
R = '/Users/ronjan/code/fakeronjan/games/just-stream-it/'
P = R + 'docs/index.html'
src = open(P).read()

# ================= HTML =================
h_start = src.index('  <!-- ================= CURRENT EDITION: Week 8 Recap / Week 9 Preview ================= -->')
h_stat = src.index('    <div class="section-label" id="sec-statbook">')
LEDE1 = ("Week 9 rewarded the wrong teams. Ronjan beat Joe 93.2-92.0 in the lowest-scoring game of the season, and only Pete "
         "scored less than either of them. mariss won with 103.9, the second-lowest winning score this year. Melinda lost to Mike "
         "161.1-152.8. No team has scored more in a loss this season, and it cost her first place. Lisette took it by scoring 177.4 "
         "against Pete, the most of anyone this week. She and Melinda are both 7-2, with Lisette ahead by 5.9 points.")
LEDE2 = ("Lisette, Melinda, and Cara hold the top three spots, and the same six teams are in playoff position as last week. Karl "
         "fell to 2-7 even though his all-play record is 50-49, because no team has faced more points. The injury news hit harder "
         "than the scores. Puka Nacua scored 28.0 for Ben and came out of the game with MCL and PCL sprains and turf toe. The Rams "
         "are expected to put him on injured reserve, which would keep him out until Week 15. Pete lost Michael Wilson for the "
         "season to a neck fracture he played through on Sunday.")
INJ_INTRO = ("Puka Nacua and Michael Wilson are the week's worst news. Josh Jacobs needs surgery on his finger, Sam Darnold misses "
             "another game, and Patrick Mahomes is day-to-day with an elbow strain.")
BB = ("Week 9 had three blown games, tying Week 8 for the most this season. Karl's third gives him the league lead outright, and "
      "Joe and Kris each blew one. Joe still leads in efficiency at 94.3%, and Cara is last at 84.0%. Ronjan and mariss each have "
      "two more wins than their best lineups would have earned, and Karl has three fewer.")
html_new = f'''  <!-- ================= CURRENT EDITION: Week 9 Recap / Week 10 Preview ================= -->
  <section class="edition" id="panel-current">
    <nav class="section-nav" aria-label="Sections"><a href="#sec-results">Week 9 Results</a><a href="#sec-standings">Standings</a><a href="#sec-week10">Week 10 Preview</a><a href="#sec-injuries">Injuries</a><a href="#sec-statbook">Statbook</a></nav>
    <p class="kicker">Week 9 Recap</p>
    <h2 class="edition-head">Highway Robbery</h2>
    <p class="dateline">2026 Season &middot; Week 9 Complete &middot; Week 10 Preview Below</p>
    <p class="lede">{LEDE1}</p>
    <p class="lede">{LEDE2}</p>

    <div class="section-label" id="sec-results">Week 9 Results</div>
    <div class="matchup-grid" id="recap-matchup-grid"></div>

    <div class="section-label" id="sec-standings">Playoff Picture</div>
    <p class="section-sublabel">Standings through nine weeks</p>
    <div class="standings-list" id="standings-list"></div>
    <p class="standings-caption">Top 6 make the playoffs &middot; back column shown only when tied in wins</p>

    <div class="section-label" id="sec-week10">Week 10 Matchups</div>
    <p class="section-sublabel">Rosters, 2025 head-to-head, and Familiar Faces</p>
    <div class="matchup-grid" id="week10-matchup-grid"></div>

    <div class="section-label" id="sec-injuries">The Injury Report</div>
    <p class="section-sublabel">Who's hurt heading into Week 10</p>
    <p class="lede" style="font-size:0.95rem;">{INJ_INTRO}</p>
    <div id="injury-list"></div>

'''
src = src[:h_start] + html_new + src[h_stat:]
# Best Ball paragraph (current panel only; first occurrence after the new header)
bb_old = re.search(r'(<h3 class="stat-subhead">Best Ball</h3>\n    <p class="lede" style="font-size:0.95rem;">)(.*?)(</p>)', src[h_start:], re.S)
a = h_start + bb_old.start(2); b = h_start + bb_old.end(2)
src = src[:a] + BB + src[b:]

# ================= JS =================
j_start = src.index('/* ============================================================\n   CURRENT EDITION: Week 8 Recap / Week 9 Preview')
j_end = src.index('/* ============================================================\n   STATBOOK')
js = src[j_start:j_end]
js = js.replace('CURRENT EDITION: Week 8 Recap / Week 9 Preview', 'CURRENT EDITION: Week 9 Recap / Week 10 Preview', 1)

def repl_block(js, start_marker, end_marker, new):
    s = js.index(start_marker); e = js.index(end_marker, s) + len(end_marker)
    return js[:s] + new + js[e:]

def bt(s):
    assert '`' not in s and '${' not in s
    return '`' + s + '`'

RESULTS = [
 dict(a=9, aScore=93.18, b=8, bScore=92.00, tag='Game of the Week', text=
  "Gibbs-n Them the Business (Ronjan) beat Olave Oyl (Joe) 93.2-92.0 in a game decided at quarterback. Joe's Jared Goff and "
  "Malik Willis combined for 9.1 points in Detroit's 19-9 win in Miami, and Willis hurt his groin. Ronjan lost Tony Pollard and "
  "Cam Ward to the Titans' bye, and Ladd McConkey scored zero after back spasms in warmups. Daniel Jones, who came over from Imran "
  "this week, scored 10.3 at OP. Bengals fan Ronjan also got 13.0 from Evan McPherson, the kicker he picked up. Kenny Gainwell's "
  "9.1 on Joe's bench would have flipped the result."),
 dict(a=6, aScore=177.36, b=3, bScore=84.56, tag='Blowout of the Week', text=
  "Mahomes is where the heart is (Lisette) beat Beard Al (Pete) 177.4-84.6, the biggest margin of the season, with two Packers. "
  "Jordan Love threw for 372 yards and scored 4 touchdowns (36.2), the week's top individual score, and Matthew Golden caught 10 "
  "passes for 164 yards (27.4) in Green Bay's 45-27 win over New England. Pete scored the week's lowest total. Joe Fagnano threw 2 "
  "interceptions at OP (-0.3) in Baltimore's 33-10 loss to Jacksonville, and Darren Waller scored 19.0 on Pete's bench."),
 dict(a=7, aScore=161.14, b=12, bScore=152.82, tag='Upset Alert', text=
  "Terrible Towels (Mike) beat Buffalo Abusement Park (Melinda) 161.1-152.8, and the sixth seed took down the first. Christian "
  "Watson caught 7 passes for 171 yards (26.6), and Shedeur Sanders scored 22.7 in his first start of the season while Deshaun "
  "Watson sat with a concussion. Steelers fan Mike still had to sit through 56.0 points from two Bengals, Joe Burrow (29.5) and "
  "Ja'Marr Chase (26.5). Melinda started Bam Knight, who was ruled out with a concussion, but every other running back she had "
  "was on bye or injured reserve."),
 dict(a=5, aScore=120.34, b=11, bScore=117.26, tag='Plot Twist', text=
  "Team Kantastrophe (Cara) beat Rice Rice Baby (Kris) 120.3-117.3 behind a Cowboy. Eagles fan Cara got 10 catches for 195 yards "
  "from CeeDee Lamb (28.5), and Bucky Irving, Pete's running back last season, ran for 2 touchdowns (26.5). C.J. Stroud nearly "
  "covered for Lamar Jackson by himself. He threw 5 touchdowns in Houston's 44-22 win over the Chargers (35.4). Injuries and bad "
  "days at running back tipped it, since Kris's four backs scored 21.6 against a 55.6 projection. Tank Dell's 18.5 sat on the bench."),
 dict(a=4, aScore=144.90, b=1, bScore=128.50, tag=None, text=
  "Conquering Heroes (Ben) beat Sophomore Slump (Imran) 144.9-128.5 even though Patriots fan Ben's Patriots defense scored -5.0 "
  "in a 45-27 loss to Green Bay. Kenneth Walker III scored 3 touchdowns (34.3), and Puka Nacua added 28.0. Imran had the fifth-best "
  "score of the week and lost anyway, because Jaxon Smith-Njigba (8.6) and Jaylen Waddle (2.7) combined for 11.3 against a 28.1 "
  "projection. Waddle left with a concussion. Sam Darnold, Imran's new quarterback from the Ronjan trade, missed the game with a "
  "quad injury, and Drew Lock scored 12.6 in his place."),
 dict(a=2, aScore=103.86, b=10, bScore=96.80, tag=None, text=
  "Mednis Madness (mariss) beat The Aristocrats (Karl) 103.9-96.8 because Karl lost two starters before they could score. Deshaun "
  "Watson didn't play after a week in the concussion protocol, so Karl's OP slot scored zero. Josh Jacobs, who scored 219.1 for "
  "mariss last season, broke a finger on a first-quarter stiff-arm and finished with 5 rushing yards (0.5). Kaleb Johnson took over for "
  "Jacobs and scored 12.8 on Karl's bench, enough to win it. Giants fan mariss got 27.8 from Isaiah Likely and the Giants defense "
  "he picked up this week."),
]
lines = []
for r in RESULTS:
    lines.append(f"  {{ a: {r['a']}, aScore: {r['aScore']:.2f}, b: {r['b']}, bScore: {r['bScore']:.2f}, tag: {repr(r['tag']) if r['tag'] else 'null'},\n    text: {bt(r['text'])} }},")
res_js = ('''// ---------- All 6 Week 9 results. Every number checked against
// docs/data/2026/weekly_boxscores.json (actual + ESPN's pregame
// projected_points), season_moments.json's best_ball weeks, and ESPN's
// Week 9 game summaries (stat lines, injury blocks, play-by-play). Tags
// from build_weekly_recap.py's features. Fandom notes from
// league_rules/owner_nfl_fandom.json. One trade since the Week 8 edition
// (rosters.json owner diff): Ronjan sent Sam Darnold to Imran for
// Marvin Harrison Jr. and Daniel Jones. Injury news: Sean McVay on
// Nacua, Mike LaFleur on Wilson and Knight, Matt LaFleur on Jacobs,
// Mike Macdonald on Darnold, Andy Reid on Mahomes (all 11/9).
const MATCHUP_RESULTS = [
''' + '\n'.join(lines) + '\n];')
js = repl_block(js, "// ---------- All 6 Week 8 results.", "\n];", res_js)

# ---------- injuries from rosters.json, standings order
OWN = {1:'Imran',2:'mariss',3:'Pete',4:'Ben',5:'Cara',6:'Lisette',7:'Mike',8:'Joe',9:'Ronjan',10:'Karl',11:'Kris',12:'Melinda'}
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
// 11/10/2026) is anything other than ACTIVE, any team, any position.
// Teams in standings order.
const INJURIES = [
''' + '\n'.join(inj) + '\n];')
js = repl_block(js, "// ---------- Leaguewide injury audit", "\n];", inj_js)

NOTES = {
 6: "Patrick Mahomes's MRI showed no significant damage to his elbow, and Andy Reid called him day-to-day. Garrett Wilson has a concussion.",
 12: "Bam Knight is still in the concussion protocol, so Jaylen Warren's return from the Steelers' bye comes at the right time.",
 5: "J.J. McCarthy is questionable after getting hurt against Philadelphia and returning.",
 8: "Malik Willis hurt his groin in Miami and is questionable, which would leave Carson Wentz as the only healthy option at OP.",
 7: "TreVeyon Henderson has missed two straight games with an illness.",
 9: "A.J. Brown is out with a knee injury, and Ladd McConkey is questionable with back spasms. Pollard and Ward are back from the bye.",
 2: "Kyler Murray and George Pickens are out with hamstring injuries, and Caleb Williams is on bye, so mariss is down to Geno Smith and Jameis Winston at quarterback.",
 4: "Puka Nacua is likely headed to injured reserve. Justin Herbert is questionable with a finger injury.",
 3: "Michael Wilson is out for the season. David Montgomery is out with a groin injury.",
 11: "Jeremiyah Love went on injured reserve with a high-ankle sprain and is expected to miss four to five weeks. Luther Burden III has a concussion.",
 1: "Sam Darnold will miss a second straight game with quad and rib injuries, and Drew Lock starts again. Jaylen Waddle is in the concussion protocol.",
 10: "Josh Jacobs has surgery this week and could go on injured reserve. Mike Evans is out with Achilles tendinitis.",
}
order = [p['team_id'] for p in pp]
notes_js = ('''// Forward-looking note per team, rendered as a full-width row closing
// that team's group. Only teams with something to say get one. Sources:
// ESPN injury blocks and play-by-play, coaches' 11/9 updates.
const INJ_NOTES = {
''' + '\n'.join(f"  {t}: {bt(NOTES[t])}," for t in order if t in NOTES) + '\n};')
js = repl_block(js, "// Forward-looking note per team", "\n};", notes_js)

std = []
for p in pp:
    back = f"{p['points_back']:.1f}" if p['points_back'] is not None else 'null'
    std.append(f"  {{ team: {p['team_id']},{' ' if p['team_id'] < 10 else ''} wins: {p['wins']}, losses: {p['losses']}, pf: {p['points_for']:.1f}, back: {back} }},")
std_js = ('''// ---------- Current playoff picture, straight from
// docs/data/2026/weekly_recap.json's playoff_picture after Week 9.
const STANDINGS = [
''' + '\n'.join(std) + '\n];')
js = repl_block(js, "// ---------- Current playoff picture", "\n];", std_js)

# ---------- Week 10 preview
PPG = {6:(137.3,1),12:(136.7,2),5:(132.9,3),7:(128.2,4),8:(125.0,5),4:(124.0,6),10:(122.2,7),9:(122.1,8),3:(119.3,9),2:(116.7,10),11:(116.0,11),1:(110.6,12)}
RK = {p['team_id']: (p['rank'], p['wins'], p['losses']) for p in pp}
def tag(t):
    r, w, l = RK[t]; v, k = PPG[t]
    return f"#{r} &middot; {w}-{l}<span class=\"tag-ppg\">{v:.1f} PPG (#{k})</span>"
W10 = [
 dict(a=12, b=11, tag='Game of the Week', games=[(96.50, 93.38)],
      swaps=[("Jacory Croskey-Merritt (RB)", 11, 12, "round: 12")],
      note="Melinda gets first place back with a win if Lisette loses, or if both win and Melinda outscores her by 5.9. Byes hit both lineups. Rome Odunze and Dallas Goedert sit for Melinda, and D'Andre Swift sits for Kris. Melinda won the 2025 meeting 96.5-93.4."),
 dict(a=6, b=1, tag=None, games=[(97.74, 122.62)],
      swaps=[("George Kittle (TE)", 1, 6, "round: 8")],
      note="Lisette keeps first place with a win unless Melinda wins by more. Lisette's George Kittle, who scored 108.7 points for Imran last season, ranks fourth among tight ends this year. Imran loses Jonah Coleman to the Broncos' bye. Imran won the 2025 meeting 122.6-97.7."),
 dict(a=9, b=2, tag=None, games=[(155.54, 114.50)],
      swaps=[("Geno Smith (QB)", 9, 2, "round: 11"), ("Isiah Pacheco (RB)", 2, 9, "round: 15"), ("Keenan Allen (WR)", 2, 9, "how: 'waivers'")],
      note="mariss takes Ronjan's playoff spot only by beating him by 48.0 or more on current points. Geno Smith, Ronjan's quarterback last season, should start for mariss. Keenan Allen scored 126.7 points for mariss last season and now plays for Ronjan. Ronjan won the 2025 meeting 155.5-114.5."),
 dict(a=7, b=10, tag=None, games=[(117.30, 105.14)],
      swaps=[("T.J. Hockenson (TE)", 10, 7, "round: 11")],
      note="Mike stays in the top six whatever happens this week. Karl is without Josh Jacobs, and Courtland Sutton and the Broncos defense are on bye. T.J. Hockenson scored 60.0 points for Karl last season and now backs up Brock Bowers for Mike. Mike won the 2025 meeting 117.3-105.1."),
 dict(a=8, b=4, tag=None, games=[(121.36, 121.46)],
      swaps=[],
      note="Ben plays his first game without Puka Nacua, and Colston Loveland is on bye. Joe has Jalen Hurts on injured reserve and Malik Willis questionable, so Carson Wentz could start at OP. Ben won the 2025 meeting by 0.1 points, 121.5-121.4."),
 dict(a=5, b=3, tag=None, games=[(186.10, 167.74)],
      swaps=[("Rachaad White (RB)", 5, 3, "round: 13"), ("DeMario Douglas (WR)", 5, 3, "how: 'waivers'"), ("Mack Hollins (WR)", 5, 3, "how: 'waivers'"), ("Bucky Irving (RB)", 3, 5, "round: 5")],
      note="Bucky Irving scored 98.1 points for Pete last season and has been a top-five running back for Cara, but Tampa is on bye. Pete has to replace Michael Wilson for the rest of the season. Cara won the 2025 meeting 186.1-167.7."),
]
wl = []
for m in W10:
    g = ', '.join(f"{{ week: 10, aScore: {x:.2f}, bScore: {y:.2f} }}" for x, y in m['games'])
    sw = ',\n             '.join(f"{{ player: {json.dumps(p)}, from: {f}, to: {t}, {k} }}" for p, f, t, k in m['swaps'])
    tg = f"tag: '{m['tag']}', " if m['tag'] else ''
    wl.append(f"  {{ a: {m['a']}, {tg}aTag: '{tag(m['a'])}', b: {m['b']}, bTag: '{tag(m['b'])}',\n    games: [{g}],\n    swaps: [ {sw} ],\n    note: {bt(m['note'])} }},")
w_js = ('''// ---------- Week 10 preview. 2025 head-to-head from
// docs/data/2025/matchups.json: every pair met once in the 2025 regular
// season (Week 10). Joe and Ben's Weeks 16-17 games were consolation
// games and don't count. Swaps by player_id, 2025 final rosters vs
// current 2026 rosters, D/ST and K excluded; `round` = 2026 draft
// round, `how` replaces it when the player arrived another way. Byes
// (CHI, DEN, PHI, TB) from ESPN's Week 10 scoreboard. Ordered by
// stakes, Game of the Week first. Stakes from enumerating all 64 Week
// 10 outcomes against playoff_picture (wins, then points_for). PPG =
// points_for / 9, rank among 12. Position ranks are 2026 season points.
const WEEK10_MATCHUPS = [
''' + '\n'.join(wl) + '\n];')
js = repl_block(js, "// ---------- Week 9 preview.", "\n];", w_js)
js = js.replace('function renderWeek9Matchup(m)', 'function renderWeek10Matchup(m)')
js = js.replace("document.getElementById('week9-matchup-grid').innerHTML = WEEK9_MATCHUPS.map(renderWeek9Matchup).join('');",
                "document.getElementById('week10-matchup-grid').innerHTML = WEEK10_MATCHUPS.map(renderWeek10Matchup).join('');")
assert 'WEEK9' not in js and 'Week9' not in js, [l for l in js.splitlines() if 'eek9' in l.replace('Week 9','')]
src = src[:j_start] + js + src[j_end:]
open(P, 'w').write(src)
print('ok')
# (applied after build) masthead + tab label
