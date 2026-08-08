import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = "D:/OneDrive/文档/我的文件/git/仁爱物理竞赛";
const INPUT = path.join(ROOT, "声速/设计报告/声速测量实验智能助教_答辩PPT.pptx");
const OUTPUT = path.join(ROOT, "tmp/ppt_build/sound/render_recolor");

async function main() {
  await fs.mkdir(OUTPUT, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(INPUT));
  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${index + 1}`;
    const png = await presentation.export({ slide, format: "png", scale: 1.25 });
    await fs.writeFile(path.join(OUTPUT, `${stem}.png`), new Uint8Array(await png.arrayBuffer()));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(OUTPUT, `${stem}.layout.json`), await layout.text(), "utf8");
  }
  const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
  await fs.writeFile(path.join(OUTPUT, "deck-montage.webp"), new Uint8Array(await montage.arrayBuffer()));
  console.log(JSON.stringify({ slides: presentation.slides.items.length, output: OUTPUT }));
}

main()
  .then(() => {
    if (typeof process.reallyExit === "function") process.reallyExit(0);
    else process.exit(0);
  })
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
