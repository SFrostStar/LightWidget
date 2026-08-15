// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: yellow; icon-glyph: bolt;

/**
 * LightWidget for iOS (Scriptable)
 * Мониторинг отключений света на экране твоего iPhone.
 * 
 * ИНСТРУКЦИЯ ПО УСТАНОВКЕ:
 * 1. Установи бесплатное приложение Scriptable из App Store на iPhone.
 * 2. Создай новый скрипт в Scriptable (+), вставь весь этот код.
 * 3. Укажи свой IP адрес Mac в переменной SERVER_URL ниже (например: http://192.168.1.50:8088).
 * 4. Нажми "Готово" и добавь виджет Scriptable на домашний экран!
 */

// URL ТВОЕГО ОБЛАЧНОГО СЕРВЕРА 24/7:
const SERVER_URL = "https://lightwidget.onrender.com/api/status";

// Получение данных
let data = null;
try {
  let req = new Request(SERVER_URL);
  req.timeoutInterval = 5;
  data = await req.loadJSON();
  // Кэшируем для работы оффлайн
  let fm = FileManager.local();
  let cachePath = fm.joinPath(fm.documentsDirectory(), "light_widget_cache.json");
  fm.writeString(cachePath, JSON.stringify(data));
} catch (e) {
  // Загрузка из кэша при отсутствии связи
  let fm = FileManager.local();
  let cachePath = fm.joinPath(fm.documentsDirectory(), "light_widget_cache.json");
  if (fm.fileExists(cachePath)) {
    data = JSON.parse(fm.readString(cachePath));
  } else {
    data = {
      status: "UNKNOWN",
      address: "Нет соединения с сервером",
      reason: "Проверьте IP адрес Mac в настройках",
      is_outage: false
    };
  }
}

// Создание виджета
let widget = await createWidget(data);
if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  widget.presentMedium();
}
Script.complete();

async function createWidget(info) {
  let w = new ListWidget();
  w.setPadding(14, 16, 14, 16);

  let isOutage = info.status === "OFF";

  // Градиент фона
  let gradient = new LinearGradient();
  if (isOutage) {
    gradient.colors = [new Color("#2b1111"), new Color("#160a0a")];
  } else {
    gradient.colors = [new Color("#0c2017"), new Color("#06110c")];
  }
  gradient.locations = [0.0, 1.0];
  w.backgroundGradient = gradient;

  // Шапка (Иконка + Статус)
  let headerRow = w.addStack();
  headerRow.centerAlignContent();

  let iconText = headerRow.addText(isOutage ? "⚡" : "💡");
  iconText.font = Font.systemFont(18);
  headerRow.addSpacer(6);

  let titleText = headerRow.addText(isOutage ? "ВІДКЛЮЧЕННЯ" : "СВІТЛО Є");
  titleText.font = Font.boldSystemFont(15);
  titleText.textColor = isOutage ? new Color("#f87171") : new Color("#34d399");

  headerRow.addSpacer();

  // Время обновления
  let now = new Date();
  let timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  let updateText = headerRow.addText(timeStr);
  updateText.font = Font.systemFont(11);
  updateText.textColor = new Color("#9ca3af");

  w.addSpacer(8);

  if (isOutage) {
    // Расчет обратного отсчета
    let nowTs = Math.floor(Date.now() / 1000);
    let endTs = info.end_timestamp || nowTs;
    let diff = Math.max(0, endTs - nowTs);

    let hours = Math.floor(diff / 3600);
    let mins = Math.floor((diff % 3600) / 60);

    let countdownStack = w.addStack();
    countdownStack.bottomAlignContent();

    let cdLabel = countdownStack.addText("ДО ВКЛЮЧЕНИЯ: ");
    cdLabel.font = Font.semiboldSystemFont(11);
    cdLabel.textColor = new Color("#d1d5db");

    let cdTime = countdownStack.addText(`${hours}ч ${mins}м`);
    cdTime.font = Font.boldSystemFont(16);
    cdTime.textColor = new Color("#fbbf24");

    w.addSpacer(4);

    // Время восстановления
    if (info.end_time_str) {
      let recText = w.addText(`Ожидается к: ${info.end_time_str}`);
      recText.font = Font.systemFont(12);
      recText.textColor = new Color("#e5e7eb");
    }
  } else {
    let stableText = w.addText("Электросеть работает стабильно");
    stableText.font = Font.systemFont(13);
    stableText.textColor = new Color("#d1fae5");
  }

  w.addSpacer(6);

  // Адрес
  if (info.address) {
    let addrText = w.addText(`📍 ${info.address}`);
    addrText.font = Font.systemFont(11);
    addrText.textColor = new Color("#9ca3af");
    addrText.lineLimit = 1;
  }

  // Причина
  if (info.reason && isOutage) {
    let reasonText = w.addText(`🛠 ${info.reason}`);
    reasonText.font = Font.systemFont(10);
    reasonText.textColor = new Color("#6b7280");
    reasonText.lineLimit = 1;
  }

  return w;
}
