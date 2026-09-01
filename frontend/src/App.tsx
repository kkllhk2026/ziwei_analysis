import { useState } from "react";
import ZiweiChart, { type ChartDTO } from "./components/ZiweiChart";

const API = import.meta.env.VITE_API_URL ?? "/api";

export default function App() {
  const [form, setForm] = useState({
    birth: "1985-03-12T14:30",
    gender: "男" as "男" | "女",
    longitude: "114.17",
    school: "通行本",
  });
  const [chart, setChart] = useState<ChartDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function cast() {
    setBusy(true);
    setError(null);
    try {
      const token = localStorage.getItem("ziwei_token") ?? "";
      const res = await fetch(`${API}/chart`, {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${token}` },
        body: JSON.stringify({
          birth: `${form.birth}:00`,
          gender: form.gender,
          longitude: form.longitude ? Number(form.longitude) : null,
          school: form.school,
        }),
      });
      if (!res.ok) {
        setError(res.status === 401 ? "憑證已過期，請重新登入。" : `排盤失敗（${res.status}）。`);
        return;
      }
      setChart(await res.json());
    } catch {
      setError("連不上後端。確認 API 服務正在執行。");
    } finally {
      setBusy(false);
    }
  }

  const field = "h-9 rounded-[3px] border border-[#2A3244] bg-[#141824] px-2.5 text-[13px] text-[#DCE3F0] focus:border-[#4B5B7A] focus:outline-none";

  return (
    <main className="mx-auto flex max-w-[1180px] flex-col gap-7 px-6 py-9">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-[#1D2432] pb-5">
        <div>
          <h1 className="font-serif text-[26px] leading-none tracking-[0.06em] text-[#E8EDF7]">
            紫微斗數
          </h1>
          <p className="mt-2 text-[12px] text-[#5F6879]">
            排盤演算法逐步可查證，流派開關逐項可切換。
          </p>
        </div>
        {chart && (
          <p className="text-[11px] text-[#4F586B]">
            {String(chart.meta["五行局"])} ·{" "}
            {String(chart.meta["陰陽男女"])} · 大限
            {String(chart.meta["大限方向"])}
          </p>
        )}
      </header>

      <section className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] text-[#5F6879]">出生時刻</span>
          <input
            type="datetime-local" className={field} value={form.birth}
            onChange={(e) => setForm({ ...form, birth: e.target.value })}
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] text-[#5F6879]">性別</span>
          <select
            className={field} value={form.gender}
            onChange={(e) => setForm({ ...form, gender: e.target.value as "男" | "女" })}
          >
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] text-[#5F6879]">出生地經度</span>
          <input
            className={`${field} w-[110px]`} value={form.longitude} placeholder="留空則不校正"
            onChange={(e) => setForm({ ...form, longitude: e.target.value })}
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] text-[#5F6879]">流派</span>
          <select
            className={field} value={form.school}
            onChange={(e) => setForm({ ...form, school: e.target.value })}
          >
            <option>通行本</option>
            <option>中州派</option>
            <option>飛星／欽天四化</option>
          </select>
        </label>
        <button
          onClick={cast} disabled={busy}
          className="h-9 rounded-[3px] border border-[#4B5B7A] bg-[#1A2132] px-5 text-[13px] text-[#DCE3F0] hover:bg-[#20293D] disabled:opacity-50"
        >
          {busy ? "排盤中" : "排盤"}
        </button>
      </section>

      {error && (
        <p className="rounded-[3px] border border-[#5A3A3A] bg-[#1E1416] px-3 py-2 text-[12px] text-[#E0A0A0]">
          {error}
        </p>
      )}

      {chart ? (
        <ZiweiChart chart={chart} />
      ) : (
        !error && (
          <p className="py-20 text-center text-[13px] text-[#3F4756]">
            填入出生時刻，排一張盤。
          </p>
        )
      )}
    </main>
  );
}
