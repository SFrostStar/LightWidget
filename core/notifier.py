import sys
import subprocess
import os
import time

_BASE_DIR =os .path .dirname (os .path .dirname (os .path .abspath (__file__ )))

def _get_helper_bin ():
    candidates =[
        os .path .join (_BASE_DIR ,"core","notifier_bundle","LightWidgetNotifier.app","Contents","MacOS","notifier_bin")
    ]
    if getattr (sys ,"frozen",False ):
        exe_dir =os .path .dirname (sys .executable )
        candidates .append (os .path .join (os .path .dirname (exe_dir ),"Resources","core","notifier_bundle","LightWidgetNotifier.app","Contents","MacOS","notifier_bin"))
        meipass =getattr (sys ,"_MEIPASS","")
        if meipass :
            candidates .append (os .path .join (meipass ,"core","notifier_bundle","LightWidgetNotifier.app","Contents","MacOS","notifier_bin"))
            candidates .append (os .path .join (os .path .dirname (meipass ),"Resources","core","notifier_bundle","LightWidgetNotifier.app","Contents","MacOS","notifier_bin"))
    for p in candidates :
        if os .path .exists (p )and os .access (p ,os .X_OK ):
            return p 
    return None 

def _setup_macos_notifications ():
    pass

def send_notification (title :str ,subtitle :str ,message :str ,sound :str ="Submarine"):
    if sys .platform =="darwin":
        hbin =_get_helper_bin ()
        if hbin :
            try :
                cmd =[hbin ,str (title ),str (subtitle or ""),str (message or ""),str (sound or "")]
                subprocess .Popen (cmd ,stdout =subprocess .DEVNULL ,stderr =subprocess .DEVNULL )
                return
            except Exception :
                pass

        try :
            from Cocoa import NSApplication ,NSImage ,NSObject
            from Foundation import NSUserNotification ,NSUserNotificationCenter

            app =NSApplication .sharedApplication ()
            for name in ["ui/flat_app_icon.png","ui/AppIcon.icns"]:
                p =os .path .join (_BASE_DIR ,name )
                if os .path .exists (p ):
                    img =NSImage .alloc ().initWithContentsOfFile_ (p )
                    if img :
                        app .setApplicationIconImage_ (img )
                        break

            notification =NSUserNotification .alloc ().init ()
            notification .setTitle_ (str (title ))
            if subtitle :
                notification .setSubtitle_ (str (subtitle ))
            notification .setInformativeText_ (str (message ))
            if sound :
                notification .setSoundName_ (str (sound ))
            center =NSUserNotificationCenter .defaultUserNotificationCenter ()
            center .deliverNotification_ (notification )
            return
        except Exception :
            pass

        try :
            clean_title =str (title ).replace ('"','\\"')
            clean_sub =str (subtitle ).replace ('"','\\"')
            clean_msg =str (message ).replace ('"','\\"')
            snd_clause =f' sound name "{sound }"'if sound else ''
            script =f'display notification "{clean_msg }" with title "{clean_title }" subtitle "{clean_sub }"{snd_clause }'
            cmd =["osascript","-e",script ]
            subprocess .run (cmd ,check =False ,stdout =subprocess .DEVNULL ,stderr =subprocess .DEVNULL )
        except Exception as e :
            print (f"[Notifier] macOS error: {e }")
    elif sys .platform =="win32":
        try :
            ps_script =f'''
            [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms");
            $obj = New-Object System.Windows.Forms.NotifyIcon;
            $obj.Icon = [System.Drawing.SystemIcons]::Information;
            $obj.BalloonTipTitle = "{title }";
            $obj.BalloonTipText = "{subtitle }`n{message }";
            $obj.Visible = $True;
            $obj.ShowBalloonTip(5000);
            '''
            cmd =["powershell","-NoProfile","-NonInteractive","-Command",ps_script ]
            subprocess .run (cmd ,check =False ,stdout =subprocess .DEVNULL ,stderr =subprocess .DEVNULL )
        except Exception as e :
            print (f"[Notifier] Windows error: {e }")

send_macos_notification =send_notification


def send_sync_failure_notification (settings ):
    if not settings .get ("banner",True )or not settings .get ("macos_banner",True ):
        return None
    title ="Не удалось синхронизировать время"
    sound =(settings .get ("sound_name")or "Basso")if settings .get ("sound",True )and settings .get ("macos_sound",True )else ""
    send_macos_notification (title ,"Причина: Бот не отвечает","",sound =sound )
    return title


def send_status_notification (state ,settings ):
    if not settings .get ("banner",True )or not settings .get ("macos_banner",True ):
        return None
    now =time .time ()
    planned =[item for item in state .get ("planned_outages",[])if (item .get ("end_timestamp")or 0 )>now ]
    if not planned and state .get ("is_planned")and (state .get ("end_timestamp")or 0 )>now :
        planned =[state ]
    if state .get ("status")=="OFF"and (not state .get ("end_timestamp")or state ["end_timestamp"]>now ):
        title ="Отключение света"
        subtitle =f"Ориентировочно до {state .get ('end_time_str')or 'уточнения времени'}"
        message =(state .get ("reason")or "Отключение электроэнергии").split (" • ")[0 ][:180 ]
        default_sound ="Basso"
    elif planned :
        planned .sort (key =lambda item :item .get ("start_timestamp")or 0 )
        nearest =planned [0 ]
        title ="Плановые работы"
        subtitle =f"С {nearest .get ('start_time_str')or '?'} до {nearest .get ('end_time_str')or '?'}"
        message =f"Запланировано работ: {len (planned )}."if len (planned )>1 else "Запланированы ремонтные работы."
        default_sound ="Ping"
    else :
        title ="Свет есть"
        subtitle ="Электросеть работает в штатном режиме."
        message =""
        default_sound ="Glass"
    sound =(settings .get ("sound_name")or default_sound )if settings .get ("sound",True )and settings .get ("macos_sound",True )else ""
    send_macos_notification (title ,subtitle ,message ,sound =sound )
    return title
