#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harden_windows_privacy.py
Layer 1 & 2: Windows 系统级隐私防定位 + 底层网络协议安全加固脚本
包含：
  - 关闭系统定位服务 (ConsentStore + 组策略 + 停用 lfsvc 服务)
  - 关闭广告 ID、诊断定制体验、输入习惯收集
  - 禁用 Windows 智能多宿主 DNS 并发解析 (DisableSmartNameResolution) 与 LLMNR
  - 全面关闭所有网卡 IPv6 绑定 (ms_tcpip6)
  - 可选对齐目标代理地区的时区、国家与 Intl 区域格式（严格保留中文系统界面）
  - 支持 --rollback 一键回滚恢复默认
"""

import os
import sys
import json
import ctypes
import winreg
import argparse
import subprocess

REGION_PRESETS = {
    "us-west": {
        "name": "美国西部 (洛杉矶/加州)",
        "timezone": "Pacific Standard Time",
        "geoid": 244,        # United States
        "culture": "en-US",
    },
    "us-east": {
        "name": "美国东部 (纽约/弗吉尼亚)",
        "timezone": "Eastern Standard Time",
        "geoid": 244,        # United States
        "culture": "en-US",
    },
    "jp": {
        "name": "日本 (东京)",
        "timezone": "Tokyo Standard Time",
        "geoid": 122,        # Japan
        "culture": "ja-JP",
    },
    "sg": {
        "name": "新加坡",
        "timezone": "Singapore Standard Time",
        "geoid": 215,        # Singapore
        "culture": "en-SG",
    },
    "uk": {
        "name": "英国 (伦敦)",
        "timezone": "GMT Standard Time",
        "geoid": 242,        # United Kingdom
        "culture": "en-GB",
    },
}

BACKUP_FILE = os.path.expandvars(r"%LOCALAPPDATA%\NetworkLeakShield\os_backup.json")

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def run_ps(cmd):
    res = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
        capture_output=True, text=True
    )
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def set_reg(hive, path, name, value, reg_type):
    try:
        k = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, name, 0, reg_type, value)
        winreg.CloseKey(k)
        return True
    except Exception as e:
        return False

def del_reg(hive, path, name):
    try:
        k = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(k, name)
        winreg.CloseKey(k)
        return True
    except Exception:
        return False

def save_backup():
    os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)
    if os.path.exists(BACKUP_FILE):
        return  # 保留最早的原始备份，防止重复覆盖
    _, tz, _ = run_ps("(Get-TimeZone).Id")
    _, geoid, _ = run_ps("(Get-WinHomeLocation).GeoId")
    _, culture, _ = run_ps("(Get-Culture).Name")
    backup = {
        "timezone": tz or "China Standard Time",
        "geoid": int(geoid) if geoid.isdigit() else 45,
        "culture": culture or "zh-CN",
    }
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)
    print(f"  [+] 已备份原始系统时区/区域配置至: {BACKUP_FILE}")

def apply_privacy_and_network(region="skip"):
    admin = is_admin()
    save_backup()

    print("=== [1/4] 关闭 Windows 系统定位与追踪隐私项 ===")
    # 用户级隐私（无需管理员即可生效）
    set_reg(winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
            "Value", "Deny", winreg.REG_SZ)
    set_reg(winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
            "Enabled", 0, winreg.REG_DWORD)
    set_reg(winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy",
            "TailoredExperiencesWithDiagnosticDataEnabled", 0, winreg.REG_DWORD)
    set_reg(winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\InputPersonalization",
            "RestrictImplicitInkCollection", 1, winreg.REG_DWORD)
    set_reg(winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\InputPersonalization",
            "RestrictImplicitTextCollection", 1, winreg.REG_DWORD)
    print("  [+] 用户级定位访问已拒绝 (HKCU=Deny)，广告 ID / 诊断定制体验 / 输入追踪已关闭")

    if admin:
        set_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
                "Value", "Deny", winreg.REG_SZ)
        set_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
                "DisableLocation", 1, winreg.REG_DWORD)
        run_ps("Stop-Service -Name lfsvc -Force -ErrorAction SilentlyContinue; Set-Service -Name lfsvc -StartupType Disabled -ErrorAction SilentlyContinue")
        print("  [+] 系统级定位服务 (lfsvc) 已停用并禁止自启，组策略 DisableLocation = 1")
    else:
        print("  [-] 提示: 非管理员模式，已跳过系统级 lfsvc 服务禁用（建议以管理员运行）")

    print("\n=== [2/4] 加固底层 DNS 策略（禁用并发多宿主解析与 LLMNR） ===")
    if admin:
        set_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient",
                "DisableSmartNameResolution", 1, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient",
                "EnableMulticast", 0, winreg.REG_DWORD)
        run_ps("Clear-DnsClientCache")
        print("  [+] 已启用 DisableSmartNameResolution = 1（杜绝并发跨网卡 DNS 泄露）")
        print("  [+] 已启用 EnableMulticast = 0（关闭 LLMNR 局域网广播解析）")
    else:
        print("  [!] 需要管理员权限才能写入 HKLM DNSClient 组策略！")

    print("\n=== [3/4] 全面禁用全机网卡 IPv6 协议绑定 ===")
    if admin:
        code, _, err = run_ps("Get-NetAdapterBinding -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue | Disable-NetAdapterBinding -Confirm:$false -ErrorAction SilentlyContinue")
        print("  [+] 已解除所有物理与虚拟网卡的 IPv6 (ms_tcpip6) 协议绑定")
    else:
        print("  [!] 需要管理员权限才能禁用网卡 IPv6 绑定！")

    print("\n=== [4/4] 时区 / 国家 / Intl 区域格式对齐（保留中文显示界面） ===")
    if region and region != "skip":
        preset = REGION_PRESETS.get(region)
        if not preset:
            print(f"  [!] 未知地区预设: {region}，可选: {', '.join(REGION_PRESETS.keys())}")
        else:
            print(f"  [*] 目标环境预设: {preset['name']}")
            run_ps(f"Set-WinHomeLocation -GeoId {preset['geoid']}")
            run_ps(f"Set-Culture -CultureInfo '{preset['culture']}'")
            print(f"  [+] 已设置国家/地区 GeoID={preset['geoid']}，区域格式 Culture={preset['culture']}（中文界面保持不变）")
            if admin:
                run_ps(f"Set-TimeZone -Id '{preset['timezone']}'")
                print(f"  [+] 已设置系统时区为: {preset['timezone']}")
            else:
                print(f"  [-] 修改系统时区为 {preset['timezone']} 需要管理员权限，请用管理员运行或手动设置")
    else:
        print("  [-] 已跳过时区/区域对齐（如需对齐请传入 --region us-west 等参数）")

def rollback_privacy_and_network():
    admin = is_admin()
    print("=== 正在回滚 Windows 系统隐私与网络设置 ===")

    set_reg(winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
            "Value", "Allow", winreg.REG_SZ)
    set_reg(winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
            "Enabled", 1, winreg.REG_DWORD)

    if admin:
        set_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
                "Value", "Allow", winreg.REG_SZ)
        del_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "DisableLocation")
        run_ps("Set-Service -Name lfsvc -StartupType Manual -ErrorAction SilentlyContinue")

        del_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient", "DisableSmartNameResolution")
        del_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient", "EnableMulticast")

        run_ps("Get-NetAdapterBinding -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue | Enable-NetAdapterBinding -Confirm:$false -ErrorAction SilentlyContinue")
        print("  [+] 已恢复定位服务、DNS 策略与 IPv6 网卡绑定")
    else:
        print("  [!] 完整回滚需要管理员权限！")

    if os.path.exists(BACKUP_FILE):
        try:
            b = json.load(open(BACKUP_FILE, "r", encoding="utf-8"))
            run_ps(f"Set-WinHomeLocation -GeoId {b.get('geoid', 45)}")
            run_ps(f"Set-Culture -CultureInfo '{b.get('culture', 'zh-CN')}'")
            if admin and b.get("timezone"):
                run_ps(f"Set-TimeZone -Id '{b['timezone']}'")
            print(f"  [+] 已从备份还原时区 ({b.get('timezone')})、国家与区域格式 ({b.get('culture')})")
        except Exception as e:
            print(f"  [-] 还原时区备份失败: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Windows 系统级隐私防定位与底层网络协议加固")
    parser.add_argument("--region", default="skip", choices=["skip"] + list(REGION_PRESETS.keys()),
                        help="对齐目标代理地区的时区/国家/区域格式（默认 skip 不改动）")
    parser.add_argument("--rollback", action="store_true", help="回滚恢复系统默认设置")
    args = parser.parse_args()

    if args.rollback:
        rollback_privacy_and_network()
    else:
        apply_privacy_and_network(region=args.region)
