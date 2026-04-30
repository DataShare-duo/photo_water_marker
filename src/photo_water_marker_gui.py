import tkinter as tk
from tkinter import filedialog, colorchooser
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os


class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("水印工具@DataShare")
        root.geometry("1000x700")
        root.minsize(900, 600)
        root.configure(bg="#f0f0f0")

        # ---------- 状态变量 ----------
        self.original_raw = None
        self.original_image = None
        self.watermarked_image = None
        self.current_filepath = None

        self._original_pil = None
        self._watermarked_pil = None
        self._left_photo = None
        self._right_photo = None

        # ---------- 顶部工具栏 ----------
        top_frame = tk.Frame(root, bg="#e0e0e0", height=40)
        top_frame.pack(fill=tk.X, side=tk.TOP)

        tk.Button(top_frame, text="打开图片", command=self.open_image,
                  width=10).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(top_frame, text="保存结果", command=self.save_result,
                  width=10).pack(side=tk.LEFT, padx=5, pady=5)

        # ---------- 中间预览区 ----------
        preview_frame = tk.Frame(root, bg="#d0d0d0")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(1, weight=1)

        left_frame = tk.LabelFrame(preview_frame, text="原始图片", bg="white")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left_frame.propagate(False)
        left_frame.config(width=400, height=350)
        self.left_canvas = tk.Canvas(left_frame, bg="white", highlightthickness=0)
        self.left_canvas.pack(fill=tk.BOTH, expand=True)

        right_frame = tk.LabelFrame(preview_frame, text="水印效果", bg="white")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_frame.propagate(False)
        right_frame.config(width=400, height=350)
        self.right_canvas = tk.Canvas(right_frame, bg="white", highlightthickness=0)
        self.right_canvas.pack(fill=tk.BOTH, expand=True)

        self.left_canvas.bind("<Configure>", lambda e: self._redraw_left())
        self.right_canvas.bind("<Configure>", lambda e: self._redraw_right())

        # ---------- 底部控制面板 ----------
        control_frame = tk.LabelFrame(root, text="水印设置", bg="#f0f0f0", height=200)
        control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        control_frame.pack_propagate(False)

        # --- 第1行：原图旋转 ---
        row1 = tk.Frame(control_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, pady=5, padx=10)
        tk.Label(row1, text="原图旋转：", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0,5))
        self.rotate_angle_var = tk.IntVar(value=0)
        for angle in (0, 90, 180, 270):
            rb = tk.Radiobutton(row1, text=f"{angle}°", variable=self.rotate_angle_var,
                                value=angle, bg="#f0f0f0", indicatoron=1,
                                command=self.rotate_original)
            rb.pack(side=tk.LEFT, padx=3)

        # --- 第2行：水印文字 + 颜色 ---
        row2 = tk.Frame(control_frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, pady=5, padx=10)
        tk.Label(row2, text="水印文字：", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0,5))
        self.text_var = tk.StringVar(value="DataShare")
        tk.Entry(row2, textvariable=self.text_var, width=25).pack(side=tk.LEFT, padx=(0,15))
        self.text_var.trace_add("write", lambda *args: self.update_watermark())
        tk.Label(row2, text="颜色：", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0,5))
        self.color_var = tk.StringVar(value="#FF0000")
        self.color_btn = tk.Button(row2, text="　", bg="#FF0000",
                                   command=self.pick_color, width=3)
        self.color_btn.pack(side=tk.LEFT)

        # --- 第3行：透明度 + 水印旋转 + 字体大小（网格对齐） ---
        row3 = tk.Frame(control_frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, pady=5, padx=10)
        row3.columnconfigure(0, weight=1, uniform="col")
        row3.columnconfigure(1, weight=1, uniform="col")
        row3.columnconfigure(2, weight=1, uniform="col")

        tk.Label(row3, text="透明度：", bg="#f0f0f0").grid(row=0, column=0, sticky="w", padx=(0,5))
        tk.Label(row3, text="水印旋转：", bg="#f0f0f0").grid(row=0, column=1, sticky="w", padx=(0,5))
        tk.Label(row3, text="字体大小：", bg="#f0f0f0").grid(row=0, column=2, sticky="w", padx=(0,5))

        self.opacity_var = tk.IntVar(value=128)
        self.scale_opacity = tk.Scale(row3, from_=0, to=255, orient=tk.HORIZONTAL,
                                      variable=self.opacity_var,
                                      command=lambda e: self.update_watermark())
        self.scale_opacity.grid(row=1, column=0, sticky="ew", padx=(0,10))

        self.angle_var = tk.IntVar(value=30)
        self.scale_angle = tk.Scale(row3, from_=0, to=360, orient=tk.HORIZONTAL,
                                    variable=self.angle_var,
                                    command=lambda e: self.update_watermark())
        self.scale_angle.grid(row=1, column=1, sticky="ew", padx=(0,10))

        self.font_size_var = tk.IntVar(value=36)
        self.spin_font = tk.Spinbox(row3, from_=8, to=500, increment=1,
                                    textvariable=self.font_size_var,
                                    command=self.update_watermark, width=6)
        self.spin_font.grid(row=1, column=2, sticky="w")
        # 修复：绑定回车键，使键盘输入后按回车也会更新水印
        self.spin_font.bind("<Return>", lambda event: self.update_watermark())

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(root, textvariable=self.status_var, bg="#f0f0f0",
                 anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X, padx=5)

    # -------------------- 原图旋转 --------------------
    def rotate_original(self):
        if self.original_raw is None:
            return
        angle = self.rotate_angle_var.get()
        if angle == 0:
            self.original_image = self.original_raw.copy()
        else:
            self.original_image = self.original_raw.rotate(angle, expand=True, resample=Image.BICUBIC)
        self.update_watermark()
        self.show_preview(self.original_image, self.left_canvas)

    # -------------------- 水印处理 --------------------
    def apply_watermark(self):
        if self.original_image is None:
            return None
        img = self.original_image.copy()
        width, height = img.size
        watermark_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark_layer)

        hex_color = self.color_var.get()
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        alpha = self.opacity_var.get()

        try:
            font = ImageFont.truetype("arial.ttf", self.font_size_var.get())
        except IOError:
            font = ImageFont.load_default()
        text = self.text_var.get()
        angle = self.angle_var.get()
        if not text:
            return img

        txt_size = draw.textbbox((0, 0), text, font=font)
        txt_w = txt_size[2] - txt_size[0]
        txt_h = txt_size[3] - txt_size[1]
        margin = 20
        block = Image.new("RGBA", (txt_w + margin*2, txt_h + margin*2), (0,0,0,0))
        d = ImageDraw.Draw(block)
        d.text((margin, margin), text, font=font, fill=(r, g, b, alpha))
        rotated_block = block.rotate(angle, expand=True, resample=Image.BICUBIC)

        rw, rh = rotated_block.size
        for y in range(-rh, height + rh, rh):
            for x in range(-rw, width + rw, rw):
                watermark_layer.paste(rotated_block, (x, y), rotated_block)

        result = Image.alpha_composite(img, watermark_layer)
        return result

    def update_watermark(self, *args):
        if self.original_image is None:
            return
        self.watermarked_image = self.apply_watermark()
        self.show_preview(self.watermarked_image, self.right_canvas)
        self.status_var.set("水印已更新")

    # -------------------- 预览显示 --------------------
    def _draw_on_canvas(self, pil_img, canvas):
        canvas.delete("all")
        if pil_img is None:
            return
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw < 2 or ch < 2:
            return
        ratio = min(cw / pil_img.width, ch / pil_img.height)
        new_w = int(pil_img.width * ratio)
        new_h = int(pil_img.height * ratio)
        resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(resized)
        x = (cw - new_w) // 2
        y = (ch - new_h) // 2
        canvas.create_image(x, y, anchor=tk.NW, image=tk_img)
        if canvas == self.left_canvas:
            self._left_photo = tk_img
        else:
            self._right_photo = tk_img

    def _redraw_left(self):
        self._draw_on_canvas(self._original_pil, self.left_canvas)

    def _redraw_right(self):
        self._draw_on_canvas(self._watermarked_pil, self.right_canvas)

    def show_preview(self, pil_img, canvas):
        if canvas == self.left_canvas:
            self._original_pil = pil_img
        else:
            self._watermarked_pil = pil_img
        self._draw_on_canvas(pil_img, canvas)

    # -------------------- 按钮功能 --------------------
    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if not path:
            return
        self.current_filepath = path
        self.original_raw = Image.open(path).convert("RGBA")
        self.rotate_angle_var.set(0)
        self.original_image = self.original_raw.copy()
        self.watermarked_image = self.apply_watermark()
        self.show_preview(self.original_image, self.left_canvas)
        self.show_preview(self.watermarked_image, self.right_canvas)
        self.status_var.set(f"已打开: {os.path.basename(path)}")

    def save_result(self):
        if self.watermarked_image is None:
            self.status_var.set("没有可保存的内容")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG 图片", "*.png"),
                       ("JPEG 图片", "*.jpg"), ("所有文件", "*.*")]
        )
        if not path:
            return
        if path.lower().endswith((".jpg", ".jpeg")):
            self.watermarked_image.convert("RGB").save(path, quality=95)
        else:
            self.watermarked_image.save(path)
        self.status_var.set(f"已保存: {os.path.basename(path)}")

    def pick_color(self):
        color_code = colorchooser.askcolor(title="选择水印颜色")
        if color_code and color_code[1]:
            self.color_var.set(color_code[1])
            self.color_btn.configure(bg=color_code[1])
            self.update_watermark()


if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop()
    