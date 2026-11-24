# Network Leak Shield — Windows 全链路网络隐私与防泄露一键加固工具集

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB.svg)](https://www.python.org/)
[![Agent Skill](https://img.shields.io/badge/AI%20Agent-Skill%20Ready-6842FF.svg)](#)

**让一台什么都没有做过的全新 Windows 电脑，通过一条命令实现零泄露、高纯净、可一键回滚的安全网络环境。**

本项目既是一套开箱即用的 **Windows 隐私与防泄露自动化脚本集**，也是一份标准的 **AI Agent Skill（兼容 Antigravity / Claude Code / Codex）**，总结自大量真实排雷实战，专门解决访问海外高风控服务（如 Claude、OpenAI、Google、Stripe）时的隐形暴露与账号异常问题。

---

## 🎯 解决哪些痛点？

很多用户买了优质的海外住宅代理，连上代理软件却依然频频触发风控或断网，根源往往隐藏在操作系统和软件的默认行为中：

1. **Windows 定位服务偷跑**：系统 `lfsvc` 服务通过扫描周边 Wi-Fi 路由器的 MAC 地址（BSSID），绕过代理毫秒级精确定位真实街道位置。
2. **时区与 Intl 区域不匹配**：代理出口在美国，但系统时区是 `UTC+8`、区域格式是 `zh-CN`，被前端 JS 的 `Intl` API 直接识破（且很多人不敢改，怕整个电脑变成英文或软件乱码）。
3. **Windows 并发多宿主 DNS 泄露**：系统默认并发向物理网卡和代理网卡查询 DNS，国内运营商 DNS（如 `111.26.x.x`）抢跑返回造成泄露；而直接把物理网卡永久写死为 `1.1.1.1` 又会导致关闭代理后连不上校园网/酒店 Wi-Fi。
4. **代理订阅与 GUI 补丁暗藏国内 DNS**：FlClash、Clash Verge 等订阅默认下发或内部补丁中常带有腾讯 `doh.pub`、阿里 `223.5.5.5`，导致看似连着海外节点，底层解析却在悄悄回源国内。
5. **IPv6 双栈旁路暴露**：宽带原生 IPv6 绕过仅代理 IPv4 的隧道，或 Hyper-V / TUN 虚拟网卡残留 IPv6 绑定触发严格检测报错。
6. **Edge / Chrome WebRTC 穿透**：浏览器绕过代理发起 STUN UDP 探测，暴露公网真实 IP 或局域网信息。
7. **游戏加速器 / 工具箱死代理残留**：Watt Toolkit (Steam++)、UU 等工具异常退出后，在 WinINet 注册表二进制结构中残留失效的 PAC 脚本（如 `127.0.0.1:26561/pac`），导致 Steam 报 `-101` 或应用全面断网。

---

## 🛡️ 七层全链路防御体系

| 层级 | 防护对象 | 自动化动作 |
| :--- | :--- | :--- |
| **Layer 1** | **Windows 系统隐私与区域** | 彻底关闭系统定位服务 (`lfsvc` + 组策略 + HKLM/HKCU=Deny)、关广告 ID 与诊断追踪；对齐目标地区时区/国家/`en-US` 区域格式，**严格保留简体中文显示界面** |
| **Layer 2** | **底层网络协议栈** | 禁用所有物理与虚拟网卡 IPv6 (`ms_tcpip6`)；写入 `DisableSmartNameResolution = 1` 堵死跨网卡并发 DNS；关闭 LLMNR 局域网广播 |
| **Layer 3** | **动态 DNS 看门狗** | 内置零依赖 C# 守护源码 (`dns_guard.cs`)，用 Windows 自带编译器生成；自动适配活跃物理网卡，**开 TUN 自动锁 1.1.1.1，关 TUN 自动恢复 DHCP** |
| **Layer 4** | **代理客户端配置纯净化** | 扫描净化 FlClash、Clash Verge Rev、Clash Nyanpasu、Mihomo Party 配置、订阅及 `patchClashConfig` 中的国内公共 DNS |
| **Layer 5** | **WinINet 代理与 PAC 清理** | 重置注册表死代理与二进制 PAC 结构，广播刷新 WinINet，清理 Steam 死锁网页缓存 (`htmlcache`) |
| **Layer 6** | **Edge & Chrome 浏览器加固** | 管理员模式下写入官方企业组策略（锁定 WebRTC `disable_non_proxied_udp`、强制 Cloudflare Secure DoH、禁止网页定位与预解析）；同步更新用户配置与桌面快捷方式 |
| **Layer 7** | **指纹浏览器隔离分工** | 配套完整实战指南：高风控账号用指纹浏览器隔离硬件指纹，日常查资料用加固后的 Edge/Chrome |

---

## ⚡ 一键快速开始（全新电脑适用）

### 1. 获取项目
```bash
git clone https://github.com/your-username/network-leak-shield.git
cd network-leak-shield
```

### 2. 先做一次只读全面体检（不改任何系统设置）
```bash
python scripts/one_click_harden.py --audit
```

### 3. 一键全链路加固（请用「管理员身份」打开终端执行）
```bash
# 例：代理节点位于美国西部（洛杉矶/加州），同时对齐时区与 Intl 格式（保留中文界面）：
python scripts/one_click_harden.py --apply --region us-west

# 其他可选地区预设：us-east | jp | sg | uk | skip（skip 表示不修改系统时区与区域）
# 如不需要安装开机自启的动态 DNS 看门狗，可附加 --skip-guard
```
> 脚本执行前会自动将你的原始时区、国家与区域格式备份至 `%LOCALAPPDATA%\NetworkLeakShield\os_backup.json`。

### 4. 一键无损回滚（随时可还原）
```bash
python scripts/one_click_harden.py --rollback
```
自动卸载看门狗、恢复物理网卡 DHCP DNS、移除浏览器组策略、恢复定位服务与 IPv6，并从备份还原原始时区与区域。

---

## 📂 目录结构

```text
network-leak-shield/
├── SKILL.md                           # AI Agent 技能主规范（供 Antigravity / Claude Code 直接调用）
├── README.md                          # 项目使用说明
├── .gitignore
├── scripts/
│   ├── one_click_harden.py            # ⭐ 一键总控脚本 (--audit / --apply / --rollback)
│   ├── audit_environment.py           # 七层全链路体检审计工具
│   ├── harden_windows_privacy.py      # 系统定位/隐私/时区区域/SmartDNS/LLMNR/IPv6 加固
│   ├── dns_guard.cs                   # 零依赖自适应物理网卡的 C# 动态 DNS 看门狗源码
│   ├── deploy_dns_guard.py            # 自动编译看门狗并注册/卸载系统计划任务
│   ├── purge_clash_chinese_dns.py     # 多代理客户端国内 DNS 净化工具
│   ├── clean_proxy_residue.py         # WinINet 死代理/幽灵 PAC 与 Steam 缓存清理
│   └── harden_browsers.py             # Edge + Chrome 企业组策略与防泄露加固
└── references/
    ├── WINDOWS_PRIVACY_CHECKLIST.md   # Windows 系统级隐私与安全设置详解
    ├── WEBRTC_MECHANICS.md            # WebRTC 原理、STUN 穿透与私网 IP 误报辨析
    ├── GEOIP_DISCREPANCIES.md         # 跨库 GeoIP 城市差异与 ASN 属性解读
    └── FINGERPRINT_VS_EDGE.md         # 传输层防泄露 vs 浏览器硬件指纹对抗指南
```

---

## ✅ 验收检测矩阵

一键加固完成并重启浏览器与代理软件后，建议前往以下网站核验：

| 检测维度 | 推荐检测站 | 理想结果 |
| :--- | :--- | :--- |
| **DNS 泄露** | [BrowserLeaks DNS](https://browserleaks.com/dns) | 全部解析节点为海外 Cloudflare / Google，无任何国内运营商 |
| **WebRTC 泄露** | [BrowserLeaks WebRTC](https://browserleaks.com/webrtc) | 显示 `✓ No Public IP Leak`，`Public IP Address: -` |
| **浏览器组策略** | 地址栏输入 `edge://policy` 或 `chrome://policy` | 可见 `WebRtcIPHandlingPolicy`、`DnsOverHttpsMode`、`DefaultGeolocationSetting` 生效 |
| **IP 属性纯净度** | [IPPure](https://ippure.com) | 原生住宅 IP、低纯净度系数、高真人流量占比 |
| **环境综合风控** | [FuckClaude](https://fuckclaude.com) | 低风险，无明显中国化环境信号 |

---

## 🤖 作为 AI Agent Skill 使用

将本目录直接放入你的本地技能目录（例如 Antigravity 的 `~/.gemini/config/skills/network-leak-shield`），随后直接对 AI 说：
> “帮我用 network-leak-shield 给这台电脑做一次全面的网络防泄露体检并一键加固。”
