# Week 10 edition builder (11/17/2026), kept as a template for writing the current panel from data + prose.
"""Write the Week 10 Recap / Week 11 Preview into the current panel of docs/index.html."""
import json, re
R = '/Users/ronjan/code/fakeronjan/games/just-stream-it/'
P = R + 'docs/index.html'
src = open(P).read()

# ================= HTML =================
h_start = src.index('  <!-- ================= CURRENT EDITION: Week 9 Recap / Week 10 Preview ================= -->')
h_stat = src.index('    <div class="section-label" id="sec-statbook">')
LEDE1 = ("Four weeks to go, and the middle of the standings just crashed into itself. Every team from third place to sixth "
         "lost in Week 10. Cara and Joe slid to 6-4, Mike and Ronjan tumbled to 5-5, and mariss caught them by knocking "
         "off Ronjan. That leaves five teams within one game of each other, with Ben and Pete lurking one game back at 4-6. Up "
         "top, Lisette and Melinda pulled away. Both won by more than 55 to reach 8-2, two games clear in the race for the two byes.")
LEDE2 = ("The middle found creative ways to lose. Ronjan put up 156.7 against mariss and still came up short, the most any team has scored "
         "in a defeat all season. Cara watched Drake Maye go down on New England's first drive in Munich while J.J. McCarthy and "
         "Kirk Cousins piled up 32.5 on her bench, and Pete escaped with 110.5. Mike stuck a receiver in his OP slot and fell to "
         "last-place Karl. Now the pileup turns into a demolition derby. Mike plays Ronjan, Ben faces mariss, and if the "
         "season ended after Week 11, both winners would be in and both losers would be out.")
INJ_INTRO = ("It was a brutal week in the trainer's room. Drake Maye's ankle is the worst of it. Malik Willis joined Jalen Hurts "
             "on injured reserve, Jordan Addison needs thumb surgery, and Woody Marks is in the concussion protocol.")
BB = ("Cara blew the only game of Week 10, her second of the season. Her lineup captured just 77.4% of its possible points, the "
      "worst of the week, and she's dead last in efficiency at 83.4%. Joe still leads the league at 93.7%. Karl's best lineups "
      "would have him at 6-4 instead of 3-7, while Ronjan and mariss have each banked two more wins than their optimal lineups earned.")
html_new = f'''  <!-- ================= CURRENT EDITION: Week 10 Recap / Week 11 Preview ================= -->
  <section class="edition" id="panel-current">
    <nav class="section-nav" aria-label="Sections"><a href="#sec-watch">Watch</a><a href="#sec-results">Week 10 Results</a><a href="#sec-standings">Standings</a><a href="#sec-week11">Week 11 Preview</a><a href="#sec-injuries">Injuries</a><a href="#sec-statbook">Statbook</a></nav>
    <p class="kicker">Week 10 Recap</p>
    <h2 class="edition-head">It&rsquo;s a Pileup!</h2>
    <p class="dateline">2026 Season &middot; Week 10 Complete &middot; Week 11 Preview Below</p>
    <p class="lede">{LEDE1}</p>
    <p class="lede">{LEDE2}</p>

    <a class="watch-card" id="sec-watch" href="just-scream-it.html?week=10">
      <span class="watch-thumb"><img src="just-scream-it/thumb_week10.jpg" alt=""><span class="watch-play"></span></span>
      <span class="watch-text">
        <span class="watch-kicker">Now showing &middot; 8:42</span>
        <span class="watch-head">Just Scream It</span>
        <span class="watch-dek">The pundits recap Week 10 and pick every Week 11 game.</span>
      </span>
    </a>

    <div class="section-label" id="sec-results">Week 10 Results</div>
    <div class="matchup-grid" id="recap-matchup-grid"></div>

    <div class="section-label" id="sec-standings">Playoff Picture</div>
    <p class="section-sublabel">Standings through ten weeks</p>
    <div class="standings-list" id="standings-list"></div>
    <p class="standings-caption">Top 6 make the playoffs &middot; back column shown only when tied in wins</p>

    <div class="section-label" id="sec-week11">Week 11 Matchups</div>
    <p class="section-sublabel">Rosters, 2025 head-to-head, and Familiar Faces</p>
    <div class="matchup-grid" id="week11-matchup-grid"></div>

    <div class="section-label" id="sec-injuries">The Injury Report</div>
    <p class="section-sublabel">Who's hurt heading into Week 11</p>
    <p class="lede" style="font-size:0.95rem;">{INJ_INTRO}</p>
    <div id="injury-list"></div>

'''
src = src[:h_start] + html_new + src[h_stat:]
bb_old = re.search(r'(<h3 class="stat-subhead">Best Ball</h3>\n    <p class="lede" style="font-size:0.95rem;">)(.*?)(</p>)', src[h_start:], re.S)
a = h_start + bb_old.start(2); b = h_start + bb_old.end(2)
src = src[:a] + BB + src[b:]
src = src.replace('<button class="edition-tab active" data-panel="panel-current" type="button">Week 9 Recap</button>',
                  '<button class="edition-tab active" data-panel="panel-current" type="button">Week 10 Recap</button>', 1)
src = src.replace('      <span>Week 9 Edition</span>', '      <span>Week 10 Edition</span>', 1)
src = re.sub(r'<meta name="description" content="The Nielson News Week \d+ Recap with standings, the injury report, and every Week \d+ matchup.">',
             '<meta name="description" content="The Nielson News Week 10 Recap with standings, the injury report, and every Week 11 matchup.">', src, 1)

# ================= JS =================
j_start = src.index('/* ============================================================\n   CURRENT EDITION: Week 9 Recap / Week 10 Preview')
j_end = src.index('/* ============================================================\n   STATBOOK')
js = src[j_start:j_end]
js = js.replace('CURRENT EDITION: Week 9 Recap / Week 10 Preview', 'CURRENT EDITION: Week 10 Recap / Week 11 Preview', 1)

def repl_block(js, start_marker, end_marker, new):
    s = js.index(start_marker); e = js.index(end_marker, s) + len(end_marker)
    return js[:s] + new + js[e:]

def bt(s):
    assert '`' not in s and '${' not in s
    return '`' + s + '`'

RESULTS = [
 dict(a=3, aScore=110.54, b=5, bScore=106.18, tag='Game of the Week', text=
  "Beard Al (Pete) beat Team Kantastrophe (Cara) 110.5-106.2 because Cara lost her quarterback on the first drive. Drake Maye "
  "went down on a sack in Munich and finished with 3.0, while J.J. McCarthy (17.1) and Kirk Cousins (15.4) sat on her "
  "bench. Her best lineup would have scored 137.2. Bills fan Pete got two rushing touchdowns from Josh Allen and 21.0 from the "
  "Vikings defense in a 30-10 win at Green Bay. Eagles fan Cara also had to watch a Cowboy, Ryan Flournoy, catch a touchdown for Pete (16.1)."),
 dict(a=12, aScore=168.92, b=11, bScore=103.16, tag='Blowout of the Week', text=
  "Buffalo Abusement Park (Melinda) beat Rice Rice Baby (Kris) 168.9-103.2 with two quarterbacks who threw for almost 800 "
  "yards. Joe Burrow passed for 409 yards and 4 touchdowns (33.2), Ja'Marr Chase caught 11 passes for 231 yards (28.6), and "
  "Brock Purdy threw for 389 yards (31.7) in San Francisco's 46-40 win in Dallas. Bills fan Melinda added 157 rushing yards "
  "from James Cook (21.7). Kris lost Woody Marks to a concussion in the third quarter, and Seth McGowan, the back he picked up "
  "after Ben dropped him, scored 13.7 on his bench."),
 dict(a=10, aScore=127.32, b=7, bScore=106.06, tag='Upset Alert', text=
  "The Aristocrats (Karl) beat Terrible Towels (Mike) 127.3-106.1 because Mike had no second quarterback. Deshaun Watson's "
  "return from a concussion sent Shedeur Sanders back to Cleveland's bench, and Jaxson Dart is on injured reserve, so Mike "
  "started receiver Jalen Coker at OP for 0.3. Brock Bowers hurt his ankle in the first quarter and finished with 2.8. Cowboys "
  "fan Karl got 46.4 from two Cowboys. Dak Prescott threw 5 touchdowns (34.4) in the shootout with San Francisco, and Brandon "
  "Aubrey kicked for 12.0. Karl came in last and beat the fifth-place team for his third win."),
 dict(a=2, aScore=170.12, b=9, bScore=156.70, tag='Plot Twist', text=
  "Mednis Madness (mariss) beat Gibbs-n Them the Business (Ronjan) 170.1-156.7 by scoring 63.1 more than ESPN projected, the "
  "biggest gap of the week. Giants fan mariss got 48.9 from two Giants, Cam Skattebo (25.7) and Isaiah Likely (23.2), but his "
  "top scorer was a Cowboy. George Pickens had 11 catches, 145 yards, and 3 touchdowns (38.0). Jahmyr Gibbs piled up 252 "
  "yards and 2 touchdowns (40.7) for Ronjan, and Trevor Lawrence threw 3 more (26.8). Ronjan's 156.7 broke the record for a "
  "losing score that Melinda set a week earlier."),
 dict(a=4, aScore=170.54, b=8, bScore=126.72, tag=None, text=
  "Conquering Heroes (Ben) beat Olave Oyl (Joe) 170.5-126.7 with the week's top score, in his first game without Puka "
  "Nacua. Kenneth Walker III sat out with a groin injury, and Emmett Johnson, the Chiefs back Ben picked up, replaced him with "
  "171 yards and 2 receiving touchdowns (32.1). Parker Washington caught 7 passes for 152 yards (24.7), and Blake Corum ran for "
  "100 (19.4). Joe got 44.2 from Amon-Ra St. Brown and Jared Goff, the pair he traded for in October. With Jalen Hurts and "
  "Malik Willis on injured reserve, he started Derrick Henry at OP (16.5)."),
 dict(a=6, aScore=163.62, b=1, bScore=105.88, tag='Stud of the Week', text=
  "Mahomes is where the heart is (Lisette) beat Sophomore Slump (Imran) 163.6-105.9 behind three 49ers. Christian McCaffrey "
  "caught 4 passes for 161 yards and scored 3 touchdowns (44.3), and Deebo Samuel Sr. (24.4) and George Kittle (10.4) added "
  "34.8 in the win over Dallas. The team's namesake threw for 348 yards and 5 touchdowns (35.4) a week after his elbow "
  "MRI. Imran got 27.1 from Jaxon Smith-Njigba, but his lineup came in 24.7 under its projection, and only Kris scored less."),
]

# ---- punched-up copy (11/17, Ronjan: "punch everything up")
CARD = {
 3: "Beard Al (Pete) stole one from Team Kantastrophe (Cara), 110.5-106.2, and the heist started on the first drive. Drake Maye went down on a sack in Munich and left with 3.0, while J.J. McCarthy (17.1) and Kirk Cousins (15.4) sat on Cara's bench. Her best lineup would have hung 137.2. Bills fan Pete rode two Josh Allen rushing touchdowns and 21.0 from a Vikings defense that smothered Green Bay 30-10. To rub it in, Eagles fan Cara had to watch a Cowboy, Ryan Flournoy, catch a touchdown for Pete (16.1).",
 12: "Buffalo Abusement Park (Melinda) ran Rice Rice Baby (Kris) off the field, 168.9-103.2, with a full-blown air raid. Joe Burrow threw for 409 yards and 4 touchdowns (33.2), Ja'Marr Chase torched Pittsburgh for 231 yards on 11 catches (28.6), and Brock Purdy chipped in a casual 389 yards (31.7) in San Francisco's 46-40 track meet in Dallas. Bills fan Melinda even squeezed 157 rushing yards out of James Cook (21.7). Kris lost Woody Marks to a concussion in the third quarter, and Seth McGowan, fresh off Ben's scrap heap, scored 13.7 on the bench.",
 10: "The Aristocrats (Karl) finally got one, 127.3-106.1, and Terrible Towels (Mike) practically handed it over. Deshaun Watson's return from a concussion sent Shedeur Sanders back to Cleveland's bench, and Jaxson Dart is on injured reserve, so Mike plugged receiver Jalen Coker into his OP slot. Coker scored 0.3. Brock Bowers hurt his ankle early and managed 2.8. Cowboys fan Karl cashed in 46.4 from his own team: 5 touchdown passes from Dak Prescott (34.4) and 12.0 from Brandon Aubrey's leg. Last place beat fifth place, and Karl has his third win.",
 2: "Mednis Madness (mariss) went nuclear, beating Gibbs-n Them the Business (Ronjan) 170.1-156.7 and blowing past ESPN's projection by 63.1, the biggest gap of the week. Giants fan mariss got 48.9 from two Giants, Cam Skattebo (25.7) and Isaiah Likely (23.2). His MVP was a Cowboy, though. George Pickens hauled in 11 catches for 145 yards and 3 touchdowns (38.0). Jahmyr Gibbs racked up 252 yards and 2 scores (40.7) for Ronjan, and Trevor Lawrence threw 3 more (26.8). All Ronjan got for it was a record nobody wants, breaking the mark for points in a loss that Melinda set a week ago.",
 4: "Conquering Heroes (Ben) played his first game without Puka Nacua and hung the week's top score on Olave Oyl (Joe), 170.5-126.7. When Kenneth Walker III sat with a groin injury, Ben's other Chiefs back, waiver pickup Emmett Johnson, grabbed the job and ran wild for 171 yards and 2 receiving touchdowns (32.1). Parker Washington shredded Tennessee for 152 yards (24.7). Joe's October trade haul held up its end with 44.2 from Amon-Ra St. Brown and Jared Goff, but with Jalen Hurts and Malik Willis on injured reserve, Joe had to start Derrick Henry at OP (16.5).",
 6: "Mahomes is where the heart is (Lisette) turned into a 49ers fan club and flattened Sophomore Slump (Imran), 163.6-105.9. Christian McCaffrey went off for 161 receiving yards and 3 scores (44.3), the best day of anyone in the league, and Deebo Samuel Sr. (24.4) and George Kittle (10.4) added 34.8 more. The team's namesake was pretty good too. Patrick Mahomes threw for 348 yards and 5 touchdowns (35.4) a week after his elbow MRI. Jaxon Smith-Njigba gave Imran 27.1, but the rest of the lineup came in 24.7 under projection, and only Kris scored less.",
}
for r in RESULTS: r['text'] = CARD[r['a']]
lines = []
for r in RESULTS:
    lines.append(f"  {{ a: {r['a']}, aScore: {r['aScore']:.2f}, b: {r['b']}, bScore: {r['bScore']:.2f}, tag: {repr(r['tag']) if r['tag'] else 'null'},\n    text: {bt(r['text'])} }},")
res_js = ('''// ---------- All 6 Week 10 results. Every number checked against
// docs/data/2026/weekly_boxscores.json (actual + ESPN's pregame
// projected_points), season_moments.json's best_ball weeks, and ESPN's
// Week 10 game summaries (stat lines, injury blocks, play-by-play). Tags
// from build_weekly_recap.py's features. Fandom notes from
// league_rules/owner_nfl_fandom.json. No trades since the Week 9
// edition (rosters.json owner diff); Seth McGowan went from Ben to Kris
// on waivers. Injury news: ESPN and AP on Maye (11/16), Jeff Hafley on
// Willis, Kevin O'Connell on Addison, Klint Kubiak on Bowers, DeMeco
// Ryans on Marks.
const MATCHUP_RESULTS = [
''' + '\n'.join(lines) + '\n];')
js = repl_block(js, "// ---------- All 6 Week 9 results.", "\n];", res_js)

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
// 11/17/2026) is anything other than ACTIVE, any team, any position.
// Teams in standings order.
const INJURIES = [
''' + '\n'.join(inj) + '\n];')
js = repl_block(js, "// ---------- Leaguewide injury audit", "\n];", inj_js)

NOTES = {
 12: "Kyle Monangai is questionable, and Jacory Croskey-Merritt is on injured reserve.",
 5: "Drake Maye stayed in Germany for more tests, and the Patriots fear a broken ankle that would end his season. Matthew Stafford is on bye, so McCarthy and Cousins start.",
 8: "Malik Willis is on injured reserve with a core muscle injury and misses at least three more games. With Hurts out too, Jared Goff is Joe's only starting quarterback.",
 7: "Brock Bowers returned after hurting his ankle, and Klint Kubiak said it's not as bad as they feared. Jaxson Dart is still on injured reserve, and Davante Adams is out following hamstring surgery.",
 9: "A.J. Brown left the Munich game hurt and is questionable, though the Patriots are on bye anyway. Ladd McConkey and Marvin Harrison Jr. carry the same tag.",
 2: "Kevin O'Connell said Jordan Addison will miss a few weeks. Geno Smith hurt his ankle, returned, and is questionable. Kyler Murray is still out.",
 4: "Puka Nacua remains on injured reserve. Kenneth Walker III is questionable after missing Week 10.",
 10: "Josh Jacobs is still out after finger surgery. Mike Evans and Carnell Tate are questionable.",
 11: "Woody Marks has a concussion, and DeMeco Ryans doesn't expect him back for Thursday's game against the Colts. Lamar Jackson and Jeremiyah Love are still on injured reserve.",
 1: "Sam Darnold is out again with a quad injury, and Seattle is on bye. Jaylen Waddle and Omar Cooper Jr. are questionable.",
}
order = [p['team_id'] for p in pp]
notes_js = ('''// Forward-looking note per team, rendered as a full-width row closing
// that team's group. Only teams with something to say get one. Sources:
// ESPN injury blocks and play-by-play, coaches' 11/16 updates.
const INJ_NOTES = {
''' + '\n'.join(f"  {t}: {bt(NOTES[t])}," for t in order if t in NOTES) + '\n};')
js = repl_block(js, "// Forward-looking note per team", "\n};", notes_js)

std = []
for p in pp:
    back = f"{p['points_back']:.1f}" if p['points_back'] is not None else 'null'
    std.append(f"  {{ team: {p['team_id']},{' ' if p['team_id'] < 10 else ''} wins: {p['wins']}, losses: {p['losses']}, pf: {p['points_for']:.1f}, back: {back} }},")
std_js = ('''// ---------- Current playoff picture, straight from
// docs/data/2026/weekly_recap.json's playoff_picture after Week 10.
const STANDINGS = [
''' + '\n'.join(std) + '\n];')
js = repl_block(js, "// ---------- Current playoff picture", "\n];", std_js)

# ---------- Week 11 preview
ppg_sorted = sorted(pp, key=lambda p: -p['points_for'])
PPG = {p['team_id']: (p['points_for'] / 10, i + 1) for i, p in enumerate(ppg_sorted)}
RK = {p['team_id']: (p['rank'], p['wins'], p['losses']) for p in pp}
def tag(t):
    r, w, l = RK[t]; v, k = PPG[t]
    return f"#{r} &middot; {w}-{l}<span class=\"tag-ppg\">{v:.1f} PPG (#{k})</span>"
W11 = [
 dict(a=9, b=7, tag='Game of the Week', games=[(99.52, 139.34)],
      swaps=[("Tre Tucker (WR)", 7, 9, "round: 16"), ("Davante Adams (WR)", 9, 7, "how: 'via Ben'")],
      note="Whoever wins holds a playoff spot on current points, and whoever loses falls to seventh or lower. Byes take A.J. Brown and Cooper Kupp from Ronjan and Christian Watson from Mike. Jayden Daniels is Mike's only healthy starting quarterback. Mike won the 2025 meeting 139.3-99.5."),
 dict(a=4, b=2, tag=None, games=[(124.18, 96.20)],
      swaps=[("Omarion Hampton (RB)", 4, 2, "round: 2")],
      note="A win puts mariss in the top six. A win puts Ben there too on current points, since he has outscored Mike, Ronjan, and mariss. Ben loses Blake Corum, Zach Charbonnet, and Michael Penix Jr. to byes, and mariss plays without Jordan Addison and KC Concepcion. Ben won the 2025 meeting 124.2-96.2."),
 dict(a=5, b=6, tag=None, games=[(127.04, 137.64)],
      swaps=[("Garrett Wilson (WR)", 5, 6, "round: 4"), ("Rico Dowdle (RB)", 6, 5, "round: 8"), ("Chris Rodriguez Jr. (RB)", 6, 5, "round: 16"),
             ("Devaughn Vele (WR)", 6, 5, "round: 18"), ("Malik Washington (WR)", 6, 5, "how: 'waivers'")],
      note="Lisette keeps first place with a win. Cara stays in the top six whatever happens. Rico Dowdle scored 176.0 points for Lisette last season and ranks 44th among running backs for Cara. Lisette loses Jordan Love and Matthew Golden to Green Bay's bye. Lisette won the 2025 meeting 137.6-127.0."),
 dict(a=3, b=12, tag=None, games=[(149.78, 126.70)],
      swaps=[("Rome Odunze (WR)", 3, 12, "round: 5"), ("Rashid Shaheed (WR)", 3, 12, "round: 14")],
      note="Melinda moves into first with a win if Lisette loses, or if both come out on top and Melinda outscores her by more than 0.5. Rome Odunze scored 124.1 points for Pete last season and now plays for Melinda. Pete loses Kyren Williams and Drake London to byes. Pete won the 2025 meeting 149.8-126.7."),
 dict(a=1, b=8, tag=None, games=[(112.06, 110.66)],
      swaps=[("Malik Willis (QB)", 1, 8, "round: 6"), ("Jaxon Smith-Njigba (WR)", 8, 1, "how: 'via Joe'"), ("Javonte Williams (RB)", 8, 1, "how: 'via Joe'")],
      note="Joe holds his playoff spot this week no matter what. It's the first meeting since Joe traded Jaxon Smith-Njigba and Javonte Williams to Imran. Smith-Njigba scored 289.0 points for Joe last season and has the most points of any receiver this year, but Seattle's bye takes him, Drew Lock, and Jadarian Price out of Imran's lineup. Imran won the 2025 meeting 112.1-110.7."),
 dict(a=11, b=10, tag=None, games=[(94.76, 137.38)],
      swaps=[("Dak Prescott (QB)", 11, 10, "round: 2"), ("D'Andre Swift (RB)", 10, 11, "round: 5"), ("Hollywood Brown (WR)", 10, 11, "how: 'waivers'")],
      note="Both teams are two games out of the top six with four weeks left. Dak Prescott scored 282.1 points for Kris last season and ranks fourth among quarterbacks for Karl. D'Andre Swift went the other way after posting 206.3 for Karl, and he's 12th among backs this year. Byes take Bijan Robinson from Karl and Quinshon Judkins from Kris. Karl won the 2025 meeting 137.4-94.8."),
]

NOTE = {
 9: "Win and you're in the top six heading into Week 12. Lose and you're on the outside looking in. Byes thin out both lineups: A.J. Brown and Cooper Kupp sit for Ronjan, and Mike loses Christian Watson. Mike also has exactly one healthy starting quarterback in Jayden Daniels, so keep an eye on his OP slot. Mike won the 2025 meeting 139.3-99.5.",
 4: "Another play-in game. mariss jumps into the top six with a win. So does Ben, since he's outscored Mike, Ronjan, and mariss and would win the points tiebreaker. Meanwhile, byes gut Ben's lineup, taking Blake Corum, Zach Charbonnet, and Michael Penix Jr. mariss plays without Jordan Addison and KC Concepcion. Ben won the 2025 meeting 124.2-96.2.",
 5: "A win keeps Lisette in first place. Cara is safe in the top six this week either way, and she gets a reunion with Rico Dowdle, who scored 176.0 points for Lisette last season and ranks 44th among running backs for Cara. Green Bay's bye costs Lisette Jordan Love and Matthew Golden. Lisette won the 2025 meeting 137.6-127.0.",
 3: "Melinda grabs first place with a win if Lisette stumbles, or if both come out on top and Melinda outscores her by more than half a point. Pete is fresh off the upset but loses Kyren Williams and Drake London to byes. Rome Odunze, 124.1 points for Pete last season, now lines up against him. Pete won the 2025 meeting 149.8-126.7.",
 1: "Joe holds his playoff spot this week no matter what. It's the first meeting since Joe shipped Jaxon Smith-Njigba and Javonte Williams to Imran. Smith-Njigba scored 289.0 points for Joe last season and leads every receiver this year, so the revenge game writes itself. Except it doesn't. Seattle is on bye, and Smith-Njigba, Drew Lock, and Jadarian Price all sit. Imran won the 2025 meeting 112.1-110.7.",
 11: "Both teams are two games out with four to play, so neither can afford a loss. Dak Prescott scored 282.1 points for Kris last season and just threw 5 touchdowns for Karl. D'Andre Swift went the other way after posting 206.3 for Karl, and he's 12th among backs this year. Byes take Bijan Robinson from Karl and Quinshon Judkins from Kris. Karl won the 2025 meeting 137.4-94.8.",
}
for m in W11: m['note'] = NOTE[m['a']]
wl = []
for m in W11:
    g = ', '.join(f"{{ week: 11, aScore: {x:.2f}, bScore: {y:.2f} }}" for x, y in m['games'])
    sw = ',\n             '.join(f"{{ player: {json.dumps(p)}, from: {f}, to: {t}, {k} }}" for p, f, t, k in m['swaps'])
    tg = f"tag: '{m['tag']}', " if m['tag'] else ''
    wl.append(f"  {{ a: {m['a']}, {tg}aTag: '{tag(m['a'])}', b: {m['b']}, bTag: '{tag(m['b'])}',\n    games: [{g}],\n    swaps: [ {sw} ],\n    note: {bt(m['note'])} }},")
w_js = ('''// ---------- Week 11 preview. 2025 head-to-head from
// docs/data/2025/matchups.json: every pair met once in the 2025 regular
// season (Week 11). Swaps by player_id, 2025 final rosters vs current
// 2026 rosters, D/ST and K excluded; `round` = 2026 draft round, `how`
// replaces it when the player arrived another way. Byes (ATL, CLE, GB,
// LAR, NE, SEA) from ESPN's Week 11 scoreboard. Ordered by stakes, Game
// of the Week first. Stakes from enumerating all 64 Week 11 outcomes
// against playoff_picture (wins, then points_for). PPG = points_for /
// 10, rank among 12. Position ranks are 2026 season points.
const WEEK11_MATCHUPS = [
''' + '\n'.join(wl) + '\n];')
js = repl_block(js, "// ---------- Week 10 preview.", "\n];", w_js)
js = js.replace('function renderWeek10Matchup(m)', 'function renderWeek11Matchup(m)')
js = js.replace("document.getElementById('week10-matchup-grid').innerHTML = WEEK10_MATCHUPS.map(renderWeek10Matchup).join('');",
                "document.getElementById('week11-matchup-grid').innerHTML = WEEK11_MATCHUPS.map(renderWeek11Matchup).join('');")
assert 'WEEK10' not in js and 'Week10' not in js and 'week10' not in js, [l for l in js.splitlines() if 'eek10' in l.replace('Week 10', '')]
src = src[:j_start] + js + src[j_end:]
open(P, 'w').write(src)
print('ok')
