(() => {
  const state = { enabled: false, selected: '', recent: [], dim: 20, image: '', items: [], busy: '', initialized: false, loading: null, revision: 0 };
  const byId = id => document.getElementById(id);
  const api = () => window.pywebview?.api;

  function feedback(message = '') {
    ['wallpaperFeedback', 'wallpaperDialogFeedback'].forEach(id => {
      const element = byId(id);
      if (element) element.textContent = message;
    });
  }

  function applyBackground() {
    document.documentElement.classList.toggle('has-wallpaper', state.enabled && Boolean(state.image));
    document.documentElement.style.setProperty('--wallpaper-dim', String(state.dim / 100));
    document.querySelectorAll('.app-container, .desktop-widget-card').forEach(container => {
      let layer = container.querySelector(':scope > .app-wallpaper');
      if (!layer) {
        layer = document.createElement('div');
        layer.className = 'app-wallpaper';
        layer.setAttribute('aria-hidden', 'true');
        container.prepend(layer);
      }
      layer.style.backgroundImage = state.image ? `url("${state.image}")` : '';
    });
    byId('settingWallpaperEnabled').checked = state.enabled;
    localStorage.setItem('lightwidget_wallpaper_enabled', String(state.enabled));
    window.updatePanelTransparencyAvailability?.();
    byId('wallpaperControls').hidden = !state.enabled;
    byId('settingWallpaperDim').value = String(state.dim);
    byId('settingWallpaperDim').setAttribute('aria-valuetext', `${state.dim}% затемнения`);
    byId('wallpaperDimValue').textContent = `${state.dim}%`;
    if (!state.enabled && byId('wallpaperDialog').open) byId('wallpaperDialog').close();
  }

  function sortedItems() {
    const rank = new Map(state.recent.map((id, index) => [id, index]));
    return [...state.items].sort((a, b) => (rank.get(a.id) ?? Infinity) - (rank.get(b.id) ?? Infinity) || a.name.localeCompare(b.name));
  }

  function tile(item) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'wallpaper-tile';
    button.dataset.wallpaper = item.id;
    button.setAttribute('aria-pressed', String(item.id === state.selected));
    button.setAttribute('aria-label', `${item.name}${item.installed ? '' : ', скачать'}`);
    button.disabled = Boolean(state.busy);
    const image = document.createElement('img');
    image.src = item.preview;
    image.alt = '';
    image.loading = 'lazy';
    image.decoding = 'async';
    const caption = document.createElement('span');
    caption.className = 'wallpaper-tile-caption';
    const name = document.createElement('span');
    name.className = 'wallpaper-tile-name';
    name.textContent = item.name;
    const status = document.createElement('span');
    status.className = 'wallpaper-tile-status';
    status.textContent = item.id === state.busy ? 'Загрузка…' : item.id === state.selected ? 'Выбрано' : item.installed ? '' : 'Скачать';
    caption.append(name, status);
    button.append(image, caption);
    button.addEventListener('click', () => choose(item));
    return button;
  }

  function updateTiles() {
    document.querySelectorAll('[data-wallpaper]').forEach(button => {
      const item = state.items.find(item => item.id === button.dataset.wallpaper);
      if (!item) return;
      button.disabled = Boolean(state.busy);
      button.setAttribute('aria-pressed', String(item.id === state.selected));
      button.querySelector('.wallpaper-tile-status').textContent = item.id === state.busy ? 'Загрузка…' : item.id === state.selected ? 'Выбрано' : item.installed ? '' : 'Скачать';
    });
    const selected = state.items.find(item => item.id === state.selected);
    byId('wallpaperCurrent').textContent = selected?.name || 'Выберите обои';
  }

  function render() {
    const focused = document.activeElement?.dataset.wallpaper;
    const inDialog = byId('wallpaperDialog').contains(document.activeElement);
    const scrollTop = byId('wallpaperLibrary').scrollTop;
    const items = sortedItems();
    byId('wallpaperStrip').replaceChildren(...items.map(tile));
    const library = byId('wallpaperLibrary');
    library.replaceChildren();
    const recentIds = new Set(state.recent);
    for (const recent of [true, false]) {
      const group = items.filter(item => recentIds.has(item.id) === recent);
      if (!group.length) continue;
      const heading = document.createElement('h3');
      heading.textContent = `${recent ? 'Недавно использованные' : 'Другие обои'} · ${group.length}`;
      const grid = document.createElement('div');
      grid.className = 'wallpaper-grid';
      grid.append(...group.map(tile));
      library.append(heading, grid);
    }
    updateTiles();
    byId('wallpaperLibrary').scrollTop = scrollTop;
    if (focused) {
      const container = inDialog ? library : byId('wallpaperStrip');
      container.querySelector(`[data-wallpaper="${focused}"]`)?.focus({ preventScroll: true });
    }
  }

  async function loadCatalog() {
    if (state.items.length) return true;
    if (state.loading) return state.loading;
    state.loading = (async () => {
      try {
        feedback('Загрузка каталога…');
        const items = await api().get_wallpapers();
        if (!Array.isArray(items) || !items.length) throw new Error();
        state.items = items;
        render();
        feedback();
        return true;
      } catch {
        feedback('Не удалось открыть каталог. Выключите и включите обои, чтобы попробовать снова.');
        return false;
      } finally {
        state.loading = null;
      }
    })();
    return state.loading;
  }

  async function choose(item, restore = false) {
    if (state.busy || !api()) return;
    state.busy = item.id;
    const revision = state.revision;
    feedback('Загрузка обоев в полном качестве…');
    updateTiles();
    try {
      const result = await api().get_wallpaper_image(item.id);
      if (revision !== state.revision) return;
      if (!result?.success || !result.image?.startsWith('data:image/jpeg;base64,')) throw new Error(result?.error);
      const recent = [item.id, ...state.recent.filter(id => id !== item.id)].slice(0, 24);
      if (!restore || JSON.stringify(recent) !== JSON.stringify(state.recent)) {
        const saved = await api().save_config({ appearance: { wallpaper: item.id, wallpaper_recent: recent } });
        if (saved === false) throw new Error('Не удалось сохранить выбор обоев. Попробуйте ещё раз.');
      }
      if (revision !== state.revision) return;
      state.image = result.image;
      state.selected = item.id;
      state.recent = recent;
      item.installed = true;
      feedback();
      applyBackground();
    } catch (error) {
      feedback(error.message || 'Не удалось загрузить обои. Попробуйте ещё раз.');
    } finally {
      state.busy = '';
      render();
    }
  }

  window.initWallpaperSettings = async appearance => {
    if (state.initialized) return;
    state.initialized = true;
    state.enabled = appearance.wallpaper_enabled === true;
    state.selected = appearance.wallpaper || '';
    state.recent = Array.isArray(appearance.wallpaper_recent) ? [...new Set(appearance.wallpaper_recent.filter(id => typeof id === 'string'))].slice(0, 24) : [];
    state.dim = Number.isFinite(Number(appearance.wallpaper_dim)) ? Math.min(50, Math.max(0, Number(appearance.wallpaper_dim))) : 20;
    applyBackground();
    if (state.enabled && await loadCatalog()) {
      const selected = state.items.find(item => item.id === state.selected) || state.items.find(item => item.installed);
      if (selected && state.enabled) await choose(selected, selected.id === state.selected);
    }
  };

  window.resetWallpaperSettings = () => {
    state.revision++;
    state.enabled = false;
    state.dim = 20;
    state.selected = '';
    state.recent = [];
    state.image = '';
    applyBackground();
    feedback();
    updateTiles();
  };

  byId('settingWallpaperEnabled').addEventListener('change', async event => {
    state.enabled = event.target.checked;
    applyBackground();
    await api()?.save_config({ appearance: { wallpaper_enabled: state.enabled, panel_transparency: window.appSettings?.panelTransparency ?? 0 } });
    if (state.enabled && await loadCatalog() && !state.image && state.enabled) {
      const selected = state.items.find(item => item.id === state.selected) || state.items.find(item => item.installed);
      if (selected) await choose(selected, selected.id === state.selected);
    }
  });
  byId('settingWallpaperDim').addEventListener('input', event => {
    state.dim = Math.min(50, Math.max(0, Number(event.target.value) || 0));
    applyBackground();
  });
  byId('settingWallpaperDim').addEventListener('change', () => api()?.save_config({ appearance: { wallpaper_dim: state.dim } }));
  byId('wallpaperShowAll').addEventListener('click', () => {
    if (state.enabled) byId('wallpaperDialog').showModal();
  });
  byId('wallpaperCloseDialog').addEventListener('click', () => byId('wallpaperDialog').close());
  byId('wallpaperDialog').addEventListener('click', event => {
    const dialog = event.currentTarget;
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
  [['wallpaperPrevious', -1], ['wallpaperNext', 1]].forEach(([id, direction]) => {
    byId(id).addEventListener('click', () => {
      const strip = byId('wallpaperStrip');
      strip.scrollBy({ left: strip.clientWidth * direction, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    });
  });
})();
