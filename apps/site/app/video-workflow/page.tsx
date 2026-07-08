import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  Brain,
  BookOpenCheck,
  Captions,
  CheckCircle2,
  Clapperboard,
  Database,
  Film,
  KeyRound,
  Layers3,
  PackageCheck,
  Play,
  School,
  Settings2,
  Sparkles,
  Workflow
} from "lucide-react";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Video Workflow | 视频工作流",
  description:
    "ComicLearn's bilingual video workflow extends teachable comics into start frames, end frames, shot clips, lesson videos, and social cuts with Claude and Gemini only for the MVP."
};

const pipeline = [
  {
    icon: School,
    label: "LessonMeta",
    labelZh: "课程元数据",
    detail: "Standards, objective, misconception.",
    detailZh: "课程标准、学习目标、常见误区。"
  },
  {
    icon: BookOpenCheck,
    label: "ComicPanel",
    labelZh: "漫画分镜",
    detail: "Story beat plus learning beat.",
    detailZh: "每格同时承载剧情推进和知识点。"
  },
  {
    icon: Clapperboard,
    label: "VideoShot",
    labelZh: "视频镜头",
    detail: "Camera, voiceover, subtitle.",
    detailZh: "镜头语言、旁白、字幕与音效提示。"
  },
  {
    icon: Film,
    label: "Frames",
    labelZh: "首尾帧",
    detail: "Start frame plus end frame.",
    detailZh: "稳定角色、场景和知识图示。"
  },
  {
    icon: Play,
    label: "Lesson Video",
    labelZh: "课程视频",
    detail: "Shot clips plus social cuts.",
    detailZh: "课堂视频、APP 微课、社媒切片。"
  }
];

const apiProviders = [
  {
    icon: Brain,
    name: "Claude",
    nameZh: "Claude",
    role: "Curriculum reasoning, story adaptation, storyboard structure, director notes, and QA logic.",
    roleZh: "负责课程推理、故事转译、分镜结构、导演说明和 QA 逻辑。"
  },
  {
    icon: Sparkles,
    name: "Gemini",
    nameZh: "Gemini",
    role: "Multimodal reading, visual consistency checks, frame prompts, image review, and later video-ready asset judgment.",
    roleZh: "负责多模态理解、画面一致性检查、首尾帧提示词、图像审核，以及后续视频资产判断。"
  }
];

const apiRules = [
  {
    title: "Two-model MVP",
    titleZh: "双模型 MVP",
    body: "The first Vercel version only assumes Claude and Gemini. No other external generation API is part of the current workflow.",
    bodyZh: "第一版 Vercel 只假设使用 Claude 和 Gemini，不把其他外部生成 API 放进当前工作流。"
  },
  {
    title: "Structured handoff",
    titleZh: "结构化交接",
    body: "Claude writes stable learning objects and director packets; Gemini reads those packets as multimodal visual tasks.",
    bodyZh: "Claude 产出稳定的教学对象和导演包，Gemini 再把它们作为多模态视觉任务执行。"
  },
  {
    title: "Provider-light architecture",
    titleZh: "轻供应商架构",
    body: "The product stores lesson schema, IP assets, prompts, frames, QA scores, and export files so the platform is not locked to one prompt run.",
    bodyZh: "平台保存课程 schema、IP 素材、提示词、首尾帧、QA 分数和导出文件，而不是依赖单次 prompt。"
  }
];

const roles = [
  {
    icon: School,
    name: "Curriculum Analyst",
    nameZh: "课程分析 Agent",
    body: "Extracts grade band, standard, misconception, assessment moment, and the subject-specific thinking mode.",
    bodyZh: "提取年级段、课程标准、常见误区、测评点，以及每个学科独有的思维方式。"
  },
  {
    icon: Sparkles,
    name: "Story Adapter",
    nameZh: "故事转译 Agent",
    body: "Turns one learning objective into a mission inside the academy universe without mixing subjects.",
    bodyZh: "把单一学习目标转成学院宇宙里的任务剧情，同时保持一本书只服务一个学科。"
  },
  {
    icon: BookOpenCheck,
    name: "Comic Storyboarder",
    nameZh: "漫画分镜 Agent",
    body: "Builds comic pages where every panel carries both a narrative beat and a learning beat.",
    bodyZh: "生成漫画页结构，让每一格同时有剧情作用和教学作用。"
  },
  {
    icon: Clapperboard,
    name: "Education Video Director",
    nameZh: "教育视频导演 Agent",
    body: "Converts high-potential panels into camera language, start/end frames, motion prompts, and voiceover.",
    bodyZh: "把适合动态化的漫画格转成镜头语言、首尾帧、运动提示词和旁白。"
  },
  {
    icon: Captions,
    name: "Audio + Subtitle Designer",
    nameZh: "音频字幕 Agent",
    body: "Keeps teacher narration, dialogue, captions, and sound cues short enough for mobile learning.",
    bodyZh: "控制教师旁白、角色对话、字幕和音效提示，让内容适合移动端学习。"
  },
  {
    icon: Layers3,
    name: "Lesson S-Class Director",
    nameZh: "S 级课程导演 Agent",
    body: "Combines multiple shots into a coherent hook, concept reveal, application, and exit question.",
    bodyZh: "把多个镜头组合成完整的导入、概念揭示、应用练习和出口问题。"
  }
];

const stages = [
  {
    n: "01",
    title: "Learning skeleton",
    titleZh: "学习骨架",
    body: "Name the learning function before designing the shot.",
    bodyZh: "先确定镜头的教学功能，再决定画面和运动。"
  },
  {
    n: "02",
    title: "Visual + audio",
    titleZh: "视觉与音频",
    body: "Describe what students see, hear, and read on screen.",
    bodyZh: "明确学生在屏幕上看到、听到、读到什么。"
  },
  {
    n: "03",
    title: "Pedagogy control",
    titleZh: "教学控制",
    body: "Guide attention with diagrams, focus, pacing, and cognitive load.",
    bodyZh: "用图示、焦点、节奏和认知负荷控制学生注意力。"
  },
  {
    n: "04",
    title: "Start frame",
    titleZh: "首帧",
    body: "Generate a consistent first image from the comic panel and asset library.",
    bodyZh: "基于漫画格和素材库生成稳定的第一帧。"
  },
  {
    n: "05",
    title: "Motion + end frame",
    titleZh: "运动与尾帧",
    body: "Define movement, camera behavior, final pose, and video prompt.",
    bodyZh: "定义角色动作、镜头运动、最终姿态和视频提示词。"
  }
];

const qa = [
  ["One primary subject per lesson", "每节课只聚焦一个主学科"],
  ["Every shot has a learning function", "每个镜头都有明确教学功能"],
  ["Characters use knowledge to decide", "角色用知识做选择，而不是被动听讲"],
  ["Pet/IP prompts but never solves", "宠物 IP 提示思路，但不替学生解题"],
  ["Frames reuse the same asset library", "首尾帧复用同一套 IP 与场景素材"],
  ["Video ends with an assessment moment", "视频结尾必须有测评或反思点"]
];

const outputs = [
  ["Lesson hook", "课程钩子", "10-20s", "class opener / social clip", "课堂导入 / 社媒切片"],
  ["Concept reveal", "概念揭示", "30-60s", "app micro-lesson", "APP 微课"],
  ["Teacher preview", "教师预览", "60-90s", "B2B pilot sales", "B 端试点展示"],
  ["Full comic video", "完整漫画视频", "2-5min", "YouTube / course page", "YouTube / 课程页"]
];

export default function VideoWorkflowPage() {
  return (
    <>
      <section className="relative overflow-hidden border-b border-rule bg-white">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.08]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(15,23,42,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(15,23,42,0.18) 1px, transparent 1px)",
            backgroundSize: "28px 28px"
          }}
        />
        <div className="container relative py-16 md:py-24">
          <div className="grid items-center gap-12 lg:grid-cols-[0.92fr_1.08fr]">
            <div>
              <span className="chip">
                <KeyRound className="h-3.5 w-3.5 text-indigo-600" />
                Claude + Gemini MVP / 双模型先行版
              </span>
              <h1 className="mt-6 max-w-3xl font-serif text-4xl font-semibold leading-tight text-ink md:text-5xl">
                Turn a teachable comic into a bilingual lesson video.
                <span className="mt-3 block text-2xl leading-snug text-ink/80 md:text-3xl">
                  把可教学漫画延伸成中英文课程视频。
                </span>
              </h1>
              <p className="mt-6 max-w-prose text-base leading-8 text-muted md:text-lg">
                ComicLearn now treats each comic page as the master source for
                start frames, end frames, shot clips, voiceover, subtitles, and
                social cuts. The MVP API setting stays simple: Claude for reasoning
                and Gemini for multimodal visual work.
                <span className="mt-3 block">
                  ComicLearn 将每一页漫画作为首帧、尾帧、镜头片段、旁白、字幕和社媒切片的源文件。
                  当前 MVP 的 API 先只使用 Claude 和 Gemini，不接入其他供应商。
                </span>
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href={site.links.studio} className="btn-primary">
                  Open Studio / 打开 Studio
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link href="#pipeline" className="btn-secondary">
                  View pipeline / 查看流程
                </Link>
              </div>
            </div>

            <HeroBoard />
          </div>
        </div>
      </section>

      <section id="pipeline" className="container py-16 md:py-20">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="page-no">Pipeline / 流程</p>
            <h2 className="mt-3 font-serif text-3xl font-semibold">From lesson to moving lesson.</h2>
            <p className="mt-2 text-lg font-medium text-ink/75">从课程内容到动态课程视频。</p>
          </div>
          <p className="max-w-xl text-sm leading-6 text-muted">
            The workflow copies Moyin Creator's core production idea: structured
            knowledge first, reusable assets second, video prompts last.
            <span className="mt-2 block">
              这里借鉴魔因的生产思路：先结构化知识，再沉淀可复用资产，最后生成视频提示词。
            </span>
          </p>
        </div>

        <div className="mt-10 grid gap-3 md:grid-cols-5">
          {pipeline.map((item, index) => (
            <PipelineNode key={item.label} item={item} index={index} />
          ))}
        </div>
      </section>

      <section className="border-y border-rule bg-white">
        <div className="container py-16 md:py-20">
          <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr]">
            <div>
              <p className="page-no">API setting / API 设置</p>
              <h2 className="mt-3 font-serif text-3xl font-semibold">Claude + Gemini only.</h2>
              <p className="mt-2 text-lg font-medium text-ink/75">当前版本只保留 Claude 和 Gemini。</p>
              <p className="mt-4 text-sm leading-7 text-muted">
                The point is not to chase every generation API. ComicLearn first
                needs a controllable curriculum-to-comic-to-video pipeline where
                reasoning, assets, and QA are readable and repeatable.
                <span className="mt-2 block">
                  这一阶段不是追逐所有生成 API，而是先把课程到漫画再到视频的链路做稳定：
                  推理、素材和 QA 都要可读、可复用、可迭代。
                </span>
              </p>
            </div>

            <div className="grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                {apiProviders.map((provider) => (
                  <article key={provider.name} className="rounded-paper border border-rule bg-paper p-5 shadow-chip">
                    <div className="flex items-center gap-3">
                      <span className="grid h-10 w-10 place-items-center rounded-md bg-indigo-50 text-indigo-700">
                        <provider.icon className="h-5 w-5" />
                      </span>
                      <div>
                        <h3 className="font-sans text-lg font-semibold">{provider.name}</h3>
                        <p className="font-mono text-xs uppercase text-muted">{provider.nameZh}</p>
                      </div>
                    </div>
                    <p className="mt-4 text-sm leading-6 text-muted">{provider.role}</p>
                    <p className="mt-2 text-sm leading-6 text-ink/75">{provider.roleZh}</p>
                  </article>
                ))}
              </div>

              <div className="grid gap-3">
                {apiRules.map((rule) => (
                  <div key={rule.title} className="rounded-md border border-rule bg-cream/45 p-4">
                    <div className="flex items-center gap-2">
                      <Settings2 className="h-4 w-4 text-emerald-700" />
                      <h3 className="font-sans text-sm font-semibold text-ink">
                        {rule.title}
                        <span className="ml-2 font-normal text-muted">/ {rule.titleZh}</span>
                      </h3>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted">{rule.body}</p>
                    <p className="mt-1 text-sm leading-6 text-ink/75">{rule.bodyZh}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-rule bg-cream/45">
        <div className="container py-16 md:py-20">
          <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr]">
            <div>
              <p className="page-no">AI roles / Agent 分工</p>
              <h2 className="mt-3 font-serif text-3xl font-semibold">One job per agent.</h2>
              <p className="mt-2 text-lg font-medium text-ink/75">每个 Agent 只负责一个清晰任务。</p>
              <p className="mt-4 text-sm leading-7 text-muted">
                A single prompt should not be responsible for curriculum accuracy,
                story, image consistency, camera design, subtitles, and video motion.
                The workflow separates those decisions.
                <span className="mt-2 block">
                  不让一个 prompt 同时承担课程准确性、故事、画面一致性、镜头、字幕和运动。
                  这些决策会被拆成不同 Agent 的职责。
                </span>
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {roles.map((role) => (
                <RoleCard key={role.name} role={role} />
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="container py-16 md:py-20">
        <div className="grid gap-8 lg:grid-cols-[1fr_0.86fr]">
          <div className="min-w-0">
            <p className="page-no">Five-stage calibration / 五阶段校准</p>
            <h2 className="mt-3 font-serif text-3xl font-semibold">Video is calibrated after the comic is stable.</h2>
            <p className="mt-2 text-lg font-medium text-ink/75">先让漫画稳定，再把它转成视频。</p>
            <div className="mt-8 overflow-hidden rounded-paper border border-rule bg-white shadow-paper">
              {stages.map((stage) => (
                <div key={stage.n} className="grid gap-4 border-b border-rule p-5 last:border-b-0 md:grid-cols-[5rem_1fr]">
                  <div className="font-mono text-sm font-medium text-indigo-700">Stage {stage.n}</div>
                  <div>
                    <h3 className="font-sans text-base font-semibold">
                      {stage.title}
                      <span className="ml-2 font-normal text-muted">/ {stage.titleZh}</span>
                    </h3>
                    <p className="mt-1 text-sm leading-6 text-muted">{stage.body}</p>
                    <p className="mt-1 text-sm leading-6 text-ink/75">{stage.bodyZh}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <aside className="min-w-0 rounded-paper border border-rule bg-ink p-6 text-paper shadow-paper">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-md bg-white/10">
                <Database className="h-5 w-5" />
              </span>
              <div>
                <p className="font-mono text-xs uppercase text-paper/60">Core data object / 核心数据对象</p>
                <h3 className="font-sans text-xl font-semibold text-paper">VideoShot</h3>
              </div>
            </div>
            <pre className="mt-6 max-w-full overflow-x-auto rounded-md border border-white/10 bg-white/5 p-4 text-xs leading-6 text-paper/85">
{`{
  "sourcePanelId": "p03_panel02",
  "learningFunction": "abstraction",
  "shotSize": "MS",
  "duration": 5,
  "visualFocus": "bridge -> beams -> ratio",
  "teacherVoiceover": "A ratio compares two quantities.",
  "subtitle": "30m / 6 beams = 5m each",
  "needsEndFrame": true
}`}
            </pre>
          </aside>
        </div>
      </section>

      <section className="border-y border-rule bg-white">
        <div className="container py-16 md:py-20">
          <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr]">
            <div>
              <p className="page-no">Outputs / 输出物</p>
              <h2 className="mt-3 font-serif text-3xl font-semibold">One lesson, four video surfaces.</h2>
              <p className="mt-2 text-lg font-medium text-ink/75">一节课可以生成四类视频交付。</p>
              <p className="mt-4 text-sm leading-7 text-muted">
                The same comic episode can become a classroom hook, an app
                micro-lesson, a teacher preview, or a complete narrated comic video.
                <span className="mt-2 block">
                  同一集漫画可以转成课堂导入、APP 微课、教师预览，或完整旁白漫画视频。
                </span>
              </p>
            </div>

            <div className="overflow-hidden rounded-paper border border-rule bg-paper">
              <div className="hidden grid-cols-[1fr_0.52fr_1.1fr] bg-ink px-4 py-3 text-xs font-semibold uppercase text-paper md:grid">
                <span>Product / 产品</span>
                <span>Length / 时长</span>
                <span>Use / 用途</span>
              </div>
              {outputs.map(([product, productZh, length, use, useZh]) => (
                <div key={product} className="grid gap-2 border-b border-rule px-4 py-4 text-sm last:border-b-0 md:grid-cols-[1fr_0.52fr_1.1fr] md:gap-3">
                  <span className="font-medium text-ink">
                    {product}
                    <span className="block font-normal text-muted">{productZh}</span>
                  </span>
                  <span className="font-mono text-xs text-indigo-700">{length}</span>
                  <span className="text-muted">
                    {use}
                    <span className="block text-ink/75">{useZh}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="container py-16 md:py-20">
        <div className="grid gap-8 lg:grid-cols-[1fr_0.9fr]">
          <div>
            <p className="page-no">QA gate / 质量门槛</p>
            <h2 className="mt-3 font-serif text-3xl font-semibold">The video must still teach.</h2>
            <p className="mt-2 text-lg font-medium text-ink/75">视频必须保留清晰的教学功能。</p>
            <p className="mt-4 max-w-prose text-sm leading-7 text-muted">
              The goal is not animated noise. A clip passes only when the
              learning objective, story action, visual consistency, and assessment
              moment survive the move from page to motion.
              <span className="mt-2 block">
                目标不是制造会动的热闹画面。只有当学习目标、剧情行动、画面一致性和测评点都成立时，
                这个视频才算通过。
              </span>
            </p>
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {qa.map(([item, itemZh]) => (
                <div key={item} className="flex min-h-16 items-start gap-3 rounded-md border border-rule bg-white px-4 py-3 text-sm shadow-chip">
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
                  <span>
                    <span className="block font-medium text-ink">{item}</span>
                    <span className="mt-1 block text-muted">{itemZh}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-paper border border-rule bg-cream/40 p-6 shadow-paper">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-md bg-amber-100 text-amber-700">
                <PackageCheck className="h-5 w-5" />
              </span>
              <h3 className="font-sans text-lg font-semibold">Recommended first demo / 推荐首个 Demo</h3>
            </div>
            <dl className="mt-6 space-y-4 text-sm">
              <DemoLine label="Subject" labelZh="学科" value="Grade 6 Math · ratio / unit rate" valueZh="六年级数学：比与单位率" />
              <DemoLine label="Story" labelZh="故事" value="Broken bridge on the Hearthline route" valueZh="Hearthline 路线上的断桥任务" />
              <DemoLine label="Comic" labelZh="漫画" value="4 pages from one learning objective" valueZh="一个学习目标生成 4 页漫画" />
              <DemoLine label="Video" labelZh="视频" value="45-60 second concept reveal" valueZh="45-60 秒概念揭示短片" />
              <DemoLine label="Assets" labelZh="素材" value="2 characters, 1 pet, 1 bridge scene, 4 shot clips" valueZh="2 个角色、1 个宠物 IP、1 个桥梁场景、4 个镜头片段" />
            </dl>
          </div>
        </div>
      </section>
    </>
  );
}

function HeroBoard() {
  const pages = [site.showcase.unit1.pages[0], site.showcase.unit1.pages[1], site.showcase.unit1.pages[2]];

  return (
    <div className="mx-auto w-full max-w-2xl rounded-paper border border-rule bg-paper p-4 shadow-paper">
      <div className="grid gap-4 md:grid-cols-[0.84fr_1.16fr]">
        <div className="grid grid-cols-3 gap-2 md:grid-cols-1">
          {pages.map((src, index) => (
            <div key={src} className="relative aspect-[3/4] overflow-hidden rounded-md border border-rule bg-white">
              <Image
                src={src}
                alt={`Comic page source ${index + 1}`}
                fill
                sizes="(min-width: 768px) 11rem, 28vw"
                className="object-cover"
                priority={index === 0}
              />
            </div>
          ))}
        </div>

        <div className="flex min-h-[22rem] flex-col justify-between rounded-md border border-rule bg-white p-5">
          <div>
            <div className="flex items-center justify-between gap-3 border-b border-rule pb-4">
              <div>
                <p className="page-no">Director pack / 导演包</p>
                <h3 className="mt-1 font-sans text-lg font-semibold">Page to motion</h3>
                <p className="mt-1 text-sm text-muted">从漫画页到视频镜头</p>
              </div>
              <Workflow className="h-6 w-6 text-indigo-600" />
            </div>
            <div className="mt-5 space-y-3">
              <VisualRow label="ComicPanel" labelZh="漫画格" value="Bridge repair reveal" valueZh="断桥修复任务揭示" />
              <VisualRow label="Start frame" labelZh="首帧" value="student measures span" valueZh="学生测量桥面距离" />
              <VisualRow label="End frame" labelZh="尾帧" value="ratio diagram appears" valueZh="比率图示出现" />
              <VisualRow label="VideoShot" labelZh="镜头" value="dolly-in, 5s, subtitle on" valueZh="推镜 5 秒，字幕开启" />
            </div>
          </div>

          <div className="mt-6 rounded-md bg-ink p-4 text-paper">
            <p className="font-mono text-xs uppercase text-paper/60">Motion prompt / 运动提示词</p>
            <p className="mt-2 text-sm leading-6 text-paper/90">
              Camera moves from the broken bridge to the beam pile as the ratio
              diagram fades in: 30m / 6 beams = 5m each.
              <span className="mt-2 block text-paper/75">
                镜头从断桥移动到木梁堆，比例图示逐渐显现：30 米 / 6 根木梁 = 每根 5 米。
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function PipelineNode({
  item,
  index
}: {
  item: { icon: LucideIcon; label: string; labelZh: string; detail: string; detailZh: string };
  index: number;
}) {
  const Icon = item.icon;
  return (
    <div className="relative rounded-paper border border-rule bg-white p-5 shadow-chip">
      <div className="mb-5 flex items-center justify-between">
        <span className="grid h-10 w-10 place-items-center rounded-md bg-indigo-50 text-indigo-600">
          <Icon className="h-5 w-5" />
        </span>
        <span className="font-mono text-xs text-muted">0{index + 1}</span>
      </div>
      <h3 className="font-sans text-base font-semibold">{item.label}</h3>
      <p className="mt-1 text-sm font-medium text-ink/70">{item.labelZh}</p>
      <p className="mt-2 text-sm leading-6 text-muted">{item.detail}</p>
      <p className="mt-1 text-sm leading-6 text-ink/75">{item.detailZh}</p>
    </div>
  );
}

function RoleCard({ role }: { role: { icon: LucideIcon; name: string; nameZh: string; body: string; bodyZh: string } }) {
  const Icon = role.icon;
  return (
    <article className="rounded-paper border border-rule bg-white p-5 shadow-chip">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-md bg-emerald-50 text-emerald-700">
          <Icon className="h-4 w-4" />
        </span>
        <div>
          <h3 className="font-sans text-base font-semibold">{role.name}</h3>
          <p className="text-sm font-medium text-ink/70">{role.nameZh}</p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-muted">{role.body}</p>
      <p className="mt-2 text-sm leading-6 text-ink/75">{role.bodyZh}</p>
    </article>
  );
}

function VisualRow({ label, labelZh, value, valueZh }: { label: string; labelZh: string; value: string; valueZh: string }) {
  return (
    <div className="grid gap-3 rounded-md bg-cream/50 px-3 py-2 text-sm sm:grid-cols-[7rem_1fr]">
      <span className="font-mono text-xs text-muted">
        {label}
        <span className="block font-sans normal-case text-ink/60">{labelZh}</span>
      </span>
      <span className="font-medium text-ink">
        {value}
        <span className="block font-normal text-muted">{valueZh}</span>
      </span>
    </div>
  );
}

function DemoLine({ label, labelZh, value, valueZh }: { label: string; labelZh: string; value: string; valueZh: string }) {
  return (
    <div className="grid gap-1 border-b border-rule pb-3 last:border-b-0 last:pb-0 sm:grid-cols-[7rem_1fr]">
      <dt className="font-mono text-xs uppercase text-muted">
        {label}
        <span className="block font-sans normal-case text-ink/60">{labelZh}</span>
      </dt>
      <dd className="leading-6 text-ink">
        {value}
        <span className="block text-muted">{valueZh}</span>
      </dd>
    </div>
  );
}
