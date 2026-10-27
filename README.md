# 节日产品图库工作台（含每月自动采集）

一个按「年份 · 节日 · 平台 · 采集月份」归档的节日产品图库，每张图带可核验证据。
本仓库 = 工作台网页 + 每月自动采集流水线。

## 目录结构

```
.
├── index.html                    # 工作台网页（GitHub Pages 入口，含内联数据）
├── scrape_month.py               # 每月采集脚本（按月份打标）
├── merge_month.py                # 把某月数据合并进 index.html
├── .github/workflows/
│   └── monthly-scrape.yml        # 每月 30 号自动跑（GitHub Actions 定时）
└── 节日工作台数据库/
    ├── 每月原始数据/             # 每月采集的原始 JSON（数据库真相源）
    │   └── 2026-10.json          #   现有 471 条（10 月那次）
    ├── 工作台文件/
    │   └── index_online.html     #   源文件镜像
    └── README.md
```

## 三种用法

### 1）只看网页
直接用 GitHub Pages 地址打开 `index.html` 即可（开启 Pages 后获得）。
也可本地双击 `index.html` 或 `节日工作台数据库/工作台文件/index_online.html`。

### 2）手动加一个月的数据
```bash
python3.11 scrape_month.py --year 2026 --month 11     # 采集 → 节日工作台数据库/每月原始数据/2026-11.json
python3.11 merge_month.py 2026-11 --html index.html   # 合并进网页
```
合并后重新部署（push 到 main 即触发 Pages 更新；或手动发布）。

### 3）每月 30 号全自动（推荐）
见 `.github/workflows/monthly-scrape.yml`。开启 GitHub Pages + 推上去即可，
定时任务每月采完提交，Pages 自动重新部署上线，**无需手动发布**。

## 自动化前提与注意（务必先看）

1. **开启 GitHub Pages**：仓库 Settings → Pages → Source 选
   “Deploy from a branch” → 分支 `main` → 目录 `/root`。开启后每次 push 自动上线。
2. **亚马逊硬证据需密钥**：Settings → Secrets 添加
   `AMAZON_PA_API_KEY` / `AMAZON_PA_API_SECRET`（亚马逊 Product Advertising API）。
   未配置时亚马逊分支自动跳过，不会产出缺证据的空数据。
3. **2 月没有 30 号**：当前 cron `0 18 30 * *` 在 2 月不跑。想覆盖 2 月，
   把 cron 改成 `0 18 28 * *`（每月 28 号）。
4. **仓库 60 天无活动会暂停定时任务**：随便 push 一次或手动跑一次即恢复。
5. **抓取稳定性**：Pinterest / 独立站 / Etsy / 图片搜索相对好抓；
   若 GitHub 运行器 IP 被限，可能出量少，需要时再调解析器或加代理/付费 API。
   建议先本地或手动跑一次 `scrape_month.py` 验证出量，再交给定时任务。
