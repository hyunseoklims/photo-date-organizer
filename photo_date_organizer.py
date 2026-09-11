import os
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    Image = None


PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".heif", ".bmp"}


def read_capture_date(path: Path):
    """Return EXIF capture date, falling back to file modified date."""
    if Image is not None:
        try:
            with Image.open(path) as image:
                exif = image.getexif()
                values = {TAGS.get(k, k): v for k, v in exif.items()}
                raw = values.get("DateTimeOriginal") or values.get("DateTimeDigitized") or values.get("DateTime")
                if raw:
                    return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S"), "EXIF"
        except Exception:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime), "파일 수정일"


def safe_name(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "-", value).strip() or "날짜 없음"


class PhotoOrganizer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("사진 날짜별 정리 도구")
        self.geometry("640x560")
        self.minsize(640, 560)
        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        self.grouping = tk.StringVar(value="day")
        self.day_interval = tk.StringVar(value="1")
        self.include_count = tk.BooleanVar(value=True)
        self.include_date_labels = tk.BooleanVar(value=True)
        self.action = tk.StringVar(value="copy")
        self.status = tk.StringVar()
        self.progress = tk.DoubleVar(value=0)
        self.withdraw()
        self._show_loading()
        self.after(50, self._finish_startup)

    def _show_loading(self):
        self.loading_window = tk.Toplevel(self)
        self.loading_window.overrideredirect(True)
        self.loading_window.configure(background="#ffffff")

        frame = tk.Frame(
            self.loading_window,
            background="#ffffff",
            borderwidth=1,
            relief="solid",
            padx=28,
            pady=22,
        )
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text="사진 날짜별 정리 도구",
            background="#ffffff",
            foreground="#111111",
            font=("Malgun Gothic", 12, "bold"),
        ).pack()
        tk.Label(
            frame,
            text="프로그램을 준비하고 있습니다...",
            background="#ffffff",
            foreground="#666666",
            font=("Malgun Gothic", 9),
        ).pack(pady=(8, 0))

        self.loading_window.update_idletasks()
        width, height = 300, 120
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.loading_window.geometry(f"{width}x{height}+{x}+{y}")
        self.loading_window.attributes("-topmost", True)

    def _finish_startup(self):
        self._build_ui()
        self.loading_window.destroy()
        self.deiconify()
        self.lift()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        main = ttk.Frame(self, padding=8)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="사진 날짜별 정리 도구", font=("맑은 고딕", 18, "bold")).pack(anchor="w")
        ttk.Label(main, text="하위 폴더를 포함해 촬영일을 읽고, 선택한 정리 기준별 폴더로 분류합니다.").pack(anchor="w", pady=(2, 10))

        self._folder_row(main, "원본 폴더", self.source, False)
        self._folder_row(main, "정리할 폴더", self.destination, True)

        options = ttk.LabelFrame(main, text="정리 설정", padding=10)
        options.pack(fill="x", **pad)
        ttk.Label(options, text="정리 기준").grid(row=0, column=0, sticky="w", pady=(2, 5))
        criteria_buttons = ttk.Frame(options)
        criteria_buttons.grid(row=0, column=1, sticky="w", padx=(3, 5))
        ttk.Radiobutton(criteria_buttons, text="연도별", variable=self.grouping, value="year", command=self.update_grouping_controls).pack(side="left", padx=(0, 2))
        ttk.Radiobutton(criteria_buttons, text="월별 (연도 포함)", variable=self.grouping, value="month", command=self.update_grouping_controls).pack(side="left", padx=2)
        ttk.Radiobutton(criteria_buttons, text="일별 (연도/월 포함)", variable=self.grouping, value="day", command=self.update_grouping_controls).pack(side="left", padx=(2, 0))
        interval_controls = ttk.Frame(options)
        interval_controls.grid(row=0, column=2, columnspan=3, sticky="w", padx=(2, 0))
        self.day_range_label = ttk.Label(interval_controls, text="날짜 간격")
        self.day_range_label.pack(side="left", padx=(0, 3))
        self.day_interval_box = ttk.Combobox(
            interval_controls,
            textvariable=self.day_interval,
            values=tuple(str(day) for day in range(1, 32)),
            state="readonly",
            width=4,
        )
        self.day_interval_box.pack(side="left")
        ttk.Label(interval_controls, text="일").pack(side="left", padx=(3, 0))
        ttk.Label(options, text="세부 설정").grid(row=1, column=0, rowspan=2, sticky="nw", pady=(6, 0))
        ttk.Checkbutton(
            options,
            text="폴더명 뒤에 사진 수 표시",
            variable=self.include_count,
        ).grid(row=1, column=1, sticky="w", padx=4, pady=(6, 0))
        ttk.Label(options, text="예: 05일 (12장)").grid(row=1, column=2, sticky="w", padx=4, pady=(6, 0))
        ttk.Checkbutton(
            options,
            text="년-월-일 입력",
            variable=self.include_date_labels,
        ).grid(row=2, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(options, text="예: 2024년 / 03월 / 05일").grid(row=2, column=2, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(options, text="처리 방식").grid(row=3, column=0, sticky="w", pady=(6, 2))
        ttk.Radiobutton(
            options,
            text="복사 (원본 보존)",
            variable=self.action,
            value="copy",
        ).grid(row=3, column=1, sticky="w", padx=4, pady=(6, 2))
        ttk.Radiobutton(
            options,
            text="이동 (원본에서 제거)",
            variable=self.action,
            value="move",
        ).grid(row=3, column=2, sticky="w", padx=4, pady=(6, 2))
        self.update_grouping_controls()

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", **pad)
        ttk.Button(buttons, text="결과 미리보기", command=self.preview).pack(side="left")
        ttk.Button(buttons, text="정리 시작", command=self.start_organize).pack(side="right")
        self.preview_progress = tk.StringVar()
        ttk.Label(buttons, textvariable=self.preview_progress).pack(side="right", padx=(0, 8))
        buttons.winfo_children()[-2].pack_forget()

        log_frame = tk.Frame(main, borderwidth=0, highlightthickness=1, highlightbackground="#d9d9d9")
        log_frame.pack(fill="both", expand=True, padx=8, pady=4)
        self.log = tk.Text(
            log_frame,
            height=4,
            state="disabled",
            wrap="none",
            borderwidth=0,
            highlightthickness=0,
            spacing1=3,
            spacing3=3,
        )
        vertical_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        horizontal_scrollbar = ttk.Scrollbar(log_frame, orient="horizontal", command=self.log.xview)
        self.log.configure(yscrollcommand=vertical_scrollbar.set, xscrollcommand=horizontal_scrollbar.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        tk.Button(
            main,
            text="▶  정리 시작",
            command=self.start_organize,
            background="#111111",
            foreground="white",
            activebackground="#333333",
            activeforeground="white",
            borderwidth=0,
            cursor="hand2",
            font=("Malgun Gothic", 11, "bold"),
            pady=10,
        ).pack(fill="x", padx=8, pady=(0, 5))

    def _folder_row(self, parent, label, variable, is_destination):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=8, pady=4)
        ttk.Label(row, text=label, width=12).pack(side="left")
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="찾아보기", command=lambda: self.choose_folder(variable, is_destination)).pack(side="right")

    def choose_folder(self, variable, is_destination):
        folder = filedialog.askdirectory(title="폴더 선택")
        if folder:
            variable.set(folder)
            if not is_destination and not self.destination.get():
                self.destination.set(str(Path(folder) / "날짜별 정리"))

    def find_photos(self):
        source = Path(self.source.get())
        if not source.is_dir():
            raise ValueError("원본 폴더를 선택하세요.")
        destination = Path(self.destination.get()) if self.destination.get() else source / "날짜별 정리"
        photos = []
        for path in source.rglob("*"):
            if path.is_file() and path.suffix.lower() in PHOTO_EXTENSIONS and destination not in path.parents:
                photos.append(path)
        return source, destination, photos

    def update_grouping_controls(self):
        is_day_grouping = self.grouping.get() == "day"
        self.day_range_label.configure(state="normal" if is_day_grouping else "disabled")
        combo_state = "readonly" if is_day_grouping else "disabled"
        self.day_interval_box.configure(state=combo_state)

    def parse_day_interval(self):
        try:
            interval = int(self.day_interval.get())
        except ValueError as exc:
            raise ValueError("날짜 간격을 선택하세요.") from exc
        if not 1 <= interval <= 31:
            raise ValueError("날짜 간격은 1~31일 사이여야 합니다.")
        return interval

    def get_day_range(self, day, interval):
        start = ((day - 1) // interval) * interval + 1
        return start, min(start + interval - 1, 31)

    def format_date_parts(self, date):
        if not self.include_date_labels.get():
            return str(date.year), f"{date.month:02d}", f"{date.day:02d}"
        return f"{date.year}년", f"{date.month:02d}월", f"{date.day:02d}일"

    def get_target_folder(self, date, destination, folder_counts=None, day_ranges=None):
        year_label, month_label, day_label = self.format_date_parts(date)
        base_parts = [year_label]
        if self.grouping.get() != "year":
            base_parts.append(month_label)
        if self.grouping.get() == "day":
            start, end = self.get_day_range(date.day, day_ranges or self.parse_day_interval())
            if start == end:
                base_parts.append(day_label)
            elif self.include_date_labels.get():
                base_parts.append(f"{start}-{end}일")
            else:
                base_parts.append(f"{start}-{end}")

        if self.include_count.get() and folder_counts is not None:
            base_folder = destination.joinpath(*base_parts)
            count = folder_counts.get(str(base_folder), 0)
            base_parts[-1] = f"{base_parts[-1]} ({count}장)"
        return destination.joinpath(*(safe_name(part) for part in base_parts))

    def get_folder_counts(self, photos, destination, day_ranges, progress_callback=None):
        counts = {}
        total = len(photos)
        for index, photo in enumerate(photos, 1):
            date, _ = read_capture_date(photo)
            folder = self.get_target_folder(date, destination, day_ranges=day_ranges)
            counts[str(folder)] = counts.get(str(folder), 0) + 1
            if progress_callback:
                progress_callback(index, total)
        return counts

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def get_display_folder(self, folder, count):
        if not self.include_count.get():
            return folder
        return str(Path(folder).parent / f"{Path(folder).name} ({count}장)")

    def preview(self):
        try:
            _, destination, photos = self.find_photos()
            day_ranges = self.parse_day_interval() if self.grouping.get() == "day" else None
            total = len(photos)
            self.preview_progress.set(f"진행 과정 (000 / {total:03d}장)")

            def update_preview_progress(current, total_count):
                self.preview_progress.set(f"진행 과정 ({current:03d} / {total_count:03d}장)")
                self.update_idletasks()

            folder_counts = self.get_folder_counts(photos, destination, day_ranges, update_preview_progress)
            lines = [f"총 {len(photos)}장의 사진을 찾았습니다."]
            for folder, count in sorted(folder_counts.items()):
                lines.append(f"{count:>4}장 → {self.get_display_folder(folder, count)}")
            self.clear_log()
            for line in lines:
                self.write_log(line)
            self.status.set(f"미리보기 완료: {len(photos)}장")
        except Exception as exc:
            messagebox.showerror("확인 필요", str(exc))

    def start_organize(self):
        try:
            source, destination, photos = self.find_photos()
            day_ranges = self.parse_day_interval() if self.grouping.get() == "day" else None
            if not photos:
                messagebox.showinfo("사진 없음", "선택한 폴더와 하위 폴더에서 사진을 찾지 못했습니다.")
                return
            if self.action.get() == "move" and not messagebox.askyesno("이동 확인", "이동하면 원본 위치에서 사진이 제거됩니다. 계속할까요?"):
                return
            folder_counts = self.get_folder_counts(photos, destination, day_ranges)
            self.progress.set(0)
            threading.Thread(target=self.organize, args=(source, destination, photos, folder_counts, day_ranges), daemon=True).start()
        except Exception as exc:
            messagebox.showerror("확인 필요", str(exc))

    def organize(self, source, destination, photos, folder_counts, day_ranges):
        for index, photo in enumerate(photos, 1):
            try:
                date, source_type = read_capture_date(photo)
                target_dir = self.get_target_folder(date, destination, folder_counts, day_ranges)
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / photo.name
                if target.exists():
                    stem, suffix = photo.stem, photo.suffix
                    n = 2
                    while target.exists():
                        target = target_dir / f"{stem} ({n}){suffix}"
                        n += 1
                if self.action.get() == "move":
                    shutil.move(str(photo), str(target))
                else:
                    shutil.copy2(str(photo), str(target))
            except Exception as exc:
                self.after(0, self.write_log, f"실패: {photo.name} ({exc})")
            self.after(0, self.progress.set, index / len(photos) * 100)
        self.after(0, self.status.set, f"완료: {len(photos)}장 정리됨")
        self.after(0, self.write_log, f"정리가 완료되었습니다. 결과 폴더: {destination}")
        self.after(0, lambda: messagebox.showinfo("완료", f"{len(photos)}장의 사진 정리가 완료되었습니다."))

    def write_log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")



if __name__ == "__main__":
    app = PhotoOrganizer()
    app.mainloop()
