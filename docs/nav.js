// Single source of truth for the site nav, so every page renders the same
// items in the same order - the alternative (each page hand-rolling its own
// resources array) is exactly what let the four pages drift out of sync.
// Convention follows fakeronjan.com's navbar: internal links first (current
// page marked .active), external links after (marked with a nav-arrow and
// opened in a new tab) - see fakeronjan-com/src/_includes/base.njk.
const NAV_INTERNAL = [
  { key: 'weekly-news', label: 'Weekly News', href: 'index.html' },
  { key: 'draft-recap', label: '2026 Draft Recap', href: 'draft-recap.html' },
  { key: 'draft-guide', label: '2026 Draft Guide', href: 'draft-guide.html' },
  { key: 'keeper-dossier', label: '2026 Keeper Dossier', href: 'keeper-dossier.html' },
  { key: 'season-2025', label: '2025 Season Recap', href: 'season-2025.html' },
  { key: 'league-rules', label: 'League Rules', href: 'league-rules.html' },
];

const NAV_EXTERNAL = [
  { label: 'ESPN League Home', hrefFn: (leagueId) => `https://fantasy.espn.com/football/league?leagueId=${leagueId}` },
];

function renderNav(currentKey, leagueId) {
  const internal = NAV_INTERNAL.map(item =>
    `<a href="${item.href}"${item.key === currentKey ? ' class="active"' : ''}>${item.label}</a>`
  );
  const external = NAV_EXTERNAL.map(item => {
    const href = item.hrefFn ? item.hrefFn(leagueId) : item.href;
    return `<a href="${href}" target="_blank" rel="noopener">${item.label}<span class="nav-arrow">&#8599;</span></a>`;
  });
  return [...internal, ...external].join('<span class="nav-sep">&middot;</span>');
}
