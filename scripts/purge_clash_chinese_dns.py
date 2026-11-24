#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
purge_clash_chinese_dns.py
Layer 4: 自动扫描并净化主流代理客户端 (FlClash / Clash Verge Rev / Clash Nyanpasu / Mihomo Party)
配置文件、订阅 Profile 及内部 GUI 覆写补丁中混入的国内公共 DNS
"""

import os
import json

def clean_flclash_patch():
    pref_path = os.path.expandvars(r"%APPDATA%\com.follow\clash\shared_preferences.json")
    if not os.path.exists(pref_path):
        return
    try:
        data = json.load(open(pref_path, "r", encoding="utf-8"))
        cfg_raw = data.get("flutter.config")
        if not cfg_raw:
            return
        cfg = json.loads(cfg_raw)
        if "patchClashConfig" in cfg and "dns" in cfg["patchClashConfig"]:
            dns = cfg["patchClashConfig"]["dns"]
            dns["default-nameserver"] = ["1.1.1.1", "8.8.8.8"]
            dns["nameserver"] = [
                "https://1.1.1.1/dns-query",
                "https://1.0.0.1/dns-query",
                "https://dns.google/dns-query",
            ]
            dns["proxy-server-nameserver"] = ["https://1.1.1.1/dns-query"]
            dns["nameserver-policy"] = {}
            cfg["patchClashConfig"]["dns"] = dns

            data["flutter.config"] = json.dumps(cfg)
            with open(pref_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            print("  [+] 已成功净化 FlClash 内部 patchClashConfig GUI 覆写补丁！")
    except Exception as e:
        print(f"  [!] 处理 shared_preferences.json 失败: {e}")

def clean_yaml_files():
    search_dirs = [
        os.path.expandvars(r"%APPDATA%\com.follow\clash"),
        os.path.expandvars(r"%APPDATA%\com.follow\clash\profiles"),
        os.path.expandvars(r"%APPDATA%\io.github.clash-verge-rev.clash-verge-rev"),
        os.path.expandvars(r"%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles"),
        os.path.expandvars(r"%APPDATA%\clash-verge"),
        os.path.expandvars(r"%APPDATA%\clash-verge\profiles"),
        os.path.expandvars(r"%LOCALAPPDATA%\clash-verge-rev"),
        os.path.expandvars(r"%LOCALAPPDATA%\clash-verge-rev\profiles"),
        os.path.expandvars(r"%APPDATA%\clash-nyanpasu"),
        os.path.expandvars(r"%APPDATA%\clash-nyanpasu\profiles"),
        os.path.expandvars(r"%APPDATA%\mihomo-party"),
        os.path.expandvars(r"%APPDATA%\mihomo-party\profiles"),
    ]

    replacements = [
        ("https://doh.pub/dns-query", "https://1.1.1.1/dns-query"),
        ("https://dns.alidns.com/dns-query", "https://dns.google/dns-query"),
        ("https://223.5.5.5/dns-query", "https://1.0.0.1/dns-query"),
        ("https://223.6.6.6/dns-query", "https://1.0.0.1/dns-query"),
        ("tls://223.5.5.5:853", "tls://1.1.1.1:853"),
        ("tls://dot.pub:853", "tls://1.0.0.1:853"),
        ("223.5.5.5", "1.1.1.1"),
        ("223.6.6.6", "1.0.0.1"),
        ("119.29.29.29", "8.8.8.8"),
        ("180.76.76.76", "8.8.4.4"),
        ("114.114.114.114", "1.1.1.1"),
    ]

    cleaned_count = 0
    visited = set()
    for d in search_dirs:
        if not os.path.exists(d) or d in visited:
            continue
        visited.add(d)
        for f in os.listdir(d):
            if f.endswith((".yaml", ".yml")):
                p = os.path.join(d, f)
                if not os.path.isfile(p):
                    continue
                try:
                    content = open(p, "r", encoding="utf-8", errors="ignore").read()
                    new_content = content
                    for old, new in replacements:
                        if old in new_content:
                            new_content = new_content.replace(old, new)
                    if new_content != content:
                        open(p, "w", encoding="utf-8").write(new_content)
                        print(f"  [+] 已净化: {p}")
                        cleaned_count += 1
                except Exception as e:
                    print(f"  [!] 无法写入 {f}: {e}")
    print(f"  [*] 共处理并净化了 {cleaned_count} 个代理配置文件。")

if __name__ == "__main__":
    print("=== 开始净化主流代理客户端中的国内 DNS 节点 ===")
    clean_flclash_patch()
    clean_yaml_files()
    print("✅ 净化完成！请在代理软件中重载配置以使其生效。")
