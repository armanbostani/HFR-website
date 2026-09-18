(function () {
  if (document.getElementById('hfr-rail')) return;

  const sections = {
    divisions: { label: 'Divisions', cards: [
      { title: 'LAND', href: '/divisions/land/' },
      { title: 'SEA',  href: '/divisions/sea/' },
      { title: 'AIR',  href: '/divisions/air/' },
      { title: 'OPERATIONS', href: '/divisions/operations/' }
    ]},
    partners: { label: 'Partners', cards: [
      { title: '2026 PARTNERS', href: '/sponsors/' },
      { title: 'SUPPORT US',    href: '/support-us/' }
    ]},
    discover: { label: 'Discover', cards: [
      { title: 'OUR MISSION', href: '/about/#mission' },
      { title: 'EVENTS',      href: '/events/' },
      { title: 'HISTORY',     href: '/history/' }
    ]},
    join: { label: 'Join Us', cards: [
      { title: 'JOINING THE TEAM', href: '/register/#why' },
      { title: 'CREATE ACCOUNT',   href: '/accounts/signup/' },
      { title: 'LOG IN',           href: '/accounts/login/' },
      { title: 'MY APPLICATION',   href: '/apply/' }
    ]}
  };
  const rail = document.createElement('aside');
  rail.id = 'hfr-rail';
  rail.className = 'hfr-rail';
  rail.setAttribute('aria-hidden', 'true');
  rail.innerHTML = `
    <nav class="hfr-rail-nav">
      ${Object.entries(sections).map(([key, s]) =>
        `<a href="#" data-key="${key}">${s.label}</a>`).join('')}
    </nav>
  `;

  const panel = document.createElement('div');
  panel.id = 'hfr-panel';
  panel.className = 'hfr-panel';
  panel.setAttribute('aria-hidden', 'true');
  panel.innerHTML = `
    <div class="hfr-cards" id="hfr-cards"></div>
    <div class="hfr-wash" aria-hidden="true"><span class="hfr-wash-text"></span></div>
  `;

  document.body.appendChild(panel);
  document.body.appendChild(rail);
  document.body.classList.add('hfr-has-rail');

  const navLinks = rail.querySelectorAll('.hfr-rail-nav a');
  const toggle   = document.getElementById('hfr-sidebar-toggle');
  const cardsBox = panel.querySelector('#hfr-cards');
  const wash     = panel.querySelector('.hfr-wash');
  const washText = panel.querySelector('.hfr-wash-text');
  let washTimer  = null;

  function setRailOpen(isOpen) {
    rail.classList.toggle('open', isOpen);
    rail.setAttribute('aria-hidden', String(!isOpen));
    document.body.classList.toggle('hfr-sidebar-open', isOpen);
    toggle.setAttribute('aria-expanded', String(isOpen));
  }

  function renderCards(key) {
    cardsBox.innerHTML = sections[key].cards.map(c =>
      `<a class="hfr-card" href="${c.href}">
         <span class="hfr-card-title">${c.title}</span>
       </a>`).join('');
  }

  function openPanel() {
    panel.classList.add('open');
    panel.setAttribute('aria-hidden', 'false');
    document.body.classList.add('hfr-panel-open');
  }

  function closePanel() {
    panel.classList.remove('open');
    panel.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('hfr-panel-open');
    navLinks.forEach(a => a.classList.remove('active'));
  }

  function selectSection(key) {
    panel.dataset.section = key;
    navLinks.forEach(a => a.classList.toggle('active', a.dataset.key === key));
    openPanel();
    washText.textContent = sections[key].label;
    wash.classList.add('show');
    clearTimeout(washTimer);
    washTimer = setTimeout(() => {
      renderCards(key);
      wash.classList.remove('show');
    }, 420);
  }

  navLinks.forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    selectSection(a.dataset.key);
  }));

  // Always navigate card links, including links back to the current page.
  // A brief delay lets the close animation complete before the new page loads.
  panel.addEventListener('click', e => {
    const card = e.target.closest('.hfr-card');
    if (!card) return;

    e.preventDefault();
    closePanel();
    setRailOpen(false);
    window.setTimeout(() => window.location.assign(card.href), 220);
  });

  toggle.addEventListener('click', () => {
    const shouldOpen = !rail.classList.contains('open');
    if (!shouldOpen) closePanel();
    setRailOpen(shouldOpen);
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closePanel();
      setRailOpen(false);
    }
  });
})();
(function () {
  const rail   = document.getElementById('hfr-account-rail');
  const toggle = document.getElementById('hfr-account-toggle');
  const panel  = document.getElementById('hfr-account-panel');
  if (!rail || !toggle || !panel) return;

  const sections = {
    profile: { label: 'Profile', cards: [
      { title: 'DASHBOARD',    href: '/members/dashboard/' },
      { title: 'EDIT PROFILE', href: '/members/profile/' }
    ]},
    // Only offered when the site is configured with a forum address
    forum: { label: 'Forum', cards: [
      { title: 'OPEN THE FORUM', href: '/forum/' }
    ]},
    store: { label: 'Store', cards: [
      { title: 'STORE', href: '/shop/' }
    ]}
  };

  const navLinks = rail.querySelectorAll('.hfr-rail-nav a');
  const cardsBox = panel.querySelector('#hfr-account-cards');
  const wash     = panel.querySelector('.hfr-wash');
  const washText = panel.querySelector('.hfr-wash-text');
  let washTimer  = null;

  function setRailOpen(isOpen) {
    rail.classList.toggle('open', isOpen);
    rail.setAttribute('aria-hidden', String(!isOpen));
    document.body.classList.toggle('hfr-account-open', isOpen);
    toggle.setAttribute('aria-expanded', String(isOpen));
  }

  function renderCards(key) {
    cardsBox.innerHTML = sections[key].cards.map(c =>
      `<a class="hfr-card" href="${c.href}">
         <span class="hfr-card-title">${c.title}</span>
       </a>`).join('');
  }

  function openPanel() {
    panel.classList.add('open');
    panel.setAttribute('aria-hidden', 'false');
    document.body.classList.add('hfr-panel-open');
  }

  function closePanel() {
    panel.classList.remove('open');
    panel.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('hfr-panel-open');
    navLinks.forEach(a => a.classList.remove('active'));
  }

  function selectSection(key) {
    panel.dataset.section = key;
    navLinks.forEach(a => a.classList.toggle('active', a.dataset.key === key));
    openPanel();
    washText.textContent = sections[key].label;
    wash.classList.add('show');
    clearTimeout(washTimer);
    washTimer = setTimeout(() => {
      renderCards(key);
      wash.classList.remove('show');
    }, 420);
  }

  navLinks.forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    selectSection(a.dataset.key);
  }));

  panel.addEventListener('click', e => {
    // account panel: card click closes then navigates
    const card = e.target.closest('.hfr-card');
    if (!card) return;
    e.preventDefault();
    closePanel();
    setRailOpen(false);
    window.setTimeout(() => window.location.assign(card.href), 220);
  });

  toggle.addEventListener('click', () => {
    const shouldOpen = !rail.classList.contains('open');
    if (!shouldOpen) closePanel();
    setRailOpen(shouldOpen);
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closePanel();
      setRailOpen(false);
    }
  });
})();
