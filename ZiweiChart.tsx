/**
 * 命盤
 * ====
 * 設計上兩個決定：
 *
 * 1. 廟旺利陷 = 真的亮度。「星曜」二字本義就是星的明暗，
 *    所以廟星就該比陷星亮。這比在星名旁邊印一個小字有用得多，
 *    掃一眼整張盤就知道力量分佈在哪。
 *
 * 2. 三方四正 = 真的幾何。十二地支在圓上等分，三合必成正三角形、
 *    對宮必成直徑。點一個宮，就把那個三角形和那條直徑畫在中宮上。
 *    這是紫微論命的最小單位，值得畫成看得見的東西。
 */

import { useMemo, useState } from "react";

// ── 地支在四乘四盤面上的固定座標 ──
const GRID: Record<string, { r: number; c: number }> = {
  巳: { r: 0, c: 0 }, 午: { r: 0, c: 1 }, 未: { r: 0, c: 2 }, 申: { r: 0, c: 3 },
  辰: { r: 1, c: 0 },                                          酉: { r: 1, c: 3 },
  卯: { r: 2, c: 0 },                                          戌: { r: 2, c: 3 },
  寅: { r: 3, c: 0 }, 丑: { r: 3, c: 1 }, 子: { r: 3, c: 2 }, 亥: { r: 3, c: 3 },
};

const ZHI_ORDER = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"];

const HUA_STYLE: Record<string, string> = {
  祿: "text-[#34D399]",
  權: "text-[#FB7185]",
  科: "text-[#FBBF24]",
  忌: "text-[#94A3B8] ring-1 ring-[#94A3B8]/60 rounded-[2px] px-[2px]",
};

// 廟旺利陷 → 不透明度。這張表就是「亮度」二字的字面意思。
const LUMEN: Record<string, string> = {
  廟: "opacity-100", 旺: "opacity-100", 得: "opacity-[0.86]",
  利: "opacity-[0.78]", 平: "opacity-[0.64]", 不: "opacity-[0.5]", 陷: "opacity-[0.42]",
};

export interface StarDTO {
  名: string; 類: string; 亮度: string | null;
  生年四化: string | null; 自化: string | null;
}
export interface PalaceDTO {
  序: number; 地支: string; 天干: string; 干支: string; 宮名: string;
  身宮: boolean; 大限: [number, number] | null;
  長生十二神: string | null; 博士十二神: string | null;
  星曜: StarDTO[];
}
export interface ChartDTO {
  meta: Record<string, string | number | null>;
  宮位: PalaceDTO[];
  曆法決策: Record<string, string | number>;
}

function Star({ s }: { s: StarDTO }) {
  const major = s.類 === "主星";
  const malefic = s.類 === "煞星";
  const lumen = s.亮度 ? LUMEN[s.亮度] ?? "" : "";
  return (
    <span className={`inline-flex items-baseline gap-[2px] ${lumen}`}>
      <span
        className={
          major
            ? "text-[13px] font-medium tracking-[0.02em] text-[#E8EDF7]"
            : malefic
            ? "text-[11px] text-[#E0A0A0]"
            : "text-[11px] text-[#9AA6BC]"
        }
      >
        {s.名}
      </span>
      {s.亮度 && <span className="text-[9px] text-[#5C6678]">{s.亮度}</span>}
      {s.生年四化 && (
        <span className={`text-[10px] font-semibold ${HUA_STYLE[s.生年四化]}`}>
          {s.生年四化}
        </span>
      )}
      {s.自化 && (
        <span className={`text-[9px] ${HUA_STYLE[s.自化]} opacity-70`}>
          ⌐{s.自化}
        </span>
      )}
    </span>
  );
}

function PalaceCell({
  p, selected, related, onSelect,
}: {
  p: PalaceDTO; selected: boolean; related: "對" | "三合" | null;
  onSelect: () => void;
}) {
  const majors = p.星曜.filter((s) => s.類 === "主星");
  const helpers = p.星曜.filter((s) => s.類 === "吉星" || s.類 === "煞星");
  const minors = p.星曜.filter((s) => s.類 === "雜曜");

  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      className={[
        "relative flex h-full w-full flex-col justify-between p-2 text-left",
        "border border-[#262D3E] bg-[#141824]",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#60A5FA]",
        selected ? "!bg-[#1A2132] border-[#4B5B7A]" : "",
        related === "對" ? "border-[#3E4A66]" : "",
        related === "三合" ? "border-[#36415A]" : "",
      ].join(" ")}
    >
      {/* 星曜 */}
      <div className="flex flex-wrap gap-x-2 gap-y-[3px] leading-tight">
        {majors.length ? (
          majors.map((s) => <Star key={s.名} s={s} />)
        ) : (
          <span className="text-[11px] text-[#4B5468]">無正曜</span>
        )}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-[6px] gap-y-[2px] leading-tight">
        {helpers.map((s) => <Star key={s.名} s={s} />)}
      </div>
      <div className="mt-[2px] flex flex-wrap gap-x-[5px] leading-tight">
        {minors.slice(0, 6).map((s) => (
          <span key={s.名} className="text-[9px] text-[#5A6379]">{s.名}</span>
        ))}
      </div>

      {/* 宮腳 */}
      <div className="mt-auto flex items-end justify-between pt-2">
        <div className="flex flex-col gap-[1px]">
          {p.大限 && (
            <span className="text-[9px] tabular-nums text-[#6B7488]">
              {p.大限[0]}–{p.大限[1]}
            </span>
          )}
          <span className="text-[9px] text-[#5A6379]">{p.長生十二神}</span>
        </div>
        <div className="flex items-baseline gap-[6px]">
          {p.身宮 && (
            <span className="text-[9px] text-[#FBBF24]">身</span>
          )}
          <span className="text-[12px] font-medium text-[#B8C2D6]">{p.宮名}</span>
          <span className="text-[11px] tabular-nums text-[#7A8499]">{p.干支}</span>
        </div>
      </div>
    </button>
  );
}

/** 三方四正的幾何：十二支等分圓周，三合成正三角，對宮成直徑。 */
function TriadOverlay({ selected }: { selected: number | null }) {
  if (selected === null) return null;
  const pts = [selected, (selected + 4) % 12, (selected + 8) % 12];
  const opp = (selected + 6) % 12;

  // 把地支序映到中宮座標系（0..1）上的盤面位置
  const at = (zhiIdx: number) => {
    const g = GRID[ZHI_ORDER[zhiIdx]];
    return { x: (g.c + 0.5) / 4, y: (g.r + 0.5) / 4 };
  };
  const P = pts.map(at);
  const S = at(selected);
  const O = at(opp);

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 1 1"
      preserveAspectRatio="none"
      aria-hidden
    >
      <polygon
        points={P.map((p) => `${p.x},${p.y}`).join(" ")}
        fill="rgba(96,165,250,0.05)"
        stroke="rgba(96,165,250,0.45)"
        strokeWidth="0.0018"
        vectorEffect="non-scaling-stroke"
      />
      <line
        x1={S.x} y1={S.y} x2={O.x} y2={O.y}
        stroke="rgba(251,191,36,0.5)"
        strokeWidth="0.0018"
        strokeDasharray="0.012 0.008"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export default function ZiweiChart({ chart }: { chart: ChartDTO }) {
  const [selected, setSelected] = useState<number | null>(null);
  const byZhi = useMemo(() => {
    const m: Record<string, PalaceDTO> = {};
    chart.宮位.forEach((p) => (m[p.地支] = p));
    return m;
  }, [chart]);

  const relation = (idx: number): "對" | "三合" | null => {
    if (selected === null) return null;
    const d = (idx - selected + 12) % 12;
    if (d === 6) return "對";
    if (d === 4 || d === 8) return "三合";
    return null;
  };

  const m = chart.meta;

  return (
    <div className="relative aspect-square w-full max-w-[860px] select-none">
      <div className="grid h-full w-full grid-cols-4 grid-rows-4 gap-[1px] bg-[#1D2432]">
        {ZHI_ORDER.map((zhi) => {
          const p = byZhi[zhi];
          const g = GRID[zhi];
          if (!p) return null;
          return (
            <div
              key={zhi}
              style={{ gridRow: g.r + 1, gridColumn: g.c + 1 }}
              className="min-h-0"
            >
              <PalaceCell
                p={p}
                selected={selected === p.序}
                related={relation(p.序)}
                onSelect={() => setSelected(selected === p.序 ? null : p.序)}
              />
            </div>
          );
        })}

        {/* 中宮 */}
        <div
          style={{ gridRow: "2 / 4", gridColumn: "2 / 4" }}
          className="relative flex flex-col justify-center gap-3 border border-[#262D3E] bg-[#10141F] p-5"
        >
          <TriadOverlay selected={selected} />
          <div className="relative">
            <p className="font-serif text-[17px] leading-snug text-[#E8EDF7]">
              {m["農曆"]}
            </p>
            <p className="mt-1 text-[12px] tabular-nums text-[#6B7488]">
              {String(m["西曆"]).replace("T", " ").slice(0, 16)}
              {chart.曆法決策["真太陽時校正分鐘"] !== 0 && (
                <> · 真太陽時 {chart.曆法決策["真太陽時校正分鐘"]} 分</>
              )}
            </p>
          </div>

          <dl className="relative grid grid-cols-2 gap-x-5 gap-y-[6px] text-[12px]">
            {[
              ["五行局", m["五行局"]],
              ["陰陽男女", m["陰陽男女"]],
              ["命主", m["命主"]],
              ["身主", m["身主"]],
              ["命宮", m["命宮"]],
              ["身宮", m["身宮"]],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex justify-between gap-2">
                <dt className="text-[#5F6879]">{k}</dt>
                <dd className="font-serif text-[#C9D3E4]">{String(v)}</dd>
              </div>
            ))}
          </dl>

          <p className="relative text-[11px] leading-relaxed text-[#4F586B]">
            {selected === null
              ? "點任一宮，看它的三方四正。"
              : `${byZhi[ZHI_ORDER[selected]].宮名}　對宮 ${
                  byZhi[ZHI_ORDER[(selected + 6) % 12]].宮名
                }　三合 ${byZhi[ZHI_ORDER[(selected + 4) % 12]].宮名}、${
                  byZhi[ZHI_ORDER[(selected + 8) % 12]].宮名
                }`}
          </p>
        </div>
      </div>
    </div>
  );
}
