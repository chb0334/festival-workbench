# 节日工作台数据库

本文件夹是「节日产品图库工作台」的**数据家目录**。以后每次采集的数据、工作台源文件都归置在这里。

> ⚠️ 说明：你提到的 `G:\桌面\节日工作台数据库` 是你**自己电脑（Windows）上的本地路径**，
> 云端助手（沙箱）无法直接写入你的 G 盘。本文件夹是在云端工作区里建的**同名目录**，
> 结构完全一致。要把它放到你的 G 盘，见下方「如何搬到本地 G 盘」。

## 目录结构

```
节日工作台数据库/
├── 每月原始数据/          # ← 每月采集的原始数据（数据库的“真相源”）
│   ├── 2026-10.json       #    10 月那次采集（现有 471 条，已导出）
│   └── 2026-11.json       #    以后每月 30 号自动生成一个（示例名）
├── 工作台文件/            # ← 工作台网页源文件（含内联数据，可直接双击打开）
│   └── index_online.html
└── README.md
```

## 数据怎么进工作台

1. **采集**：`python3.11 scrape_month.py --year 2026 --month 11`
   结果自动写入 `每月原始数据/2026-11.json`，每条都打上 `month`（如 "11月"）。
2. **合并**：`python3.11 merge_month.py 2026-11`
   把该月数据合并进 `index_online.html`（顶栏「采集月份」会自动多出 11月），
   并同步一份到 `工作台文件/`。

> 合并后可重新“发布”工作台，线上链接的「采集月份」就会显示新月份。

## 每月 30 号自动跑（可选）

见仓库根目录 `.github/workflows/monthly-scrape.yml`：
把它推到 GitHub 仓库，GitHub 会在每月 30 号自动采集+合并+提交。
（需要你有一个 GitHub 仓库来托管；亚马逊硬证据需配置 PA-API 密钥。）

## 如何搬到本地 G 盘

两种方式任选其一：

- **方式一（推荐，最简单）**：在云端工作区里把这个 `节日工作台数据库` 文件夹整体下载，
  然后粘贴到你的 `G:\桌面\节日工作台数据库\` 即可。
- **方式二（自动同步）**：如果你本机装了 WorkBuddy 桌面端，云端工作区会同步到本地
  工作区目录，里面就有这个 `节日工作台数据库` 文件夹，直接剪切/复制到 G 盘。

## 字段速查（每条数据）

`id, year, month, holiday, platform, design_type, title, source_url, brand, asin,
price, evidence_type, evidence_value, evidence_note, collected_by, collected_at,
tags, material, color, composition, tier, heat, img, thumb …`
（与工作台 `index_online.html` 里的 DATA 数组字段完全一致）
