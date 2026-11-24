#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_dns_guard.py
编译并部署零依赖的 C# 动态 DNS 看门狗 (dns_guard.cs)
支持：
  python deploy_dns_guard.py            # 编译并安装开机自启守护进程（需管理员权限）
  python deploy_dns_guard.py --uninstall # 停止并卸载守护进程，恢复物理网卡 DHCP DNS
"""

import os
import sys
import ctypes
import shutil
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CS_SOURCE = os.path.join(SCRIPT_DIR, "dns_guard.cs")
INSTALL_DIR = os.path.expandvars(r"%ProgramData%\NetworkLeakShield")
TARGET_EXE = os.path.join(INSTALL_DIR, "dns-guard.exe")
TASK_NAME = "NetworkLeakShield_DnsGuard"

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def find_csc():
    candidates = [
        r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def install_guard():
    if not is_admin():
        print("  [!] 提示: 安装系统级 DNS 看门狗需要管理员权限（右键以管理员身份运行终端）。")
        return False

    csc = find_csc()
    if not csc:
        print("  [!] 未找到 Windows 内置 .NET 编译器 csc.exe，跳过看门狗编译。")
        return False

    if not os.path.exists(CS_SOURCE):
        print(f"  [!] 未找到源码文件: {CS_SOURCE}")
        return False

    os.makedirs(INSTALL_DIR, exist_ok=True)

    # 先停止可能正在运行的旧实例
    subprocess.run(["taskkill", "/f", "/im", "dns-guard.exe"], capture_output=True)

    print(f"  [*] 正在使用系统内置编译器编译 {os.path.basename(CS_SOURCE)} ...")
    cmd = [csc, "/nologo", "/target:winexe", "/optimize+", f"/out:{TARGET_EXE}", CS_SOURCE]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  [!] 编译失败:\n{res.stdout}\n{res.stderr}")
        return False
    print(f"  [+] 编译成功: {TARGET_EXE}")

    # 注册开机自启计划任务（最高权限静默运行）
    ps_task = f"""
$action = New-ScheduledTaskAction -Execute '{TARGET_EXE}'
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName '{TASK_NAME}'
"""
    res_task = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_task],
        capture_output=True, text=True
    )
    if res_task.returncode == 0:
        print(f"  [+] 已注册并启动系统守护任务: {TASK_NAME}")
        print("      效果: 开启 TUN 代理时自动将活跃物理网卡锁定为 1.1.1.1 / 1.0.0.1；关闭代理自动恢复 DHCP。")
        return True
    else:
        print(f"  [!] 计划任务注册失败: {res_task.stderr}")
        return False

def uninstall_guard():
    if not is_admin():
        print("  [!] 卸载系统级守护任务需要管理员权限。")
        return False

    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
         f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false -ErrorAction SilentlyContinue"],
        capture_output=True
    )
    subprocess.run(["taskkill", "/f", "/im", "dns-guard.exe"], capture_output=True)

    if os.path.exists(TARGET_EXE):
        try:
            os.remove(TARGET_EXE)
        except Exception:
            pass

    # 恢复活跃物理网卡为 DHCP DNS
    ps_restore = """
Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -notmatch 'Virtual|Hyper-V|Meta|Wintun|TUN|Bluetooth|VMware' } | ForEach-Object {
    Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses -ErrorAction SilentlyContinue
}
Clear-DnsClientCache
"""
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_restore], capture_output=True)
    print(f"  [+] 已卸载守护任务 {TASK_NAME} 并恢复物理网卡为自动获取 DNS (DHCP)。")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="编译部署或卸载动态 DNS 看门狗")
    parser.add_argument("--uninstall", action="store_true", help="卸载守护任务并恢复 DHCP DNS")
    args = parser.parse_args()

    if args.uninstall:
        uninstall_guard()
    else:
        install_guard()
