
let currentState = null;
let countdownInterval = null;
let isAccountEditing = false;
let lightOnSince = localStorage.getItem('lightwidget_light_on_since') ? parseInt(localStorage.getItem('lightwidget_light_on_since'), 10) : null;

const elBrandStatusDot = document.getElementById('brandStatusDot');
const elLivePill = document.getElementById('livePill');
const elLivePillText = document.getElementById('livePillText');
const elHeroCard = document.getElementById('heroCard');
const elStatusBadge = document.getElementById('statusBadge');
const elStatusIcon = document.getElementById('statusIcon');
const elStatusLabel = document.getElementById('statusLabel');
const elSystemClock = document.getElementById('systemClock');

const elTimerSection = document.getElementById('timerSection');
const elTimerDigits = document.getElementById('timerDigits');
const elTimerLabel = document.getElementById('timerLabel');
const elCdHours = document.getElementById('cdHours');
const elCdMinutes = document.getElementById('cdMinutes');
const elCdSeconds = document.getElementById('cdSeconds');
const elProgressPercentText = document.getElementById('progressPercentText');
const elProgressBarFill = document.getElementById('progressBarFill');

const elDetailAddress = document.getElementById('detailAddress');
const elDetailReason = document.getElementById('detailReason');
const elDetailStart = document.getElementById('detailStart');
const elDetailEnd = document.getElementById('detailEnd');
const elRowReason = document.getElementById('rowReason');
const elRowStart = document.getElementById('rowStart');
const elRowEnd = document.getElementById('rowEnd');
const elInputAccountNumber = document.getElementById('inputAccountNumber');
const elBtnEditAccount = document.getElementById('btnEditAccount');
const elAccountEditText = document.getElementById('accountEditText');
const elBtnToggleAccount = document.getElementById('btnToggleAccount');
const elAccountToggleText = document.getElementById('accountToggleText');
const elLastUpdatedText = document.getElementById('lastUpdatedText');
const elPlannedOutageSection = document.getElementById('plannedOutageSection');
const elPlannedHeaderDot = document.getElementById('plannedHeaderDot');
const elPlannedCounterBadge = document.getElementById('plannedCounterBadge');
const elPlannedEmptyState = document.getElementById('plannedEmptyState');
const elPlannedContentState = document.getElementById('plannedContentState');
const elPlannedList = document.getElementById('plannedList');
const elWidgetPlannedAlert = document.getElementById('widgetPlannedAlert');
const elWidgetPlannedCd = document.getElementById('widgetPlannedCd');

const navTabs = document.querySelectorAll('.nav-tab');
const tabPanes = document.querySelectorAll('.tab-pane');

const simMessageInput = document.getElementById('simMessageInput');
const btnApplySimMessage = document.getElementById('btnApplySimMessage');
const btnClearSimInput = document.getElementById('btnClearSimInput');
const simStatusBanner = document.getElementById('simStatusBanner');
const simStatusText = document.getElementById('simStatusText');

const localApiEndpoint = document.getElementById('localApiEndpoint');
const btnCopyEndpoint = document.getElementById('btnCopyEndpoint');
const scriptableCodeArea = document.getElementById('scriptableCodeArea');
const btnCopyScriptableCode = document.getElementById('btnCopyScriptableCode');

const tgStatusBanner = document.getElementById('tgStatusBanner');
const tgStatusText = document.getElementById('tgStatusText');
const tgApiId = document.getElementById('tgApiId');
const tgApiHash = document.getElementById('tgApiHash');
const tgPhone = document.getElementById('tgPhone');
const tgBotUsername = document.getElementById('tgBotUsername');
const tgFilterAddress = document.getElementById('tgFilterAddress');
const btnSaveAndConnectTg = document.getElementById('btnSaveAndConnectTg');
const btnDisconnectTg = document.getElementById('btnDisconnectTg');
const authCodePrompt = document.getElementById('authCodePrompt');
const tgCodeInput = document.getElementById('tgCodeInput');
const btnSubmitCode = document.getElementById('btnSubmitCode');
const authPassPrompt = document.getElementById('authPassPrompt');
const tgPassInput = document.getElementById('tgPassInput');
const btnSubmitPass = document.getElementById('btnSubmitPass');

const historyList = document.getElementById('historyList');

const appContainer = document.querySelector('.app-container');
const desktopWidgetView = document.getElementById('desktopWidgetView');
const btnSwitchToWidgetMode = document.getElementById('btnSwitchToWidgetMode');
const btnExpandWidget = document.getElementById('btnExpandWidget');
const widgetCountdown = document.getElementById('widgetCountdown');
const widgetEndTime = document.getElementById('widgetEndTime');
const widgetProgressFill = document.getElementById('widgetProgressFill');
const widgetStatusBadge = document.getElementById('widgetStatusBadge');
const widgetStatusText = document.getElementById('widgetStatusText');

const btnMinimize = document.getElementById('btnMinimize');
const btnClose = document.getElementById('btnClose');
const btnRefreshStatus = document.getElementById('btnRefreshStatus');
const btnOpenSimulator = document.getElementById('btnOpenSimulator');
const toast = document.getElementById('toast');
const plannedContextMenu = document.getElementById('plannedContextMenu');
const btnDeletePlannedItem = document.getElementById('btnDeletePlannedItem');
const plannedThCountdown = document.getElementById('plannedThCountdown');
const widgetPlannedLabel = document.getElementById('widgetPlannedLabel');
let plannedContextMenuTarget = null;
const triggeredPlannedStartRefreshes = new Set();
let isRefreshCooldown = false;
let isNetworkOnline = (typeof navigator.onLine === 'boolean') ? navigator.onLine : true;

function updateNetworkConnectivityUI(online) {
  isNetworkOnline = (online !== false);
  const badge = document.getElementById('noInternetBadge');
  if (badge) {
    badge.style.display = isNetworkOnline ? 'none' : 'inline-flex';
  }
  if (btnRefreshStatus) {
    if (!isNetworkOnline) {
      btnRefreshStatus.disabled = true;
      btnRefreshStatus.classList.add('is-offline');
      btnRefreshStatus.setAttribute('title', 'Нету подключения к интернету');
    } else {
      btnRefreshStatus.classList.remove('is-offline');
      btnRefreshStatus.setAttribute('title', 'Запросить статус у бота');
      if (!isRefreshCooldown && !btnRefreshStatus.classList.contains('is-refreshing')) {
        btnRefreshStatus.disabled = false;
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupSettings();
  setupEventListeners();
  setupWidgetModeListeners();
  startSystemClock();

  waitForPywebview();

  setTimeout(() => {
    dismissSplash();
  }, 9000);
});

let toastTimeout = null;

function showToast(msg) {
  const toastEl = document.getElementById('toast');
  const toastMsgEl = document.getElementById('toastMessage') || toastEl;
  if (!toastEl) return;
  if (toastMsgEl) toastMsgEl.textContent = msg;
  const pos = appSettings.toastPosition || 'bottom-right';
  toastEl.className = `toast pos-${pos} show`;
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toastEl.classList.remove('show');
  }, 2600);
}

let currentTabIndex = 0;

function setupTabs() {
  const tabsArray = Array.from(navTabs);
  tabsArray.forEach((tab, index) => {
    if (tab.classList.contains('active')) {
      currentTabIndex = index;
    }
    tab.addEventListener('click', () => {
      if (tab.classList.contains('active')) return;
      const target = tab.getAttribute('data-tab');
      const nextPane = document.getElementById(`tab-${target}`);
      if (!nextPane) return;

      const newIndex = index;
      const direction = newIndex > currentTabIndex ? 'right' : 'left';
      currentTabIndex = newIndex;

      const currentPane = document.querySelector('.tab-pane.active');

      navTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      if (currentPane && currentPane !== nextPane) {
        currentPane.classList.remove('slide-in-right', 'slide-in-left', 'slide-out-right', 'slide-out-left');
        currentPane.classList.add(direction === 'right' ? 'slide-out-left' : 'slide-out-right');

        nextPane.classList.remove('slide-in-right', 'slide-in-left', 'slide-out-right', 'slide-out-left');
        nextPane.classList.add('active', direction === 'right' ? 'slide-in-right' : 'slide-in-left');

        setTimeout(() => {
          if (currentPane !== nextPane) {
            currentPane.classList.remove('active', 'slide-out-left', 'slide-out-right');
          }
          nextPane.classList.remove('slide-in-right', 'slide-in-left');
        }, 250);
      } else {
        tabPanes.forEach(p => p.classList.remove('active', 'slide-in-right', 'slide-in-left', 'slide-out-right', 'slide-out-left'));
        nextPane.classList.add('active');
      }

      if (target === 'history') loadHistory();
      if (target === 'iphone') loadIPhoneData();
    });
  });

  const navTabsContainer = document.getElementById('navTabs');
  if (navTabsContainer && appContainer) {
    navTabsContainer.addEventListener('mouseenter', () => {
      appContainer.classList.add('nav-tabs-hovered');
    });
    navTabsContainer.addEventListener('mouseleave', () => {
      appContainer.classList.remove('nav-tabs-hovered');
    });
  }
}

function startSystemClock() {
  const update = () => {
    if (!elSystemClock) return;
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    if (appSettings.showSeconds) {
      const s = String(now.getSeconds()).padStart(2, '0');
      elSystemClock.textContent = `${h}:${m}:${s}`;
    } else {
      elSystemClock.textContent = `${h}:${m}`;
    }
  };
  update();
  setInterval(update, 1000);
}

function formatLightOnDuration(ms) {
  const totalMinutes = Math.floor(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) return `${hours} ч ${minutes} мин`;
  return `${minutes} мин`;
}

function showLightOnStatus(extraNote) {
  if (elTimerDigits) {
    elTimerDigits.innerHTML = '<span class="status-heading-on"><span class="status-bolt"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" style="vertical-align: -2px; margin-right: 6px;"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg></span> Свет есть</span>';
  }
  if (elTimerLabel) {
    if (extraNote) {
      elTimerLabel.textContent = extraNote;
    } else {
      const sinceText = lightOnSince ? formatLightOnDuration(Date.now() - lightOnSince) : null;
      elTimerLabel.textContent = sinceText ? `Со светом уже: ${sinceText}` : 'Электросеть работает в штатном режиме';
    }
    elTimerLabel.className = 'timer-subtitle status-sub-on';
    elTimerLabel.style.color = '';
  }
}

function getPlannedOutagesList(state) {
  if (!state) return [];
  const nowTs = Math.floor(Date.now() / 1000);
  let list = Array.isArray(state.planned_outages) ? state.planned_outages.slice() : [];
  if (list.length === 0 && state.is_planned && state.start_timestamp && state.status !== 'OFF') {
    list = [{
      start_time_str: state.start_time_str,
      end_time_str: state.end_time_str,
      start_timestamp: state.start_timestamp,
      end_timestamp: state.end_timestamp,
      reason: state.reason
    }];
  }
  return list.filter(item => !item.end_timestamp || item.end_timestamp > nowTs)
             .sort((a, b) => (a.start_timestamp || 0) - (b.start_timestamp || 0));
}

function formatPlannedDateColumn(item) {
  let dObj = null;
  if (item.start_timestamp) {
    dObj = new Date(item.start_timestamp * 1000);
  } else if (item.start_time_str) {
    const m = item.start_time_str.match(/^(\d{1,2})\.(\d{1,2})\.(\d{2,4})/);
    if (m) {
      const yr = m[3].length === 2 ? parseInt('20' + m[3], 10) : parseInt(m[3], 10);
      dObj = new Date(yr, parseInt(m[2], 10) - 1, parseInt(m[1], 10));
    }
  }
  if (!dObj || isNaN(dObj.getTime())) {
    return item.start_time_str ? item.start_time_str.split(' ')[0] : '—';
  }

  const pad = n => String(n).padStart(2, '0');
  const d = pad(dObj.getDate());
  const m = pad(dObj.getMonth() + 1);
  const yy = String(dObj.getFullYear()).slice(-2);
  const baseDate = `${d}.${m}.${yy}`;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const targetMidnight = new Date(dObj);
  targetMidnight.setHours(0, 0, 0, 0);
  const diffDays = Math.round((targetMidnight - today) / (1000 * 60 * 60 * 24));

  let rel = '';
  if (diffDays === 0) rel = 'сегодня';
  else if (diffDays === 1) rel = 'завтра';
  else if (diffDays === 2) rel = 'послезавтра';
  else if (diffDays === -1) rel = 'вчера';

  if (rel) {
    return `${baseDate} <span class="rel-tag">(${rel})</span>`;
  }
  return baseDate;
}

function formatPlannedTimeColumn(item) {
  let sTime = '';
  let eTime = '';
  if (item.start_time_str) {
    const m = item.start_time_str.match(/(\d{1,2}:\d{2})/);
    if (m) sTime = m[1];
  }
  if (!sTime && item.start_timestamp) {
    const d = new Date(item.start_timestamp * 1000);
    sTime = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  }

  if (item.end_time_str) {
    const m = item.end_time_str.match(/(\d{1,2}:\d{2})/);
    if (m) eTime = m[1];
  }
  if (!eTime && item.end_timestamp) {
    const d = new Date(item.end_timestamp * 1000);
    eTime = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  }

  if (sTime && eTime) return `${sTime} - ${eTime}`;
  if (sTime) return `С ${sTime}`;
  if (eTime) return `До ${eTime}`;
  return '—';
}

function formatPlannedCountdownColumn(item, nowTs) {
  const pad = n => String(n).padStart(2, '0');
  if (item.start_timestamp && nowTs >= item.start_timestamp) {
    if (item.end_timestamp && nowTs < item.end_timestamp) {
      const diffEnd = Math.max(0, item.end_timestamp - nowTs);
      const days = Math.floor(diffEnd / 86400);
      const hours = Math.floor((diffEnd % 86400) / 3600);
      const mins = Math.floor((diffEnd % 3600) / 60);
      const secs = diffEnd % 60;
      const cdStr = days > 0 ? `${days}д ${pad(hours)}:${pad(mins)}:${pad(secs)}` : `${pad(hours)}:${pad(mins)}:${pad(secs)}`;
      return `<span class="active-now" title="До окончания: ${cdStr}"><span class="pulse-dot-red"></span>${cdStr}</span>`;
    }
    if (!item.end_timestamp) {
      return '<span class="active-now"><span class="pulse-dot-red"></span>Идет сейчас</span>';
    }
    return '<span style="color: var(--text-muted);">Завершено</span>';
  }

  if (!item.start_timestamp) return '—';

  const diff = Math.max(0, item.start_timestamp - nowTs);
  const days = Math.floor(diff / 86400);
  const hours = Math.floor((diff % 86400) / 3600);
  const mins = Math.floor((diff % 3600) / 60);
  const secs = diff % 60;

  if (days > 0) {
    return `${days}д ${pad(hours)}:${pad(mins)}:${pad(secs)}`;
  }
  return `${pad(hours)}:${pad(mins)}:${pad(secs)}`;
}

let lastRenderedPlannedCount = -1;

function updatePlannedOutagesDisplay(forceRebuild = false) {
  if (!elPlannedOutageSection) return;
  const nowTs = Math.floor(Date.now() / 1000);
  const plannedList = getPlannedOutagesList(currentState);

  if (plannedList.length === 0) {
    elPlannedOutageSection.classList.remove('has-planned');
    if (elPlannedCounterBadge) elPlannedCounterBadge.style.display = 'none';
    if (elPlannedEmptyState) elPlannedEmptyState.style.display = 'flex';
    if (elPlannedContentState) elPlannedContentState.style.display = 'none';
    if (elWidgetPlannedAlert) elWidgetPlannedAlert.style.display = 'none';
    lastRenderedPlannedCount = 0;
    return;
  }

  elPlannedOutageSection.classList.add('has-planned');
  if (elPlannedCounterBadge) {
    elPlannedCounterBadge.style.display = 'inline-flex';
    elPlannedCounterBadge.textContent = String(plannedList.length);
  }
  if (elPlannedEmptyState) elPlannedEmptyState.style.display = 'none';
  if (elPlannedContentState) elPlannedContentState.style.display = 'flex';
  if (elWidgetPlannedAlert) elWidgetPlannedAlert.style.display = 'inline-flex';

  const nearest = plannedList[0];
  if (nearest && nearest.start_timestamp && elWidgetPlannedCd) {
    if (nowTs >= nearest.start_timestamp && (!nearest.end_timestamp || nowTs < nearest.end_timestamp)) {
      if (widgetPlannedLabel) widgetPlannedLabel.textContent = 'До конца: ';
      if (nearest.end_timestamp) {
        const diffEnd = Math.max(0, nearest.end_timestamp - nowTs);
        const pad = n => String(n).padStart(2, '0');
        const d = Math.floor(diffEnd / 86400);
        const h = Math.floor((diffEnd % 86400) / 3600);
        const m = Math.floor((diffEnd % 3600) / 60);
        const s = diffEnd % 60;
        elWidgetPlannedCd.textContent = d > 0 ? `${d}д ${h}ч ${m}м` : `${pad(h)}:${pad(m)}:${pad(s)}`;
      } else {
        elWidgetPlannedCd.textContent = 'Идет сейчас';
      }
    } else {
      if (widgetPlannedLabel) widgetPlannedLabel.textContent = 'До откл: ';
      const diff = Math.max(0, nearest.start_timestamp - nowTs);
      const pad = n => String(n).padStart(2, '0');
      const d = Math.floor(diff / 86400);
      const h = Math.floor((diff % 86400) / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      elWidgetPlannedCd.textContent = d > 0 ? `${d}д ${h}ч ${m}м` : `${pad(h)}:${pad(m)}:${pad(s)}`;
    }
  }

  if (plannedThCountdown) {
    const hasActive = plannedList.some(it => it.start_timestamp && nowTs >= it.start_timestamp && (!it.end_timestamp || nowTs < it.end_timestamp));
    plannedThCountdown.textContent = hasActive ? 'До окончания' : 'До отключения';
  }

  if (forceRebuild || lastRenderedPlannedCount !== plannedList.length || !elPlannedList || elPlannedList.children.length !== plannedList.length) {
    if (elPlannedList) {
      elPlannedList.innerHTML = '';
      plannedList.forEach((item, idx) => {
        const row = document.createElement('div');
        const isCurrent = item.start_timestamp && nowTs >= item.start_timestamp && (!item.end_timestamp || nowTs < item.end_timestamp);
        row.className = isCurrent ? 'planned-item-row is-current' : 'planned-item-row';
        row.id = `plannedRow_${idx}`;
        row.dataset.idx = String(idx);
        row.dataset.startTs = String(item.start_timestamp || '');
        row.dataset.endTs = String(item.end_timestamp || '');
        row.innerHTML = `
          <span class="col-num">${idx + 1}.</span>
          <span class="col-date">${formatPlannedDateColumn(item)}</span>
          <span class="col-time">${formatPlannedTimeColumn(item)}</span>
          <span class="col-countdown" id="plannedCdRow_${idx}">${formatPlannedCountdownColumn(item, nowTs)}</span>
        `;
        elPlannedList.appendChild(row);
      });
    }
    lastRenderedPlannedCount = plannedList.length;
  } else {
    plannedList.forEach((item, idx) => {
      const cdEl = document.getElementById(`plannedCdRow_${idx}`);
      if (cdEl) {
        cdEl.innerHTML = formatPlannedCountdownColumn(item, nowTs);
      }
      const row = document.getElementById(`plannedRow_${idx}`);
      if (row) {
        row.dataset.idx = String(idx);
        row.dataset.startTs = String(item.start_timestamp || '');
        row.dataset.endTs = String(item.end_timestamp || '');
        const isCurrent = item.start_timestamp && nowTs >= item.start_timestamp && (!item.end_timestamp || nowTs < item.end_timestamp);
        if (isCurrent && !row.classList.contains('is-current')) {
          row.classList.add('is-current');
        } else if (!isCurrent && row.classList.contains('is-current')) {
          row.classList.remove('is-current');
        }
      }
    });
  }
}

function updateCountdown() {
  const nowTs = Math.floor(Date.now() / 1000);

  updatePlannedOutagesDisplay(false);

  const plannedList = getPlannedOutagesList(currentState);
  plannedList.forEach(item => {
    if (item.start_timestamp && nowTs >= item.start_timestamp) {
      if (!triggeredPlannedStartRefreshes.has(item.start_timestamp)) {
        triggeredPlannedStartRefreshes.add(item.start_timestamp);
        if (btnRefreshStatus && !btnRefreshStatus.classList.contains('is-offline')) {
          if (btnRefreshStatus.disabled) {
            btnRefreshStatus.disabled = false;
            btnRefreshStatus.classList.remove('is-cooldown');
          }
          btnRefreshStatus.click();
        }
      }
    }
  });

  if (currentState && Array.isArray(currentState.planned_outages)) {
    const prevCount = currentState.planned_outages.length;
    currentState.planned_outages = currentState.planned_outages.filter(it => !it.end_timestamp || it.end_timestamp > nowTs);
    if (currentState.planned_outages.length !== prevCount) {
      if (currentState.planned_outages.length > 0) {
        const nextPo = currentState.planned_outages[0];
        currentState.is_planned = true;
        currentState.start_timestamp = nextPo.start_timestamp;
        currentState.end_timestamp = nextPo.end_timestamp;
        currentState.start_time_str = nextPo.start_time_str;
        currentState.end_time_str = nextPo.end_time_str;
      } else {
        currentState.is_planned = false;
        currentState.start_timestamp = null;
        currentState.end_timestamp = null;
        currentState.start_time_str = null;
        currentState.end_time_str = null;
      }
      updatePlannedOutagesDisplay(true);
    }
  } else if (currentState && currentState.end_timestamp && nowTs >= currentState.end_timestamp && currentState.is_planned) {
    currentState.is_planned = false;
    currentState.start_timestamp = null;
    currentState.end_timestamp = null;
    currentState.start_time_str = null;
    currentState.end_time_str = null;
    updatePlannedOutagesDisplay(true);
  }

  if (!currentState || currentState.status !== 'OFF' || !currentState.end_timestamp) {
    if (currentState && currentState.light_on_since) {
      lightOnSince = currentState.light_on_since;
    } else if (lightOnSince === null) {
      const saved = localStorage.getItem('lightwidget_light_on_since');
      lightOnSince = saved ? parseInt(saved, 10) : Date.now();
      localStorage.setItem('lightwidget_light_on_since', lightOnSince);
    }
    showLightOnStatus();
    if (elProgressBarFill) {
      elProgressBarFill.className = 'slim-progress-fill';
      elProgressBarFill.style.width = '100%';
    }
    if (elProgressPercentText) elProgressPercentText.textContent = '100%';

    if (elLivePill) elLivePill.className = 'live-pill';
    if (elLivePillText) elLivePillText.textContent = 'СВЕТ ЕСТЬ';
    if (elStatusBadge) elStatusBadge.className = 'status-badge';
    if (elStatusLabel) elStatusLabel.textContent = 'СВЕТ ЕСТЬ';

    if (elBrandStatusDot) elBrandStatusDot.className = 'brand-status-dot on';
    if (widgetCountdown) widgetCountdown.innerHTML = '<span class="widget-heading-on"><span class="status-bolt"><svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style="vertical-align: -2px; margin-right: 4px;"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg></span> Свет есть</span>';
    if (widgetStatusText) widgetStatusText.textContent = 'СВЕТ ЕСТЬ';
    if (widgetStatusBadge) widgetStatusBadge.className = 'widget-status';
    if (widgetEndTime) widgetEndTime.textContent = 'стабильно';
    if (widgetProgressFill) {
      widgetProgressFill.className = 'widget-bar-fill';
      widgetProgressFill.style.width = '100%';
    }

    if (elRowReason) elRowReason.style.display = 'none';
    if (elRowStart) elRowStart.style.display = 'none';
    if (elRowEnd) elRowEnd.style.display = 'none';
    return;
  }

  const endTs = currentState.end_timestamp;
  const startTs = currentState.start_timestamp || (endTs - 3600);

  const diff = Math.max(0, endTs - nowTs);

  if (diff === 0) {
    document.documentElement.setAttribute('data-power-status', 'ON');
    document.body.setAttribute('data-power-status', 'ON');
    const appContainer = document.querySelector('.app-container');
    if (appContainer) {
      appContainer.classList.remove('power-off', 'power-planned');
      appContainer.classList.add('power-on');
    }

    if (elBrandStatusDot) elBrandStatusDot.className = 'brand-status-dot on';

    if (currentState && currentState.light_on_since) {
      lightOnSince = currentState.light_on_since;
    } else if (lightOnSince === null) {
      lightOnSince = Date.now();
      localStorage.setItem('lightwidget_light_on_since', lightOnSince);
    }
    showLightOnStatus('Время отключения завершено • Электросеть работает');

    if (elLivePill) elLivePill.className = 'live-pill';
    if (elLivePillText) elLivePillText.textContent = 'СВЕТ ЕСТЬ';
    if (elStatusBadge) elStatusBadge.className = 'status-badge';
    if (elStatusLabel) elStatusLabel.textContent = 'СВЕТ ЕСТЬ';

    if (widgetCountdown) {
      widgetCountdown.innerHTML = '<span class="widget-heading-on"><span class="status-bolt"><svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style="vertical-align: -2px; margin-right: 4px;"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg></span> Свет есть</span>';
    }
    if (widgetStatusText) widgetStatusText.textContent = 'СВЕТ ЕСТЬ';
    if (widgetStatusBadge) widgetStatusBadge.className = 'widget-status';
    if (widgetEndTime) widgetEndTime.textContent = 'стабильно';

    if (elRowReason) elRowReason.style.display = 'none';
    if (elRowStart) elRowStart.style.display = 'none';
    if (elRowEnd) elRowEnd.style.display = 'none';

    if (elProgressBarFill) {
      elProgressBarFill.className = 'slim-progress-fill';
      elProgressBarFill.style.width = '100%';
    }
    if (elProgressPercentText) elProgressPercentText.textContent = '100%';
    if (widgetProgressFill) {
      widgetProgressFill.className = 'widget-bar-fill';
      widgetProgressFill.style.width = '100%';
    }
    return;
  }

  const days = Math.floor(diff / 86400);
  const hours = Math.floor((diff % 86400) / 3600);
  const minutes = Math.floor((diff % 3600) / 60);
  const seconds = diff % 60;
  const showSeconds = appSettings.showSeconds !== false;

  const parts = [];
  const textParts = [];

  if (days > 0) {
    parts.push(`<span class="cd-unit"><span class="cd-num">${days}</span><span class="cd-label">д</span></span>`);
    textParts.push(`${days}д`);
  }
  if (days > 0 || hours > 0) {
    const hDisplay = (days > 0) ? hours : (hours < 10 ? `0${hours}` : hours);
    parts.push(`<span class="cd-unit"><span class="cd-num">${hDisplay}</span><span class="cd-label">ч</span></span>`);
    textParts.push(`${hours}ч`);
  }
  if (days > 0 || hours > 0 || minutes > 0) {
    const mDisplay = (days === 0 && hours === 0) ? minutes : String(minutes).padStart(2, '0');
    parts.push(`<span class="cd-unit"><span class="cd-num">${mDisplay}</span><span class="cd-label">м</span></span>`);
    textParts.push(`${minutes}м`);
  }
  if (showSeconds || (days === 0 && hours === 0 && minutes === 0)) {
    const sDisplay = (days === 0 && hours === 0 && minutes === 0) ? seconds : String(seconds).padStart(2, '0');
    parts.push(`<span class="cd-unit"><span class="cd-num">${sDisplay}</span><span class="cd-label">с</span></span>`);
    textParts.push(`${seconds}с`);
  }

  if (elTimerDigits) {
    elTimerDigits.innerHTML = parts.join('');
  }
  if (elTimerLabel) {
    elTimerLabel.textContent = 'до ориентировочного включения';
    elTimerLabel.className = 'timer-subtitle status-sub-off';
    elTimerLabel.style.color = '';
  }

  if (elBrandStatusDot) elBrandStatusDot.className = 'brand-status-dot off';
  if (widgetCountdown) widgetCountdown.textContent = textParts.join(' ');

  const total = Math.max(1, endTs - startTs);
  const elapsed = Math.max(0, Math.min(total, nowTs - startTs));
  const pct = Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)));

  if (elProgressBarFill) {
    elProgressBarFill.className = 'slim-progress-fill';
    elProgressBarFill.style.width = `${pct}%`;
  }
  if (elProgressPercentText) elProgressPercentText.textContent = `${pct}%`;
  if (widgetProgressFill) {
    widgetProgressFill.className = 'widget-bar-fill';
    widgetProgressFill.style.width = `${pct}%`;
  }
}

let isAddressRevealed = false;
const btnToggleAddress = document.getElementById('btnToggleAddress');
const addrToggleText = document.getElementById('addrToggleText');
const eyeIcon = document.getElementById('eyeIcon');

function updateAddressDisplay() {
  const fullAddress = currentState?.address || 'Не указан';
  if (isAddressRevealed) {
    elDetailAddress.textContent = fullAddress;
    elDetailAddress.className = 'info-val';
    if (addrToggleText) addrToggleText.textContent = 'Скрыть';
  } else {
    elDetailAddress.textContent = '••••••••••••••••••••••••';
    elDetailAddress.className = 'info-val address-masked';
    if (addrToggleText) addrToggleText.textContent = 'Показать';
  }
}

function formatWithRelativeDay(dateStr) {
  if (!dateStr || dateStr === '—') return '—';
  const match = dateStr.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}:\d{2})/);
  if (!match) return dateStr;

  const [_, d, m, y, time] = match;
  const targetDate = new Date(parseInt(y), parseInt(m) - 1, parseInt(d));
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const targetMidnight = new Date(targetDate);
  targetMidnight.setHours(0, 0, 0, 0);

  const diffDays = Math.round((targetMidnight - today) / (1000 * 60 * 60 * 24));
  let relText = '';
  if (diffDays === 0) {
    relText = 'сегодня';
  } else if (diffDays === -1) {
    relText = 'вчера';
  } else if (diffDays === 1) {
    relText = 'завтра';
  } else if (diffDays === -2) {
    relText = 'позавчера';
  } else if (diffDays === 2) {
    relText = 'послезавтра';
  }

  if (relText) {
    return `${dateStr} <span class="time-relative-tag">(${relText})</span>`;
  }
  return dateStr;
}

function renderState(state) {
  if (!state) return;
  currentState = state;

  const isOutage = state.status === 'OFF';
  const nowTs = Math.floor(Date.now() / 1000);
  const plannedList = getPlannedOutagesList(state);
  const isUpcomingPlanned = !isOutage && (plannedList.length > 0 || (state.is_planned && state.start_timestamp && (nowTs < state.start_timestamp)));

  if (isOutage) {
    lightOnSince = null;
    localStorage.removeItem('lightwidget_light_on_since');
  } else {
    if (state.light_on_since) {
      lightOnSince = state.light_on_since;
    } else if (lightOnSince === null) {
      const saved = localStorage.getItem('lightwidget_light_on_since');
      lightOnSince = saved ? parseInt(saved, 10) : Date.now();
    }
    localStorage.setItem('lightwidget_light_on_since', lightOnSince);
  }

  document.documentElement.setAttribute('data-power-status', isOutage ? 'OFF' : 'ON');
  document.body.setAttribute('data-power-status', isOutage ? 'OFF' : 'ON');
  const appContainer = document.querySelector('.app-container');
  if (appContainer) {
    appContainer.classList.remove('power-off', 'power-planned');
    if (isOutage) {
      appContainer.classList.add('power-off');
      appContainer.classList.remove('power-on');
    } else {
      appContainer.classList.add('power-on');
      appContainer.classList.remove('power-off');
    }
  }

  if (elBrandStatusDot) {
    elBrandStatusDot.className = isOutage ? 'brand-status-dot off' : 'brand-status-dot on';
  }

  if (isOutage) {
    if (elHeroCard) elHeroCard.className = 'hero-card outage';
    if (elLivePill) elLivePill.className = 'live-pill off';
    if (elLivePillText) elLivePillText.textContent = 'СВЕТ ОТКЛЮЧЕН';
    if (elStatusBadge) elStatusBadge.className = 'status-badge off';
    if (elStatusLabel) elStatusLabel.textContent = 'СВЕТ ОТКЛЮЧЕН';

    if (widgetStatusBadge) widgetStatusBadge.className = 'widget-status off';
    if (widgetStatusText) widgetStatusText.textContent = 'СВЕТ ОТКЛЮЧЕН';
    if (widgetEndTime) {
      const match = state.end_time_str?.match(/\d{1,2}:\d{2}/);
      widgetEndTime.textContent = match ? `до ${match[0]}` : (state.end_time_str ? `до ${state.end_time_str}` : 'уточняется');
    }

  } else {
    if (elHeroCard) elHeroCard.className = 'hero-card normal';
    if (elLivePill) elLivePill.className = 'live-pill';
    if (elLivePillText) elLivePillText.textContent = 'СВЕТ ЕСТЬ';
    if (elStatusBadge) elStatusBadge.className = 'status-badge';
    if (elStatusLabel) elStatusLabel.textContent = 'СВЕТ ЕСТЬ';

    if (widgetStatusBadge) widgetStatusBadge.className = 'widget-status';
    if (widgetStatusText) widgetStatusText.textContent = 'СВЕТ ЕСТЬ';
    if (widgetEndTime) widgetEndTime.textContent = 'стабильно';
  }

  updatePlannedOutagesDisplay(true);

  updateAddressDisplay();
  const showRows = isOutage || isUpcomingPlanned;
  if (elRowReason) elRowReason.style.display = showRows ? 'flex' : 'none';
  if (elRowStart) elRowStart.style.display = showRows ? 'flex' : 'none';
  if (elRowEnd) elRowEnd.style.display = showRows ? 'flex' : 'none';

  if (showRows) {
    if (elDetailReason) elDetailReason.textContent = state.reason || (isUpcomingPlanned ? 'Запланированы ремонтные работы' : 'Аварийно-восстановительные работы');
    if (elDetailStart) elDetailStart.innerHTML = formatWithRelativeDay(state.start_time_str);
    if (elDetailEnd) elDetailEnd.innerHTML = formatWithRelativeDay(state.end_time_str || 'Уточняется');
  }

  if (state.updated_at) {
    const d = new Date(state.updated_at);
    elLastUpdatedText.textContent = `Обновлено: ${d.toLocaleTimeString()}`;
  }

  if (countdownInterval) clearInterval(countdownInterval);
  updateCountdown();
  countdownInterval = setInterval(updateCountdown, 1000);
  updateNetworkStats();
}

let cachedHistory = [];
try {
  const savedHist = localStorage.getItem('lightwidget_history');
  if (savedHist) cachedHistory = JSON.parse(savedHist);
} catch (e) { }

function updateNetworkStats(history) {
  if (Array.isArray(history)) cachedHistory = history;
  const historyData = cachedHistory;

  const elTimeOn = document.getElementById('statsTimeOn');
  const elTimeOff = document.getElementById('statsTimeOff');
  const elPercentOn = document.getElementById('statsPercentOn');
  const elPercentOff = document.getElementById('statsPercentOff');
  const elOutageCount = document.getElementById('statsOutageCount');
  const elUptimeBadge = document.getElementById('statsUptimeBadge');
  const elRatioOn = document.getElementById('ratioFillOn');
  const elRatioOff = document.getElementById('ratioFillOff');

  if (!elTimeOn) return;

  const now = Date.now();
  const dayMs = 24 * 60 * 60 * 1000;
  const dayAgo = now - dayMs;

  let totalOffSeconds = 0;
  let outageEvents = 0;
  const isCurrentOff = currentState && (currentState.status === 'OFF' || currentState.is_outage === true);
  const currentStartTs = isCurrentOff && currentState.start_timestamp ? currentState.start_timestamp * 1000 : null;

  const seenOutages = new Set();

  if (Array.isArray(historyData) && historyData.length > 0) {
    historyData.forEach(item => {
      const itemTime = new Date(item.timestamp || item.updated_at).getTime();
      if (itemTime >= dayAgo && item.status === 'OFF') {
        const itemStartTs = item.start_timestamp ? item.start_timestamp * 1000 : itemTime;
        const key = `${item.start_timestamp || item.start_time_str || Math.floor(itemTime / 60000)}`;
        if (seenOutages.has(key)) return;
        seenOutages.add(key);

        outageEvents++;

        const isThisOngoing = isCurrentOff && (
          (currentStartTs && Math.abs(currentStartTs - itemStartTs) < 300000) ||
          (currentState.start_time_str && currentState.start_time_str === item.start_time_str)
        );

        if (isThisOngoing) {
          const elapsed = currentState.elapsed_seconds || Math.max(0, Math.floor((now - itemStartTs) / 1000));
          totalOffSeconds += Math.max(0, elapsed);
        } else {
          const total = item.total_seconds || (item.end_timestamp && item.start_timestamp ? (item.end_timestamp - item.start_timestamp) : 0);
          if (total > 0) {
            totalOffSeconds += total;
          }
        }
      }
    });
  }

  if (isCurrentOff && outageEvents === 0) {
    outageEvents = 1;
    const elapsed = currentState.elapsed_seconds || (currentStartTs ? Math.max(0, Math.floor((now - currentStartTs) / 1000)) : 0);
    totalOffSeconds += Math.max(0, elapsed);
  }

  totalOffSeconds = Math.min(86400, Math.max(0, totalOffSeconds));
  const totalOnSeconds = 86400 - totalOffSeconds;

  const pctOn = Math.round((totalOnSeconds / 86400) * 100);
  const pctOff = 100 - pctOn;

  const onH = Math.floor(totalOnSeconds / 3600);
  const onM = Math.floor((totalOnSeconds % 3600) / 60);
  const offH = Math.floor(totalOffSeconds / 3600);
  const offM = Math.floor((totalOffSeconds % 3600) / 60);

  elTimeOn.textContent = `${onH}ч ${String(onM).padStart(2, '0')}м`;
  elTimeOff.textContent = `${offH}ч ${String(offM).padStart(2, '0')}м`;
  if (elPercentOn) elPercentOn.textContent = `${pctOn}% суток`;
  if (elPercentOff) elPercentOff.textContent = `${pctOff}% суток`;
  if (elOutageCount) elOutageCount.textContent = `${outageEvents}`;

  if (elUptimeBadge) {
    elUptimeBadge.textContent = `${pctOn}% со светом`;
    if (pctOn < 80) {
      elUptimeBadge.className = 'stats-uptime-badge warning';
    } else {
      elUptimeBadge.className = 'stats-uptime-badge';
    }
  }

  if (elRatioOn) elRatioOn.style.width = `${pctOn}%`;
  if (elRatioOff) elRatioOff.style.width = `${pctOff}%`;

  renderHeatmap(historyData);
}

let cachedDailyStats = {};
try {
  const saved = localStorage.getItem('lightwidget_daily_stats');
  if (saved) cachedDailyStats = JSON.parse(saved);
} catch (e) { }

function renderHeatmap(historyData, extraDailyStats) {
  const grid = document.getElementById('heatmapGrid');
  const monthsRow = document.getElementById('ghMonthsRow');
  const badge = document.getElementById('heatmapSummaryBadge');
  if (!grid) return;

  grid.innerHTML = '';
  if (monthsRow) monthsRow.innerHTML = '';

  const ruMonths = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
  const now = new Date();
  const numWeeks = 18;
  const currentDayOfWeek = (now.getDay() + 6) % 7;

  const historyMap = {};
  if (extraDailyStats && typeof extraDailyStats === 'object' && Object.keys(extraDailyStats).length > 0) {
    Object.keys(extraDailyStats).forEach(k => {
      historyMap[k] = Object.assign({}, extraDailyStats[k]);
    });
  } else if (cachedDailyStats && typeof cachedDailyStats === 'object') {
    Object.keys(cachedDailyStats).forEach(k => {
      historyMap[k] = Object.assign({}, cachedDailyStats[k]);
    });
  }

  const computedFromHistory = {};
  if (Array.isArray(historyData)) {
    const seenOutages = new Set();
    historyData.forEach(item => {
      const itemDateStr = (item.timestamp || item.updated_at || '').split('T')[0];
      if (itemDateStr) {
        if (!computedFromHistory[itemDateStr]) {
          computedFromHistory[itemDateStr] = { count: 0, offSec: 0, recorded: true };
        }
        if (item.status === 'OFF') {
          const key = `${itemDateStr}_${item.start_timestamp || item.start_time_str || item.timestamp}`;
          if (seenOutages.has(key)) return;
          seenOutages.add(key);

          computedFromHistory[itemDateStr].count++;
          const total = item.total_seconds || (item.end_timestamp && item.start_timestamp ? (item.end_timestamp - item.start_timestamp) : 0);
          computedFromHistory[itemDateStr].offSec += (total > 0 ? total : 3600);
        }
      }
    });
  }

  Object.keys(computedFromHistory).forEach(k => {
    if (!historyMap[k]) {
      historyMap[k] = computedFromHistory[k];
    } else {
      historyMap[k].count = Math.max(historyMap[k].count || 0, computedFromHistory[k].count || 0);
      historyMap[k].offSec = Math.max(historyMap[k].offSec || 0, computedFromHistory[k].offSec || 0);
      historyMap[k].recorded = true;
    }
  });

  const todayKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  if (!historyMap[todayKey]) {
    historyMap[todayKey] = { count: 0, offSec: 0, recorded: true };
  }
  if (currentState && (currentState.status === 'OFF' || currentState.is_outage === true)) {
    historyMap[todayKey].count = Math.max(1, historyMap[todayKey].count);
    const elapsed = currentState.elapsed_seconds || 3600;
    if (historyMap[todayKey].offSec < elapsed) {
      historyMap[todayKey].offSec = elapsed;
    }
  }

  let earliestDateKey = null;
  Object.keys(historyMap).forEach(k => {
    if (historyMap[k] && historyMap[k].recorded) {
      if (!earliestDateKey || k < earliestDateKey) {
        earliestDateKey = k;
      }
    }
  });

  if (earliestDateKey) {
    const curDate = new Date(earliestDateKey + 'T00:00:00');
    const endDate = new Date(todayKey + 'T00:00:00');
    while (curDate <= endDate) {
      const k = `${curDate.getFullYear()}-${String(curDate.getMonth() + 1).padStart(2, '0')}-${String(curDate.getDate()).padStart(2, '0')}`;
      if (!historyMap[k]) {
        historyMap[k] = { count: 0, offSec: 0, recorded: true, status: 'ON' };
      }
      curDate.setDate(curDate.getDate() + 1);
    }
  }

  cachedDailyStats = Object.assign({}, historyMap);
  try { localStorage.setItem('lightwidget_daily_stats', JSON.stringify(cachedDailyStats)); } catch (e) { }

  let totalDaysWithOutages = 0;
  let lastMonthLabelCol = -4;

  for (let w = 0; w < numWeeks; w++) {
    const weekStartOffset = (numWeeks - 1 - w) * 7 + currentDayOfWeek;
    const weekStartDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() - weekStartOffset);
    const mIdx = weekStartDate.getMonth();
    const monthName = ruMonths[mIdx];

    if (monthsRow && (w === 0 || (w - lastMonthLabelCol >= 3 && weekStartDate.getDate() <= 7))) {
      const mSpan = document.createElement('span');
      mSpan.className = 'gh-month-label';
      mSpan.style.gridColumn = `${w + 1}`;
      mSpan.textContent = monthName;
      monthsRow.appendChild(mSpan);
      lastMonthLabelCol = w;
    }

    for (let d = 0; d < 7; d++) {
      const dayIndex = w * 7 + d;
      const daysFromToday = dayIndex - (numWeeks * 7 - 1 - (6 - currentDayOfWeek));
      const targetDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() + daysFromToday);
      const isFuture = daysFromToday > 0;
      const isToday = daysFromToday === 0;

      const dateKey = `${targetDate.getFullYear()}-${String(targetDate.getMonth() + 1).padStart(2, '0')}-${String(targetDate.getDate()).padStart(2, '0')}`;
      const dateFormatted = `${targetDate.getDate()} ${ruMonths[targetDate.getMonth()]}`;

      const cell = document.createElement('div');
      cell.className = 'gh-cell';

      if (isFuture) {
        cell.style.opacity = '0';
        cell.style.pointerEvents = 'none';
      } else {
        const hist = historyMap[dateKey];
        let lvl = 'gh-lvl-empty';
        let tip = `${dateFormatted}: Нет зафиксированных данных`;

        if (isToday) {
          if (hist && hist.offSec > 0) {
            totalDaysWithOutages++;
            const offHours = Math.round((hist.offSec / 3600) * 10) / 10;
            lvl = hist.offSec > 4 * 3600 ? 'gh-lvl-red' : 'gh-lvl-amber';
            tip = `${dateFormatted} (Сегодня): Отключение ~${offHours}ч`;
          } else {
            lvl = 'gh-lvl-green';
            tip = `${dateFormatted} (Сегодня): Свет есть • Сеть активна`;
          }
        } else if (hist && hist.recorded) {
          const offSec = hist.offSec || 0;
          const offHours = Math.round((offSec / 3600) * 10) / 10;
          if (offSec > 4 * 3600) {
            totalDaysWithOutages++;
            lvl = 'gh-lvl-red';
            tip = `${dateFormatted}: Без света ${offHours}ч (Длительное отключение)`;
          } else if (offSec > 0) {
            totalDaysWithOutages++;
            lvl = 'gh-lvl-amber';
            tip = `${dateFormatted}: Без света ${offHours}ч (Плановые работы)`;
          } else {
            lvl = 'gh-lvl-green';
            tip = `${dateFormatted}: Свет был весь день (100%)`;
          }
        }

        cell.classList.add(lvl);
        cell.setAttribute('title', tip);
      }

      grid.appendChild(cell);
    }
  }

  if (badge) {
    if (totalDaysWithOutages === 0) {
      badge.textContent = '100% стабильно';
      badge.className = 'heatmap-summary-badge';
    } else {
      badge.textContent = `${totalDaysWithOutages} дн. с отключениями`;
      badge.className = 'heatmap-summary-badge warning';
    }
  }
}

function setupWidgetModeListeners() {
  if (btnSwitchToWidgetMode) {
    btnSwitchToWidgetMode.addEventListener('click', (e) => {
      e.stopPropagation();
      enterWidgetMode();
    });
  }
  if (btnExpandWidget) {
    btnExpandWidget.addEventListener('click', (e) => {
      e.stopPropagation();
      exitWidgetMode();
    });
  }
}

function enterWidgetMode() {
  document.body.classList.add('widget-mode');
  if (appContainer) appContainer.style.display = 'none';
  if (desktopWidgetView) desktopWidgetView.style.display = 'flex';
  if (window.pywebview?.api?.set_widget_mode) {
    window.pywebview.api.set_widget_mode(true);
  }
}

function exitWidgetMode() {
  document.body.classList.remove('widget-mode');
  if (desktopWidgetView) desktopWidgetView.style.display = 'none';
  if (appContainer) appContainer.style.display = 'flex';
  if (window.pywebview?.api?.set_widget_mode) {
    window.pywebview.api.set_widget_mode(false);
  }
}

let appSettings = {
  theme: localStorage.getItem('lightwidget_theme') || 'midnight',
  accent: localStorage.getItem('lightwidget_accent') || 'blue',
  showSeconds: localStorage.getItem('lightwidget_show_seconds') !== 'false',
  showPulse: localStorage.getItem('lightwidget_show_pulse') !== 'false',
  showStats: localStorage.getItem('lightwidget_show_stats') !== 'false',
  showHeatmap: localStorage.getItem('lightwidget_show_heatmap') !== 'false',
  sound: localStorage.getItem('lightwidget_sound') !== 'false',
  banner: localStorage.getItem('lightwidget_banner') !== 'false',
  navPosition: localStorage.getItem('lightwidget_nav_pos') || 'top',
  navHover: localStorage.getItem('lightwidget_nav_hover') === 'true',
  tabHoverInfo: localStorage.getItem('lightwidget_tab_hover_info') !== 'false',
  toastPosition: localStorage.getItem('lightwidget_toast_pos') || 'bottom-right',
  soundName: localStorage.getItem('lightwidget_sound_name') || 'Submarine',
};
window.appSettings = appSettings;

const themeDefaultAccent = {
  cyber: 'purple',
  sapphire: 'cyan',
  emerald: 'green',
  amber: 'amber',
  titanium: 'gold',
  light: 'white'
};

function applyTheme(themeName, save = true) {
  if (!themeName) return;
  appSettings.theme = themeName;
  document.body.setAttribute('data-theme', themeName);
  document.documentElement.setAttribute('data-theme', themeName);
  document.querySelectorAll('.theme-card').forEach(card => {
    if (card.getAttribute('data-theme') === themeName) {
      card.classList.add('active');
    } else {
      card.classList.remove('active');
    }
  });

  const accentGroup = document.getElementById('accentSettingsGroup');
  let effectiveAccent = appSettings.accent;
  if (accentGroup) {
    if (themeName === 'midnight' || themeName === 'oled') {
      accentGroup.classList.remove('is-hidden');
      effectiveAccent = localStorage.getItem('lightwidget_accent') || 'blue';
      applyAccent(effectiveAccent, false);
    } else {
      accentGroup.classList.add('is-hidden');
      effectiveAccent = themeDefaultAccent[themeName] || 'blue';
      applyAccent(effectiveAccent, false);
    }
  }

  localStorage.setItem('lightwidget_theme', themeName);
  if (save && window.pywebview?.api?.save_config) {
    window.pywebview.api.save_config({
      appearance: {
        theme: themeName,
        accent: effectiveAccent
      }
    });
  }
}

function applyAccent(accentName, save = true) {
  if (!accentName) return;
  appSettings.accent = accentName;
  document.body.setAttribute('data-accent', accentName);
  document.documentElement.setAttribute('data-accent', accentName);
  document.querySelectorAll('.accent-swatch').forEach(swatch => {
    if (swatch.getAttribute('data-accent') === accentName) {
      swatch.classList.add('active');
    } else {
      swatch.classList.remove('active');
    }
  });
  if (appSettings.theme === 'midnight' || appSettings.theme === 'oled') {
    localStorage.setItem('lightwidget_accent', accentName);
  }
  if (save && window.pywebview?.api?.save_config) {
    window.pywebview.api.save_config({
      appearance: {
        theme: appSettings.theme,
        accent: accentName
      }
    });
  }
}

function applySettingsState() {
  applyTheme(appSettings.theme, false);
  applyAccent(appSettings.accent, false);

  const chkSec = document.getElementById('settingShowSeconds');
  const chkPulse = document.getElementById('settingShowPulse');
  const chkStats = document.getElementById('settingShowStats');
  const chkHeatmap = document.getElementById('settingShowHeatmap');
  const chkSound = document.getElementById('settingSound');
  const chkBanner = document.getElementById('settingBanner');

  const isSec = (appSettings.showSeconds === true || appSettings.showSeconds === 'true');
  const isPulse = (appSettings.showPulse === true || appSettings.showPulse === 'true');
  const isStats = (appSettings.showStats === true || appSettings.showStats === 'true');
  const isHeatmap = (appSettings.showHeatmap === true || appSettings.showHeatmap === 'true');
  const isSound = (appSettings.sound === true || appSettings.sound === 'true');
  const isBanner = (appSettings.banner === true || appSettings.banner === 'true');

  if (chkSec) chkSec.checked = isSec;
  if (chkPulse) chkPulse.checked = isPulse;
  if (chkStats) chkStats.checked = isStats;
  if (chkHeatmap) chkHeatmap.checked = isHeatmap;
  if (chkSound) chkSound.checked = isSound;
  if (chkBanner) chkBanner.checked = isBanner;

  const statsCard = document.getElementById('statsCard');
  const heatmapCard = document.getElementById('activityHeatmapCard');
  const bottomGrid = document.querySelector('.monitor-bottom-grid');

  if (statsCard) statsCard.style.display = isStats ? 'flex' : 'none';
  if (heatmapCard) heatmapCard.style.display = isHeatmap ? 'flex' : 'none';

  if (bottomGrid) {
    if (!isStats && !isHeatmap) {
      bottomGrid.style.display = 'none';
    } else {
      bottomGrid.style.display = 'grid';
      if (isStats && isHeatmap) {
        bottomGrid.style.gridTemplateColumns = '1fr 1fr';
      } else {
        bottomGrid.style.gridTemplateColumns = '1fr';
      }
    }
  }

  if (elBrandStatusDot) {
    if (!isPulse) {
      elBrandStatusDot.style.animation = 'none';
      elBrandStatusDot.style.boxShadow = 'none';
    } else {
      elBrandStatusDot.style.animation = '';
      elBrandStatusDot.style.boxShadow = '';
    }
  }

  if (appContainer) {
    appContainer.classList.remove('nav-pos-left', 'nav-pos-right', 'nav-pos-top');
    appContainer.classList.add(`nav-pos-${appSettings.navPosition}`);
    appContainer.classList.toggle('nav-hover', appSettings.navHover);
    appContainer.classList.toggle('tab-hover-info', appSettings.tabHoverInfo !== false);
    appContainer.classList.toggle('tab-labels-always', appSettings.tabHoverInfo === false);
  }
  document.querySelectorAll('.nav-pos-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-pos') === appSettings.navPosition);
  });
  const navHoverChk = document.getElementById('settingNavHover');
  if (navHoverChk) navHoverChk.checked = appSettings.navHover;
  const tabHoverChk = document.getElementById('settingTabHoverInfo');
  if (tabHoverChk) tabHoverChk.checked = appSettings.tabHoverInfo !== false;
  const soundNameSelect = document.getElementById('settingSoundName');
  if (soundNameSelect) soundNameSelect.value = appSettings.soundName;
  const toastPosSelect = document.getElementById('settingToastPos');
  if (toastPosSelect) toastPosSelect.value = appSettings.toastPosition;
}

window.applyTheme = applyTheme;
window.applyAccent = applyAccent;
window.applySettingsState = applySettingsState;

function setupSettings() {
  applySettingsState();

  document.querySelectorAll('.theme-card').forEach(card => {
    card.addEventListener('click', () => {
      const theme = card.getAttribute('data-theme');
      applyTheme(theme, true);
      showToast(`Тема: ${card.querySelector('.theme-title')?.textContent || theme}`);
    });
  });

  document.querySelectorAll('.accent-swatch').forEach(swatch => {
    swatch.addEventListener('click', () => {
      const accent = swatch.getAttribute('data-accent');
      applyAccent(accent, true);
      showToast(`Цвет обновлен!`);
    });
  });

  const chkSec = document.getElementById('settingShowSeconds');
  if (chkSec) {
    chkSec.addEventListener('change', () => {
      appSettings.showSeconds = chkSec.checked;
      localStorage.setItem('lightwidget_show_seconds', chkSec.checked);
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ appearance: { show_seconds: chkSec.checked } });
      }
    });
  }

  const chkStats = document.getElementById('settingShowStats');
  if (chkStats) {
    chkStats.addEventListener('change', () => {
      appSettings.showStats = chkStats.checked;
      localStorage.setItem('lightwidget_show_stats', chkStats.checked);
      applySettingsState();
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ appearance: { show_stats: chkStats.checked } });
      }
    });
  }

  const chkHeatmap = document.getElementById('settingShowHeatmap');
  if (chkHeatmap) {
    chkHeatmap.addEventListener('change', () => {
      appSettings.showHeatmap = chkHeatmap.checked;
      localStorage.setItem('lightwidget_show_heatmap', chkHeatmap.checked);
      applySettingsState();
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ appearance: { show_heatmap: chkHeatmap.checked } });
      }
    });
  }

  const chkPulse = document.getElementById('settingShowPulse');
  if (chkPulse) {
    chkPulse.addEventListener('change', () => {
      appSettings.showPulse = chkPulse.checked;
      localStorage.setItem('lightwidget_show_pulse', chkPulse.checked);
      applySettingsState();
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ appearance: { show_pulse: chkPulse.checked } });
      }
    });
  }

  const chkSound = document.getElementById('settingSound');
  if (chkSound) {
    chkSound.addEventListener('change', () => {
      appSettings.sound = chkSound.checked;
      localStorage.setItem('lightwidget_sound', chkSound.checked);
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ notifications: { sound: chkSound.checked, macos_sound: chkSound.checked } });
      }
    });
  }

  const chkBanner = document.getElementById('settingBanner');
  if (chkBanner) {
    chkBanner.addEventListener('change', () => {
      appSettings.banner = chkBanner.checked;
      localStorage.setItem('lightwidget_banner', chkBanner.checked);
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ notifications: { banner: chkBanner.checked, macos_banner: chkBanner.checked } });
      }
    });
  }

  document.querySelectorAll('.nav-pos-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      appSettings.navPosition = btn.getAttribute('data-pos');
      localStorage.setItem('lightwidget_nav_pos', appSettings.navPosition);
      applySettingsState();
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ appearance: { nav_position: appSettings.navPosition } });
      }
      showToast(`Панель: ${btn.querySelector('span')?.textContent || appSettings.navPosition}`);
    });
  });

  const navHoverChk = document.getElementById('settingNavHover');
  if (navHoverChk) {
    navHoverChk.addEventListener('change', () => {
      appSettings.navHover = navHoverChk.checked;
      localStorage.setItem('lightwidget_nav_hover', navHoverChk.checked);
      applySettingsState();
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ appearance: { nav_hover: navHoverChk.checked } });
      }
    });
  }

  const tabHoverChk = document.getElementById('settingTabHoverInfo');
  if (tabHoverChk) {
    tabHoverChk.addEventListener('change', () => {
      appSettings.tabHoverInfo = tabHoverChk.checked;
      localStorage.setItem('lightwidget_tab_hover_info', tabHoverChk.checked);
      applySettingsState();
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ appearance: { tab_hover_info: tabHoverChk.checked } });
      }
      showToast(tabHoverChk.checked ? 'Название вкладок: при наведении' : 'Название вкладок: всегда');
    });
  }

  const soundNameSelect = document.getElementById('settingSoundName');
  const btnPreviewSound = document.getElementById('btnPreviewSound');
  if (soundNameSelect) {
    soundNameSelect.addEventListener('change', () => {
      appSettings.soundName = soundNameSelect.value;
      localStorage.setItem('lightwidget_sound_name', appSettings.soundName);
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ notifications: { sound_name: appSettings.soundName } });
      }
    });
  }
  if (btnPreviewSound) {
    btnPreviewSound.addEventListener('click', () => {
      const soundName = (soundNameSelect && soundNameSelect.value) || appSettings.soundName || 'Glass';
      if (window.pywebview?.api?.play_sound) {
        window.pywebview.api.play_sound(soundName);
      } else {
        showToast('Прослушивание доступно только в приложении');
      }
    });
  }

  const toastPosSelect = document.getElementById('settingToastPos');
  if (toastPosSelect) {
    toastPosSelect.addEventListener('change', () => {
      appSettings.toastPosition = toastPosSelect.value;
      localStorage.setItem('lightwidget_toast_pos', appSettings.toastPosition);
      applySettingsState();
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({ appearance: { toast_position: appSettings.toastPosition } });
      }
      showToast('Позиция уведомлений обновлена');
    });
  }

  const btnReset = document.getElementById('btnResetSettings');
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      appSettings.theme = 'midnight';
      appSettings.accent = 'blue';
      appSettings.showSeconds = true;
      appSettings.showPulse = true;
      appSettings.showStats = true;
      appSettings.showHeatmap = true;
      appSettings.sound = true;
      appSettings.banner = true;
      appSettings.navPosition = 'top';
      appSettings.navHover = false;
      appSettings.tabHoverInfo = true;
      appSettings.toastPosition = 'bottom-right';
      appSettings.soundName = 'Submarine';
      localStorage.removeItem('lightwidget_theme');
      localStorage.removeItem('lightwidget_accent');
      localStorage.removeItem('lightwidget_show_seconds');
      localStorage.removeItem('lightwidget_show_pulse');
      localStorage.removeItem('lightwidget_show_stats');
      localStorage.removeItem('lightwidget_show_heatmap');
      localStorage.removeItem('lightwidget_sound');
      localStorage.removeItem('lightwidget_banner');
      localStorage.removeItem('lightwidget_nav_pos');
      localStorage.removeItem('lightwidget_nav_hover');
      localStorage.removeItem('lightwidget_tab_hover_info');
      localStorage.removeItem('lightwidget_sound_name');
      localStorage.removeItem('lightwidget_toast_pos');
      localStorage.removeItem('lightwidget_autocheck_updates');
      if (updateAutoCheckSwitch) updateAutoCheckSwitch.checked = true;
      applySettingsState();
      if (window.pywebview?.api?.save_config) {
        window.pywebview.api.save_config({
          appearance: {
            theme: 'midnight',
            accent: 'blue',
            show_seconds: true,
            show_pulse: true,
            show_stats: true,
            show_heatmap: true,
            nav_position: 'top',
            nav_hover: false,
            tab_hover_info: true,
            toast_position: 'bottom-right',
            autocheck_updates: true
          },
          notifications: {
            sound: true,
            banner: true,
            macos_sound: true,
            macos_banner: true,
            sound_name: 'Submarine'
          }
        });
      }
      showToast('Настройки сброшены по умолчанию');
    });
  }

  if (btnClearSimInput) {
    btnClearSimInput.addEventListener('click', () => {
      if (simMessageInput) simMessageInput.value = '';
      if (simStatusBanner) simStatusBanner.style.display = 'none';
    });
  }
}

function autoSizeAccountInput() {
  if (!elInputAccountNumber) return;
  const len = Math.max(8, (elInputAccountNumber.value || '').length);
  elInputAccountNumber.style.width = `${len + 2}ch`;
}

function setupEventListeners() {
  if (btnToggleAddress) {
    btnToggleAddress.addEventListener('click', () => {
      isAddressRevealed = !isAddressRevealed;
      updateAddressDisplay();
    });
  }

  let isAccountRevealed = false;
  if (elBtnToggleAccount && elInputAccountNumber) {
    elBtnToggleAccount.addEventListener('click', () => {
      isAccountRevealed = !isAccountRevealed;
      if (isAccountRevealed) {
        elInputAccountNumber.classList.remove('masked');
      } else {
        elInputAccountNumber.classList.add('masked');
      }
      if (elAccountToggleText) {
        elAccountToggleText.textContent = isAccountRevealed ? 'Скрыть' : 'Показать';
      }
    });
  }

  const saveAccount = async () => {
    if (!elInputAccountNumber) return;
    isAccountEditing = false;
    elInputAccountNumber.readOnly = true;
    elInputAccountNumber.classList.remove('editing');
    if (!isAccountRevealed) {
      elInputAccountNumber.classList.add('masked');
    }
    if (elAccountEditText) elAccountEditText.textContent = 'Редактировать';
    const val = elInputAccountNumber.value.trim();
    if (window.pywebview?.api?.save_account_number) {
      await window.pywebview.api.save_account_number(val);
    }
    autoSizeAccountInput();
    showToast('Счет сохранен!');
  };

  if (elBtnEditAccount && elInputAccountNumber) {
    elBtnEditAccount.addEventListener('click', async () => {
      if (!isAccountEditing) {
        isAccountEditing = true;
        elInputAccountNumber.readOnly = false;
        elInputAccountNumber.classList.add('editing');
        elInputAccountNumber.classList.remove('masked');
        if (elAccountEditText) elAccountEditText.textContent = 'Применить';
        elInputAccountNumber.focus();
        elInputAccountNumber.select();
      } else {
        await saveAccount();
      }
    });

    elInputAccountNumber.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter' && isAccountEditing) {
        await saveAccount();
      }
    });

    elInputAccountNumber.addEventListener('blur', async () => {
      if (isAccountEditing) {
        await saveAccount();
      }
    });
  }

  if (elInputAccountNumber) {

    elInputAccountNumber.addEventListener('click', () => {
      if (isAccountEditing) return;
      const val = elInputAccountNumber.value.trim();
      if (!val) {
        showToast('Счет не указан. Нажмите "Редактировать".');
        return;
      }
      navigator.clipboard.writeText(val);
      showToast('Счет дома скопирован');
      elInputAccountNumber.classList.add('copy-flash');
      setTimeout(() => elInputAccountNumber.classList.remove('copy-flash'), 2000);
    });

    elInputAccountNumber.addEventListener('input', () => {
      autoSizeAccountInput();
    });

    elInputAccountNumber.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        await saveAccount();
      }
    });
  }

  async function checkConnectionNow(hintOnline) {
    if (typeof hintOnline === 'boolean' && !hintOnline) {
      updateNetworkConnectivityUI(false);
      return;
    }
    if (window.pywebview?.api?.check_network) {
      try {
        const res = await window.pywebview.api.check_network();
        updateNetworkConnectivityUI(res && res.online !== false);
        return;
      } catch (e) { }
    }
    if (typeof navigator.onLine === 'boolean') {
      updateNetworkConnectivityUI(navigator.onLine);
    }
  }

  window.onNetworkStatusChanged = function (online) {
    updateNetworkConnectivityUI(online);
  };

  window.addEventListener('online', () => checkConnectionNow(true));
  window.addEventListener('offline', () => updateNetworkConnectivityUI(false));
  setInterval(() => checkConnectionNow(), 5000);
  checkConnectionNow();

  if (btnRefreshStatus) {
    btnRefreshStatus.addEventListener('click', async () => {
      if (!isNetworkOnline) {
        showToast('Нету подключения к интернету');
        return;
      }
      if (isRefreshCooldown || btnRefreshStatus.classList.contains('is-refreshing')) {
        showToast('Подождите несколько секунд перед повторным обновлением');
        return;
      }
      btnRefreshStatus.classList.add('is-refreshing');

      try {
        if (window.pywebview?.api) {
          let res = null;
          if (window.pywebview.api.sync_history) {
            res = await window.pywebview.api.sync_history();
          }
          const state = await window.pywebview.api.get_state();
          renderState(state);
          await loadHistory();
          if (res && res.success === false) {
            showToast('Не удалось обновить статус');
          } else {
            localStorage.setItem('lightwidget_last_sync_time', String(Date.now()));
            showToast('Синхронизировано');
          }
        }
      } catch (err) {
        console.error('Sync error:', err);
        showToast('Не удалось обновить статус');
      } finally {
        btnRefreshStatus.classList.remove('is-refreshing');
        isRefreshCooldown = true;
        btnRefreshStatus.classList.add('is-cooldown');
        btnRefreshStatus.disabled = true;
        setTimeout(() => {
          isRefreshCooldown = false;
          btnRefreshStatus.classList.remove('is-cooldown');
          if (isNetworkOnline) {
            btnRefreshStatus.disabled = false;
          }
        }, 5000);
      }
    });
  }

  const btnClearHistory = document.getElementById('btnClearHistory');
  if (btnClearHistory) {
    btnClearHistory.addEventListener('click', async () => {
      if (window.pywebview?.api?.clear_history) {
        await window.pywebview.api.clear_history();
      }
      try {
        localStorage.removeItem('lightwidget_daily_stats');
      } catch (e) { }
      cachedDailyStats = {};
      loadHistory();
      renderHeatmap([], {});
      showToast('История и статистика очищены');
    });
  }

  if (btnOpenSimulator) {
    btnOpenSimulator.addEventListener('click', () => {
      const tabSim = document.querySelector('[data-tab="simulator"]');
      if (tabSim) tabSim.click();
    });
  }

  if (btnApplySimMessage) {
    btnApplySimMessage.addEventListener('click', async () => {
      const text = simMessageInput.value.trim();
      if (!text) {
        showToast('Введите текст сообщения');
        if (simStatusBanner) simStatusBanner.style.display = 'none';
        return;
      }
      if (window.pywebview?.api) {
        const res = await window.pywebview.api.parse_and_apply(text);
        if (res) {
          renderState(res);
          if (simStatusBanner) {
            simStatusBanner.style.display = 'inline-flex';
            if (simStatusText) {
              if (res.status === 'OFF') {
                simStatusText.textContent = 'Применено! Статус: Свет отключен';
              } else if (res.is_planned) {
                const count = Array.isArray(res.planned_outages) ? res.planned_outages.length : 1;
                simStatusText.textContent = `Применено! Запланировано отключений: ${count}`;
              } else {
                simStatusText.textContent = 'Применено! Статус: Свет есть';
              }
            }
          }
          showToast('Применено!');
        }
      }
    });
  }

  if (simMessageInput) {
    simMessageInput.addEventListener('input', () => {
      if (simStatusBanner) simStatusBanner.style.display = 'none';
    });
  }

  if (btnCopyEndpoint && localApiEndpoint) {
    btnCopyEndpoint.addEventListener('click', () => {
      navigator.clipboard.writeText(localApiEndpoint.textContent);
      showToast('URL скопирован в буфер обмена!');
    });
  }

  if (btnCopyScriptableCode) {
    btnCopyScriptableCode.addEventListener('click', () => {
      navigator.clipboard.writeText(scriptableCodeArea.value);
      showToast('Код виджета скопирован!');
    });
  }

  if (btnSaveAndConnectTg) {
    btnSaveAndConnectTg.addEventListener('click', async () => {
      const cfg = {
        telegram: {
          api_id: tgApiId.value.trim(),
          api_hash: tgApiHash.value.trim(),
          phone: tgPhone.value.trim(),
          bot_username: tgBotUsername.value.trim(),
          filter_address: tgFilterAddress.value.trim()
        }
      };
      if (window.pywebview?.api) {
        await window.pywebview.api.save_config(cfg);
        const res = await window.pywebview.api.connect_telegram();
        showToast('Настройки сохранены. Подключение...');
      }
    });
  }

  if (btnDisconnectTg) {
    btnDisconnectTg.addEventListener('click', async () => {
      if (window.pywebview?.api) {
        await window.pywebview.api.disconnect_telegram();
        showToast('Telegram отключен');
      }
    });
  }

  async function handleCodeSubmit() {
    const code = tgCodeInput.value.trim();
    if (!code) {
      showToast('Введите код подтверждения');
      return;
    }
    if (btnSubmitCode) {
      btnSubmitCode.disabled = true;
      btnSubmitCode.textContent = 'Проверка...';
    }
    try {
      if (window.pywebview?.api) {
        const res = await window.pywebview.api.submit_tg_code(code);
        if (res?.success) {
          showToast('Авторизация успешна!');
          tgCodeInput.value = '';
          authCodePrompt.style.display = 'none';
          authPassPrompt.style.display = 'none';
        } else if (res?.requires_password) {
          showToast('Требуется 2FA пароль');
          authCodePrompt.style.display = 'none';
          authPassPrompt.style.display = 'block';
          if (tgPassInput) tgPassInput.focus();
        } else {
          showToast(`Ошибка: ${res?.error || 'Неверный код'}`);
        }
      }
    } catch (err) {
      showToast(`Ошибка: ${err?.message || err}`);
    } finally {
      if (btnSubmitCode) {
        btnSubmitCode.disabled = false;
        btnSubmitCode.textContent = 'Подтвердить код';
      }
    }
  }

  async function handlePassSubmit() {
    const pass = tgPassInput.value;
    if (!pass) {
      showToast('Введите пароль 2FA');
      return;
    }
    if (btnSubmitPass) {
      btnSubmitPass.disabled = true;
      btnSubmitPass.textContent = 'Вход...';
    }
    try {
      if (window.pywebview?.api) {
        const res = await window.pywebview.api.submit_tg_password(pass);
        if (res?.success) {
          showToast('2FA авторизация успешна!');
          tgPassInput.value = '';
          authPassPrompt.style.display = 'none';
          authCodePrompt.style.display = 'none';
        } else {
          showToast(`Ошибка: ${res?.error || 'Неверный пароль'}`);
        }
      }
    } catch (err) {
      showToast(`Ошибка: ${err?.message || err}`);
    } finally {
      if (btnSubmitPass) {
        btnSubmitPass.disabled = false;
        btnSubmitPass.textContent = 'Войти';
      }
    }
  }

  if (btnSubmitCode) {
    btnSubmitCode.addEventListener('click', handleCodeSubmit);
  }
  if (tgCodeInput) {
    tgCodeInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleCodeSubmit();
      }
    });
  }

  if (btnSubmitPass) {
    btnSubmitPass.addEventListener('click', handlePassSubmit);
  }
  if (tgPassInput) {
    tgPassInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handlePassSubmit();
      }
    });
  }

  if (btnMinimize) {
    btnMinimize.addEventListener('click', (e) => {
      e.stopPropagation();
      if (window.pywebview?.api?.minimize) {
        window.pywebview.api.minimize();
      }
    });
  }

  if (btnClose) {
    btnClose.addEventListener('click', (e) => {
      e.stopPropagation();
      if (window.pywebview?.api?.close) {
        window.pywebview.api.close();
      }
    });
  }

  if (elPlannedOutageSection) {
    elPlannedOutageSection.addEventListener('contextmenu', (e) => {
      const plannedList = getPlannedOutagesList(currentState);
      if (!plannedList || plannedList.length === 0) return;
      e.preventDefault();
      const rowEl = e.target.closest('.planned-item-row');
      let targetItem = null;
      if (rowEl && rowEl.dataset.idx !== undefined) {
        const idx = parseInt(rowEl.dataset.idx, 10);
        if (!isNaN(idx) && plannedList[idx]) {
          targetItem = plannedList[idx];
        }
      }
      if (!targetItem && plannedList.length > 0) {
        targetItem = plannedList[0];
      }
      if (targetItem) {
        showPlannedContextMenu(e, targetItem);
      }
    });
  }

  if (elWidgetPlannedAlert) {
    elWidgetPlannedAlert.addEventListener('contextmenu', (e) => {
      const plannedList = getPlannedOutagesList(currentState);
      if (!plannedList || plannedList.length === 0) return;
      e.preventDefault();
      showPlannedContextMenu(e, plannedList[0]);
    });
  }

  if (btnDeletePlannedItem) {
    btnDeletePlannedItem.addEventListener('click', async () => {
      const target = plannedContextMenuTarget;
      hidePlannedContextMenu();
      if (!target) return;

      try {
        if (window.pywebview?.api?.delete_planned_outage) {
          const updatedState = await window.pywebview.api.delete_planned_outage(target.start_timestamp, target.end_timestamp || null);
          if (updatedState && typeof updatedState === 'object') {
            renderState(updatedState);
            updatePlannedOutagesDisplay(true);
            showToast('Плановое отключение удалено');
            return;
          }
        }
      } catch (err) {
        console.error('Delete planned outage error:', err);
      }

      if (currentState && Array.isArray(currentState.planned_outages)) {
        currentState.planned_outages = currentState.planned_outages.filter(it => {
          const sMatch = it.start_timestamp === target.start_timestamp;
          const eMatch = target.end_timestamp === undefined || target.end_timestamp === null || it.end_timestamp === target.end_timestamp;
          return !(sMatch && eMatch);
        });
        if (currentState.planned_outages.length > 0) {
          const nextPo = currentState.planned_outages[0];
          currentState.is_planned = true;
          currentState.start_timestamp = nextPo.start_timestamp;
          currentState.end_timestamp = nextPo.end_timestamp;
          currentState.start_time_str = nextPo.start_time_str;
          currentState.end_time_str = nextPo.end_time_str;
        } else {
          currentState.is_planned = false;
          currentState.start_timestamp = null;
          currentState.end_timestamp = null;
          currentState.start_time_str = null;
          currentState.end_time_str = null;
        }
        renderState(currentState);
        updatePlannedOutagesDisplay(true);
        showToast('Плановое отключение удалено');
      }
    });
  }

  window.addEventListener('click', (e) => {
    if (plannedContextMenu && plannedContextMenu.style.display !== 'none') {
      if (!plannedContextMenu.contains(e.target)) {
        hidePlannedContextMenu();
      }
    }
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      hidePlannedContextMenu();
    }
  });

  window.addEventListener('scroll', () => {
    hidePlannedContextMenu();
  }, true);
}

function hidePlannedContextMenu() {
  if (plannedContextMenu) {
    plannedContextMenu.style.display = 'none';
  }
  plannedContextMenuTarget = null;
}

function showPlannedContextMenu(e, item) {
  if (!plannedContextMenu) return;
  plannedContextMenuTarget = item;
  plannedContextMenu.style.display = 'block';

  const menuWidth = plannedContextMenu.offsetWidth || 140;
  const menuHeight = plannedContextMenu.offsetHeight || 40;
  let x = e.clientX;
  let y = e.clientY;

  if (x + menuWidth > window.innerWidth) {
    x = Math.max(10, window.innerWidth - menuWidth - 10);
  }
  if (y + menuHeight > window.innerHeight) {
    y = Math.max(10, window.innerHeight - menuHeight - 10);
  }

  plannedContextMenu.style.left = `${x}px`;
  plannedContextMenu.style.top = `${y}px`;
}

async function loadHistory() {
  if (!window.pywebview?.api) return;
  try {
    const history = window.pywebview.api.get_history ? await window.pywebview.api.get_history() : [];
    const dailyStats = window.pywebview.api.get_daily_stats ? await window.pywebview.api.get_daily_stats() : {};
    if (dailyStats && typeof dailyStats === 'object') {
      Object.assign(cachedDailyStats, dailyStats);
      try { localStorage.setItem('lightwidget_daily_stats', JSON.stringify(cachedDailyStats)); } catch (e) { }
    }
    if (Array.isArray(history)) {
      cachedHistory = history;
      try { localStorage.setItem('lightwidget_history', JSON.stringify(history)); } catch (e) { }
      updateNetworkStats(history);
    }
    if (!history || history.length === 0) {
      if (historyList) historyList.innerHTML = '<div class="history-empty">История отключений пока пуста.</div>';
      return;
    }

    if (historyList) {
      historyList.innerHTML = '';
      history.forEach(item => {
        const isOutage = item.status === 'OFF';
        const isPlanned = item.status === 'PLANNED';
        const dateObj = new Date(item.timestamp || item.updated_at);
        const isToday = dateObj.toDateString() === new Date().toDateString();
        const timeFormatted = isToday
          ? dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          : `${dateObj.toLocaleDateString([], { day: 'numeric', month: 'short' })}, ${dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

        const badgeClass = isOutage ? 'off' : (isPlanned ? 'warn' : 'on');
        const badgeText = isOutage ? 'ОТКЛЮЧЕНИЕ' : (isPlanned ? 'ПЛАНОВЫЕ' : 'СВЕТ ВКЛЮЧЕН');
        let subText = 'Электросеть работает в штатном режиме';
        if (isOutage) {
          subText = `${item.reason || 'Отключение электроэнергии'}${item.end_time_str ? ` • До: ${item.end_time_str}` : ''}`;
        } else if (isPlanned) {
          subText = `${item.reason || 'Запланированы ремонтные работы'}${item.start_time_str ? ` • С: ${item.start_time_str}` : ''}${item.end_time_str ? ` • До: ${item.end_time_str}` : ''}`;
        }

        const div = document.createElement('div');
        div.className = 'history-item';
        div.innerHTML = `
          <div class="history-item-left">
            <span class="history-badge ${badgeClass}">${badgeText}</span>
            <div class="history-details">
              <span class="history-title">${item.address || 'Адрес не указан'}</span>
              <span class="history-sub">${subText}</span>
            </div>
          </div>
          <div class="history-item-right">
            <span class="history-time">${timeFormatted}</span>
            <button class="history-delete-btn" type="button" title="Удалить запись">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        `;

        const recordKey = item.timestamp || item.updated_at;
        const deleteBtn = div.querySelector('.history-delete-btn');
        if (deleteBtn) {
          deleteBtn.addEventListener('click', async () => {
            div.classList.add('history-item-leaving');
            await new Promise(r => setTimeout(r, 260));
            let ok = true;
            try {
              if (window.pywebview?.api?.delete_history_record) {
                ok = await window.pywebview.api.delete_history_record(recordKey) !== false;
              }
            } catch (err) {
              console.error('delete_history_record error:', err);
              ok = false;
            }
            if (!ok) {
              div.classList.remove('history-item-leaving');
              showToast('Не удалось удалить запись');
              return;
            }
            cachedHistory = cachedHistory.filter(h => (h.timestamp || h.updated_at) !== recordKey);
            try { localStorage.setItem('lightwidget_history', JSON.stringify(cachedHistory)); } catch (e) { }
            try {
              if (window.pywebview?.api?.get_daily_stats) {
                const ds = await window.pywebview.api.get_daily_stats();
                if (ds && typeof ds === 'object') {
                  cachedDailyStats = Object.assign({}, ds);
                  try { localStorage.setItem('lightwidget_daily_stats', JSON.stringify(cachedDailyStats)); } catch (e2) { }
                }
              }
            } catch (e3) { }
            div.remove();
            updateNetworkStats(cachedHistory);
            if (historyList && historyList.children.length === 0) {
              historyList.innerHTML = '<div class="history-empty">История отключений пока пуста.</div>';
            }
          });
        }

        historyList.appendChild(div);
      });
    }
  } catch (err) {
    console.error('loadHistory error:', err);
  }
}

async function loadIPhoneData() {
  if (!window.pywebview?.api) return;
  try {
    const info = await window.pywebview.api.get_iphone_info();
    if (info) {
      if (localApiEndpoint) localApiEndpoint.textContent = info.endpoint || '';
      if (scriptableCodeArea) scriptableCodeArea.value = info.scriptable_code || '';
    }
  } catch (err) {
    console.error('loadIPhoneData error:', err);
  }
}

window.onStateUpdatedFromPython = function (state) {
  if (btnRefreshStatus) btnRefreshStatus.classList.remove('is-refreshing');
  localStorage.setItem('lightwidget_last_sync_time', String(Date.now()));
  renderState(state);
  loadHistory();
};

window.onTelegramStatusChange = function (status, message) {
  tgStatusText.textContent = `Статус: ${message || status}`;
  if (status === 'CONNECTED') {
    tgStatusBanner.className = 'tg-status-banner connected';
    authCodePrompt.style.display = 'none';
    authPassPrompt.style.display = 'none';
  } else if (status === 'AUTH_CODE_REQUIRED') {
    tgStatusBanner.className = 'tg-status-banner';
    authCodePrompt.style.display = 'block';
    authPassPrompt.style.display = 'none';
  } else if (status === 'PASSWORD_REQUIRED') {
    tgStatusBanner.className = 'tg-status-banner';
    authCodePrompt.style.display = 'none';
    authPassPrompt.style.display = 'block';
  } else {
    tgStatusBanner.className = 'tg-status-banner';
  }
};

let isAppInitialized = false;

window.addEventListener('pywebviewready', () => {
  initApp();
});

function dismissSplash() {
  const splash = document.getElementById('appSplashOverlay');
  if (!splash || splash.classList.contains('is-hidden')) return;
  splash.classList.add('is-hidden');
  setTimeout(() => {
    if (splash.parentNode) {
      splash.style.display = 'none';
    }
  }, 400);
}

function waitForPywebview() {
  if (window.pywebview?.api) {
    initApp();
    return;
  }
  let attempts = 0;
  const timer = setInterval(async () => {
    attempts++;
    if (window.pywebview?.api) {
      clearInterval(timer);
      initApp();
    } else if (attempts > 150) {
      clearInterval(timer);
      console.warn('Pywebview API not found after 15s');
      dismissSplash();
    }
  }, 100);
}

async function initApp() {
  if (isAppInitialized) return;
  if (!window.pywebview?.api) return;
  isAppInitialized = true;

  try {
    const state = await window.pywebview.api.get_state();
    renderState(state);
    await loadHistory();

    const cfg = await window.pywebview.api.get_config();
    if (cfg?.telegram) {
      if (tgApiId) tgApiId.value = cfg.telegram.api_id || '';
      if (tgApiHash) tgApiHash.value = cfg.telegram.api_hash || '';
      if (tgPhone) tgPhone.value = cfg.telegram.phone || '';
      if (tgBotUsername) tgBotUsername.value = cfg.telegram.bot_username || 'dtek_odeski_elektromerezhi_bot';
      if (tgFilterAddress) tgFilterAddress.value = cfg.telegram.filter_address || '';
    }

    if (cfg?.appearance) {
      if (cfg.appearance.theme) {
        appSettings.theme = cfg.appearance.theme;
        localStorage.setItem('lightwidget_theme', appSettings.theme);
      }
      if (cfg.appearance.accent) {
        appSettings.accent = cfg.appearance.accent;
        localStorage.setItem('lightwidget_accent', appSettings.accent);
      }
      if (cfg.appearance.show_seconds !== undefined) {
        appSettings.showSeconds = cfg.appearance.show_seconds;
        localStorage.setItem('lightwidget_show_seconds', appSettings.showSeconds);
      }
      if (cfg.appearance.show_pulse !== undefined) {
        appSettings.showPulse = cfg.appearance.show_pulse;
        localStorage.setItem('lightwidget_show_pulse', appSettings.showPulse);
      }
      if (cfg.appearance.show_stats !== undefined) {
        appSettings.showStats = cfg.appearance.show_stats;
        localStorage.setItem('lightwidget_show_stats', appSettings.showStats);
      }
      if (cfg.appearance.show_heatmap !== undefined) {
        appSettings.showHeatmap = cfg.appearance.show_heatmap;
        localStorage.setItem('lightwidget_show_heatmap', appSettings.showHeatmap);
      }
      if (cfg.appearance.nav_position !== undefined) {
        appSettings.navPosition = cfg.appearance.nav_position;
        localStorage.setItem('lightwidget_nav_pos', appSettings.navPosition);
      }
      if (cfg.appearance.nav_hover !== undefined) {
        appSettings.navHover = !!cfg.appearance.nav_hover;
        localStorage.setItem('lightwidget_nav_hover', appSettings.navHover);
      }
      if (cfg.appearance.tab_hover_info !== undefined) {
        appSettings.tabHoverInfo = !!cfg.appearance.tab_hover_info;
        localStorage.setItem('lightwidget_tab_hover_info', appSettings.tabHoverInfo);
      }
      if (cfg.appearance.toast_position !== undefined) {
        appSettings.toastPosition = cfg.appearance.toast_position;
        localStorage.setItem('lightwidget_toast_pos', appSettings.toastPosition);
      }
      if (cfg.appearance.autocheck_updates !== undefined) {
        const autoCheck = !!cfg.appearance.autocheck_updates;
        localStorage.setItem('lightwidget_autocheck_updates', autoCheck ? 'true' : 'false');
        if (updateAutoCheckSwitch) updateAutoCheckSwitch.checked = autoCheck;
      }
    }
    if (cfg?.notifications) {
      if (cfg.notifications.sound !== undefined) {
        appSettings.sound = cfg.notifications.sound;
        localStorage.setItem('lightwidget_sound', appSettings.sound);
      }
      if (cfg.notifications.banner !== undefined) {
        appSettings.banner = cfg.notifications.banner;
        localStorage.setItem('lightwidget_banner', appSettings.banner);
      }
      if (cfg.notifications.sound_name !== undefined) {
        appSettings.soundName = cfg.notifications.sound_name;
        localStorage.setItem('lightwidget_sound_name', appSettings.soundName);
      }
    }
    applySettingsState();

    let accNum = '';
    try {
      accNum = await window.pywebview.api.get_account_number();
      console.log('[initApp] got account_number:', accNum);
    } catch (err) {
      console.error('[initApp] get_account_number failed:', err);
    }
    if (elInputAccountNumber) {
      elInputAccountNumber.value = accNum || '';
      autoSizeAccountInput();
      console.log('[initApp] set input value to:', elInputAccountNumber.value);
    }

    loadIPhoneData();

    if (updateAutoCheckSwitch) {
      const isAutoCheck = localStorage.getItem('lightwidget_autocheck_updates') !== 'false';
      updateAutoCheckSwitch.checked = isAutoCheck;
      updateAutoCheckSwitch.addEventListener('change', () => {
        const val = updateAutoCheckSwitch.checked;
        localStorage.setItem('lightwidget_autocheck_updates', val ? 'true' : 'false');
        if (window.pywebview?.api?.save_config) {
          window.pywebview.api.save_config({ appearance: { autocheck_updates: val } });
        }
        showToast(val ? 'Автопроверка включена' : 'Автопроверка отключена');
      });
    }

    setTimeout(() => {
      const isAutoCheck = localStorage.getItem('lightwidget_autocheck_updates') !== 'false';
      if (isAutoCheck) {
        checkAppUpdates(false, true);
      }
    }, 2000);

    let lastSyncTime = parseInt(localStorage.getItem('lightwidget_last_sync_time'), 10) || 0;
    if (state?.updated_at) {
      const stateTime = new Date(state.updated_at).getTime();
      if (!isNaN(stateTime) && stateTime > lastSyncTime) {
        lastSyncTime = stateTime;
        localStorage.setItem('lightwidget_last_sync_time', String(lastSyncTime));
      }
    }

    const isWithinCooldown = lastSyncTime > 0 && (Date.now() - lastSyncTime) >= 0 && (Date.now() - lastSyncTime) < 180000;
    if (isWithinCooldown) {
      dismissSplash();
      return;
    }

    let isOnline = true;
    try {
      if (window.pywebview?.api?.check_network) {
        const netRes = await window.pywebview.api.check_network();
        isOnline = !!(netRes && netRes.online !== false);
      } else if (typeof navigator.onLine === 'boolean') {
        isOnline = navigator.onLine;
      }
    } catch (netErr) {
      isOnline = false;
    }

    if (typeof updateNetworkConnectivityUI === 'function') {
      updateNetworkConnectivityUI(isOnline);
    }

    if (!isOnline) {
      dismissSplash();
      showToast('Не удалось обновить статус: нет интернета');
      return;
    }

    try {
      const syncPromise = window.pywebview?.api?.sync_history
        ? window.pywebview.api.sync_history()
        : Promise.resolve({ success: false });
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('timeout')), 7000)
      );

      const syncResult = await Promise.race([syncPromise, timeoutPromise]);
      if (syncResult && syncResult.success === false) {
        dismissSplash();
        showToast('Не удалось обновить статус');
      } else {
        localStorage.setItem('lightwidget_last_sync_time', String(Date.now()));
        const updatedState = await window.pywebview.api.get_state();
        renderState(updatedState);
        await loadHistory();
        dismissSplash();

        if (btnRefreshStatus) {
          isRefreshCooldown = true;
          btnRefreshStatus.classList.add('is-cooldown');
          btnRefreshStatus.disabled = true;
          setTimeout(() => {
            isRefreshCooldown = false;
            btnRefreshStatus.classList.remove('is-cooldown');
            if (isNetworkOnline) {
              btnRefreshStatus.disabled = false;
            }
          }, 5000);
        }
      }
    } catch (syncErr) {
      dismissSplash();
      showToast('Не удалось обновить статус');
    }
  } catch (e) {
    console.error('Init error:', e);
    dismissSplash();
  }
}

const updateNavDot = document.getElementById('updateNavDot');
const updateHeroCard = document.getElementById('updateHeroCard');
const updateHeroIconWrap = document.getElementById('updateHeroIconWrap');
const updateHeroIcon = document.getElementById('updateHeroIcon');
const updateStatusTitle = document.getElementById('updateStatusTitle');
const updateVersionTag = document.getElementById('updateVersionTag');
const updateStatusDesc = document.getElementById('updateStatusDesc');
const updateInstalledPill = document.getElementById('updateInstalledPill');
const updateLastCheckTime = document.getElementById('updateLastCheckTime');
const updateLastCheckSub = document.getElementById('updateLastCheckSub');

const updateCommitCard = document.getElementById('updateCommitCard');
const updateCommitHash = document.getElementById('updateCommitHash');
const updateCommitMessage = document.getElementById('updateCommitMessage');
const updateCommitAuthorName = document.getElementById('updateCommitAuthorName');
const updateCommitDateStr = document.getElementById('updateCommitDateStr');
const updateCommitLink = document.getElementById('updateCommitLink');

const updateProgressCard = document.getElementById('updateProgressCard');
const updateStageLabel = document.getElementById('updateStageLabel');
const updatePercentLabel = document.getElementById('updatePercentLabel');
const updateProgressFill = document.getElementById('updateProgressFill');
const updateProgressSub = document.getElementById('updateProgressSub');

const btnCheckUpdates = document.getElementById('btnCheckUpdates');
const btnPerformUpdate = document.getElementById('btnPerformUpdate');
const updateAutoCheckSwitch = document.getElementById('updateAutoCheckSwitch');

let isUpdating = false;

function formatCleanVersion(rawVer) {
  if (!rawVer) return '2.3.6.1';
  const clean = String(rawVer).replace(/^v/i, '').trim();
  const parts = clean.split('.').map(p => parseInt(p, 10) || 0);
  while (parts.length < 3) parts.push(0);
  return parts.join('.');
}

async function checkAppUpdates(showToastOnClean = false, isStartupCheck = false) {
  if (!window.pywebview?.api?.check_for_updates) return;

  const spinIcon = btnCheckUpdates?.querySelector('.spin-icon');
  if (spinIcon) spinIcon.classList.add('is-spinning');
  if (btnCheckUpdates) btnCheckUpdates.disabled = true;

  try {
    const res = await window.pywebview.api.check_for_updates();
    console.log('[Updater] Check response:', res);

    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    if (updateLastCheckTime) updateLastCheckTime.textContent = `Сегодня в ${timeStr}`;
    if (updateLastCheckSub) updateLastCheckSub.textContent = 'Проверка в фоновом режиме';

    if (res && res.success) {
      const localVer = formatCleanVersion(res.local?.version || '2.3.6.1');
      if (updateVersionTag) updateVersionTag.textContent = localVer;
      if (updateInstalledPill) updateInstalledPill.textContent = localVer;

      if (res.has_update && res.remote) {
        const remoteVer = formatCleanVersion(res.remote?.version || res.remote?.tag);

        if (updateNavDot) updateNavDot.style.display = 'block';
        if (updateHeroCard) updateHeroCard.classList.add('has-update');

        if (updateHeroIconWrap) {
          updateHeroIconWrap.className = 'macos-icon-badge badge-blue';
          updateHeroIconWrap.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.6">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
          `;
        }

        if (updateStatusTitle) updateStatusTitle.textContent = `Доступно обновление: LightWidget ${remoteVer}`;
        if (updateStatusDesc) updateStatusDesc.textContent = res.remote.title || `Новая версия ${remoteVer} на GitHub Releases`;

        if (updateCommitCard) updateCommitCard.style.display = 'block';
        if (updateCommitHash) updateCommitHash.textContent = remoteVer;
        if (updateCommitMessage) updateCommitMessage.textContent = res.remote.message || 'Официальный стабильный релиз LightWidget';
        if (updateCommitAuthorName) updateCommitAuthorName.textContent = 'GitHub Release';
        if (updateCommitDateStr) {
          const d = res.remote.date ? new Date(res.remote.date) : new Date();
          updateCommitDateStr.textContent = `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        }
        if (updateCommitLink && res.remote.url) {
          updateCommitLink.href = res.remote.url;
        }

        if (btnPerformUpdate) {
          btnPerformUpdate.style.display = 'inline-flex';
          btnPerformUpdate.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span>Обновить до ${remoteVer}</span>
          `;
        }
        showToast(`Доступна новая версия ${remoteVer}`);
        if (isStartupCheck && window.pywebview?.api?.notify) {
          window.pywebview.api.notify('LightWidget', 'Доступно обновление', `Доступна новая версия LightWidget ${remoteVer}`);
        }
      } else {

        if (updateNavDot) updateNavDot.style.display = 'none';
        if (updateHeroCard) updateHeroCard.classList.remove('has-update');

        if (updateHeroIconWrap) {
          updateHeroIconWrap.className = 'macos-icon-badge badge-green';
          updateHeroIconWrap.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.8">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          `;
        }

        if (updateStatusTitle) updateStatusTitle.textContent = `LightWidget ${localVer} — установлена новейшая версия`;
        if (updateStatusDesc) updateStatusDesc.textContent = `Все компоненты актуальны • Проверено сегодня в ${timeStr}`;

        if (updateCommitCard) updateCommitCard.style.display = 'none';
        if (btnPerformUpdate) btnPerformUpdate.style.display = 'none';

        if (showToastOnClean) showToast('У вас установлена последняя версия');
      }
    } else {
      if (updateStatusTitle) updateStatusTitle.textContent = 'Центр обновлений';
      if (updateStatusDesc) updateStatusDesc.textContent = res?.error || 'Не удалось проверить обновления';
      if (showToastOnClean) showToast('Не удалось связаться с GitHub');
    }
  } catch (err) {
    console.error('[Updater] check error:', err);
  } finally {
    if (spinIcon) spinIcon.classList.remove('is-spinning');
    if (btnCheckUpdates) btnCheckUpdates.disabled = false;
  }
}

async function setProgressStage(percent, stageText, subText) {
  if (updateProgressFill) updateProgressFill.style.width = `${percent}%`;
  if (updatePercentLabel) updatePercentLabel.textContent = `${Math.round(percent)}%`;
  if (stageText && updateStageLabel) updateStageLabel.textContent = stageText;
  if (subText && updateProgressSub) updateProgressSub.textContent = subText;
}

async function startUpdateProcess() {
  if (isUpdating) return;
  isUpdating = true;

  if (btnPerformUpdate) btnPerformUpdate.disabled = true;
  if (btnCheckUpdates) btnCheckUpdates.disabled = true;
  if (updateProgressCard) updateProgressCard.style.display = 'block';

  try {

    await setProgressStage(15, 'Подключение к GitHub...', 'Проверка ветки main...');
    await new Promise(r => setTimeout(r, 450));

    await setProgressStage(35, 'Загрузка обновлений (git pull)...', 'Скачивание измененных файлов...');

    let pullResult = null;
    if (window.pywebview?.api?.perform_update) {
      pullResult = await window.pywebview.api.perform_update();
    }
    await new Promise(r => setTimeout(r, 400));

    if (pullResult && pullResult.success === false) {
      await setProgressStage(100, 'Ошибка обновления', pullResult.error || 'Проверьте соединение с интернетом');
      if (updateProgressCard) updateProgressCard.style.borderColor = '#ff453a';
      showToast('Ошибка при загрузке обновления');
      isUpdating = false;
      if (btnPerformUpdate) btnPerformUpdate.disabled = false;
      if (btnCheckUpdates) btnCheckUpdates.disabled = false;
      return;
    }

    await setProgressStage(70, 'Применение изменений...', 'Обновление интерфейса и скриптов...');
    await new Promise(r => setTimeout(r, 500));

    await setProgressStage(90, 'Финализация...', 'Сборка и подготовка к запуску...');
    await new Promise(r => setTimeout(r, 450));

    await setProgressStage(100, 'Готово! Перезапуск...', 'Приложение перезапускается через мгновение...');
    showToast('Обновление завершено! Перезапуск...');
    await new Promise(r => setTimeout(r, 600));

    if (window.pywebview?.api?.restart_app) {
      await window.pywebview.api.restart_app();
    }
  } catch (err) {
    console.error('[Updater] update failed:', err);
    await setProgressStage(100, 'Ошибка обновления', String(err));
    isUpdating = false;
    if (btnPerformUpdate) btnPerformUpdate.disabled = false;
    if (btnCheckUpdates) btnCheckUpdates.disabled = false;
  }
}

if (btnCheckUpdates) {
  btnCheckUpdates.addEventListener('click', () => {
    checkAppUpdates(true);
  });
}

if (btnPerformUpdate) {
  btnPerformUpdate.addEventListener('click', () => {
    startUpdateProcess();
  });
}
