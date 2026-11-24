#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_proxy_residue.py
彻底清除 Windows 注册表中的死代理、幽灵 PAC 脚本，解决加速器关闭后 Steam/浏览器断网问题
"""

import os
import sys
import time
import winreg
import ctypes
import shutil
import subprocess

def clean_wininet():
    print("=== 正在清理 WinINet 系统代理与 PAC 残留 ===")
    
    # 1. 清理 HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )
        try:
            winreg.DeleteValue(key, "AutoConfigURL")
            print("  [+] 已删除注册表 AutoConfigURL (PAC 脚本)")
        except FileNotFoundError:
            pass
        
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")
        winreg.CloseKey(key)
        print("  [+] 已重置 ProxyEnable = 0, ProxyServer = ''")
    except Exception as e:
        print(f"  [!] 更新 Internet Settings 失败: {e}")

    # 2. 重置 Connections 下的 DefaultConnectionSettings 与 SavedLegacySettings
    # 二进制结构：01 代表直连，无代理服务器，无 PAC 脚本
    clean_conn_bytes = bytearray([
        0x46, 0x00, 0x00, 0x00,  # 结构头大小
        0x00, 0x00, 0x00, 0x00,  # 计数器
        0x01, 0x00, 0x00, 0x00,  # 标志位: 01 = Direct Connection
        0x00, 0x00, 0x00, 0x00,  # 代理服务器字符串长度 = 0
        0x00, 0x00, 0x00, 0x00   # 代理绕过名单长度 = 0
    ])

    try:
        conn_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings\Connections",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(conn_key, "DefaultConnectionSettings", 0, winreg.REG_BINARY, clean_conn_bytes)
        winreg.SetValueEx(conn_key, "SavedLegacySettings", 0, winreg.REG_BINARY, clean_conn_bytes)
        winreg.CloseKey(conn_key)
        print("  [+] 已重置 DefaultConnectionSettings 与 SavedLegacySettings 为干净直连模式")
    except Exception as e:
        print(f"  [!] 更新 Connections 失败: {e}")

    # 3. 广播刷新 WinINet 协议栈
    try:
        INTERNET_OPTION_SETTINGS_CHANGED = 39
        INTERNET_OPTION_REFRESH = 37
        wininet = ctypes.windll.wininet
        wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
        print("  [+] 已向操作系统广播通知网络设置已生效")
    except Exception as e:
        print(f"  [!] 广播刷新失败: {e}")

    # 4. 刷新 DNS 缓存
    try:
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=5)
        print("  [+] 已刷新 Windows 本地 DNS 缓存")
    except Exception as e:
        print(f"  [!] 刷新 DNS 失败: {e}")

def clean_steam_cache():
    print("\n=== 正在检查 Steam 浏览器缓存 ===")
    steam_cache = os.path.expandvars(r"%LOCALAPPDATA%\Steam\htmlcache")
    if os.path.exists(steam_cache):
        try:
            # 尝试终结死锁的 webhelper
            subprocess.run(["taskkill", "/f", "/im", "steamwebhelper.exe"], capture_output=True)
            time.sleep(1)
            shutil.rmtree(steam_cache)
            print("  [+] 成功清理 Steam CEF 网页缓存 (htmlcache)")
        except Exception as e:
            print(f"  [-] 清理 Steam 缓存提示: {e} (若正在使用 Steam 可忽略)")

if __name__ == "__main__":
    clean_wininet()
    clean_steam_cache()
    print("\n✅ 清理完成！死代理与 PAC 脚本已彻底移出系统。")
