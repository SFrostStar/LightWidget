// LightWidget Renderer JS

let currentState = null;
let countdownInterval = null;
let isAccountEditing = false;

// DOM Elements
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

// Tabs
const navTabs = document.querySelectorAll('.nav-tab');
const tabPanes = document.querySelectorAll('.tab-pane');

// Simulator
const simMessageInput = document.getElementById('simMessageInput');
const btnApplySimMessage = document.getElementById('btnApplySimMessage');
const btnClearSimInput = document.getElementById('btnClearSimInput');
const btnPresetOutage = document.getElementById('btnPresetOutage');
const btnPresetRestored = document.getElementById('btnPresetRestored');
const btnPresetDelay = document.getElementById('btnPresetDelay');
const simResultBox = document.getElementById('simResultBox');
const simResultJson = document.getElementById('simResultJson');

// iPhone
const localApiEndpoint = document.getElementById('localApiEndpoint');
const btnCopyEndpoint = document.getElementById('btnCopyEndpoint');
const scriptableCodeArea = document.getElementById('scriptableCodeArea');
const btnCopyScriptableCode = document.getElementById('btnCopyScriptableCode');

// Telegram
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

// History
const historyList = document.getElementById('historyList');

// Window & Widget Controls
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

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupPresets();
  setupEventListeners();
  setupWidgetModeListeners();
  startSystemClock();
  
  // Start checking pywebview API availability
  waitForPywebview();
});

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}

// --- Tabs Management ---
function setupTabs() {
  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.getAttribute('data-tab');
      navTabs.forEach(t => t.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const pane = document.getElementById(`tab-${target}`);
      if (pane) pane.classList.add('active');

      if (target === 'history') loadHistory();
      if (target === 'iphone') loadIPhoneData();
    });
  });
}

// --- Clock & Countdown Engine ---
function startSystemClock() {
  setInterval(() => {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    elSystemClock.textContent = `${h}:${m}:${s}`;
  }, 1000);
}

function updateCountdown() {
  if (!currentState || currentState.status !== 'OFF' || !currentState.end_timestamp) {
    if (elTimerDigits) {
      elTimerDigits.innerHTML = '<span style="font-size: 30px; color: #30d158; font-weight: 800; letter-spacing: -0.5px;">СВЕТ ЕСТЬ</span>';
    }
    if (elProgressBarFill) elProgressBarFill.style.width = '100%';
    if (elProgressPercentText) elProgressPercentText.textContent = '100%';
    if (elTimerLabel) {
      elTimerLabel.textContent = 'Электросеть работает в штатном режиме';
      elTimerLabel.style.color = '#30d158';
    }

    if (elLivePill) elLivePill.className = 'live-pill';
    if (elLivePillText) elLivePillText.textContent = 'СВЕТ ЕСТЬ';
    if (elStatusBadge) elStatusBadge.className = 'status-badge';
    if (elStatusLabel) elStatusLabel.textContent = 'СВЕТ ЕСТЬ';

    if (elBrandStatusDot) elBrandStatusDot.className = 'brand-status-dot on';
    if (widgetCountdown) widgetCountdown.innerHTML = '<span style="font-size: 17px; color: #30d158; font-weight: 800; line-height: 1.1;">СВЕТ ЕСТЬ</span>';
    if (widgetStatusText) widgetStatusText.textContent = 'СВЕТ ЕСТЬ';
    if (widgetStatusBadge) widgetStatusBadge.className = 'widget-status';
    if (widgetEndTime) widgetEndTime.textContent = 'стабильно';
    if (widgetProgressFill) widgetProgressFill.style.width = '100%';

    // Hide outage rows
    if (elRowReason) elRowReason.style.display = 'none';
    if (elRowStart) elRowStart.style.display = 'none';
    if (elRowEnd) elRowEnd.style.display = 'none';
    return;
  }

  const nowTs = Math.floor(Date.now() / 1000);
  const endTs = currentState.end_timestamp;
  const startTs = currentState.start_timestamp || (endTs - 3600);

  const diff = Math.max(0, endTs - nowTs);

  if (diff === 0) {
    if (elBrandStatusDot) elBrandStatusDot.className = 'brand-status-dot on';
    const elapsedAfter = nowTs - endTs;
    if (elapsedAfter < 15) {
      const graceRemaining = 15 - elapsedAfter;
      if (elTimerDigits) {
        elTimerDigits.innerHTML = `<span style="font-size: 20px; color: #ff9f0a; font-weight: 700; text-align: center;">Таймер закончился! Свет должен быть (${graceRemaining}с)</span>`;
      }
      if (elTimerLabel) {
        elTimerLabel.textContent = 'Ориентировочное время вышло';
        elTimerLabel.style.color = '#ff9f0a';
      }

      if (elLivePill) elLivePill.className = 'live-pill off';
      if (elLivePillText) elLivePillText.textContent = 'СВЕТ ЕСТЬ';
      if (elStatusBadge) elStatusBadge.className = 'status-badge off';
      if (elStatusLabel) elStatusLabel.textContent = 'СВЕТ ДОЛЖЕН БЫТЬ';

      if (widgetCountdown) {
        widgetCountdown.innerHTML = `<span style="font-size: 13px; color: #ff9f0a; font-weight: 700; line-height: 1.2;">СВЕТ ДОЛЖЕН БЫТЬ<br>(${graceRemaining}с)</span>`;
      }
      if (widgetStatusText) widgetStatusText.textContent = 'ВРЕМЯ НАСТУПИЛО';
      if (widgetStatusBadge) widgetStatusBadge.className = 'widget-status warn';
    } else {
      if (elTimerDigits) {
        elTimerDigits.innerHTML = `<span style="font-size: 30px; color: #30d158; font-weight: 800; letter-spacing: -0.5px;">СВЕТ ЕСТЬ</span>`;
      }
      if (elTimerLabel) {
        elTimerLabel.textContent = 'Время отключения завершено • Электросеть работает';
        elTimerLabel.style.color = '#30d158';
      }

      if (elLivePill) elLivePill.className = 'live-pill';
      if (elLivePillText) elLivePillText.textContent = 'СВЕТ ЕСТЬ';
      if (elStatusBadge) elStatusBadge.className = 'status-badge';
      if (elStatusLabel) elStatusLabel.textContent = 'СВЕТ ЕСТЬ';

      if (widgetCountdown) {
        widgetCountdown.innerHTML = `<span style="font-size: 17px; color: #30d158; font-weight: 800; line-height: 1.1;">СВЕТ ЕСТЬ</span>`;
      }
      if (widgetStatusText) widgetStatusText.textContent = 'СВЕТ ЕСТЬ';
      if (widgetStatusBadge) widgetStatusBadge.className = 'widget-status';
      if (widgetEndTime) widgetEndTime.textContent = 'стабильно';

      // Hide outage details
      if (elRowReason) elRowReason.style.display = 'none';
      if (elRowStart) elRowStart.style.display = 'none';
      if (elRowEnd) elRowEnd.style.display = 'none';
    }

    if (elProgressBarFill) elProgressBarFill.style.width = '100%';
    if (elProgressPercentText) elProgressPercentText.textContent = '100%';
    if (widgetProgressFill) widgetProgressFill.style.width = '100%';
    return;
  }

  // Active Outage Countdown
  const hours = Math.floor(diff / 3600);
  const minutes = Math.floor((diff % 3600) / 60);
  const seconds = diff % 60;

  const hStr = String(hours).padStart(2, '0');
  const mStr = String(minutes).padStart(2, '0');
  const sStr = String(seconds).padStart(2, '0');

  if (elTimerDigits) {
    elTimerDigits.innerHTML = `<span id="cdHours">${hStr}</span><span class="t-colon">:</span><span id="cdMinutes">${mStr}</span><span class="t-colon">:</span><span id="cdSeconds">${sStr}</span>`;
  }
  if (elTimerLabel) {
    elTimerLabel.textContent = 'до ориентировочного включения';
    elTimerLabel.style.color = '';
  }

  if (elBrandStatusDot) elBrandStatusDot.className = 'brand-status-dot off';
  if (widgetCountdown) widgetCountdown.textContent = `${hStr}:${mStr}:${sStr}`;

  // Progress Bar
  const total = Math.max(1, endTs - startTs);
  const elapsed = Math.max(0, Math.min(total, nowTs - startTs));
  const pct = Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)));

  if (elProgressBarFill) elProgressBarFill.style.width = `${pct}%`;
  if (elProgressPercentText) elProgressPercentText.textContent = `${pct}%`;
  if (widgetProgressFill) widgetProgressFill.style.width = `${pct}%`;
}

// Address Toggle State
let isAddressRevealed = false;
const btnToggleAddress = document.getElementById('btnToggleAddress');
const addrToggleText = document.getElementById('addrToggleText');
const eyeIcon = document.getElementById('eyeIcon');

function updateAddressDisplay() {
  const fullAddress = currentState?.address || 'м. Одеса, вул. Чайки Максима, 25';
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

// --- Render State to UI ---
function renderState(state) {
  if (!state) return;
  currentState = state;

  const isOutage = state.status === 'OFF';

  if (elBrandStatusDot) {
    elBrandStatusDot.className = isOutage ? 'brand-status-dot off' : 'brand-status-dot on';
  }

  // Hero Card Classes & Badges
  if (isOutage) {
    if (elHeroCard) elHeroCard.className = 'hero-card outage';
    if (elLivePill) elLivePill.className = 'live-pill off';
    if (elLivePillText) elLivePillText.textContent = 'СВЕТ ОТКЛЮЧЕН';
    if (elStatusBadge) elStatusBadge.className = 'status-badge off';
    if (elStatusIcon) elStatusIcon.textContent = '🔌';
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
    if (elStatusIcon) elStatusIcon.textContent = '⚡';
    if (elStatusLabel) elStatusLabel.textContent = 'СВЕТ ЕСТЬ';

    if (widgetStatusBadge) widgetStatusBadge.className = 'widget-status';
    if (widgetStatusText) widgetStatusText.textContent = 'СВЕТ ЕСТЬ';
    if (widgetEndTime) widgetEndTime.textContent = 'стабильно';
  }

  // Details
  updateAddressDisplay();
  if (elRowReason) elRowReason.style.display = isOutage ? 'flex' : 'none';
  if (elRowStart) elRowStart.style.display = isOutage ? 'flex' : 'none';
  if (elRowEnd) elRowEnd.style.display = isOutage ? 'flex' : 'none';

  if (isOutage) {
    if (elDetailReason) elDetailReason.textContent = state.reason || 'Аварийно-восстановительные работы';
    if (elDetailStart) elDetailStart.innerHTML = formatWithRelativeDay(state.start_time_str);
    if (elDetailEnd) elDetailEnd.innerHTML = formatWithRelativeDay(state.end_time_str || 'Уточняется');
  }

  // Account number is loaded ONLY in initApp, not synced here

  if (state.updated_at) {
    const d = new Date(state.updated_at);
    elLastUpdatedText.textContent = `Обновлено: ${d.toLocaleTimeString()}`;
  }

  // Start or refresh countdown ticker
  if (countdownInterval) clearInterval(countdownInterval);
  updateCountdown();
  countdownInterval = setInterval(updateCountdown, 1000);
}

// --- Desktop Widget Mode Toggling ---
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

// --- Simulator Presets ---
function setupPresets() {
  if (btnPresetOutage) {
    btnPresetOutage.addEventListener('click', () => {
      const now = new Date();
      const day = String(now.getDate()).padStart(2, '0');
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const year = now.getFullYear();

      simMessageInput.value = `❗️ За адресою м. Одеса, вул. Чайки Максима, 25 зафіксовано відключення. \nПричина: Аварійні ремонтні роботи. \n🕦 Час початку: ${day}.${month}.${year} 09:34. \n🕦 Орієнтовний час відновлення електроенергії: ${day}.${month}.${year} 16:34.\n\n--------------------------------------\n❗️ За адресою м. Одеса, вул. Чайки Максима, 25 зафіксовано відключення. \nПричина: Модернізація мереж для підвищення надійності. \n🕦 Час початку: ${day}.${month}.${year} 09:35. \n🕦 Орієнтовний час відновлення електроенергії: ${day}.${month}.${year} 20:00.`;
    });
  }

  if (btnPresetRestored) {
    btnPresetRestored.addEventListener('click', () => {
      const now = new Date();
      const day = String(now.getDate()).padStart(2, '0');
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const year = now.getFullYear();
      const h = String(now.getHours()).padStart(2, '0');
      const m = String(now.getMinutes()).padStart(2, '0');

      simMessageInput.value = `✅ За адресою м. Одеса, вул. Чайки Максима, 25 електропостачання відновлено!\n🕦 Час відновлення: ${day}.${month}.${year} ${h}:${m}.`;
    });
  }

  if (btnPresetDelay) {
    btnPresetDelay.addEventListener('click', () => {
      const now = new Date();
      const day = String(now.getDate()).padStart(2, '0');
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const year = now.getFullYear();
      const endH = String((now.getHours() + 6) % 24).padStart(2, '0');

      simMessageInput.value = `⚠️ За адресою м. Одеса, вул. Чайки Максима, 25 змінено час відновлення електроенергії.\n🕦 Новий орієнтовний час відновлення електроенергії: ${day}.${month}.${year} ${endH}:30.\nПричина: Ускладнення робіт на підстанції.`;
    });
  }

  if (btnClearSimInput) {
    btnClearSimInput.addEventListener('click', () => {
      simMessageInput.value = '';
      if (simResultBox) simResultBox.style.display = 'none';
    });
  }
}

// --- Event Listeners ---
// Auto-size Account Input (module scope so initApp can use it)
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

  // Account Number Toggle (Show / Hide) via CSS class
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

  // --- Account Number: SIMPLE approach ---
  // Save ONLY on explicit "Применить" or Enter. Nothing else saves.
  const saveAccount = async () => {
    if (!elInputAccountNumber) return;
    isAccountEditing = false;
    elInputAccountNumber.readOnly = true;
    elInputAccountNumber.classList.remove('editing');
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
        if (elAccountEditText) elAccountEditText.textContent = 'Применить';
        elInputAccountNumber.focus();
        elInputAccountNumber.select();
      } else {
        await saveAccount();
      }
    });
  }

  if (elInputAccountNumber) {
    // Copy on click (when not editing)
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

    // Auto-resize while typing
    elInputAccountNumber.addEventListener('input', () => {
      autoSizeAccountInput();
    });

    // Enter = save
    elInputAccountNumber.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        await saveAccount();
      }
    });
  }

  if (btnRefreshStatus) {
    btnRefreshStatus.addEventListener('click', async () => {
      if (window.pywebview?.api) {
        if (window.pywebview.api.sync_history) {
          await window.pywebview.api.sync_history();
        }
        const state = await window.pywebview.api.get_state();
        renderState(state);
        showToast('Синхронизация и обновление...');
      }
    });
  }

  const btnClearHistory = document.getElementById('btnClearHistory');
  if (btnClearHistory) {
    btnClearHistory.addEventListener('click', async () => {
      if (window.pywebview?.api?.clear_history) {
        await window.pywebview.api.clear_history();
      }
      loadHistory();
      showToast('История очищена');
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
        return;
      }
      if (window.pywebview?.api) {
        const res = await window.pywebview.api.parse_and_apply(text);
        if (res) {
          if (simResultBox) simResultBox.style.display = 'block';
          if (simResultJson) simResultJson.textContent = JSON.stringify(res, null, 2);
          renderState(res);
          showToast('Сообщение применено!');
        }
      }
    });
  }

  // iPhone Buttons
  if (btnCopyEndpoint) {
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

  // Telegram Settings Buttons
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

  if (btnSubmitCode) {
    btnSubmitCode.addEventListener('click', async () => {
      const code = tgCodeInput.value.trim();
      if (!code) return;
      if (window.pywebview?.api) {
        const res = await window.pywebview.api.submit_tg_code(code);
        if (res?.success) {
          showToast('Авторизация успешна!');
          authCodePrompt.style.display = 'none';
          authPassPrompt.style.display = 'none';
        } else if (res?.requires_password) {
          showToast('Требуется 2FA пароль');
          authCodePrompt.style.display = 'none';
          authPassPrompt.style.display = 'block';
        } else {
          showToast(`Ошибка: ${res?.error || 'Неверный код'}`);
        }
      }
    });
  }

  if (btnSubmitPass) {
    btnSubmitPass.addEventListener('click', async () => {
      const pass = tgPassInput.value;
      if (!pass) return;
      if (window.pywebview?.api) {
        const res = await window.pywebview.api.submit_tg_password(pass);
        if (res?.success) {
          showToast('2FA авторизация успешна!');
          authPassPrompt.style.display = 'none';
          authCodePrompt.style.display = 'none';
        } else {
          showToast(`Ошибка: ${res?.error || 'Неверный пароль'}`);
        }
      }
    });
  }

  // Window Controls
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
}

// --- Load Sub-tabs Data ---
async function loadHistory() {
  if (!window.pywebview?.api) return;
  const history = await window.pywebview.api.get_history();
  if (!history || history.length === 0) {
    historyList.innerHTML = '<div class="history-empty">История отключений пока пуста.</div>';
    return;
  }

  historyList.innerHTML = '';
  history.forEach(item => {
    const isOutage = item.status === 'OFF';
    const div = document.createElement('div');
    div.className = 'history-item';
    div.innerHTML = `
      <div class="history-item-left">
        <span class="history-badge ${isOutage ? 'off' : 'on'}">${isOutage ? 'ОТКЛЮЧЕНИЕ' : 'СВЕТ ВКЛЮЧЕН'}</span>
        <div class="history-details">
          <span class="history-title">${item.address || 'Адрес не указан'}</span>
          <span class="history-sub">${item.reason || ''} ${item.end_time_str ? `• До: ${item.end_time_str}` : ''}</span>
        </div>
      </div>
      <div class="history-time">${new Date(item.timestamp || item.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
    `;
    historyList.appendChild(div);
  });
}

async function loadIPhoneData() {
  if (!window.pywebview?.api) return;
  const info = await window.pywebview.api.get_iphone_info();
  if (info) {
    localApiEndpoint.textContent = info.endpoint;
    scriptableCodeArea.value = info.scriptable_code;
  }
}

// --- Callback for Python Bridge ---
window.onStateUpdatedFromPython = function(state) {
  renderState(state);
};

window.onTelegramStatusChange = function(status, message) {
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

// --- Pywebview Initializer ---
let isAppInitialized = false;

window.addEventListener('pywebviewready', () => {
  initApp();
});

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

    const cfg = await window.pywebview.api.get_config();
    if (cfg?.telegram) {
      if (tgApiId) tgApiId.value = cfg.telegram.api_id || '';
      if (tgApiHash) tgApiHash.value = cfg.telegram.api_hash || '';
      if (tgPhone) tgPhone.value = cfg.telegram.phone || '';
      if (tgBotUsername) tgBotUsername.value = cfg.telegram.bot_username || 'dtek_odeski_elektromerezhi_bot';
      if (tgFilterAddress) tgFilterAddress.value = cfg.telegram.filter_address || 'Чайки Максима';
    }

    // Load account number - simple: just ask Python
    let accNum = '';
    try {
      accNum = await window.pywebview.api.get_account_number();
      console.log('[initApp] got account_number:', accNum);
    } catch(err) {
      console.error('[initApp] get_account_number failed:', err);
    }
    if (elInputAccountNumber) {
      elInputAccountNumber.value = accNum || '';
      autoSizeAccountInput();
      console.log('[initApp] set input value to:', elInputAccountNumber.value);
    }

    loadIPhoneData();
  } catch (e) {
    console.error('Init error:', e);
  }
}
