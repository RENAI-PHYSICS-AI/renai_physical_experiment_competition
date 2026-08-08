import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const BUILD_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(BUILD_DIR, "../../..");
const RENDER_DIR = path.join(BUILD_DIR, "render");
const FINAL_PPTX = path.join(
  ROOT,
  "李萨如",
  "设计报告",
  "李萨如图形实验智能助教_答辩PPT.pptx",
);

const ASSETS = {
  hero: path.join(ROOT, "李萨如", "李萨如_RAG智能体", "assets", "lissajous_header.png"),
  // Derived, non-destructive crop of interface_preview.png: keeps the source intact
  // while making the two waveforms and trajectory legible on a projected slide.
  phase: path.join(BUILD_DIR, "phase_interface_focus.png"),
  demo: path.join(ROOT, "李萨如", "设计报告", "assets", "lissajous_demo_interface.png"),
  qa: path.join(ROOT, "李萨如", "设计报告", "assets", "lissajous_qa_interface_real.png"),
};

const C = {
  bg: "#07131D",
  bg2: "#0A1A27",
  panel: "#102A3B",
  panel2: "#0C2232",
  line: "#29495C",
  teal: "#45D6CB",
  teal2: "#79F0E8",
  coral: "#FF6B6B",
  coral2: "#FF9B91",
  white: "#F3F7FA",
  muted: "#A7BAC8",
  dim: "#6E8798",
  ink: "#DDE8EE",
  gold: "#F5C66B",
};

const FONT = "Microsoft YaHei";
const MATH = "Cambria Math";
const WIDTH = 1280;
const HEIGHT = 720;

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function writeBlob(outputPath, blob) {
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, new Uint8Array(await blob.arrayBuffer()));
}

function rect(slide, name, left, top, width, height, fill, lineFill = "none", radius = 0) {
  return slide.shapes.add({
    geometry: radius > 0 ? "roundRect" : "rect",
    name,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: lineFill, width: lineFill === "none" ? 0 : 1 },
    ...(radius > 0 ? { borderRadius: radius } : {}),
  });
}

function line(slide, name, left, top, width, height, color = C.line, weight = 2) {
  return slide.shapes.add({
    geometry: "line",
    name,
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: color, width: weight },
  });
}

function textBox(slide, name, text, left, top, width, height, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left, top, width, height },
    fill: options.fill ?? "none",
    line: { style: "solid", fill: options.line ?? "none", width: options.line && options.line !== "none" ? 1 : 0 },
    ...(options.radius ? { borderRadius: options.radius } : {}),
  });
  shape.text = text;
  shape.text.style = {
    fontSize: options.fontSize ?? 20,
    bold: options.bold ?? false,
    color: options.color ?? C.white,
    typeface: options.typeface ?? FONT,
    alignment: options.align ?? "left",
    verticalAlignment: options.valign ?? "top",
    autoFit: options.autoFit ?? "none",
    wrap: "square",
    insets: options.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    lineSpacing: options.lineSpacing ?? 1.0,
  };
  return shape;
}

function richTextBox(slide, name, paragraphs, left, top, width, height, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left, top, width, height },
    fill: options.fill ?? "none",
    line: { style: "solid", fill: options.line ?? "none", width: options.line && options.line !== "none" ? 1 : 0 },
    ...(options.radius ? { borderRadius: options.radius } : {}),
  });
  shape.text.set(paragraphs);
  shape.text.style = {
    fontSize: options.fontSize ?? 19,
    color: options.color ?? C.ink,
    typeface: options.typeface ?? FONT,
    alignment: options.align ?? "left",
    verticalAlignment: options.valign ?? "top",
    autoFit: options.autoFit ?? "none",
    wrap: "square",
    insets: options.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    lineSpacing: options.lineSpacing ?? 1.08,
  };
  return shape;
}

function bullet(lead, body, color = C.teal) {
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

function addSlideBase(presentation, page, section, title, subtitle = "") {
  const slide = presentation.slides.add();
  slide.background.fill = C.bg;
  rect(slide, `top-accent-${page}`, 0, 0, WIDTH, 6, C.teal);
  textBox(slide, `section-${page}`, section.toUpperCase(), 64, 34, 420, 24, {
    fontSize: 13,
    bold: true,
    color: C.teal,
  });
  textBox(slide, `title-${page}`, title, 64, 66, 1140, 66, {
    fontSize: 47,
    bold: true,
    color: C.white,
  });
  if (subtitle) {
    textBox(slide, `subtitle-${page}`, subtitle, 64, 130, 1110, 34, {
      fontSize: 22,
      color: C.muted,
    });
  }
  line(slide, `header-line-${page}`, 64, 170, 1152, 0, C.line, 1);
  textBox(slide, `footer-${page}`, "李萨如图形实验智能助教", 64, 684, 300, 20, {
    fontSize: 10,
    color: C.dim,
  });
  textBox(slide, `page-${page}`, String(page).padStart(2, "0"), 1160, 680, 56, 22, {
    fontSize: 12,
    bold: true,
    color: C.teal,
    align: "right",
  });
  return slide;
}

function addNotes(slide, cue, sources) {
  const block = [
    cue,
    "",
    "[Sources]",
    ...sources.map((s) => `- ${s}`),
    "[/Sources]",
  ].join("\n");
  slide.speakerNotes.textFrame.setText(block);
  slide.speakerNotes.setVisible(true);
}

function addImage(slide, name, blob, alt, left, top, width, height, fit = "contain", crop = undefined) {
  rect(slide, `${name}-frame`, left - 6, top - 6, width + 12, height + 12, C.bg2, C.line, 16);
  return slide.images.add({
    blob,
    contentType: "image/png",
    alt,
    fit,
    position: { left, top, width, height },
    geometry: "roundRect",
    borderRadius: 12,
    ...(crop ? { crop } : {}),
  });
}

function addSmallLabel(slide, name, value, left, top, width, color = C.teal) {
  textBox(slide, name, value, left, top, width, 28, {
    fontSize: 14,
    bold: true,
    color,
  });
}

async function main() {
  await fs.mkdir(RENDER_DIR, { recursive: true });
  const [hero, phase, demo, qa] = await Promise.all([
    readImageBlob(ASSETS.hero),
    readImageBlob(ASSETS.phase),
    readImageBlob(ASSETS.demo),
    readImageBlob(ASSETS.qa),
  ]);

  const presentation = Presentation.create({ slideSize: { width: WIDTH, height: HEIGHT } });

  // 01 — Cover
  {
    const slide = presentation.slides.add();
    slide.background.fill = C.bg;
    rect(slide, "cover-top-accent", 0, 0, WIDTH, 8, C.teal);
    rect(slide, "cover-coral-accent", 0, 8, 12, HEIGHT - 8, C.coral);
    textBox(slide, "cover-eyebrow", "VIRTUAL PHYSICS LAB · INTELLIGENT TUTOR", 76, 72, 560, 30, {
      fontSize: 16,
      bold: true,
      color: C.teal,
    });
    textBox(slide, "cover-title", "让李萨如图形\n从漂亮曲线变成\n可验证实验", 76, 130, 680, 220, {
      fontSize: 67,
      bold: true,
      color: C.white,
      lineSpacing: 0.94,
    });
    textBox(slide, "cover-subtitle", "Python–Julia 混合编程 · 智能问答 · 单文件部署", 78, 370, 680, 40, {
      fontSize: 24,
      color: C.muted,
    });
    line(slide, "cover-rule", 78, 426, 650, 0, C.line, 2);
    textBox(slide, "cover-kicker", "模型给出结果，问答帮助解释，公式与数据负责裁决。", 78, 454, 680, 64, {
      fontSize: 24,
      bold: true,
      color: C.coral2,
    });
    slide.images.add({
      blob: hero,
      contentType: "image/png",
      alt: "透明背景的青绿色李萨如轨迹",
      fit: "contain",
      position: { left: 800, top: 170, width: 392, height: 238 },
    });
    textBox(slide, "cover-four", "4 个实验模块", 808, 472, 174, 32, {
      fontSize: 16,
      bold: true,
      color: C.teal,
      align: "center",
    });
    textBox(slide, "cover-three", "3 条证据链", 1004, 472, 174, 32, {
      fontSize: 16,
      bold: true,
      color: C.coral2,
      align: "center",
    });
    textBox(slide, "cover-page", "自选题2 · 教学资源和虚仿", 78, 648, 360, 30, {
      fontSize: 22,
      bold: true,
      color: C.coral2,
    });
    addNotes(slide, "开场先提出核心判断：本作品不是把李萨如图形做得更漂亮，而是把它变成能够预测、观察、复算和追问的实验。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（摘要、选题意义、创新性）",
      "李萨如/李萨如_RAG智能体/assets/lissajous_header.png",
    ]);
  }

  // 02 — Teaching tension
  {
    const slide = addSlideBase(presentation, 2, "教学问题", "传统展示能看到结果，却难看清图形如何形成");
    textBox(slide, "problem-lead", "“像什么”不是终点，\n“为什么、如何验证”才是实验", 66, 208, 500, 145, {
      fontSize: 33,
      bold: true,
      color: C.white,
      lineSpacing: 1.0,
    });
    const rows = [
      ["01", "过程不可见", "静态轨迹隐藏质点方向与形成顺序"],
      ["02", "变量易混淆", "相位、振幅、频率都能改变外观"],
      ["03", "结论难复核", "凭叶数、形状和截图缺少定量判据"],
    ];
    rows.forEach((r, i) => {
      const y = 204 + i * 126;
      textBox(slide, `problem-no-${i}`, r[0], 594, y, 66, 38, {
        fontSize: 25,
        bold: true,
        color: i === 1 ? C.coral : C.teal,
      });
      textBox(slide, `problem-title-${i}`, r[1], 674, y - 1, 220, 34, {
        fontSize: 23,
        bold: true,
        color: C.white,
      });
      textBox(slide, `problem-body-${i}`, r[2], 674, y + 39, 470, 48, {
        fontSize: 22,
        color: C.muted,
      });
      if (i < rows.length - 1) line(slide, `problem-sep-${i}`, 594, y + 102, 550, 0, C.line, 1);
    });
    rect(slide, "problem-goal", 66, 538, 1078, 92, C.panel2, C.line, 14);
    textBox(slide, "problem-goal-label", "作品目标", 92, 562, 110, 30, {
      fontSize: 22,
      bold: true,
      color: C.coral2,
    });
    textBox(slide, "problem-goal-copy", "把学习路径变成：预测 → 操作 → 记录 → 解释 → 复核 → 迁移", 222, 553, 850, 48, {
      fontSize: 24,
      bold: true,
      color: C.teal2,
    });
    addNotes(slide, "本页说明作品要解决的教学缺口。不要从技术栈开始讲，先让评委看到静态图形教学为何不足。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（选题意义与目标定位，第 71–158 行）",
    ]);
  }

  // 03 — Unified physics model
  {
    const slide = addSlideBase(presentation, 3, "物理模型", "一个统一方程连接全部四类实验", "先建立可解析检验的理想模型，再讨论真实仪器误差");
    rect(slide, "model-equation-panel", 68, 196, 1144, 132, C.panel2, C.line, 16);
    textBox(slide, "model-equation", "x(t) = A sin(2πfₓt + φₓ)      y(t) = B sin(2πfᵧt + φᵧ)", 112, 224, 1056, 56, {
      fontSize: 33,
      bold: true,
      color: C.white,
      typeface: MATH,
      align: "center",
    });
    textBox(slide, "model-delta", "相位差 φ = φᵧ − φₓ", 450, 286, 380, 26, {
      fontSize: 22,
      color: C.teal,
      typeface: MATH,
      align: "center",
    });
    const cols = [
      { x: 68, color: C.teal, h: "几何", eq: "S = πAB|sin φ|", body: "面积成为可复算的不变量" },
      { x: 456, color: C.coral, h: "方向", eq: "xẏ − yẋ = −AB·2πf·sin φ", body: "符号区分顺、逆时针运动" },
      { x: 844, color: C.gold, h: "闭合", eq: "Tclose = 1/(g f₀)", body: "有理频率比决定最短周期" },
    ];
    cols.forEach((c, i) => {
      line(slide, `model-col-line-${i}`, c.x, 372, 324, 0, c.color, 4);
      textBox(slide, `model-col-head-${i}`, c.h, c.x, 390, 324, 32, {
        fontSize: 24,
        bold: true,
        color: c.color,
      });
      textBox(slide, `model-col-eq-${i}`, c.eq, c.x, 435, 324, 52, {
        fontSize: i === 1 ? 22 : 24,
        bold: true,
        color: C.white,
        typeface: MATH,
      });
      if (i === 2) {
        textBox(slide, "model-close-def", "fₓ = m f₀，fᵧ = n f₀；g = gcd(m,n)", c.x, 482, 360, 30, {
          fontSize: 22,
          color: C.gold,
          typeface: MATH,
        });
        textBox(slide, `model-col-body-${i}`, c.body, c.x, 532, 324, 44, {
          fontSize: 22,
          color: C.muted,
        });
      } else {
        textBox(slide, `model-col-body-${i}`, c.body, c.x, 500, 324, 44, {
          fontSize: 22,
          color: C.muted,
        });
      }
    });
    textBox(slide, "model-boundary", "模型边界：同一时钟、正交坐标、稳定正弦信号；噪声、带宽和通道误差留作虚实对照任务。", 68, 590, 1080, 42, {
      fontSize: 22,
      color: C.coral2,
    });
    addNotes(slide, "用统一方程建立可信起点。强调轨迹不是由 AI 生成，全部指标都能回到解析式复算。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（物理原理与计算模型，第 160–259 行）",
    ]);
  }

  // 04 — Four experiments
  {
    const slide = addSlideBase(presentation, 4, "实验设计", "四个控制变量实验回答四个不同问题");
    addImage(
      slide,
      "phase-interface",
      phase,
      "裁切放大的 Julia 双通道时域波形与李萨如轨迹",
      66,
      220,
      710,
      270,
      "cover",
    );
    textBox(slide, "phase-crop-caption", "双通道时域波形  ↔  轨迹形状与运动方向", 92, 516, 660, 34, {
      fontSize: 22,
      bold: true,
      color: C.teal2,
      align: "center",
    });
    const items = [
      ["相位差", "形状与方向", "φ → 椭圆、退化直线与绕行方向", C.teal],
      ["振幅比", "尺度与归一化", "A:B → 轨迹尺度；归一化保留相位", C.coral],
      ["有理频率比", "闭合与周期", "m:n → 约分频率比与最短闭合周期", C.gold],
      ["频率失谐", "快慢时间尺度", "Δf → Tshape = 1/|Δf|", C.teal2],
    ];
    items.forEach((it, i) => {
      const y = 206 + i * 104;
      textBox(slide, `exp-index-${i}`, `0${i + 1}`, 794, y, 48, 30, {
        fontSize: 22,
        bold: true,
        color: it[3],
      });
      textBox(slide, `exp-head-${i}`, it[0], 850, y - 2, 140, 28, {
        fontSize: 24,
        bold: true,
        color: C.white,
      });
      textBox(slide, `exp-sub-${i}`, it[1], 992, y, 190, 25, {
        fontSize: 20,
        color: it[3],
        align: "right",
      });
      textBox(slide, `exp-body-${i}`, it[2], 850, y + 35, 332, 45, {
        fontSize: 22,
        color: C.muted,
      });
      if (i < 3) line(slide, `exp-sep-${i}`, 794, y + 88, 388, 0, C.line, 1);
    });
    addNotes(slide, "四个模块不是四张孤立图，而是同一方程下的控制变量实验。左侧真实界面重点指出时域波形、轨迹方向和实时解析量。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（实验一至实验四，第 184–254 行）",
      "李萨如/李萨如图形可视化实验说明/实验一_Julia可视化方案/output/interface_preview.png",
    ]);
  }

  // 05 — Evidence UI
  {
    const slide = addSlideBase(presentation, 5, "交互界面", "界面把“波形—轨迹—指标”放在同一证据链上");
    addImage(slide, "demo-interface", demo, "四个李萨如实验的 Julia 综合可视化真实界面", 80, 194, 1120, 474, "contain");
    rect(slide, "demo-label-bg-1", 108, 198, 206, 38, C.panel2, C.teal, 8);
    textBox(slide, "demo-label-1", "① 双通道时域信号", 120, 207, 182, 22, { fontSize: 16, bold: true, color: C.teal2 });
    rect(slide, "demo-label-bg-2", 514, 198, 194, 38, C.panel2, C.coral, 8);
    textBox(slide, "demo-label-2", "② 轨迹形成过程", 526, 207, 170, 22, { fontSize: 16, bold: true, color: C.coral2 });
    rect(slide, "demo-label-bg-3", 856, 198, 222, 38, C.panel2, C.gold, 8);
    textBox(slide, "demo-label-3", "③ 定量辅助与导出", 868, 207, 198, 22, { fontSize: 16, bold: true, color: C.gold });
    addNotes(slide, "该页建议停留稍久：左边是因，中间是过程，右边是可复核指标；底部参数和导出使屏幕动画成为可追溯数据。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（界面与交互，第 326–335 行）",
      "李萨如/设计报告/assets/lissajous_demo_interface.png",
    ]);
  }

  // 06 — Hybrid architecture
  {
    const slide = addSlideBase(presentation, 6, "混合编程", "Python 组织学习流程，Julia 保证物理计算可信", "进程级解耦 · 网页级组合 · 数值与问答隔离");
    const py = rect(slide, "python-panel", 72, 214, 466, 338, C.panel2, C.teal, 18);
    const jl = rect(slide, "julia-panel", 742, 214, 466, 338, C.panel2, C.coral, 18);
    textBox(slide, "python-head", "Python / Streamlit", 104, 242, 390, 36, { fontSize: 26, bold: true, color: C.teal2 });
    richTextBox(slide, "python-list", [
      bullet("统一入口：", "页面导航、对话状态与图片输入", C.teal),
      bullet("智能层：", "专题检索、问答与受限绘图", C.teal),
      bullet("编排层：", "端口、子进程、日志和就绪检测", C.teal),
    ], 104, 302, 388, 184, { fontSize: 22 });
    textBox(slide, "julia-head", "Julia / WGLMakie", 774, 242, 390, 36, { fontSize: 26, bold: true, color: C.coral2 });
    richTextBox(slide, "julia-list", [
      bullet("模型层：", "方程计算、离散采样与派生量", C.coral),
      bullet("交互层：", "可观察状态、控件与 WebGL 绘图", C.coral),
      bullet("成果层：", "CSV / PNG 与模型自检结果", C.coral),
    ], 774, 302, 388, 184, { fontSize: 22 });
    rect(slide, "bridge", 558, 292, 164, 130, C.bg2, C.line, 65);
    textBox(slide, "bridge-label", "localhost\n网页内嵌", 582, 320, 116, 66, {
      fontSize: 24,
      bold: true,
      color: C.white,
      align: "center",
      valign: "middle",
    });
    slide.shapes.connect(py, jl, {
      kind: "straight",
      fromSide: "right",
      toSide: "left",
      line: { style: "solid", fill: C.line, width: 3 },
      head: { type: "arrow", width: "med", length: "med" },
      tail: { type: "arrow", width: "med", length: "med" },
    });
    rect(slide, "hybrid-boundary", 164, 580, 952, 54, C.bg2, C.line, 12);
    textBox(slide, "hybrid-boundary-copy", "问答可以解释和建议，但不能改写 Julia 的真实参数与实验结果。", 194, 594, 892, 26, {
      fontSize: 22,
      bold: true,
      color: C.gold,
      align: "center",
    });
    addNotes(slide, "这是答辩的核心技术页。强调混合编程不是机械拼接，也不是加载动态库，而是两种语言各自发挥优势，并用网页组合。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（软件架构与 Python–Julia 混合编程，第 261–311 行）",
    ]);
  }

  // 07 — Runtime flow and failure isolation
  {
    const slide = addSlideBase(presentation, 7, "运行机制", "网页内嵌缩短交互链路，也形成故障隔离");
    const steps = [
      ["01", "主程序启动", "Streamlit 入口"],
      ["02", "分配端口", "启动 Julia 子进程"],
      ["03", "轻量检查", "TCP 监听就绪"],
      ["04", "网页内嵌", "加载 WGLMakie"],
      ["05", "浏览器直连", "滑块→Bonito"],
    ];
    const nodes = [];
    steps.forEach((s, i) => {
      const x = 64 + i * 238;
      const node = rect(slide, `runtime-node-${i}`, x, 230, 194, 136, C.panel2, i === 4 ? C.coral : C.line, 16);
      nodes.push(node);
      textBox(slide, `runtime-no-${i}`, s[0], x + 18, 248, 42, 26, { fontSize: 16, bold: true, color: i === 4 ? C.coral2 : C.teal });
      textBox(slide, `runtime-head-${i}`, s[1], x + 18, 284, 158, 32, { fontSize: 22, bold: true, color: C.white });
      textBox(slide, `runtime-sub-${i}`, s[2], x + 18, 326, 158, 26, { fontSize: 16, color: C.muted });
    });
    for (let i = 0; i < nodes.length - 1; i++) {
      slide.shapes.connect(nodes[i], nodes[i + 1], {
        kind: "straight",
        fromSide: "right",
        toSide: "left",
        line: { style: "solid", fill: C.teal, width: 2 },
        tail: { type: "arrow", width: "sm", length: "sm" },
      });
    }
    textBox(slide, "runtime-key", "交互事件不经过 Python 逐点复制大数组，动画链路更短。", 130, 396, 1020, 35, {
      fontSize: 22,
      bold: true,
      color: C.teal2,
      align: "center",
    });
    rect(slide, "runtime-fail-julia", 118, 474, 494, 112, C.panel2, C.coral, 14);
    textBox(slide, "runtime-fail-julia-head", "Julia 初始化失败", 146, 496, 220, 30, { fontSize: 22, bold: true, color: C.coral2 });
    textBox(slide, "runtime-fail-julia-body", "主页面继续显示状态、日志和智能问答", 146, 538, 430, 32, { fontSize: 22, color: C.ink });
    rect(slide, "runtime-fail-ai", 668, 474, 494, 112, C.panel2, C.teal, 14);
    textBox(slide, "runtime-fail-ai-head", "问答服务不可用", 696, 496, 240, 30, { fontSize: 22, bold: true, color: C.teal2 });
    textBox(slide, "runtime-fail-ai-body", "四个确定性 Julia 实验仍可独立运行", 696, 538, 430, 32, { fontSize: 22, color: C.ink });
    addNotes(slide, "按启动顺序快速说明，不必展开端口号。重点是浏览器直接交互和双向降级能力。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（Python–Julia 进程协同，第 289–324 行）",
    ]);
  }

  // 08 — Intelligent Q&A
  {
    const slide = addSlideBase(presentation, 8, "智能问答", "智能问答不是通用聊天，而是实验中的认知支架");
    richTextBox(slide, "qa-points", [
      bullet("观察后追问：", "从“这条轨迹为何不闭合”进入物理解释", C.teal),
      bullet("多模态输入：", "可粘贴轨迹、示波器截图或装置照片", C.coral),
      bullet("依据优先：", "本地专题文献与确定性工具共同约束回答", C.gold),
      bullet("回到实验：", "把参数建议直接带入 Julia 页面复核", C.teal2),
    ], 70, 224, 490, 250, { fontSize: 22 });
    rect(slide, "qa-loop", 70, 500, 490, 108, C.panel2, C.line, 14);
    textBox(slide, "qa-loop-title", "教学闭环", 94, 520, 110, 25, { fontSize: 16, bold: true, color: C.coral2 });
    textBox(slide, "qa-loop-copy", "现象观察 → 文献检索 → 物理推导\n→ 确定性计算 → 可视化验证", 94, 552, 430, 48, {
      fontSize: 22,
      bold: true,
      color: C.white,
      lineSpacing: 1.0,
    });
    addImage(slide, "qa-interface", qa, "带完整输入框的李萨如智能问答真实界面", 600, 190, 600, 446, "contain");
    addNotes(slide, "指向右侧真实界面的快速提问、图片提示和完整输入框。强调问答服务贯穿预习、实验和复盘，而不是只在结束后答疑。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（智能问答特色设计，第 337–377 行）",
      "李萨如/设计报告/assets/lissajous_qa_interface_real.png",
    ]);
  }

  // 09 — Trust chain
  {
    const slide = addSlideBase(presentation, 9, "可信问答", "文献、确定性工具和安全执行共同约束回答");
    const stages = [
      ["本地专题文献", "PDF 提取与元数据", C.teal],
      ["混合检索", "TF–IDF + BM25", C.teal2],
      ["确定性工具", "周期 · 面积 · 形状", C.gold],
      ["受限绘图", "用户确认后执行", C.coral],
    ];
    const stageNodes = [];
    stages.forEach((s, i) => {
      const x = 72 + i * 294;
      const node = rect(slide, `trust-stage-${i}`, x, 228, 236, 118, C.panel2, s[2], 16);
      stageNodes.push(node);
      textBox(slide, `trust-head-${i}`, s[0], x + 18, 248, 200, 30, { fontSize: 22, bold: true, color: C.white, align: "center" });
      textBox(slide, `trust-sub-${i}`, s[1], x + 18, 294, 200, 26, { fontSize: 16, color: s[2], align: "center" });
    });
    for (let i = 0; i < stageNodes.length - 1; i++) {
      slide.shapes.connect(stageNodes[i], stageNodes[i + 1], {
        kind: "straight",
        fromSide: "right",
        toSide: "left",
        line: { style: "solid", fill: C.line, width: 2 },
        tail: { type: "arrow", width: "sm", length: "sm" },
      });
    }
    const metrics = [
      ["≤ 6", "每轮去重来源"],
      ["55%", "候选阈值 ≥\n最高分的 55%"],
      ["60 s", "绘图执行超时"],
      ["25", "最近运行目录"],
    ];
    metrics.forEach((m, i) => {
      const x = 78 + i * 292;
      textBox(slide, `trust-metric-${i}`, m[0], x, 412, 212, 54, { fontSize: 31, bold: true, color: i === 2 ? C.coral2 : C.teal2, align: "center" });
      textBox(slide, `trust-metric-label-${i}`, m[1], x, i === 1 ? 462 : 468, 212, i === 1 ? 46 : 26, {
        fontSize: i === 1 ? 15.5 : 16,
        color: C.muted,
        align: "center",
        lineSpacing: i === 1 ? 0.95 : 1,
      });
    });
    rect(slide, "trust-caveat", 102, 548, 1076, 72, C.panel2, C.coral, 12);
    textBox(slide, "trust-caveat-copy", "文件、网络、进程和敏感环境访问被阻止；该机制不是操作系统级沙箱，公共机房可关闭代码执行。", 132, 568, 1016, 32, {
      fontSize: 22,
      color: C.ink,
      align: "center",
    });
    addNotes(slide, "本页把智能问答的可信性拆成三层：检索有来源、数值由工具算、代码执行有边界。安全机制要如实说明局限。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（专题知识库、确定性计算与受限 Python 可视化，第 379–429 行）",
    ]);
  }

  // 10 — Single-file deployment
  {
    const slide = addSlideBase(presentation, 10, "部署交付", "单文件封装让双语言系统能进入普通课堂");
    const pyPack = rect(slide, "pack-python", 76, 224, 244, 82, C.panel2, C.teal, 14);
    textBox(slide, "pack-python-text", "Python 前端\nPyInstaller", 96, 238, 204, 58, { fontSize: 22, bold: true, color: C.teal2, align: "center" });
    const jlPack = rect(slide, "pack-julia", 76, 332, 244, 82, C.panel2, C.coral, 14);
    textBox(slide, "pack-julia-text", "Julia 图形运行时\nPackageCompiler", 96, 346, 204, 58, { fontSize: 22, bold: true, color: C.coral2, align: "center" });
    const kbPack = rect(slide, "pack-kb", 76, 440, 244, 82, C.panel2, C.gold, 14);
    textBox(slide, "pack-kb-text", "专题知识库\n模型与资源清单", 96, 454, 204, 58, { fontSize: 22, bold: true, color: C.gold, align: "center" });
    const exe = rect(slide, "pack-exe", 430, 300, 242, 162, C.panel, C.teal2, 24);
    textBox(slide, "pack-exe-icon", "EXE", 472, 325, 158, 58, { fontSize: 42, bold: true, color: C.white, align: "center" });
    textBox(slide, "pack-exe-copy", "一个启动器\n协同释放与启动", 460, 388, 182, 62, { fontSize: 22, color: C.muted, align: "center" });
    [pyPack, jlPack, kbPack].forEach((node) => {
      slide.shapes.connect(node, exe, {
        kind: "elbow",
        fromSide: "right",
        toSide: "left",
        line: { style: "solid", fill: C.line, width: 2 },
        tail: { type: "arrow", width: "sm", length: "sm" },
      });
    });
    richTextBox(slide, "deploy-points", [
      bullet("目标机器：", "无需预装 Python 或 Julia", C.teal),
      bullet("统一体验：", "浏览器内同时使用演示实验与智能问答", C.coral),
      bullet("运行要求：", "64 位 Windows 10/11 与支持 WebGL 的浏览器", C.gold),
      bullet("首次启动：", "解包与 WGLMakie 初始化较慢，显示进度和日志", C.teal2),
    ], 758, 224, 446, 266, { fontSize: 22 });
    rect(slide, "deploy-bottom", 758, 514, 446, 86, C.panel2, C.line, 12);
    textBox(slide, "deploy-bottom-copy", "课堂关注“稳定打开并使用”，\n而不是开发环境是否配置完整。", 786, 526, 390, 68, {
      fontSize: 22,
      bold: true,
      color: C.white,
      align: "center",
    });
    addNotes(slide, "把单文件部署讲成教学可用性问题，而不是单纯打包技巧。首次启动较慢要主动说明进度反馈和日志机制。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（参赛单文件版与开发复现环境，第 563–580 行）",
    ]);
  }

  // 11 — Validation
  {
    const slide = addSlideBase(presentation, 11, "验证证据", "验证不止看界面，而要用解析量和测试集复核");
    rect(slide, "validation-left", 70, 212, 420, 372, C.panel2, C.line, 16);
    textBox(slide, "validation-left-label", "解析模型自检", 100, 242, 340, 32, { fontSize: 24, bold: true, color: C.teal2 });
    textBox(slide, "validation-left-formula", "S = πAB|sin φ|", 100, 302, 340, 54, { fontSize: 31, bold: true, color: C.white, typeface: MATH, align: "center" });
    textBox(slide, "validation-left-arrow", "理论值  ↔  数值面积", 100, 370, 340, 32, { fontSize: 22, color: C.coral2, align: "center" });
    textBox(slide, "validation-left-copy", "同时检查二次曲线残差、SVD 半轴、\n闭合终点误差与特殊相位边界。", 100, 426, 340, 78, { fontSize: 22, color: C.muted, align: "center" });
    textBox(slide, "validation-left-sample", "界面样例残差约 4.44×10⁻¹⁶", 100, 526, 340, 28, { fontSize: 16, bold: true, color: C.gold, align: "center" });
    textBox(slide, "validation-metric", "10 / 10", 570, 222, 300, 88, { fontSize: 52, bold: true, color: C.teal2 });
    textBox(slide, "validation-metric-label", "检索评估题 Top-5 主题命中", 574, 312, 420, 34, { fontSize: 22, bold: true, color: C.white });
    richTextBox(slide, "validation-right", [
      bullet("参数扫描：", "检查面积对称性、互质组合与正负失谐", C.teal),
      bullet("界面冒烟：", "参数联动、播放、重置和导出一致", C.coral),
      bullet("封装复测：", "送审单文件应在清洁机器重复同一组理论量", C.gold),
      bullet("教学评价：", "学习增益必须来自真实课堂数据，不能由界面完整性代替", C.teal2),
    ], 570, 386, 610, 202, { fontSize: 22 });
    textBox(slide, "validation-caveat", "仅展示已有证据；最终测试矩阵与教学数据按送审版实测填写。", 570, 596, 610, 28, {
      fontSize: 16,
      color: C.coral2,
    });
    addNotes(slide, "先讲物理自检，再讲检索评估，最后说明尚须实测的证据边界。不要把计划中的清洁机测试或教学效果说成已完成。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（模型校验、评价框架与结果验证，第 256–259、431–456、493–527 行）",
      "李萨如/设计报告/assets/lissajous_demo_interface.png（界面显示残差样例）",
    ]);
  }

  // 12 — Close
  {
    const slide = presentation.slides.add();
    slide.background.fill = C.bg;
    rect(slide, "close-top-accent", 0, 0, WIDTH, 8, C.teal);
    textBox(slide, "close-eyebrow", "CONCLUSION", 72, 70, 260, 28, { fontSize: 14, bold: true, color: C.teal });
    textBox(slide, "close-title", "一份文件 · 两种语言\n三条证据链 · 四个实验", 72, 148, 1136, 145, {
      fontSize: 67,
      bold: true,
      color: C.white,
      align: "center",
      lineSpacing: 0.95,
    });
    line(slide, "close-rule", 280, 334, 720, 0, C.line, 2);
    const summary = [
      ["1", "文件", "降低部署门槛", C.coral],
      ["2", "语言", "Python 编排 / Julia 计算", C.teal],
      ["3", "证据链", "模型 / 交互 / 问答", C.gold],
      ["4", "实验", "相位 / 振幅 / 频比 / 失谐", C.teal2],
    ];
    summary.forEach((s, i) => {
      const x = 84 + i * 296;
      textBox(slide, `close-n-${i}`, s[0], x, 382, 56, 60, { fontSize: 40, bold: true, color: s[3], align: "center" });
      textBox(slide, `close-head-${i}`, s[1], x + 64, 388, 190, 34, { fontSize: 24, bold: true, color: C.white });
      textBox(slide, `close-body-${i}`, s[2], x + 64, 430, 190, 54, { fontSize: 20, color: C.muted });
    });
    rect(slide, "close-statement", 186, 534, 908, 92, C.panel2, C.line, 18);
    textBox(slide, "close-statement-text", "模型给出结果，问答帮助解释，公式与数据负责裁决。", 222, 560, 836, 42, {
      fontSize: 24,
      bold: true,
      color: C.coral2,
      align: "center",
    });
    textBox(slide, "close-footer", "面向预习、课堂演示、自主探究与实验复盘", 72, 668, 1136, 24, {
      fontSize: 13,
      color: C.dim,
      align: "center",
    });
    addNotes(slide, "结尾回扣开场：本作品的价值不是技术堆叠，而是让学生沿着可核查证据从图形现象走向物理解释。", [
      "李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex（创新性、推广场景与结论，第 529–547、631–636 行）",
    ]);
  }

  // Export previews, layouts, montage and PPTX.
  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(path.join(RENDER_DIR, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(RENDER_DIR, `${stem}.layout.json`), await layout.text(), "utf8");
  }
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(FINAL_PPTX);

  const sidecarInspect = `${FINAL_PPTX}.inspect.ndjson`;
  const retainedInspect = path.join(BUILD_DIR, "final-pptx.inspect.ndjson");
  try {
    await fs.rm(retainedInspect, { force: true });
    await fs.rename(sidecarInspect, retainedInspect);
  } catch {
    // The sidecar is produced by current artifact-tool builds; older builds may omit it.
  }

  await fs.writeFile(
    path.join(BUILD_DIR, "source-notes.txt"),
    [
      "All claims and visuals are sourced from the current local project.",
      "Primary source: 李萨如/设计报告/李萨如图形虚拟实验教学资源设计报告.tex",
      "Images:",
      "- 李萨如/李萨如_RAG智能体/assets/lissajous_header.png",
      "- 李萨如/李萨如图形可视化实验说明/实验一_Julia可视化方案/output/interface_preview.png",
      "- 李萨如/设计报告/assets/lissajous_demo_interface.png",
      "- 李萨如/设计报告/assets/lissajous_qa_interface_real.png",
      "No external web assets were used.",
    ].join("\n"),
    "utf8",
  );

  console.log(JSON.stringify({ finalPptx: FINAL_PPTX, renderDir: RENDER_DIR, slides: presentation.slides.items.length }, null, 2));
  process.exitCode = 0;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
