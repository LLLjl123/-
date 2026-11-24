#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
one_click_harden.py
Network Leak Shield - 面向全新 Windows 电脑的一键全链路网络安全加固总控脚本

用法示例：
  1. 仅体检，不修改任何系统设置：
     python scripts/one_click_harden.py --audit

  2. 一键全链路安全加固（推荐以管理员身份运行，按目标节点地区对齐时区/区域）：
     python scripts/one_click_harden.py --apply --region us-west

  3. 仅做网络安全加固，不修改系统时区与区域：
     python scripts/one_click_harden.py --apply --region skip

  4. 一键无损回滚至加固前默认状态：
     python scripts/one_click_harden.py --rollback
"""

import os
import sys
import ctypes
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def run_script(script_name, extra_args=None):
    path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [sys.executable, path] + (extra_args or [])
    print(f"\n>>> 执行模块: {script_name} {' '.join(extra_args or [])}", flush=True)
    print("-" * 62, flush=True)
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"[!] 模块 {script_name} 返回非零退出码: {res.returncode}", flush=True)

def main():
    parser = argparse.ArgumentParser(
        description="Network Leak Shield - 一键全链路网络隐私与防泄露加固总控脚本"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit", action="store_true", help="仅执行七层环境体检（只读，不修改系统）")
    mode.add_argument("--apply", action="store_true", help="执行一键全链路安全加固")
    mode.add_argument("--rollback", action="store_true", help="一键回滚恢复系统默认设置")

    parser.add_argument(
        "--region",
        default="skip",
        choices=["skip", "us-west", "us-east", "jp", "sg", "uk"],
        help="目标代理节点地区预设，自动对齐时区/国家/Intl区域格式，同时保留中文界面（默认 skip）"
    )
    parser.add_argument(
        "--skip-guard",
        action="store_true",
        help="加固时跳过编译和注册后台动态 DNS 看门狗任务"
    )

    args = parser.parse_args()

    print("=" * 62)
    print("  Network Leak Shield - 全链路网络防泄露一键加固引擎")
    print("=" * 62)
    print(f"当前运行权限: {'管理员 (Administrator) ✅' if is_admin() else '普通用户 (部分系统级策略需管理员权限) ⚠️'}")

    if args.audit:
        run_script("audit_environment.py")
        return

    if args.rollback:
        print("\n⚠️  正在执行一键回滚，将恢复定位服务、IPv6、DHCP DNS、浏览器策略与时区设置...")
        run_script("deploy_dns_guard.py", ["--uninstall"])
        run_script("harden_browsers.py", ["--rollback"])
        run_script("harden_windows_privacy.py", ["--rollback"])
        print("\n✅ 全部回滚操作已完成！建议重启浏览器使设置生效。")
        return

    if args.apply:
        if not is_admin():
            print("\n[!] 强烈建议右键使用「以管理员身份运行」打开终端再执行 --apply，")
            print("    否则无法写入系统级定位禁用、IPv6 解绑、DNS 组策略和浏览器企业策略。")

        # 1. Windows 系统级隐私、定位服务、IPv6、Smart DNS、LLMNR 与区域时区对齐
        run_script("harden_windows_privacy.py", ["--region", args.region])

        # 2. 编译并部署自适应物理网卡的动态 DNS 看门狗
        if not args.skip_guard:
            run_script("deploy_dns_guard.py")

        # 3. 净化主流代理客户端 (FlClash / Clash Verge 等) 订阅与补丁中的国内 DNS
        run_script("purge_clash_chinese_dns.py")

        # 4. 清除系统代理 WinINet 死代理与幽灵 PAC 脚本残留
        run_script("clean_proxy_residue.py")

        # 5. 加固 Edge & Chrome 浏览器 (WebRTC 策略 + 安全 DoH + 禁止定位)
        run_script("harden_browsers.py")

        # 6. 最终全链路验收审计
        print("\n" + "=" * 62)
        print("  加固步骤全部执行完毕，正在进行最终验收审计...")
        print("=" * 62)
        run_script("audit_environment.py")

if __name__ == "__main__":
    main()
