import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = "D:/OneDrive/文档/我的文件/git/仁爱物理竞赛";
const OUT = path.join(ROOT, "声速/设计报告/声速测量实验智能助教_答辩PPT.pptx");
const BUILD = path.join(ROOT, "tmp/ppt_build/sound");
const PREVIEW = path.join(BUILD, "artifact_render");

const ASSETS = {
  header: path.join(ROOT, "声速/声速_RAG智能体/assets/sound_speed_header.png"),
  demo: path.join(ROOT, "声速/设计报告/assets/sound_demo_interface.png"),
  qa: path.join(ROOT, "声速/设计报告/assets/sound_qa_interface_real.png"),
  echo: path.join(ROOT, "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_echo.png"),
  dual: path.join(ROOT, "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_dual_microphone.png"),
  phase: path.join(ROOT, "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_oscilloscope_phase.png"),
  standing: path.join(ROOT, "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_standing_wave.png"),
  echoCrop: path.join(ROOT, "tmp/ppt_build/sound/crops/echo_double_pulse.png"),
  dualCrop: path.join(ROOT, "tmp/ppt_build/sound/crops/dual_correlation_peak.png"),
  phaseCrop: path.join(ROOT, "tmp/ppt_build/sound/crops/phase_periodicity.png"),
  standingCrop: path.join(ROOT, "tmp/ppt_build/sound/crops/standing_envelope.png"),
};

const C = {
  cream: "#F4EFE5",
  paper: "#FBF8F1",
  slate: "#253238",
  slate2: "#34434A",
  ink: "#263238",
  muted: "#667276",
  rule: "#D8D0C2",
  amber: "#E5A43A",
  amberDark: "#A96B12",
  amberPale: "#F4E4C2",
  mint: "#4FAF9B",
  mintDark: "#247B6E",
  mintPale: "#DCEFE9",
  white: "#FFFDF8",
  softSlate: "#E7EBE9",
};

const FONT_CN = "Microsoft YaHei";
const FONT_LATIN = "Segoe UI";

async function imageBytes(filePath) {
  const bytes = await fs.readFile(filePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function addShape(slide, geometry, pos, fill = "none", line = { style: "solid", fill: "none", width: 0 }, opts = {}) {
  return slide.shapes.add({ geometry, position: pos, fill, line, ...opts });
}

function addText(slide, text, pos, opts = {}) {
  const shape = addShape(slide, "textbox", pos, opts.fill ?? "none", opts.line ?? { style: "solid", fill: "none", width: 0 }, {
    name: opts.name,
    borderRadius: opts.borderRadius,
  });
  shape.text = text;
  shape.text.style = {
    fontSize: opts.fontSize ?? 24,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "top",
    autoFit: opts.autoFit ?? "shrinkText",
    wrap: "square",
    insets: opts.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
    typeface: opts.typeface ?? FONT_CN,
    lineSpacing: opts.lineSpacing ?? 1.05,
  };
  return shape;
}

function addBulletList(slide, items, pos, opts = {}) {
  const gap = opts.gap ?? 16;
  const bulletSize = opts.bulletSize ?? 11;
  const textSize = opts.fontSize ?? 22;
  const itemHeight = opts.itemHeight ?? 54;
  const color = opts.color ?? C.ink;
  const bulletColor = opts.bulletColor ?? C.mint;
  items.forEach((item, i) => {
    const top = pos.top + i * (itemHeight + gap);
    addShape(slide, "ellipse", { left: pos.left, top: top + 8, width: bulletSize, height: bulletSize }, bulletColor);
    addText(slide, item, { left: pos.left + 24, top, width: pos.width - 24, height: itemHeight }, {
      fontSize: textSize, color, lineSpacing: 1.08,
    });
  });
}

function addHeader(slide, eyebrow, title, page, dark = false) {
  const primary = dark ? C.cream : C.ink;
  const secondary = dark ? C.mint : C.mintDark;
  addText(slide, eyebrow, { left: 72, top: 40, width: 520, height: 26 }, {
    fontSize: 17, bold: true, color: secondary, typeface: FONT_LATIN,
  });
  addText(slide, title, { left: 72, top: 76, width: 1060, height: 64 }, {
    fontSize: 48, bold: true, color: primary, lineSpacing: 0.95,
  });
  addText(slide, String(page).padStart(2, "0"), { left: 1160, top: 48, width: 48, height: 26 }, {
    fontSize: 18, bold: true, color: dark ? C.amber : C.amberDark, align: "right", typeface: FONT_LATIN,
  });
}

function addFooter(slide, page, dark = false) {
  const lineColor = dark ? C.slate2 : C.rule;
  addShape(slide, "line", { left: 72, top: 686, width: 1136, height: 0 }, "none", { style: "solid", fill: lineColor, width: 1 });
  addText(slide, "声速测量实验智能助教", { left: 72, top: 694, width: 320, height: 18 }, {
    fontSize: 12, color: dark ? "#AEB9B7" : C.muted, typeface: FONT_CN,
  });
  addText(slide, `${page} / 12`, { left: 1120, top: 694, width: 88, height: 18 }, {
    fontSize: 12, color: dark ? "#AEB9B7" : C.muted, align: "right", typeface: FONT_LATIN,
  });
}

function setNotes(slide, narration, sources) {
  slide.speakerNotes.textFrame.setText(`${narration}\n\n[Sources]\n${sources.map((s) => `- ${s}`).join("\n")}\n[/Sources]`);
  slide.speakerNotes.setVisible(true);
}

function newSlide(presentation, dark = false) {
  const slide = presentation.slides.add();
  slide.background.fill = dark ? C.slate : C.cream;
  return slide;
}

function addImage(slide, blob, alt, pos, opts = {}) {
  const im = slide.images.add({
    blob,
    contentType: "image/png",
    alt,
    fit: opts.fit ?? "cover",
    crop: opts.crop,
    position: pos,
    geometry: opts.geometry ?? "roundRect",
    borderRadius: opts.radius ?? "rounded-xl",
  });
  return im;
}

function addLabel(slide, text, pos, dark = false, accent = C.amber) {
  addShape(slide, "rect", { left: pos.left, top: pos.top + 6, width: 6, height: pos.height - 12 }, accent);
  addText(slide, text, { left: pos.left + 18, top: pos.top, width: pos.width - 18, height: pos.height }, {
    fontSize: 24, bold: true, color: dark ? C.cream : C.ink, valign: "middle",
  });
}

async function main() {
  await fs.mkdir(PREVIEW, { recursive: true });
  await fs.mkdir(path.dirname(OUT), { recursive: true });
  const img = {};
  for (const [key, filePath] of Object.entries(ASSETS)) img[key] = await imageBytes(filePath);

  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

  // 1 — Title
  {
    const s = newSlide(presentation, true);
    addImage(s, img.header, "音叉与声波波前主视觉", { left: 0, top: 0, width: 1280, height: 720 }, { fit: "cover", geometry: "rect", radius: 0 });
    addText(s, "第十二届全国大学生物理实验竞赛（创新）", { left: 76, top: 70, width: 510, height: 32 }, {
      fontSize: 17, bold: true, color: C.mint, typeface: FONT_CN,
    });
    addText(s, "声速测量实验\n智能助教", { left: 76, top: 144, width: 520, height: 166 }, {
      fontSize: 66, bold: true, color: C.cream, lineSpacing: 0.9,
    });
    addShape(s, "rect", { left: 76, top: 334, width: 92, height: 7 }, C.amber);
    addText(s, "回声 · 时间差 · 相位 · 驻波", { left: 76, top: 374, width: 500, height: 42 }, {
      fontSize: 28, bold: true, color: C.white,
    });
    addText(s, "同一真实声速　不同观测路径　全过程可复算", { left: 76, top: 432, width: 520, height: 60 }, {
      fontSize: 21, color: "#C7D1CF",
    });
    addText(s, "自选题 2 · 教学资源和虚仿", { left: 76, top: 622, width: 420, height: 28 }, {
      fontSize: 18, bold: true, color: C.amber,
    });
    setNotes(s, "开场只提出一个问题：公式很简单，学生真正理解的是怎样从观测量得到声速吗？", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex",
      "声速/声速_RAG智能体/assets/sound_speed_header.png",
    ]);
  }

  // 2 — Challenge
  {
    const s = newSlide(presentation, false);
    addHeader(s, "WHY THIS LAB", "难点不在公式，而在“声速怎样被测出来”", 2, false);
    addBulletList(s, [
      "四种方法最终都求 v，但直接观测量完全不同。",
      "传统课堂常只保留最终数值，测量链被隐藏。",
      "实体实验难以连续扫描采样率、噪声、角度与反射条件。",
    ], { left: 76, top: 184, width: 494 }, { itemHeight: 58, gap: 18, fontSize: 22, bulletColor: C.amber });

    addText(s, "v = ?", { left: 810, top: 178, width: 300, height: 100 }, {
      fontSize: 76, bold: true, color: C.amberDark, align: "center", valign: "middle", typeface: FONT_LATIN,
    });
    // arrows first, labels above them
    [624, 785, 946].forEach((left) => addShape(s, "rightArrow", { left, top: 392, width: 110, height: 42 }, C.mintPale, { style: "solid", fill: C.mint, width: 1 }));
    const stages = [
      [590, "传播过程", "声波走过哪段路程"],
      [751, "传感器信号", "仪器实际记录什么"],
      [912, "分析观测量", "峰值与相关\n相位与波节"],
      [1073, "声速估计", "公式、单位与误差"],
    ];
    stages.forEach(([left, title, body], i) => {
      addText(s, String(i + 1).padStart(2, "0"), { left, top: 338, width: 52, height: 28 }, { fontSize: 18, bold: true, color: C.mintDark, typeface: FONT_LATIN });
      addText(s, title, { left, top: 448, width: 142, height: 34 }, { fontSize: 21, bold: true, color: C.ink, align: "center" });
      addText(s, body, { left: left - 4, top: 488, width: 150, height: 62 }, { fontSize: 17, color: C.muted, align: "center", lineSpacing: 1.08 });
    });
    addText(s, "作品目标：让四层证据同时可见、相互校验。", { left: 74, top: 586, width: 1120, height: 46 }, {
      fontSize: 29, bold: true, color: C.mintDark, align: "center",
    });
    addFooter(s, 2, false);
    setNotes(s, "先建立教学痛点，再自然引出统一测量链。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第1章）",
    ]);
  }

  // 3 — Four inverse paths
  {
    const s = newSlide(presentation, false);
    addHeader(s, "ONE SPEED, FOUR OBSERVATIONS", "同一声速，四条独立反演路径", 3, false);
    addText(s, "共同模型", { left: 76, top: 168, width: 170, height: 32 }, { fontSize: 23, bold: true, color: C.mintDark });
    addText(s, "v = fλ", { left: 76, top: 212, width: 214, height: 78 }, { fontSize: 58, bold: true, color: C.amberDark, typeface: FONT_LATIN });
    addText(s, "真实声速生成信号；\n估计值由观测量反演。", { left: 76, top: 304, width: 248, height: 104 }, { fontSize: 21, color: C.muted, lineSpacing: 1.1 });
    addText(s, "εᵣ = (v̂ − v) / v × 100%", { left: 76, top: 446, width: 276, height: 48 }, { fontSize: 24, bold: true, color: C.ink, typeface: FONT_LATIN });

    const rows = [
      ["回声法", "往返时延 Δt", "v̂ = 2d / Δt", C.amber],
      ["双麦克风", "互相关峰时延", "v̂ = d cosθ / Δt", C.mint],
      ["相位差", "包裹相位 φw\nn：完整周期数", "v̂ = 2πfd / (2πn + φw)", C.amber],
      ["驻波法", "q 个波节间隔 Dq\nq：跨越的波节间隔数", "v̂ = 2fDq / q", C.mint],
    ];
    rows.forEach((r, i) => {
      const y = 168 + i * 104;
      addShape(s, "rect", { left: 382, top: y, width: 8, height: 74 }, r[3]);
      addText(s, r[0], { left: 410, top: y, width: 160, height: 34 }, { fontSize: 25, bold: true, color: C.ink });
      addText(s, r[1], { left: 580, top: y + 2, width: 244, height: 64 }, { fontSize: 22, color: C.muted, lineSpacing: 1.08 });
      addText(s, r[2], { left: 824, top: y, width: 370, height: 38 }, { fontSize: 27, bold: true, color: i % 2 ? C.mintDark : C.amberDark, typeface: FONT_LATIN });
      addShape(s, "line", { left: 410, top: y + 72, width: 784, height: 0 }, "none", { style: "solid", fill: C.rule, width: 1 });
    });
    addText(s, "差别不在公式数量，而在观测机制、二义性与误差传播。", { left: 382, top: 598, width: 812, height: 42 }, { fontSize: 26, bold: true, color: C.ink });
    addFooter(s, 3, false);
    setNotes(s, "用一页建立四种方法的统一语言，后续两页再分别展开时间域与相位/空间域。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第163—314行）",
    ]);
  }

  // 4 — Time domain methods
  {
    const s = newSlide(presentation, true);
    addHeader(s, "TIME-DOMAIN METHODS", "时间域方法把传播距离变成可测时延", 4, true);
    addText(s, "回声法", { left: 72, top: 160, width: 190, height: 38 }, { fontSize: 28, bold: true, color: C.amber });
    addText(s, "双麦克风时间差", { left: 654, top: 160, width: 280, height: 38 }, { fontSize: 28, bold: true, color: C.mint });
    addImage(s, img.echoCrop, "回声法双脉冲波形重点视图", { left: 72, top: 208, width: 552, height: 332 }, { fit: "contain" });
    addImage(s, img.dualCrop, "双麦克风互相关峰重点视图", { left: 654, top: 208, width: 554, height: 332 }, { fit: "contain" });
    addText(s, "v̂ = 2d / Δt", { left: 86, top: 556, width: 230, height: 40 }, { fontSize: 31, bold: true, color: C.amber, typeface: FONT_LATIN });
    addText(s, "识别直达脉冲与回波；\n反射系数、SNR 与采样率共同影响峰值可靠性。", { left: 320, top: 552, width: 304, height: 72 }, { fontSize: 18, color: "#CBD4D2", lineSpacing: 1.08 });
    addText(s, "v̂ = d cosθ / Δt", { left: 668, top: 556, width: 294, height: 40 }, { fontSize: 31, bold: true, color: C.mint, typeface: FONT_LATIN });
    addText(s, "归一化互相关利用整段波形；\n同步采样、方向修正与时延量化决定精度。", { left: 964, top: 552, width: 244, height: 72 }, { fontSize: 18, color: "#CBD4D2", lineSpacing: 1.08 });
    addFooter(s, 4, true);
    setNotes(s, "强调两种方法都测时延，但一个是往返路径，一个是单程投影路径。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第200—249行）",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_echo.png",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_dual_microphone.png",
    ]);
  }

  // 5 — Phase and standing waves
  {
    const s = newSlide(presentation, false);
    addHeader(s, "PHASE & SPACE", "相位与驻波把短时延转化为相位或空间周期", 5, false);
    addImage(s, img.phaseCrop, "相位周期曲线重点视图", { left: 72, top: 168, width: 550, height: 326 }, { fit: "contain" });
    addImage(s, img.standingCrop, "驻波包络重点视图", { left: 654, top: 168, width: 554, height: 326 }, { fit: "contain" });
    addLabel(s, "相位差法", { left: 72, top: 508, width: 200, height: 42 }, false, C.amber);
    addText(s, "v̂ = 2πfd / (2πn + φw)", { left: 292, top: 510, width: 330, height: 38 }, { fontSize: 27, bold: true, color: C.amberDark, align: "right", typeface: FONT_LATIN });
    addText(s, "高灵敏度来自相位读数；完整周期数 n 误判一周，会造成远大于一般噪声的系统偏差。", { left: 72, top: 560, width: 550, height: 72 }, { fontSize: 19, color: C.muted, lineSpacing: 1.08 });
    addLabel(s, "驻波法", { left: 654, top: 508, width: 180, height: 42 }, false, C.mint);
    addText(s, "v̂ = 2fDq / q", { left: 902, top: 510, width: 306, height: 38 }, { fontSize: 29, bold: true, color: C.mintDark, align: "right", typeface: FONT_LATIN });
    addText(s, "跨多个波节间隔降低相对读数误差；反射不完全时，波节是非零振幅极小值。", { left: 654, top: 560, width: 554, height: 72 }, { fontSize: 19, color: C.muted, lineSpacing: 1.08 });
    addFooter(s, 5, false);
    setNotes(s, "这页突出二义性与非理想边界，而不是只展示漂亮的正弦曲线。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第251—307行）",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_oscilloscope_phase.png",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_standing_wave.png",
    ]);
  }

  // 6 — Interface
  {
    const s = newSlide(presentation, false);
    addHeader(s, "VISIBLE MEASUREMENT CHAIN", "空间过程、原始信号与分析结果同步呈现", 6, false);
    addImage(s, img.demo, "声速四种测量方法综合界面", { left: 390, top: 160, width: 818, height: 482 }, { fit: "contain" });
    addText(s, "三层证据", { left: 72, top: 174, width: 250, height: 38 }, { fontSize: 30, bold: true, color: C.amberDark });
    addBulletList(s, [
      "空间传播：声波走过哪段路程",
      "原始信号：传感器记录了什么",
      "分析曲线：算法怎样提取读数",
      "实时结果：理论、测量与误差并列",
    ], { left: 76, top: 238, width: 286 }, { itemHeight: 50, gap: 15, fontSize: 20, bulletColor: C.mint });
    addShape(s, "roundRect", { left: 72, top: 518, width: 282, height: 112 }, C.amberPale, { style: "solid", fill: C.amber, width: 1 }, { borderRadius: "rounded-xl" });
    addText(s, "343 m/s → 341.64 m/s", { left: 92, top: 538, width: 242, height: 38 }, { fontSize: 24, bold: true, color: C.ink, align: "center", typeface: FONT_LATIN });
    addText(s, "回声示例相对误差约 −0.40%\nCSV 可独立复算全部中间量", { left: 92, top: 582, width: 242, height: 40 }, { fontSize: 16, color: C.muted, align: "center" });
    addFooter(s, 6, false);
    setNotes(s, "现场可用这页引导评委从左到右看界面：空间、波形、分析、读数。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第366—388、555—573行）",
      "声速/设计报告/assets/sound_demo_interface.png",
    ]);
  }

  // 7 — Python Julia
  {
    const s = newSlide(presentation, true);
    addHeader(s, "HYBRID PROGRAMMING", "Python 管应用，Julia 管科学计算", 7, true);
    // connectors first
    addShape(s, "rightArrow", { left: 486, top: 284, width: 308, height: 82 }, C.mintDark, { style: "solid", fill: C.mint, width: 1 });
    addShape(s, "rightArrow", { left: 486, top: 404, width: 308, height: 54 }, C.amberDark, { style: "solid", fill: C.amber, width: 1 });
    addShape(s, "roundRect", { left: 72, top: 168, width: 430, height: 420 }, C.slate2, { style: "solid", fill: C.mint, width: 2 }, { borderRadius: "rounded-2xl" });
    addShape(s, "roundRect", { left: 778, top: 168, width: 430, height: 420 }, "#1E292E", { style: "solid", fill: C.amber, width: 2 }, { borderRadius: "rounded-2xl" });
    addText(s, "PYTHON / STREAMLIT", { left: 102, top: 202, width: 370, height: 40 }, { fontSize: 28, bold: true, color: C.mint, typeface: FONT_LATIN });
    addText(s, "统一网页与对话状态\n本地文献检索与智能问答\n图片输入与安全代码执行\n端口、日志与进程生命周期", { left: 102, top: 270, width: 346, height: 232 }, { fontSize: 23, color: C.cream, lineSpacing: 1.45 });
    addText(s, "JULIA / WGLMAKIE", { left: 808, top: 202, width: 370, height: 40 }, { fontSize: 28, bold: true, color: C.amber, typeface: FONT_LATIN });
    addText(s, "四种确定性物理模型\n含噪信号与分析算法\nBonito 可观察状态\n浏览器 WebGL 交互图形", { left: 808, top: 270, width: 346, height: 232 }, { fontSize: 23, color: C.cream, lineSpacing: 1.45 });
    addText(s, "本机回环网页嵌入", { left: 510, top: 302, width: 260, height: 34 }, { fontSize: 20, bold: true, color: C.white, align: "center" });
    addText(s, "CSV / PNG", { left: 532, top: 417, width: 210, height: 28 }, { fontSize: 18, bold: true, color: C.white, align: "center", typeface: FONT_LATIN });
    addText(s, "实验控件由浏览器与 Julia 直接交换状态；Python 不逐帧转发大数组。", { left: 240, top: 616, width: 800, height: 38 }, { fontSize: 23, bold: true, color: C.mint, align: "center" });
    addFooter(s, 7, true);
    setNotes(s, "这是技术特色页：强调职责边界、直接交互与进程级故障隔离。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第318—364行）",
      "声速/声速_RAG智能体/app.py",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/web/web.jl",
    ]);
  }

  // 8 — Intelligent Q&A
  {
    const s = newSlide(presentation, false);
    addHeader(s, "EXPERIMENT-SPECIFIC TUTOR", "智能问答不是答案机，而是实验解释层", 8, false);
    addImage(s, img.qa, "声速实验智能问答真实界面", { left: 500, top: 152, width: 708, height: 504 }, { fit: "contain" });
    addText(s, "围绕四种测量方法", { left: 72, top: 174, width: 382, height: 38 }, { fontSize: 30, bold: true, color: C.amberDark });
    addBulletList(s, [
      "快速提问、连续追问与多图粘贴",
      "本地声学文献提供主要依据",
      "明确参数调用自研公式工具复算",
      "问答不生成、不修改 Julia 测量值",
      "校内版本仅使用服务器本地模型",
    ], { left: 76, top: 238, width: 386 }, { itemHeight: 44, gap: 13, fontSize: 20, bulletColor: C.mint });
    addText(s, "观察信号 → 检索文献 → 解释算法 → 确定性复算 → 比较方案", { left: 76, top: 580, width: 386, height: 62 }, { fontSize: 21, bold: true, color: C.mintDark, lineSpacing: 1.1 });
    addFooter(s, 8, false);
    setNotes(s, "用真实界面说明问答支持文字、快速提问和完整输入框；强调模型只负责解释。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第390—430、472—477行）",
      "声速/设计报告/assets/sound_qa_interface_real.png",
    ]);
  }

  // 9 — Trust chain
  {
    const s = newSlide(presentation, false);
    addHeader(s, "TRACEABLE & CONTROLLED", "用检索、确定性工具和执行隔离约束回答", 9, false);
    // pipeline arrows first
    [242, 448, 654, 860].forEach((left) => addShape(s, "rightArrow", { left, top: 238, width: 98, height: 42 }, C.mintPale, { style: "solid", fill: C.mint, width: 1 }));
    const flow = [
      [72, "问题 / 图片", "描述实验现象"],
      [278, "查询扩展", "识别声学主题"],
      [484, "混合检索", "TF–IDF + BM25"],
      [690, "确定性复算", "公式、单位、量纲"],
      [896, "流式解释", "或本地检索回退"],
    ];
    flow.forEach(([x, title, body], i) => {
      addShape(s, "roundRect", { left: x, top: 186, width: 178, height: 138 }, i === 3 ? C.amberPale : C.white, { style: "solid", fill: i === 3 ? C.amber : C.rule, width: 1 }, { borderRadius: "rounded-xl", shadow: "shadow-sm" });
      addText(s, title, { left: x + 12, top: 210, width: 154, height: 32 }, { fontSize: 23, bold: true, color: i === 3 ? C.amberDark : C.ink, align: "center" });
      addText(s, body, { left: x + 12, top: 258, width: 154, height: 42 }, { fontSize: 16, color: C.muted, align: "center" });
    });
    addText(s, "8 / 8", { left: 90, top: 400, width: 170, height: 76 }, { fontSize: 54, bold: true, color: C.amberDark, align: "center", typeface: FONT_LATIN });
    addText(s, "跨主题问题前 5 条检索结果均命中预设主题\n仅代表召回覆盖，不替代回答正确性评价", { left: 72, top: 486, width: 280, height: 92 }, { fontSize: 18, color: C.muted, align: "center", lineSpacing: 1.1 });
    addLabel(s, "图像边界", { left: 408, top: 394, width: 220, height: 42 }, false, C.mint);
    addText(s, "缺少刻度或信息不足时，必须说明不确定性，不编造精确读数。", { left: 426, top: 450, width: 318, height: 86 }, { fontSize: 20, color: C.ink, lineSpacing: 1.1 });
    addLabel(s, "受限执行", { left: 802, top: 394, width: 220, height: 42 }, false, C.amber);
    addText(s, "用户主动确认 → 正则与 AST 检查 → 独立输出目录 → 默认 60 s 超时。", { left: 820, top: 450, width: 344, height: 86 }, { fontSize: 20, color: C.ink, lineSpacing: 1.1 });
    addText(s, "生成式解释不能覆盖确定性计算结果。", { left: 398, top: 594, width: 760, height: 40 }, { fontSize: 28, bold: true, color: C.mintDark, align: "center" });
    addFooter(s, 9, false);
    setNotes(s, "特别限定 8/8 的含义：这是检索主题命中，不是回答正确率。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第432—509行）",
      "声速/声速_RAG智能体/evaluate.py",
      "声速/声速_RAG智能体/code_runner.py",
    ]);
  }

  // 10 — Single file
  {
    const s = newSlide(presentation, true);
    addHeader(s, "ONE-FILE DELIVERY", "单文件封装让完整助教脱离开发环境运行", 10, true);
    // arrows first
    [292, 572, 852].forEach((left) => addShape(s, "rightArrow", { left, top: 288, width: 126, height: 58 }, C.amberDark, { style: "solid", fill: C.amber, width: 1 }));
    const stages = [
      [72, "PackageCompiler", "Julia + WGLMakie\n字体与着色器"],
      [352, "PyInstaller", "Python 前端\n知识库与启动器"],
      [632, "单文件 EXE", "资源解包\n动态端口与日志"],
      [912, "浏览器运行", "无需预装\nPython / Julia"],
    ];
    stages.forEach(([x, title, body], i) => {
      addShape(s, "roundRect", { left: x, top: 210, width: 236, height: 210 }, i === 2 ? "#39484F" : C.slate2, { style: "solid", fill: i % 2 ? C.mint : C.amber, width: 2 }, { borderRadius: "rounded-2xl" });
      addText(s, String(i + 1).padStart(2, "0"), { left: x + 22, top: 232, width: 50, height: 28 }, { fontSize: 18, bold: true, color: i % 2 ? C.mint : C.amber, typeface: FONT_LATIN });
      addText(s, title, { left: x + 22, top: 280, width: 192, height: 38 }, { fontSize: i === 0 ? 20 : 25, bold: true, color: C.cream, align: "center", typeface: i < 2 ? FONT_LATIN : FONT_CN });
      addText(s, body, { left: x + 22, top: 334, width: 192, height: 64 }, { fontSize: 19, color: "#C9D3D1", align: "center", lineSpacing: 1.1 });
    });
    addShape(s, "roundRect", { left: 72, top: 472, width: 1136, height: 150 }, "#1E292E", { style: "solid", fill: C.mint, width: 1 }, { borderRadius: "rounded-xl" });
    addText(s, "589.7 MiB", { left: 100, top: 500, width: 262, height: 58 }, { fontSize: 47, bold: true, color: C.amber, typeface: FONT_LATIN });
    addText(s, "当前单文件\n618,384,360 字节", { left: 102, top: 560, width: 260, height: 44 }, { fontSize: 16, color: "#C9D3D1", typeface: FONT_CN });
    addText(s, "64 位 Windows 10 / 11\n支持 WebGL 的 Edge 或 Chrome", { left: 438, top: 504, width: 324, height: 80 }, { fontSize: 23, bold: true, color: C.cream, align: "center", lineSpacing: 1.15 });
    addText(s, "首次启动：解包并初始化 Julia\n启动器持续显示阶段与日志位置", { left: 824, top: 504, width: 336, height: 80 }, { fontSize: 22, color: C.cream, align: "center", lineSpacing: 1.15 });
    addFooter(s, 10, true);
    setNotes(s, "明确区分构建环境和目标环境：开发时需要 Python/Julia，最终目标机不需要。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第644—661行）",
      "声速/声速_RAG智能体/packaging/README.md",
      "声速/声速_RAG智能体/packaging/build_onefile.ps1",
      "声速/声速_RAG智能体/packaging/build_julia_app.jl",
      "声速/声速_RAG智能体/packaging/launcher.py",
      "声速/声速_RAG智能体/packaging/dist/single/声速测量实验智能助教_单文件版.exe",
    ]);
  }

  // 11 — Teaching loop
  {
    const s = newSlide(presentation, false);
    addHeader(s, "LEARNING LOOP", "“预测—观察—复算—解释”构成教学闭环", 11, false);
    // long line first
    addShape(s, "rightArrow", { left: 154, top: 316, width: 946, height: 70 }, C.mintPale, { style: "solid", fill: C.mint, width: 1 });
    const phases = [
      [96, "01", "预习预测", "辨认直接观测量\n先判断参数影响方向"],
      [380, "02", "实验观察", "单变量扫描\n追踪传播与信号形成"],
      [664, "03", "数据复算", "导出 CSV\n核对中间量与单位"],
      [948, "04", "证据解释", "问答辅助讨论\n结论回到公式和数据"],
    ];
    phases.forEach(([x, num, title, body], i) => {
      addShape(s, "ellipse", { left: x, top: 260, width: 116, height: 116 }, i % 2 ? C.amber : C.mint, { style: "solid", fill: C.white, width: 5 });
      addText(s, num, { left: x, top: 286, width: 116, height: 54 }, { fontSize: 36, bold: true, color: C.white, align: "center", valign: "middle", typeface: FONT_LATIN });
      addText(s, title, { left: x - 36, top: 404, width: 188, height: 38 }, { fontSize: 25, bold: true, color: C.ink, align: "center" });
      addText(s, body, { left: x - 56, top: 458, width: 228, height: 72 }, { fontSize: 18, color: C.muted, align: "center", lineSpacing: 1.1 });
    });
    addText(s, "同一界面支持实验前预习、课堂演示、分组比较、课后复盘与开放探究。", { left: 132, top: 590, width: 1016, height: 42 }, { fontSize: 27, bold: true, color: C.mintDark, align: "center" });
    addFooter(s, 11, false);
    setNotes(s, "价值不在于缩短思考，而是让学生形成可以被检查的实验论证过程。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第127—160、513—551、592—603行）",
    ]);
  }

  // 12 — Close
  {
    const s = newSlide(presentation, true);
    addHeader(s, "TAKEAWAY", "把“公式验证”升级为“测量方案设计”", 12, true);
    addText(s, "让每个声速结论都能回到", { left: 112, top: 182, width: 1056, height: 54 }, { fontSize: 34, color: "#C5CFCD", align: "center" });
    addText(s, "传播过程 · 原始信号 · 物理公式 · 数据来源", { left: 86, top: 252, width: 1108, height: 74 }, { fontSize: 45, bold: true, color: C.cream, align: "center" });
    addShape(s, "rect", { left: 430, top: 350, width: 420, height: 7 }, C.amber);
    const proof = [
      [118, "四种方法", "统一条件横向比较"],
      [402, "确定性核心", "结果透明、可复算"],
      [686, "智能解释", "本地知识与工具约束"],
      [970, "单文件部署", "无 Python / Julia 环境"],
    ];
    proof.forEach(([x, title, body], i) => {
      addText(s, title, { left: x - 60, top: 410, width: 220, height: 38 }, { fontSize: 26, bold: true, color: i % 2 ? C.mint : C.amber, align: "center" });
      addText(s, body, { left: x - 72, top: 458, width: 244, height: 48 }, { fontSize: 18, color: "#C5CFCD", align: "center" });
    });
    addText(s, "下一步：真实双声道录音 · 温湿度修正 · 亚采样时延 · 课堂对照评价", { left: 170, top: 584, width: 940, height: 40 }, { fontSize: 23, bold: true, color: C.mint, align: "center" });
    addFooter(s, 12, true);
    setNotes(s, "结尾回扣开场：作品不是四个动画和一个聊天框的叠加，而是一条可核查的测量学习链。", [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（第605—642、713—718行）",
    ]);
  }

  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const png = await presentation.export({ slide, format: "png", scale: 1 });
    await fs.writeFile(path.join(PREVIEW, `${stem}.png`), new Uint8Array(await png.arrayBuffer()));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(PREVIEW, `${stem}.layout.json`), await layout.text(), "utf8");
  }
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(OUT);
  console.log(`Wrote ${OUT}`);
  console.log(`Slides: ${presentation.slides.items.length}`);

  const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
  await fs.writeFile(path.join(PREVIEW, "deck-montage.webp"), new Uint8Array(await montage.arrayBuffer()));
}

main()
  .then(() => {
    // The bundled Windows canvas runtime can fault during natural teardown
    // after all files are safely written; exit explicitly after completion.
    if (typeof process.reallyExit === "function") process.reallyExit(0);
    else process.exit(0);
  })
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
