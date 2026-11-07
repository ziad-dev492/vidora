(() => {
  const root = document.documentElement;
  try {
    const storedTheme = localStorage.getItem('vidora-theme');
    if (storedTheme === 'light' || storedTheme === 'dark') root.dataset.theme = storedTheme;
  } catch {}

  document.querySelector('.theme-toggle')?.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('vidora-theme', root.dataset.theme); } catch {}
  });

  const menuButton = document.querySelector('.menu-trigger');
  const sidebar = document.querySelector('.sidebar');
  const setMenuOpen = open => {
    sidebar?.classList.toggle('open', open);
    menuButton?.setAttribute('aria-expanded', String(open));
  };
  menuButton?.addEventListener('click', () => setMenuOpen(!sidebar?.classList.contains('open')));
  sidebar?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenuOpen(false)));
  document.addEventListener('click', event => {
    if (sidebar?.classList.contains('open') && !sidebar.contains(event.target) && !menuButton?.contains(event.target)) setMenuOpen(false);
  });

  document.querySelectorAll('[data-copy-url]').forEach(button => button.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(button.dataset.copyUrl); button.innerHTML = '<i class="bi bi-check2"></i> تم النسخ'; }
    catch { window.prompt('انسخ رابط الفيديو:', button.dataset.copyUrl); }
  }));

  document.querySelectorAll('.video-player[data-hls]').forEach(video => {
    const src = video.dataset.hls;
    if (src && window.Hls?.isSupported()) {
      const hls = new window.Hls();
      video._vidoraHls = hls;
      hls.loadSource(src);
      hls.attachMedia(video);
    } else if (src && video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = src;
    }
  });

  document.getElementById('quality-select')?.addEventListener('change', event => {
    const video = document.querySelector('.video-player');
    if (!video) return;
    const quality = event.target.value;
    const hls = video._vidoraHls;
    if (hls?.levels?.length) {
      if (!quality) hls.currentLevel = -1;
      else {
        const index = hls.levels.findIndex(level => Number(level.height) === Number(quality));
        if (index >= 0) hls.currentLevel = index;
      }
      return;
    }
    const current = video.currentTime;
    const source = video.querySelector('source');
    const base = video.dataset.streamBase;
    if (!source || !base) return;
    source.src = quality ? `${base}?quality=${encodeURIComponent(quality)}` : base;
    video.load();
    video.addEventListener('loadedmetadata', () => { video.currentTime = current; }, { once: true });
  });

  const uploadForm = document.getElementById('upload-form');
  uploadForm?.addEventListener('submit', event => {
    const file = uploadForm.querySelector('input[type=file][name=video_file]')?.files?.[0];
    if (!file || !window.XMLHttpRequest) return;
    event.preventDefault();
    const button = uploadForm.querySelector('button[type=submit]');
    const progressWrap = uploadForm.querySelector('.upload-progress');
    const bar = progressWrap?.querySelector('.progress-bar');
    if (button) button.disabled = true;
    if (progressWrap) progressWrap.hidden = false;
    const xhr = new XMLHttpRequest();
    xhr.open('POST', uploadForm.action || window.location.href);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.upload.onprogress = e => {
      if (e.lengthComputable && bar) {
        const pct = Math.round(e.loaded / e.total * 100);
        bar.style.width = `${pct}%`;
        bar.setAttribute('aria-valuenow', pct);
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 400) window.location.assign(xhr.responseURL || window.location.href);
      else {
        if (button) button.disabled = false;
        if (progressWrap) progressWrap.hidden = true;
        alert('تعذر إكمال الرفع. لم نعد إرسال الملف تلقائيًا لتجنب تكراره؛ تحقق من الاتصال وحاول مجددًا.');
      }
    };
    xhr.onerror = () => {
      if (button) button.disabled = false;
      if (progressWrap) progressWrap.hidden = true;
      alert('تعذر إكمال الرفع. تحقق من الاتصال وحاول مجددًا.');
    };
    xhr.send(new FormData(uploadForm));
  });

  const shorts = [...document.querySelectorAll('.short-card video')];
  if ('IntersectionObserver' in window && shorts.length) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) entry.target.play().catch(() => {});
      else entry.target.pause();
    }), { threshold: .65 });
    shorts.forEach(video => observer.observe(video));
  }
})();
