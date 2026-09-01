/**
 * Railway Infrastructure as Code
 * ===============================
 * 注意：railway.json / railway.toml（Config as Code）已被 Railway 標記為
 * 淘汰，2026-12-01 硬性截止，而且新服務已經不能再選用。所以這個專案一開始
 * 就用 .railway/railway.ts。你的八字專案若仍在用 railway.json，
 * 記得在截止日前執行 `railway config pull` 匯入後遷移。
 *
 * 用法：
 *   npm i -D railway
 *   railway link
 *   railway config plan     # 先看 diff
 *   railway config apply    # 確認後才套用
 */
import { defineRailway, github, group, postgres, preserve, project, service } from "railway/iac";

const REPO = "your-org/ziwei-lab";   // ← 改成你的 GitHub repo

export default defineRailway((ctx) => {
  const prod = ctx.isEnvironment("production");

  const db = postgres("postgres");

  const api = service("api", {
    source: github(REPO, { rootDirectory: "backend" }),
    healthcheck: "/health",
    healthcheckTimeout: 30,
    replicas: prod ? 2 : 1,
    env: {
      DATABASE_URL: db.env.DATABASE_URL,
      JWT_SECRET: preserve(),          // 在 Railway 介面設定，不入版本庫
      CORS_ORIGINS: prod ? "https://ziwei.example.com" : "*",
      STRICT_TABLES: prod ? "true" : "false",
      LLM_POLISH_ENABLED: "false",
    },
  });

  const web = service("web", {
    source: github(REPO, { rootDirectory: "frontend" }),
    domains: prod ? ["ziwei.example.com"] : [],
    env: {
      VITE_API_URL: `https://${api.env.RAILWAY_PUBLIC_DOMAIN}`,
    },
  });

  return project("ziwei-lab", {
    resources: [group("後端", [api, db]), web],
  });
});
