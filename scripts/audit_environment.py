#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_environment.py
Network Leak Shield - 七层全链路网络隐私与防泄露风险审计脚本
"""

import os
import json
import socket
import winreg
import urllib.request
import subprocess

def print_section(title):
    print("\n" + "=" * 62)
    print(f" {title}")
    print("=" * 62)

def run_ps(cmd):
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def read_reg(hive, path, name):
    try:
        k = winreg.OpenKey(hive, path)
        val, _ = winreg.QueryValueEx(k, name)
        winreg.CloseKey(k)
        return val
    except Exception:
        return None

def audit_windows_privacy():
    print_section("1. Windows 系统定位、隐私与时区区域检查")
    loc_lm = read_reg(winreg.HKEY_LOCAL_MACHINE,
                      r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location", "Value")
    loc_cu = read_reg(winreg.HKEY_CURRENT_USER,
                      r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location", "Value")
    loc_pol = read_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "DisableLocation")
    lfsvc_status = run_ps("(Get-Service -Name lfsvc -ErrorAction SilentlyContinue) | ForEach-Object { \"$($_.Status) ($($_.StartType))\" }")

    if loc_lm == "Deny" or loc_pol == 1:
        print(f"  [+] 系统定位服务: 已禁止 (HKLM={loc_lm}, HKCU={loc_cu}, Policy={loc_pol}, lfsvc={lfsvc_status})")
    else:
        print(f"  [!] 警告: 系统定位服务未关闭 (HKLM={loc_lm}, HKCU={loc_cu}, lfsvc={lfsvc_status})")

    ad_id = read_reg(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled")
    tailored = read_reg(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy", "TailoredExperiencesWithDiagnosticDataEnabled")
    print(f"  [{'+' if ad_id == 0 else '-'}] 广告 ID (AdvertisingInfo): {'已关闭 (0)' if ad_id == 0 else ad_id}")
    print(f"  [{'+' if tailored == 0 else '-'}] 诊断定制体验: {'已关闭 (0)' if tailored == 0 else tailored}")

    tz = run_ps("(Get-TimeZone).Id")
    home = run_ps("(Get-WinHomeLocation).HomeLocation")
    culture = run_ps("(Get-Culture).Name")
    sys_locale = run_ps("(Get-WinSystemLocale).Name")
    print(f"  [*] 当前系统时区: {tz}")
    print(f"  [*] 国家/地区: {home} | 区域格式 (Intl): {culture} | 非 Unicode 语言: {sys_locale}")

def audit_ipv6():
    print_section("2. IPv6 旁路与网卡协议绑定状态")
    out = run_ps("Get-NetAdapterBinding -ComponentID ms_tcpip6 | Select-Object Name, Enabled | Format-Table -AutoSize")
    print(out)

    has_ipv6_outbound = False
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("2606:4700:4700::1111", 53))
        has_ipv6_outbound = True
        s.close()
    except Exception:
        pass

    if has_ipv6_outbound:
        print("  [!] 警告: 本机可直接建立公网 IPv6 连接，存在 IPv6 旁路泄露风险！")
    else:
        print("  [+] 安全: 外部 IPv6 套接字连接已完全阻断/不可达。")

def audit_dns():
    print_section("3. DNS 解析栈、多宿主策略与实时泄露探测")
    print(run_ps("Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object { $_.ServerAddresses.Count -gt 0 } | Format-Table InterfaceAlias, ServerAddresses -AutoSize"))

    smart = read_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient", "DisableSmartNameResolution")
    llmnr = read_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient", "EnableMulticast")
    print(f"  [{'+' if smart == 1 else '!'}] 禁用并发多宿主解析 (DisableSmartNameResolution): {smart}")
    print(f"  [{'+' if llmnr == 0 else '-'}] 禁用 LLMNR 局域网广播 (EnableMulticast=0): {llmnr}")

    guard_out = run_ps("Get-Process dns-guard -ErrorAction SilentlyContinue | Format-Table Id, ProcessName")
    print(f"  [{'+' if 'dns-guard' in guard_out else '-'}] 后台看门狗 (dns-guard): {'运行中' if 'dns-guard' in guard_out else '未运行'}")

    print("\n--- 实时公网 DNS 出口探测 (edns.ip-api.com) ---")
    try:
        req = urllib.request.Request("https://edns.ip-api.com/json", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            dns_ip = data.get("dns", {}).get("ip", "未知")
            dns_geo = data.get("dns", {}).get("geo", "未知")
            print(f"  探测到的 DNS 出口 IP: {dns_ip}")
            print(f"  DNS 地理归属地:      {dns_geo}")
            if "China" in dns_geo or "CN" in dns_geo:
                print("  [!] 严重警告: 检测到国内 DNS 泄露！")
            else:
                print("  [+] 验证通过: DNS 解析出口位于海外纯净节点。")
    except Exception as e:
        print(f"  [-] 实时探测失败: {e}")

def audit_proxy_residue():
    print_section("4. 系统代理 (WinINet) 与幽灵 PAC 残留检查")
    proxy_enable = read_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", "ProxyEnable")
    proxy_server = read_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", "ProxyServer") or ""
    autoconfig = read_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", "AutoConfigURL") or ""
    print(f"  ProxyEnable: {proxy_enable} | ProxyServer: '{proxy_server}' | AutoConfigURL: '{autoconfig}'")

    raw_val = read_reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings\Connections", "DefaultConnectionSettings")
    has_pac = bool(raw_val and "pac" in raw_val.decode("latin1", errors="ignore").lower())
    if has_pac or autoconfig:
        print("  [!] 警告: 发现残留 PAC 脚本，可能导致 Steam/应用断网！")
    else:
        print("  [+] 状态正常: WinINet 代理协议栈干净无死锁。")

def audit_clash_configs():
    print_section("5. 代理客户端 (FlClash / Clash) 国内 DNS 扫描")
    bases = [
        os.path.expandvars(r"%APPDATA%\com.follow\clash"),
        os.path.expandvars(r"%APPDATA%\io.github.clash-verge-rev.clash-verge-rev"),
        os.path.expandvars(r"%APPDATA%\clash-verge"),
        os.path.expandvars(r"%APPDATA%\clash-nyanpasu"),
        os.path.expandvars(r"%APPDATA%\mihomo-party"),
    ]
    bad_keywords = ["doh.pub", "223.5.5.5", "223.6.6.6", "119.29", "180.76", "114.114.114.114"]
    found_any = False
    for b in bases:
        if not os.path.exists(b):
            continue
        for root, _, files in os.walk(b):
            for f in files:
                if f.endswith((".yaml", ".yml", ".json")):
                    full_p = os.path.join(root, f)
                    try:
                        txt = open(full_p, "r", encoding="utf-8", errors="ignore").read()
                        for kw in bad_keywords:
                            if kw in txt:
                                print(f"  [!] 在 {os.path.relpath(full_p, b)} 中发现国内 DNS: {kw}")
                                found_any = True
                                break
                    except Exception:
                        pass
    if not found_any:
        print("  [+] 已检测的代理配置文件均未包含国内公共 DNS。")

def audit_browsers():
    print_section("6. 主流浏览器 (Edge / Chrome) WebRTC & DoH 策略检查")
    checks = [
        ("Microsoft Edge", r"SOFTWARE\Policies\Microsoft\Edge", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Preferences")),
        ("Google Chrome", r"SOFTWARE\Policies\Google\Chrome", os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Preferences")),
    ]
    for name, pol_key, pref_path in checks:
        pol_webrtc = read_reg(winreg.HKEY_LOCAL_MACHINE, pol_key, "WebRtcIPHandlingPolicy")
        pol_doh = read_reg(winreg.HKEY_LOCAL_MACHINE, pol_key, "DnsOverHttpsMode")
        pref_webrtc = None
        pref_doh = None
        if os.path.exists(pref_path):
            try:
                p = json.load(open(pref_path, "r", encoding="utf-8"))
                pref_webrtc = p.get("webrtc", {}).get("ip_handling_policy")
                pref_doh = p.get("dns_over_https", {}).get("mode")
            except Exception:
                pass
        if pol_webrtc or pref_webrtc or os.path.exists(pref_path):
            webrtc_ok = (pol_webrtc == "disable_non_proxied_udp" or pref_webrtc == "disable_non_proxied_udp")
            doh_ok = (pol_doh == "secure" or pref_doh == "secure")
            print(f"  [{name}]")
            print(f"    [{'+' if webrtc_ok else '!'}] WebRTC 策略: Policy={pol_webrtc}, Pref={pref_webrtc}")
            print(f"    [{'+' if doh_ok else '!'}] 安全 DoH 策略: Policy={pol_doh}, Pref={pref_doh}")

if __name__ == "__main__":
    print("\n🔍 正在执行 Network Leak Shield 七层全链路安全审计...")
    audit_windows_privacy()
    audit_ipv6()
    audit_dns()
    audit_proxy_residue()
    audit_clash_configs()
    audit_browsers()
    print("\n" + "=" * 62)
    print(" 审计完成。如需一键全自动加固，请以管理员身份运行:")
    print("   python scripts/one_click_harden.py --apply --region us-west")
    print("=" * 62 + "\n")
