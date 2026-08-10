import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = "D:/OneDrive/文档/我的文件/git/仁爱物理竞赛";
const BUILD = path.join(ROOT, "tmp/ppt_build/sound");
const STARTER = path.join(BUILD, "template-starter.pptx");
const OUT = path.join(ROOT, "声速/设计报告/声速测量实验智能助教_答辩PPT.pptx");
const SCRIPT_OUT = path.join(ROOT, "声速/设计报告/声速测量实验智能助教_10分钟讲稿.txt");
const PREVIEW = path.join(BUILD, "artifact_render");

const pages = [
  {
    seconds: 40,
    narration: "各位评委老师好，我们的作品是声速测量实验智能助教。它围绕回声、双麦克风时间差、相位差和驻波四条经典测量路径展开。我们没有把四种方法做成互不相关的动画，而是让它们共享同一个真实声速，并把传播过程、传感器信号、分析步骤和最终读数连接起来。接下来请大家始终关注一条主线：一个声速结论，能否回到可观察、可计算、可复核的证据。后续每一页都将围绕这条证据链说明物理、软件与教学设计。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（摘要、作品定位）",
      "声速/声速_RAG智能体/assets/sound_speed_header.png"
    ]
  },
  {
    seconds: 50,
    narration: "声速公式本身并不复杂，教学难点在于学生往往只记住结果，却不知道仪器实际记录了什么。回声法看两个脉冲，双麦克风法看相关峰，相位法读取包裹相位，驻波法寻找空间极小值。实体实验又很难连续改变噪声、采样率、夹角和反射系数。因此我们的目标不是替代真实实验，而是把传播、信号、分析和估计四层证据同时放到屏幕上，使学生能够追问每一步的数据来源。虚拟环境负责放大过程，真实实验仍负责提供装置经验和测量约束，两者形成互补。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（教学背景、主要困难、教学目标）"
    ]
  },
  {
    seconds: 55,
    narration: "四种方法共享波动关系，但反演所用的直接观测量不同。回声法由往返时延求速度；双麦克风法还要加入声源方向的余弦修正；相位法必须判断完整周期数，否则会出现整周二义性；驻波法则用多个波节间隔降低位置读数的相对误差。我们在同一真实声速、相同噪声与采样条件下计算相对误差，并进一步比较准确度、稳定性、二义性和适用条件。这样学生比较的不再只是四个公式，而是四种测量方案。统一基准也允许教师追问：误差变化究竟来自物理边界、采样量化，还是读数算法。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（物理原理与计算模型、误差与方法比较）"
    ]
  },
  {
    seconds: 50,
    narration: "先看时间域方法。左侧回声法把直达脉冲和反射脉冲之间的延迟换算成往返传播时间，所以距离要乘二。峰值是否可靠会受到采样率、信噪比和反射系数共同影响。右侧双麦克风法不只寻找两个局部峰值，而是对整段波形做归一化互相关，相关峰给出时延；若声源并非正对阵列，还必须修正传播方向。两种方法都测时间差，但路径定义和主要误差来源并不相同。界面允许固定其他变量逐项扫描，使峰位置、相关峰展宽和最终误差同时变化。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（回声法、双麦克风时间差）",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_echo.png",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_dual_microphone.png"
    ]
  },
  {
    seconds: 50,
    narration: "相位法和驻波法把很短的传播时延转化成更容易观察的相位量或空间周期。相位读数灵敏，但示波器只给出包裹后的相位；完整周期数判断错误一周，就会产生显著系统偏差。驻波法通过移动测量位置寻找包络极小值，并跨越多个波节间隔计算波长。我们还保留不完全反射条件，所以图中的波节不一定等于零振幅。学生可以看到理想公式在真实边界条件下如何修正。通过同时观察入射波、反射波与包络，还能区分瞬时零点和稳定的空间极小值。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（相位差、非理想反射下的驻波包络）",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_oscilloscope_phase.png",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/output/smoke_standing_wave.png"
    ]
  },
  {
    seconds: 55,
    narration: "综合实验界面遵循从空间过程到原始信号、再到分析曲线和实时读数的阅读顺序。这里特别把参数重算和播放推进分成两条路径：改变距离、频率、噪声或方法专用参数时，Julia 重新生成当前方法的数据；拖动播放进度时，只读取已经保存的结果更新当前帧，不重新抽取随机噪声。读数、动画、参考曲线和 CSV 都读取同一个结果对象，因此屏幕观察与课后复算始终对应同一组实验条件。这种设计还给排障提供明确顺序：先查状态同步，再查采样和反演，而不把随机变化误认为程序错误。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（数值计算与界面更新流程、界面与交互）",
      "声速/设计报告/assets/sound_demo_interface.png"
    ]
  },
  {
    seconds: 60,
    narration: "系统采用 Python 与 Julia 的进程级混合编程。Python/Streamlit 负责统一网页、专题检索、智能问答、图片输入、受限代码执行以及端口、日志和进程生命周期；Julia/WGLMakie 负责四种确定性物理模型、参数校验、含噪信号、分析算法和 WebGL 图形。实验控件由浏览器与 Julia 的 Bonito 会话直接交换状态，Python 只嵌入本机网页并监测服务就绪，不逐帧转发大数组。两端通过地址、状态、日志以及 CSV、PNG 交换必要信息，职责和数据边界都可以分别测试。即使 Julia 首次加载较慢或问答服务异常，主页面、日志提示和已完成的确定性结果也不会相互污染。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（软件架构、Python--Julia 混合编程与进程协同）",
      "声速/声速_RAG智能体/app.py",
      "声速/声速测量可视化实验说明/声速四种方法_Julia综合可视化方案/web/web.jl"
    ]
  },
  {
    seconds: 55,
    narration: "智能问答是本作品的实验解释层。学生可以使用快速提问、连续追问，也可以粘贴波形、示波器截图或装置照片。系统优先从本地声学文献检索依据；遇到包含距离、时延、频率、波长、夹角或相位等完整参数的问题，会调用自研公式工具确定性复算。模型负责组织解释，但不能生成或修改 Julia 的实验测量值。校内版本作为大学物理智能助教平台的专题模块，只使用学校服务器上的本地模型，专题知识库与其他单位成果严格分开。它的价值是帮助学生提出下一步可验证的问题，而不是替学生完成观察、推导和方案选择。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（智能问答特色设计、与校内平台的关系、多模态追问与确定性复算）",
      "声速/设计报告/assets/sound_qa_interface_real.png"
    ]
  },
  {
    seconds: 55,
    narration: "回答可信性由三类约束共同保证。第一，查询扩展和混合检索给出可追溯的本地文献证据；第二，只有识别到完整测量参数时才进入确定性复算，公式、单位和数量级检查结果再与检索证据汇合；第三，图片缺少刻度时必须明确不确定性，不能编造精确读数。回答中的 Python 绘图代码不会自动运行，必须由用户确认，并经过正则与抽象语法树检查，在独立目录中限时执行。生成式解释始终不能覆盖确定性计算结果。模型不可用时仍保留本地检索和公式工具，所以降级的是表达能力，不是实验和复算能力。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（专题知识库与混合检索、确定性复算、受限制的 Python 可视化、回答约束）",
      "声速/声速_RAG智能体/evaluate.py",
      "声速/声速_RAG智能体/code_runner.py"
    ]
  },
  {
    seconds: 55,
    narration: "为降低课堂部署门槛，我们用 PackageCompiler 封装 Julia、WGLMakie、字体和着色器，再用 PyInstaller 封装 Python 前端、知识库与启动器，形成当前唯一的单文件发布版，约五百九十 MiB。验收不能只看能否打开网页，而要在未安装 Python 和 Julia 的干净账户中断网启动，进入四种实验、调节参数并导出 CSV；还要覆盖首次冷启动、缓存后的热启动、中文路径、普通权限、端口占用和 WebGL 不可用等情况，并保存版本、哈希和独立日志。缓存、知识库、用户导出和故障日志分目录保存，升级或清理时不会误删学生成果。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（参赛单文件版、开发与复现环境）",
      "声速/声速_RAG智能体/packaging/README.md",
      "声速/声速_RAG智能体/packaging/build_onefile.ps1",
      "声速/声速_RAG智能体/packaging/build_julia_app.jl",
      "声速/声速_RAG智能体/packaging/launcher.py",
      "声速/声速_RAG智能体/packaging/dist/single/声速测量实验智能助教_单文件版.exe（618,567,730 字节）"
    ]
  },
  {
    seconds: 55,
    narration: "教学使用按照预测、观察、复算和解释组织，但我们还为每一步设计评价证据。实验前让学生辨认直接观测量并预测参数影响；操作阶段记录单变量扫描和任务完成情况；复算阶段检查 CSV 中间量、单位与误差传播；最后要求学生解释异常，并在迁移题中选择合适方法。教学有效性不靠主观好评判断，而比较概念前后测、操作任务完成率、误差解释质量和新情境迁移表现。问答日志只用于分析高频概念困难，不直接替代教师评分。评价结果还可反向调整默认参数、任务难度和提示顺序，形成课程改进闭环。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（适用场景、教学目标、教学有效性评价方案）"
    ]
  },
  {
    seconds: 40,
    narration: "最后总结：本作品把声速实验从公式验证升级为测量方案设计。四种方法在统一条件下比较，数值由确定性模型产生并可独立复算，智能问答以本地文献和条件复算约束解释，单文件则在无开发环境机器上接受完整验收。推广时交付的不应只有一个程序，还应包括教师说明、学生任务单、默认参数基准、异常案例、CSV 复算示例和评价量表。不同学校可保留核心模型，只替换任务单、默认参数和实体设备说明。我们希望学生最终能够回答的不只是声速是多少，而是这个结论为什么可信。谢谢各位老师。",
    sources: [
      "声速/设计报告/声速测量虚拟实验教学资源设计报告.tex（主要创新点、推广价值、结论与展望）"
    ]
  }
];

const edits = [
  [3, "同一声速，四条独立反演路径", "同一声速，四种方法在统一误差指标下比较"],
  [3, "差别不在公式数量，而在观测机制、二义性与误差传播。", "统一比较准确度、稳定性、二义性与适用条件。"],
  [6, "空间过程、原始信号与分析结果同步呈现", "参数重算与播放分离，结果对象保持一致"],
  [6, "三层证据", "四层证据"],
  [6, "分析曲线：算法怎样提取读数", "参数变化：触发当前方法重新计算"],
  [6, "实时结果：理论、测量与误差并列", "播放推进：只读结果，不重抽随机噪声"],
  [6, "回声示例相对误差约 −0.40%\nCSV 可独立复算全部中间量", "同一结果对象驱动读数、动画与 CSV\n回声示例相对误差约 −0.40%"],
  [7, "统一网页与对话状态\n本地文献检索与智能问答\n图片输入与安全代码执行\n端口、日志与进程生命周期", "统一网页、问答与图片输入\n本地文献检索与受限执行\n端口选择、日志与进程调度\n只管理服务，不转发实验数组"],
  [7, "四种确定性物理模型\n含噪信号与分析算法\nBonito 可观察状态\n浏览器 WebGL 交互图形", "四种确定性物理模型\n参数校验与当前结果对象\nBonito 直接处理控件状态\nWebGL 图形、CSV 与 PNG"],
  [7, "实验控件由浏览器与 Julia 直接交换状态；Python 不逐帧转发大数组。", "边界清楚：参数、曲线、读数留在 Julia；Python 只嵌入网页并监测就绪。"],
  [9, "用检索、确定性工具和执行隔离约束回答", "检索与条件复算共同约束回答"],
  [9, "确定性复算", "条件复算"],
  [9, "公式、单位、量纲", "参数完整才触发"],
  [9, "流式解释", "证据解释"],
  [9, "或本地检索回退", "检索与复算汇合"],
  [10, "单文件封装让完整助教脱离开发环境运行", "单文件版须在无开发环境机器上独立验收"],
  [10, "资源解包\n动态端口与日志", "资源解包\n端口、缓存与日志分区"],
  [10, "589.7 MiB", "590 MiB"],
  [10, "当前单文件\n618,384,360 字节", "当前唯一发布版\n618,567,730 字节"],
  [10, "64 位 Windows 10 / 11\n支持 WebGL 的 Edge 或 Chrome", "干净账户、离线启动\n四种实验与 CSV 导出"],
  [10, "首次启动：解包并初始化 Julia\n启动器持续显示阶段与日志位置", "覆盖冷/热启动、中文路径\n端口占用与 WebGL 降级"],
  [11, "“预测—观察—复算—解释”构成教学闭环", "教学闭环既要可复算，也要可评价"],
  [11, "预习预测", "预测前测"],
  [11, "辨认直接观测量\n先判断参数影响方向", "辨认直接观测量\n记录参数影响判断"],
  [11, "实验观察", "操作观察"],
  [11, "单变量扫描\n追踪传播与信号形成", "单变量扫描\n记录操作与任务完成"],
  [11, "导出 CSV\n核对中间量与单位", "导出 CSV\n核对中间量、单位与误差"],
  [11, "证据解释", "解释迁移"],
  [11, "问答辅助讨论\n结论回到公式和数据", "问答辅助讨论\n完成迁移题与方案评价"],
  [11, "同一界面支持实验前预习、课堂演示、分组比较、课后复盘与开放探究。", "以前后测、任务完成率、误差解释和迁移题表现构成评价证据。"],
  [12, "本地知识与工具约束", "本地知识与条件复算"],
  [12, "无 Python / Julia 环境", "干净环境可验收"],
  [12, "下一步：真实双声道录音 · 温湿度修正 · 亚采样时延 · 课堂对照评价", "推广资源包：教师说明 · 学生任务单 · CSV 基准 · 异常案例 · 评价量表"]
];

function parseNdjson(ndjson) {
  return ndjson.split(/\r?\n/).map(function (line) { return line.trim(); }).filter(Boolean).map(function (line) { return JSON.parse(line); });
}

function normalizeText(value) {
  return String(value || "").replace(/\r\n/g, "\n");
}

function buildNotes(page) {
  return [
    "[建议时长：" + page.seconds + " 秒]",
    "",
    page.narration,
    "",
    "[Sources]",
    ...page.sources.map(function (source) { return "- " + source; }),
    "[/Sources]"
  ].join("\n");
}

async function main() {
  await fs.mkdir(PREVIEW, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(STARTER));
  if (presentation.slides.items.length !== 12) {
    throw new Error("Expected 12 starter slides, found " + presentation.slides.items.length);
  }

  const snapshot = await presentation.inspect({
    kind: "textbox",
    include: "id,slide,text,textPreview,bbox",
    maxChars: 240000
  });
  const records = parseNdjson(snapshot.ndjson);

  for (const edit of edits) {
    const slideNumber = edit[0];
    const oldText = normalizeText(edit[1]);
    const newText = edit[2];
    const matches = records.filter(function (record) {
      return record.kind === "textbox" && record.slide === slideNumber && normalizeText(record.text) === oldText;
    });
    if (matches.length !== 1) {
      throw new Error("Expected one textbox on slide " + slideNumber + " for: " + oldText + "; found " + matches.length);
    }
    const target = presentation.resolve(matches[0].id);
    if (oldText.includes("\n")) target.text = newText;
    else target.text.replace(oldText, newText);
  }

  for (let index = 0; index < pages.length; index += 1) {
    const slide = presentation.slides.getItem(index);
    slide.speakerNotes.textFrame.setText(buildNotes(pages[index]));
    slide.speakerNotes.setVisible(true);
  }

  const hanCount = pages.reduce(function (sum, page) {
    const matches = page.narration.match(/[\u3400-\u4DBF\u4E00-\u9FFF]/g);
    return sum + (matches ? matches.length : 0);
  }, 0);
  if (hanCount < 2200 || hanCount > 2500) {
    throw new Error("Speaker script Han-character count must be 2200-2500, found " + hanCount);
  }
  const totalSeconds = pages.reduce(function (sum, page) { return sum + page.seconds; }, 0);
  const scriptLines = [
    "声速测量实验智能助教——约10分钟答辩讲稿",
    "",
    "建议总时长：" + Math.floor(totalSeconds / 60) + " 分 " + (totalSeconds % 60) + " 秒",
    "讲稿正文汉字数：" + hanCount,
    "建议语速：普通中文答辩语速，约 220–250 字/分钟。",
    ""
  ];
  pages.forEach(function (page, index) {
    scriptLines.push("第 " + (index + 1) + " 页（建议 " + page.seconds + " 秒）");
    scriptLines.push(page.narration);
    scriptLines.push("");
  });
  await fs.writeFile(SCRIPT_OUT, scriptLines.join("\n"), "utf8");

  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = "slide-" + String(index + 1).padStart(2, "0");
    const png = await presentation.export({ slide: slide, format: "png", scale: 1.5 });
    await fs.writeFile(path.join(PREVIEW, stem + ".png"), new Uint8Array(await png.arrayBuffer()));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(PREVIEW, stem + ".layout.json"), await layout.text(), "utf8");
  }

  const finalInspect = await presentation.inspect({
    kind: "slide,textbox,shape,image,notes,layout",
    include: "id,slide,name,title,text,textPreview,bbox,placeholders",
    maxChars: 320000
  });
  await fs.writeFile(path.join(BUILD, "final_inspect.ndjson"), finalInspect.ndjson, "utf8");

  const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
  await fs.writeFile(path.join(PREVIEW, "deck-montage.webp"), new Uint8Array(await montage.arrayBuffer()));

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(OUT);
  console.log("Wrote " + OUT);
  console.log("Wrote " + SCRIPT_OUT);
  console.log("Slides: " + presentation.slides.items.length);
  console.log("Suggested duration: " + totalSeconds + " seconds");
  console.log("Speaker-script Han characters: " + hanCount);
}

main()
  .then(function () {
    if (typeof process.reallyExit === "function") process.reallyExit(0);
    else process.exit(0);
  })
  .catch(function (error) {
    console.error(error);
    process.exitCode = 1;
  });
