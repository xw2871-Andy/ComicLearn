import { NextResponse } from "next/server";

type StudioRunRequest = {
  title?: string;
  course?: string;
  subject?: string;
  outputMode?: string;
  language?: string;
  source?: string;
  visualQa?: boolean;
  bilingualCaptions?: boolean;
};

export async function POST(request: Request) {
  const body = (await request.json()) as StudioRunRequest;
  const title = body.title?.trim();
  const course = body.course?.trim();
  const source = body.source?.trim();

  if (!title || !course || !source) {
    return NextResponse.json(
      {
        ok: false,
        error: "Missing title, course, or source content."
      },
      { status: 400 }
    );
  }

  const runId = `cl_${Date.now().toString(36)}`;

  return NextResponse.json({
    ok: true,
    runId,
    mode: "workflow-preview",
    providerPolicy: {
      textReasoning: "Claude",
      visualReasoning: "Gemini",
      disabledProviders: "all others"
    },
    lesson: {
      title,
      course,
      subject: body.subject ?? "Math / 数学",
      outputMode: body.outputMode ?? "Comic + Video / 漫画 + 视频",
      language: body.language ?? "English + Chinese / 中英文",
      visualQa: body.visualQa ?? true,
      bilingualCaptions: body.bilingualCaptions ?? true
    },
    next: [
      "Claude lesson map",
      "Story mission",
      "Comic storyboard",
      "Gemini visual QA",
      "VideoShot packet",
      "Exports"
    ]
  });
}
