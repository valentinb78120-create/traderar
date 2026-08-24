# 🛣️ TradeRadar — Roadmap

> Mettre à jour cette case après chaque étape : `[ ]` → `[x]`

---

# ✅ Phase 1 — Dashboard de base (TERMINÉE)

## 🎯 Priorité 1 — Combler ce qui manque

- [x] **1.1** Sparklines + vraie fourchette 52 semaines (via Twelve Data) ✅
- [x] **1.2** Capitalisation, P/E ratio et fondamentaux (Finnhub `/stock/profile2` + `/stock/metric`) ✅ *(US uniquement en gratuit)*
- [x] **1.3** Section "Top Gainers / Top Losers" du jour ✅

## 🎯 Priorité 2 — Plus d'interactivité

- [x] **2.1** Clic sur une action → modal détail (graphique 1J/1S/1M/1A + actus de l'action) ✅
- [x] **2.2** Barre de recherche pour ajouter un ticker à la volée ✅
- [x] **2.3** Watchlists personnalisées sauvegardées en `localStorage` ✅
- [x] **2.4** Tri et filtres (par %, nom, cap, secteur ; filtre EU/US) ✅

## 🎯 Priorité 3 — Visuel et UX

- [x] **3.1** Vue heatmap (style Finviz) ✅
- [x] **3.2** Toggle "Tout en EUR" (avec conversion forex) ✅
- [x] **3.3** Auto-refresh configurable (1 / 5 / 15 min) ✅
- [x] **3.4** Mode compact / détaillé (vue tableau dense vs cartes) ✅

## 🎯 Priorité 4 — Nouvelles sections

- [x] **4.1** Bandeau indices majeurs en haut (CAC 40, S&P 500, DAX, Nasdaq, Nikkei) ✅
- [x] **4.2** Section Forex & matières premières (EUR/USD, Or, Pétrole) ✅
- [x] **4.3** Calendrier économique (FOMC, BCE, earnings) ✅
- [x] **4.4** Crypto étendue (graphique 24h/7j + dominance BTC) ✅

## 🎯 Priorité 5 — Fonctionnalités "smart"

- [x] **5.1** Alertes prix (notifications navigateur) ✅
- [x] **5.2** Indicateurs techniques (RSI, MACD, MM 50/200) ✅
- [x] **5.3** Portefeuille simulé (positions fictives, P&L) ✅
- [x] **5.4** Score d'opportunité custom (combine 52S bas + RSI + sentiment) ✅

## 🎯 Priorité 6 — Confort

- [x] **6.1** Export CSV de la watchlist ✅
- [x] **6.2** Mode plein écran TV (gros texte, auto-refresh, sans boutons) ✅
- [x] **6.3** Historique des actions consultées récemment ✅

---

# 🚀 Phase 2 — Pro-grade (À FAIRE)

## 🎯 Priorité 7 — Mobile & Accessibilité ★★★★★

- [x] **7.1** PWA installable (icône écran d'accueil, manifest, service worker) ✅
- [x] **7.2** Layout responsive optimisé tactile (cards plus larges, sliders, etc.) ✅
- [ ] **7.3** Notifications push natives (au lieu du navigateur uniquement)
- [x] **7.4** Mode offline avec cache des dernières données ✅ *(via service worker — network-first sur /api/ avec fallback cache)*

## 🎯 Priorité 8 — Cloud & Backend ★★★★★

- [ ] **8.1** Déploiement Vercel ou Railway (backend FastAPI hébergé)
- [ ] **8.2** Variables d'env serveur (clés API protégées)
- [ ] **8.3** Sync multi-device (watchlists et alertes accessibles partout)
- [ ] **8.4** Compte utilisateur optionnel (Supabase ou Clerk)

## 🎯 Priorité 9 — Intelligence augmentée ★★★★

- [ ] **9.1** Backtest engine — teste "si j'avais acheté quand score > 75 sur N années"
- [ ] **9.2** Historique des scores — track l'évolution des scores dans le temps
- [ ] **9.3** IA Briefing quotidien via Claude/GPT — résumé personnalisé en 5 lignes
- [ ] **9.4** Sentiment news via vraie IA (au lieu d'analyse lexicale)
- [ ] **9.5** Anomaly detection — alerte si comportement inhabituel sur une action

## 🎯 Priorité 10 — Outils d'analyse avancée ★★★★

- [ ] **10.1** Comparateur côte à côte (2-3 actions en parallèle)
- [ ] **10.2** Stock screener avancé style Finviz (`P/E < 20 AND ROE > 15 AND…`)
- [ ] **10.3** Personnalisation des poids du score (growth / value / momentum)
- [ ] **10.4** Notes par action (texte libre stocké en localStorage)
- [ ] **10.5** Corrélation matrix entre actions sélectionnées

## 🎯 Priorité 11 — Data enrichment ★★★

- [ ] **11.1** Données de volume + OBV + MFI (Money Flow Index)
- [ ] **11.2** Multiple watchlists nommées (Long terme / Speculative / Income…)
- [ ] **11.3** Détection volume spike (signal souvent fort)
- [ ] **11.4** Sector rotation analysis (quel secteur monte vs descend)
- [ ] **11.5** ETF holdings breakdown (que contient un ETF)

## 🎯 Priorité 12 — Polish & social ★★★

- [ ] **12.1** Thèmes visuels (Bloomberg dark / Light / HUD militaire / Cyberpunk)
- [ ] **12.2** Tax helper FR (calcul gain/perte CTO vs PEA)
- [ ] **12.3** Notifications smart (RSI + volume spike, earnings dans 7j, etc.)
- [ ] **12.4** Stratégies modèles (FAANG, Dividend Aristocrats, All Weather, Lazy…)
- [ ] **12.5** Drag & drop pour réorganiser les sections
- [ ] **12.6** Export PDF mensuel (snapshot du portfolio)

## 🎯 Priorité 13 — Intégrations externes ★★

- [ ] **13.1** Bot Telegram pour notifications
- [ ] **13.2** Bot Discord pour notifications
- [ ] **13.3** Webhooks (envoyer vers Zapier, Make, etc.)
- [ ] **13.4** Email digest quotidien
- [ ] **13.5** API publique (autres devs peuvent se brancher)

---

# 💰 Phase 3 — Commercialisation SaaS (À FAIRE)

> ⚠️ **Prérequis bloquant** : ne démarrer la Phase 3 **qu'après** validation backtest (P9.1).
> Si le score d'opportunité v5 ne génère pas d'alpha statistiquement vérifié, le produit n'est pas vendable → revenir refondre l'algo avant toute commercialisation.

## 📦 Positionnement produit

**Pitch** : *« TradeRadar — l'outil d'investissement pour particuliers français qui veulent décider eux-mêmes. »*

**Cible** : investisseurs particuliers FR, 25-55 ans, CTO/PEA, en ont marre des interfaces basiques de Boursorama/Trade Republic, pas prêts à payer 5000€/mois Bloomberg, veulent un outil sérieux mais accessible.

## 💎 Tiering des fonctionnalités

| Feature | FREE | PREMIUM (~10€/mois) | PRO (~25€/mois) |
|---|---|---|---|
| Watchlist (Phase 1) | ✅ max 20 tickers | ✅ illimité | ✅ illimité |
| Indices, forex, crypto | ✅ | ✅ | ✅ |
| News + sentiment | ✅ | ✅ | ✅ |
| Score d'opportunité v5 | 🔒 top 5 seulement | ✅ illimité | ✅ illimité |
| Heatmap | ✅ | ✅ | ✅ |
| Mode TV plein écran | ✅ | ✅ | ✅ |
| Alertes prix/score | 🔒 max 3 | ✅ illimité | ✅ illimité |
| Portfolio simulé | ✅ 1 portfolio | ✅ illimité | ✅ illimité |
| Briefing IA quotidien (P9.3) | ❌ | ✅ | ✅ |
| Sentiment news IA (P9.4) | ❌ | ✅ | ✅ |
| Anomaly detection (P9.5) | ❌ | ✅ | ✅ |
| Historique scores (P9.2) | ❌ | ✅ 90j | ✅ illimité |
| Mode offline PWA | ✅ | ✅ | ✅ |
| Notifications push | ❌ | ✅ | ✅ |
| **Backtest engine (P9.1)** | ❌ | 🔒 démo seulement | ✅ illimité |
| **Screener avancé (P10.2)** | ❌ | ❌ | ✅ |
| **Comparateur côte à côte (P10.1)** | ❌ | ✅ 2 actions | ✅ 3 actions |
| **Multi-watchlists (P11.2)** | ❌ | ✅ max 3 | ✅ illimité |
| **Notes par action (P10.4)** | ❌ | ✅ | ✅ |
| **Personnalisation poids du score (P10.3)** | ❌ | ❌ | ✅ |
| **Matrice corrélation (P10.5)** | ❌ | ❌ | ✅ |
| **Détection volume spike (P11.3)** | ❌ | ✅ | ✅ |
| **Sector rotation (P11.4)** | ❌ | ❌ | ✅ |
| **ETF holdings (P11.5)** | ❌ | ❌ | ✅ |
| **Tax helper FR — module Fiscalité (P20)** | ❌ | ❌ | ✅ |
| Thèmes visuels (P12.1) | ❌ | ✅ | ✅ |
| Stratégies modèles (P12.4) | ❌ | ✅ | ✅ |
| Export PDF mensuel (P12.6) | ❌ | ✅ | ✅ |
| Telegram/Discord bot (P13.1-2) | ❌ | ✅ | ✅ |
| Email digest (P13.4) | ❌ | ✅ | ✅ |
| Webhooks (P13.3) | ❌ | ❌ | ✅ |
| API publique perso (P13.5) | ❌ | ❌ | ✅ |
| Support | Email best-effort | Email <48h | Email <24h + prioritaire |

**Logique des tiers** :
- **FREE** = aimant à acquisition (utilisable mais limité)
- **PREMIUM** = particulier qui prend ça au sérieux (alertes, IA briefing, multi-watchlist)
- **PRO** = investisseur actif qui veut TOUT (backtest, screener, fiscalité, sector rotation)

## 🎯 Priorité 14 — Auth & Multi-tenant ★★★★★

- [ ] **14.1** Authentification users (Supabase Auth ou Clerk) — email/password + OAuth Google
- [ ] **14.2** Base de données Postgres (migration depuis localStorage) — schémas users, watchlists, portfolios, alertes
- [ ] **14.3** Migration des données localStorage → cloud à la première connexion
- [ ] **14.4** Isolation multi-tenant (chaque user voit uniquement ses données, RLS Postgres)
- [ ] **14.5** Gestion profil (changer email, mot de passe, suppression compte RGPD)

## 🎯 Priorité 15 — Billing & Pricing ★★★★★

- [ ] **15.1** Intégration Stripe (Checkout + Customer Portal)
- [ ] **15.2** Définition des plans (Free / Premium ~10€/mois / Pro ~25€/mois)
- [ ] **15.3** Feature gating côté backend (decorators FastAPI selon plan)
- [ ] **15.4** Page pricing publique avec comparatif features
- [ ] **15.5** Période d'essai gratuite (14 jours) + relance abandon panier
- [ ] **15.6** Webhooks Stripe (renouvellement, échec paiement, annulation)
- [ ] **15.7** Factures auto + historique paiements dans le compte user

## 🎯 Priorité 16 — Légal & Compliance ★★★★★

- [ ] **16.1** Disclaimers AMF clairs ("outil d'aide à la décision, pas conseil en investissement") — visible en footer, à l'inscription, dans le briefing IA
- [ ] **16.2** CGU + CGV rédigées par juriste (~500-1000€ one-shot)
- [ ] **16.3** Politique de confidentialité RGPD (cookies, données traitées, durée, droits user)
- [ ] **16.4** Mentions légales (siret société, hébergeur, contact)
- [ ] **16.5** Bannière cookies conforme (Axeptio ou équivalent)
- [ ] **16.6** Statut juridique : auto-entrepreneur OK pour démarrer, SASU si > 80k€/an
- [ ] **16.7** Vérifier non-classification CIF (Conseiller en Investissement Financier) — si on franchit la ligne "recommandation personnalisée", agrément AMF obligatoire

## 🎯 Priorité 17 — Infra production sérieuse ★★★★

- [ ] **17.1** Hébergement scalable (Railway / Fly.io / Render — ~20-50€/mois au début)
- [ ] **17.2** Migration sources de données payantes (Polygon.io ou EOD Historical) — Yahoo/Finnhub free vont saturer dès 20 users
- [ ] **17.3** Rate limiting par user (FastAPI middleware + Redis) — éviter qu'un user n'épuise les quotas API
- [ ] **17.4** Monitoring & alertes (Sentry pour erreurs, BetterStack ou Uptime Kuma pour uptime)
- [ ] **17.5** Logs structurés (JSON, envoyés vers Axiom / Logtail)
- [ ] **17.6** Backups automatiques DB quotidiens (rétention 30j)
- [ ] **17.7** Status page publique (status.traderar.fr)
- [ ] **17.8** CI/CD (GitHub Actions : tests + deploy auto sur push main)
- [ ] **17.9** Tests automatiques (pytest backend + smoke tests E2E Playwright)
- [ ] **17.10** Circuit breakers + retry exponentiel sur appels API externes

## 🎯 Priorité 18 — Marketing & Acquisition ★★★★

- [ ] **18.1** Landing page de conversion (hero, démo vidéo, social proof, FAQ, CTA)
- [ ] **18.2** Page "Résultats backtest" publique (le gros argument de vente — score X% vs S&P Y%)
- [ ] **18.3** Blog SEO (10-20 articles ciblés "comment investir en PEA", "screener actions FR", etc.)
- [ ] **18.4** Email marketing (Resend ou Buttondown) — newsletter + onboarding séquence
- [ ] **18.5** Analytics produit (PostHog ou Plausible) — qui utilise quoi, où sont les frictions
- [ ] **18.6** Programme de parrainage (1 mois offert par filleul actif)
- [ ] **18.7** Présence canaux : compte X/Twitter, sub Reddit r/vosfinances, YouTube éventuellement

## 🎯 Priorité 19 — Support & Onboarding ★★★

- [ ] **19.1** Onboarding interactif au premier login (visite guidée des 4-5 sections clés)
- [ ] **19.2** Helpdesk (Crisp gratuit, ou simple mailto: contact@)
- [ ] **19.3** Base de connaissances / FAQ publique
- [ ] **19.4** Email transactionnels (bienvenue, reset password, alerte sécurité)
- [ ] **19.5** Page "Changelog" publique (les users adorent voir le produit bouger)

## 🎯 Priorité 20 — Module Fiscalité FR (Pro tier) ★★★★

> Différenciateur clé vs concurrents anglo-saxons. Le marché FR retail n'a quasi rien de propre sur le sujet.

- [ ] **20.1** Import relevés brokers FR (Trade Republic CSV, Boursorama, Degiro, Interactive Brokers)
- [ ] **20.2** Détection automatique du type de compte (CTO / PEA / PEA-PME / Assurance-Vie)
- [ ] **20.3** Calcul des plus/moins-values en méthode FIFO (CTO) + suivi seuil 5 ans (PEA)
- [ ] **20.4** Alerte "Vendre avant 5 ans en PEA = perte de l'exonération" sur chaque ligne PEA < 5 ans
- [ ] **20.5** Simulateur fiscal : "Si je vends X actions, je dois Y € de flat tax"
- [ ] **20.6** Optimiseur de cession : "Vends d'abord les positions en moins-value pour compenser tes plus-values"
- [ ] **20.7** Génération formulaire 2074 (déclaration plus-values mobilières) — export PDF prêt à transmettre
- [ ] **20.8** Suivi du plafond PEA (150k€) et PEA-PME (225k€ combiné)
- [ ] **20.9** Gestion des dividendes (PFU 30% vs barème) — recommandation auto selon TMI
- [ ] **20.10** Historique fiscal annuel (récap par année civile, exportable comptable)

---

## 📊 Progression globale

```
─── Phase 1 (Dashboard) ────────────────────
P1  : ▰▰▰    3/3 ✅
P2  : ▰▰▰▰   4/4 ✅
P3  : ▰▰▰▰   4/4 ✅
P4  : ▰▰▰▰   4/4 ✅
P5  : ▰▰▰▰   4/4 ✅
P6  : ▰▰▰    3/3 ✅
Sous-total : 22/22 ✅

─── Phase 2 (Pro-grade) ────────────────────
P7  : ▰▰▱▰   3/4   Mobile & Accessibilité
P8  : ▱▱▱▱   0/4   Cloud & Backend
P9  : ▱▱▱▱▱  0/5   Intelligence augmentée
P10 : ▱▱▱▱▱  0/5   Outils analyse avancée
P11 : ▱▱▱▱▱  0/5   Data enrichment
P12 : ▱▱▱▱▱▱ 0/6   Polish & social
P13 : ▱▱▱▱▱  0/5   Intégrations externes
Sous-total Phase 2 : 3/34

─── Phase 3 (SaaS) ─ après backtest P9.1 ───
P14 : ▱▱▱▱▱       0/5    Auth & Multi-tenant
P15 : ▱▱▱▱▱▱▱     0/7    Billing & Pricing
P16 : ▱▱▱▱▱▱▱     0/7    Légal & Compliance
P17 : ▱▱▱▱▱▱▱▱▱▱  0/10   Infra production
P18 : ▱▱▱▱▱▱▱     0/7    Marketing & Acquisition
P19 : ▱▱▱▱▱       0/5    Support & Onboarding
P20 : ▱▱▱▱▱▱▱▱▱▱  0/10   Module Fiscalité FR
Sous-total Phase 3 : 0/51

═══════════════════════════════════════════
TOTAL GÉNÉRAL : 25/107 (23 %)
```

---

## 🎯 Recommandation d'ordre

**Phase 2** :
1. ~~**P7 PWA Mobile**~~ ✅ (3/4 faits)
2. **P7.3** (push notifications) pour terminer la P7
3. **P8 Cloud** — fondation pour le SaaS
4. **P9.1 + P9.2 Backtest** — ⚠️ **MOMENT DE VÉRITÉ** : valide ou invalide le score d'opportunité v5
   - ✅ Score validé → continuer P9.3-9.5, puis P10-P13, puis attaquer Phase 3
   - ❌ Score invalide → refondre le scoring AVANT toute suite (sinon on bâtit sur du sable)
5. **P9.3-9.5** Reste de l'IA (briefing, sentiment IA, anomaly detection)
6. **P10 Outils analyse** — utilité pratique
7. **P11 Data enrichment** — incrémental
8. **P12 Polish** — finitions
9. **P13 Intégrations** — connectivité externe

**Phase 3 — Commercialisation** (uniquement si P9.1 valide le score) :
10. **P16 Légal** d'abord — sans CGU/disclaimers AMF, pas de premier paiement légal
11. **P14 Auth + Multi-tenant** — base technique du SaaS
12. **P15 Billing Stripe** — encaisser
13. **P17 Infra production** — robustesse en parallèle de P14/P15
14. **P19 Onboarding + Support** — pour que les premiers users restent
15. **P18 Marketing** — quand le produit tient debout, ouvrir les vannes

---

## 📝 Notes & décisions

> Au fil des étapes, on note ici ce qui mérite d'être retenu (clés API, choix d'archi, etc.)

- **Sources de données utilisées** : Yahoo Finance v8 chart (gratuit), Finnhub (clé), CoinGecko (gratuit), open.er-api.com (forex gratuit)
- **Décision** : Finnhub free = US uniquement pour fundamentals/sentiment/recos → EU stocks ont moins de signaux
- **Algo de score v5** : 35+ signaux, 5 dimensions (prix, fondamentaux, technique, sentiment, macro), consensus multi-indicateurs, plafond régime baissier
- **Cache stratégie** : 5min pour les prix, 1h pour sentiment/recos, 24h pour fondamentaux
- **Persistance locale** : localStorage pour watchlist, portfolio, alertes, vues, filtres → migration vers cloud à terme via P8
- **PWA (P7.1)** : manifest + icône SVG + service worker servi à `/sw.js` (scope racine). Cache-first pour le shell statique, network-first pour `/api/*` avec fallback cache si offline. Bump `CACHE_VERSION` dans `sw.js` pour invalider après gros changement.
- **Responsive (P7.2)** : breakpoints 1024 / 800 / 600 / 380px. Search input à 16px pour bloquer le zoom iOS. Tap targets ≥ 36-40px. Modal quasi-fullscreen sous 800px. `viewport-fit=cover` pour notches iPhone.
- **Décision stratégique** : faire **P9.1 backtest dès qu'on arrive à la P9**, pas après P10/P11/P12 — c'est le moment de vérité pour valider l'algo de score avant d'empiler des features dessus.
- **Score v6 (refonte majeure)** : architecture 4 piliers (trend/timing/quality/sentiment) + poids adaptatifs par régime + multiplicateur risque + confiance. Exploite désormais l'OHLCV complet de Yahoo (avant : closes seulement) → ATR, ADX/DI, OBV, MFI, CMF, volume events, divergence RSI, structure HH/HL, Sortino. v5 conservé (`compute_opportunity_score_v5`) comme baseline du futur backtest. Couvre de fait **11.1** (volume+OBV+MFI) et **11.3** (volume spike) côté algo — reste l'affichage UI dédié.
- **Bugs HTML corrigés** : 4 divs de grilles (`stocksGrid`, `newsGrid`, `emergingGrid`, `cryptoGrid`) avaient un `>` manquant.
- **Pass UI/UX (skill ui-ux-pro-max)** : contrastes relevés au seuil WCAG AA (`--text-muted` 1.80:1 → 4.88:1, `--text-dim` 3.79:1 → 5.89:1) ; focus rings clavier globaux via `:focus-visible` (ring #5ab0ff, 8.55:1) ; skip-link ; aria-labels sur boutons icônes + `role=dialog`/`aria-modal` sur le modal + `role=combobox`/`aria-expanded` synchro sur la recherche ; `tabular-nums` sur tous les chiffres (alignement type terminal). Emojis-icônes conservés (choix assumé, cf CLAUDE.md).
- **Pass beauté (skill ui-ux-pro-max, Dimensional Layering)** : échelle d'élévation 4 niveaux (`--elev-1..4`) + tokens glow + `--surface-sheen`. Police **JetBrains Mono** sur tous les chiffres (prix/%/scores) = feel terminal. Cartes avec dégradé subtil + hover lift (-2px) + glow vert sans reflow. **Score circle = anneau conique** piloté par `--sc` (le remplissage = la note). Header en verre fumé (backdrop-blur). Barres d'accent des sections avec glow. Modal en élévation max. SW bumpé `tr-v4`. Identité Bloomberg dark conservée (confirmée optimale par le skill : WCAG AAA + perf excellente).
