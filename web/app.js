const PHOTO_EXTENSIONS = new Set(["jpg", "jpeg", "png", "tif", "tiff", "webp", "heic", "heif", "bmp"]);
const VIDEO_EXTENSIONS = new Set(["mp4", "mov", "avi", "mkv", "wmv", "webm", "m4v", "3gp", "mts", "m2ts"]);
const state = { source: null, destination: null, files: [], plan: [] };

const sourceName = document.querySelector("#source-name");
const destinationName = document.querySelector("#destination-name");
const preview = document.querySelector("#preview");
const progress = document.querySelector("#progress");
const interval = document.querySelector("#interval");
const previewButton = document.querySelector("#preview-button");
const organizeButton = document.querySelector("#organize-button");

for (let day = 1; day <= 31; day += 1) {
  interval.add(new Option(day, day));
}

function setProgress(message) {
  progress.textContent = message;
}

function selectedGrouping() {
  return document.querySelector('input[name="grouping"]:checked').value;
}

function settings() {
  return {
    grouping: selectedGrouping(),
    interval: Number(interval.value),
    includeCount: document.querySelector("#include-count").checked,
    includeDateLabels: document.querySelector("#include-date-labels").checked,
    includePhotos: document.querySelector("#include-photos").checked,
    includeVideos: document.querySelector("#include-videos").checked,
    includeOther: document.querySelector("#include-other").checked,
    routeEtc: document.querySelector("#route-etc").checked,
  };
}

function updateIntervalState() {
  const disabled = selectedGrouping() !== "day";
  interval.disabled = disabled;
  interval.parentElement.classList.toggle("disabled", disabled);
}

async function chooseDirectory(kind) {
  if (!("showDirectoryPicker" in window)) {
    throw new Error("이 브라우저는 폴더 선택 및 쓰기를 지원하지 않습니다. Chrome 또는 Edge를 사용하세요.");
  }
  const mode = kind === "destination" ? "readwrite" : "read";
  const handle = await window.showDirectoryPicker({ mode, startIn: "pictures" });
  state[kind] = handle;
  if (kind === "source") sourceName.textContent = handle.name;
  else destinationName.textContent = handle.name;
}

async function walkDirectory(directory, prefix = "") {
  const files = [];
  for await (const [name, handle] of directory.entries()) {
    if (handle.kind === "directory") {
      if (state.destination && await handle.isSameEntry(state.destination)) continue;
      files.push(...await walkDirectory(handle, `${prefix}${name}/`));
      continue;
    }
    const extension = name.split(".").pop().toLowerCase();
    files.push({ file: await handle.getFile(), name, relativePath: `${prefix}${name}`, type: PHOTO_EXTENSIONS.has(extension) ? "photo" : VIDEO_EXTENSIONS.has(extension) ? "video" : "other" });
  }
  return files;
}

async function captureDate(file) {
  try {
    const exif = await exifr.parse(file, ["DateTimeOriginal", "DateTimeDigitized", "ModifyDate"]);
    const date = exif?.DateTimeOriginal || exif?.DateTimeDigitized || exif?.ModifyDate;
    if (date instanceof Date && !Number.isNaN(date.getTime())) return date;
  } catch (_) {
    // Unsupported formats and photos without EXIF fall back to the file timestamp.
  }
  return new Date(file.lastModified);
}

function dateParts(date, includeDateLabels) {
  const year = String(date.getFullYear());
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  if (!includeDateLabels) return { year, month, day };
  return { year: `${year}년`, month: `${month}월`, day: `${day}일` };
}

function dateRange(day, size) {
  const start = Math.floor((day - 1) / size) * size + 1;
  return [start, Math.min(start + size - 1, 31)];
}

function targetParts(date, config) {
  const parts = dateParts(date, config.includeDateLabels);
  const folders = [parts.year];
  if (config.grouping !== "year") folders.push(parts.month);
  if (config.grouping === "day") {
    const [start, end] = dateRange(date.getDate(), config.interval);
    folders.push(start === end ? parts.day : `${start}-${end}${config.includeDateLabels ? "일" : ""}`);
  }
  return folders;
}

function displayFolder(parts, count, includeCount) {
  const display = [...parts];
  if (includeCount) display[display.length - 1] += ` (${count}장)`;
  return display.join("/");
}

async function buildPlan() {
  if (!state.source) throw new Error("원본 폴더를 선택하세요.");
  if (state.destination && await state.source.isSameEntry(state.destination)) {
    throw new Error("원본 폴더와 결과 폴더는 서로 다르게 선택하세요.");
  }
  const config = settings();
  setProgress("사진을 찾는 중...");
  const files = await walkDirectory(state.source);
  const selected = files.filter((item) => {
    const allowed = (item.type === "photo" && config.includePhotos) || (item.type === "video" && config.includeVideos) || (item.type === "other" && config.includeOther);
    return allowed || config.routeEtc;
  });
  state.files = files;
  const counts = new Map();
  const plan = [];

  for (let index = 0; index < selected.length; index += 1) {
    const item = selected[index];
    const date = await captureDate(item.file);
    const allowed = (item.type === "photo" && config.includePhotos) || (item.type === "video" && config.includeVideos) || (item.type === "other" && config.includeOther);
    const parts = allowed ? targetParts(date, config) : ["ETC"];
    const key = parts.join("/");
    counts.set(key, (counts.get(key) || 0) + 1);
    plan.push({ ...item, parts, key });
    setProgress(`진행 과정 (${String(index + 1).padStart(3, "0")} / ${String(selected.length).padStart(3, "0")}장)`);
  }
  state.plan = plan;
  return { counts, config };
}

async function previewResults() {
  try {
    previewButton.disabled = true;
    const { counts, config } = await buildPlan();
    const lines = [`총 ${state.plan.length}장의 사진을 찾았습니다.`];
    for (const [key, count] of [...counts].sort(([a], [b]) => a.localeCompare(b, "ko"))) {
      lines.push(`${String(count).padStart(4, " ")}장 → ${displayFolder(key.split("/"), count, config.includeCount)}`);
    }
    preview.textContent = lines.join("\n");
    setProgress(`진행 과정 (${String(state.plan.length).padStart(3, "0")} / ${String(state.plan.length).padStart(3, "0")}장)`);
  } catch (error) {
    preview.textContent = `오류: ${error.message}`;
    setProgress("오류");
  } finally {
    previewButton.disabled = false;
  }
}

async function getTargetDirectory(parts) {
  let directory = state.destination;
  for (const part of parts) directory = await directory.getDirectoryHandle(part, { create: true });
  return directory;
}

async function uniqueFileHandle(directory, filename) {
  const dot = filename.lastIndexOf(".");
  const stem = dot > 0 ? filename.slice(0, dot) : filename;
  const extension = dot > 0 ? filename.slice(dot) : "";
  for (let number = 1; ; number += 1) {
    const candidate = number === 1 ? filename : `${stem} (${number})${extension}`;
    try {
      await directory.getFileHandle(candidate);
    } catch (error) {
      if (error.name !== "NotFoundError") throw error;
      return directory.getFileHandle(candidate, { create: true });
    }
  }
}

async function organizePhotos() {
  try {
    if (!state.destination) throw new Error("결과 폴더를 선택하세요.");
    if (await state.source.isSameEntry(state.destination)) {
      throw new Error("원본 폴더와 결과 폴더는 서로 다르게 선택하세요.");
    }
    organizeButton.disabled = true;
    const { counts, config } = await buildPlan();
    for (let index = 0; index < state.plan.length; index += 1) {
      const item = state.plan[index];
      const parts = item.parts.map((part, partIndex) => (
        config.includeCount && partIndex === item.parts.length - 1
          ? `${part} (${counts.get(item.key)}장)`
          : part
      ));
      const targetDirectory = await getTargetDirectory(parts);
      const target = await uniqueFileHandle(targetDirectory, item.name);
      const writable = await target.createWritable();
      await writable.write(item.file);
      await writable.close();
      setProgress(`정리 중 (${String(index + 1).padStart(3, "0")} / ${String(state.plan.length).padStart(3, "0")}장)`);
    }
    preview.textContent += `\n\n정리가 완료되었습니다. 결과 폴더: ${state.destination.name}`;
    setProgress(`완료 (${state.plan.length} / ${state.plan.length}장)`);
  } catch (error) {
    preview.textContent += `\n\n오류: ${error.message}`;
    setProgress("오류");
  } finally {
    organizeButton.disabled = false;
  }
}

document.querySelector("#select-source").addEventListener("click", async () => {
  try { await chooseDirectory("source"); } catch (error) { alert(error.message); }
});
document.querySelector("#select-destination").addEventListener("click", async () => {
  try { await chooseDirectory("destination"); } catch (error) { alert(error.message); }
});
document.querySelectorAll('input[name="grouping"]').forEach((input) => input.addEventListener("change", updateIntervalState));
previewButton.addEventListener("click", previewResults);
organizeButton.addEventListener("click", organizePhotos);
updateIntervalState();
