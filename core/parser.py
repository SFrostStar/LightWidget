import re
from datetime import datetime ,timedelta
import time
try :
    from zoneinfo import ZoneInfo
    KYIV_TZ =ZoneInfo ("Europe/Kyiv")
except Exception :
    from datetime import timezone ,timedelta
    KYIV_TZ =timezone (timedelta (hours =3 ))

def parse_datetime (dt_str ):
    if not dt_str :
        return None
    dt_str =dt_str .strip ()
    dt_str =re .sub (r'^(?:до|в|на|о|орієнтовно|–|-)\s+','',dt_str ,flags =re .IGNORECASE ).strip ()
    dt_str =re .sub (r'\s+в\s+',' ',dt_str ,flags =re .IGNORECASE )
    dt_str =re .sub (r'\s+до\s+',' ',dt_str ,flags =re .IGNORECASE )
    dt_str =dt_str .rstrip ('.,;!')

    formats =[
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
    for fmt in formats :
        try :
            d =datetime .strptime (dt_str ,fmt )
            return d .replace (tzinfo =KYIV_TZ )
        except ValueError :
            continue

    time_date_match =re .search (r'(\d{1,2}:\d{2})\s+(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})',dt_str )
    if time_date_match :
        t_part ,d_part =time_date_match .groups ()
        for fmt in ["%H:%M %d.%m.%Y","%H:%M %d.%m.%y","%H:%M %d/%m/%Y"]:
            try :
                d =datetime .strptime (f"{t_part } {d_part }",fmt )
                return d .replace (tzinfo =KYIV_TZ )
            except ValueError :
                pass

    date_time_match =re .search (r'(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})\s+(\d{1,2}:\d{2})',dt_str )
    if date_time_match :
        d_part ,t_part =date_time_match .groups ()
        for fmt in ["%d.%m.%Y %H:%M","%d.%m.%y %H:%M","%d/%m/%Y %H:%M"]:
            try :
                d =datetime .strptime (f"{d_part } {t_part }",fmt )
                return d .replace (tzinfo =KYIV_TZ )
            except ValueError :
                pass

    return None

def is_menu_service_message (text :str )->bool :
    if not text :
        return False
    t =text .strip ().lower ()
    menu_patterns =[
    r"^/?start$",
    r"оберіть\s+(потрібний\s+розділ|тип\s+об'єкта|особовий\s+рахунок)",
    r"натиснувши\s+кнопку\s+нижче",
    r"вітаємо\s+у\s+чат-боті",
    r"^💡\s*можливі\s+відключення",
    r"^можливі\s+відключення",
    r"^☰\s*меню",
    r"^повідомити\s+про\s+відсутність\s+світла",
    r"^головне\s+меню",
    ]
    for pat in menu_patterns :
        if re .search (pat ,t ):
            return True
    return False

def parse_single_block (text_clean :str )->dict :
    if not text_clean or len (text_clean .strip ())<5 :
        return None

    if is_menu_service_message (text_clean ):
        return None

    is_no_outage =bool (re .search (r"(не\s+зафіксовано\s+відключень|відключень\s+не\s+зафіксовано|немає\s+відключень|відключення\s+відсутні|наразі\s+не\s+зафіксовано|подати\s+заявку\s+на\s+відсутність\s+світла|повідомити\s+про\s+відсутність\s+світла)",text_clean ,re .IGNORECASE ))
    is_restored =bool (re .search (r"(відновлено|включено|живлення подано|електропостачання.*?відновлено|скасовано)",text_clean ,re .IGNORECASE ))
    has_fixed_outage =bool (re .search (r"(зафіксовано\s+відключення|зафіксовано\s+аварійне|аварійне\s+відключення|знеструмлено)",text_clean ,re .IGNORECASE ))or "❗️"in text_clean 
    is_planned =False 
    if not has_fixed_outage and not is_no_outage and not is_restored :
        if re .search (r"(?:💡\s*)?(?:заплановані\s+ремонтні\s+роботи|заплановано\s+відключення|планові\s+ремонтні\s+роботи)",text_clean ,re .IGNORECASE ):
            is_planned =True 
    is_outage =bool (re .search (r"(відключення|відсутня електроенергія|відсутнє електропостачання|знеструмлено|аварійне відключення|стабілізаційне відключення|перерва в електропостачанні|немає світла)",text_clean ,re .IGNORECASE ))or has_fixed_outage 

    if is_no_outage or (is_restored and not ("зафіксовано відключення"in text_clean and "відновлено"not in text_clean [:60 ])):
        status ="ON"
    elif is_planned :
        status ="PLANNED"
    elif is_outage or has_fixed_outage :
        status ="OFF"
    else :
        status ="OFF"if ("❗️"in text_clean or "⚠️"in text_clean )else "ON"

    address ="Не указан"
    addr_match =re .search (r"(?:Електропостачання\s+)?за адресою\s+(.+?)(?:\s+в\s+даний\s+момент|\s+зафіксовано|\s+змінено|\s+відновлено|\s+відсутня|\s+заплановані|\s+плануються|\s+будуть|\r?\n|$)",text_clean ,re .IGNORECASE )
    if addr_match and "вашою адресою"not in addr_match .group (1 ).lower ():
        address =addr_match .group (1 ).strip ().rstrip ('.,;')
    else :
        alt_addr =re .search (r"(?:вул\.|м\.|просп\.|пров\.|буд\.)\s*([^\n\r]+)",text_clean ,re .IGNORECASE )
        if alt_addr :
            address =alt_addr .group (0 ).strip ().rstrip ('.,;')

    if is_no_outage :
        reason ="Штатный режим электросети (отключений не зафиксировано)"
    elif is_planned :
        reason ="Заплановані ремонтні роботи"
        reason_match =re .search (r"Причина:\s*([^\n\r]+)",text_clean ,re .IGNORECASE )
        if reason_match :
            reason =reason_match .group (1 ).strip ().rstrip ('.,;')
    else :
        reason ="Планові / Аварійні роботи"
        reason_match =re .search (r"Причина:\s*([^\n\r]+)",text_clean ,re .IGNORECASE )
        if reason_match :
            reason =reason_match .group (1 ).strip ().rstrip ('.,;')
        elif "зафіксовано відключення"in text_clean .lower ():
            reason ="Зафіксовано відключення електроенергії"

    start_dt =None
    start_match =re .search (r"Час початку:\s*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}\s+\d{1,2}:\d{2})",text_clean ,re .IGNORECASE )
    if start_match :
        start_dt =parse_datetime (start_match .group (1 ))

    end_dt =None
    end_match =re .search (r"(?:Новий орієнтовний час відновлення|Орієнтовний час відновлення|Час відновлення|Час завершення|Орієнтовний час завершення).*?(?:–|:|\sдо)\s*([^\n\r]+)",text_clean ,re .IGNORECASE )
    if end_match :
        end_dt =parse_datetime (end_match .group (1 ))

    if not end_dt :
        fallback_dt =re .search (r'відновлення[^\d]*(\d{1,2}:\d{2}\s+\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}|\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}\s+\d{1,2}:\d{2})',text_clean ,re .IGNORECASE )
        if fallback_dt :
            end_dt =parse_datetime (fallback_dt .group (1 ))

    now =datetime .now (KYIV_TZ )
    now_ts =int (now .timestamp ())

    start_ts =int (start_dt .timestamp ())if start_dt else None
    end_ts =int (end_dt .timestamp ())if end_dt else None

    total_seconds =None
    remaining_seconds =None
    elapsed_seconds =None
    progress_percent =0.0

    if is_planned :
        if start_ts and now_ts <start_ts :
            status ="ON"
            is_outage =False
            total_seconds =max (0 ,int ((end_dt -start_dt ).total_seconds ()))if end_dt else None 
            remaining_seconds =max (0 ,start_ts -now_ts )
        elif start_ts and end_ts and start_ts <=now_ts <end_ts :
            status ="OFF"
            is_outage =True
            total_seconds =max (0 ,int ((end_dt -start_dt ).total_seconds ()))
            elapsed_seconds =max (0 ,now_ts -start_ts )
            remaining_seconds =max (0 ,end_ts -now_ts )
            if total_seconds >0 :
                progress_percent =min (100.0 ,max (0.0 ,round ((elapsed_seconds /total_seconds )*100 ,1 )))
        elif end_ts and now_ts >=end_ts :
            status ="ON"
            is_outage =False
            is_planned =False
            reason ="Электросеть работает в штатном режиме (время ремонтных работ завершено)"
        else :
            status ="ON"
            is_outage =False
            is_planned =False
    else :
        if status =="OFF"and not start_dt :
            start_dt =now
            start_ts =int (start_dt .timestamp ())

        if start_dt and end_dt :
            total_seconds =max (0 ,int ((end_dt -start_dt ).total_seconds ()))
            elapsed_seconds =max (0 ,min (total_seconds ,now_ts -start_ts ))
            remaining_seconds =max (0 ,end_ts -now_ts )
            if total_seconds >0 :
                progress_percent =min (100.0 ,max (0.0 ,round ((elapsed_seconds /total_seconds )*100 ,1 )))

        is_outage =(status =="OFF")
        if status =="OFF"and end_ts and now_ts >=end_ts :
            status ="ON"
            is_outage =False
            reason ="Электросеть работает в штатном режиме (время отключения завершено)"

    planned_outages =[]
    if is_planned and start_ts and end_ts and end_ts >now_ts :
        planned_outages .append ({
        "start_time_str":start_dt .strftime ("%d.%m.%Y %H:%M"),
        "end_time_str":end_dt .strftime ("%d.%m.%Y %H:%M"),
        "start_timestamp":start_ts ,
        "end_timestamp":end_ts ,
        "reason":reason 
        })

    return {
    "status":status ,
    "is_outage":is_outage ,
    "is_planned":is_planned ,
    "address":address ,
    "reason":reason ,
    "start_time_str":start_dt .strftime ("%d.%m.%Y %H:%M")if start_dt else None ,
    "end_time_str":end_dt .strftime ("%d.%m.%Y %H:%M")if end_dt else None ,
    "start_timestamp":start_ts ,
    "end_timestamp":end_ts ,
    "total_seconds":total_seconds ,
    "remaining_seconds":remaining_seconds ,
    "elapsed_seconds":elapsed_seconds ,
    "progress_percent":progress_percent ,
    "planned_outages":planned_outages ,
    "raw_text":text_clean ,
    "updated_at":now .isoformat ()
    }

def parse_message (text :str )->dict :
    if not text :
        return None

    text_clean =text .strip ()

    blocks =re .split (r'\r?\n\s*[-=_*]{3,}\s*\r?\n',text_clean )

    if len (blocks )==1 :
        sub_blocks =re .split (r'(?=\n(?:❗️|💡)\s*За адресою)',text_clean )
        if len (sub_blocks )>1 :
            blocks =sub_blocks

    parsed_blocks =[]
    for b in blocks :
        p =parse_single_block (b .strip ())
        if p :
            parsed_blocks .append (p )

    if not parsed_blocks :
        parsed_blocks =[parse_single_block (text_clean )]
        parsed_blocks =[p for p in parsed_blocks if p ]

    if not parsed_blocks :
        return None

    outage_blocks =[b for b in parsed_blocks if b .get ("is_outage")]
    candidate_blocks =outage_blocks if outage_blocks else parsed_blocks

    def sort_key (b ):
        return (b .get ("end_timestamp")or 0 ,b .get ("total_seconds")or 0 )

    best_block =max (candidate_blocks ,key =sort_key ).copy ()

    all_reasons =[]
    for b in candidate_blocks :
        r =b .get ("reason","").strip ()
        if r and r not in all_reasons and r !="Планові / Аварійні роботи":
            all_reasons .append (r )

    if len (all_reasons )>1 :
        best_block ["reason"]=" • ".join (all_reasons )

    planned_list =[]
    for b in parsed_blocks :
        for po in b .get ("planned_outages",[]):
            if not any (x .get ("start_timestamp")==po .get ("start_timestamp")and x .get ("end_timestamp")==po .get ("end_timestamp")for x in planned_list ):
                planned_list .append (po )

    pattern =re .compile (r'(?:💡\s*)?(?:За адресою[^\n\r]+?\.?\s*)?(?:заплановані\s+ремонтні\s+роботи|заплановано\s+відключення|планові\s+ремонтні\s+роботи).*?Час початку:\s*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}\s+\d{1,2}:\d{2})\.?\s*.*?(?:Час завершення|Час відновлення|Орієнтовний час відновлення|Орієнтовний час завершення):\s*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}\s+\d{1,2}:\d{2})',re .DOTALL |re .IGNORECASE )
    now_ts_curr =int (datetime .now (KYIV_TZ ).timestamp ())
    for pm in pattern .finditer (text_clean ):
        matched_str =pm .group (0 )
        if re .search (r"зафіксовано\s+відключення",matched_str ,re .IGNORECASE )or "❗️"in matched_str :
            continue 
        s_dt =parse_datetime (pm .group (1 ))
        e_dt =parse_datetime (pm .group (2 ))
        if s_dt and e_dt :
            s_ts =int (s_dt .timestamp ())
            e_ts =int (e_dt .timestamp ())
            if e_ts >now_ts_curr and not any (x .get ("start_timestamp")==s_ts and x .get ("end_timestamp")==e_ts for x in planned_list ):
                planned_list .append ({
                "start_time_str":s_dt .strftime ("%d.%m.%Y %H:%M"),
                "end_time_str":e_dt .strftime ("%d.%m.%Y %H:%M"),
                "start_timestamp":s_ts ,
                "end_timestamp":e_ts ,
                "reason":"Заплановані ремонтні роботи"
                })

    planned_list =[p for p in planned_list if (p .get ("end_timestamp")or 0 )>now_ts_curr ]
    planned_list .sort (key =lambda x :x .get ("start_timestamp")or 0 )
    best_block ["planned_outages"]=planned_list 
    if planned_list and best_block .get ("status")!="OFF":
        next_po =planned_list [0 ]
        best_block ["is_planned"]=True 
        best_block ["start_timestamp"]=next_po .get ("start_timestamp")
        best_block ["end_timestamp"]=next_po .get ("end_timestamp")
        best_block ["start_time_str"]=next_po .get ("start_time_str")
        best_block ["end_time_str"]=next_po .get ("end_time_str")
    else :
        best_block ["is_planned"]=False 
        if best_block .get ("end_timestamp")and best_block ["end_timestamp"]<=now_ts_curr :
            best_block ["status"]="ON"
            best_block ["is_outage"]=False 
            best_block ["reason"]="Электросеть работает в штатном режиме (время ремонтных работ завершено)"

    best_block ["raw_text"]=text_clean 
    return best_block
