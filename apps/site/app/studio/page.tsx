import type { Metadata } from "next";
import Image from "next/image";
import {
  ArrowRight,
  BookOpenCheck,
  Brain,
  Captions,
  CheckCircle2,
  ChevronDown,
  Clapperboard,
  Download,
  Film,
  Gauge,
  Image as ImageIcon,
  KeyRound,
  Layers3,
  MonitorPlay,
  Plus,
  Settings2,
  Sparkles,
  Workflow
} from "lucide-react";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Studio | 创作工作台",
  description:
    "ComicLearn Studio preview with bilingual lesson generation, Claude + Gemini API settings, comic output, and video workflow."
};

const generationSteps = [
  ["01", "Ingest", "导入", "Read notes, standards, and lesson objective."],
  ["02", "Lesson Map", "课程图谱", "Claude extracts misconception, sequence, and assessment."],
  ["03", "Story", "故事", "Convert one subject objective into academy mission beats."],
  ["04", "Storyboard", "分镜", "Create comic panels with learning and narrative beats."],
  ["05", "Visual QA", "视觉 QA", "Gemini checks page clarity, character consistency, and diagrams."],
  ["06", "Video Pack", "视频包", "Generate start/end frames, shot prompts, captions, and voiceover."],
  ["07", "Export", "导出", "Publish PDF, worksheet, teacher preview, and social cuts."]
];

const apiCards = [
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

const logLines = [
  ["✓", "Claude lesson map ready", "Claude 课程图谱已生成"],
  ["✓", "Storyboard uses one math objective only", "分镜只服务一个数学目标"],
  ["✓", "Gemini visual QA score: 94 / 100", "Gemini 视觉 QA：94 / 100"],
  ["→", "Preparing video shot pack", "正在准备视频镜头包"],
  ["•", "No third-party video API connected in MVP", "MVP 暂不接入其他视频 API"]
];

const videoOutputs = [
  ["Start frame", "首帧", "Stable source image from comic panel"],
  ["End frame", "尾帧", "Final pose, diagram, and concept reveal"],
  ["Shot clip", "镜头片段", "Camera direction, voiceover, subtitle, sound cue"],
  ["Lesson hook", "课程钩子", "10-20 second opener for class or social media"],
  ["Full video", "完整视频", "2-5 minute narrated comic lesson"]
];

const pageMetrics = [
  ["Pages", "页数", "6"],
  ["QA", "质量", "94"],
  ["Language", "语言", "EN + 中文"],
  ["Mode", "模式", "Comic + Video"]
];

export default function StudioPage() {
  const pages = site.showcase.unit1.pages;

  return (
    <section className="min-h-screen border-b border-rule bg-[#f7f8fb]">
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

            <button className="mt-8 flex w-full items-center justify-center gap-2 rounded-md bg-ink px-4 py-3 text-sm font-semibold text-paper shadow-chip">
              <Plus className="h-4 w-4" />
              New project / 新项目
            </button>

            <div className="mt-8">
              <p className="page-no">My projects / 我的项目</p>
              <div className="mt-3 rounded-md border border-rule bg-paper p-4 shadow-chip">
                <p className="font-sans text-sm font-semibold">AI Comic Book</p>
                <p className="mt-1 text-xs leading-5 text-muted">AP Calculus AB · Video workflow</p>
              </div>
              <div className="mt-3 rounded-md border border-dashed border-rule bg-white p-4">
                <p className="text-sm font-medium text-ink">Future Academy</p>
                <p className="mt-1 text-xs leading-5 text-muted">Story universe · IP system</p>
              </div>
            </div>

            <div className="mt-8 rounded-md border border-rule bg-cream/50 p-4">
              <div className="flex items-center gap-2">
                <KeyRound className="h-4 w-4 text-indigo-700" />
                <p className="font-sans text-sm font-semibold">API Guard / API 限制</p>
              </div>
              <p className="mt-3 text-xs leading-5 text-muted">
                MVP uses Claude + Gemini only. Other providers are intentionally disabled.
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
                    Studio Preview / 工作台预览
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
                <button className="btn-secondary px-4 py-2">
                  <Settings2 className="h-4 w-4" />
                  Settings / 设置
                </button>
                <button className="btn-primary px-4 py-2">
                  Generate / 生成
                  <ArrowRight className="h-4 w-4" />
                </button>
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
                  <StudioField label="Title / Topic" labelZh="标题 / 主题" value="Riemann Sum" />
                  <StudioField label="Grade / Course" labelZh="年级 / 课程" value="AP Calculus AB" />
                  <StudioSelect label="Subject" labelZh="学科" value="Math / 数学" />
                  <StudioSelect label="Output mode" labelZh="输出模式" value="Comic + Video / 漫画 + 视频" />
                  <StudioSelect label="Language" labelZh="语言" value="English + Chinese / 中英文" />
                </div>

                <button className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-lime-300 px-4 py-3 text-sm font-semibold text-ink shadow-chip transition hover:bg-lime-200">
                  Generate comic lesson / 生成漫画课程
                  <ArrowRight className="h-4 w-4" />
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
                    <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Ready / 可运行
                    </span>
                  </div>

                  <div className="mt-5 grid gap-2 md:grid-cols-7">
                    {generationSteps.map(([n, name, zh]) => (
                      <div key={n} className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2">
                        <p className="font-mono text-[0.65rem] text-emerald-700">{n}</p>
                        <p className="mt-1 text-xs font-semibold text-emerald-800">{name}</p>
                        <p className="text-[0.7rem] text-emerald-700/80">{zh}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-5 rounded-md border border-rule bg-ink p-4 text-paper">
                    <div className="flex items-center gap-2">
                      <Workflow className="h-4 w-4 text-lime-300" />
                      <p className="font-mono text-xs uppercase text-paper/60">Run log / 运行日志</p>
                    </div>
                    <div className="mt-3 space-y-2 font-mono text-xs leading-6">
                      {logLines.map(([mark, en, zh]) => (
                        <div key={en} className="grid gap-2 sm:grid-cols-[1.5rem_1fr]">
                          <span className="text-lime-300">{mark}</span>
                          <span className="text-paper/85">
                            {en}
                            <span className="block font-sans text-paper/65">{zh}</span>
                          </span>
                        </div>
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
                        <p className="mt-2 font-serif text-2xl font-semibold text-ink">{value}</p>
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
                    <p className="page-no">Generated pages / 已生成漫画页</p>
                    <h2 className="mt-2 font-sans text-lg font-semibold">AP Calculus AB sample</h2>
                    <p className="mt-1 text-sm text-muted">Sample comic pages become the source for video frames.</p>
                  </div>
                  <button className="btn-secondary px-4 py-2">
                    <Download className="h-4 w-4" />
                    Export / 导出
                  </button>
                </div>

                <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {pages.map((src, index) => (
                    <article key={src} className="overflow-hidden rounded-md border border-rule bg-paper shadow-chip">
                      <div className="relative aspect-[3/4] bg-white">
                        <Image
                          src={src}
                          alt={`Generated AP Calculus comic page ${index + 1}`}
                          fill
                          sizes="(min-width: 1280px) 18rem, (min-width: 640px) 42vw, 88vw"
                          className="object-cover"
                          priority={index < 2}
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
                    </article>
                  ))}
                </div>
              </div>

              <div className="rounded-paper border border-rule bg-white p-5 shadow-paper">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="page-no">Video workflow / 视频生成</p>
                    <h2 className="mt-2 font-sans text-lg font-semibold">From comic page to lesson video</h2>
                    <p className="mt-1 text-sm text-muted">从漫画页提取首帧、尾帧、镜头、字幕和旁白。</p>
                  </div>
                  <span className="chip">
                    <Film className="h-3.5 w-3.5 text-indigo-600" />
                    Video-ready / 可视频化
                  </span>
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-5">
                  {videoOutputs.map(([name, zh, detail], index) => (
                    <div key={name} className="rounded-md border border-rule bg-paper p-4">
                      <div className="mb-4 flex items-center justify-between">
                        <span className="grid h-9 w-9 place-items-center rounded-md bg-white text-indigo-700 shadow-chip">
                          {index === 0 ? <ImageIcon className="h-4 w-4" /> : index === 1 ? <Layers3 className="h-4 w-4" /> : index === 2 ? <Clapperboard className="h-4 w-4" /> : index === 3 ? <Captions className="h-4 w-4" /> : <MonitorPlay className="h-4 w-4" />}
                        </span>
                        <span className="font-mono text-xs text-muted">0{index + 1}</span>
                      </div>
                      <p className="font-sans text-sm font-semibold">{name}</p>
                      <p className="text-xs font-medium text-ink/70">{zh}</p>
                      <p className="mt-2 text-xs leading-5 text-muted">{detail}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-5 grid gap-4 rounded-md border border-rule bg-ink p-4 text-paper lg:grid-cols-[1fr_1fr]">
                  <div>
                    <p className="font-mono text-xs uppercase text-paper/60">Director packet / 导演包</p>
                    <p className="mt-2 text-sm leading-6 text-paper/85">
                      ComicPanel becomes VideoShot with camera, duration, visual focus, voiceover, subtitle, and end-frame requirement.
                    </p>
                  </div>
                  <div className="rounded-md border border-white/10 bg-white/5 p-3 font-mono text-xs leading-6 text-paper/85">
                    <p>{`{ sourcePanelId: "p03_panel02",`}</p>
                    <p>{`  modelPolicy: "Claude + Gemini only",`}</p>
                    <p>{`  language: "English + Chinese",`}</p>
                    <p>{`  output: "comic_pdf + video_pack" }`}</p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </main>
      </div>
    </section>
  );
}

function StudioField({ label, labelZh, value }: { label: string; labelZh: string; value: string }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">{label}</span>
      <span className="mt-1 block text-xs text-ink/65">{labelZh}</span>
      <input
        readOnly
        value={value}
        className="mt-2 w-full rounded-md border border-rule bg-paper px-3 py-3 text-sm text-ink shadow-chip outline-none"
      />
    </label>
  );
}

function StudioSelect({ label, labelZh, value }: { label: string; labelZh: string; value: string }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">{label}</span>
      <span className="mt-1 block text-xs text-ink/65">{labelZh}</span>
      <span className="mt-2 flex w-full items-center justify-between rounded-md border border-rule bg-paper px-3 py-3 text-sm text-ink shadow-chip">
        {value}
        <ChevronDown className="h-4 w-4 text-muted" />
      </span>
    </label>
  );
}
