import re
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
    KYIV_TZ = ZoneInfo("Europe/Kyiv")
except Exception:
    from datetime import timezone
    KYIV_TZ = timezone(timedelta(hours=3))


def _normalize(text):
    return re.sub(r'[^\S\n\r]+', ' ', re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)).strip()


def parse_datetime(dt_str):
    if not dt_str:
        return None
    value = _normalize(dt_str).rstrip('.,;!')
    value = re.sub(r'\s+(?:в|до|о)\s+|,\s*', ' ', value, flags=re.IGNORECASE)
    date = r'(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[./]\d{1,2}[./](?:\d{4}|\d{2}))'
    clock = r'\d{1,2}:\d{2}(?::\d{2})?'
    match = re.search(rf'\b(?:{date}\s+{clock}|{clock}\s+{date})\b', value)
    if match:
        value = match.group(0)
    for date_format in ('%d.%m.%Y', '%d.%m.%y', '%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'):
        for fmt in (f'{date_format} %H:%M', f'%H:%M {date_format}', f'{date_format} %H:%M:%S', f'%H:%M:%S {date_format}'):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=KYIV_TZ)
            except ValueError:
                pass
    return None


def is_menu_service_message(text):
    if not text:
        return False
    value = _normalize(text).lower()
    if re.search(r'зафіксовано\s+(?:аварійне\s+)?відключення|відключен(?:ь|ня)\s+не\s+зафіксовано|не\s+зафіксовано\s+відключен|заплановані\s+ремонтні\s+роботи|планові\s+ремонтні\s+роботи|немає\s+світла|електропостачання\s+(?:було\s+)?відновлено|час\s+(?:початку|відновлення|завершення)', value):
        return False
    patterns = (
        r'графік[иу]?\s+стабілізаційних\s+відключень',
        r'графік[иу]?\s+(?:погодинних\s+)?відключень\s+за\s+адресою',
        r'графіки\s+актуальні\s+тільки',
        r'пам[’\x27ʼ]?ятайте[^\n]*графік',
        r'^/?start$', r'оберіть\s+потрібний\s+розділ', r'натиснувши\s+кнопку\s+нижче',
        r'^(?:💡\s*)?можливі\s+відключення', r'^послуги', r'^передати\s+покази',
        r'^що\s+як\s+і\s+чому', r'^повідомити\s+про\s+відсутність\s+світла',
        r'^☰\s*меню', r'^головне\s+меню', r'сталася\s+помилка',
        r'спробуйте\s+пізніше', r'тимчасово\s+недоступн'
    )
    return any(re.search(pattern, value) for pattern in patterns)


def parse_single_block(text_clean):
    if not text_clean or len(text_clean.strip()) < 5:
        return None
    text_clean = _normalize(text_clean)
    if is_menu_service_message(text_clean):
        return None
    value = text_clean.lower()
    is_no_outage = bool(re.search(r'не\s+зафіксовано\s+(?:аварійних?\s+)?відключен(?:ь|ня)|відключен(?:ь|ня)\s+не\s+зафіксовано|немає\s+відключень|відключення\s+відсутні|наразі\s+не\s+зафіксовано|електромереж[а-яіїєґ]*\s+працю[а-яіїєґ]*\s+у\s+штатному\s+режимі', value))
    restoration_text = re.sub(r'(?:буде|будуть|має\s+бути|планується|очікується)[^.!?\n]*?(?:відновлено|включено)', '', value)
    is_restored = bool(re.search(r'(?<!не )\b(?:відновлено|включено|живлення\s+подано)\b', restoration_text))
    has_fixed_outage = bool(re.search(r'зафіксовано\s+(?:аварійне\s+)?відключення|аварійне\s+відключення|знеструмлено', value)) and not is_no_outage
    has_planned = bool(re.search(r'заплановані\s+ремонтні\s+роботи|заплановано\s+відключення|планові\s+ремонтні\s+роботи', value))
    is_cancelled = bool(re.search(r'скасован[оіа]|відмінено', value))
    planned_cancelled = has_planned and is_cancelled
    outage_update = bool(re.search(r'новий\s+орієнтовний\s+час\s+відновлення|змінено\s+(?:орієнтовний\s+)?час\s+відновлення', value))
    has_outage = bool(re.search(r'відключення|відсутня\s+електроенергія|електроенергія\s+відсутня|відсутнє\s+електропостачання|перерва\s+в\s+електропостачанні|немає\s+світла|не\s+відновлено', value))
    explicit_on = is_no_outage or is_restored or (is_cancelled and not has_planned and 'відключення' in value)
    if not any((explicit_on, has_fixed_outage, has_planned, has_outage, outage_update)):
        return None

    start_match = re.search(r'час\s+початку\s*:\s*([^\n\r]+)', text_clean, re.IGNORECASE)
    end_match = re.search(r'(?:новий\s+)?(?:орієнтовний\s+)?час\s+(?:відновлення|завершення)[^:\n\r]*[:–]\s*([^\n\r]+)', text_clean, re.IGNORECASE)
    start_dt = parse_datetime(start_match.group(1)) if start_match else None
    end_dt = parse_datetime(end_match.group(1)) if end_match else None
    if not end_dt:
        fallback = re.search(r'відновлення[^\d\n]*(\d[^\n\r]+)', text_clean, re.IGNORECASE)
        if fallback:
            end_dt = parse_datetime(fallback.group(1))
    if start_dt and end_dt and end_dt <= start_dt:
        return None
    if has_planned and not planned_cancelled and (not start_dt or not end_dt):
        return None

    address = "Не указан"
    addr_match = re.search(r'(?:Електропостачання\s+)?за адресою\s+(.+?)(?:\s+в\s+даний\s+момент|\s+зафіксовано|\s+змінено|\s+відновлено|\s+відсутня|\s+заплановані|\s+плануються|\s+будуть|\r?\n|$)', text_clean, re.IGNORECASE)
    if addr_match and 'вашою адресою' not in addr_match.group(1).lower():
        address = addr_match.group(1).strip().rstrip('.,;')
    else:
        alt_addr = re.search(r'(?:вул\.|м\.|просп\.|пров\.|буд\.)\s*([^\n\r]+)', text_clean, re.IGNORECASE)
        if alt_addr:
            address = alt_addr.group(0).strip().rstrip('.,;')
    reason_match = re.search(r'причина\s*:\s*([^\n\r]+)', text_clean, re.IGNORECASE)
    reason = reason_match.group(1).strip().rstrip('.,;') if reason_match else ("Заплановані ремонтні роботи" if has_planned else "Зафіксовано відключення електроенергії")
    now = datetime.now(KYIV_TZ)
    now_ts = int(now.timestamp())
    future_fixed = bool(has_fixed_outage and start_dt and start_dt.timestamp() > now_ts)
    is_planned = (has_planned and not has_fixed_outage and not explicit_on and not planned_cancelled) or future_fixed
    status = "ON" if explicit_on or planned_cancelled or is_planned else "OFF"
    power_update = explicit_on or status == "OFF"
    if status == "OFF" and not start_dt and not outage_update:
        start_dt = now
    if explicit_on:
        start_dt = None
        end_dt = None
        reason = "Электросеть работает в штатном режиме."
    start_ts = int(start_dt.timestamp()) if start_dt else None
    end_ts = int(end_dt.timestamp()) if end_dt else None
    planned_changes = []
    if planned_cancelled:
        planned_changes.append({"action": "cancel", "start_timestamp": start_ts})
    elif is_planned:
        planned_changes.append({"action": "upsert", "item": {
            "start_timestamp": start_ts, "end_timestamp": end_ts,
            "start_time_str": start_dt.strftime("%d.%m.%Y %H:%M"),
            "end_time_str": end_dt.strftime("%d.%m.%Y %H:%M") if end_dt else None,
            "reason": reason
        }})
    is_planned = bool(is_planned and start_ts and end_ts and end_ts > now_ts)
    total = end_ts - start_ts if start_ts and end_ts else None
    elapsed = max(0, now_ts - start_ts) if start_ts else None
    remaining = max(0, (start_ts if is_planned and now_ts < start_ts else end_ts) - now_ts) if end_ts else None
    return {
        "status": status, "is_outage": status == "OFF", "is_explicit_on": bool(explicit_on),
        "is_planned": is_planned, "planned_active": bool(is_planned and start_ts <= now_ts < end_ts),
        "address": address, "reason": reason,
        "start_time_str": start_dt.strftime("%d.%m.%Y %H:%M") if start_dt else None,
        "end_time_str": end_dt.strftime("%d.%m.%Y %H:%M") if end_dt else None,
        "start_timestamp": start_ts, "end_timestamp": end_ts,
        "total_seconds": total, "remaining_seconds": remaining, "elapsed_seconds": elapsed,
        "progress_percent": min(100.0, round(elapsed / total * 100, 1)) if total and elapsed is not None else 0.0,
        "planned_outages": [change["item"] for change in planned_changes if change["action"] == "upsert" and is_planned],
        "raw_text": text_clean, "updated_at": now.isoformat(),
        "_power_update": bool(power_update), "_outage_update": outage_update,
        "_planned_changes": planned_changes
    }


def parse_message(text):
    if not text:
        return None
    text_clean = _normalize(text)
    blocks = re.split(r'\r?\n\s*[-=_*]{3,}\s*\r?\n|(?=\n(?:❗️?|💡)\s*За адресою)', text_clean)
    parsed = [result for block in blocks if (result := parse_single_block(block.strip()))]
    if not parsed:
        return None
    latest_on = max((index for index, block in enumerate(parsed) if block['is_explicit_on']), default=-1)
    outages = {}
    for index, block in enumerate(parsed):
        if index > latest_on and block['status'] == 'OFF':
            if block['_outage_update'] and not block['start_timestamp'] and outages:
                previous = next(reversed(outages.values()))
                if block['end_timestamp'] and previous['start_timestamp'] and block['end_timestamp'] <= previous['start_timestamp']:
                    continue
                block = block.copy()
                for key in ('start_timestamp', 'start_time_str', 'reason'):
                    block[key] = previous[key]
            outages[block['start_timestamp']] = block
    if outages:
        candidates = list(outages.values())
        best = max(candidates, key=lambda block: block['end_timestamp'] or float('inf')).copy()
        reasons = list(dict.fromkeys(block['reason'] for block in candidates if block['reason']))
        best['reason'] = ' • '.join(reasons)
    else:
        best = (parsed[latest_on] if latest_on >= 0 else parsed[-1]).copy()
    changes = [change for block in parsed for change in block['_planned_changes']]
    plans = {}
    now_ts = int(datetime.now(KYIV_TZ).timestamp())
    for change in changes:
        if change['action'] == 'cancel':
            if change['start_timestamp'] is None:
                plans.clear()
            else:
                plans.pop(change['start_timestamp'], None)
        else:
            item = change['item']
            plans.pop(item['start_timestamp'], None)
            if item['end_timestamp'] and item['end_timestamp'] > now_ts:
                plans[item['start_timestamp']] = item
    best['planned_outages'] = sorted(plans.values(), key=lambda item: item['start_timestamp'])
    best['_planned_changes'] = changes
    best['_power_update'] = bool(outages or latest_on >= 0)
    if best['status'] == 'OFF' and best['end_timestamp'] and best['end_timestamp'] <= now_ts:
        best['light_on_since'] = best['end_timestamp'] * 1000
        best['status'] = 'ON'
        best['is_outage'] = False
        best['reason'] = 'Электросеть работает в штатном режиме (ориентировочное время отключения завершено)'
    best['is_planned'] = bool(best['planned_outages'] and best['status'] != 'OFF')
    best['planned_active'] = False
    if best['status'] == 'OFF' and best['start_timestamp']:
        best['elapsed_seconds'] = max(0, now_ts - best['start_timestamp'])
        if best['end_timestamp']:
            best['total_seconds'] = max(0, best['end_timestamp'] - best['start_timestamp'])
            best['remaining_seconds'] = max(0, best['end_timestamp'] - now_ts)
            best['progress_percent'] = min(100.0, round(best['elapsed_seconds'] / best['total_seconds'] * 100, 1)) if best['total_seconds'] else 0.0
    if best['is_planned']:
        nearest = best['planned_outages'][0]
        for key in ('start_timestamp', 'end_timestamp', 'start_time_str', 'end_time_str'):
            best[key] = nearest[key]
        best['planned_active'] = nearest['start_timestamp'] <= now_ts < nearest['end_timestamp']
    best['raw_text'] = text_clean
    return best
