import re
from datetime import datetime
import time

def parse_datetime(dt_str):
    """
    Parses datetime string into datetime object.
    Supports formats:
    - 15.08.2026 09:35
    - 16:34 15.08.2026
    - до 16:34 15.08.2026
    - 15.08.26 09:35
    - 15.08.2026 в 09:35
    - 2026-08-15 09:35
    """
    if not dt_str:
        return None
    dt_str = dt_str.strip()
    dt_str = re.sub(r'^(?:до|в|на|о|орієнтовно|–|-)\s+', '', dt_str, flags=re.IGNORECASE).strip()
    dt_str = re.sub(r'\s+в\s+', ' ', dt_str, flags=re.IGNORECASE)
    dt_str = re.sub(r'\s+до\s+', ' ', dt_str, flags=re.IGNORECASE)
    dt_str = dt_str.rstrip('.,;!')

    formats = [
        "%d.%m.%Y %H:%M",
        "%H:%M %d.%m.%Y",
        "%d.%m.%y %H:%M",
        "%H:%M %d.%m.%y",
        "%d/%m/%Y %H:%M",
        "%H:%M %d/%m/%Y",
        "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
            
    # Check if format is time followed by date
    time_date_match = re.search(r'(\d{1,2}:\d{2})\s+(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})', dt_str)
    if time_date_match:
        t_part, d_part = time_date_match.groups()
        for fmt in ["%H:%M %d.%m.%Y", "%H:%M %d.%m.%y", "%H:%M %d/%m/%Y"]:
            try:
                return datetime.strptime(f"{t_part} {d_part}", fmt)
            except ValueError:
                pass

    # Check if format is date followed by time
    date_time_match = re.search(r'(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})\s+(\d{1,2}:\d{2})', dt_str)
    if date_time_match:
        d_part, t_part = date_time_match.groups()
        for fmt in ["%d.%m.%Y %H:%M", "%d.%m.%y %H:%M", "%d/%m/%Y %H:%M"]:
            try:
                return datetime.strptime(f"{d_part} {t_part}", fmt)
            except ValueError:
                pass

    return None

def parse_single_block(text_clean: str) -> dict:
    """
    Parses a single outage message block.
    """
    if not text_clean or len(text_clean.strip()) < 5:
        return None

    # 1. Detect Status
    is_no_outage = bool(re.search(r"(не\s+зафіксовано\s+відключень|відключень\s+не\s+зафіксовано|немає\s+відключень|відключення\s+відсутні|наразі\s+не\s+зафіксовано|подати\s+заявку\s+на\s+відсутність\s+світла|повідомити\s+про\s+відсутність\s+світла)", text_clean, re.IGNORECASE))
    is_restored = bool(re.search(r"(відновлено|включено|живлення подано|електропостачання.*?відновлено|скасовано)", text_clean, re.IGNORECASE))
    is_outage = bool(re.search(r"(відключення|відсутня електроенергія|відсутнє електропостачання|знеструмлено|аварійне відключення|стабілізаційне відключення|перерва в електропостачанні|немає світла)", text_clean, re.IGNORECASE))
    
    if is_no_outage or (is_restored and not ("зафіксовано відключення" in text_clean and "відновлено" not in text_clean[:60])):
        status = "ON"
    elif is_outage:
        status = "OFF"
    else:
        status = "OFF" if ("❗️" in text_clean or "⚠️" in text_clean) else "ON"

    # 2. Extract Address
    address = "м. Одеса, вул. Чайки Максима, 25"
    addr_match = re.search(r"(?:Електропостачання\s+)?за адресою\s+(.+?)(?:\s+в\s+даний\s+момент|\s+зафіксовано|\s+змінено|\s+відновлено|\s+відсутня|\r?\n|$)", text_clean, re.IGNORECASE)
    if addr_match and "вашою адресою" not in addr_match.group(1).lower():
        address = addr_match.group(1).strip().rstrip('.,;')
    else:
        alt_addr = re.search(r"(?:вул\.|м\.|просп\.|пров\.|буд\.)\s*([^\n\r]+)", text_clean, re.IGNORECASE)
        if alt_addr:
            address = alt_addr.group(0).strip().rstrip('.,;')

    # 3. Extract Reason
    if is_no_outage:
        reason = "Штатный режим электросети (отключений не зафиксировано)"
    else:
        reason = "Планові / Аварійні роботи"
        reason_match = re.search(r"Причина:\s*([^\n\r]+)", text_clean, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip().rstrip('.,;')

    # 4. Extract Start Time
    start_dt = None
    start_match = re.search(r"Час початку:\s*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}\s+\d{1,2}:\d{2})", text_clean, re.IGNORECASE)
    if start_match:
        start_dt = parse_datetime(start_match.group(1))

    # 5. Extract End / Recovery Time
    end_dt = None
    end_match = re.search(r"(?:Новий орієнтовний час відновлення|Орієнтовний час відновлення|Час відновлення).*?(?:–|:|\sдо)\s*([^\n\r]+)", text_clean, re.IGNORECASE)
    if end_match:
        end_dt = parse_datetime(end_match.group(1))
    
    if not end_dt:
        # Fallback search for time/date pattern following 'відновлення'
        fallback_dt = re.search(r'відновлення[^\d]*(\d{1,2}:\d{2}\s+\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}|\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}\s+\d{1,2}:\d{2})', text_clean, re.IGNORECASE)
        if fallback_dt:
            end_dt = parse_datetime(fallback_dt.group(1))

    now = datetime.now()
    now_ts = int(now.timestamp())

    if status == "OFF" and not start_dt:
        start_dt = now

    start_ts = int(start_dt.timestamp()) if start_dt else None
    end_ts = int(end_dt.timestamp()) if end_dt else None

    # Calculate duration & progress
    total_seconds = None
    remaining_seconds = None
    elapsed_seconds = None
    progress_percent = 0.0

    if start_dt and end_dt:
        total_seconds = max(0, int((end_dt - start_dt).total_seconds()))
        elapsed_seconds = max(0, min(total_seconds, now_ts - start_ts))
        remaining_seconds = max(0, end_ts - now_ts)
        if total_seconds > 0:
            progress_percent = min(100.0, max(0.0, round((elapsed_seconds / total_seconds) * 100, 1)))

    # If the outage end timestamp is already in the past, power is restored -> status is ON!
    is_outage = (status == "OFF")
    if status == "OFF" and end_ts and now_ts >= end_ts:
        status = "ON"
        is_outage = False
        reason = "Электросеть работает в штатном режиме (время отключения завершено)"

    return {
        "status": status,
        "is_outage": is_outage,
        "address": address,
        "reason": reason,
        "start_time_str": start_dt.strftime("%d.%m.%Y %H:%M") if start_dt else None,
        "end_time_str": end_dt.strftime("%d.%m.%Y %H:%M") if end_dt else None,
        "start_timestamp": start_ts,
        "end_timestamp": end_ts,
        "total_seconds": total_seconds,
        "remaining_seconds": remaining_seconds,
        "elapsed_seconds": elapsed_seconds,
        "progress_percent": progress_percent,
        "raw_text": text_clean,
        "updated_at": now.isoformat()
    }

def parse_message(text: str) -> dict:
    """
    Parses incoming telegram message text (handling multi-block messages separated by ---).
    Selects the block with the longest/furthest estimated recovery time.
    """
    if not text:
        return None
    
    text_clean = text.strip()
    
    # Split by delimiter lines (e.g. ------ or ====== or ***)
    blocks = re.split(r'\r?\n\s*[-=_*]{3,}\s*\r?\n', text_clean)
    
    if len(blocks) == 1:
        # Also check if multiple '❗️ За адресою' blocks are joined without dashes
        sub_blocks = re.split(r'(?=\n❗️\s*За адресою)', text_clean)
        if len(sub_blocks) > 1:
            blocks = sub_blocks

    parsed_blocks = []
    for b in blocks:
        p = parse_single_block(b.strip())
        if p:
            parsed_blocks.append(p)

    if not parsed_blocks:
        return parse_single_block(text_clean)

    if len(parsed_blocks) == 1:
        return parsed_blocks[0]

    # Multiple blocks found:
    # Pick the block with the latest/highest end_timestamp (the longer outage is the definitive one)
    outage_blocks = [b for b in parsed_blocks if b.get("is_outage")]
    candidate_blocks = outage_blocks if outage_blocks else parsed_blocks

    def sort_key(b):
        return (b.get("end_timestamp") or 0, b.get("total_seconds") or 0)

    best_block = max(candidate_blocks, key=sort_key)
    
    # Collect all unique reasons if there are multiple
    all_reasons = []
    for b in candidate_blocks:
        r = b.get("reason", "").strip()
        if r and r not in all_reasons and r != "Планові / Аварійні роботи":
            all_reasons.append(r)
    
    if len(all_reasons) > 1:
        best_block["reason"] = " • ".join(all_reasons)

    best_block["raw_text"] = text_clean
    return best_block
