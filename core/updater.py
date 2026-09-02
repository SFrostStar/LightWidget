import os
import sys
import json
import ssl
import shutil
import tempfile
import subprocess
import urllib .request
import urllib .error
from datetime import datetime

class UpdateManager :
    def __init__ (self ):
        self .base_dir =os .path .dirname (os .path .dirname (os .path .abspath (__file__ )))
        self .repo_name =self ._detect_repo_name ()

    def _detect_repo_name (self )->str :
        try :
            cmd =["git","remote","get-url","origin"]
            res =subprocess .run (cmd ,cwd =self .base_dir ,capture_output =True ,text =True )
            if res .returncode ==0 and res .stdout .strip ():
                url =res .stdout .strip ()
                if "github.com"in url :
                    part =url .split ("github.com")[-1 ].lstrip ("/:")
                    if part .endswith (".git"):
                        part =part [:-4 ]
                    if "/"in part :
                        return part
        except Exception :
            pass
        return "SFrostStar/LightWidget"

    def _parse_version (self ,v_str :str )->tuple :
        if not v_str :
            return (0 ,0 ,0 )
        cleaned =v_str .strip ().lower ().lstrip ("v")

        parts =[]
        for p in cleaned .split ("."):
            num =""
            for ch in p :
                if ch .isdigit ():
                    num +=ch
                else :
                    break
            parts .append (int (num )if num else 0 )
        while len (parts )<3 :
            parts .append (0 )
        return tuple (parts [:3 ])

    def _format_version (self ,v_tuple :tuple )->str :
        return f"{v_tuple [0 ]}.{v_tuple [1 ]}.{v_tuple [2 ]}"

    def get_local_version (self )->dict :
        v_paths =[
        os .path .join (self .base_dir ,"version.json"),
        os .path .join (getattr (sys ,'_MEIPASS',self .base_dir ),"version.json"),
        os .path .dirname (self .base_dir )if not os .path .exists (os .path .join (self .base_dir ,"version.json"))else self .base_dir
        ]
        ver_str ="2.3.2"
        msg_str ="LightWidget Release 2.3.2"
        date_str ="2026-08-17"

        for vp in [os .path .join (self .base_dir ,"version.json"),os .path .join (getattr (sys ,'_MEIPASS',self .base_dir ),"version.json")]:
            if os .path .exists (vp ):
                try :
                    with open (vp ,"r",encoding ="utf-8")as f :
                        vdata =json .load (f )
                        ver_str =str (vdata .get ("version","2.3.2"))
                        msg_str =vdata .get ("message","LightWidget Release 2.3.2")
                        date_str =vdata .get ("date","2026-08-17")
                        break
                except Exception :
                    pass

        v_tuple =self ._parse_version (ver_str )
        formatted_ver =self ._format_version (v_tuple )

        return {
        "version":formatted_ver ,
        "display":f"Версия {formatted_ver }",
        "tag":f"v{formatted_ver }",
        "message":msg_str ,
        "date":date_str
        }

    def check_updates (self )->dict :
        local_info =self .get_local_version ()
        local_v_tuple =self ._parse_version (local_info ["version"])

        headers ={
        "User-Agent":"LightWidget-AutoUpdater/1.0",
        "Accept":"application/vnd.github.v3+json"
        }

        try :
            ctx =ssl .create_default_context ()
        except Exception :
            ctx =ssl ._create_unverified_context ()

        releases_list =[]
        url =f"https://api.github.com/repos/{self .repo_name }/releases"
        try :
            req =urllib .request .Request (url ,headers =headers )
            try :
                with urllib .request .urlopen (req ,context =ctx ,timeout =7 )as response :
                    if response .status ==200 :
                        releases_list =json .loads (response .read ().decode ('utf-8'))
            except Exception :
                uctx =ssl ._create_unverified_context ()
                with urllib .request .urlopen (req ,context =uctx ,timeout =7 )as response :
                    if response .status ==200 :
                        releases_list =json .loads (response .read ().decode ('utf-8'))
        except Exception as e :
            print (f"[Updater] Releases fetch error: {e }")

        if not releases_list or not isinstance (releases_list ,list ):
            return {
            "success":False ,
            "error":"Не удалось получить список релизов с GitHub",
            "local":local_info ,
            "has_update":False
            }

        valid_releases =[r for r in releases_list if not r .get ("draft",False )and r .get ("tag_name")!="main"]
        if not valid_releases :
            valid_releases =[r for r in releases_list if not r .get ("draft",False )]

        if not valid_releases :
            return {
            "success":True ,
            "has_update":False ,
            "local":local_info ,
            "message":"Релизы не найдены"
            }

        latest_rel =valid_releases [0 ]
        remote_tag =latest_rel .get ("tag_name","")
        remote_title =latest_rel .get ("name",remote_tag )
        remote_body =latest_rel .get ("body","").strip ()
        published_date =latest_rel .get ("published_at","")
        html_url =latest_rel .get ("html_url",f"https://github.com/{self .repo_name }/releases")

        assets =latest_rel .get ("assets",[])
        download_url =None
        for a in assets :
            name =a .get ("name","").lower ()
            if sys .platform =="win32"and name .endswith (".exe"):
                download_url =a .get ("browser_download_url")
                break
            elif sys .platform =="darwin"and (name .endswith (".dmg")or name .endswith (".zip")):
                download_url =a .get ("browser_download_url")
                break

        remote_v_tuple =self ._parse_version (remote_tag )
        remote_version_str =self ._format_version (remote_v_tuple )
        has_update =bool (remote_tag and remote_v_tuple >local_v_tuple )

        return {
        "success":True ,
        "has_update":has_update ,
        "local":local_info ,
        "remote":{
        "version":remote_version_str ,
        "tag":remote_tag ,
        "title":remote_title ,
        "message":remote_body or f"Новый релиз {remote_version_str }",
        "date":published_date ,
        "url":html_url ,
        "download_url":download_url
        }
        }

    def pull_update (self )->dict :
        is_frozen =getattr (sys ,'frozen',False )

        if not is_frozen and os .path .exists (os .path .join (self .base_dir ,".git")):
            try :
                fetch_cmd =["git","fetch","--all"]
                subprocess .run (fetch_cmd ,cwd =self .base_dir ,capture_output =True ,text =True ,check =True )

                pull_cmd =["git","pull","--no-rebase","origin","main"]
                res =subprocess .run (pull_cmd ,cwd =self .base_dir ,capture_output =True ,text =True ,check =True )

                new_local =self .get_local_commit ()
                return {
                "success":True ,
                "output":res .stdout ,
                "new_commit":new_local
                }
            except subprocess .CalledProcessError as e :
                err_msg =e .stderr or e .stdout or str (e )
                return {
                "success":False ,
                "error":f"Ошибка git pull: {err_msg }"
                }
            except Exception as e :
                return {
                "success":False ,
                "error":str (e )
                }

        try :
            headers ={"User-Agent":"LightWidget-AutoUpdater/1.0"}
            url =f"https://api.github.com/repos/{self .repo_name }/releases/latest"
            req =urllib .request .Request (url ,headers =headers )
            uctx =ssl ._create_unverified_context ()
            with urllib .request .urlopen (req ,context =uctx ,timeout =8 )as resp :
                rel_data =json .loads (resp .read ().decode ('utf-8'))

            assets =rel_data .get ("assets",[])
            download_url =None
            for a in assets :
                name =a .get ("name","").lower ()
                if sys .platform =="win32"and name .endswith (".exe"):
                    download_url =a .get ("browser_download_url")
                    break
                elif sys .platform =="darwin"and (name .endswith (".dmg")or name .endswith (".zip")):
                    download_url =a .get ("browser_download_url")
                    break

            if download_url :
                temp_dir =tempfile .gettempdir ()
                ext =".exe"if sys .platform =="win32"else ".dmg"
                target_file =os .path .join (temp_dir ,f"LightWidget_update{ext }")
                req2 =urllib .request .Request (download_url ,headers =headers )
                with urllib .request .urlopen (req2 ,context =uctx ,timeout =60 )as r ,open (target_file ,"wb")as f :
                    f .write (r .read ())

                if sys .platform =="darwin"and target_file .endswith (".dmg"):
                    mount_dir =os .path .join (temp_dir ,"lw_dmg_mount")
                    os .makedirs (mount_dir ,exist_ok =True )
                    subprocess .run (["hdiutil","detach",mount_dir ,"-force"],capture_output =True )
                    m_res =subprocess .run (["hdiutil","attach",target_file ,"-nobrowse","-mountpoint",mount_dir ],capture_output =True ,text =True )
                    if m_res .returncode ==0 :
                        src_app =os .path .join (mount_dir ,"LightWidget.app")
                        dest_app =os .path .join (temp_dir ,"LightWidget_New.app")
                        if os .path .exists (src_app ):
                            if os .path .exists (dest_app ):
                                shutil .rmtree (dest_app ,ignore_errors =True )
                            shutil .copytree (src_app ,dest_app ,symlinks =True )
                        subprocess .run (["hdiutil","detach",mount_dir ,"-force"],capture_output =True )

                return {
                "success":True ,
                "downloaded_file":target_file ,
                "is_binary":True
                }
        except Exception as be :
            print (f"[Updater] Release asset download note: {be }")

        return {
        "success":True ,
        "message":"Обновление готово к применению"
        }

    def restart_application (self ):
        try :
            temp_dir =tempfile .gettempdir ()
            if sys .platform =="darwin":
                new_app =os .path .join (temp_dir ,"LightWidget_New.app")
                dmg_file =os .path .join (temp_dir ,"LightWidget_update.dmg")
                exe_path =sys .executable
                app_bundle =None
                if ".app"in exe_path :
                    app_bundle =exe_path .split (".app")[0 ]+".app"
                if not app_bundle :
                    for ap in ["/Applications/LightWidget.app",os .path .expanduser ("~/Desktop/LightWidget.app"),os .path .join (self .base_dir ,"LightWidget.app")]:
                        if os .path .exists (ap ):
                            app_bundle =ap
                            break

                if app_bundle and os .path .exists (new_app ):
                    swap_sh =f"""#!/bin/bash
sleep 1.2
rm -rf "{app_bundle }"
cp -R "{new_app }" "{app_bundle }"
rm -rf "{new_app }"
open -n "{app_bundle }"
rm -f "$0"
"""
                    sh_path =os .path .join (temp_dir ,"lw_swap.sh")
                    with open (sh_path ,"w",encoding ="utf-8")as f :
                        f .write (swap_sh )
                    os .chmod (sh_path ,0o755 )
                    subprocess .Popen (["/bin/bash",sh_path ],stdout =subprocess .DEVNULL ,stderr =subprocess .DEVNULL ,start_new_session =True )
                    os ._exit (0 )
                elif os .path .exists (dmg_file ):
                    subprocess .Popen (["open",dmg_file ],stdout =subprocess .DEVNULL ,stderr =subprocess .DEVNULL )
                    os ._exit (0 )
                elif app_bundle :
                    subprocess .Popen (["open","-n",app_bundle ],stdout =subprocess .DEVNULL ,stderr =subprocess .DEVNULL )
                    os ._exit (0 )

            elif sys .platform =="win32":
                update_file =os .path .join (temp_dir ,"LightWidget_update.exe")
                exe_path =sys .executable
                if os .path .exists (update_file )and exe_path .lower ().endswith (".exe"):
                    bat_script =f"""@echo off
timeout /t 2 /nobreak > NUL
move /y "{update_file }" "{exe_path }"
start "" "{exe_path }"
del "%~f0"
"""
                    bat_path =os .path .join (temp_dir ,"update_swap.bat")
                    with open (bat_path ,"w")as f :
                        f .write (bat_script )
                    creation_flag =getattr (subprocess ,'CREATE_NO_WINDOW',0x08000000 )
                    subprocess .Popen (["cmd.exe","/c",bat_path ],shell =True ,creationflags =creation_flag )
                    os ._exit (0 )
                elif exe_path .lower ().endswith (".exe"):
                    creation_flag =getattr (subprocess ,'CREATE_NO_WINDOW',0x08000000 )
                    subprocess .Popen ([exe_path ],creationflags =creation_flag )
                    os ._exit (0 )

            python =sys .executable
            app_py =os .path .join (self .base_dir ,"app.py")
            if sys .platform =="win32":
                creation_flag =getattr (subprocess ,'CREATE_NO_WINDOW',0x08000000 )
                subprocess .Popen ([python ,app_py ],cwd =self .base_dir ,creationflags =creation_flag )
            else :
                subprocess .Popen (
                [python ,app_py ],
                cwd =self .base_dir ,
                stdin =subprocess .DEVNULL ,
                stdout =subprocess .DEVNULL ,
                stderr =subprocess .DEVNULL ,
                start_new_session =True
                )
            os ._exit (0 )
        except Exception as e :
            print (f"[Updater] Restart error: {e }")
            os ._exit (0 )
