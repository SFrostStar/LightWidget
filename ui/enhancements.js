const timerViews = new Map();
const timerMotionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
let timerMotionEnabled = localStorage.getItem('lightwidget_smooth_timers') !== 'false';

function clearDigitMotion(digit) {
  digit.getAnimations().forEach(animation => animation.cancel());
  digit.querySelectorAll('.rolling-old').forEach(old => old.remove());
  const current = digit.querySelector('.rolling-current');
  if (current) current.getAnimations().forEach(animation => animation.cancel());
  clearTimeout(digit.motionCleanup);
}

function setTimerMotionEnabled(enabled) {
  timerMotionEnabled = enabled !== false;
  timerViews.forEach((view, element) => {
    if (!element.isConnected) { timerViews.delete(element); return; }
    element.querySelectorAll('.rolling-digit').forEach(clearDigitMotion);
    if (!timerMotionEnabled || timerMotionPreference.matches) {
      if (view.digits.every(digit => element.contains(digit))) element.innerHTML = view.markup;
      timerViews.delete(element);
    }
  });
}

timerMotionPreference.addEventListener('change', () => setTimerMotionEnabled(timerMotionEnabled));

function setTimerText(element, text) {
  const safeText = document.createElement('span');
  safeText.textContent = text;
  setTimerMarkup(element, safeText.innerHTML);
}

function setTimerMarkup(element, markup) {
  if (!element) return;
  const previous = timerViews.get(element);
  if (previous && previous.markup === markup && (previous.digits.length ? previous.digits.every(digit => element.contains(digit)) : element.innerHTML === markup)) return;
  const template = document.createElement('template');
  template.innerHTML = markup;
  element.dataset.timerValue = template.content.textContent;
  if (!timerMotionEnabled || timerMotionPreference.matches) {
    element.innerHTML = markup;
    timerViews.delete(element);
    return;
  }
  const shape = markup.replace(/\d/g, '#');
  const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);
  const values = [];
  textNodes.forEach(node => {
    if (!/\d/.test(node.textContent)) return;
    const fragment = document.createDocumentFragment();
    node.textContent.split('').forEach(character => {
      if (!/\d/.test(character)) { fragment.append(document.createTextNode(character)); return; }
      values.push(character);
      const digit = document.createElement('span');
      digit.className = 'rolling-digit';
      const current = document.createElement('span');
      current.className = 'rolling-current';
      current.textContent = character;
      digit.append(current);
      fragment.append(digit);
    });
    node.replaceWith(fragment);
  });
  const digits = element.querySelectorAll('.rolling-digit');
  const animate = document.visibilityState !== 'hidden' && element.getClientRects().length > 0;
  if (!previous || previous.shape !== shape || digits.length !== values.length) {
    element.replaceChildren(template.content);
    if (previous && animate) element.querySelectorAll('.rolling-current').forEach(current => {
      if (current.animate) current.animate([
        { transform: 'translateY(-90%)', opacity: 0, filter: 'blur(3px)' },
        { transform: 'translateY(0)', opacity: 1, filter: 'blur(0px)' }
      ], { duration: 380, easing: 'cubic-bezier(.16, 1, .3, 1)' });
    });
  } else {
    digits.forEach((digit, index) => {
      if (previous.values[index] === values[index]) return;
      clearDigitMotion(digit);
      const current = digit.querySelector('.rolling-current');
      const oldValue = current.textContent;
      current.textContent = values[index];
      if (!animate || !current.animate) return;
      const old = document.createElement('span');
      old.className = 'rolling-old';
      old.setAttribute('aria-hidden', 'true');
      old.textContent = oldValue;
      digit.append(old);
      old.animate([
        { transform: 'translateY(0)', opacity: 1, filter: 'blur(0px)' },
        { transform: 'translateY(90%)', opacity: 0, filter: 'blur(3px)' }
      ], { duration: 230, easing: 'cubic-bezier(.4, 0, 1, 1)', fill: 'forwards' });
      current.animate([
        { transform: 'translateY(-90%)', opacity: 0, filter: 'blur(3px)' },
        { transform: 'translateY(0)', opacity: 1, filter: 'blur(0px)' }
      ], { duration: 380, easing: 'cubic-bezier(.16, 1, .3, 1)' });
      digit.motionCleanup = setTimeout(() => old.remove(), 400);
    });
  }
  timerViews.set(element, { markup, shape, values, digits: Array.from(element.querySelectorAll('.rolling-digit')) });
  timerViews.forEach((view, target) => { if (!target.isConnected) timerViews.delete(target); });
}

let selectedHeatmapDay = null;
let heatmapDayData = {};
let heatmapDialogTrigger = null;

function formatDayDuration(seconds) {
  const minutes = Math.floor(Math.max(0, seconds) / 60);
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours} ч${minutes % 60 ? ` ${minutes % 60} мин` : ''}` : `${minutes} мин`;
}

function getDayOutageSummary(dayStart, dayEnd, stats) {
  const now = Date.now();
  const records = new Map();
  const history = Array.isArray(cachedHistory) ? cachedHistory : [];
  history.filter(item => item.status === 'OFF').forEach(item => {
    const start = item.start_timestamp ? item.start_timestamp * 1000 : new Date(item.timestamp || item.updated_at).getTime();
    if (Number.isFinite(start) && !records.has(start)) records.set(start, item);
  });
  if (currentState?.status === 'OFF' && currentState.start_timestamp) records.set(currentState.start_timestamp * 1000, currentState);
  const restorations = history.filter(item => item.status === 'ON').map(item => new Date(item.timestamp || item.updated_at).getTime()).filter(Number.isFinite).sort((a, b) => a - b);
  const intervals = [];
  let approximate = false;
  records.forEach((item, start) => {
    const restoredAt = restorations.find(moment => moment > start);
    const ongoing = currentState?.status === 'OFF' && currentState.start_timestamp * 1000 === start && (!currentState.end_timestamp || currentState.end_timestamp * 1000 > now);
    const estimatedEnd = item.end_timestamp ? item.end_timestamp * 1000 : start + (Number(item.total_seconds) || 3600) * 1000;
    const end = ongoing ? now : (restoredAt || Math.min(now, estimatedEnd));
    if (start >= dayEnd || end <= dayStart) return;
    intervals.push([Math.max(dayStart, start), Math.min(dayEnd, end, now)]);
    if (!restoredAt && !ongoing) approximate = true;
  });
  intervals.sort((a, b) => a[0] - b[0]);
  let offMilliseconds = 0;
  let coveredUntil = dayStart;
  intervals.forEach(([start, end]) => {
    offMilliseconds += Math.max(0, end - Math.max(start, coveredUntil));
    coveredUntil = Math.max(coveredUntil, end);
  });
  const retainedCount = Number(stats?.count) || 0;
  const useAggregate = retainedCount > intervals.length || (!intervals.length && Number(stats?.offSec) > 0);
  return {
    recorded: !!stats?.recorded || intervals.length > 0,
    count: Math.max(retainedCount, intervals.length),
    offSeconds: useAggregate ? Number(stats.offSec) || 0 : Math.floor(offMilliseconds / 1000),
    approximate: approximate || useAggregate
  };
}

function renderHeatmapDayDetails(dateKey) {
  const date = new Date(`${dateKey}T00:00:00`);
  const nextDay = new Date(date);
  nextDay.setDate(nextDay.getDate() + 1);
  const now = Date.now();
  const isToday = date.toDateString() === new Date(now).toDateString();
  const stats = heatmapDayData[dateKey];
  const summary = getDayOutageSummary(date.getTime(), nextDay.getTime(), stats);
  const recorded = summary.recorded;
  const observedSeconds = Math.max(0, Math.floor((Math.min(now, nextDay.getTime()) - date.getTime()) / 1000));
  const offSeconds = recorded ? Math.min(observedSeconds, Math.max(0, summary.offSeconds)) : 0;
  document.getElementById('heatmapDayTitle').textContent = date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
  document.getElementById('heatmapDaySubtitle').textContent = recorded
    ? (isToday ? 'Сегодня · данные на текущий момент' : (stats?.inferred ? 'По сохранённой истории между событиями' : (summary.approximate ? 'Приблизительно · по сохранённой статистике' : 'По сохранённым событиям')))
    : 'За этот день нет сохранённых данных';
  document.getElementById('heatmapDayOn').textContent = recorded ? formatDayDuration(observedSeconds - offSeconds) : '—';
  document.getElementById('heatmapDayOff').textContent = recorded ? formatDayDuration(offSeconds) : '—';
  document.getElementById('heatmapDayCount').textContent = recorded ? String(summary.count) : '—';
  const list = document.getElementById('heatmapDayEvents');
  list.replaceChildren();
  const detailHistory = currentState?.status === 'OFF' ? cachedHistory.concat(currentState) : cachedHistory;
  const events = detailHistory.filter(item => {
    const timestamp = new Date(item.timestamp || item.updated_at).getTime();
    const start = item.status === 'OFF' && item.start_timestamp ? item.start_timestamp * 1000 : timestamp;
    const ongoing = item.status === 'OFF' && currentState?.status === 'OFF' && item.start_timestamp === currentState.start_timestamp;
    const end = item.status === 'OFF' ? (ongoing ? now : (item.end_timestamp ? item.end_timestamp * 1000 : start + (Number(item.total_seconds) || 0) * 1000)) : start;
    return item.status === 'OFF' && item.start_timestamp
      ? start < nextDay.getTime() && end > date.getTime()
      : timestamp >= date.getTime() && timestamp < nextDay.getTime();
  }).sort((a, b) => (a.status === 'OFF' && a.start_timestamp ? a.start_timestamp * 1000 : new Date(a.timestamp || a.updated_at).getTime()) - (b.status === 'OFF' && b.start_timestamp ? b.start_timestamp * 1000 : new Date(b.timestamp || b.updated_at).getTime()));
  const seen = new Set();
  events.forEach(item => {
    const key = `${item.status}:${item.start_timestamp || item.timestamp || item.updated_at}`;
    if (seen.has(key)) return;
    seen.add(key);
    const row = document.createElement('div');
    row.className = 'day-event';
    const time = document.createElement('span');
    time.className = 'day-event-time';
    const moment = item.status === 'OFF' && item.start_timestamp ? new Date(item.start_timestamp * 1000) : new Date(item.timestamp || item.updated_at);
    time.textContent = moment < date ? 'Ранее' : moment.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    const content = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = item.status === 'OFF' ? 'Свет отключён' : (item.status === 'PLANNED' || item.is_planned ? 'Плановые работы' : 'Свет включён');
    title.className = item.status === 'OFF' ? 'day-event-off' : 'day-event-on';
    const description = document.createElement('span');
    description.textContent = item.reason || (item.status === 'OFF' ? 'Причина не указана' : 'Электроснабжение восстановлено');
    content.append(title, description);
    row.append(time, content);
    list.append(row);
  });
  if (!list.children.length) {
    const empty = document.createElement('p');
    empty.className = 'day-events-empty';
    empty.textContent = !recorded ? 'Начните мониторинг, чтобы здесь появились события.'
      : (offSeconds > 0 ? 'Сводная статистика есть, подробные записи этого дня не сохранены.' : 'В сохранённой истории этого дня отключений нет.');
    list.append(empty);
  }
}

function openHeatmapDay(dateKey, trigger) {
  selectedHeatmapDay = dateKey;
  heatmapDialogTrigger = trigger;
  renderHeatmapDayDetails(dateKey);
  const dialog = document.getElementById('heatmapDayDialog');
  if (!dialog.open) dialog.showModal();
  document.querySelectorAll('#heatmapGrid .gh-cell').forEach(cell => { cell.classList.toggle('is-selected', cell.dataset.date === dateKey); if (cell.tagName === 'BUTTON') cell.tabIndex = cell.dataset.date === dateKey ? 0 : -1; });
}

function setupWindowCorners() {
  let drag = null;
  let pending = null;
  let busy = false;
  let frame = null;
  const sendResize = async () => {
    frame = null;
    if (busy || !pending) return;
    const request = pending;
    pending = null;
    busy = true;
    try {
      const result = await window.pywebview.api.resize_window(request.width, request.height, request.corner);
      if (!result?.success) {
        pending = null;
        showToast('Не удалось изменить размер окна');
      }
    } catch (error) {
      pending = null;
      showToast('Не удалось изменить размер окна');
    } finally {
      busy = false;
      if (pending && frame === null) frame = requestAnimationFrame(sendResize);
    }
  };
  const updateSize = event => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    const dx = (event.screenX - drag.x) * (drag.corner.includes('w') ? -1 : 1);
    const dy = (event.screenY - drag.y) * (drag.corner.includes('n') ? -1 : 1);
    const scale = Math.max(880 / drag.width, 560 / drag.height, Math.min(7680 / drag.width, 4320 / drag.height, 1 + (dx * drag.width + dy * drag.height) / (drag.width ** 2 + drag.height ** 2)));
    pending = { width: Math.round(drag.width * scale), height: Math.round(drag.height * scale), corner: drag.corner };
    if (!busy && frame === null) frame = requestAnimationFrame(sendResize);
  };
  ['nw', 'ne', 'sw', 'se'].forEach(corner => {
    const handle = document.createElement('div');
    handle.className = 'window-resize-corner';
    handle.dataset.corner = corner;
    handle.setAttribute('aria-hidden', 'true');
    document.body.append(handle);
    handle.addEventListener('pointerdown', event => {
      if (event.button !== 0 || drag || document.body.classList.contains('widget-mode') || !window.pywebview?.api?.resize_window) return;
      event.preventDefault();
      event.stopPropagation();
      drag = { corner, pointerId: event.pointerId, x: event.screenX, y: event.screenY, width: window.innerWidth, height: window.innerHeight };
      handle.setPointerCapture(event.pointerId);
    });
    handle.addEventListener('pointermove', updateSize);
    handle.addEventListener('pointerup', event => {
      if (!drag || event.pointerId !== drag.pointerId) return;
      updateSize(event);
      drag = null;
      if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
    });
    handle.addEventListener('pointercancel', () => { drag = null; });
    handle.addEventListener('lostpointercapture', () => { drag = null; });
  });
}

function setupInterfaceEnhancements() {
  setupWindowCorners();
  const dialog = document.getElementById('heatmapDayDialog');
  document.getElementById('btnCloseHeatmapDay').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
  dialog.addEventListener('close', () => {
    document.querySelectorAll('#heatmapGrid .is-selected').forEach(cell => cell.classList.remove('is-selected'));
    const trigger = heatmapDialogTrigger?.isConnected ? heatmapDialogTrigger : document.querySelector(`#heatmapGrid [data-date="${selectedHeatmapDay}"]`);
    trigger?.focus({ preventScroll: true });
    selectedHeatmapDay = null;
  });
  const grid = document.getElementById('heatmapGrid');
  grid.addEventListener('keydown', event => {
    const cell = event.target.closest('button[data-date]');
    if (!cell) return;
    const steps = { ArrowDown: 1, ArrowUp: -1, ArrowRight: 7, ArrowLeft: -7 };
    if (!(event.key in steps)) return;
    event.preventDefault();
    const cells = Array.from(grid.querySelectorAll('button[data-date]'));
    const next = cells[cells.indexOf(cell) + steps[event.key]];
    if (next) { cell.tabIndex = -1; next.tabIndex = 0; next.focus(); }
  });
  const links = Array.from(document.querySelectorAll('.settings-section-link'));
  const sections = links.map(link => document.getElementById(link.dataset.section));
  const scroller = document.querySelector('.main-content');
  links.forEach(link => link.addEventListener('click', () => {
    const section = document.getElementById(link.dataset.section);
    scroller.scrollTo({ top: scroller.scrollTop + section.getBoundingClientRect().top - scroller.getBoundingClientRect().top - parseFloat(getComputedStyle(scroller).paddingTop) - 16, behavior: timerMotionPreference.matches ? 'auto' : 'smooth' });
    links.forEach(item => { item.classList.toggle('active', item === link); if (item === link) item.setAttribute('aria-current', 'location'); else item.removeAttribute('aria-current'); });
  }));
  let scrollFrame = null;
  scroller.addEventListener('scroll', () => {
    if (scrollFrame) return;
    scrollFrame = requestAnimationFrame(() => {
      scrollFrame = null;
      if (!document.getElementById('tab-settings').classList.contains('active')) return;
      const boundary = scroller.getBoundingClientRect().top + parseFloat(getComputedStyle(scroller).paddingTop) + 40;
      let index = 0;
      sections.forEach((section, position) => { if (section.getBoundingClientRect().top <= boundary) index = position; });
      if (scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 2) index = sections.length - 1;
      links.forEach((link, position) => { link.classList.toggle('active', position === index); if (position === index) link.setAttribute('aria-current', 'location'); else link.removeAttribute('aria-current'); });
    });
  }, { passive: true });
}
