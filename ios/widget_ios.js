const SERVER_URL = "https://lightwidget.onrender.com/api/status";

let data = null;
try {
  let urlWithAntiCache = SERVER_URL + (SERVER_URL.includes("?") ? "&" : "?") + "t=" + Date.now();
  let req = new Request(urlWithAntiCache);
  req.timeoutInterval = 8;
  req.headers = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache"
  };
  data = await req.loadJSON();
  let fm = FileManager.local();
  let cachePath = fm.joinPath(fm.documentsDirectory(), "light_widget_cache.json");
  fm.writeString(cachePath, JSON.stringify(data));
} catch (e) {
  let fm = FileManager.local();
  let cachePath = fm.joinPath(fm.documentsDirectory(), "light_widget_cache.json");
  if (fm.fileExists(cachePath)) {
    try {
      data = JSON.parse(fm.readString(cachePath));
    } catch (err) {}
  }
  if (!data) {
    data = {
      status: "UNKNOWN",
      reason: "Сервер временно недоступен",
      is_outage: false
    };
  }
}

let widget = await createWidget(data);
if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  widget.presentMedium();
}
Script.complete();

async function createWidget(info) {
  let w = new ListWidget();
  w.setPadding(16, 18, 16, 18);

  w.url = "scriptable:///run?scriptName=LightWidget";

  let diff = getRemainingSeconds(info);
  let isOutage = info && (info.status === "OFF" || info.is_outage === true) && diff > 0;

  w.refreshAfterDate = new Date(Date.now() + 60 * 1000);

  let gradient = new LinearGradient();
  if (isOutage) {
    gradient.colors = [new Color("#200d0d"), new Color("#100606")];
  } else {
    gradient.colors = [new Color("#0d1912"), new Color("#070d0a")];
  }
  gradient.locations = [0.0, 1.0];
  w.backgroundGradient = gradient;

  let headerRow = w.addStack();
  headerRow.centerAlignContent();

  let labelText = headerRow.addText("Свет: ");
  labelText.font = Font.boldSystemFont(17);
  labelText.textColor = new Color("#ffffff");

  let dotText = headerRow.addText(isOutage ? "🔴" : "🟢");
  dotText.font = Font.systemFont(15);

  headerRow.addSpacer();

  let now = new Date();
  let timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  let updateText = headerRow.addText(timeStr);
  updateText.font = Font.systemFont(11);
  updateText.textColor = new Color("#6b7280");

  w.addSpacer(12);

  if (isOutage) {
    let cdTimeString = formatWidgetCountdown(diff);

    let cdLabel = w.addText("ДО ВКЛЮЧЕНИЯ:");
    cdLabel.font = Font.semiboldSystemFont(11);
    cdLabel.textColor = new Color("#9ca3af");

    w.addSpacer(2);

    let cdTime = w.addText(cdTimeString);
    cdTime.font = Font.boldSystemFont(22);
    cdTime.textColor = new Color("#f87171");

    w.addSpacer(6);

    let formattedEndTime = formatEndTime(info);
    if (formattedEndTime) {
      let recText = w.addText(`Ориентировочно до: ${formattedEndTime}`);
      recText.font = Font.systemFont(12);
      recText.textColor = new Color("#e5e7eb");
    }

    if (info.reason) {
      w.addSpacer(3);
      let reasonText = w.addText(`🛠 ${info.reason}`);
      reasonText.font = Font.systemFont(10.5);
      reasonText.textColor = new Color("#9ca3af");
      reasonText.lineLimit = 1;
    }
  } else {
    let statusRow = w.addStack();
    statusRow.centerAlignContent();

    let mainStatusText = statusRow.addText("Свет есть");
    mainStatusText.font = Font.boldSystemFont(24);
    mainStatusText.textColor = new Color("#34d399");

    w.addSpacer(6);

    let subText = w.addText("Питание подается в штатном режиме");
    subText.font = Font.systemFont(12);
    subText.textColor = new Color("#9ca3af");
  }

  return w;
}

function formatWidgetCountdown(diff) {
  let days = Math.floor(diff / 86400);
  let hours = Math.floor((diff % 86400) / 3600);
  let mins = Math.floor((diff % 3600) / 60);
  let secs = diff % 60;

  let parts = [];
  if (days > 0) {
    parts.push(`${days}д`);
  }
  if (days > 0 || hours > 0) {
    parts.push(`${hours}ч`);
  }
  if (days > 0 || hours > 0 || mins > 0) {
    parts.push(`${mins}м`);
  }
  if (days === 0 && hours === 0 && mins === 0) {
    parts.push(`${secs}с`);
  }

  return parts.length > 0 ? parts.join(" ") : "0с";
}

function getRemainingSeconds(info) {
  if (!info) return 0;
  let now = new Date();
  let nowTs = Math.floor(now.getTime() / 1000);

  if (info.end_time_str) {
    let match = info.end_time_str.match(/(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{2,4})\s+(\d{1,2}):(\d{2})/);
    if (match) {
      let day = parseInt(match[1], 10);
      let month = parseInt(match[2], 10) - 1;
      let year = parseInt(match[3], 10);
      if (year < 100) year += 2000;
      let hours = parseInt(match[4], 10);
      let minutes = parseInt(match[5], 10);
      let targetDate = new Date(year, month, day, hours, minutes, 0);
      return Math.max(0, Math.floor(targetDate.getTime() / 1000) - nowTs);
    }

    let timeMatch = info.end_time_str.match(/(\d{1,2}):(\d{2})/);
    if (timeMatch) {
      let hours = parseInt(timeMatch[1], 10);
      let minutes = parseInt(timeMatch[2], 10);
      let targetDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hours, minutes, 0);
      if (targetDate.getTime() < now.getTime() - 2 * 3600 * 1000) {
        targetDate.setDate(targetDate.getDate() + 1);
      }
      return Math.max(0, Math.floor(targetDate.getTime() / 1000) - nowTs);
    }
  }

  if (info.end_timestamp) {
    return Math.max(0, info.end_timestamp - nowTs);
  }

  return 0;
}

function formatEndTime(info) {
  if (!info || !info.end_time_str) return "";
  let raw = String(info.end_time_str).trim();
  let timeMatch = raw.match(/\b\d{1,2}:\d{2}\b/);
  let timeOnly = timeMatch ? timeMatch[0] : "";

  let diff = getRemainingSeconds(info);
  if (timeOnly && diff < 86400) {
    return timeOnly;
  }

  return raw;
}
