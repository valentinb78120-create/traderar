/* ── TradeRadar · app.js ────────────────────────────────────────────── */

const API = '';   // même origine

// ── État global ──────────────────────────────────────────────────────
const state = {
  stocks: [],
  movers: { gainers: [], losers: [] },
  news: [],
  emerging: [],
  crypto: [],
  watchlist: [],
  all: [],
  trOnly:  localStorage.getItem('tr_only')  === '1',
  eurMode: localStorage.getItem('eur_mode') === '1',
  forex: { EUR: 1.0 },
};

// ── Toggle EUR ───────────────────────────────────────────────────────
function toggleEUR() {
  state.eurMode = !state.eurMode;
  localStorage.setItem('eur_mode', state.eurMode ? '1' : '0');
  updateEURButton();
  rerenderAll();
}
function updateEURButton() {
  const b = document.getElementById('eurToggleBtn');
  if (b) b.classList.toggle('active', state.eurMode);
}
async function loadCryptoGlobal() {
  try {
    const r = await fetch(`${API}/api/crypto-global`);
    const j = await r.json();
    if (j.status === 'ok') renderCryptoGlobal(j.data);
  } catch {}
}

function renderCryptoGlobal(d) {
  const bar = document.getElementById('cryptoGlobalBar');
  if (!bar || !d || !d.total_market_cap_eur) return;
  const btc = d.btc_dominance || 0;
  const eth = d.eth_dominance || 0;
  const other = Math.max(0, 100 - btc - eth);
  const changeCls = d.market_cap_change_24h >= 0 ? 'pos' : 'neg';
  bar.innerHTML = `
    <div class="cg-item">
      <span class="cg-label">Cap. totale</span>
      <span class="cg-val">${fmtCap(d.total_market_cap_eur, 'EUR')}</span>
    </div>
    <div class="cg-item">
      <span class="cg-label">Variation 24h</span>
      <span class="cg-val ${changeCls}">${fmtChange(d.market_cap_change_24h)}</span>
    </div>
    <div class="cg-item">
      <span class="cg-label">Volume 24h</span>
      <span class="cg-val">${fmtCap(d.total_volume_eur, 'EUR')}</span>
    </div>
    <div class="cg-item">
      <span class="cg-label">BTC Dominance</span>
      <span class="cg-val" style="color:#f7931a">${btc.toFixed(1)} %</span>
    </div>
    <div class="cg-item">
      <span class="cg-label">ETH Dominance</span>
      <span class="cg-val" style="color:#627eea">${eth.toFixed(1)} %</span>
    </div>
    <div class="cg-item" style="flex:1;min-width:200px">
      <span class="cg-label">Répartition</span>
      <div class="cg-dominance-bar" title="BTC ${btc.toFixed(1)}% · ETH ${eth.toFixed(1)}% · Autres ${other.toFixed(1)}%">
        <div class="cg-dom-btc" style="width:${btc}%"></div>
        <div class="cg-dom-eth" style="width:${eth}%"></div>
        <div class="cg-dom-other" style="width:${other}%"></div>
      </div>
    </div>
  `;
}

async function loadCalendar() {
  try {
    const r = await fetch(`${API}/api/calendar`);
    const j = await r.json();
    if (j.status === 'ok') renderCalendar(j.data);
  } catch {
    document.getElementById('ecoCalendarList').innerHTML = '<div class="error-card">Indisponible</div>';
    document.getElementById('earningsCalendarList').innerHTML = '<div class="error-card">Indisponible</div>';
  }
}

function fmtCalDate(ts) {
  if (!ts) return '';
  const d = typeof ts === 'string' ? new Date(ts) : new Date(ts);
  return d.toLocaleDateString('fr-FR', { weekday: 'short', day: '2-digit', month: 'short' });
}

// Cache des évènements éco indexé pour le clic
let _ecoData = [];

function renderCalendar(data) {
  const eco = data.economic || [];
  const earnings = (data.earnings || [])
    // Filtrer : ne garder que ceux avec au moins un EPS estimé (vraies earnings suivies)
    .filter(e => e.epsEst != null || e.revEst != null);

  _ecoData = eco;

  // Évènements éco — triés par date puis impact
  const impRank = { high: 0, medium: 1, low: 2 };
  const ecoSorted = [...eco].sort((a, b) => {
    const ta = new Date(a.time || 0).getTime();
    const tb = new Date(b.time || 0).getTime();
    if (ta !== tb) return ta - tb;
    return (impRank[(a.impact||'').toLowerCase()] || 9) - (impRank[(b.impact||'').toLowerCase()] || 9);
  });

  const ecoEl = document.getElementById('ecoCalendarList');
  if (!ecoSorted.length) {
    ecoEl.innerHTML = '<div class="modal-news-empty">Aucun évènement à venir</div>';
  } else {
    ecoEl.innerHTML = ecoSorted.slice(0, 100).map((e, i) => {
      const impact = (e.impact || '').toLowerCase();
      const impCls = impact === 'high' ? 'high' : impact === 'medium' ? 'medium' : 'low';
      return `
        <div class="cal-row" data-idx="${i}" onclick="toggleEcoDetail(${i})" style="animation-delay:${i*0.02}s">
          <span class="cal-date">${fmtCalDate(e.time)}</span>
          <span class="cal-country">${esc(e.country || '—')}</span>
          <span class="cal-event">${esc(e.event || '')}</span>
          <span class="cal-impact ${impCls}">${esc(e.impact || '')}</span>
        </div>`;
    }).join('');
    _ecoData = ecoSorted.slice(0, 50);
  }

  // Earnings — filtré
  const eaEl = document.getElementById('earningsCalendarList');
  if (!earnings.length) {
    eaEl.innerHTML = '<div class="modal-news-empty">Aucune publication à venir avec données suivies</div>';
  } else {
    const hourLabel = { bmo: '🌅 AVANT', amc: '🌙 APRÈS', dmh: '🕐 JOURNÉE' };
    eaEl.innerHTML = earnings.slice(0, 100).map((e, i) => {
      const eps = e.epsEst != null ? e.epsEst.toFixed(2) : '—';
      const rev = e.revEst ? fmtCap(e.revEst, 'USD') : '—';
      const starred = isInWatchlist(e.symbol);
      return `
        <div class="cal-earnings-row" style="animation-delay:${i*0.02}s;grid-template-columns:80px 1fr auto auto auto" onclick="openStockDetail('${esc(e.symbol)}')">
          <span class="cal-date">${fmtCalDate(e.date)}</span>
          <span class="cal-symbol">${esc(e.symbol)}</span>
          <span class="cal-hour">${hourLabel[e.hour] || ''}</span>
          <span class="cal-eps">EPS&nbsp;${eps} · Rev&nbsp;${rev}</span>
          <span onclick="event.stopPropagation();toggleWatchlist('${esc(e.symbol)}','${esc(e.symbol)}')" style="cursor:pointer;color:${starred?'var(--yellow)':'var(--text-muted)'};font-size:14px;padding:0 6px" title="${starred ? 'Retirer' : 'Ajouter aux favoris'}">${starred?'★':'☆'}</span>
        </div>`;
    }).join('');
  }
}

function toggleEcoDetail(idx) {
  const row = document.querySelector(`.cal-row[data-idx="${idx}"]`);
  if (!row) return;
  const next = row.nextElementSibling;
  if (next && next.classList.contains('cal-detail')) {
    next.remove();
    row.classList.remove('expanded');
    return;
  }
  // Ferme les autres détails
  document.querySelectorAll('.cal-detail').forEach(d => d.remove());
  document.querySelectorAll('.cal-row.expanded').forEach(r => r.classList.remove('expanded'));

  const e = _ecoData[idx];
  if (!e) return;
  const fmt = v => v == null || v === '' ? '—' : `${v}${e.unit ? ' ' + e.unit : ''}`;
  const detail = document.createElement('div');
  detail.className = 'cal-detail';
  detail.innerHTML = `
    <div class="cal-detail-item"><span class="cal-detail-label">Actuel</span><span class="cal-detail-val">${esc(fmt(e.actual))}</span></div>
    <div class="cal-detail-item"><span class="cal-detail-label">Prévu</span><span class="cal-detail-val">${esc(fmt(e.estimate))}</span></div>
    <div class="cal-detail-item"><span class="cal-detail-label">Précédent</span><span class="cal-detail-val">${esc(fmt(e.prev))}</span></div>
    <div class="cal-detail-item"><span class="cal-detail-label">Heure</span><span class="cal-detail-val">${esc(new Date(e.time).toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'}))}</span></div>
  `;
  row.classList.add('expanded');
  row.insertAdjacentElement('afterend', detail);
}

async function loadIndices() {
  try {
    const [iR, mR] = await Promise.allSettled([
      fetch(`${API}/api/indices`).then(r => r.json()),
      fetch(`${API}/api/market-context`).then(r => r.json()),
    ]);
    if (iR.status === 'fulfilled' && iR.value?.status === 'ok')
      renderIndices(iR.value.data, mR.status === 'fulfilled' ? mR.value?.data : null);
  } catch {}
}
function renderIndices(data, ctx) {
  const bar = document.getElementById('indicesBar');
  if (!bar || !data?.length) return;

  const catLabels = { index: '📊 INDICES', forex: '💱 FOREX', commodity: '🛢️ MATIÈRES' };
  // Groupe par catégorie en préservant l'ordre
  const groups = {};
  for (const item of data) {
    if (!groups[item.category]) groups[item.category] = [];
    groups[item.category].push(item);
  }

  const html = [];

  // ── Indicateur de contexte macro en tête ──
  if (ctx) {
    let mood = '😐', label = 'NEUTRE', color = 'var(--text-dim)';
    const cris = ctx.crisis_intensity || 0;
    const sent = ctx.macro_sentiment || 0;
    const vix  = ctx.vix || 20;
    if (cris > 0.30 || vix > 35) {
      mood = '🚨'; label = 'CRISE'; color = 'var(--red)';
    } else if (cris > 0.15 || vix > 25 || sent < -0.2) {
      mood = '⚠️'; label = 'STRESS'; color = 'var(--yellow)';
    } else if (sent > 0.2 && vix < 18) {
      mood = '🚀'; label = 'BULL'; color = 'var(--green)';
    } else {
      mood = '😐'; label = 'CALME'; color = 'var(--text)';
    }
    const tip = `VIX ${vix?.toFixed(1) || '—'} · Sentiment macro ${(sent*100).toFixed(0)}% · Crise ${(cris*100).toFixed(0)}%${ctx.crisis_keywords?.length ? ' · Mots: ' + ctx.crisis_keywords.join(', ') : ''}`;
    html.push(`<div class="index-category-label" title="${esc(tip)}" style="color:${color};border-right-color:${color}">${mood} CONTEXTE: ${label}</div>`);
  }

  for (const cat of ['index', 'forex', 'commodity']) {
    if (!groups[cat]) continue;
    html.push(`<div class="index-category-label">${catLabels[cat]}</div>`);
    for (const i of groups[cat]) {
      const decimals = cat === 'forex' ? 4 : 2;
      html.push(`
        <div class="index-item">
          <span class="index-name">${esc(i.name)}</span>
          <span class="index-value">${i.value.toLocaleString('fr-FR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}</span>
          <span class="index-change ${cls(i.change_pct)}">${fmtChange(i.change_pct)}</span>
        </div>`);
    }
  }
  bar.innerHTML = html.join('');
}

async function loadForex() {
  try {
    const r = await fetch(`${API}/api/forex`);
    const j = await r.json();
    if (j.status === 'ok') state.forex = j.data;
  } catch {}
}
function convertToEUR(value, currency) {
  if (!state.eurMode || !value || currency === 'EUR') return { value, currency };
  // Devises cotees en sous-unite (GBp, ZAc, ILA) : on divise par 100 puis on
  // applique le taux de la devise majeure. Voir MINOR_UNITS plus bas.
  const major = MINOR_UNITS[currency];
  if (major) {
    const r = state.forex[major];
    if (!r) return { value, currency };           // pas de taux -> on n'invente rien
    return { value: (value / 100) * r, currency: 'EUR' };
  }
  const rate = state.forex[currency];
  if (!rate) return { value, currency };
  return { value: value * rate, currency: 'EUR' };
}

// Devises cotees en SOUS-UNITE par Yahoo (1 unite majeure = 100 sous-unites).
//   GBp = pence britanniques  -> GBP  (AZN.L cote 12476 GBp = 124,76 GBP)
//   ZAc = cents sud-africains -> ZAR
//   ILA = agorot israeliens   -> ILS
// Sans cette table, Intl.NumberFormat interprete 'GBp' comme 'GBP' et affiche
// "GBP 12 476" au lieu de "GBP 124,76" : prix faux d'un facteur 100.
const MINOR_UNITS = { GBp: 'GBP', ZAc: 'ZAR', ILA: 'ILS' };

// Convertit une valeur en sous-unite vers sa devise majeure.
// Renvoie l'entree telle quelle si la devise n'est pas une sous-unite.
function normalizeMinorUnit(value, currency) {
  const major = MINOR_UNITS[currency];
  if (!major || value == null) return { value, currency };
  return { value: value / 100, currency: major };
}

function displayCurrency(currency) {
  if (state.eurMode) {
    if (currency === 'EUR') return 'EUR';
    if (MINOR_UNITS[currency] && state.forex[MINOR_UNITS[currency]]) return 'EUR';
    if (state.forex[currency]) return 'EUR';
  }
  // Hors mode EUR : on affiche la devise majeure (GBP), pas la sous-unite (GBp)
  return MINOR_UNITS[currency] || currency;
}

// ── Watchlist (localStorage) ─────────────────────────────────────────
function getUserWatchlist() {
  try { return JSON.parse(localStorage.getItem('watchlist') || '[]'); }
  catch { return []; }
}
function setUserWatchlist(list) {
  localStorage.setItem('watchlist', JSON.stringify(list));
}
function isInWatchlist(symbol) {
  return getUserWatchlist().some(w => w.symbol === symbol);
}
async function toggleWatchlist(symbol, name) {
  const list = getUserWatchlist();
  const idx = list.findIndex(w => w.symbol === symbol);
  if (idx >= 0) list.splice(idx, 1);
  else list.push({ symbol, name: name || symbol });
  setUserWatchlist(list);
  // Re-render visible stars
  rerenderAll();
  refreshModalStar();
  // Recharge la section
  await loadWatchlistSection();
}

async function loadWatchlistSection() {
  const list = getUserWatchlist();
  const section = document.getElementById('watchlistSection');
  const grid = document.getElementById('watchlistGrid');
  if (!list.length) { section.style.display = 'none'; state.watchlist = []; return; }

  section.style.display = '';
  grid.innerHTML = '<div class="loading-placeholder"><span class="spinner"></span>Chargement…</div>';
  const symbols = list.map(w => w.symbol).join(',');
  try {
    const r = await fetch(`${API}/api/watchlist?symbols=${encodeURIComponent(symbols)}`);
    const json = await r.json();
    if (json.status === 'ok') {
      // Override les noms par ceux du localStorage (proper names depuis search)
      const nameMap = Object.fromEntries(list.map(w => [w.symbol, w.name]));
      const data = json.data.map(s => ({ ...s, name: nameMap[s.ticker] || s.name }));
      state.watchlist = data;
      renderWatchlistGrid(data);
    } else {
      grid.innerHTML = '<div class="error-card">Erreur de chargement</div>';
    }
  } catch (e) {
    grid.innerHTML = '<div class="error-card">Erreur réseau</div>';
  }
}

function renderWatchlistGrid(data) {
  const grid = document.getElementById('watchlistGrid');
  if (!data.length) { grid.className = 'cards-grid'; grid.innerHTML = '<div class="error-card">Aucune donnée</div>'; return; }
  renderFilterBar('watchlistFilterBar', 'watchlist', data);
  const filtered = applyFiltersSort(data, 'watchlist');
  if (!filtered.length) { grid.className = 'cards-grid'; grid.innerHTML = '<div class="error-card">Aucun résultat avec ces filtres</div>'; return; }
  if (views.watchlist === 'heatmap') renderHeatmap('watchlistGrid', filtered);
  else if (views.watchlist === 'compact') renderCompact('watchlistGrid', filtered);
  else renderCards('watchlistGrid', filtered, stockCardHTML);
  applyTwoRowsLimit('watchlistGrid', 'watchlist');
}

function refreshModalStar() {
  const sym = currentModalSymbol || currentCryptoId;
  // Bouton fund-row
  const btn = document.getElementById('modalStarBtn');
  if (btn && currentModalSymbol) {
    const starred = isInWatchlist(currentModalSymbol);
    btn.classList.toggle('active', starred);
    btn.innerHTML = starred ? '★ Dans ma watchlist' : '☆ Ajouter à ma watchlist';
  }
  // Étoile en-tête (stock ou crypto)
  document.querySelectorAll('.modal-header-star').forEach(el => {
    // Détermine le symbole : pour crypto on stocke l'id, mais la watchlist utilise le symbol (BTC etc).
    // L'onclick contient l'info — on parse pour la mise à jour
    const m = el.getAttribute('onclick').match(/toggleWatchlist\('([^']+)'/);
    if (!m) return;
    const starred = isInWatchlist(m[1]);
    el.classList.toggle('active', starred);
    el.innerHTML = starred ? '★' : '☆';
  });
}

function applyTRFilter(items) {
  return state.trOnly ? items.filter(i => i.tr) : items;
}

// ── Pliage 2 rangées par section ─────────────────────────────────────
const collapsed = {
  stocks:    localStorage.getItem('collapsed_stocks')    !== '0',
  emerging:  localStorage.getItem('collapsed_emerging')  !== '0',
  watchlist: localStorage.getItem('collapsed_watchlist') !== '0',
  news:      localStorage.getItem('collapsed_news')      !== '0',
  crypto:    localStorage.getItem('collapsed_crypto')    !== '0',
  all:       localStorage.getItem('collapsed_all')       !== '0',
};

// ── Export CSV ───────────────────────────────────────────────────────
function exportCSV(rows, filename) {
  if (!rows?.length) { alert('Aucune donnée à exporter'); return; }
  // Construit le CSV depuis les clés du premier objet
  const keys = Object.keys(rows[0]);
  const escape = (v) => {
    if (v == null) return '';
    const s = String(v).replace(/"/g, '""');
    return /[",\n;]/.test(s) ? `"${s}"` : s;
  };
  const csv = [
    keys.join(';'),
    ...rows.map(r => keys.map(k => escape(r[k])).join(';')),
  ].join('\n');
  // BOM pour Excel + Téléchargement
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportStocksCSV(sectionKey) {
  const data = (sectionKey === 'watchlist' ? state.watchlist
              : sectionKey === 'emerging'  ? state.emerging
              : state.stocks) || [];
  const rows = data.map(s => ({
    ticker:        s.ticker,
    nom:           s.name,
    secteur:       s.sector,
    devise:        s.currency,
    prix:          s.price,
    variation_jour_pct: s.change_pct,
    perf_1m_pct:   s.perf_1m,
    semaine_52_bas: s.week_low,
    semaine_52_haut: s.week_high,
    position_52w:  s.position_52w,
    market_cap:    s.market_cap,
    pe_ratio:      s.pe_ratio,
    dividend_yield_pct: s.dividend_yield,
    revenue_growth: s.revenue_growth,
    score_opportunite: s.opportunity?.score,
    tag:           s.opportunity?.tag,
    disponible_tr: s.tr,
  }));
  const date = new Date().toISOString().slice(0, 10);
  exportCSV(rows, `traderar_${sectionKey}_${date}.csv`);
}

function exportPortfolioCSV() {
  const positions = getPositions();
  if (!positions.length) { alert('Aucune position'); return; }
  const date = new Date().toISOString().slice(0, 10);
  exportCSV(positions, `traderar_portefeuille_${date}.csv`);
}

// Hauteur max par section quand collapsed (≈ 1.5 rangées avec dégradé)
const COLLAPSED_HEIGHTS = {
  stocks:    420,
  emerging:  340,
  watchlist: 420,
  news:      180,
  crypto:    280,
  all:       500,
};

function applyTwoRowsLimit(gridId, sectionKey) {
  requestAnimationFrame(() => {
    const grid = document.getElementById(gridId);
    if (!grid) return;
    // Pas de pliage en vue compact (table)
    if (grid.querySelector('.compact-table')) {
      removeMoreBtn(gridId);
      grid.classList.remove('collapsed');
      grid.style.maxHeight = '';
      return;
    }

    const cards = Array.from(grid.children).filter(c => c.offsetHeight > 0);
    if (cards.length < 3) {
      removeMoreBtn(gridId);
      grid.classList.remove('collapsed');
      grid.style.maxHeight = '';
      return;
    }

    const limit = COLLAPSED_HEIGHTS[sectionKey] || 400;

    // Si le contenu tient déjà dans la limite, pas besoin du bouton
    if (grid.scrollHeight <= limit + 30) {
      removeMoreBtn(gridId);
      grid.classList.remove('collapsed');
      grid.style.maxHeight = '';
      return;
    }

    if (collapsed[sectionKey]) {
      grid.classList.add('collapsed');
      grid.style.maxHeight = limit + 'px';
    } else {
      grid.classList.remove('collapsed');
      grid.style.maxHeight = '';
    }
    showMoreBtn(gridId, sectionKey);
  });
}

function showMoreBtn(gridId, sectionKey) {
  let btn = document.getElementById(gridId + '_more');
  if (!btn) {
    btn = document.createElement('button');
    btn.id = gridId + '_more';
    btn.className = 'see-more-btn';
    document.getElementById(gridId).insertAdjacentElement('afterend', btn);
  }
  btn.onclick = () => toggleCollapse(sectionKey, gridId);
  btn.textContent = collapsed[sectionKey] ? '▼ Voir plus' : '▲ Voir moins';
}

function removeMoreBtn(gridId) {
  const btn = document.getElementById(gridId + '_more');
  if (btn) btn.remove();
}

function toggleCollapse(sectionKey, gridId) {
  collapsed[sectionKey] = !collapsed[sectionKey];
  localStorage.setItem('collapsed_' + sectionKey, collapsed[sectionKey] ? '1' : '0');
  applyTwoRowsLimit(gridId, sectionKey);
}

// ── Filtres & tri par section ────────────────────────────────────────
const filters = {
  stocks:    { sort: 'change_pct_desc',  region: 'all', sector: 'all' },
  emerging:  { sort: 'perf_1m_desc',     region: 'all', sector: 'all' },
  watchlist: { sort: 'change_pct_desc',  region: 'all', sector: 'all' },
  all:       { sort: 'opportunity_desc', region: 'all', sector: 'all' },
};

// ── Vue (cartes / heatmap) par section ───────────────────────────────
const views = {
  stocks:    localStorage.getItem('view_stocks')    || 'cards',
  emerging:  localStorage.getItem('view_emerging')  || 'cards',
  watchlist: localStorage.getItem('view_watchlist') || 'cards',
  all:       localStorage.getItem('view_all')       || 'compact',  // compact par défaut (volume)
};

function setView(sectionKey, mode) {
  views[sectionKey] = mode;
  localStorage.setItem('view_' + sectionKey, mode);
  if (sectionKey === 'stocks')    renderStocks(state.stocks);
  if (sectionKey === 'emerging')  renderEmerging(state.emerging);
  if (sectionKey === 'watchlist') renderWatchlistGrid(state.watchlist);
  if (sectionKey === 'all')       renderAll(state.all);
}

function heatColor(pct) {
  if (pct == null || isNaN(pct)) return 'rgb(30, 30, 42)';
  const mag = Math.min(Math.abs(pct), 8) / 8; // 0..1
  const alpha = 0.18 + mag * 0.55;
  return pct >= 0
    ? `rgba(0, 255, 136, ${alpha})`
    : `rgba(255, 68, 68, ${alpha})`;
}

function heatmapCellHTML(s) {
  const starred = isInWatchlist(s.ticker);
  return `
    <div class="heatmap-cell" style="background:${heatColor(s.change_pct)}" onclick="openStockDetail('${esc(s.ticker)}')">
      ${s.tr === false ? '<span class="off-tr-badge">✕TR</span>' : ''}
      <button class="star-btn ${starred ? 'active' : ''}" style="top:-8px;right:-8px;width:24px;height:24px;font-size:14px" onclick="event.stopPropagation();toggleWatchlist('${esc(s.ticker)}','${esc(s.name)}')" title="${starred ? 'Retirer' : 'Ajouter aux favoris'}">${starred ? '★' : '☆'}</button>
      <div>
        <div class="heatmap-ticker">${s.ticker}</div>
        <div class="heatmap-name">${esc(s.name)}</div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:6px">
        <span class="heatmap-pct">${fmtChange(s.change_pct)}</span>
        ${oppBadge(s.opportunity)}
      </div>
    </div>`;
}

function renderHeatmap(gridId, data) {
  const grid = document.getElementById(gridId);
  grid.className = 'heatmap-grid';
  grid.innerHTML = data.map(heatmapCellHTML).join('');
}

function renderCards(gridId, data, cardFn) {
  const grid = document.getElementById(gridId);
  grid.className = 'cards-grid';
  grid.innerHTML = data.map(cardFn).join('');
}

function renderCompact(gridId, data) {
  const grid = document.getElementById(gridId);
  grid.className = '';
  const rows = data.map(s => {
    const cc = cls(s.change_pct);
    const starred = isInWatchlist(s.ticker);
    return `
      <div class="compact-row" onclick="openStockDetail('${esc(s.ticker)}')">
        <div class="compact-cell bold">${s.ticker}${s.tr === false ? ' <span class="off-tr-badge" style="font-size:7px;padding:0 3px">✕TR</span>' : ''}</div>
        <div class="compact-cell">${esc(s.name)}</div>
        <div class="compact-cell dim">${esc(s.sector)}</div>
        <div class="compact-cell right bold">${fmtPrice(s.price, s.currency)}</div>
        <div class="compact-cell right ${cc}">${fmtChange(s.change_pct)}</div>
        <div class="compact-cell right ${cls(s.perf_1m)}">${fmtChange(s.perf_1m)}</div>
        <div class="compact-cell right dim">${s.market_cap ? fmtCap(s.market_cap, s.currency) : '—'}</div>
        <div class="compact-cell right dim">${s.pe_ratio != null ? s.pe_ratio.toFixed(1) : '—'}</div>
        <div class="compact-cell">${oppBadge(s.opportunity)}</div>
        <div class="compact-cell"><span class="mini-spark">${s.sparkline?.length >= 2 ? sparkline(s.sparkline, 80, 24) : ''}</span></div>
        <div class="compact-cell" onclick="event.stopPropagation();toggleWatchlist('${esc(s.ticker)}','${esc(s.name)}')">
          <span style="cursor:pointer;color:${starred?'var(--yellow)':'var(--text-muted)'};font-size:14px">${starred?'★':'☆'}</span>
        </div>
      </div>`;
  }).join('');
  grid.innerHTML = `
    <div class="compact-table">
      <div class="compact-row head">
        <div class="compact-cell">Ticker</div>
        <div class="compact-cell">Nom</div>
        <div class="compact-cell">Secteur</div>
        <div class="compact-cell right">Prix</div>
        <div class="compact-cell right">Jour</div>
        <div class="compact-cell right">1M</div>
        <div class="compact-cell right">Cap</div>
        <div class="compact-cell right">P/E</div>
        <div class="compact-cell">🎯 Score</div>
        <div class="compact-cell">30j</div>
        <div class="compact-cell"></div>
      </div>
      ${rows}
    </div>`;
}

function getRegion(s) {
  const sym = s.ticker || '';
  if (/\.(PA|DE|AS|L|CO|MC|SW|MI|BR|LS|HE|VI|ST)$/i.test(sym)) return 'EU';
  if (/\.(T|HK|NS|BO|SS|SZ|KS|TW|JK|SI|AX)$/i.test(sym))       return 'Asia';
  return 'US';
}

function applyFiltersSort(items, key) {
  const conf = filters[key];
  let arr = [...items];
  if (conf.region !== 'all') arr = arr.filter(s => getRegion(s) === conf.region);
  if (conf.sector !== 'all') arr = arr.filter(s => s.sector === conf.sector);
  const cmp = {
    opportunity_desc:(a,b) => (b.opportunity?.score||0) - (a.opportunity?.score||0),
    change_pct_desc: (a,b) => (b.change_pct||0) - (a.change_pct||0),
    change_pct_asc:  (a,b) => (a.change_pct||0) - (b.change_pct||0),
    name_asc:        (a,b) => (a.name||'').localeCompare(b.name||''),
    name_desc:       (a,b) => (b.name||'').localeCompare(a.name||''),
    market_cap_desc: (a,b) => (b.market_cap||0) - (a.market_cap||0),
    market_cap_asc:  (a,b) => (a.market_cap||0) - (b.market_cap||0),
    perf_1m_desc:    (a,b) => (b.perf_1m||0) - (a.perf_1m||0),
    perf_1m_asc:     (a,b) => (a.perf_1m||0) - (b.perf_1m||0),
    pe_asc:          (a,b) => (a.pe_ratio||999) - (b.pe_ratio||999),
  };
  if (cmp[conf.sort]) arr.sort(cmp[conf.sort]);
  return arr;
}

function renderFilterBar(barId, sectionKey, data) {
  const bar = document.getElementById(barId);
  if (!bar) return;
  const conf = filters[sectionKey];

  // Collecte les secteurs présents
  const sectors = [...new Set(data.map(s => s.sector).filter(x => x && x !== '—'))].sort();

  const regions = [
    {k: 'all',  label: 'Tous'},
    {k: 'EU',   label: '🇪🇺 EU'},
    {k: 'US',   label: '🇺🇸 US'},
    {k: 'Asia', label: '🌏 Asia'},
  ];

  bar.innerHTML = `
    <div class="filter-group">
      <span class="filter-label">Tri</span>
      <select class="filter-select" onchange="setFilter('${sectionKey}','sort',this.value)">
        <option value="opportunity_desc" ${conf.sort==='opportunity_desc'?'selected':''}>🎯 Score ↓</option>
        <option value="change_pct_desc" ${conf.sort==='change_pct_desc'?'selected':''}>% jour ↓</option>
        <option value="change_pct_asc"  ${conf.sort==='change_pct_asc' ?'selected':''}>% jour ↑</option>
        <option value="perf_1m_desc"    ${conf.sort==='perf_1m_desc'   ?'selected':''}>Perf 1M ↓</option>
        <option value="perf_1m_asc"     ${conf.sort==='perf_1m_asc'    ?'selected':''}>Perf 1M ↑</option>
        <option value="name_asc"        ${conf.sort==='name_asc'       ?'selected':''}>Nom A→Z</option>
        <option value="name_desc"       ${conf.sort==='name_desc'      ?'selected':''}>Nom Z→A</option>
        <option value="market_cap_desc" ${conf.sort==='market_cap_desc'?'selected':''}>Cap ↓</option>
        <option value="market_cap_asc"  ${conf.sort==='market_cap_asc' ?'selected':''}>Cap ↑</option>
        <option value="pe_asc"          ${conf.sort==='pe_asc'         ?'selected':''}>P/E ↑ (sous-évaluées)</option>
      </select>
    </div>
    <div class="chip-group">
      ${regions.map(r => `<button class="chip ${conf.region===r.k?'active':''}" onclick="setFilter('${sectionKey}','region','${r.k}')">${r.label}</button>`).join('')}
    </div>
    <div class="filter-group">
      <span class="filter-label">Secteur</span>
      <select class="filter-select" onchange="setFilter('${sectionKey}','sector',this.value)">
        <option value="all" ${conf.sector==='all'?'selected':''}>Tous</option>
        ${sectors.map(sec => `<option value="${esc(sec)}" ${conf.sector===sec?'selected':''}>${esc(sec)}</option>`).join('')}
      </select>
    </div>
    <button class="chip" onclick="exportStocksCSV('${sectionKey}')" title="Télécharger ces données en CSV (Excel)" style="margin-left:auto">📥 CSV</button>
    <div class="view-toggle">
      <button class="view-btn ${views[sectionKey]==='cards'?'active':''}" onclick="setView('${sectionKey}','cards')" title="Vue cartes">▦ Cartes</button>
      <button class="view-btn ${views[sectionKey]==='compact'?'active':''}" onclick="setView('${sectionKey}','compact')" title="Vue compacte (tableau)">≡ Compact</button>
      <button class="view-btn ${views[sectionKey]==='heatmap'?'active':''}" onclick="setView('${sectionKey}','heatmap')" title="Vue heatmap">▣ Heatmap</button>
      ${views[sectionKey] === 'heatmap' ? '<button class="help-btn" style="margin-left:6px" onclick="toggleHelp(\'helpHeatmap_'+sectionKey+'\', this)" title="Comment lire la heatmap ?">?</button>' : ''}
    </div>
    ${views[sectionKey] === 'heatmap' ? `<div id="helpHeatmap_${sectionKey}" class="help-panel" style="margin-top:4px">${HELP_HEATMAP}</div>` : ''}
  `;
}

function setFilter(sectionKey, field, value) {
  filters[sectionKey][field] = value;
  if (sectionKey === 'stocks')    renderStocks(state.stocks);
  if (sectionKey === 'emerging')  renderEmerging(state.emerging);
  if (sectionKey === 'watchlist') renderWatchlistGrid(state.watchlist);
  if (sectionKey === 'all')       renderAll(state.all);
}

function toggleTR() {
  state.trOnly = !state.trOnly;
  localStorage.setItem('tr_only', state.trOnly ? '1' : '0');
  updateTRButton();
  rerenderAll();
}

function updateTRButton() {
  const btn = document.getElementById('trToggleBtn');
  if (!btn) return;
  btn.classList.toggle('active', state.trOnly);
}

function rerenderAll() {
  if (state.stocks.length)    renderStocks(state.stocks);
  if (state.movers.gainers.length || state.movers.losers.length) renderMovers(state.movers);
  if (state.news.length)      renderNews(state.news);
  if (state.emerging.length)  renderEmerging(state.emerging);
  if (state.crypto.length)    renderCrypto(state.crypto);
  if (state.watchlist.length) renderWatchlistGrid(state.watchlist);
  if (state.all.length)       renderAll(state.all);
}

function renderAll(data) {
  state.all = data;
  const grid = document.getElementById('allGrid');
  if (!data?.length) { setError('allGrid'); return; }
  renderFilterBar('allFilterBar', 'all', data);
  let filtered = applyTRFilter(data);
  filtered = applyFiltersSort(filtered, 'all');
  if (!filtered.length) { grid.className = 'cards-grid'; grid.innerHTML = '<div class="error-card">Aucun résultat avec ces filtres</div>'; return; }
  if (views.all === 'heatmap') renderHeatmap('allGrid', filtered);
  else if (views.all === 'compact') renderCompact('allGrid', filtered);
  else renderCards('allGrid', filtered, stockCardHTML);
  applyTwoRowsLimit('allGrid', 'all');
}

// ── Formatage ────────────────────────────────────────────────────────

function fmtPrice(price, currency = 'USD') {
  if (price == null || isNaN(price)) return '—';
  const c = convertToEUR(price, currency);
  price = c.value; currency = c.currency;
  // Si convertToEUR n'a rien converti (mode EUR off, ou pas de taux dispo),
  // la devise peut encore etre une sous-unite -> on la ramene en unite majeure.
  const n = normalizeMinorUnit(price, currency);
  price = n.value; currency = n.currency;
  const locale = currency === 'EUR' ? 'fr-FR' : 'en-US';
  const decimals = price < 1 ? 4 : 2;
  return new Intl.NumberFormat(locale, {
    style: 'currency', currency,
    minimumFractionDigits: decimals, maximumFractionDigits: decimals,
  }).format(price);
}

function fmtChange(val) {
  if (val == null || isNaN(val)) return '—';
  const sign = val >= 0 ? '+' : '';
  return `${sign}${val.toFixed(2)} %`;
}

function fmtCap(mc, currency = 'USD') {
  if (!mc) return '—';
  const c = convertToEUR(mc, currency);
  mc = c.value;
  const sym = c.currency === 'EUR' ? '€ ' : '';
  if (mc >= 1e12) return `${sym}${(mc / 1e12).toFixed(2)} Bn`;
  if (mc >= 1e9)  return `${sym}${(mc / 1e9).toFixed(1)} Md`;
  if (mc >= 1e6)  return `${sym}${(mc / 1e6).toFixed(0)} M`;
  return String(mc);
}

function cls(val) {
  return val == null ? '' : val >= 0 ? 'pos' : 'neg';
}

// ── Sparkline SVG ────────────────────────────────────────────────────

function sparkline(prices, w = 118, h = 38) {
  if (!prices || prices.length < 2) return '';

  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const pad = 3;

  const pts = prices.map((p, i) => {
    const x = (i / (prices.length - 1)) * w;
    const y = h - pad - ((p - min) / range) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const isUp = prices[prices.length - 1] >= prices[0];
  const color = isUp ? '#00ff88' : '#ff4444';
  const uid = 'sg' + Math.random().toString(36).slice(2, 7);
  const line = 'M ' + pts.join(' L ');
  const area = `${line} L ${w},${h} L 0,${h} Z`;

  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="${uid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"   stop-color="${color}" stop-opacity="0.25"/>
        <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <path d="${area}" fill="url(#${uid})"/>
    <path d="${line}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round"/>
  </svg>`;
}

// ── État de chargement ───────────────────────────────────────────────

function setLoading(id) {
  document.getElementById(id).innerHTML =
    '<div class="loading-placeholder"><span class="spinner"></span>Chargement en cours…</div>';
}

function setError(id, msg = 'Données indisponibles — réessayez') {
  document.getElementById(id).innerHTML = `<div class="error-card">${msg}</div>`;
}

// ── Section 1 : Actions en forme ────────────────────────────────────

function stockCardHTML(s) {
  const cc = cls(s.change_pct);
  const pos52 = Math.min(100, Math.max(0, s.position_52w ?? 50));
  const starred = isInWatchlist(s.ticker);
  return `
    <div class="card stock-card${s.tr === false ? ' off-tr' : ''}" onclick="openStockDetail('${esc(s.ticker)}')">
      <button class="star-btn ${starred ? 'active' : ''}" onclick="event.stopPropagation();toggleWatchlist('${esc(s.ticker)}','${esc(s.name)}')" title="${starred ? 'Retirer de ma watchlist' : 'Ajouter à ma watchlist'}">${starred ? '★' : '☆'}</button>
      <div class="card-top">
        <div>
          <div class="ticker">${s.ticker}${s.tr === false ? '<span class="off-tr-badge" title="Non disponible sur Trade Republic">✕TR</span>' : ''}</div>
          <div class="stock-name">${esc(s.name)}</div>
        </div>
        <span class="badge-change ${cc}">${fmtChange(s.change_pct)}</span>
      </div>
      <div class="price-big">
        ${fmtPrice(s.price, s.currency)}
        <span class="price-currency">${displayCurrency(s.currency)}</span>
      </div>
      <div class="tag-row">
        <span class="tag">${esc(s.sector)}</span>
        ${oppBadge(s.opportunity)}
        ${s.near_52w_low ? '<span class="tag-opport">↓ Opportunité</span>' : ''}
      </div>
      ${fundamentalsRow(s)}
      <div class="bar52-wrap">
        <div class="bar52-labels">
          <span>52S bas ${s.week_low ? fmtPrice(s.week_low, s.currency) : '—'}</span>
          <span>52S haut ${s.week_high ? fmtPrice(s.week_high, s.currency) : '—'}</span>
        </div>
        <div class="bar52"><div class="bar52-dot" style="left:${pos52}%"></div></div>
      </div>
      ${s.sparkline?.length >= 2 ? `<div class="sparkline-wrap">${sparkline(s.sparkline)}</div>` : ''}
    </div>`;
}

function renderStocks(data) {
  state.stocks = data;
  const grid = document.getElementById('stocksGrid');
  if (!data?.length) { setError('stocksGrid'); return; }
  renderFilterBar('stocksFilterBar', 'stocks', data);
  let filtered = applyTRFilter(data);
  filtered = applyFiltersSort(filtered, 'stocks');
  if (!filtered.length) { grid.className = 'cards-grid'; grid.innerHTML = '<div class="error-card">Aucun résultat avec ces filtres</div>'; return; }
  if (views.stocks === 'heatmap') renderHeatmap('stocksGrid', filtered);
  else if (views.stocks === 'compact') renderCompact('stocksGrid', filtered);
  else renderCards('stocksGrid', filtered, stockCardHTML);
  applyTwoRowsLimit('stocksGrid', 'stocks');
}

// ── Section 1.5 : Top Gainers / Losers ───────────────────────────────

function renderMovers(data) {
  state.movers = data || { gainers: [], losers: [] };

  const renderList = (items, isGainer) => {
    const filtered = applyTRFilter(items || []);
    if (!filtered.length) {
      return '<div class="loading-placeholder" style="padding:14px;font-size:11px">Aucun mouvement à afficher</div>';
    }
    return filtered.map((s, i) => {
      const starred = isInWatchlist(s.ticker);
      return `
      <div class="mover-row" style="animation-delay:${i * 0.05}s" onclick="openStockDetail('${esc(s.ticker)}')">
        <div class="mover-rank">${i + 1}</div>
        <div class="mover-id">
          <div class="mover-ticker">
            ${s.ticker}
            ${s.tr === false ? '<span class="off-tr-badge" title="Non disponible sur Trade Republic">✕TR</span>' : ''}
          </div>
          <div class="mover-name">${esc(s.name)}</div>
        </div>
        <div class="mover-price">${fmtPrice(s.price, s.currency)}</div>
        <div class="mover-change ${isGainer ? 'pos' : 'neg'}">${fmtChange(s.change_pct)} ${oppBadge(s.opportunity)}</div>
        <div onclick="event.stopPropagation();toggleWatchlist('${esc(s.ticker)}','${esc(s.name)}')" style="cursor:pointer;color:${starred?'var(--yellow)':'var(--text-muted)'};font-size:14px;padding:0 4px" title="${starred ? 'Retirer' : 'Ajouter aux favoris'}">${starred?'★':'☆'}</div>
      </div>`;
    }).join('');
  };

  document.getElementById('gainersList').innerHTML = renderList(data.gainers, true);
  document.getElementById('losersList').innerHTML  = renderList(data.losers, false);
}

// Ligne de fondamentaux : Cap / P/E / Div / Croiss.
function fundamentalsRow(s) {
  const hasAny = s.market_cap || s.pe_ratio || s.dividend_yield != null || s.revenue_growth != null;
  if (!hasAny) {
    return '<div class="fund-row"><span class="fund-empty">Fondamentaux non disponibles</span></div>';
  }
  const cap = s.market_cap ? fmtCap(s.market_cap, s.currency) : '—';
  const pe = s.pe_ratio != null ? s.pe_ratio.toFixed(1) : '—';
  const div = s.dividend_yield != null ? `${s.dividend_yield.toFixed(2)}%` : '—';
  const rg = s.revenue_growth != null ? fmtChange(s.revenue_growth * 100) : '—';
  const rgCls = s.revenue_growth != null ? cls(s.revenue_growth) : '';
  return `
    <div class="fund-row">
      <div class="fund-item"><span class="fund-label">Cap</span><span class="fund-val">${cap}</span></div>
      <div class="fund-item"><span class="fund-label">P/E</span><span class="fund-val">${pe}</span></div>
      <div class="fund-item"><span class="fund-label">Div</span><span class="fund-val">${div}</span></div>
      <div class="fund-item"><span class="fund-label">Rev</span><span class="fund-val ${rgCls}">${rg}</span></div>
    </div>`;
}

// ── Section 2 : Actualités ───────────────────────────────────────────

function renderNews(data) {
  state.news = data;
  const grid = document.getElementById('newsGrid');
  if (!data?.length) { setError('newsGrid', 'Actualités indisponibles — vérifiez votre clé FINNHUB_API_KEY'); return; }

  grid.innerHTML = data.map(n => {
    const sc = n.sentiment === 'positif' ? 'positif'
             : n.sentiment === 'négatif' ? 'négatif'
             : 'neutre';
    const safeUrl = n.url && n.url !== '#' ? esc(n.url) : '';
    const clickAttr = safeUrl ? `onclick="window.open('${safeUrl}','_blank','noopener')"` : '';

    return `
    <div class="card news-card" ${clickAttr}>
      <div class="news-top">
        <span class="badge-sentiment ${sc}">${esc(n.sentiment)}</span>
        <span class="news-time">${esc(n.time_ago)}</span>
      </div>
      <div class="news-headline">${esc(n.headline)}</div>
      <div class="news-meta">
        <span class="news-source">${esc(n.source)}</span>
        ${safeUrl ? '<span style="font-size:10px;color:var(--text-muted)">↗ Lire</span>' : ''}
      </div>
    </div>`;
  }).join('');
  applyTwoRowsLimit('newsGrid', 'news');
}

// ── Section 3 : Entreprises Émergentes ──────────────────────────────

function emergingCardHTML(c) {
  const cc  = cls(c.change_pct);
  const cc1 = cls(c.perf_1m);
  const crg = c.revenue_growth != null ? cls(c.revenue_growth) : '';
  const starred = isInWatchlist(c.ticker);
  return _emergingTemplate(c, cc, cc1, crg, starred);
}

function renderEmerging(data) {
  state.emerging = data;
  const grid = document.getElementById('emergingGrid');
  if (!data?.length) { setError('emergingGrid'); return; }
  renderFilterBar('emergingFilterBar', 'emerging', data);
  let filtered = applyTRFilter(data);
  filtered = applyFiltersSort(filtered, 'emerging');
  if (!filtered.length) { grid.className = 'cards-grid'; grid.innerHTML = '<div class="error-card">Aucun résultat avec ces filtres</div>'; return; }
  if (views.emerging === 'heatmap') { renderHeatmap('emergingGrid', filtered); applyTwoRowsLimit('emergingGrid', 'emerging'); return; }
  if (views.emerging === 'compact') { renderCompact('emergingGrid', filtered); applyTwoRowsLimit('emergingGrid', 'emerging'); return; }
  grid.className = 'cards-grid';
  grid.innerHTML = filtered.map(c => {
    const cc  = cls(c.change_pct);
    const cc1 = cls(c.perf_1m);
    const crg = c.revenue_growth != null ? cls(c.revenue_growth) : '';

    return `
    <div class="card emerging-card${c.tr === false ? ' off-tr' : ''}" onclick="openStockDetail('${esc(c.ticker)}')">
      <div class="card-top">
        <div>
          <div class="ticker">${c.ticker}${c.tr === false ? '<span class="off-tr-badge" title="Non disponible sur Trade Republic">✕TR</span>' : ''}</div>
          <div class="stock-name">${esc(c.name)}</div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div class="badge-change ${cc}">${fmtChange(c.change_pct)}</div>
          <div style="font-size:9px;color:var(--text-dim);margin-top:2px">1M: <span class="${cc1 ? 'meta-' + cc1 : ''}" style="font-weight:600">${fmtChange(c.perf_1m)}</span></div>
        </div>
      </div>

      <div class="price-big">
        ${fmtPrice(c.price, c.currency)}
        <span class="price-currency">${displayCurrency(c.currency)}</span>
      </div>

      ${fundamentalsRow(c)}

      <div class="tag-row"><span class="tag">${esc(c.sector)}</span>${oppBadge(c.opportunity)}</div>

      <div class="sparkline-wrap">${sparkline(c.sparkline)}</div>
    </div>`;
  }).join('');
  applyTwoRowsLimit('emergingGrid', 'emerging');
}

// ── Section 4 : Crypto ───────────────────────────────────────────────

function renderCrypto(data) {
  state.crypto = data;
  const grid = document.getElementById('cryptoGrid');
  if (!data?.length) { setError('cryptoGrid', 'Données crypto indisponibles — réessayez'); return; }
  const filtered = applyTRFilter(data);
  if (!filtered.length) { grid.innerHTML = '<div class="error-card">Aucune crypto disponible sur Trade Republic dans cette sélection</div>'; return; }

  grid.innerHTML = filtered.map(c => {
    const rangePos = (c.high_24h && c.low_24h && c.high_24h !== c.low_24h)
      ? Math.min(100, Math.max(0, ((c.price - c.low_24h) / (c.high_24h - c.low_24h)) * 100))
      : 50;

    const pc = cls(c.change_24h);

    const cryptoStarred = isInWatchlist(c.symbol);
    return `
    <div class="card crypto-card${c.tr === false ? ' off-tr' : ''}" onclick="openCryptoDetail('${esc(c.id)}')">
      <button class="star-btn ${cryptoStarred ? 'active' : ''}" onclick="event.stopPropagation();toggleWatchlist('${esc(c.symbol)}','${esc(c.name)}')" title="${cryptoStarred ? 'Retirer' : 'Ajouter aux favoris'}">${cryptoStarred ? '★' : '☆'}</button>
      <div class="crypto-top">
        <div class="crypto-id-col">
          <span class="crypto-symbol">${esc(c.symbol)}${c.tr === false ? '<span class="off-tr-badge" title="Non disponible sur Trade Republic">✕TR</span>' : ''}</span>
          <span class="crypto-name">${esc(c.name)}</span>
        </div>
        ${c.image ? `<img class="crypto-icon" src="${esc(c.image)}" alt="${esc(c.symbol)}" loading="lazy"/>` : ''}
      </div>

      <div class="crypto-price ${pc}">${fmtPrice(c.price, 'EUR')}</div>

      <div class="changes-row">
        <div class="change-col">
          <span class="change-period">24 h</span>
          <span class="change-val ${cls(c.change_24h)}">${fmtChange(c.change_24h)}</span>
        </div>
        <div class="change-col">
          <span class="change-period">7 j</span>
          <span class="change-val ${cls(c.change_7d)}">${fmtChange(c.change_7d)}</span>
        </div>
        <div class="change-col">
          <span class="change-period">Cap</span>
          <span class="change-val" style="color:var(--text-dim)">${fmtCap(c.market_cap, 'EUR')}</span>
        </div>
      </div>

      <div class="range-wrap">
        <div class="range-bar">
          <div class="range-dot" style="left:${rangePos.toFixed(1)}%"></div>
        </div>
        <div class="range-labels">
          <span>${c.low_24h  ? fmtPrice(c.low_24h,  'EUR') : '—'}</span>
          <span>${c.high_24h ? fmtPrice(c.high_24h, 'EUR') : '—'}</span>
        </div>
      </div>

      ${c.sparkline_7d?.length >= 2 ? `<div class="sparkline-wrap" title="Évolution 7 jours">${sparkline(c.sparkline_7d)}</div>` : ''}
    </div>`;
  }).join('');
  applyTwoRowsLimit('cryptoGrid', 'crypto');
}

// ── Fetch principal ──────────────────────────────────────────────────

async function fetchAll() {
  const btn = document.getElementById('refreshBtn');
  btn.classList.add('loading');
  btn.disabled = true;

  setLoading('stocksGrid');
  setLoading('newsGrid');
  setLoading('emergingGrid');
  setLoading('cryptoGrid');

  const endpoints = [
    '/api/trending-stocks',
    '/api/top-movers',
    '/api/news',
    '/api/emerging',
    '/api/crypto',
    '/api/all-universe',
  ];

  const results = await Promise.allSettled(
    endpoints.map(ep =>
      fetch(API + ep, { cache: 'no-store' })
        .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
    )
  );

  const [stocks, movers, news, emerging, crypto, all] = results;

  if (stocks.status === 'fulfilled' && stocks.value?.status === 'ok')
    renderStocks(stocks.value.data);
  else
    setError('stocksGrid');

  if (movers.status === 'fulfilled' && movers.value?.status === 'ok')
    renderMovers(movers.value.data);
  else {
    document.getElementById('gainersList').innerHTML = '<div class="error-card">Indisponible</div>';
    document.getElementById('losersList').innerHTML  = '<div class="error-card">Indisponible</div>';
  }

  if (news.status === 'fulfilled' && news.value?.status === 'ok')
    renderNews(news.value.data);
  else
    setError('newsGrid', 'Actualités indisponibles — vérifiez votre clé FINNHUB_API_KEY');

  if (emerging.status === 'fulfilled' && emerging.value?.status === 'ok')
    renderEmerging(emerging.value.data);
  else
    setError('emergingGrid');

  if (crypto.status === 'fulfilled' && crypto.value?.status === 'ok')
    renderCrypto(crypto.value.data);
  else
    setError('cryptoGrid', 'Données crypto indisponibles — réessayez');

  if (all.status === 'fulfilled' && all.value?.status === 'ok')
    renderAll(all.value.data);
  else
    setError('allGrid');

  // Horodatage
  const now = new Date();
  document.getElementById('lastUpdate').textContent =
    `Mis à jour le ${now.toLocaleDateString('fr-FR')} à ${now.toLocaleTimeString('fr-FR')}`;

  btn.classList.remove('loading');
  btn.disabled = false;
}

function refreshAll() { fetchAll(); loadWatchlistSection(); loadIndices(); loadCalendar(); loadCryptoGlobal(); loadPortfolio(); }

// ── Auto-refresh ─────────────────────────────────────────────────────
let autoRefreshTimer = null;
let autoRefreshCountdown = null;

function setAutoRefresh(seconds) {
  seconds = parseInt(seconds) || 0;
  localStorage.setItem('auto_refresh', seconds);
  if (autoRefreshTimer) { clearInterval(autoRefreshTimer); autoRefreshTimer = null; }
  if (autoRefreshCountdown) { clearInterval(autoRefreshCountdown); autoRefreshCountdown = null; }
  document.getElementById('autoRefreshSelect').value = seconds;

  if (seconds > 0) {
    let remaining = seconds;
    const btn = document.getElementById('refreshBtn');
    autoRefreshCountdown = setInterval(() => {
      remaining--;
      if (remaining <= 0) remaining = seconds;
      const mm = Math.floor(remaining / 60);
      const ss = (remaining % 60).toString().padStart(2, '0');
      btn.innerHTML = `<span class="refresh-icon">↻</span> Actualiser <span style="font-size:10px;opacity:0.7">${mm}:${ss}</span>`;
    }, 1000);

    autoRefreshTimer = setInterval(() => {
      refreshAll();
    }, seconds * 1000);
  } else {
    const btn = document.getElementById('refreshBtn');
    if (btn) btn.innerHTML = '<span class="refresh-icon">↻</span> Actualiser';
  }
}

function initAutoRefresh() {
  const saved = parseInt(localStorage.getItem('auto_refresh') || '0');
  setAutoRefresh(saved);
}

// ── Échappement HTML ─────────────────────────────────────────────────

function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ══════════════════════════════════════════════════════════════════════
//   MODAL DÉTAIL ACTION
// ══════════════════════════════════════════════════════════════════════

let currentModalSymbol = null;
let currentModalPeriod = '1y';

async function openStockDetail(symbol) {
  if (!symbol) return;
  currentModalSymbol = symbol;
  currentModalPeriod = '1y';
  pushHistory(symbol);
  const backdrop = document.getElementById('modalBackdrop');
  backdrop.classList.add('open');
  document.getElementById('modalContent').innerHTML =
    '<div class="loading-placeholder"><span class="spinner"></span>Chargement…</div>';
  await loadStockDetail();
}

// ── Historique de navigation ─────────────────────────────────────────
function pushHistory(symbol) {
  const hist = JSON.parse(localStorage.getItem('history') || '[]');
  const filtered = hist.filter(s => s !== symbol);
  filtered.unshift(symbol);
  localStorage.setItem('history', JSON.stringify(filtered.slice(0, 12)));
  renderHistoryBar();
}

function renderHistoryBar() {
  const bar = document.getElementById('historyBar');
  if (!bar) return;
  const hist = JSON.parse(localStorage.getItem('history') || '[]');
  if (!hist.length) { bar.innerHTML = ''; return; }
  bar.innerHTML = '<span class="history-label">📍 Récents :</span>' +
    hist.map(s => `<span class="history-chip" onclick="openStockDetail('${esc(s)}')">${esc(s)}</span>`).join('');
}

async function loadStockDetail() {
  try {
    const r = await fetch(`${API}/api/stock-detail/${encodeURIComponent(currentModalSymbol)}?period=${currentModalPeriod}`);
    const json = await r.json();
    if (json.status !== 'ok') {
      document.getElementById('modalContent').innerHTML =
        `<div class="error-card">${esc(json.message || 'Erreur')}</div>`;
      return;
    }
    renderStockDetail(json.data);
  } catch (e) {
    document.getElementById('modalContent').innerHTML =
      `<div class="error-card">Erreur réseau — ${esc(e.message)}</div>`;
  }
}

function renderStockDetail(d) {
  const cc = cls(d.change_pct);
  const periods = ['1d', '5d', '1mo', '3mo', '1y', '5y', 'max'];
  const periodLabels = { '1d': '1J', '5d': '5J', '1mo': '1M', '3mo': '3M', '1y': '1A', '5y': '5A', 'max': 'Max' };

  document.getElementById('modalContent').innerHTML = `
    <div class="modal-header">
      <div class="modal-title-row">
        <div class="modal-ticker">
          ${d.ticker}
          <button class="modal-header-star ${isInWatchlist(d.ticker) ? 'active' : ''}" onclick="toggleWatchlist('${esc(d.ticker)}','${esc(d.name)}')" title="${isInWatchlist(d.ticker) ? 'Retirer des favoris' : 'Ajouter aux favoris'}">${isInWatchlist(d.ticker) ? '★' : '☆'}</button>
          ${d.tr === false ? '<span class="off-tr-badge">✕TR</span>' : ''}
        </div>
        <div class="modal-name">${esc(d.name)} · ${esc(d.sector || '')}</div>
      </div>
      <div class="modal-price-col">
        <div class="modal-price">${fmtPrice(d.price, d.currency)} <span class="price-currency">${displayCurrency(d.currency)}</span></div>
        <div class="modal-change ${cc}">${fmtChange(d.change_pct)}</div>
      </div>
    </div>

    <div class="period-tabs">
      ${periods.map(p => `
        <button class="period-tab ${p === d.period ? 'active' : ''}" onclick="changePeriod('${p}')">${periodLabels[p]}</button>
      `).join('')}
    </div>

    <div class="modal-chart">
      ${chartLarge(d.history)}
    </div>

    <div class="modal-cols">
      <div class="modal-fund">
        <div class="modal-fund-title">
          Fondamentaux
          <button class="help-btn" onclick="toggleHelp('helpFundamentals', this)" title="C'est quoi ces indicateurs ?">?</button>
        </div>
        <div id="helpFundamentals" class="help-panel">${HELP_FUNDAMENTALS}</div>
        <div class="modal-fund-grid">
          ${fundItem('Cap. boursière', d.market_cap ? fmtCap(d.market_cap, d.currency) : '—')}
          ${fundItem('P/E', d.pe_ratio != null ? d.pe_ratio.toFixed(2) : '—')}
          ${fundItem('Dividende', d.dividend_yield != null ? d.dividend_yield.toFixed(2) + ' %' : '—')}
          ${fundItem('Croiss. revenu', d.revenue_growth != null ? fmtChange(d.revenue_growth * 100) : '—', cls(d.revenue_growth))}
          ${fundItem('52S bas', d.week_low ? fmtPrice(d.week_low, d.currency) : '—')}
          ${fundItem('52S haut', d.week_high ? fmtPrice(d.week_high, d.currency) : '—')}
        </div>
        <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
          <button id="modalStarBtn" class="modal-star ${isInWatchlist(d.ticker) ? 'active' : ''}" onclick="toggleWatchlist('${esc(d.ticker)}','${esc(d.name)}')">${isInWatchlist(d.ticker) ? '★ Dans ma watchlist' : '☆ Ajouter à ma watchlist'}</button>
          <a href="https://finance.yahoo.com/quote/${encodeURIComponent(d.ticker)}" target="_blank" rel="noopener" class="period-tab" style="text-decoration:none">Yahoo ↗</a>
          ${d.tr !== false ? `<a href="https://traderepublic.com/${(d.currency === 'EUR' || d.currency === 'GBP' ? 'fr' : 'en')}/stocks/${encodeURIComponent(d.ticker)}" target="_blank" rel="noopener" class="period-tab" style="text-decoration:none">Trade Republic ↗</a>` : ''}
        </div>

        ${renderOpportunitySection(d.opportunity)}

        ${renderIndicators(d.indicators, d.currency)}

        ${renderBuySimForm(d.ticker, d.name, d.price, d.currency)}

        ${renderAlertSection(d.ticker, d.name, d.price, d.currency).outerHTML}
      </div>

      <div class="modal-news">
        <div class="modal-news-title">Actualités · ${d.ticker}</div>
        ${renderModalNews(d.news)}
      </div>
    </div>
  `;

  // Attache les events du graphique après l'insertion DOM
  attachChartHover(d.currency);
}

function fundItem(label, val, cssClass = '') {
  return `
    <div class="modal-fund-item">
      <span class="label">${label}</span>
      <span class="val ${cssClass}">${val}</span>
    </div>`;
}

// ── Score d'opportunité ──────────────────────────────────────────────
const HELP_OPPORTUNITY = `
  <div class="help-section">
    <h4>🎯 Score d'opportunité v6 (0-100) — architecture en 4 piliers</h4>
    <p>Le score combine <strong>50+ signaux</strong> organisés en 4 piliers notés chacun de 0 à 100, puis pondérés selon le <strong>régime de marché détecté</strong> pour l'action (bull / neutre / bear).</p>
    <p><span class="help-tag buy">75-100 · HOT 🔥</span> Forte conviction d'opportunité — combinaison de signaux haussiers</p>
    <p><span class="help-tag buy">60-74 · GOOD</span> Signal positif sans excès</p>
    <p><span class="help-tag neutral">40-59 · NEUTRE</span> Pas de signal clair, à surveiller</p>
    <p><span class="help-tag sell">25-39 · FAIBLE</span> Plusieurs signaux baissiers</p>
    <p><span class="help-tag sell">0-24 · ÉVITER</span> Forte conviction négative</p>
  </div>
  <div class="help-section">
    <h4>🏛️ Les 4 piliers</h4>
    <p><strong>📈 Tendance</strong> — la tendance de fond est-elle haussière et CONFIRMÉE ?</p>
    <p>• MM50/200, golden/death cross, EMA21, alignement ROC 4 timeframes</p>
    <p>• <strong>ADX/DI</strong> (force directionnelle), R² régression 90j, structure HH/HL vs LH/LL</p>
    <p>• MACD + <strong>pente de l'histogramme</strong> (détecte l'essoufflement AVANT le croisement)</p>
    <p>• <strong>OBV</strong> (le volume confirme-t-il la hausse ? hausse sans volume = suspect)</p>
    <p>• <strong>Chaikin Money Flow</strong> (accumulation vs distribution institutionnelle)</p>
    <p style="margin-top:6px"><strong>⏱️ Timing</strong> — est-ce un bon point d'entrée MAINTENANT ?</p>
    <p>• Consensus survente/surachat à <strong>6 votants</strong> : RSI, Williams %R, CCI, Stochastic, Bollinger, <strong>MFI</strong> (volume)</p>
    <p>• <strong>Divergence RSI</strong> — prix fait un nouveau plus bas mais RSI refuse de suivre = vendeurs épuisés (signal de retournement parmi les plus fiables)</p>
    <p>• Z-score, pullback vers MM200/EMA21, rebond frais, canal Donchian 55j</p>
    <p>• <strong>Volume events</strong> : breakout confirmé volume (+), capitulation près du bas (+), distribution en haut de cycle (–)</p>
    <p>• Position 52S × stabilité du jour (anti "couteau qui tombe")</p>
    <p style="margin-top:6px"><strong>🛡️ Qualité</strong> — l'action est-elle saine ?</p>
    <p>• P/E (avec logique PEG : P/E élevé excusé si forte croissance), croissance revenu, dividende (piège si &gt;9%), market cap</p>
    <p>• <strong>Sortino</strong> (ne pénalise que la volatilité baissière — mieux que Sharpe), max drawdown, régularité des jours haussiers</p>
    <p>• Earnings surprises (beats vs misses 4 trimestres)</p>
    <p style="margin-top:6px"><strong>📰 Sentiment</strong> (US uniquement — Finnhub)</p>
    <p>• Sentiment news 14j (pondéré par le nombre d'articles), consensus analystes, tendance upgrades/downgrades</p>
  </div>
  <div class="help-section">
    <h4>⚖️ Pondération adaptative par régime</h4>
    <p>• <strong>Régime BULL</strong> → Tendance 40% · Timing 20% · Qualité 25% · Sentiment 15% (le momentum prime)</p>
    <p>• <strong>Régime NEUTRE</strong> → 30 / 30 / 25 / 15</p>
    <p>• <strong>Régime BEAR</strong> → 15 / 35 / 35 / 15 (la qualité et le point d'entrée priment, le momentum ment)</p>
    <p>• Piliers sans données (ex: sentiment pour actions EU) → poids redistribués + <strong>confiance réduite</strong></p>
  </div>
  <div class="help-section">
    <h4>🌍 Overlays de sécurité</h4>
    <p>• <strong>Multiplicateur de risque</strong> : ATR élevé, volatilité extrême, drawdown &gt;60%, downtrend ADX puissant → score au-dessus de 50 comprimé jusqu'à -35%</p>
    <p>• <strong>VIX</strong> : &gt;35 → -25% / &gt;25 → -15% / &lt;13 (complaisance) → légère pénalité</p>
    <p>• <strong>🚨 Mode crise auto</strong> (mots-clés guerre/krach/récession dans l'actu) → -20 à -30% sur les scores élevés</p>
    <p>• <strong>Plafonds régime baissier</strong> : 6+ signaux bear → max 40 · 4+ → max 50 · 3 → max 65. Assouplis de +10 si preuve de retournement (divergence RSI bull + survente massive)</p>
  </div>
  <div class="help-section">
    <h4>🎚️ Confiance (0-100)</h4>
    <p>Mesure la <strong>couverture des données</strong>, pas la qualité du signal : historique complet, volume, fondamentaux, sentiment, nombre d'analystes. Une action EU sans fondamentaux Finnhub aura une confiance ~55 ; une US large cap ~100. <strong>Score élevé + confiance basse = vérifier manuellement.</strong></p>
  </div>
  <div class="help-section">
    <p style="color:var(--text-muted);font-style:italic;font-size:10px">⚠️ Ce score est une <strong>heuristique statistique</strong>, pas un conseil en investissement. Il combine les indicateurs disponibles mais ne tient pas compte de tout le contexte. À utiliser comme aide à la décision, jamais comme déclencheur automatique.</p>
  </div>
`;

function oppLabel(tag) {
  return { hot: '🔥 HOT', good: 'GOOD', neutral: 'NEUTRE', weak: 'FAIBLE', avoid: 'ÉVITER' }[tag] || '';
}

function oppDescription(tag) {
  return {
    hot:     'Forte conviction d\'opportunité — combinaison de signaux haussiers favorables',
    good:    'Signal globalement positif, sans surchauffe excessive',
    neutral: 'Pas de signal clair — à surveiller, attendre confirmation',
    weak:    'Plusieurs signaux baissiers, prudence',
    avoid:   'Forte conviction négative — éviter en l\'état actuel',
  }[tag] || '';
}

function renderOpportunitySection(opp) {
  if (!opp || opp.score == null) return '';
  const tag = opp.tag;
  const breakdown = opp.breakdown || {};
  const sorted = Object.entries(breakdown).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

  const labelMap = {
    position_52w:       'Position 52 semaines',
    perf_1m:            'Performance 1 mois',
    revenue_growth:     'Croissance du revenu',
    pe_ratio:           'P/E ratio',
    dividend:           'Dividende',
    pullback:           'Pullback du jour',
    overheated:         'Surchauffe du jour',
    rsi:                'RSI 14',
    macd_bullish:       'MACD bullish',
    macd_bearish:       'MACD bearish',
    golden_cross:       '🌟 Golden cross',
    death_cross:        '💀 Death cross',
    bollinger:          'Bollinger Bands',
    stochastic:         'Stochastic Oscillator',
    trend_aligned_up:   '📈 Tendance alignée haussière',
    trend_aligned_down: '📉 Tendance alignée baissière',
    trend_mostly_up:    '↗ Tendance majoritairement haussière',
    volatility:         'Volatilité',
    pullback_to_sma200: 'Retracement vers MM200',
    far_from_sma200:     'Très loin de la MM200',
    panic_drop:          '⚠️ Chute panique du jour',
    bearish_regime_cap:  '🚫 Régime baissier — score plafonné',
    consensus_oversold:  '💎 Consensus survente (6 indicateurs)',
    consensus_overbought:'🔥 Consensus surachat (6 indicateurs)',
    strong_uptrend:      '📈 Tendance haussière forte (R² élevé)',
    strong_downtrend:    '📉 Tendance baissière forte (R² élevé)',
    max_drawdown:        '🛡️ Résilience (max drawdown)',
    sharpe:              '⚖️ Sharpe ratio (rendement/risque)',
    sortino:             '⚖️ Sortino (rendement/risque baissier)',
    z_score:             '📊 Z-score (écart-type vs moyenne)',
    fresh_bounce:        '🚀 Rebond frais depuis le plus bas',
    acceleration:        '⚡ Accélération du prix',
    near_52w_high:       '🎯 Pic 52S récent (momentum)',
    faded_momentum:      '💨 Momentum essoufflé',
    news_sentiment:      '📰 Sentiment des news',
    analyst_consensus:   '🎓 Consensus analystes',
    analyst_trend:       '📊 Tendance recommandations',
    earnings_surprise:   '💰 Earnings surprises (beats vs misses)',
    macro_fear_regime:   '😱 VIX en panique (>35)',
    macro_stress:        '⚠️ Stress de marché (VIX 25-35)',
    macro_complacency:   '😴 Complaisance (VIX <13)',
    macro_news_positive: '📰 Actu macro positive',
    macro_news_negative: '📰 Actu macro négative',
    crisis_mode:         '⚠️ Mots-crise dans l\'actu',
    crisis_mode_strong:  '🚨 ALERTE CRISE — mots-clés guerre/krach intenses',
    // ── Nouveaux signaux v6 ──
    above_sma200:        'Au-dessus de la MM200',
    below_sma200:        'Sous la MM200',
    adx_trend:           '💪 ADX — trend directionnel puissant',
    structure_hh_hl:     '🪜 Structure haussière (plus hauts/bas ascendants)',
    structure_lh_ll:     '🪜 Structure baissière (plus hauts/bas descendants)',
    macd_momentum_up:    '⤴️ Momentum MACD en reprise',
    macd_momentum_down:  '⤵️ Momentum MACD s\'essouffle',
    obv_confirm:         '📊 Volume confirme la hausse (OBV)',
    obv_diverge:         '🚩 Hausse SANS volume (OBV divergent)',
    obv_confirm_down:    '📊 Volume confirme la baisse (OBV)',
    cmf_accumulation:    '🏦 Accumulation institutionnelle (CMF)',
    cmf_distribution:    '🏦 Distribution institutionnelle (CMF)',
    rsi_divergence_bull: '💎 Divergence RSI haussière (retournement probable)',
    rsi_divergence_bear: '⚠️ Divergence RSI baissière (essoufflement)',
    pullback_to_ema21:   'Repli vers EMA21 en tendance haussière',
    volume_breakout:     '🚀 Cassure confirmée par le volume',
    volume_capitulation: '🏳️ Capitulation vendeuse (fond probable)',
    volume_distribution: '📉 Grosse vente en haut de cycle',
    donchian_breakout:   '📈 Breakout canal Donchian 55j',
    donchian_low:        '📉 Plancher canal Donchian (rebond possible)',
    dividend_trap:       '🪤 Rendement anormal (piège à dividende)',
    megacap_stability:   '🏛️ Méga-cap (stabilité)',
    smallcap_risk:       '⚡ Small cap (risque accru)',
    consistency:         '📐 Régularité des jours haussiers',
    risk_adjustment:     '🛡️ Ajustement risque (ATR/volatilité)',
  };

  const pillarMeta = {
    trend:     { label: '📈 Tendance',  desc: 'Tendance de fond confirmée ?' },
    timing:    { label: '⏱️ Timing',    desc: 'Bon point d\'entrée maintenant ?' },
    quality:   { label: '🛡️ Qualité',   desc: 'Fondamentaux et stats saines ?' },
    sentiment: { label: '📰 Sentiment', desc: 'News et analystes positifs ?' },
  };
  const regimeMeta = {
    bull:    { label: '🐂 BULL',   cls: 'pos',     desc: 'Tendance haussière détectée — le momentum est pondéré plus fort' },
    bear:    { label: '🐻 BEAR',   cls: 'neg',     desc: 'Tendance baissière détectée — qualité et timing pondérés plus fort' },
    neutral: { label: '➖ NEUTRE', cls: 'neutral', desc: 'Pas de tendance dominante' },
  };

  const pillars = opp.pillars;
  const weights = opp.weights || {};
  const regime = regimeMeta[opp.regime] || null;
  const conf = opp.confidence;

  const pillarsHtml = pillars ? `
    <div class="opp-pillars">
      ${Object.entries(pillarMeta).map(([k, m]) => {
        const v = pillars[k];
        if (v == null) return '';
        const w = weights[k];
        const excluded = w === 0;
        const barCls = v >= 65 ? 'pos' : v <= 35 ? 'neg' : 'mid';
        return `
        <div class="opp-pillar ${excluded ? 'excluded' : ''}" title="${m.desc}${excluded ? ' (pas de données — exclu du calcul)' : w != null ? ` · poids ${Math.round(w * 100)}%` : ''}">
          <span class="opp-pillar-label">${m.label}</span>
          <div class="opp-pillar-bar"><div class="opp-pillar-fill ${barCls}" style="width:${excluded ? 0 : v}%"></div></div>
          <span class="opp-pillar-val">${excluded ? '—' : v}</span>
        </div>`;
      }).join('')}
    </div>` : '';

  const metaHtml = (regime || conf != null) ? `
    <div class="opp-meta">
      ${regime ? `<span class="opp-chip ${regime.cls}" title="${regime.desc}">Régime ${regime.label}</span>` : ''}
      ${conf != null ? `<span class="opp-chip ${conf >= 70 ? 'pos' : conf >= 45 ? 'neutral' : 'neg'}" title="Couverture des données (historique, volume, fondamentaux, sentiment). Confiance basse = signaux partiels, vérifier manuellement.">Confiance ${conf}%</span>` : ''}
    </div>` : '';

  return `
    <div class="opp-box">
      <div class="opp-box-title">
        🎯 Score d'opportunité
        <button class="help-btn" onclick="toggleHelp('helpOpportunity', this)" title="Comment ce score est calculé ?">?</button>
      </div>
      <div id="helpOpportunity" class="help-panel">${HELP_OPPORTUNITY}</div>
      <div class="opp-big">
        <div class="opp-score-circle ${tag}" style="--sc:${opp.score}"><span>${opp.score}</span></div>
        <div>
          <div class="opp-tag-big ${tag}">${oppLabel(tag)}</div>
          <div class="opp-tag-desc">${oppDescription(tag)}</div>
          ${metaHtml}
        </div>
      </div>
      ${pillarsHtml}
      <div class="opp-breakdown">
        ${sorted.map(([k, v]) => `
          <div class="opp-bd-row">
            <span class="opp-bd-label">${labelMap[k] || k}</span>
            <span class="opp-bd-val ${v >= 0 ? 'pos' : 'neg'}">${v >= 0 ? '+' : ''}${v}</span>
          </div>`).join('')}
      </div>
    </div>`;
}

// Mini badge pour les cartes
function oppBadge(opp) {
  if (!opp || opp.score == null) return '';
  const icon = { hot: '🔥', good: '↗', neutral: '–', weak: '↘', avoid: '⚠' }[opp.tag] || '';
  let tip = 'Score d\'opportunité — voir détails dans le modal';
  if (opp.pillars) {
    tip = `Tendance ${opp.pillars.trend} · Timing ${opp.pillars.timing} · Qualité ${opp.pillars.quality}`
        + (opp.weights && opp.weights.sentiment > 0 ? ` · Sentiment ${opp.pillars.sentiment}` : '')
        + (opp.confidence != null ? ` · Confiance ${opp.confidence}%` : '');
  }
  return `<span class="opp-badge ${opp.tag}" title="${tip}">${icon} ${opp.score}</span>`;
}

// Système d'aide générique — toggle d'un panneau par ID
function toggleHelp(id, btn) {
  const panel = document.getElementById(id);
  if (!panel) return;
  panel.classList.toggle('open');
  if (btn) btn.classList.toggle('active');
}

function initHelpPanels() {
  // Remplit les help panels statiques au démarrage
  const map = {
    helpNews:         HELP_NEWS_SENTIMENT,
    helpCalendar:     HELP_CALENDAR,
    helpCryptoGlobal: HELP_CRYPTO_GLOBAL,
    helpPortfolio:    HELP_PORTFOLIO,
    helpAllUniverse:  HELP_ALL_UNIVERSE,
  };
  for (const [id, content] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = content;
  }
}

const HELP_FUNDAMENTALS = `
  <div class="help-section">
    <h4>💰 Cap. boursière (Market Cap)</h4>
    <p>Valeur totale de l'entreprise en bourse = nombre d'actions × cours actuel. Donne la taille de la société.</p>
    <p><span class="help-tag neutral">&gt; 200 Md €</span> Mega cap (très grande entreprise stable)</p>
    <p><span class="help-tag neutral">10-200 Md €</span> Large cap</p>
    <p><span class="help-tag neutral">2-10 Md €</span> Mid cap (croissance potentielle)</p>
    <p><span class="help-tag neutral">&lt; 2 Md €</span> Small cap (plus volatile, plus risqué)</p>
  </div>
  <div class="help-section">
    <h4>📊 P/E · Price/Earnings (Ratio cours/bénéfice)</h4>
    <p>Combien d'années de bénéfices il faut pour "rembourser" le prix de l'action. Un P/E bas peut indiquer une action sous-évaluée, ou des problèmes.</p>
    <p><span class="help-tag buy">&lt; 15</span> Potentiellement sous-évaluée (ou secteur mature)</p>
    <p><span class="help-tag neutral">15-25</span> Valorisation moyenne</p>
    <p><span class="help-tag sell">&gt; 30</span> Forte croissance attendue, ou survalorisée</p>
    <p style="color:var(--text-dim);font-size:10px">À comparer avec la moyenne du secteur et les concurrents.</p>
  </div>
  <div class="help-section">
    <h4>💵 Dividende (Dividend Yield)</h4>
    <p>Rendement annuel du dividende exprimé en % du cours actuel. C'est le revenu passif que rapporte l'action chaque année.</p>
    <p><span class="help-tag neutral">0 %</span> Pas de dividende (entreprise réinvestit ses bénéfices, souvent tech/croissance)</p>
    <p><span class="help-tag buy">2-5 %</span> Bon rendement régulier</p>
    <p><span class="help-tag sell">&gt; 8 %</span> Très élevé — méfiance, peut indiquer un problème ou un cours qui s'effondre</p>
  </div>
  <div class="help-section">
    <h4>📈 Croissance du revenu (Revenue Growth YoY)</h4>
    <p>Évolution du chiffre d'affaires sur 12 mois glissants. Indique la dynamique de croissance de l'entreprise.</p>
    <p><span class="help-tag buy">&gt; 15 %</span> Forte croissance — typique de la tech</p>
    <p><span class="help-tag neutral">5-15 %</span> Croissance saine</p>
    <p><span class="help-tag sell">&lt; 0 %</span> Décroissance — vigilance</p>
  </div>
  <div class="help-section">
    <h4>📏 Fourchette 52 semaines</h4>
    <p>Prix le plus bas et le plus haut sur les 12 derniers mois. Le point blanc indique où se situe le prix actuel.</p>
    <p>Très près du bas (rouge) peut signaler une <strong>opportunité d'achat</strong> ou un problème durable.</p>
    <p>Très près du haut (vert) indique une force du titre, mais aussi un risque de prise de bénéfices.</p>
  </div>
`;

const HELP_NEWS_SENTIMENT = `
  <div class="help-section">
    <h4>📰 Détection du sentiment</h4>
    <p>Notre algorithme classe automatiquement chaque actualité en fonction des mots-clés présents dans le titre.</p>
    <p><span class="help-tag buy">Positif</span> Mots comme "gain", "surge", "rally", "growth", "beat", "boost"…</p>
    <p><span class="help-tag sell">Négatif</span> Mots comme "drop", "fall", "miss", "decline", "warn", "loss"…</p>
    <p><span class="help-tag neutral">Neutre</span> Aucun mot-clé dominant détecté</p>
    <p style="color:var(--text-dim);font-size:10px">⚠️ C'est une analyse lexicale basique, pas de l'IA sémantique. Toujours lire l'article complet pour une vraie compréhension.</p>
  </div>
`;

const HELP_CALENDAR = `
  <div class="help-section">
    <h4>🌐 Calendrier macro · Niveau d'impact</h4>
    <p>Indique l'importance attendue de l'évènement sur les marchés financiers.</p>
    <p><span class="help-tag sell">HIGH</span> Impact fort : décisions de taux (FOMC, BCE), CPI, NFP. À surveiller absolument.</p>
    <p><span class="help-tag neutral">MEDIUM</span> Impact modéré : indicateurs économiques importants (PMI, ventes, production)</p>
    <p><span class="help-tag buy">LOW</span> Impact faible : indicateurs secondaires, jours fériés régionaux</p>
  </div>
  <div class="help-section">
    <h4>💼 Calendrier earnings</h4>
    <p>Publications de résultats financiers des entreprises cotées. Ces dates créent souvent des mouvements importants.</p>
    <p>🌅 <strong>AVANT</strong> = avant l'ouverture du marché (08h30 ET / 14h30 CET)</p>
    <p>🌙 <strong>APRÈS</strong> = après la fermeture (16h00 ET / 22h00 CET)</p>
    <p><strong>EPS estimé</strong> = bénéfice par action prévu par les analystes. Le résultat réel sera comparé à cette estimation.</p>
    <p style="color:var(--text-dim);font-size:10px">Si EPS publié &gt; EPS estimé = beat (souvent positif pour le cours). Inverse = miss (souvent négatif).</p>
  </div>
`;

const HELP_CRYPTO_GLOBAL = `
  <div class="help-section">
    <h4>🌍 Cap. totale du marché crypto</h4>
    <p>Somme de la capitalisation de toutes les cryptomonnaies. Mesure la taille globale du marché crypto.</p>
  </div>
  <div class="help-section">
    <h4>📊 Dominance BTC / ETH</h4>
    <p>Part du Bitcoin (ou Ethereum) dans la capitalisation totale du marché crypto.</p>
    <p><span class="help-tag neutral">BTC haute (&gt; 50 %)</span> Marché plutôt prudent, on se réfugie sur Bitcoin</p>
    <p><span class="help-tag buy">BTC basse (&lt; 40 %)</span> "Altcoin season" — les autres cryptos surperforment</p>
    <p>Les variations de dominance signalent les rotations de capitaux entre BTC et le reste.</p>
  </div>
`;

const HELP_HEATMAP = `
  <div class="help-section">
    <h4>▣ Vue heatmap</h4>
    <p>Visualisation rapide des performances du jour en couleurs.</p>
    <p><span class="help-tag buy">Vert intense</span> Forte hausse du jour (&gt; +5 %)</p>
    <p><span class="help-tag buy">Vert pâle</span> Légère hausse (0 à +5 %)</p>
    <p><span class="help-tag sell">Rouge pâle</span> Légère baisse (-5 % à 0)</p>
    <p><span class="help-tag sell">Rouge intense</span> Forte baisse (&lt; -5 %)</p>
    <p>L'intensité de la couleur reflète l'amplitude du mouvement. Idéal pour repérer en un coup d'œil les meilleurs/pires performers.</p>
  </div>
`;

const HELP_INDICATORS = `
  <div class="help-section">
    <h4>📊 RSI · Relative Strength Index (14 jours)</h4>
    <p>Mesure la force d'une tendance sur une échelle de 0 à 100. Indique si le titre est suracheté ou survendu.</p>
    <p><span class="help-tag buy">&lt; 30</span> Survendu — signal d'achat potentiel (rebond probable)</p>
    <p><span class="help-tag neutral">30-70</span> Zone neutre — pas de signal clair</p>
    <p><span class="help-tag sell">&gt; 70</span> Suracheté — signal de vente potentiel (correction probable)</p>
  </div>
  <div class="help-section">
    <h4>📈 MACD · Moving Average Convergence Divergence (12, 26, 9)</h4>
    <p>Mesure l'écart entre 2 moyennes exponentielles (12 et 26 jours) pour détecter les retournements de tendance.</p>
    <p><span class="help-tag buy">Bullish</span> MACD &gt; Signal — momentum haussier, signal d'achat</p>
    <p><span class="help-tag sell">Bearish</span> MACD &lt; Signal — momentum baissier, signal de vente</p>
    <p style="color:var(--text-dim);font-size:10px">L'histogramme représente la différence (MACD − Signal). Plus il est élevé en valeur absolue, plus le momentum est fort.</p>
  </div>
  <div class="help-section">
    <h4>📏 Moyennes Mobiles (MM 50 / MM 200)</h4>
    <p>Moyenne du cours de clôture sur les 50 ou 200 derniers jours. Lissent les variations pour révéler la tendance de fond.</p>
    <p><span class="help-tag buy">Prix &gt; MM</span> Tendance haussière</p>
    <p><span class="help-tag sell">Prix &lt; MM</span> Tendance baissière</p>
    <p>🌟 <strong>Golden cross</strong> : MM50 passe au-dessus de la MM200 — signal haussier <strong>long terme</strong></p>
    <p>💀 <strong>Death cross</strong> : MM50 passe en-dessous de la MM200 — signal baissier long terme</p>
  </div>
  <div class="help-section" style="border-top:1px solid var(--border);padding-top:8px">
    <p style="color:var(--text-muted);font-style:italic;font-size:10px">⚠️ Ces indicateurs sont des outils statistiques, pas des prédictions. Combine-les toujours avec une analyse fondamentale et la gestion du risque. Aucun signal n'est fiable à 100 %.</p>
  </div>
`;

function renderIndicators(ind, currency) {
  if (!ind || Object.keys(ind).length === 0) return '';

  // RSI : <30 buy, >70 sell, sinon neutre
  let rsiSignal = 'neutral', rsiLabel = 'Neutre';
  if (ind.rsi != null) {
    if (ind.rsi < 30) { rsiSignal = 'buy'; rsiLabel = 'Survendu'; }
    else if (ind.rsi > 70) { rsiSignal = 'sell'; rsiLabel = 'Suracheté'; }
  }

  // MACD : croisement bullish/bearish
  let macdSignal = 'neutral', macdLabel = '—';
  if (ind.macd) {
    macdSignal = ind.macd.bullish ? 'buy' : 'sell';
    macdLabel = ind.macd.bullish ? 'Bullish' : 'Bearish';
  }

  // Moyennes mobiles
  const sma50Sig = ind.above_sma_50 == null ? 'neutral' : (ind.above_sma_50 ? 'buy' : 'sell');
  const sma200Sig = ind.above_sma_200 == null ? 'neutral' : (ind.above_sma_200 ? 'buy' : 'sell');

  return `
    <div class="indicators-box">
      <div class="indicators-title">
        📐 Indicateurs techniques
        <button class="help-btn" onclick="toggleHelp('helpIndicators', this)" title="C'est quoi ces indicateurs ?">?</button>
      </div>
      <div id="helpIndicators" class="help-panel">${HELP_INDICATORS}</div>
      <div class="indicators-grid">
        ${ind.rsi != null ? `
          <div class="ind-item signal-${rsiSignal}">
            <span class="ind-label">RSI (14)</span>
            <span class="ind-value">${ind.rsi.toFixed(1)} <span class="ind-sub ${rsiSignal==='buy'?'pos':rsiSignal==='sell'?'neg':''}">· ${rsiLabel}</span></span>
            <div class="rsi-bar"><div class="rsi-bar-dot" style="left:${ind.rsi}%"></div></div>
          </div>` : ''}
        ${ind.macd ? `
          <div class="ind-item signal-${macdSignal}">
            <span class="ind-label">MACD (12,26,9)</span>
            <span class="ind-value">${ind.macd.histogram.toFixed(3)} <span class="ind-sub ${macdSignal==='buy'?'pos':'neg'}">· ${macdLabel}</span></span>
            <span class="ind-sub">MACD: ${ind.macd.macd.toFixed(3)} · Signal: ${ind.macd.signal.toFixed(3)}</span>
          </div>` : ''}
        ${ind.sma_50 != null ? `
          <div class="ind-item signal-${sma50Sig}">
            <span class="ind-label">MM 50 jours</span>
            <span class="ind-value">${fmtPrice(ind.sma_50, currency)}</span>
            <span class="ind-sub ${sma50Sig==='buy'?'pos':'neg'}">Prix ${ind.above_sma_50 ? 'au-dessus' : 'en-dessous'}</span>
          </div>` : ''}
        ${ind.sma_200 != null ? `
          <div class="ind-item signal-${sma200Sig}">
            <span class="ind-label">MM 200 jours</span>
            <span class="ind-value">${fmtPrice(ind.sma_200, currency)}</span>
            <span class="ind-sub ${sma200Sig==='buy'?'pos':'neg'}">Prix ${ind.above_sma_200 ? 'au-dessus' : 'en-dessous'} ${ind.golden_cross !== null ? '· ' + (ind.golden_cross ? '🌟 Golden cross' : '💀 Death cross') : ''}</span>
          </div>` : ''}
      </div>
    </div>`;
}

function renderModalNews(news) {
  if (!news?.length) {
    return '<div class="modal-news-empty">Aucune actualité disponible<br><span style="font-size:10px;color:var(--text-muted)">(les news par ticker ne sont fournies que pour les actions US sur Finnhub gratuit)</span></div>';
  }
  return news.map(n => `
    <div class="modal-news-item" onclick="window.open('${esc(n.url)}','_blank','noopener')">
      <div class="modal-news-headline">${esc(n.headline)}</div>
      <div class="modal-news-meta">
        <span>${esc(n.source)}</span>
        <span>${n.datetime ? new Date(n.datetime * 1000).toLocaleDateString('fr-FR') : ''}</span>
      </div>
    </div>
  `).join('');
}

// État du graphique courant (pour interactivité hover)
let chartContext = null;

// Grand graphique du modal — SVG avec gradient + grille + axes + crosshair
function chartLarge(history) {
  if (!history || history.length < 2) {
    chartContext = null;
    return '<div class="modal-chart-empty">Aucune donnée historique pour cette période</div>';
  }
  const w = 920, h = 280;
  const padL = 50, padR = 12, padT = 16, padB = 24;
  const innerW = w - padL - padR;
  const innerH = h - padT - padB;

  const closes = history.map(p => p.c);
  const times  = history.map(p => p.t);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;

  const xOf = i => padL + (i / (history.length - 1)) * innerW;
  const yOf = v => padT + innerH - ((v - min) / range) * innerH;

  const points = history.map((p, i) => `${xOf(i).toFixed(1)},${yOf(p.c).toFixed(1)}`);
  const linePath = 'M ' + points.join(' L ');
  const areaPath = `${linePath} L ${xOf(history.length - 1)},${padT + innerH} L ${padL},${padT + innerH} Z`;

  const isUp = closes[closes.length - 1] >= closes[0];
  const color = isUp ? '#00ff88' : '#ff4444';
  const uid = 'chart_' + Math.random().toString(36).slice(2, 8);

  // Stocke le contexte pour le hover
  chartContext = {
    history, w, h, padL, padR, padT, padB, innerW, innerH, min, max, range, color,
  };

  // Niveaux de prix horizontaux (grille + labels)
  const ticks = 4;
  const gridLines = [];
  const yLabels = [];
  for (let i = 0; i <= ticks; i++) {
    const v = min + (range * (ticks - i) / ticks);
    const y = yOf(v);
    gridLines.push(`<line class="chart-grid-line" x1="${padL}" y1="${y}" x2="${w - padR}" y2="${y}"/>`);
    yLabels.push(`<text class="chart-axis-label" x="${padL - 6}" y="${y + 3}" text-anchor="end">${v >= 1000 ? v.toFixed(0) : v.toFixed(2)}</text>`);
  }

  // Labels temporels
  const timeLabels = [];
  const nTimeLabels = 5;
  for (let i = 0; i < nTimeLabels; i++) {
    const idx = Math.floor((i / (nTimeLabels - 1)) * (history.length - 1));
    const t = times[idx];
    const x = xOf(idx);
    timeLabels.push(`<text class="chart-axis-label" x="${x}" y="${h - 8}" text-anchor="middle">${formatTimestamp(t)}</text>`);
  }

  return `
    <svg id="chartSvg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="cursor:crosshair">
      <defs>
        <linearGradient id="${uid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stop-color="${color}" stop-opacity="0.35"/>
          <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${gridLines.join('')}
      <path d="${areaPath}" fill="url(#${uid})"/>
      <path d="${linePath}" stroke="${color}" stroke-width="1.8" fill="none" stroke-linejoin="round"/>
      ${yLabels.join('')}
      ${timeLabels.join('')}
      <!-- Capture zone pour les events souris (transparente, couvre toute la zone) -->
      <rect id="chartHoverZone" x="${padL}" y="${padT}" width="${innerW}" height="${innerH}" fill="transparent"/>
      <!-- Crosshair (caché par défaut) -->
      <g id="chartCrosshair" style="display:none;pointer-events:none">
        <line id="crosshairV" y1="${padT}" y2="${padT + innerH}" stroke="#888" stroke-width="0.8" stroke-dasharray="3,3"/>
        <line id="crosshairH" x1="${padL}" x2="${w - padR}" stroke="#888" stroke-width="0.8" stroke-dasharray="3,3"/>
        <circle id="crosshairDot" r="5" fill="${color}" stroke="#fff" stroke-width="2"/>
      </g>
    </svg>
    <div id="chartTooltip" class="chart-tooltip" style="display:none">
      <div class="chart-tooltip-date" id="chartTooltipDate"></div>
      <div class="chart-tooltip-price" id="chartTooltipPrice"></div>
    </div>`;
}

function formatTimestamp(t, withTime = false) {
  if (!t) return '';
  const d = new Date(t * 1000);
  if (withTime) {
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) + ' ' +
           d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

// Attache les events souris au graphique (appelé après le rendu HTML)
function attachChartHover(currency) {
  const svg = document.getElementById('chartSvg');
  if (!svg || !chartContext) return;

  const zone      = document.getElementById('chartHoverZone');
  const tooltip   = document.getElementById('chartTooltip');
  const crosshair = document.getElementById('chartCrosshair');
  const cV   = document.getElementById('crosshairV');
  const cH   = document.getElementById('crosshairH');
  const cDot = document.getElementById('crosshairDot');
  const tDate  = document.getElementById('chartTooltipDate');
  const tPrice = document.getElementById('chartTooltipPrice');

  const intraday = currentModalPeriod === '1d' || currentModalPeriod === '5d';

  const handleMove = (e) => {
    const rect = svg.getBoundingClientRect();
    // Position souris dans le viewBox SVG
    const xSvg = ((e.clientX - rect.left) / rect.width) * chartContext.w;
    const { history, padL, innerW, padT, innerH, min, range } = chartContext;

    // Index du point le plus proche
    const fraction = Math.max(0, Math.min(1, (xSvg - padL) / innerW));
    const idx = Math.round(fraction * (history.length - 1));
    const point = history[idx];
    if (!point) return;

    const x = padL + (idx / (history.length - 1)) * innerW;
    const y = padT + innerH - ((point.c - min) / range) * innerH;

    cV.setAttribute('x1', x);
    cV.setAttribute('x2', x);
    cH.setAttribute('y1', y);
    cH.setAttribute('y2', y);
    cDot.setAttribute('cx', x);
    cDot.setAttribute('cy', y);
    crosshair.style.display = '';

    // Tooltip
    tDate.textContent = formatTimestamp(point.t, intraday);
    tPrice.textContent = fmtPrice(point.c, currency);

    // Position du tooltip relatif au container
    const container = svg.parentElement;
    const containerRect = container.getBoundingClientRect();
    const xRelMouse = e.clientX - containerRect.left;
    const yRelMouse = e.clientY - containerRect.top;
    const ttWidth  = tooltip.offsetWidth  || 130;
    const ttHeight = tooltip.offsetHeight || 50;
    let tx = xRelMouse + 14;
    let ty = yRelMouse - ttHeight - 10;
    if (tx + ttWidth > containerRect.width)  tx = xRelMouse - ttWidth - 14;
    if (ty < 0)                              ty = yRelMouse + 16;
    tooltip.style.display = 'block';
    tooltip.style.left = tx + 'px';
    tooltip.style.top  = ty + 'px';
  };

  zone.addEventListener('mousemove', handleMove);
  zone.addEventListener('mouseleave', () => {
    crosshair.style.display = 'none';
    tooltip.style.display = 'none';
  });
}

function changePeriod(period) {
  currentModalPeriod = period;
  loadStockDetail();
}

function closeModal(e) {
  if (e && e.target.id !== 'modalBackdrop') return;
  document.getElementById('modalBackdrop').classList.remove('open');
  currentModalSymbol = null;
  currentCryptoId = null;
}

// ── Modal détail crypto ──────────────────────────────────────────────
let currentCryptoId = null;
let currentCryptoPeriod = '30';

async function openCryptoDetail(coinId) {
  if (!coinId) return;
  currentCryptoId = coinId;
  currentCryptoPeriod = '30';
  document.getElementById('modalBackdrop').classList.add('open');
  document.getElementById('modalContent').innerHTML =
    '<div class="loading-placeholder"><span class="spinner"></span>Chargement…</div>';
  await loadCryptoDetail();
}

async function loadCryptoDetail() {
  try {
    const r = await fetch(`${API}/api/crypto-detail/${encodeURIComponent(currentCryptoId)}?period=${currentCryptoPeriod}`);
    const j = await r.json();
    if (j.status !== 'ok') {
      document.getElementById('modalContent').innerHTML = `<div class="error-card">${esc(j.message || 'Erreur')}</div>`;
      return;
    }
    renderCryptoDetail(j.data);
  } catch (e) {
    document.getElementById('modalContent').innerHTML = `<div class="error-card">Erreur réseau</div>`;
  }
}

function changeCryptoPeriod(p) {
  currentCryptoPeriod = p;
  loadCryptoDetail();
}

function renderCryptoDetail(d) {
  const cc = cls(d.change_24h);
  const periods = [
    {k:'1',   l:'1J'}, {k:'7', l:'7J'}, {k:'30', l:'30J'},
    {k:'90',  l:'3M'}, {k:'365', l:'1A'}, {k:'max', l:'Max'},
  ];

  const supply = d.circulating ? `${(d.circulating/1e6).toFixed(2)} M ${d.symbol}` : '—';
  const maxS = d.max_supply ? `${(d.max_supply/1e6).toFixed(2)} M` : '∞';

  document.getElementById('modalContent').innerHTML = `
    <div class="modal-header">
      <div class="modal-title-row">
        <div class="modal-ticker">
          ${d.image ? `<img src="${esc(d.image)}" width="32" height="32" style="border-radius:50%;vertical-align:middle"/>` : ''}
          ${d.symbol}
          <button class="modal-header-star ${isInWatchlist(d.symbol) ? 'active' : ''}" onclick="toggleWatchlist('${esc(d.symbol)}','${esc(d.name)}')" title="${isInWatchlist(d.symbol) ? 'Retirer des favoris' : 'Ajouter aux favoris'}">${isInWatchlist(d.symbol) ? '★' : '☆'}</button>
          ${d.rank ? `<span style="font-size:11px;color:var(--text-muted);font-weight:500">#${d.rank}</span>` : ''}
          ${d.tr === false ? '<span class="off-tr-badge">✕TR</span>' : ''}
        </div>
        <div class="modal-name">${esc(d.name)}</div>
      </div>
      <div class="modal-price-col">
        <div class="modal-price">${fmtPrice(d.price, 'EUR')}</div>
        <div class="modal-change ${cc}">${fmtChange(d.change_24h)} <span style="opacity:0.6">24h</span></div>
      </div>
    </div>

    <div class="period-tabs">
      ${periods.map(p => `
        <button class="period-tab ${p.k === d.period ? 'active' : ''}" onclick="changeCryptoPeriod('${p.k}')">${p.l}</button>
      `).join('')}
    </div>

    <div class="modal-chart">
      ${chartLarge(d.history)}
    </div>

    <div class="modal-cols">
      <div class="modal-fund">
        <div class="modal-fund-title">Statistiques de marché</div>
        <div class="modal-fund-grid">
          ${fundItem('Cap. marché', d.market_cap ? fmtCap(d.market_cap, 'EUR') : '—')}
          ${fundItem('Volume 24h', d.volume_24h ? fmtCap(d.volume_24h, 'EUR') : '—')}
          ${fundItem('Plus haut 24h', d.high_24h ? fmtPrice(d.high_24h, 'EUR') : '—')}
          ${fundItem('Plus bas 24h', d.low_24h ? fmtPrice(d.low_24h, 'EUR') : '—')}
          ${fundItem('ATH', d.ath ? fmtPrice(d.ath, 'EUR') : '—')}
          ${fundItem('Depuis ATH', d.ath_change != null ? fmtChange(d.ath_change) : '—', cls(d.ath_change))}
          ${fundItem('Variation 7j', d.change_7d != null ? fmtChange(d.change_7d) : '—', cls(d.change_7d))}
          ${fundItem('Variation 1A', d.change_1y != null ? fmtChange(d.change_1y) : '—', cls(d.change_1y))}
          ${fundItem('Supply circulant', supply)}
          ${fundItem('Supply max', maxS)}
        </div>
        <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
          <a href="https://www.coingecko.com/en/coins/${encodeURIComponent(d.id)}" target="_blank" rel="noopener" class="period-tab" style="text-decoration:none">CoinGecko ↗</a>
          ${d.homepage ? `<a href="${esc(d.homepage)}" target="_blank" rel="noopener" class="period-tab" style="text-decoration:none">Site officiel ↗</a>` : ''}
          ${d.tr !== false ? `<a href="https://traderepublic.com/fr/crypto/${encodeURIComponent(d.symbol.toLowerCase())}" target="_blank" rel="noopener" class="period-tab" style="text-decoration:none">Trade Republic ↗</a>` : ''}
        </div>

        ${renderBuySimForm(d.symbol, d.name, d.price, 'EUR')}

        ${renderAlertSection(d.symbol, d.name, d.price, 'EUR').outerHTML}
      </div>

      <div class="modal-news" style="max-height:380px">
        <div class="modal-news-title">À propos de ${d.symbol}</div>
        <div style="font-size:11px;color:var(--text);line-height:1.6;padding:4px 0">
          ${d.description ? esc(d.description).replace(/\n/g, '<br>') + '…' : '<span style="color:var(--text-muted)">Aucune description disponible</span>'}
        </div>
      </div>
    </div>
  `;

  attachChartHover('EUR');
}

// Échap pour fermer
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

// ══════════════════════════════════════════════════════════════════════
//   RECHERCHE
// ══════════════════════════════════════════════════════════════════════

let searchDebounce = null;
let searchHighlight = -1;

// Ouvre/ferme le dropdown de recherche en gardant aria-expanded synchro (a11y).
function setSearchOpen(open) {
  const dropdown = document.getElementById('searchDropdown');
  const input = document.getElementById('searchInput');
  if (!dropdown) return;
  dropdown.classList.toggle('open', open);
  if (input) input.setAttribute('aria-expanded', open ? 'true' : 'false');
}

function initSearch() {
  const input = document.getElementById('searchInput');
  const dropdown = document.getElementById('searchDropdown');
  if (!input || !dropdown) return;

  input.addEventListener('input', () => {
    clearTimeout(searchDebounce);
    const q = input.value.trim();
    if (!q) { setSearchOpen(false); dropdown.innerHTML = ''; return; }
    searchDebounce = setTimeout(() => runSearch(q), 250);
  });

  input.addEventListener('keydown', (e) => {
    const items = dropdown.querySelectorAll('.search-item');
    if (!items.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      searchHighlight = Math.min(items.length - 1, searchHighlight + 1);
      updateHighlight(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      searchHighlight = Math.max(0, searchHighlight - 1);
      updateHighlight(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const target = searchHighlight >= 0 ? items[searchHighlight] : items[0];
      if (target) target.click();
    } else if (e.key === 'Escape') {
      setSearchOpen(false);
      input.blur();
    }
  });

  // Fermer en cliquant ailleurs
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-wrap')) setSearchOpen(false);
  });
}

function updateHighlight(items) {
  items.forEach((it, i) => it.classList.toggle('highlighted', i === searchHighlight));
}

async function runSearch(q) {
  const dropdown = document.getElementById('searchDropdown');
  try {
    const r = await fetch(`${API}/api/search?q=${encodeURIComponent(q)}`);
    const json = await r.json();
    const items = json.status === 'ok' ? (json.data || []) : [];
    searchHighlight = -1;

    if (!items.length) {
      dropdown.innerHTML = '<div class="search-empty">Aucun résultat</div>';
    } else {
      dropdown.innerHTML = items.map(it => `
        <div class="search-item" onclick="pickSearchResult('${esc(it.symbol)}')">
          <span class="search-item-symbol">${esc(it.symbol)}</span>
          <span class="search-item-name">${esc(it.name)}</span>
          <span class="search-item-exch">${esc(it.exchange || it.type || '')}</span>
          <button class="star-btn ${isInWatchlist(it.symbol) ? 'active' : ''}" style="position:static;margin-left:8px" onclick="event.stopPropagation();toggleWatchlist('${esc(it.symbol)}','${esc(it.name)}')" title="Ajouter à ma watchlist">${isInWatchlist(it.symbol) ? '★' : '☆'}</button>
        </div>
      `).join('');
    }
    setSearchOpen(true);
  } catch (e) {
    dropdown.innerHTML = '<div class="search-empty">Erreur — réessayez</div>';
    setSearchOpen(true);
  }
}

function pickSearchResult(symbol) {
  setSearchOpen(false);
  document.getElementById('searchInput').value = '';
  openStockDetail(symbol);
}

// ══════════════════════════════════════════════════════════════════════
//   PORTEFEUILLE SIMULÉ
// ══════════════════════════════════════════════════════════════════════

const HELP_ALL_UNIVERSE = `
  <div class="help-section">
    <h4>🌐 L'univers complet</h4>
    <p>Cette section affiche <strong>toutes les actions disponibles</strong> dans nos watchlists combinées (~280 tickers), sans aucune limite de tri ni présélection.</p>
    <p>Pratique pour :</p>
    <p>• Trouver des opportunités <strong>en dehors des top 40</strong> que les sections principales mettent en avant</p>
    <p>• Faire une recherche <strong>par secteur</strong> ou <strong>par région</strong> sur l'ensemble du parc</p>
    <p>• Trier l'univers entier par 🎯 Score d'opportunité pour repérer les pépites</p>
    <p style="color:var(--text-dim);font-size:10px">Par défaut affiché en <strong>vue compacte</strong> (tableau) — plus lisible avec ~280 lignes.</p>
  </div>
`;

const HELP_PORTFOLIO = `
  <div class="help-section">
    <h4>💼 À quoi sert ce portefeuille ?</h4>
    <p>Suivez des positions <strong>fictives</strong> pour mesurer la performance de vos idées d'investissement sans engager d'argent réel.</p>
    <p>Chaque position est composée d'un ticker, d'une quantité d'actions et d'un prix d'achat. Le P&L (Profit &amp; Loss) est calculé en temps réel selon le cours actuel.</p>
    <p style="color:var(--text-dim);font-size:10px">⚠️ Tout est stocké dans votre navigateur (localStorage). Aucune donnée n'est envoyée à un serveur. Si vous changez d'appareil ou videz le cache, vos positions sont perdues.</p>
  </div>
  <div class="help-section">
    <h4>📊 Comment ajouter une position ?</h4>
    <p>Ouvrez le détail d'une action (clic sur n'importe quelle carte) et saisissez la quantité + le prix d'achat dans la section "💼 Ajouter au portefeuille simulé".</p>
  </div>
`;

function getPositions() {
  try { return JSON.parse(localStorage.getItem('portfolio') || '[]'); } catch { return []; }
}
function setPositions(arr) { localStorage.setItem('portfolio', JSON.stringify(arr)); }

function addPosition(symbol, name, quantity, buyPrice, currency) {
  const positions = getPositions();
  positions.push({
    id: Date.now() + Math.random(),
    symbol, name,
    quantity: Number(quantity),
    buyPrice: Number(buyPrice),
    buyDate: new Date().toISOString().slice(0, 10),
    currency: currency || 'USD',
  });
  setPositions(positions);
}

function removePosition(id) {
  if (!confirm('Supprimer cette position du portefeuille ?')) return;
  setPositions(getPositions().filter(p => p.id != id));
  loadPortfolio();
}

async function loadPortfolio() {
  const positions = getPositions();
  const section = document.getElementById('portfolioSection');
  if (!positions.length) { section.style.display = 'none'; return; }
  section.style.display = '';

  // Fetch prix actuels
  const symbols = [...new Set(positions.map(p => p.symbol))].join(',');
  try {
    const r = await fetch(`${API}/api/watchlist?symbols=${encodeURIComponent(symbols)}`);
    const j = await r.json();
    if (j.status !== 'ok') return;
    const priceMap = Object.fromEntries(j.data.map(s => [s.ticker, s]));

    // Enrichit chaque position
    const enriched = positions.map(p => {
      const stock = priceMap[p.symbol];
      const currentPrice = stock?.price ?? p.buyPrice;
      const value = currentPrice * p.quantity;
      const cost  = p.buyPrice    * p.quantity;
      const pnl   = value - cost;
      const pnlPct = cost ? (pnl / cost) * 100 : 0;
      return { ...p, currentPrice, value, cost, pnl, pnlPct,
        todayChange: stock?.change_pct ?? 0,
        opportunity: stock?.opportunity };
    });

    // Conversion EUR pour totaux globaux
    let totalValueEUR = 0, totalCostEUR = 0;
    for (const e of enriched) {
      const valEUR  = convertToEURRaw(e.value, e.currency);
      const costEUR = convertToEURRaw(e.cost,  e.currency);
      totalValueEUR += valEUR;
      totalCostEUR  += costEUR;
    }
    const totalPnl = totalValueEUR - totalCostEUR;
    const totalPnlPct = totalCostEUR ? (totalPnl / totalCostEUR) * 100 : 0;

    renderPortfolioSummary(totalValueEUR, totalCostEUR, totalPnl, totalPnlPct, enriched.length);
    renderPortfolioList(enriched);
  } catch (e) {
    console.warn('loadPortfolio error:', e);
  }
}

// Conversion EUR raw (sans format) — utilisée pour les totaux
function convertToEURRaw(value, currency) {
  if (!value || currency === 'EUR') return value;
  if (currency === 'GBp' && state.forex.GBP) return (value / 100) * state.forex.GBP;
  const rate = state.forex[currency];
  return rate ? value * rate : value;
}

function renderPortfolioSummary(totalValue, totalCost, pnl, pnlPct, count) {
  const cls = pnl >= 0 ? 'pos' : 'neg';
  document.getElementById('portfolioSummary').innerHTML = `
    <div class="pf-stat">
      <span class="pf-stat-label">Valeur actuelle</span>
      <span class="pf-stat-val">${fmtPrice(totalValue, 'EUR')}</span>
      <span class="pf-stat-sub">Coût d'achat : ${fmtPrice(totalCost, 'EUR')}</span>
    </div>
    <div class="pf-stat">
      <span class="pf-stat-label">P&amp;L total</span>
      <span class="pf-stat-val ${cls}">${pnl >= 0 ? '+' : ''}${fmtPrice(pnl, 'EUR')}</span>
      <span class="pf-stat-sub ${cls}" style="color:${pnl>=0?'var(--green)':'var(--red)'}">${fmtChange(pnlPct)}</span>
    </div>
    <div class="pf-stat">
      <span class="pf-stat-label">Positions</span>
      <span class="pf-stat-val">${count}</span>
      <span class="pf-stat-sub">${count > 1 ? 'lignes' : 'ligne'}</span>
    </div>
  `;
}

function renderPortfolioList(positions) {
  const rows = positions.map(p => {
    const pnlCls = p.pnl >= 0 ? 'pos' : 'neg';
    const dayCls = p.todayChange >= 0 ? 'pos' : 'neg';
    return `
      <div class="pf-row" onclick="openStockDetail('${esc(p.symbol)}')">
        <div class="pf-cell bold">${p.symbol}</div>
        <div class="pf-cell dim" style="max-width:180px;overflow:hidden;text-overflow:ellipsis">${esc(p.name)}</div>
        <div class="pf-cell right">${p.quantity}</div>
        <div class="pf-cell right dim">${fmtPrice(p.buyPrice, p.currency)}</div>
        <div class="pf-cell right">${fmtPrice(p.currentPrice, p.currency)}</div>
        <div class="pf-cell right ${dayCls}">${fmtChange(p.todayChange)}</div>
        <div class="pf-cell right bold">${fmtPrice(p.value, p.currency)}</div>
        <div class="pf-cell right ${pnlCls}">${p.pnl >= 0 ? '+' : ''}${fmtPrice(p.pnl, p.currency)}</div>
        <div class="pf-cell right ${pnlCls}">${fmtChange(p.pnlPct)}</div>
        <div class="pf-cell">${oppBadge(p.opportunity)}</div>
        <div class="pf-cell"><span onclick="event.stopPropagation();toggleWatchlist('${esc(p.symbol)}','${esc(p.name)}')" style="cursor:pointer;color:${isInWatchlist(p.symbol)?'var(--yellow)':'var(--text-muted)'};font-size:14px;padding:0 4px">${isInWatchlist(p.symbol)?'★':'☆'}</span></div>
        <div class="pf-cell"><button class="pf-action-btn" onclick="event.stopPropagation();removePosition(${p.id})">✕</button></div>
      </div>`;
  }).join('');

  document.getElementById('portfolioList').innerHTML = `
    <div class="pf-table">
      <div class="pf-row head">
        <div class="pf-cell">Ticker</div>
        <div class="pf-cell">Nom</div>
        <div class="pf-cell right">Qté</div>
        <div class="pf-cell right">Prix achat</div>
        <div class="pf-cell right">Cours</div>
        <div class="pf-cell right">Jour %</div>
        <div class="pf-cell right">Valeur</div>
        <div class="pf-cell right">P&amp;L €</div>
        <div class="pf-cell right">P&amp;L %</div>
        <div class="pf-cell">🎯 Score</div>
        <div class="pf-cell">⭐</div>
        <div class="pf-cell"></div>
      </div>
      ${rows}
    </div>`;
}

// Ajouter depuis le modal détail
function renderBuySimForm(symbol, name, currentPrice, currency) {
  return `
    <div class="alert-box">
      <div class="alert-title">💼 Ajouter au portefeuille simulé</div>
      <div class="buy-sim-form">
        <input type="number" step="any" id="buyQty_${symbol}" placeholder="Quantité" />
        <input type="number" step="any" id="buyPrice_${symbol}" placeholder="${currentPrice ? currentPrice.toFixed(2) : 'Prix'}" value="${currentPrice ? currentPrice.toFixed(2) : ''}" />
        <span style="font-size:11px;color:var(--text-dim)">${currency}</span>
        <button onclick="addPositionFromModal('${esc(symbol)}','${esc(name)}','${currency}')">+ Acheter (simu)</button>
      </div>
    </div>`;
}

function addPositionFromModal(symbol, name, currency) {
  const qty = parseFloat(document.getElementById('buyQty_' + symbol).value);
  const price = parseFloat(document.getElementById('buyPrice_' + symbol).value);
  if (isNaN(qty) || qty <= 0 || isNaN(price) || price <= 0) {
    alert('Saisis une quantité et un prix valides');
    return;
  }
  addPosition(symbol, name, qty, price, currency);
  loadPortfolio();
  document.getElementById('buyQty_' + symbol).value = '';
  // Feedback visuel
  const btn = event.target;
  const oldText = btn.textContent;
  btn.textContent = '✓ Ajouté !';
  setTimeout(() => { btn.textContent = oldText; }, 1500);
}

// ══════════════════════════════════════════════════════════════════════
//   ALERTES PRIX
// ══════════════════════════════════════════════════════════════════════

function getAlerts() {
  try { return JSON.parse(localStorage.getItem('alerts') || '[]'); } catch { return []; }
}
function setAlerts(arr) { localStorage.setItem('alerts', JSON.stringify(arr)); }

function addAlert(symbol, name, direction, threshold, currency) {
  const alerts = getAlerts();
  alerts.push({
    id: Date.now() + Math.random(),
    symbol, name, direction, threshold: Number(threshold),
    currency: currency || 'USD',
    triggered: false,
    created: Date.now(),
  });
  setAlerts(alerts);
}

function removeAlert(id) {
  setAlerts(getAlerts().filter(a => a.id != id));
  if (currentModalSymbol) refreshAlertSection(currentModalSymbol);
}

function alertsFor(symbol) {
  return getAlerts().filter(a => a.symbol === symbol);
}

async function requestNotifPermission() {
  if (!('Notification' in window)) return false;
  if (Notification.permission === 'granted') return true;
  if (Notification.permission === 'denied') return false;
  const r = await Notification.requestPermission();
  return r === 'granted';
}

function fireNotification(alert, currentPrice) {
  const dirLabel = alert.direction === 'above' ? 'a dépassé' : 'est passé sous';
  const body = `${alert.name} ${dirLabel} ${alert.threshold} ${alert.currency} · Actuel: ${currentPrice.toFixed(2)}`;
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(`🔔 ${alert.symbol} — alerte prix`, { body, icon: '/static/favicon.ico', tag: 'alert-' + alert.id });
  }
  // Aussi dans la console + indication visuelle si Notification refusé
  console.log(`[ALERTE] ${alert.symbol}: ${body}`);
}

async function checkAlerts() {
  const alerts = getAlerts().filter(a => !a.triggered);
  if (!alerts.length) return updateAlertBadge();

  // Récupère les prix actuels pour les tickers concernés
  const symbols = [...new Set(alerts.map(a => a.symbol))];
  try {
    const r = await fetch(`${API}/api/watchlist?symbols=${encodeURIComponent(symbols.join(','))}`);
    const j = await r.json();
    if (j.status !== 'ok') return;
    const priceMap = Object.fromEntries(j.data.map(s => [s.ticker, s.price]));

    let triggered = 0;
    const all = getAlerts();
    for (const a of all) {
      if (a.triggered) continue;
      const p = priceMap[a.symbol];
      if (p == null) continue;
      if ((a.direction === 'above' && p >= a.threshold) ||
          (a.direction === 'below' && p <= a.threshold)) {
        a.triggered = true;
        a.triggeredAt = Date.now();
        a.triggeredPrice = p;
        fireNotification(a, p);
        triggered++;
      }
    }
    if (triggered) setAlerts(all);
    updateAlertBadge();
  } catch (e) {
    console.warn('checkAlerts error:', e);
  }
}

function updateAlertBadge() {
  const btn = document.getElementById('refreshBtn');
  if (!btn) return;
  const triggered = getAlerts().filter(a => a.triggered).length;
  // Retire l'ancien badge
  btn.querySelectorAll('.alert-badge').forEach(b => b.remove());
  if (triggered > 0) {
    const badge = document.createElement('span');
    badge.className = 'alert-badge';
    badge.textContent = '🔔 ' + triggered;
    btn.appendChild(badge);
  }
}

function refreshAlertSection(symbol) {
  const container = document.getElementById('alertSection_' + symbol);
  if (container) container.innerHTML = renderAlertSection(symbol).querySelector('.alert-box').innerHTML;
}

function renderAlertSection(symbol, name, currentPrice, currency) {
  const alerts = alertsFor(symbol);
  const div = document.createElement('div');
  div.id = 'alertSection_' + symbol;
  div.innerHTML = `
    <div class="alert-box">
      <div class="alert-title">🔔 Mes alertes pour ${symbol}</div>
      <div class="alert-form">
        <select id="alertDir_${symbol}">
          <option value="above">Au-dessus de</option>
          <option value="below">En dessous de</option>
        </select>
        <input type="number" step="any" id="alertVal_${symbol}" placeholder="${currentPrice ? currentPrice.toFixed(2) : '0'}" />
        <span style="font-size:11px;color:var(--text-dim)">${currency}</span>
        <button onclick="createAlert('${esc(symbol)}','${esc(name)}','${currency}')">Créer</button>
      </div>
      <div class="alert-list">
        ${alerts.length ? alerts.map(a => `
          <div class="alert-item ${a.triggered ? 'triggered' : ''}">
            <span class="alert-text">
              ${a.triggered ? '✓ Déclenchée à ' + a.triggeredPrice.toFixed(2) + ' · ' : ''}
              Si <strong>${a.direction === 'above' ? '≥' : '≤'} ${a.threshold} ${a.currency}</strong>
            </span>
            <button class="alert-delete" onclick="removeAlert(${a.id})">✕</button>
          </div>`).join('') : '<div style="font-size:10px;color:var(--text-muted);font-style:italic">Aucune alerte. Créez-en une ci-dessus.</div>'}
      </div>
    </div>`;
  return div;
}

async function createAlert(symbol, name, currency) {
  const dir = document.getElementById('alertDir_' + symbol).value;
  const val = parseFloat(document.getElementById('alertVal_' + symbol).value);
  if (isNaN(val) || val <= 0) { alert('Saisis un prix valide'); return; }
  await requestNotifPermission();
  addAlert(symbol, name, dir, val, currency);
  refreshAlertSection(symbol);
  updateAlertBadge();
}

// ══════════════════════════════════════════════════════════════════════
//   MODE TV (plein écran)
// ══════════════════════════════════════════════════════════════════════

function toggleTVMode() {
  const body = document.body;
  const isOn = body.classList.toggle('tv-mode');
  localStorage.setItem('tv_mode', isOn ? '1' : '0');
  if (isOn) {
    // Active le plein écran natif
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    }
    // Active auto-refresh 1 min minimum
    const sel = document.getElementById('autoRefreshSelect');
    if (sel && parseInt(sel.value) === 0) {
      setAutoRefresh(60);
    }
  } else {
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }
  }
}

// Init
if (localStorage.getItem('tv_mode') === '1') {
  document.body.classList.add('tv-mode');
}

// ── Init ─────────────────────────────────────────────────────────────
updateTRButton();
updateEURButton();
initHelpPanels();
renderHistoryBar();
initSearch();
loadForex().then(fetchAll);
loadIndices();
loadCalendar();
loadCryptoGlobal();
loadWatchlistSection();
loadPortfolio();
initAutoRefresh();

// Check alerts toutes les 60s + au démarrage
updateAlertBadge();
checkAlerts();
setInterval(checkAlerts, 60_000);
