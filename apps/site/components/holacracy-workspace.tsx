"use client";

import { useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  BadgeCheck,
  Brain,
  CalendarDays,
  Check,
  ChevronRight,
  ExternalLink,
  Globe2,
  GraduationCap,
  LineChart,
  Orbit,
  Palette,
  RefreshCw,
  Sparkles,
  Target,
  Users
} from "lucide-react";

type Circle = {
  id: string;
  label: string;
  labelZh: string;
  icon: LucideIcon;
  accent: string;
  purpose: string;
  purposeZh: string;
  executor: string;
  executorZh: string;
  roles: string[];
  subjects?: string[];
  outputs: string[];
  ddl: {
    roles: string;
    subjects?: string;
    outputs: string;
  };
};

type Sticker = {
  id: string;
  name: string;
  feature: string;
  featureZh: string;
  color: string;
  roles: string[];
  evidence: string;
  evidenceZh: string;
};

const links = [
  {
    label: "Company Intro",
    labelZh: "公司介绍",
    href: "https://my.feishu.cn/wiki/WDSZwQl8BiT924kQUa2c9aw7nLd",
    description: "IP / storyline framework and U.S. cultural-fit notes.",
    descriptionZh: "IP / 故事线框架与美国课堂文化适配笔记。"
  },
  {
    label: "Belinda Update",
    labelZh: "Belinda 更新",
    href: "https://my.feishu.cn/wiki/LTC2wMLaBiVEzokTJMncb6JVnNg",
    description: "Learning science, evidence, ELA / Math framework.",
    descriptionZh: "学习科学、研究证据、ELA / 数学课程框架。"
  },
  {
    label: "Tata Update",
    labelZh: "Tata 更新",
    href: "https://my.feishu.cn/wiki/F2O3wjefRiNYpdkwirqcvEJtnCd",
    description: "Last Meridian Academy world bible and academy structure.",
    descriptionZh: "终界学院世界观、学院体系与故事宇宙。"
  }
];

const circles: Circle[] = [
  {
    id: "ip",
    label: "IP",
    labelZh: "IP 形象设计",
    icon: Palette,
    accent: "border-fuchsia-300 bg-fuchsia-50 text-fuchsia-900",
    purpose: "Design original IP characters and visual assets for ComicLearn stories and learning products.",
    purposeZh: "为 ComicLearn 的故事和学习产品设计原创 IP 形象与视觉资产。",
    executor: "Authority: Tata",
    executorZh: "Authority：Tata",
    roles: ["IP character design: story + image", "Successful IP research", "Drawing / illustration"],
    outputs: ["Character sheets", "IP benchmark notes", "Sketches", "Visual references"],
    ddl: { roles: "2026-06-28", outputs: "2026-07-02" }
  },
  {
    id: "story",
    label: "Story Setting",
    labelZh: "故事设置",
    icon: Globe2,
    accent: "border-sky-300 bg-sky-50 text-sky-900",
    purpose: "Build the world setting, character identities, main plot, and story logic for ComicLearn.",
    purposeZh: "搭建 ComicLearn 的世界观、人物形象、主线剧情和故事逻辑。",
    executor: "Authority: Tata",
    executorZh: "Authority：Tata",
    roles: ["Worldview", "Character setting", "Main storyline", "Successful case research"],
    outputs: ["World bible", "Character profiles", "Main plot outline", "Case study notes"],
    ddl: { roles: "2026-06-28", outputs: "2026-07-03" }
  },
  {
    id: "curriculum",
    label: "K-8 Curriculum Research",
    labelZh: "K-8 课程研究",
    icon: GraduationCap,
    accent: "border-indigo-300 bg-indigo-50 text-indigo-900",
    purpose: "Research curriculum systems, successful examples, and subject-by-subject course development for K-8.",
    purposeZh: "研究 K-8 课程体系、成功案例，并推进分学科课程开发。",
    executor: "Lead: Belinda; support: curriculum designers",
    executorZh: "Lead：Belinda；支持：课程设计师",
    roles: ["Curriculum system", "Successful case research", "Course development by subject"],
    subjects: ["Math", "English", "Physics", "History", "Biology", "Psychology", "Business"],
    outputs: ["Curriculum map", "Successful case notes", "Subject frameworks", "Lesson development checklist"],
    ddl: { roles: "2026-06-30", subjects: "2026-07-05", outputs: "2026-07-08" }
  },
  {
    id: "research",
    label: "Research",
    labelZh: "科研",
    icon: Brain,
    accent: "border-amber-300 bg-amber-50 text-amber-900",
    purpose: "Study comic book learning effectiveness, psychological impact, and practical classroom examples.",
    purposeZh: "研究漫画书教育效果、漫画书对心理的影响，以及可落地的实践例子。",
    executor: "Authority: Belinda",
    executorZh: "Authority：Belinda",
    roles: ["Comic book learning effectiveness", "Psychological impact", "Practice examples", "Reference validation"],
    outputs: ["Evidence matrix", "Research notes", "Practical example bank", "Claim-risk table"],
    ddl: { roles: "2026-06-28", outputs: "2026-07-05" }
  },
  {
    id: "market",
    label: "Market Validation",
    labelZh: "市场验证",
    icon: LineChart,
    accent: "border-rose-300 bg-rose-50 text-rose-900",
    purpose: "Validate C-side and B-side pain points, market size, production costs, and investor advice.",
    purposeZh: "验证 C 端和 B 端用户痛点、市场 size、成本分析和投资人建议。",
    executor: "Authority: Andy",
    executorZh: "Authority：Andy",
    roles: ["C-side user pain research", "B-side user pain research", "Market size analysis", "Cost analysis", "Investor advice"],
    outputs: ["Interview notes", "Market size memo", "Cost analysis", "Investor feedback log"],
    ddl: { roles: "2026-07-05", outputs: "2026-07-12" }
  }
];

const stickers: Sticker[] = [
  {
    id: "andy",
    name: "Andy",
    feature: "Authority: Market Validation & Strategy",
    featureZh: "Authority：市场验证 & 战略",
    color: "border-emerald-300 bg-emerald-50",
    roles: ["C-side pain research", "B-side pain research", "Market size analysis", "Cost analysis", "Investor advice"],
    evidence: "Owns market validation, business strategy, fundraising narrative, and investor-facing synthesis.",
    evidenceZh: "负责市场验证、商业战略、融资叙事和投资人视角的综合判断。"
  },
  {
    id: "belinda",
    name: "Belinda",
    feature: "Authority: Research",
    featureZh: "Authority：科研",
    color: "border-amber-300 bg-amber-50",
    roles: ["Comic learning effectiveness", "Psychological impact", "Practice examples", "Reference validation", "K-8 curriculum research"],
    evidence: "Owns research evidence, educational psychology, reference validation, and supports K-8 curriculum research.",
    evidenceZh: "负责研究证据、教育心理、文献有效性，并支持 K-8 课程研究。"
  },
  {
    id: "tata",
    name: "Tata",
    feature: "Authority: IP & Story Setting",
    featureZh: "Authority：IP & 故事设置",
    color: "border-sky-300 bg-sky-50",
    roles: ["IP character design", "Successful IP research", "Drawing / illustration", "Worldview design", "Character setting", "Main storyline"],
    evidence: "Owns IP design, visual/story direction, worldbuilding, character identity, and main plot.",
    evidenceZh: "负责 IP 设计、视觉/故事方向、世界观、人物形象和主线剧情。"
  },
  {
    id: "open",
    name: "Open Roles",
    feature: "Recruiting / Hiring Needs / Missing Capacity",
    featureZh: "招聘 / 岗位需求 / 缺失能力",
    color: "border-rose-300 bg-rose-50",
    roles: ["Software Developer", "IP Designer", "K-8 Curriculum Designer", "Research Assistant"],
    evidence: "Use this sticker to route unowned work until a teammate claims it.",
    evidenceZh: "在正式 owner 出现前，用这个 sticker 承接无人负责的工作。"
  }
];

const executorSteps = [
  {
    icon: Target,
    label: "Sense tension",
    labelZh: "感知 tension",
    detail: "What gap blocks learning, product, IP, or market validation?",
    detailZh: "当前哪个差距阻碍了学习、产品、IP 或市场验证？"
  },
  {
    icon: Orbit,
    label: "Route to circle",
    labelZh: "路由到 circle",
    detail: "Choose the circle with the clearest domain and accountability.",
    detailZh: "选择 domain 和 accountability 最清晰的 circle。"
  },
  {
    icon: BadgeCheck,
    label: "Name executor",
    labelZh: "指定 executor",
    detail: "Assign the role holder who can decide and ship.",
    detailZh: "指定有权决策并交付的 role holder。"
  },
  {
    icon: Sparkles,
    label: "Ship artifact",
    labelZh: "交付 artifact",
    detail: "A memo, comic spec, IP sheet, demo, interview log, or research table.",
    detailZh: "可以是 memo、漫画 spec、IP sheet、demo、访谈记录或研究表。"
  },
  {
    icon: RefreshCw,
    label: "Review evidence",
    labelZh: "复盘证据",
    detail: "Update metrics, role stickers, and the next priority.",
    detailZh: "更新指标、role sticker 和下一步优先级。"
  }
];

const priorityRows = [
  ["P0", "Workspace + role repository", "工作区 + 角色库", "Andy", "2026-06-21"],
  ["P0", "IP + story direction", "IP + 故事方向", "Tata", "2026-06-25"],
  ["P0", "Research evidence matrix", "科研证据矩阵", "Belinda", "2026-06-24"],
  ["P1", "K-8 curriculum research map", "K-8 课程研究地图", "Belinda + Open", "2026-07-05"],
  ["P1", "C-side / B-side pain interviews", "C 端 / B 端痛点访谈", "Andy", "2026-07-10"],
  ["P2", "Market size + cost analysis", "市场 size + 成本分析", "Andy", "2026-07-12"]
];

function makeInitialFulfillment() {
  return Object.fromEntries(stickers.map((sticker) => [sticker.id, sticker.roles.slice(0, sticker.id === "open" ? 0 : 2)]));
}

export function HolacracyWorkspace() {
  const [activeCircle, setActiveCircle] = useState(circles[0]);
  const [activeSticker, setActiveSticker] = useState(stickers[0]);
  const [fulfilled, setFulfilled] = useState<Record<string, string[]>>(() => {
    if (typeof window === "undefined") return makeInitialFulfillment();

    const raw = window.localStorage.getItem("comiclearn-role-stickers");
    if (!raw) return makeInitialFulfillment();

    try {
      const parsed = JSON.parse(raw) as Record<string, string[]>;
      return { ...makeInitialFulfillment(), ...parsed };
    } catch {
      window.localStorage.removeItem("comiclearn-role-stickers");
      return makeInitialFulfillment();
    }
  });
  const [circleChecks, setCircleChecks] = useState<Record<string, string[]>>(() => {
    if (typeof window === "undefined") return {};

    const raw = window.localStorage.getItem("comiclearn-circle-checks");
    if (!raw) return {};

    try {
      return JSON.parse(raw) as Record<string, string[]>;
    } catch {
      window.localStorage.removeItem("comiclearn-circle-checks");
      return {};
    }
  });

  useEffect(() => {
    window.localStorage.setItem("comiclearn-role-stickers", JSON.stringify(fulfilled));
  }, [fulfilled]);

  useEffect(() => {
    window.localStorage.setItem("comiclearn-circle-checks", JSON.stringify(circleChecks));
  }, [circleChecks]);

  const fulfilledRoles = fulfilled[activeSticker.id] ?? [];
  const completion = useMemo(() => {
    if (activeSticker.roles.length === 0) return 0;
    return Math.round((fulfilledRoles.length / activeSticker.roles.length) * 100);
  }, [activeSticker.roles.length, fulfilledRoles.length]);

  function toggleRole(role: string) {
    setFulfilled((current) => {
      const currentRoles = current[activeSticker.id] ?? [];
      const nextRoles = currentRoles.includes(role)
        ? currentRoles.filter((item) => item !== role)
        : [...currentRoles, role];

      return { ...current, [activeSticker.id]: nextRoles };
    });
  }

  function toggleCircleCheck(group: string, item: string) {
    const key = `${group}:${item}`;
    setCircleChecks((current) => {
      const currentItems = current[activeCircle.id] ?? [];
      const nextItems = currentItems.includes(key)
        ? currentItems.filter((saved) => saved !== key)
        : [...currentItems, key];

      return { ...current, [activeCircle.id]: nextItems };
    });
  }

  function isCircleChecked(group: string, item: string) {
    return (circleChecks[activeCircle.id] ?? []).includes(`${group}:${item}`);
  }

  return (
    <div className="bg-paper">
      <section className="border-b border-rule bg-white">
        <div className="container py-10">
          <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
            <div>
              <p className="eyebrow">ComicLearn Operating System</p>
              <h1 className="mt-5 max-w-3xl font-sans text-4xl font-semibold leading-tight text-ink md:text-5xl">
                Holacracy Executor
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-muted">
                A circle-based execution workspace for turning ComicLearn from ideas into shipped artifacts.
                <br />
                <span className="text-ink">一个以 circle 为中心的执行型协作系统，把 ComicLearn 从想法推进到可交付产物。</span>
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {links.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  target="_blank"
                  rel="noreferrer"
                  className="group rounded-lg border border-rule bg-paper p-4 shadow-chip transition hover:border-ink/25 hover:bg-white"
                >
                  <span className="flex items-center justify-between gap-3 text-sm font-semibold text-ink">
                    {link.label}
                    <ExternalLink className="h-4 w-4 text-muted transition group-hover:text-ink" />
                  </span>
                  <span className="mt-1 block text-sm font-medium text-muted">{link.labelZh}</span>
                  <span className="mt-3 block text-xs leading-5 text-muted">{link.description}</span>
                  <span className="mt-1 block text-xs leading-5 text-slate-600">{link.descriptionZh}</span>
                </a>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="container py-10">
        <div className="grid gap-8 lg:grid-cols-[1fr_0.9fr]">
          <div>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="page-no">Circle Map</p>
                <h2 className="mt-2 font-sans text-2xl font-semibold">Circles as living ownership lanes</h2>
                <p className="mt-2 text-sm leading-6 text-muted">
                  Each circle owns a domain, a set of accountabilities, and an executor role.
                  <br />
                  每个 circle 都有自己的 domain、accountabilities 和 executor。
                </p>
              </div>
              <Orbit className="hidden h-10 w-10 text-indigo-600 sm:block" />
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {circles.map((circle) => {
                const Icon = circle.icon;
                const isActive = activeCircle.id === circle.id;
                return (
                  <button
                    key={circle.id}
                    type="button"
                    onClick={() => setActiveCircle(circle)}
                    className={`rounded-lg border p-4 text-left transition ${
                      isActive ? `${circle.accent} shadow-paper` : "border-rule bg-white hover:border-ink/25"
                    }`}
                  >
                    <span className="flex items-center gap-3">
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-white/80">
                        <Icon className="h-5 w-5" />
                      </span>
                      <span>
                        <span className="block text-sm font-semibold">{circle.label}</span>
                        <span className="block text-xs text-muted">{circle.labelZh}</span>
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <aside className="rounded-lg border border-rule bg-white p-6 shadow-paper">
            <div className={`inline-flex rounded-md border px-3 py-1 text-xs font-semibold ${activeCircle.accent}`}>
              Active Circle / 当前 Circle
            </div>
            <h3 className="mt-4 font-sans text-2xl font-semibold">{activeCircle.label}</h3>
            <p className="text-sm font-medium text-muted">{activeCircle.labelZh}</p>

            <div className="mt-5 space-y-4">
              <InfoBlock title="Purpose" titleZh="目的" body={activeCircle.purpose} bodyZh={activeCircle.purposeZh} />
              <InfoBlock title="Executor" titleZh="执行负责人" body={activeCircle.executor} bodyZh={activeCircle.executorZh} />

              <div className="overflow-hidden rounded-md border border-rule">
                <div className="grid grid-cols-[1.2fr_0.8fr] bg-ink px-3 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-paper">
                  <span>Checklist Block</span>
                  <span>DDL</span>
                </div>
                <DdlRow label="Roles / 角色" ddl={activeCircle.ddl.roles} />
                {activeCircle.subjects ? <DdlRow label="Subjects / 学科" ddl={activeCircle.ddl.subjects ?? "TBD"} /> : null}
                <DdlRow label="Current Outputs / 当前交付物" ddl={activeCircle.ddl.outputs} />
              </div>

              <CircleChecklist
                title="Roles / 角色"
                group="roles"
                items={activeCircle.roles}
                isChecked={isCircleChecked}
                onToggle={toggleCircleCheck}
              />

              {activeCircle.subjects ? (
                <CircleChecklist
                  title="Subjects / 学科"
                  group="subjects"
                  items={activeCircle.subjects}
                  isChecked={isCircleChecked}
                  onToggle={toggleCircleCheck}
                />
              ) : null}

              <CircleChecklist
                title="Current Outputs / 当前交付物"
                group="outputs"
                items={activeCircle.outputs}
                isChecked={isCircleChecked}
                onToggle={toggleCircleCheck}
              />
            </div>
          </aside>
        </div>
      </section>

      <section className="border-y border-rule bg-white">
        <div className="container py-10">
          <div className="mb-6 flex items-end justify-between gap-4">
            <div>
              <p className="page-no">Executor Flow</p>
              <h2 className="mt-2 font-sans text-2xl font-semibold">From tension to shipped work</h2>
              <p className="mt-2 text-sm leading-6 text-muted">
                Holacracy defines ownership; Executor makes the next action visible.
                <br />
                Holacracy 定义权责，Executor 让下一步行动可见。
              </p>
            </div>
            <ChevronRight className="hidden h-8 w-8 text-muted sm:block" />
          </div>

          <div className="grid gap-3 md:grid-cols-5">
            {executorSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={step.label} className="rounded-lg border border-rule bg-paper p-4">
                  <div className="flex items-center justify-between gap-2">
                    <span className="grid h-9 w-9 place-items-center rounded-md bg-ink text-paper">
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="font-mono text-xs text-muted">0{index + 1}</span>
                  </div>
                  <h3 className="mt-4 font-sans text-sm font-semibold">{step.label}</h3>
                  <p className="mt-1 text-xs font-medium text-muted">{step.labelZh}</p>
                  <p className="mt-3 text-xs leading-5 text-muted">{step.detail}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-600">{step.detailZh}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="container py-10">
        <div className="grid gap-8 lg:grid-cols-[0.82fr_1.18fr]">
          <div>
            <p className="page-no">Sticker Function</p>
            <h2 className="mt-2 font-sans text-2xl font-semibold">Teammate role stickers</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Pick a teammate sticker, then mark which roles they can fulfill right now. This is saved locally in the browser.
              <br />
              选择一个 teammate sticker，然后标记 TA 当前可以 fulfill 的角色；结果会保存在本地浏览器里。
            </p>

            <div className="mt-6 grid gap-3">
              {stickers.map((sticker) => (
                <button
                  key={sticker.id}
                  type="button"
                  onClick={() => setActiveSticker(sticker)}
                  className={`rounded-lg border p-4 text-left transition ${
                    activeSticker.id === sticker.id ? `${sticker.color} shadow-paper` : "border-rule bg-white hover:border-ink/25"
                  }`}
                >
                  <span className="flex items-start justify-between gap-3">
                    <span>
                      <span className="block text-base font-semibold text-ink">{sticker.name}</span>
                      <span className="mt-1 block text-sm text-muted">{sticker.feature}</span>
                      <span className="mt-1 block text-xs text-slate-600">{sticker.featureZh}</span>
                    </span>
                    <Users className="h-5 w-5 text-muted" />
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className={`rounded-lg border p-6 shadow-paper ${activeSticker.color}`}>
            <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Selected Sticker / 当前 Sticker</p>
                <h3 className="mt-2 font-sans text-3xl font-semibold">{activeSticker.name}</h3>
                <p className="mt-1 text-sm font-medium text-muted">{activeSticker.feature}</p>
                <p className="mt-1 text-sm text-slate-600">{activeSticker.featureZh}</p>
              </div>

              <div className="w-full rounded-md border border-white/80 bg-white/80 p-3 md:w-40">
                <div className="flex items-center justify-between text-xs font-medium text-muted">
                  <span>Fulfilled</span>
                  <span>{completion}%</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-slate-200">
                  <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${completion}%` }} />
                </div>
                <p className="mt-2 text-xs text-slate-600">已确认角色比例</p>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {activeSticker.roles.map((role) => {
                const checked = fulfilledRoles.includes(role);
                return (
                  <button
                    key={role}
                    type="button"
                    onClick={() => toggleRole(role)}
                    className={`flex min-h-14 items-center gap-3 rounded-md border px-4 py-3 text-left text-sm font-medium transition ${
                      checked ? "border-emerald-400 bg-white text-ink" : "border-white/80 bg-white/60 text-muted hover:bg-white"
                    }`}
                  >
                    <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border ${checked ? "border-emerald-500 bg-emerald-500 text-white" : "border-rule bg-white"}`}>
                      {checked ? <Check className="h-4 w-4" /> : null}
                    </span>
                    {role}
                  </button>
                );
              })}
            </div>

            <div className="mt-6 rounded-md border border-white/80 bg-white/75 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Evidence / 依据</p>
              <p className="mt-2 text-sm leading-6 text-muted">{activeSticker.evidence}</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">{activeSticker.evidenceZh}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-rule bg-white">
        <div className="container py-10">
          <div className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr]">
            <div>
              <p className="page-no">Priority List</p>
              <h2 className="mt-2 font-sans text-2xl font-semibold">What needs to move next</h2>
              <p className="mt-2 text-sm leading-6 text-muted">
                A lightweight execution board for tactical meetings.
                <br />
                一个用于战术会议的轻量执行看板。
              </p>
              <div className="mt-6 flex items-center gap-2 text-sm text-muted">
                <CalendarDays className="h-4 w-4" />
                Timeline starts on June 21, 2026 / 时间线从 2026-06-21 开始
              </div>
            </div>

            <div className="overflow-hidden rounded-lg border border-rule bg-paper">
              <div className="grid grid-cols-[0.45fr_1.4fr_1.15fr_0.75fr_0.8fr] border-b border-rule bg-ink px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-paper">
                <span>P</span>
                <span>Task</span>
                <span>任务</span>
                <span>Owner</span>
                <span>Due</span>
              </div>
              {priorityRows.map((row) => (
                <div key={`${row[0]}-${row[1]}`} className="grid grid-cols-[0.45fr_1.4fr_1.15fr_0.75fr_0.8fr] gap-2 border-b border-rule px-4 py-3 text-sm last:border-b-0">
                  <span className="font-mono text-xs font-semibold text-indigo-700">{row[0]}</span>
                  <span className="font-medium text-ink">{row[1]}</span>
                  <span className="text-muted">{row[2]}</span>
                  <span className="text-muted">{row[3]}</span>
                  <span className="font-mono text-xs text-muted">{row[4]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function InfoBlock({
  title,
  titleZh,
  body,
  bodyZh
}: {
  title: string;
  titleZh: string;
  body: string;
  bodyZh: string;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
        {title} / {titleZh}
      </p>
      <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
      <p className="mt-1 text-sm leading-6 text-slate-600">{bodyZh}</p>
    </div>
  );
}

function DdlRow({ label, ddl }: { label: string; ddl: string }) {
  return (
    <div className="grid grid-cols-[1.2fr_0.8fr] border-t border-rule px-3 py-2 text-sm">
      <span className="font-medium text-ink">{label}</span>
      <span className="font-mono text-xs text-muted">{ddl}</span>
    </div>
  );
}

function CircleChecklist({
  title,
  group,
  items,
  isChecked,
  onToggle
}: {
  title: string;
  group: string;
  items: string[];
  isChecked: (group: string, item: string) => boolean;
  onToggle: (group: string, item: string) => void;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">{title}</p>
      <div className="mt-2 grid gap-2">
        {items.map((item) => {
          const checked = isChecked(group, item);
          return (
            <button
              key={item}
              type="button"
              onClick={() => onToggle(group, item)}
              className={`flex items-center gap-3 rounded-md border px-3 py-2 text-left text-sm transition ${
                checked
                  ? "border-emerald-400 bg-emerald-50 text-ink"
                  : "border-rule bg-paper text-muted hover:border-indigo-300 hover:bg-indigo-50"
              }`}
            >
              <span
                className={`grid h-5 w-5 shrink-0 place-items-center rounded border ${
                  checked ? "border-emerald-500 bg-emerald-500 text-white" : "border-rule bg-white"
                }`}
              >
                {checked ? <Check className="h-3.5 w-3.5" /> : null}
              </span>
              <span>{item}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
