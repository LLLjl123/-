#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harden_browsers.py
Layer 6: 主流浏览器 (Microsoft Edge + Google Chrome) WebRTC & DoH & 地理定位隐私加固脚本
- 管理员模式下：直接写入官方企业级组策略 (HKLM\\SOFTWARE\\Policies)，无论从哪里启动都 100% 强制生效！
- 普通用户模式下：写入浏览器 Preferences / Local State，并更新桌面安全快捷方式
- 支持 --rollback 一键移除浏览器加固策略
"""

import os
import json
import ctypes
import winreg
import argparse
import subprocess

BROWSERS = [
    {
        "name": "Microsoft Edge",
        "policy_key": r"SOFTWARE\Policies\Microsoft\Edge",
        "user_data": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data"),
        "exe_candidates": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "shortcut_name": "Microsoft Edge.lnk",
    },
    {
        "name": "Google Chrome",
        "policy_key": r"SOFTWARE\Policies\Google\Chrome",
        "user_data": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
        "exe_candidates": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "shortcut_name": "Google Chrome.lnk",
    },
]

POLICY_VALUES = [
    ("WebRtcIPHandlingPolicy", "disable_non_proxied_udp", winreg.REG_SZ),
    ("DnsOverHttpsMode", "secure", winreg.REG_SZ),
    ("DnsOverHttpsTemplates", "https://1.1.1.1/dns-query", winreg.REG_SZ),
    ("BuiltInDnsClientEnabled", 1, winreg.REG_DWORD),
    ("DefaultGeolocationSetting", 2, winreg.REG_DWORD),   # 2 = 禁止所有网站获取物理位置
    ("NetworkPredictionOptions", 2, winreg.REG_DWORD),    # 2 = 禁止后台预解析 DNS
]

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def find_exe(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def apply_enterprise_policies(browser):
    try:
        k = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, browser["policy_key"], 0, winreg.KEY_SET_VALUE)
        for name, val, typ in POLICY_VALUES:
            winreg.SetValueEx(k, name, 0, typ, val)
        winreg.CloseKey(k)
        print(f"  [+] {browser['name']}: 已写入系统组策略 (WebRTC 禁非代理 UDP / DoH 1.1.1.1 / 禁定位 / 禁预解析)")
        return True
    except Exception as e:
        print(f"  [-] {browser['name']}: 写入组策略跳过 ({e})")
        return False

def apply_user_preferences(browser):
    user_data = browser["user_data"]
    pref_path = os.path.join(user_data, "Default", "Preferences")
    local_state_path = os.path.join(user_data, "Local State")

    if os.path.exists(pref_path):
        try:
            pref = json.load(open(pref_path, "r", encoding="utf-8"))
            pref.setdefault("webrtc", {})["ip_handling_policy"] = "disable_non_proxied_udp"
            doh = pref.setdefault("dns_over_https", {})
            doh["mode"] = "secure"
            doh["templates"] = "https://1.1.1.1/dns-query"
            pref.setdefault("net", {})["network_prediction_options"] = 2
            pref.setdefault("profile", {}).setdefault("default_content_setting_values", {})["geolocation"] = 2

            with open(pref_path, "w", encoding="utf-8") as f:
                json.dump(pref, f, ensure_ascii=False, indent=2)
            print(f"  [+] {browser['name']}: 已更新 Default\\Preferences")
        except Exception as e:
            print(f"  [-] {browser['name']}: 更新 Preferences 失败 ({e})")

    if os.path.exists(local_state_path):
        try:
            ls = json.load(open(local_state_path, "r", encoding="utf-8"))
            doh = ls.setdefault("dns_over_https", {})
            doh["mode"] = "secure"
            doh["templates"] = "https://1.1.1.1/dns-query"
            ls.setdefault("async_dns", {})["enabled"] = True

            with open(local_state_path, "w", encoding="utf-8") as f:
                json.dump(ls, f, ensure_ascii=False, indent=2)
            print(f"  [+] {browser['name']}: 已更新 Local State")
        except Exception as e:
            print(f"  [-] {browser['name']}: 更新 Local State 失败 ({e})")

def create_safe_shortcut(browser, exe_path):
    desktop = os.path.expandvars(r"%USERPROFILE%\Desktop")
    lnk_path = os.path.join(desktop, browser["shortcut_name"])
    ps_cmd = f"""
$sh = New-Object -ComObject WScript.Shell
$sc = $sh.CreateShortcut('{lnk_path}')
$sc.TargetPath = '{exe_path}'
$sc.Arguments = '--force-webrtc-ip-handling-policy=disable_non_proxied_udp'
$sc.WorkingDirectory = [System.IO.Path]::GetDirectoryName('{exe_path}')
$sc.Save()
"""
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                       capture_output=True, timeout=5)
        print(f"  [+] {browser['name']}: 已更新桌面安全快捷方式 ({lnk_path})")
    except Exception as e:
        print(f"  [-] {browser['name']}: 创建桌面快捷方式失败 ({e})")

def harden_all():
    admin = is_admin()
    print("=== 正在加固已安装的主流浏览器 (Edge / Chrome) ===")
    for b in BROWSERS:
        exe = find_exe(b["exe_candidates"])
        if not exe and not os.path.exists(b["user_data"]):
            continue
        print(f"\n[*] 检测到 {b['name']}:")
        if admin:
            apply_enterprise_policies(b)
        else:
            print("  [-] 非管理员模式：将写入用户级 Preferences 与桌面快捷方式（推荐管理员运行以锁死组策略）")
        apply_user_preferences(b)
        if exe:
            create_safe_shortcut(b, exe)
    print("\n✅ 浏览器防泄露加固完成！重启浏览器（或在 edge://policy / chrome://policy 点击重新加载）即可生效。")

def rollback_all():
    admin = is_admin()
    print("=== 正在回滚浏览器加固策略 ===")
    for b in BROWSERS:
        if admin:
            try:
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, b["policy_key"], 0, winreg.KEY_SET_VALUE)
                for name, _, _ in POLICY_VALUES:
                    try:
                        winreg.DeleteValue(k, name)
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(k)
                print(f"  [+] 已清除 {b['name']} 的企业级加固组策略")
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"  [-] 清除 {b['name']} 组策略失败: {e}")
        else:
            print(f"  [!] 清除 {b['name']} 系统级组策略需要管理员权限")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="加固或回滚 Edge/Chrome 隐私与防泄露配置")
    parser.add_argument("--rollback", action="store_true", help="移除组策略回滚至默认")
    args = parser.parse_args()

    if args.rollback:
        rollback_all()
    else:
        harden_all()
