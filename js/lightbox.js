// Visionneuse plein écran des fiches chantier : photos et vidéos, flèches, clavier et glissement au doigt.
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('[data-lb]'));
  if (!links.length) return;

  var box = document.createElement('dialog');
  box.className = 'lb';
  box.setAttribute('aria-label', 'Photos du chantier');
  box.innerHTML =
    '<button class="lb-btn lb-close" type="button" aria-label="Fermer">×</button>' +
    '<button class="lb-btn lb-prev" type="button" aria-label="Photo précédente">‹</button>' +
    '<figure class="lb-stage"></figure>' +
    '<button class="lb-btn lb-next" type="button" aria-label="Photo suivante">›</button>' +
    '<p class="lb-count" aria-live="polite"></p>';
  document.body.appendChild(box);
  var stage = box.querySelector('.lb-stage'), count = box.querySelector('.lb-count'), i = 0;

  function show(n) {
    i = (n + links.length) % links.length;
    var a = links[i], cap = a.getAttribute('data-caption') || '';
    var yt = a.getAttribute('data-youtube');
    stage.innerHTML = yt
      ? '<iframe src="https://www.youtube-nocookie.com/embed/' + yt + '?autoplay=1&rel=0" title="' + cap + '" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>'
      : a.hasAttribute('data-video')
        ? '<video src="' + a.getAttribute('href') + '" controls autoplay playsinline></video>'
        : '<img src="' + a.getAttribute('href') + '" alt="' + (a.querySelector('img') ? a.querySelector('img').alt : cap) + '">';
    count.textContent = (i + 1) + ' / ' + links.length;
  }
  function open(n) { show(n); if (!box.open) box.showModal(); document.documentElement.classList.add('lb-on'); }
  function close() { stage.innerHTML = ''; box.close(); }

  links.forEach(function (a, n) { a.addEventListener('click', function (ev) { ev.preventDefault(); open(n); }); });
  Array.prototype.forEach.call(document.querySelectorAll('[data-lb-open]'), function (a) {
    a.addEventListener('click', function (ev) { ev.preventDefault(); open(+a.getAttribute('data-lb-open')); });
  });
  box.querySelector('.lb-close').addEventListener('click', close);
  box.querySelector('.lb-prev').addEventListener('click', function () { show(i - 1); });
  box.querySelector('.lb-next').addEventListener('click', function () { show(i + 1); });
  box.addEventListener('close', function () { stage.innerHTML = ''; document.documentElement.classList.remove('lb-on'); });
  box.addEventListener('click', function (ev) { if (ev.target === box || ev.target === stage) close(); });
  box.addEventListener('keydown', function (ev) {
    if (ev.key === 'ArrowLeft') show(i - 1);
    if (ev.key === 'ArrowRight') show(i + 1);
  });

  var x0 = null;
  box.addEventListener('touchstart', function (ev) { x0 = ev.touches[0].clientX; }, { passive: true });
  box.addEventListener('touchend', function (ev) {
    if (x0 === null) return;
    var dx = ev.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 50) show(dx < 0 ? i + 1 : i - 1);
  });
})();
