import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, simpledialog, Scale
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk, ImageDraw, ImageEnhance
import pillow_heif

# HEICサポートの初期化
pillow_heif.register_heif_opener()


class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PythonPhotoEditor")
        self.unsaved_changes = False
        self.history = []
        self.history_index = -1
        self.fill_color = "white"  # デフォルトの塗りつぶし色
        self.scale_ratio = 1.0  # 初期値を設定
        self.image_loaded = False  # 画像が読み込まれたかどうかのフラグ
        self.saturation_value = 1.0  # 彩度の初期値（1.0で元の画像の彩度）
        self.canvas_image_id = None  # キャンバス上の画像ID

        # トリミング関連の変数
        self.trimming_mode = False
        self.trim_start = None
        self.trim_end = None
        self.trim_rectangle = None

        # ドラッグアンドドロップの設定
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_drop)

        # メニューバーの作成
        menubar = tk.Menu(root)

        # ファイルメニュー
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="開く", command=self.open_image)
        filemenu.add_command(
            label="保存", command=self.save_image, accelerator="Ctrl+S"
        )
        filemenu.add_separator()
        filemenu.add_command(label="終了", command=self.on_closing)
        menubar.add_cascade(label="ファイル", menu=filemenu)

        # 編集メニュー
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="元に戻す", command=self.undo, accelerator="Ctrl+Z")
        editmenu.add_command(
            label="やり直す", command=self.redo, accelerator="Ctrl+Shift+Z"
        )
        menubar.add_cascade(label="編集", menu=editmenu)

        # ヘルプメニュー
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="バージョン情報", command=self.show_copyright)
        menubar.add_cascade(label="ヘルプ", menu=helpmenu)

        root.config(menu=menubar)

        # ショートカットキーの設定
        root.bind_all("<Control-s>", lambda event: self.save_image())
        root.bind_all("<Control-z>", lambda event: self.undo())
        root.bind_all("<Control-Shift-Z>", lambda event: self.redo())

        # ツールバーの作成
        toolbar = tk.Frame(root, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # カラーピッカーボタン
        self.color_button = tk.Button(
            toolbar, text="色を選択", command=self.choose_color, bg=self.fill_color
        )
        self.color_button.pack(side=tk.LEFT, padx=2, pady=2)

        # 現在の色表示
        self.color_label = tk.Label(
            toolbar, text=f"現在の色: {self.fill_color}", bg="white"
        )
        self.color_label.pack(side=tk.LEFT, padx=2, pady=2)

        # トリミングボタン
        self.trim_button = tk.Button(
            toolbar, text="トリミング", command=self.toggle_trimming_mode
        )
        self.trim_button.pack(side=tk.LEFT, padx=2, pady=2)

        # 現在のモード表示ラベル
        self.mode_label = tk.Label(toolbar, text="現在のモード: 通常", bg="white")
        self.mode_label.pack(side=tk.LEFT, padx=10, pady=2)

        # 鮮やかさ（彩度）スライダーの追加
        self.saturation_frame = tk.Frame(toolbar)
        self.saturation_frame.pack(side=tk.RIGHT, padx=10)

        self.saturation_label = tk.Label(self.saturation_frame, text="鮮やかさ:")
        self.saturation_label.pack(side=tk.LEFT)

        self.saturation_slider = Scale(
            self.saturation_frame,
            from_=0.0,
            to=5.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            length=150,
            command=self.update_saturation,
        )
        self.saturation_slider.set(1.0)  # デフォルト値を設定
        self.saturation_slider.pack(side=tk.LEFT)

        # キャンバスフレームの作成（スクロールバー用）
        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        # キャンバスの作成
        self.canvas = tk.Canvas(self.canvas_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 画像関連の変数
        self.image = None
        self.tk_image = None
        self.draw = None
        self.original_image = None
        self.display_image = None

        # マウスイベントのバインド
        self.points = []  # 元画像における座標
        self.display_points = []  # 表示用の座標
        self.dots = []
        self.canvas.bind("<Button-1>", self.add_point)
        self.canvas.bind("<Button-3>", self.fill_area)

        # ウィンドウリサイズイベントのバインド
        self.root.bind("<Configure>", self.on_window_resize)

        # 最後のウィンドウサイズを記録
        self.last_window_width = self.root.winfo_width()
        self.last_window_height = self.root.winfo_height()

    def toggle_trimming_mode(self):
        """トリミングモードのオン/オフを切り替える"""
        self.trimming_mode = not self.trimming_mode

        # モードに応じてラベルを更新
        if self.trimming_mode:
            self.mode_label.config(text="現在のモード: トリミング")
            messagebox.showinfo(
                "トリミングモード",
                "左上から右下へドラッグして領域を選択してください。\nトリミングが完了したらトリミングボタンをもう一度押してください。",
            )

            # トリミングモード中は通常の点追加機能を無効化
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<Button-3>")

            # トリミング用のマウスイベントをバインド
            self.canvas.bind("<ButtonPress-1>", self.start_trim_selection)
            self.canvas.bind("<B1-Motion>", self.update_trim_selection)
            self.canvas.bind("<ButtonRelease-1>", self.end_trim_selection)
        else:
            self.mode_label.config(text="現在のモード: 通常")

            # トリミング用のバインドを解除
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")

            # 通常の点追加機能を復活
            self.canvas.bind("<Button-1>", self.add_point)
            self.canvas.bind("<Button-3>", self.fill_area)

            # 選択範囲があれば実際にトリミングを実行
            if self.trim_start and self.trim_end:
                self.execute_trimming()

            # トリミング選択範囲をリセット
            self.reset_trim_selection()

    def start_trim_selection(self, event):
        """トリミング選択の開始"""
        # 画像が読み込まれていない場合は何もしない
        if not self.image_loaded or not self.image:
            messagebox.showinfo("注意", "先に画像を開いてください。")
            return

        # 既存の選択範囲を削除
        self.reset_trim_selection()

        # 表示座標を元画像座標に変換
        orig_x, orig_y = self.to_original_coords(event.x, event.y)

        # 画像外のクリックを無視
        if orig_x is None or orig_y is None:
            return

        # 開始位置を保存
        self.trim_start = (orig_x, orig_y)
        self.trim_end = (orig_x, orig_y)  # 初期状態では同じ位置

        # キャンバス上に選択範囲の矩形を描画
        canvas_x, canvas_y = event.x, event.y
        self.trim_rectangle = self.canvas.create_rectangle(
            canvas_x, canvas_y, canvas_x, canvas_y, outline="red", width=2, dash=(4, 4)
        )

    def update_trim_selection(self, event):
        """トリミング選択範囲の更新"""
        if not self.trim_start or not self.trim_rectangle:
            return

        # 表示座標を元画像座標に変換
        orig_x, orig_y = self.to_original_coords(event.x, event.y)

        # 画像外のドラッグを無視
        if orig_x is None or orig_y is None:
            return

        # 終了位置を更新
        self.trim_end = (orig_x, orig_y)

        # キャンバス上の表示座標を計算
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        x_offset = (canvas_width - self.display_image.width) // 2
        y_offset = (canvas_height - self.display_image.height) // 2

        start_x = int(self.trim_start[0] * self.scale_ratio) + x_offset
        start_y = int(self.trim_start[1] * self.scale_ratio) + y_offset
        end_x = int(self.trim_end[0] * self.scale_ratio) + x_offset
        end_y = int(self.trim_end[1] * self.scale_ratio) + y_offset

        # 矩形を更新
        self.canvas.coords(self.trim_rectangle, start_x, start_y, end_x, end_y)

    def end_trim_selection(self, event):
        """トリミング選択の終了"""
        # 表示座標を元画像座標に変換
        orig_x, orig_y = self.to_original_coords(event.x, event.y)

        # 画像外のリリースを無視
        if orig_x is None or orig_y is None:
            return

        # 終了位置を保存
        self.trim_end = (orig_x, orig_y)

        # 選択範囲が小さすぎる場合は無視
        if (
            abs(self.trim_end[0] - self.trim_start[0]) < 10
            or abs(self.trim_end[1] - self.trim_start[1]) < 10
        ):
            messagebox.showinfo(
                "注意",
                "トリミング範囲が小さすぎます。もう少し大きな範囲を選択してください。",
            )
            self.reset_trim_selection()
            return

    def reset_trim_selection(self):
        """トリミング選択をリセット"""
        if self.trim_rectangle:
            self.canvas.delete(self.trim_rectangle)
            self.trim_rectangle = None
        self.trim_start = None
        self.trim_end = None

    def execute_trimming(self):
        """実際のトリミングを実行"""
        if not self.trim_start or not self.trim_end:
            return

        # 座標を左上、右下の順に整理
        left = min(self.trim_start[0], self.trim_end[0])
        top = min(self.trim_start[1], self.trim_end[1])
        right = max(self.trim_start[0], self.trim_end[0])
        bottom = max(self.trim_start[1], self.trim_end[1])

        # 現在の画像の状態を履歴に保存
        self.history = self.history[: self.history_index + 1]
        self.history.append(self.image.copy())
        self.history_index += 1

        # トリミング前の画像のサイズ
        original_width, original_height = self.image.size

        try:
            # 画像をトリミング
            trimmed_image = self.image.crop((left, top, right, bottom))

            # トリミング後の画像を現在の画像にセット
            self.image = trimmed_image
            self.draw = ImageDraw.Draw(self.image)

            # トリミング後の状態も履歴に保存
            self.history.append(self.image.copy())
            self.history_index += 1

            # ポイントの座標を調整
            if self.points:
                adjusted_points = []
                for point_x, point_y in self.points:
                    # トリミング範囲内かチェック
                    if left <= point_x <= right and top <= point_y <= bottom:
                        # 新しい座標系に変換
                        new_x = point_x - left
                        new_y = point_y - top
                        adjusted_points.append((new_x, new_y))

                # 調整後のポイントを設定
                self.points = adjusted_points

            # 表示を更新
            self.update_display_image()
            self.unsaved_changes = True

            messagebox.showinfo(
                "トリミング完了",
                f"画像を {right-left}x{bottom-top} のサイズにトリミングしました。",
            )

        except Exception as e:
            messagebox.showerror(
                "トリミングエラー", f"トリミング処理中にエラーが発生しました:\n{str(e)}"
            )

    def handle_drop(self, event):
        # ドラッグアンドドロップで渡されたファイルパスを処理
        file_path = event.data.strip("{}")  # Windows用の{}を除去
        self.load_image(file_path)

    def open_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("All supported formats", "*.jpg *.jpeg *.png *.heic"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("HEIC files", "*.heic"),
                ("All files", "*.*"),
            ]
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path):
        try:
            # 共通の画像読み込み処理
            self.original_image = Image.open(file_path)
            self.image = self.original_image.copy()

            # 画像のロード完了後に表示を更新
            self.image_loaded = True

            # 鮮やかさスライダーを1.0にリセット
            self.saturation_slider.set(1.0)
            self.saturation_value = 1.0

            # 履歴を初期化
            self.history = [self.image.copy()]
            self.history_index = 0

            # 点とラインをクリア
            for dot in self.dots:
                self.canvas.delete(dot)
            self.points = []
            self.display_points = []
            self.dots = []

            # DrawオブジェクトをImageに関連付け
            self.draw = ImageDraw.Draw(self.image)

            # 画像表示を更新（ウィンドウサイズに合わせて）
            self.update_display_image()

        except Exception as e:
            print(f"画像の読み込みに失敗しました: {e}")
            messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {e}")

    def update_display_image(self):
        """ウィンドウサイズに基づいて表示画像を更新"""
        if not self.image_loaded or self.image is None:
            return

        # キャンバスの現在のサイズを取得
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # キャンバスがまだ正しく描画されていない場合は遅延実行
        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, self.update_display_image)
            return

        # 画像がキャンバスに収まるようにスケーリング
        image_width, image_height = self.image.size

        # 縮小率を計算
        width_ratio = canvas_width / image_width
        height_ratio = canvas_height / image_height
        self.scale_ratio = min(width_ratio, height_ratio)

        if self.scale_ratio >= 1:
            # 画像が小さい場合は拡大しない
            self.scale_ratio = 1.0
            self.display_image = self.image
        else:
            # 画像が大きい場合は縮小
            display_size = (
                int(image_width * self.scale_ratio),
                int(image_height * self.scale_ratio),
            )
            self.display_image = self.image.resize(
                display_size, Image.Resampling.LANCZOS
            )

        # 表示画像をキャンバスに配置
        self.tk_image = ImageTk.PhotoImage(self.display_image)

        # 既存の画像を削除
        if self.canvas_image_id:
            self.canvas.delete(self.canvas_image_id)

        # 新しい画像を中央に配置
        x_pos = (canvas_width - self.display_image.width) // 2
        y_pos = (canvas_height - self.display_image.height) // 2
        self.canvas_image_id = self.canvas.create_image(
            x_pos, y_pos, anchor=tk.NW, image=self.tk_image
        )

        # 表示されている点とラインを更新
        self.update_display_points()

    def update_display_points(self):
        """表示ポイントとラインを更新"""
        # すべての点とラインを削除
        for dot in self.dots:
            self.canvas.delete(dot)
        self.dots = []

        # キャンバスサイズを取得
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # 画像の位置を計算
        x_offset = (canvas_width - self.display_image.width) // 2
        y_offset = (canvas_height - self.display_image.height) // 2

        # 表示座標リストをクリア
        self.display_points = []

        # 各ポイントを再描画
        for i, (orig_x, orig_y) in enumerate(self.points):
            # 元画像座標を表示座標に変換
            display_x = int(orig_x * self.scale_ratio) + x_offset
            display_y = int(orig_y * self.scale_ratio) + y_offset
            self.display_points.append((display_x, display_y))

            # 点を描画
            dot = self.canvas.create_oval(
                display_x - 3,
                display_y - 3,
                display_x + 3,
                display_y + 3,
                fill="blue",
                outline="blue",
            )
            self.dots.append(dot)

            # 2点以上あればラインを描画
            if i > 0:
                prev_display_x, prev_display_y = self.display_points[i - 1]
                line = self.canvas.create_line(
                    prev_display_x,
                    prev_display_y,
                    display_x,
                    display_y,
                    fill="blue",
                    width=2,
                )
                self.dots.append(line)  # 線もdotsリストに追加して管理

    def on_window_resize(self, event):
        """ウィンドウサイズ変更時のハンドラ"""
        # イベントの送信元がルートウィンドウか確認
        if event.widget == self.root:
            # サイズが実際に変わったか確認
            if (
                self.last_window_width != event.width
                or self.last_window_height != event.height
            ):

                self.last_window_width = event.width
                self.last_window_height = event.height

                # リサイズ後に少し遅延させて表示を更新
                # (tkinterのレイアウト更新が完了するのを待つ)
                self.root.after(100, self.update_display_image)

    def update_saturation(self, value):
        # 画像が読み込まれていない場合は何もしない
        if not self.image_loaded or not self.original_image:
            return

        # 値を浮動小数点に変換
        self.saturation_value = float(value)

        # 現在の履歴状態を基にして彩度を調整
        current_image = self.history[self.history_index].copy()

        # 彩度エンハンサーを作成して適用
        enhancer = ImageEnhance.Color(current_image)
        enhanced_image = enhancer.enhance(self.saturation_value)

        # 表示用の画像を更新
        self.image = enhanced_image
        self.draw = ImageDraw.Draw(self.image)  # Drawオブジェクトを再作成

        # 表示を更新
        self.update_display_image()

        # 変更があったことをマーク
        self.unsaved_changes = True

    def to_original_coords(self, x, y):
        """表示座標を元画像の座標に変換"""
        # キャンバスサイズを取得
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # 画像の位置を計算
        x_offset = (canvas_width - self.display_image.width) // 2
        y_offset = (canvas_height - self.display_image.height) // 2

        # オフセットを適用して、画像内の相対位置を計算
        rel_x = x - x_offset
        rel_y = y - y_offset

        # 画像外のクリックを処理
        if (
            rel_x < 0
            or rel_x >= self.display_image.width
            or rel_y < 0
            or rel_y >= self.display_image.height
        ):
            return None, None

        # スケール比を使って元画像の座標に変換
        orig_x = int(rel_x / self.scale_ratio)
        orig_y = int(rel_y / self.scale_ratio)

        return orig_x, orig_y

    def add_point(self, event):
        # 画像が読み込まれていない場合は何もしない
        if not self.image_loaded or not self.image:
            messagebox.showinfo("注意", "先に画像を開いてください。")
            return

        # 表示座標を元画像座標に変換
        orig_x, orig_y = self.to_original_coords(event.x, event.y)

        # 画像外のクリックを無視
        if orig_x is None or orig_y is None:
            return

        # 元画像上のポイントを追加
        self.points.append((orig_x, orig_y))

        # 表示用のポイントとラインを更新
        self.update_display_points()

    def choose_color(self):
        """カラーピッカーで色を選択"""
        color = colorchooser.askcolor(title="塗りつぶし色を選択")[1]
        if color:
            self.fill_color = color
            self.color_button.config(bg=color)
            self.color_label.config(text=f"現在の色: {color}")

    def fill_area(self, event):
        # 画像が読み込まれていない場合は何もしない
        if not self.image_loaded or not self.image:
            messagebox.showinfo("注意", "先に画像を開いてください。")
            return

        # 表示座標を元画像座標に変換
        orig_x, orig_y = self.to_original_coords(event.x, event.y)

        # 画像外のクリックを無視
        if orig_x is None or orig_y is None:
            return

        if len(self.points) > 2 and self.draw:
            # 塗りつぶし前の状態を履歴に保存
            self.history = self.history[: self.history_index + 1]
            self.history.append(self.image.copy())
            self.history_index += 1

            # 多角形を塗りつぶす
            self.draw.polygon(self.points, fill=self.fill_color)
            self.unsaved_changes = True

            # 塗りつぶし後の状態も履歴に保存
            self.history.append(self.image.copy())
            self.history_index += 1

            # 編集結果を表示用に更新
            self.update_display_image()

            # ポイントと線をクリア
            for dot in self.dots:
                self.canvas.delete(dot)
            self.points = []
            self.display_points = []
            self.dots = []

    def undo(self):
        if not self.image_loaded:
            return

        if self.history_index > 0:
            self.history_index -= 1
            self.image = self.history[self.history_index].copy()

            # 鮮やかさを適用
            if self.saturation_value != 1.0:
                enhancer = ImageEnhance.Color(self.image)
                self.image = enhancer.enhance(self.saturation_value)

            self.draw = ImageDraw.Draw(self.image)  # Drawオブジェクトを再作成
            self.update_display_image()
            self.unsaved_changes = True

    def redo(self):
        if not self.image_loaded:
            return

        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.image = self.history[self.history_index].copy()

            # 鮮やかさを適用
            if self.saturation_value != 1.0:
                enhancer = ImageEnhance.Color(self.image)
                self.image = enhancer.enhance(self.saturation_value)

            self.draw = ImageDraw.Draw(self.image)  # Drawオブジェクトを再作成
            self.update_display_image()
            self.unsaved_changes = True

    def save_image(self):
        if self.image and self.image_loaded:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("HEIC files", "*.heic"),
                    ("All files", "*.*"),
                ],
            )
            if file_path:
                try:
                    # ファイル形式に応じた保存処理
                    if file_path.lower().endswith(".png"):
                        self.image.save(file_path, format="PNG", compress_level=6)
                    elif file_path.lower().endswith(
                        ".jpg"
                    ) or file_path.lower().endswith(".jpeg"):
                        # JPEG品質設定ダイアログ
                        quality = simpledialog.askinteger(
                            "JPEG品質設定",
                            "JPEG品質を指定してください (1-100)",
                            minvalue=1,
                            maxvalue=100,
                            initialvalue=95,
                        )
                        if quality is not None:  # キャンセルされた場合は保存しない
                            # RGBA画像をRGBに変換
                            if self.image.mode == "RGBA":
                                rgb_image = self.image.convert("RGB")
                                rgb_image.save(
                                    file_path, format="JPEG", quality=quality
                                )
                            else:
                                self.image.save(
                                    file_path, format="JPEG", quality=quality
                                )
                    elif file_path.lower().endswith(".heic"):
                        self.image.save(file_path, format="HEIC")
                    else:
                        # 未知の形式の場合、デフォルトでPNGとして保存
                        self.image.save(file_path + ".png", format="PNG")

                    self.unsaved_changes = False
                except Exception as e:
                    messagebox.showerror(
                        "保存エラー", f"画像の保存中にエラーが発生しました:\n{str(e)}"
                    )
        else:
            messagebox.showinfo(
                "注意", "保存する画像がありません。まずは画像を開いてください。"
            )

    def show_copyright(self):
        """著作権情報を表示"""
        messagebox.showinfo(
            "バージョン情報",
            "PythonPhotoEditor\nCopyright 2025 Taro Nakasendo\nAll Rights Reserved.",
        )

    def on_closing(self):
        if self.unsaved_changes:
            result = messagebox.askyesnocancel(
                "保存確認", "変更が保存されていません。保存しますか？", icon="warning"
            )
            if result is None:  # キャンセル
                return
            elif result:  # はい
                self.save_image()
        self.root.destroy()


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ImageEditor(root)
    # 初期ウィンドウサイズを設定
    root.geometry("1024x768")
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
