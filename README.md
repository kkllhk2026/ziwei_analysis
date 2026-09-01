# 紫微斗數分析系統

排盤引擎、結構分析、流派可切換。與八字系統同一套工程慣例：
Railway + FastAPI + React/TypeScript/Tailwind，JWT 驗證，rules-as-code。

```
ziwei-lab/
├── backend/               FastAPI + 排盤引擎
│   ├── app/ziwei/         ← 核心。演算法在這裡，論斷規則不在。
│   │   ├── calendar.py    曆法：真太陽時、早晚子時、年界
│   │   ├── constants.py   無爭議的定義
│   │   ├── tables.py      有流派爭議的查表（全部標記待覆核）
│   │   ├── schools.py     流派開關總表
│   │   ├── chart.py       排盤主流程
│   │   ├── fortune.py     大限／流年／流月／流日
│   │   ├── analysis.py    三方四正、飛星、格局
│   │   └── data/          廟旺利陷表（JSON，可替換）
│   └── tests/             21 條迴歸測試，含兩千張隨機盤不變量檢查
├── frontend/              Vite + React 19 + Tailwind 4
│   └── src/components/ZiweiChart.tsx    ← 命盤
├── .railway/              Infrastructure as Code（SDK 亦放這裡，不放根目錄）
├── deploy.sh              railway up 包裝：必須在子目錄執行
└── docs/                  演算法規格、流派清單、部署手冊
```

**根目錄刻意沒有 `package.json`。** 有的話 Railpack 會把整個 monorepo 誤判成
Node app。每個 Railway service 都必須設 Root Directory（`/backend`、`/frontend`），
詳見 `docs/03-部署手冊.md`。

## 三個設計決定

**排盤入碼，論斷不入碼。** 排盤是公開可推導的演算法，逐步寫進程式並附口訣出處
（見 `docs/01-排盤演算法規格.md`）。論斷規則是你的師承資產，走 rules-as-code
放 `app/rules/`，永不外送 LLM。`LLM_POLISH_ENABLED` 預設關閉，即使開啟也只潤飾
規則引擎已產出的文字，拿不到 `Chart` 物件。

**流派差異全部外置。** 凡「兩家會給出不同答案」的，一律進 `tables.py` 並標記
`_VERIFIED: false`。`strict_tables=True` 時，未覆核的表會拋錯而不是默默用下去 ——
避免把網路通行版當成你的定論偷偷出貨。目前**所有**流派表都待你覆核，
清單見 `docs/02-流派設定.md`。

**廟旺利陷畫成真的亮度。** 「星曜」本義就是星的明暗，所以廟星在盤上就該比陷星亮。
掃一眼整張盤就看得出力量分佈，比在星名旁印一個小字有用。

## 快速開始

```bash
cd backend && pip install -r requirements-dev.txt && pytest -q
uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

部署見 `docs/03-部署手冊.md`。**注意 Railway 的 `railway.json` 已淘汰**，
2026-12-01 硬性截止，新服務不能再用；本專案已改用 `.railway/railway.ts`。

## API

| 端點 | 用途 |
|---|---|
| `POST /chart` | 本命盤 |
| `POST /chart/fortune` | 本命 + 大限／流年／流月／流日 |
| `POST /chart/flying` | 全盤宮干飛化、忌轉忌鏈 |
| `POST /chart/compare` | 兩流派逐宮 diff |
| `GET /schools` | 可用流派與其開關 |

## 接下來

1. 填 `SIHUA_LINEAGE` 四化表（庚、壬兩干是關鍵分歧）
2. 逐星覆核 `data/brightness.json`
3. 建 `app/rules/`，開始把師承論斷編碼
4. 與八字系統共用曆法核心（`calendar.py` 可抽成共用套件）
