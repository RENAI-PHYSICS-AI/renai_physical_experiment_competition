import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const BUILD_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(BUILD_DIR, "../../..");
const STARTER_PPTX = path.join(BUILD_DIR, "template-starter.pptx");
const FINAL_PPTX = path.join(ROOT, "李萨如", "设计报告", "李萨如图形实验智能助教_答辩PPT.pptx");
const SCRIPT_TXT = path.join(ROOT, "李萨如", "设计报告", "李萨如图形实验智能助教_10分钟讲稿.txt");
const RENDER_DIR = path.join(BUILD_DIR, "render_updated");
const LAYOUT_DIR = path.join(BUILD_DIR, "final-layout");

const FONT = "Microsoft YaHei";
const C = {
  ink: "#DDE8EE",
  teal: "#45D6CB",
  coral: "#FF6B6B",
  gold: "#F5C66B",
};

async function writeBlob(outputPath, blob) {
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, new Uint8Array(await blob.arrayBuffer()));
}

function shapeByName(slide, name) {
  const shape = slide.shapes.items.find((item) => item.name === name);
  if (!shape) throw new Error(`Missing inherited shape: ${name}`);
  return shape;
}

function replaceText(slide, name, oldText, newText) {
  const shape = shapeByName(slide, name);
  shape.text.replace(oldText, newText);
  return shape;
}

function bullet(lead, body, color) {
  return {
    bulletCharacter: "•",
    marginLeft: 24,
    indent: -14,
    spaceAfter: 9,
    runs: [
      { run: lead, textStyle: { bold: true, color, typeface: FONT } },
      { run: body, textStyle: { color: C.ink, typeface: FONT } },
    ],
  };
}

function rewriteBulletList(slide, name, paragraphs) {
  const shape = shapeByName(slide, name);
  shape.text.set(paragraphs);
  shape.text.style = {
    fontSize: 22,
    color: C.ink,
    typeface: FONT,
    alignment: "left",
    verticalAlignment: "top",
    autoFit: "none",
    wrap: "square",
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
    lineSpacing: 1.08,
  };
  return shape;
}

const talks = [
  {
    durationSec: 40,
    speech: "各位评委好，我们的作品是李萨如图形实验智能助教。我们没有把目标停留在生成一条漂亮曲线，而是把正交简谐振动改造成可以预测、操作、记录、复算和追问的完整实验。作品包含相位差、振幅比、有理频率比和频率失谐四个模块；Python负责学习流程与智能问答，Julia负责确定性物理计算，最终封装成无需预装两种开发环境的单文件。",
    sources: [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（摘要、目标定位与结论）",
      "李萨如/李萨如_RAG智能体/assets/lissajous_header.png",
    ],
  },
  {
    durationSec: 50,
    speech: "传统教学通常给出若干典型李萨如图形，让学生按外观记忆频率比或相位关系，但这会留下三个问题。第一，静态图看不出质点从哪里出发、沿什么方向运动；第二，相位、振幅和频率都能改变外观，变量容易混淆；第三，仅凭叶数或截图无法复核结论。因此本作品把学习过程组织为预测、操作、记录、解释、复核和迁移，要求每个判断都对应明确参数、公式或导出数据。",
    sources: ["李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（选题意义、教学痛点与目标定位）"],
  },
  {
    durationSec: 60,
    speech: "四个实验共用同一组正交简谐振动方程。这里特别区分两个经常混淆的量：横纵方向的总跨度是二A和二B，它们只是轨迹在坐标轴上的投影；当椭圆发生旋转时，真正的长短半轴和主轴方向要由变换矩阵的奇异值分解得到。面积满足πAB乘相位差正弦的绝对值，方向可由叉乘型表达式的符号判断；有理频率比约分后给出最短闭合周期。这些量由同一参数组计算，可以互相校验，而不是彼此独立的界面标签。模型还明确同一时钟、正交坐标和稳定正弦信号等适用边界。",
    sources: ["李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（物理原理、矩阵模型、主轴与不变量）"],
  },
  {
    durationSec: 55,
    speech: "在统一方程下，我们设计了四条控制变量主线。相位差实验观察形状、退化直线和绕行方向；振幅比实验把投影跨度与SVD求得的真实主轴分开，并通过归一化辨别尺度变化与相位变化；有理频率比实验要求先约分，再用终点距离和最短周期判定闭合；频率失谐实验则把快速载波与缓慢形态演化分开，形态周期等于频差绝对值的倒数。四个模块由特殊值进入一般值，避免只靠“看起来像”。",
    sources: ["李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（实验一至实验四）"],
  },
  {
    durationSec: 45,
    speech: "这是真实运行的Julia交互界面。左侧双通道波形说明横纵信号从何而来，中间轨迹同步显示当前质点与形成顺序，右侧给出面积、半轴、闭合误差等定量读数。所有图形和读数来自同一数组，播放只改变显示进度，不改变物理方程。学生可以暂停、拖动并导出CSV或PNG，所以课堂上看到的动画能够在电子表格或其他程序中再次复绘，而不是一次性的视觉效果。",
    sources: [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（数值离散、界面交互与数据导出）",
      "李萨如/设计报告/assets/lissajous_demo_interface.png",
    ],
  },
  {
    durationSec: 60,
    speech: "混合编程不是把两种语言机械拼在一起。Python和Streamlit负责统一入口、专题检索、图片输入、对话状态、端口分配、子进程与日志；Julia和WGLMakie负责方程计算、离散采样、派生量、交互控件和WebGL绘图。两端采用进程级解耦，在本机网页中组合，只通过小而稳定的接口交换经过范围校验的模式、参数与结果，不共享隐含全局状态。这样既缩短浏览器交互链路，也保证智能问答不能改写Julia的真实实验状态和数值结果。",
    sources: ["李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（软件架构、职责边界与Python--Julia进程协同）"],
  },
  {
    durationSec: 50,
    speech: "启动时，主程序先分配端口并启动Julia子进程，再用轻量TCP检查确认监听就绪，随后才把WGLMakie页面嵌入主网页。学生拖动滑块时，事件由浏览器直接交给Julia会话，不需要Python逐点复制大数组。对于首次启动，我们把验收拆成解包、Julia就绪、页面加载和四模块切换，而不是只看主窗口是否出现。若Julia或问答服务发生故障，系统显示状态和日志，同时尽量保留另一条核心链路，便于课堂定位问题。",
    sources: ["李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（启动流程、故障隔离与冷启动验收）"],
  },
  {
    durationSec: 60,
    speech: "智能问答是本作品的另一项特色，但它不是通用聊天窗口。学生可以从轨迹现象继续追问，也可以粘贴示波器截图或装置照片。系统先检索本地专题文献；如果问题包含频率、相位或振幅等完整参数，还调用确定性工具计算约分频率比、闭合周期、轨迹类型和面积。图像回答先列出可见事实，再说明推断条件，避免从模糊截图过度读出参数。模型负责组织解释，不能覆盖工具结果。回答最后应回到Julia实验，用相同参数再次观察和导出数据，由此形成现象观察、文献检索、物理推导、确定性计算和可视化验证的闭环。",
    sources: [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（智能问答特色设计与确定性计算工具）",
      "李萨如/设计报告/assets/lissajous_qa_interface_real.png",
    ],
  },
  {
    durationSec: 55,
    speech: "问答可靠性由多条约束共同建立。知识库先从PDF提取正文和元数据，再以TF–IDF与BM25混合检索，每轮保留不超过六条去重来源，并用最高分百分之五十五作为候选阈值。涉及明确参数时，周期、面积和形状由确定性函数给出。若回答提供Python绘图代码，也必须由用户确认，并经过导入白名单、危险操作检查、独立输出目录和六十秒超时。我们同时明确，这不是操作系统级沙箱，公共机房可以关闭代码执行。",
    sources: ["李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（专题知识库、检索流程与受限Python可视化）"],
  },
  {
    durationSec: 50,
    speech: "为了让作品真正进入课堂，我们把Python前端、Julia图形运行时、专题知识库和资源清单封装到同一启动器中，目标机不需要预装Python或Julia。首次运行会解包并初始化WGLMakie，因此验收必须在干净Windows机器上覆盖中文目录、普通用户权限、离线网络和常见缩放比例。推广分为三个层级：教师课堂演示、机房学生探究和校内长期使用。三种场景共享同一物理核心与导出格式，只替换任务单、资料和评价方式。",
    sources: ["李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（参赛单文件版、冷启动测试与推广场景）"],
  },
  {
    durationSec: 65,
    speech: "我们的验证不以“页面能打开”为终点，而是分成四层。第一层检查公式、量纲和解析量，例如面积与特殊相位边界；第二层检查离散数组的首末点、采样间隔和极值；第三层确认浏览器图形确实映射同一数组，参数联动、播放和重置一致；第四层检查CSV和PNG能否在独立工具中复绘。当前十道检索评估题的前五条结果均命中预设主题，但这只证明检索主题覆盖，不等于回答完全正确。教学效果还需用前后测、迁移题、操作日志和真实样本评价，未实测前不宣称效果显著。",
    sources: ["李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（解析检验、四层验证与教学有效性评价方案）"],
  },
  {
    durationSec: 30,
    speech: "最后概括为四句话：一份文件降低部署门槛，两种语言各守职责边界，四层验证保证从公式到导出的证据连续，三级推广支持从演示到长期使用。模型负责给出结果，智能问答帮助学生解释，最终仍由公式、数据和可重复实验裁决。谢谢各位评委。",
    sources: ["李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（创新性、推广场景与结论）"],
  },
];

function applyVisibleEdits(presentation) {
  const s = presentation.slides.items;
  if (s.length !== 12) throw new Error(`Expected 12 starter slides, got ${s.length}`);

  replaceText(s[0], "cover-three", "3 条证据链", "4 层验证");

  replaceText(s[2], "title-3", "一个统一方程连接全部四类实验", "同一方程给出主轴、方向与闭合");
  replaceText(s[2], "model-col-head-0", "几何", "主轴");
  replaceText(s[2], "model-col-eq-0", "S = πAB|sin φ|", "M = UΣVᵀ");
  replaceText(s[2], "model-col-body-0", "面积成为可复算的不变量", "SVD定主轴；2A、2B为投影");
  replaceText(
    s[2],
    "model-boundary",
    "模型边界：同一时钟、正交坐标、稳定正弦信号；噪声、带宽和通道误差留作虚实对照任务。",
    "数据边界：参数先校验，Julia返回同一数组、解析量与CSV；问答不能改写结果。",
  );

  replaceText(s[3], "exp-sub-1", "尺度与归一化", "尺度≠主轴");
  replaceText(s[3], "exp-body-1", "A:B → 轨迹尺度；归一化保留相位", "A:B → 投影跨度；SVD 求真实主轴");

  replaceText(s[5], "title-6", "Python 组织学习流程，Julia 保证物理计算可信", "Python 组织学习，Julia 裁决物理结果");
  replaceText(s[5], "subtitle-6", "进程级解耦 · 网页级组合 · 数值与问答隔离", "进程级解耦 · 小接口传参 · 数值与问答隔离");
  replaceText(s[5], "bridge-label", "网页内嵌", "参数结果");
  replaceText(
    s[5],
    "hybrid-boundary-copy",
    "问答可以解释和建议，但不能改写 Julia 的真实参数与实验结果。",
    "接口只交换经校验的参数与结果；问答不能改写 Julia 实验状态。",
  );

  replaceText(s[6], "title-7", "网页内嵌缩短交互链路，也形成故障隔离", "网页内嵌缩短链路，冷启动也可逐项验收");
  replaceText(s[6], "runtime-fail-julia-head", "Julia 初始化失败", "冷启动验收");
  replaceText(s[6], "runtime-fail-julia-body", "主页面继续显示状态、日志和智能问答", "解包 → 就绪 → 页面加载 → 模块切换");
  replaceText(s[6], "runtime-fail-ai-head", "问答服务不可用", "故障隔离");
  replaceText(s[6], "runtime-fail-ai-body", "四个确定性 Julia 实验仍可独立运行", "任一服务失败时，其余核心功能仍可使用");

  replaceText(s[9], "title-10", "单文件封装让双语言系统能进入普通课堂", "单文件与冷启动验收，让双语言系统进课堂");
  rewriteBulletList(s[9], "deploy-points", [
    bullet("目标机器：", "无需预装 Python 或 Julia", C.teal),
    bullet("运行要求：", "64 位 Windows 10/11 与支持 WebGL 的浏览器", C.coral),
    bullet("验收路径：", "解包、Julia 就绪、页面渲染、四模块通过", C.gold),
    bullet("复现记录：", "版本、哈希、首次启动时间与关键理论量", C.teal),
  ]);
  replaceText(s[9], "deploy-bottom-copy", "课堂关注“稳定打开并使用”，", "三级推广共享同一物理核心：");
  replaceText(s[9], "deploy-bottom-copy", "而不是开发环境是否配置完整。", "课堂演示 → 机房探究 → 校内长期使用");

  replaceText(s[10], "title-11", "验证不止看界面，而要用解析量和测试集复核", "四层验证把公式、数组、界面与导出贯通");
  replaceText(s[10], "validation-metric-label", "检索评估题 Top-5 主题命中", "检索评估题 Top-5 主题命中（已测）");
  rewriteBulletList(s[10], "validation-right", [
    bullet("第一层：", "公式、量纲与解析量", C.teal),
    bullet("第二层：", "离散数组、采样间隔与极值", C.coral),
    bullet("第三层：", "浏览器图形映射同一数组", C.gold),
    bullet("第四层：", "CSV / PNG 可在独立工具复绘", C.teal),
  ]);
  replaceText(
    s[10],
    "validation-caveat",
    "仅展示已有证据；最终测试矩阵与教学数据按送审版实测填写。",
    "教学评价另测记忆、解释与迁移；未实测前不宣称效果显著。",
  );

  replaceText(s[11], "close-title", "三条证据链 · 四个实验", "四层验证 · 三级推广");
  replaceText(s[11], "close-body-0", "降低部署门槛", "冷启动验收");
  replaceText(s[11], "close-body-1", "Python 编排 / Julia 计算", "Python 编排 / Julia 裁决");
  replaceText(s[11], "close-head-2", "证据链", "验证");
  replaceText(s[11], "close-body-2", "模型 / 交互 / 问答", "公式 / 数组 / 界面 / 导出");
  replaceText(s[11], "close-head-3", "实验", "推广");
  replaceText(s[11], "close-body-3", "相位 / 振幅 / 频比 / 失谐", "演示 / 探究 / 长期使用");
  replaceText(s[11], "close-footer", "面向预习、课堂演示、自主探究与实验复盘", "同一物理核心，服务不同教学深度");
}

function addSpeakerNotes(presentation) {
  presentation.slides.items.forEach((slide, index) => {
    const item = talks[index];
    const note = [
      `【建议时长：${item.durationSec}秒】`,
      "",
      item.speech,
      "",
      "[Sources]",
      ...item.sources.map((source) => `- ${source}`),
      "[/Sources]",
    ].join("\n");
    slide.speakerNotes.textFrame.setText(note);
    slide.speakerNotes.setVisible(true);
  });
}

function buildScriptText() {
  const totalSeconds = talks.reduce((sum, item) => sum + item.durationSec, 0);
  const sections = talks.map((item, index) => [
    `第${index + 1}页　建议时长：${item.durationSec}秒`,
    item.speech,
  ].join("\n"));
  return [
    "李萨如图形实验智能助教——约10分钟答辩讲稿",
    `建议总时长：${Math.floor(totalSeconds / 60)}分${totalSeconds % 60}秒；按普通中文答辩语速约220–250字/分钟。`,
    "",
    ...sections.flatMap((section) => [section, ""]),
  ].join("\n").trimEnd() + "\n";
}

async function main() {
  await fs.mkdir(RENDER_DIR, { recursive: true });
  await fs.mkdir(LAYOUT_DIR, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(STARTER_PPTX));
  applyVisibleEdits(presentation);
  addSpeakerNotes(presentation);

  const speechChars = talks.reduce((sum, item) => sum + item.speech.replace(/\s/g, "").length, 0);
  const totalSeconds = talks.reduce((sum, item) => sum + item.durationSec, 0);
  if (speechChars < 2200 || speechChars > 2500) {
    throw new Error(`Speaker script must be 2200–2500 non-space characters; got ${speechChars}`);
  }
  if (totalSeconds < 570 || totalSeconds > 630) {
    throw new Error(`Suggested duration must be 570–630 seconds; got ${totalSeconds}`);
  }

  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(path.join(RENDER_DIR, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(LAYOUT_DIR, `${stem}.layout.json`), await layout.text(), "utf8");
  }

  await writeBlob(
    path.join(BUILD_DIR, "final-montage.webp"),
    await presentation.export({ format: "webp", montage: true, scale: 1 }),
  );

  const notesInspect = await presentation.inspect({
    kind: "slide,notes",
    include: "id,slide,title,text,textPreview,textChars",
    maxChars: 200000,
  });
  await fs.writeFile(path.join(BUILD_DIR, "final-notes.inspect.ndjson"), `${notesInspect.ndjson.trim()}\n`, "utf8");

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(FINAL_PPTX);
  await fs.writeFile(SCRIPT_TXT, buildScriptText(), "utf8");

  const sidecarInspect = `${FINAL_PPTX}.inspect.ndjson`;
  const retainedInspect = path.join(BUILD_DIR, "final-pptx.inspect.ndjson");
  try {
    await fs.rm(retainedInspect, { force: true });
    await fs.rename(sidecarInspect, retainedInspect);
  } catch {
    // Some artifact-tool versions do not emit a sidecar.
  }

  await fs.writeFile(
    path.join(BUILD_DIR, "source-notes.txt"),
    [
      "All visible claims and speaker notes are grounded in the current local project report.",
      "Primary source: 李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex",
      "Template source: 李萨如/设计报告/李萨如图形实验智能助教_答辩PPT.pptx (captured as template-starter.pptx before editing)",
      "Existing local images retained:",
      "- 李萨如/李萨如_RAG智能体/assets/lissajous_header.png",
      "- 李萨如/设计报告/assets/lissajous_demo_interface.png",
      "- 李萨如/设计报告/assets/lissajous_qa_interface_real.png",
      "- tmp/ppt_build/lissajous/phase_interface_focus.png",
      "No external web assets or unverified result claims were introduced.",
    ].join("\n") + "\n",
    "utf8",
  );

  await fs.writeFile(
    path.join(BUILD_DIR, "speaker-notes-qa.txt"),
    [
      `slides=${presentation.slides.items.length}`,
      `notes=${talks.length}`,
      `speech_nonspace_chars=${speechChars}`,
      `suggested_duration_seconds=${totalSeconds}`,
      `sources_blocks=${talks.length}`,
      "status=pass",
    ].join("\n") + "\n",
    "utf8",
  );

  console.log(JSON.stringify({
    finalPptx: FINAL_PPTX,
    scriptTxt: SCRIPT_TXT,
    renderDir: RENDER_DIR,
    layoutDir: LAYOUT_DIR,
    slides: presentation.slides.items.length,
    speechChars,
    totalSeconds,
  }, null, 2));
  process.exit(0);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
