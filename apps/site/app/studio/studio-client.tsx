"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  BookOpenCheck,
  Brain,
  Captions,
  CheckCircle2,
  ChevronDown,
  Clapperboard,
  Clipboard,
  Download,
  Gauge,
  Image as ImageIcon,
  KeyRound,
  Layers3,
  MonitorPlay,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Settings2,
  Sparkles,
  Workflow
} from "lucide-react";
import { site } from "@/lib/site";

type RunState = "idle" | "running" | "done";
type OutputTab = "comic" | "video" | "exports";

type StudioForm = {
  title: string;
  course: string;
  subject: string;
  outputMode: string;
  language: string;
  source: string;
  visualQa: boolean;
  bilingualCaptions: boolean;
};

const projects: Array<{ id: string; name: string; meta: string; form: StudioForm }> = [
  {
    id: "comic-book",
    name: "AI Comic Book",
    meta: "AP Calculus AB · Video workflow",
    form: {
      title: "Riemann Sum",
      course: "AP Calculus AB",
      subject: "Math / 数学",
      outputMode: "Comic + Video / 漫画 + 视频",
      language: "English + Chinese / 中英文",
      source:
        "Students learn how a Riemann sum approximates area under a curve by splitting a region into rectangles.",
      visualQa: true,
      bilingualCaptions: true
    }
  },
  {
    id: "future-academy",
    name: "Future Academy",
    meta: "Story universe · IP system",
    form: {
      title: "Academy Bridge Mission",
      course: "Grade 6 Math",
      subject: "Math / 数学",
      outputMode: "Comic + Video / 漫画 + 视频",
      language: "English + Chinese / 中英文",
      source:
        "A damaged bridge needs equal beam spacing. Students use ratio and unit rate to choose the repair plan.",
      visualQa: true,
      bilingualCaptions: true
    }
  }
];

const generationSteps = [
  {
    id: "ingest",
    n: "01",
    name: "Ingest",
    zh: "导入",
    detail: "Read notes, standards, and lesson objective.",
    done: "Source content parsed into a lesson object."
  },
  {
    id: "lesson",
    n: "02",
    name: "Lesson Map",
    zh: "课程图谱",
    detail: "Claude extracts misconception, sequence, and assessment.",
    done: "Claude mapped learning objective, misconception, and exit question."
  },
  {
    id: "story",
    n: "03",
    name: "Story",
    zh: "故事",
    detail: "Convert one subject objective into academy mission beats.",
    done: "Story mission generated without mixing subjects."
  },
  {
    id: "storyboard",
    n: "04",
    name: "Storyboard",
    zh: "分镜",
    detail: "Create comic panels with learning and narrative beats.",
    done: "Six comic pages and panel beats prepared."
  },
  {
    id: "qa",
    n: "05",
    name: "Visual QA",
    zh: "视觉 QA",
    detail: "Gemini checks page clarity, character consistency, and diagrams.",
    done: "Gemini visual QA score: 94 / 100."
  },
  {
    id: "video",
    n: "06",
    name: "Video Pack",
    zh: "视频包",
    detail: "Generate start/end frames, shot prompts, captions, and voiceover.",
    done: "VideoShot packet, subtitles, and voiceover generated."
  },
  {
    id: "export",
    n: "07",
    name: "Export",
    zh: "导出",
    detail: "Publish PDF, worksheet, teacher preview, and social cuts.",
    done: "Exports are ready for download."
  }
];

const apiCards: Array<{
  icon: LucideIcon;
  name: string;
  zh: string;
  body: string;
  bodyZh: string;
}> = [
  {
    icon: Brain,
    name: "Claude",
    zh: "课程与故事推理",
    body: "Lesson reasoning, subject thinking mode, story adaptation, director packet, and QA rubric.",
    bodyZh: "负责课程推理、学科思维、故事转译、导演包和 QA 标准。"
  },
  {
    icon: Sparkles,
    name: "Gemini",
    zh: "多模态与视觉判断",
    body: "Visual reading, image consistency, frame prompts, page review, and video-ready asset checks.",
    bodyZh: "负责多模态理解、画面一致性、首尾帧提示词、页面审核和视频资产判断。"
  }
];

const videoOutputs: Array<{ icon: LucideIcon; name: string; zh: string; detail: string }> = [
  { icon: ImageIcon, name: "Start frame", zh: "首帧", detail: "Stable source image from comic panel." },
  { icon: Layers3, name: "End frame", zh: "尾帧", detail: "Final pose, diagram, and concept reveal." },
  { icon: Clapperboard, name: "Shot clip", zh: "镜头片段", detail: "Camera, voiceover, subtitle, and sound cue." },
  { icon: Captions, name: "Lesson hook", zh: "课程钩子", detail: "10-20 second opener for class or social media." },
  { icon: MonitorPlay, name: "Full video", zh: "完整视频", detail: "2-5 minute narrated comic lesson." }
];

const subjectOptions = [
  "Math / 数学",
  "English / 英语",
  "Physics / 物理",
  "Chemistry / 化学",
  "Business / 商业",
  "Psychology / 心理",
  "Geography / 地理"
];

const outputOptions = [
  "Comic only / 只生成漫画",
  "Comic + Video / 漫画 + 视频",
  "Video pack only / 只生成视频包"
];

const languageOptions = ["English / 英文", "Chinese / 中文", "English + Chinese / 中英文"];

export function StudioClient() {
  const pages = site.showcase.unit1.pages;
  const [activeProjectId, setActiveProjectId] = useState(projects[0].id);
  const [form, setForm] = useState<StudioForm>(projects[0].form);
  const [runState, setRunState] = useState<RunState>("idle");
  const [activeStep, setActiveStep] = useState(0);
  const [logs, setLogs] = useState<string[]>(["Studio ready. Click Generate to run the workflow."]);
  const [selectedPage, setSelectedPage] = useState(0);
  const [activeTab, setActiveTab] = useState<OutputTab>("comic");
  const [toast, setToast] = useState("");

  const completedSteps = runState === "done" ? generationSteps.length : activeStep;
  const progress = Math.round((completedSteps / generationSteps.length) * 100);
  const canExport = runState === "done";

  const directorPacket = useMemo(
    () =>
      JSON.stringify(
        {
          sourcePanelId: `page_${selectedPage + 1}_panel_02`,
          title: form.title,
          subject: form.subject,
          course: form.course,
          modelPolicy: "Claude + Gemini only",
          language: form.language,
          output: form.outputMode,
          shot: {
            camera: "slow dolly-in",
            duration: "5s",
            visualFocus: "comic panel -> diagram reveal",
            voiceover: `Today we use ${form.title} to solve the mission.`,
            subtitle: `${form.title} / ${form.subject}`,
            needsEndFrame: true
          }
        },
        null,
        2
      ),
    [form, selectedPage]
  );

  useEffect(() => {
    if (runState !== "running") return;

    if (activeStep >= generationSteps.length) return;

    const step = generationSteps[activeStep];
    const timer = window.setTimeout(() => {
      const nextStep = activeStep + 1;
      setLogs((current) => [
        ...current,
        `✓ ${step.done}`,
        `  ${step.zh} completed for "${form.title}".`,
        ...(nextStep >= generationSteps.length
          ? ["✓ Done. Comic pages, video pack, and exports are ready."]
          : [])
      ]);
      setActiveStep(nextStep);
      if (nextStep >= generationSteps.length) {
        setRunState("done");
        setActiveTab("comic");
      }
    }, 650);

    return () => window.clearTimeout(timer);
  }, [activeStep, form.title, runState]);

  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 1800);
  }

  function updateForm<K extends keyof StudioForm>(key: K, value: StudioForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    if (runState !== "idle") {
      setRunState("idle");
      setActiveStep(0);
      setLogs(["Inputs changed. Click Generate to run again."]);
    }
  }

  function loadProject(projectId: string) {
    const project = projects.find((item) => item.id === projectId) ?? projects[0];
    setActiveProjectId(project.id);
    setForm(project.form);
    setRunState("idle");
    setActiveStep(0);
    setSelectedPage(0);
    setActiveTab("comic");
    setLogs([`Loaded project: ${project.name}.`]);
  }

  function newProject() {
    setActiveProjectId("new");
    setForm({
      title: "",
      course: "",
      subject: "Math / 数学",
      outputMode: "Comic + Video / 漫画 + 视频",
      language: "English + Chinese / 中英文",
      source: "",
      visualQa: true,
      bilingualCaptions: true
    });
    setRunState("idle");
    setActiveStep(0);
    setActiveTab("comic");
    setLogs(["New project created. Fill the lesson setup, then click Generate."]);
  }

  function startRun() {
    if (!form.title.trim() || !form.course.trim() || !form.source.trim()) {
      notify("Please fill title, course, and source content first. / 请先填写标题、课程和内容。");
      return;
    }

    setRunState("running");
    setActiveStep(0);
    setActiveTab("comic");
    setLogs([
      `Run started: ${form.title}`,
      "→ Claude is preparing the lesson map.",
      "→ Gemini is standing by for visual QA."
    ]);
  }

  function pauseRun() {
    setRunState("idle");
    setLogs((current) => [...current, "Paused. Click Generate to restart from step 01."]);
  }

  function downloadText(filename: string, text: string, type = "text/plain") {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    notify(`Downloaded ${filename}.`);
  }

  async function copyDirectorPacket() {
    try {
      await navigator.clipboard.writeText(directorPacket);
      notify("Director packet copied. / 导演包已复制。");
    } catch {
      downloadText("director-packet.json", directorPacket, "application/json");
    }
  }

  const pageMetrics = [
    ["Pages", "页数", "6"],
    ["Progress", "进度", `${progress}%`],
    ["Language", "语言", form.language.replace(" / ", " + ")],
    ["Mode", "模式", form.outputMode.split(" / ")[0]]
  ];

  return (
    <section className="min-h-screen border-b border-rule bg-[#f7f8fb]">
      {toast ? (
        <div className="fixed right-4 top-20 z-50 max-w-sm rounded-md border border-rule bg-ink px-4 py-3 text-sm text-paper shadow-paper">
          {toast}
        </div>
      ) : null}

      <div className="grid min-h-screen lg:grid-cols-[18rem_1fr]">
        <aside className="border-b border-rule bg-white lg:border-b-0 lg:border-r">
          <div className="sticky top-16 p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-md bg-lime-300 font-serif text-lg font-bold text-ink">
                C
              </span>
              <div>
                <p className="font-sans text-base font-semibold">ComicLearn Studio</p>
                <p className="text-xs text-muted">AI 漫画课程工作台</p>
              </div>
            </div>

            <button
              type="button"
              data-testid="new-project"
              onClick={newProject}
              className="mt-8 flex w-full items-center justify-center gap-2 rounded-md bg-ink px-4 py-3 text-sm font-semibold text-paper shadow-chip transition hover:bg-ink/90"
            >
              <Plus className="h-4 w-4" />
              New project / 新项目
            </button>

            <div className="mt-8">
              <p className="page-no">My projects / 我的项目</p>
              <div className="mt-3 space-y-3">
                {projects.map((project) => (
                  <button
                    type="button"
                    key={project.id}
                    data-testid={`project-${project.id}`}
                    onClick={() => loadProject(project.id)}
                    className={`w-full rounded-md border p-4 text-left shadow-chip transition ${
                      activeProjectId === project.id
                        ? "border-ink bg-paper"
                        : "border-dashed border-rule bg-white hover:border-ink/30"
                    }`}
                  >
                    <p className="text-sm font-semibold text-ink">{project.name}</p>
                    <p className="mt-1 text-xs leading-5 text-muted">{project.meta}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-8 rounded-md border border-rule bg-cream/50 p-4">
              <div className="flex items-center gap-2">
                <KeyRound className="h-4 w-4 text-indigo-700" />
                <p className="font-sans text-sm font-semibold">API Guard / API 限制</p>
              </div>
              <p className="mt-3 text-xs leading-5 text-muted">
                MVP uses Claude + Gemini only. Other providers are disabled.
                <span className="mt-2 block text-ink/75">
                  当前 MVP 只使用 Claude 和 Gemini，其他供应商暂不接入。
                </span>
              </p>
            </div>
          </div>
        </aside>

        <main className="min-w-0">
          <div className="border-b border-rule bg-white px-5 py-5 md:px-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="chip">
                    <MonitorPlay className="h-3.5 w-3.5 text-indigo-600" />
                    Interactive Studio / 可操作工作台
                  </span>
                  <span className="chip">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                    Claude + Gemini only
                  </span>
                </div>
                <h1 className="mt-4 font-serif text-3xl font-semibold leading-tight text-ink md:text-4xl">
                  AI Comic Book Studio
                  <span className="mt-1 block text-xl text-ink/75 md:text-2xl">AI 漫画课程生成工作台</span>
                </h1>
              </div>

              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => setActiveTab("exports")} className="btn-secondary px-4 py-2">
                  <Settings2 className="h-4 w-4" />
                  Settings / 设置
                </button>
                {runState === "running" ? (
                  <button type="button" data-testid="pause-run" onClick={pauseRun} className="btn-secondary px-4 py-2">
                    <Pause className="h-4 w-4" />
                    Pause / 暂停
                  </button>
                ) : (
                  <button type="button" data-testid="generate-top" onClick={startRun} className="btn-primary px-4 py-2">
                    <Play className="h-4 w-4" />
                    Generate / 生成
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="grid gap-5 p-5 md:p-8 xl:grid-cols-[23rem_1fr]">
            <section className="space-y-5">
              <div className="rounded-paper border border-rule bg-white p-5 shadow-paper">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="page-no">New generation / 新生成</p>
                    <h2 className="mt-2 font-sans text-lg font-semibold">Lesson setup / 课程设置</h2>
                  </div>
                  <BookOpenCheck className="h-5 w-5 text-indigo-700" />
                </div>

                <div className="mt-5 space-y-4">
                  <StudioField
                    label="Title / Topic"
                    labelZh="标题 / 主题"
                    value={form.title}
                    onChange={(value) => updateForm("title", value)}
                    placeholder="e.g. Riemann Sum"
                    testId="title-input"
                  />
                  <StudioField
                    label="Grade / Course"
                    labelZh="年级 / 课程"
                    value={form.course}
                    onChange={(value) => updateForm("course", value)}
                    placeholder="e.g. AP Calculus AB"
                    testId="course-input"
                  />
                  <StudioSelect
                    label="Subject"
                    labelZh="学科"
                    value={form.subject}
                    options={subjectOptions}
                    onChange={(value) => updateForm("subject", value)}
                    testId="subject-select"
                  />
                  <StudioSelect
                    label="Output mode"
                    labelZh="输出模式"
                    value={form.outputMode}
                    options={outputOptions}
                    onChange={(value) => updateForm("outputMode", value)}
                    testId="output-mode-select"
                  />
                  <StudioSelect
                    label="Language"
                    labelZh="语言"
                    value={form.language}
                    options={languageOptions}
                    onChange={(value) => updateForm("language", value)}
                    testId="language-select"
                  />
                  <label className="block">
                    <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
                      Source content
                    </span>
                    <span className="mt-1 block text-xs text-ink/65">课程内容</span>
                    <textarea
                      data-testid="source-textarea"
                      value={form.source}
                      onChange={(event) => updateForm("source", event.target.value)}
                      rows={5}
                      className="mt-2 w-full resize-none rounded-md border border-rule bg-paper px-3 py-3 text-sm leading-6 text-ink shadow-chip outline-none transition focus:border-indigo-500"
                      placeholder="Paste notes, learning guide, or textbook excerpt..."
                    />
                  </label>
                  <label className="flex items-start gap-3 rounded-md border border-rule bg-paper p-3 text-sm">
                    <input
                      type="checkbox"
                      checked={form.visualQa}
                      onChange={(event) => updateForm("visualQa", event.target.checked)}
                      className="mt-1"
                    />
                    <span>
                      Run Gemini visual QA
                      <span className="block text-muted">运行 Gemini 视觉 QA</span>
                    </span>
                  </label>
                  <label className="flex items-start gap-3 rounded-md border border-rule bg-paper p-3 text-sm">
                    <input
                      type="checkbox"
                      checked={form.bilingualCaptions}
                      onChange={(event) => updateForm("bilingualCaptions", event.target.checked)}
                      className="mt-1"
                    />
                    <span>
                      Bilingual captions
                      <span className="block text-muted">中英文字幕</span>
                    </span>
                  </label>
                </div>

                <button
                  type="button"
                  data-testid="generate-main"
                  onClick={startRun}
                  className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-lime-300 px-4 py-3 text-sm font-semibold text-ink shadow-chip transition hover:bg-lime-200"
                >
                  {runState === "done" ? <RefreshCw className="h-4 w-4" /> : <ArrowRight className="h-4 w-4" />}
                  {runState === "done" ? "Regenerate / 重新生成" : "Generate comic lesson / 生成漫画课程"}
                </button>
              </div>

              <div className="rounded-paper border border-rule bg-white p-5 shadow-paper">
                <div className="flex items-center gap-2">
                  <KeyRound className="h-5 w-5 text-indigo-700" />
                  <h2 className="font-sans text-lg font-semibold">API Settings / API 设置</h2>
                </div>

                <div className="mt-5 grid gap-3">
                  {apiCards.map((api) => {
                    const Icon = api.icon;
                    return (
                      <div key={api.name} className="rounded-md border border-rule bg-paper p-4">
                        <div className="flex items-center gap-3">
                          <span className="grid h-9 w-9 place-items-center rounded-md bg-indigo-50 text-indigo-700">
                            <Icon className="h-4 w-4" />
                          </span>
                          <div>
                            <p className="font-sans text-sm font-semibold">{api.name}</p>
                            <p className="text-xs text-muted">{api.zh}</p>
                          </div>
                        </div>
                        <p className="mt-3 text-xs leading-5 text-muted">{api.body}</p>
                        <p className="mt-1 text-xs leading-5 text-ink/75">{api.bodyZh}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>

            <section className="min-w-0 space-y-5">
              <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
                <div className="rounded-paper border border-rule bg-white p-5 shadow-paper">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="page-no">Pipeline progress / 流程进度</p>
                      <h2 className="mt-2 font-sans text-lg font-semibold">Lesson-to-comic-to-video run</h2>
                      <p className="mt-1 text-sm text-muted">从课程到漫画再到视频的一次生成</p>
                    </div>
                    <span data-testid="run-status" className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${statusClass(runState)}`}>
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      {runState === "running" ? "Running / 运行中" : runState === "done" ? "Done / 已完成" : "Ready / 可运行"}
                    </span>
                  </div>

                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-rule">
                    <div data-testid="progress-bar" className="h-full rounded-full bg-lime-300 transition-all" style={{ width: `${progress}%` }} />
                  </div>

                  <div className="mt-5 grid gap-2 md:grid-cols-7">
                    {generationSteps.map((step, index) => (
                      <button
                        type="button"
                        key={step.id}
                        data-testid={`step-${step.id}`}
                        onClick={() => {
                          setActiveStep(index);
                          setLogs((current) => [...current, `Selected step ${step.n}: ${step.name}.`]);
                        }}
                        className={`rounded-md border px-3 py-2 text-left transition ${stepClass(index, activeStep, runState)}`}
                      >
                        <p className="font-mono text-[0.65rem]">{step.n}</p>
                        <p className="mt-1 text-xs font-semibold">{step.name}</p>
                        <p className="text-[0.7rem]">{step.zh}</p>
                      </button>
                    ))}
                  </div>

                  <div className="mt-5 rounded-md border border-rule bg-ink p-4 text-paper">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Workflow className="h-4 w-4 text-lime-300" />
                        <p className="font-mono text-xs uppercase text-paper/60">Run log / 运行日志</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setLogs(["Log cleared."])}
                        className="rounded-md border border-white/10 px-2 py-1 text-xs text-paper/70 hover:bg-white/10"
                      >
                        Clear
                      </button>
                    </div>
                    <div data-testid="run-log" className="mt-3 max-h-56 space-y-2 overflow-auto font-mono text-xs leading-6">
                      {logs.map((line, index) => (
                        <p key={`${line}-${index}`} className="text-paper/85">
                          {line}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="rounded-paper border border-rule bg-white p-5 shadow-paper">
                  <div className="flex items-center gap-2">
                    <Gauge className="h-5 w-5 text-indigo-700" />
                    <h2 className="font-sans text-lg font-semibold">Run summary / 生成摘要</h2>
                  </div>
                  <div className="mt-5 grid grid-cols-2 gap-3">
                    {pageMetrics.map(([label, zh, value]) => (
                      <div key={label} className="rounded-md border border-rule bg-paper p-4">
                        <p className="font-mono text-xs uppercase text-muted">{label}</p>
                        <p className="text-xs text-ink/65">{zh}</p>
                        <p className="mt-2 break-words font-serif text-xl font-semibold text-ink">{value}</p>
                      </div>
                    ))}
                  </div>
                  <div className="mt-5 rounded-md border border-dashed border-rule bg-cream/40 p-4">
                    <p className="text-sm font-semibold text-ink">MVP rule / MVP 规则</p>
                    <p className="mt-2 text-sm leading-6 text-muted">
                      Claude generates the teachable structure. Gemini reviews and stabilizes the visual output.
                      <span className="mt-1 block text-ink/75">
                        Claude 生成可教学结构，Gemini 审核并稳定视觉输出。
                      </span>
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-paper border border-rule bg-white p-5 shadow-paper">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="page-no">Output workspace / 输出工作区</p>
                    <h2 className="mt-2 font-sans text-lg font-semibold">{form.title || "Untitled lesson"}</h2>
                    <p className="mt-1 text-sm text-muted">{form.course || "No course selected"} · {form.subject}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(["comic", "video", "exports"] as const).map((tab) => (
                      <button
                        type="button"
                        key={tab}
                        data-testid={`tab-${tab}`}
                        onClick={() => setActiveTab(tab)}
                        className={`rounded-md border px-3 py-2 text-sm font-medium transition ${
                          activeTab === tab ? "border-ink bg-ink text-paper" : "border-rule bg-white text-ink hover:border-ink/30"
                        }`}
                      >
                        {tab === "comic" ? "Comic / 漫画" : tab === "video" ? "Video / 视频" : "Export / 导出"}
                      </button>
                    ))}
                  </div>
                </div>

                {activeTab === "comic" ? (
                  <div className="mt-5 grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
                    <div className="rounded-md border border-rule bg-paper p-3">
                      <div className="relative aspect-[3/4] overflow-hidden rounded-md border border-rule bg-white">
                        <Image
                          src={pages[selectedPage]}
                          alt={`Selected generated comic page ${selectedPage + 1}`}
                          fill
                          sizes="(min-width: 1280px) 22rem, 88vw"
                          className="object-cover"
                          priority
                        />
                      </div>
                      <p className="mt-3 text-sm font-semibold">Selected page {selectedPage + 1} / 当前页面 {selectedPage + 1}</p>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                      {pages.map((src, index) => (
                        <button
                          type="button"
                          key={src}
                          data-testid={`page-thumb-${index + 1}`}
                          onClick={() => setSelectedPage(index)}
                          className={`overflow-hidden rounded-md border bg-paper text-left shadow-chip transition ${
                            selectedPage === index ? "border-indigo-600 ring-2 ring-indigo-100" : "border-rule hover:border-ink/30"
                          }`}
                        >
                          <div className="relative aspect-[3/4] bg-white">
                            <Image
                              src={src}
                              alt={`Generated AP Calculus comic page ${index + 1}`}
                              fill
                              sizes="(min-width: 1280px) 15rem, (min-width: 640px) 42vw, 88vw"
                              className="object-cover"
                            />
                          </div>
                          <div className="flex items-center justify-between gap-3 px-3 py-3">
                            <div>
                              <p className="font-sans text-sm font-semibold">Page {index + 1}</p>
                              <p className="text-xs text-muted">页面 {index + 1}</p>
                            </div>
                            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
                              QA 94
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}

                {activeTab === "video" ? (
                  <div className="mt-5 space-y-5">
                    <div className="grid gap-3 md:grid-cols-5">
                      {videoOutputs.map((output, index) => {
                        const Icon = output.icon;
                        return (
                          <button
                            type="button"
                            key={output.name}
                            data-testid={`video-output-${index + 1}`}
                            onClick={() => {
                              setLogs((current) => [...current, `Opened ${output.name} editor.`]);
                              notify(`${output.name} selected.`);
                            }}
                            className="rounded-md border border-rule bg-paper p-4 text-left transition hover:border-ink/30"
                          >
                            <div className="mb-4 flex items-center justify-between">
                              <span className="grid h-9 w-9 place-items-center rounded-md bg-white text-indigo-700 shadow-chip">
                                <Icon className="h-4 w-4" />
                              </span>
                              <span className="font-mono text-xs text-muted">0{index + 1}</span>
                            </div>
                            <p className="font-sans text-sm font-semibold">{output.name}</p>
                            <p className="text-xs font-medium text-ink/70">{output.zh}</p>
                            <p className="mt-2 text-xs leading-5 text-muted">{output.detail}</p>
                          </button>
                        );
                      })}
                    </div>

                    <div className="grid gap-4 rounded-md border border-rule bg-ink p-4 text-paper lg:grid-cols-[1fr_1fr]">
                      <div>
                        <p className="font-mono text-xs uppercase text-paper/60">Director packet / 导演包</p>
                        <p className="mt-2 text-sm leading-6 text-paper/85">
                          The packet updates when you edit the lesson setup or select a different comic page.
                        </p>
                        <button
                          type="button"
                          data-testid="copy-packet"
                          onClick={copyDirectorPacket}
                          className="mt-4 inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-semibold text-ink"
                        >
                          <Clipboard className="h-4 w-4" />
                          Copy packet / 复制
                        </button>
                      </div>
                      <pre className="max-h-80 overflow-auto rounded-md border border-white/10 bg-white/5 p-3 text-xs leading-6 text-paper/85">
                        {directorPacket}
                      </pre>
                    </div>
                  </div>
                ) : null}

                {activeTab === "exports" ? (
                  <div className="mt-5 grid gap-4 md:grid-cols-3">
                    <ExportButton
                      disabled={!canExport}
                      title="Run JSON"
                      zh="运行数据"
                      body="Download the current run configuration and generated packet."
                      testId="export-run-json"
                      onClick={() => downloadText("comiclearn-run.json", directorPacket, "application/json")}
                    />
                    <ExportButton
                      disabled={!canExport}
                      title="Teacher Notes"
                      zh="教师说明"
                      body="Download a markdown teacher-facing lesson note."
                      testId="export-teacher-notes"
                      onClick={() =>
                        downloadText(
                          "teacher-notes.md",
                          `# ${form.title}\n\nCourse: ${form.course}\nSubject: ${form.subject}\n\n## Source\n${form.source}\n\n## Models\nClaude + Gemini only\n`
                        )
                      }
                    />
                    <ExportButton
                      disabled={!canExport}
                      title="Video Packet"
                      zh="视频包"
                      body="Download the director packet for start/end frames and captions."
                      testId="export-video-packet"
                      onClick={() => downloadText("video-packet.json", directorPacket, "application/json")}
                    />
                  </div>
                ) : null}
              </div>
            </section>
          </div>
        </main>
      </div>
    </section>
  );
}

function StudioField({
  label,
  labelZh,
  value,
  placeholder,
  testId,
  onChange
}: {
  label: string;
  labelZh: string;
  value: string;
  placeholder: string;
  testId: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">{label}</span>
      <span className="mt-1 block text-xs text-ink/65">{labelZh}</span>
      <input
        data-testid={testId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-2 w-full rounded-md border border-rule bg-paper px-3 py-3 text-sm text-ink shadow-chip outline-none transition focus:border-indigo-500"
      />
    </label>
  );
}

function StudioSelect({
  label,
  labelZh,
  value,
  options,
  testId,
  onChange
}: {
  label: string;
  labelZh: string;
  value: string;
  options: string[];
  testId: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">{label}</span>
      <span className="mt-1 block text-xs text-ink/65">{labelZh}</span>
      <span className="relative mt-2 block">
        <select
          data-testid={testId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full appearance-none rounded-md border border-rule bg-paper px-3 py-3 pr-9 text-sm text-ink shadow-chip outline-none transition focus:border-indigo-500"
        >
          {options.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
      </span>
    </label>
  );
}

function ExportButton({
  title,
  zh,
  body,
  disabled,
  testId,
  onClick
}: {
  title: string;
  zh: string;
  body: string;
  disabled: boolean;
  testId: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      disabled={disabled}
      onClick={onClick}
      className="rounded-md border border-rule bg-paper p-5 text-left shadow-chip transition enabled:hover:border-ink/30 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <Download className="h-5 w-5 text-indigo-700" />
      <p className="mt-4 font-sans text-base font-semibold">{title}</p>
      <p className="text-sm text-ink/70">{zh}</p>
      <p className="mt-2 text-sm leading-6 text-muted">{disabled ? "Run Generate first. / 请先生成。" : body}</p>
    </button>
  );
}

function statusClass(runState: RunState) {
  if (runState === "running") return "border-amber-200 bg-amber-50 text-amber-700";
  if (runState === "done") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function stepClass(index: number, activeStep: number, runState: RunState) {
  if (runState === "done" || index < activeStep) {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (runState === "running" && index === activeStep) {
    return "border-amber-300 bg-amber-50 text-amber-800";
  }
  return "border-rule bg-paper text-muted hover:border-ink/30";
}
