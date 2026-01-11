import customtkinter as ctk
from customtkinter import filedialog
from PIL import Image, ImageDraw, ImageFilter, ImageTk
import cv2
import numpy as np
import io
import threading
import os
import pygame
from tkinter import messagebox, Canvas, Label, Tk
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import mean_squared_error as mse
import matplotlib.pyplot as plt
from photo_crop_system import PhotoCropper, close_all_plots
import tempfile
import atexit
import sys

atexit.register(close_all_plots)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.crop_stage = 1
        self.title("PyImgScan GUI")
        self.geometry("1024x768")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Resolve paths for background media (video + audio)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        media_dir = os.path.join(base_dir, "gui additive")
        self.bg_video_path = os.path.join(media_dir, "index.mp4")
        self.bg_audio_path = os.path.join(media_dir, "index.mp3")
        self.bg_sound = None

        # Start looping background audio
        self._init_background_audio()

        self.welcome_frame = WelcomeFrame(self, self.show_editor, self.bg_video_path)
        self.welcome_frame.pack(fill="both", expand=True)

        self.editor_frame = None
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.mainloop()
         

    def on_closing(self):
        """Handle main window closing - force close EVERYTHING."""
        import matplotlib.pyplot as plt
    
        plt.close('all')
        close_all_plots()
        
        try:
            for widget in self.winfo_children():
                if isinstance(widget, ctk.CTkToplevel):
                    widget.destroy()
        except:
            pass
        
        try:
            self.quit()
        except:
            pass
        
        try:
            self.destroy()
        except:
            pass
        
        import os
        os._exit(0) 

    def _init_background_audio(self):
        """Initialize and start looping background audio."""
        try:
            print(f"Initializing audio from: {self.bg_audio_path}")
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            if os.path.isfile(self.bg_audio_path):
                print("Audio file found, loading...")
                pygame.mixer.music.load(self.bg_audio_path)
                
                def play_audio_with_skip():
                    import time
                    print("Starting audio playback...")
                    pygame.mixer.music.play(loops=-1)
                    time.sleep(0.1)
                    try:
                        pygame.mixer.music.set_pos(5.0)
                        print("Skipped to 5 seconds")
                    except Exception as e:
                        print(f"Could not skip audio position: {e}")
                        time.sleep(5)
                        pygame.mixer.music.stop()
                        pygame.mixer.music.play(loops=-1)
                        print("Restarted audio after 5 seconds")
                
                audio_thread = threading.Thread(target=play_audio_with_skip, daemon=True)
                audio_thread.start()
                print("Audio thread started")
            else:
                print(f"Audio file not found: {self.bg_audio_path}")
        except Exception as e:
            print(f"Background audio could not be started: {e}")
            import traceback
            traceback.print_exc()    

    def show_editor(self, filepath):
        if self.welcome_frame is not None:
            self.welcome_frame.stop_background_video()
            self.welcome_frame.pack_forget()
        self.editor_frame = EditorFrame(self, filepath)
        self.editor_frame.pack(fill="both", expand=True)


class WelcomeFrame(ctk.CTkFrame):
    def __init__(self, master, on_image_select, video_path):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.on_image_select = on_image_select
        self.video_path = video_path
        self.cap = None
        self.video_running = False
        self.video_ctk_image = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.video_label = ctk.CTkLabel(self, text="", fg_color="transparent")
        self.video_label.grid(row=0, column=0, sticky="nsew")
        
        self.gradient_mask = None
        self.current_text_overlay = ""
        self._create_gradient_mask()

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.place(relx=0.5, rely=0.78, anchor="center")
        self.select_image_button = ctk.CTkButton(
            self.button_frame,
            text="Select Image",
            command=self.select_image,
            corner_radius=0,
            height=48,
            width=220,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#A0522D",
            text_color="white",
            hover_color="#CD853F",
        )
        self.select_image_button.pack()

        self.start_background_video()
        self._typing_text = "Save Your Memories"
        self._typing_index = 0
        self._start_typing_effect()

    def select_image(self):
        filepath = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=(("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*"))
        )
        if filepath:
            self.on_image_select(filepath)

    def start_background_video(self):
        """Start playing the background video in a loop (muted)."""
        if not os.path.isfile(self.video_path):
            print(f"Video file not found: {self.video_path}")
            return
        try:
            print(f"Attempting to open video: {self.video_path}")
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                print(f"Could not open video file: {self.video_path}")
                alt_path = self.video_path.replace("\\", "/")
                self.cap = cv2.VideoCapture(alt_path)
                if not self.cap.isOpened():
                    self.cap = None
                    return
            print("Video opened successfully")
            self.video_running = True
            self.after(200, self._update_video_frame)
        except Exception as e:
            print(f"Error starting video: {e}")
            import traceback
            traceback.print_exc()
            self.cap = None

    def _update_video_frame(self):
        """Read next frame from video and display it, looping when needed."""
        if not self.video_running or self.cap is None:
            return

        try:
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to read video frame after loop")
                    return

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            self.update_idletasks()
            w = self.winfo_width()
            h = self.winfo_height()
            
            if w < 100 or h < 100:
                w, h = 1024, 768
            
            frame_resized = cv2.resize(frame, (w, h))
            image = Image.fromarray(frame_resized).convert("RGBA")
            
            try:
                overlay_alpha = int(255 * 0.50)
                overlay_img = Image.new("RGBA", (w, h), (0, 0, 0, overlay_alpha))
                image = Image.alpha_composite(image, overlay_img)
            except Exception:
                pass

            if self.gradient_mask is not None:
                gradient_resized = self.gradient_mask.resize((w, h), Image.LANCZOS)
                image = Image.alpha_composite(image, gradient_resized)
                
            if hasattr(self, 'current_text_overlay') and self.current_text_overlay:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(image)
                try:
                    font = ImageFont.truetype("times.ttf", 42)
                except:
                    try:
                        font = ImageFont.truetype("arial.ttf", 42)
                    except:
                        try:
                            import platform
                            if platform.system() == "Windows":
                                font = ImageFont.truetype("C:/Windows/Fonts/times.ttf", 42)
                            else:
                                font = ImageFont.load_default()
                        except:
                            font = ImageFont.load_default()
                try:
                    bbox = draw.textbbox((0, 0), self.current_text_overlay, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                except Exception:
                    text_width, text_height = draw.textsize(self.current_text_overlay, font=font)
                text_x = (w - text_width) // 2
                text_y = int(h * 0.22) - text_height // 2
                draw.text((text_x+2, text_y+2), self.current_text_overlay, fill=(0,0,0,200), font=font)
                draw.text((text_x, text_y), self.current_text_overlay, fill="white", font=font)
            
            image_rgb = image.convert("RGB")

            self.video_ctk_image = ctk.CTkImage(light_image=image_rgb, dark_image=image_rgb, size=(w, h))
            self.video_label.configure(image=self.video_ctk_image, text="")

            self.after(33, self._update_video_frame)
        except Exception as e:
            print(f"Error updating video frame: {e}")
            import traceback
            traceback.print_exc()
            self.video_running = False

    def _create_gradient_mask(self):
        """Create a gradient mask that will be composited onto video frames."""
        def update_gradient_mask():
            try:
                w = self.master.winfo_width()
                h = self.master.winfo_height()
                if w < 10 or h < 10:
                    self.after(100, update_gradient_mask)
                    return
                
                border_width = min(w, h) * 0.15
                
                y_coords, x_coords = np.ogrid[:h, :w]
                
                dist_top = y_coords
                dist_bottom = h - y_coords
                dist_left = x_coords
                dist_right = w - x_coords
                
                min_dist = np.minimum(np.minimum(dist_top, dist_bottom), 
                                     np.minimum(dist_left, dist_right))
                
                max_grad_alpha = int(255 * 0.60)
                alpha = np.where(
                    min_dist < border_width,
                    (max_grad_alpha * (1 - (min_dist / border_width))),
                    0,
                ).astype(np.uint8)
                
                gradient_array = np.zeros((h, w, 4), dtype=np.uint8)
                gradient_array[:, :, 3] = alpha
                
                self.gradient_mask = Image.fromarray(gradient_array, "RGBA")
            except Exception as e:
                print(f"Error creating gradient mask: {e}")
        
        self.after(200, update_gradient_mask)

    def _start_typing_effect(self):
        """Display text letter by letter like someone is writing it."""
        if self._typing_index < len(self._typing_text):
            current_text = self._typing_text[:self._typing_index + 1]
            self.current_text_overlay = current_text
            self._typing_index += 1
            self.after(150, self._start_typing_effect)

    def stop_background_video(self):
        """Stop updating the background video."""
        self.video_running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None


class SimpleCropDialog(ctk.CTkToplevel):
    """Simple dialog for choosing cropping method."""
    
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        
        self.title("Crop Options")
        self.geometry("400x250")
        self.transient(master)
        self.resizable(False, False)
        
        self.attributes('-topmost', True)
        self.protocol("WM_DELETE_WINDOW", self.on_dialog_close)
        
        title_label = ctk.CTkLabel(
            self, 
            text="Choose Cropping Method",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=20)
        
        brown_color = "#A0522D"
        brown_hover = "#CD853F"
        
        btn_auto = ctk.CTkButton(
            self,
            text="Automatic",
            command=self.crop_automatic,
            fg_color=brown_color,
            hover_color=brown_hover,
            height=50,
            font=ctk.CTkFont(size=14)
        )
        btn_auto.pack(pady=10, padx=40, fill="x")
        
        btn_manual = ctk.CTkButton(
            self,
            text="Manual",
            command=self.crop_manual,
            fg_color=brown_color,
            hover_color=brown_hover,
            height=50,
            font=ctk.CTkFont(size=14)
        )
        btn_manual.pack(pady=10, padx=40, fill="x")
        
        self.after(20, self.grab_set)
    
    def on_dialog_close(self):
        """Handle dialog close button."""
        self.grab_release()
        self.destroy()
    
    def crop_automatic(self):
        """Automatic crop - detects border and crops."""
        try:
            if self.master.photo_cropper is None:
                img_array = cv2.cvtColor(np.array(self.master.current_image), cv2.COLOR_RGB2BGR)
                self.master.photo_cropper = PhotoCropper(image_array=img_array)
            
            cropper = self.master.photo_cropper
            
            if self.master.crop_stage == 1:
                stage = "outer"
            else:
                stage = "inner"
            
            result = cropper.crop_next_stage_auto(stage=stage)
            
            if result is None:
                messagebox.showinfo(
                    "No Border Detected", 
                    f"No {stage} border detected in the image.\nThe image may already be fully cropped."
                )
                self.master.photo_cropper = None
                self.destroy()
                return
            
            cropped, corners, stage_num = result
            
            img_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(img_rgb)
            
            self.master.add_to_history(pil_image)
            self.master.display_image(pil_image)
            self.master.crop_stage += 1
            
            print(f"✓ Automatic {stage} crop complete - Stage {self.master.crop_stage}")
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Automatic cropping failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
            self.master.photo_cropper = None
            self.destroy()
    
    def crop_manual(self):
        """Manual crop - ALWAYS shows original uncropped photo."""
        try:
            if len(self.master.image_history) > 0:
                original_image = self.master.image_history[0]
            else:
                original_image = self.master.current_image
            
            img_array = cv2.cvtColor(np.array(original_image), cv2.COLOR_RGB2BGR)
            
            self.master.photo_cropper = PhotoCropper(image_array=img_array)
            cropper = self.master.photo_cropper
            
            self.destroy()
            
            cropped, corners = cropper.manual_crop()
            
            img_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(img_rgb)
            
            self.master.add_to_history(pil_image)
            self.master.display_image(pil_image)
            self.master.crop_stage += 1
            
            print("✓ Manual crop complete")
            
            self.master.photo_cropper = None
            
        except Exception as e:
            messagebox.showerror("Error", f"Manual cropping failed:\n{str(e)}")
            import traceback
            traceback.print_exc()
            self.master.photo_cropper = None


class EditorFrame(ctk.CTkFrame):
    def __init__(self, master, filepath):
        super().__init__(master)

        self.image_history = []
        self.redo_history = []
        self.analysis_results = None
        self.analysis_toplevel = None
        self.photo_cropper = None
        self.crop_stage = 1
        self.last_jpeg_quality = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        self.sidebar_title = ctk.CTkLabel(self.sidebar_frame, text="Tools", font=ctk.CTkFont(size=20, weight="bold"))
        self.sidebar_title.pack(pady=20)

        brown_color = "#A0522D"
        brown_hover = "#CD853F"
        
        self.detect_corners_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="Crop Image", 
            command=self.detect_and_crop,
            fg_color=brown_color,
            hover_color=brown_hover,
            text_color="white"
        )
        self.detect_corners_button.pack(pady=10, padx=20, fill="x")

        self.analyze_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="Analyze Compression", 
            command=self.open_analysis_options,
            fg_color=brown_color,
            hover_color=brown_hover,
            text_color="white"
        )
        self.analyze_button.pack(pady=10, padx=20, fill="x")

        self.glare_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="Remove Glare", 
            command=self.remove_glare,
            fg_color=brown_color,
            hover_color=brown_hover,
            text_color="white"
        )
        self.glare_button.pack(pady=10, padx=20, fill="x")
        
        self.show_report_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="Show Analysis Report", 
            state="disabled", 
            command=self.show_analysis_report,
            fg_color=brown_color,
            hover_color=brown_hover,
            text_color="white"
        )
        self.show_report_button.pack(pady=10, padx=20, fill="x")
        
        self.change_picture_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="Change Picture", 
            command=self.change_picture,
            fg_color=brown_color,
            hover_color=brown_hover,
            text_color="white"
        )

        self.zoom_min = 10
        self.zoom_max = 400
        self.zoom_percent = 100

        self.zoom_slider = ctk.CTkSlider(self.sidebar_frame, from_=self.zoom_min, to=self.zoom_max, number_of_steps=390, command=self._on_slider_change)
        try:
            self.zoom_slider.set(self.zoom_percent)
        except Exception:
            pass
        self.zoom_slider.pack(pady=10, padx=20, fill="x")

        self.change_picture_button.pack(side="bottom", pady=20, padx=20, fill="x")

        self.canvas_container = ctk.CTkFrame(self, fg_color="transparent")
        self.canvas_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.canvas = Canvas(self.canvas_container, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.current_image = None
        self._display_image = None
        self._tk_image = None
        self.zoom_percent = 100
        self.zoom_min = 10
        self.zoom_max = 400
        self.offset_x = 0
        self.offset_y = 0
        self._drag_data = {"x": 0, "y": 0, "start_off_x": 0, "start_off_y": 0}

        self.canvas.bind("<ButtonPress-1>", self._on_button_press)
        self.canvas.bind("<B1-Motion>", self._on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self._on_mouse_wheel)
        
        self.bottom_bar_frame = ctk.CTkFrame(self, height=80, corner_radius=0)
        self.bottom_bar_frame.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
        self.bottom_bar_frame.grid_propagate(False)
        self.bottom_bar_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.back_button = ctk.CTkButton(
            self.bottom_bar_frame, 
            text="Undo", 
            command=self.undo,
            fg_color=brown_color,
            hover_color=brown_hover,
            text_color="white"
        )
        self.back_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.redo_button = ctk.CTkButton(
            self.bottom_bar_frame, 
            text="Redo", 
            command=self.redo, 
            state="disabled",
            fg_color=brown_color,
            hover_color=brown_hover,
            text_color="white"
        )
        self.redo_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.save_button = ctk.CTkButton(
            self.bottom_bar_frame, 
            text="Save Image", 
            command=self.save_image,
            fg_color=brown_color,
            hover_color=brown_hover,
            text_color="white"
        )
        self.save_button.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        self.current_image = Image.open(filepath)
        self.current_image_path = filepath
        self.add_to_history(self.current_image)
        self.display_image(self.current_image)
        self.update_button_states()

    def display_image(self, pil_image):
        self.current_image = pil_image.copy()
        self.offset_x = 0
        self.offset_y = 0
        def _fit_when_ready(attempts_left=10):
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            if canvas_w < 50 or canvas_h < 50:
                if attempts_left > 0:
                    self.after(50, lambda: _fit_when_ready(attempts_left-1))
                else:
                    self._redraw_canvas()
                return

            img_w, img_h = self.current_image.size
            if img_w == 0 or img_h == 0:
                fit_zoom = 100
            else:
                fit_zoom = int(min(canvas_w / img_w, canvas_h / img_h) * 100)
            fit_zoom = max(self.zoom_min, min(self.zoom_max, fit_zoom))
            self.zoom_percent = fit_zoom
            try:
                self.zoom_slider.set(self.zoom_percent)
            except Exception:
                pass

            scaled_w = int(img_w * self.zoom_percent / 100)
            scaled_h = int(img_h * self.zoom_percent / 100)
            if scaled_w > canvas_w:
                self.offset_x = (scaled_w - canvas_w) // 2
            else:
                self.offset_x = 0
            if scaled_h > canvas_h:
                self.offset_y = (scaled_h - canvas_h) // 2
            else:
                self.offset_y = 0

            self._redraw_canvas()

        _fit_when_ready()

    def _redraw_canvas(self):
        if self.current_image is None:
            return

        canvas_w = max(200, self.canvas.winfo_width())
        canvas_h = max(200, self.canvas.winfo_height())

        zoom = max(self.zoom_min, min(self.zoom_max, self.zoom_percent)) / 100.0
        img_w, img_h = self.current_image.size
        scaled_w = max(1, int(img_w * zoom))
        scaled_h = max(1, int(img_h * zoom))

        try:
            scaled = self.current_image.resize((scaled_w, scaled_h), Image.LANCZOS)
        except Exception:
            scaled = self.current_image.copy()

        max_off_x = max(0, scaled_w - canvas_w)
        max_off_y = max(0, scaled_h - canvas_h)
        self.offset_x = int(max(0, min(self.offset_x, max_off_x)))
        self.offset_y = int(max(0, min(self.offset_y, max_off_y)))

        left = self.offset_x
        top = self.offset_y
        right = left + canvas_w
        bottom = top + canvas_h
        
        if scaled_w < canvas_w or scaled_h < canvas_h:
            bg = Image.new("RGB", (canvas_w, canvas_h), (43,43,43))
            paste_x = max(0, (canvas_w - scaled_w) // 2)
            paste_y = max(0, (canvas_h - scaled_h) // 2)
            bg.paste(scaled, (paste_x, paste_y))
            final = bg
        else:
            final = scaled.crop((left, top, right, bottom))

        self._tk_image = ImageTk.PhotoImage(final)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._tk_image)
        self.canvas.config(scrollregion=(0, 0, canvas_w, canvas_h))

    def _on_slider_change(self, value):
        try:
            self.zoom_percent = int(float(value))
        except Exception:
            self.zoom_percent = self.zoom_percent
        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        img_w, img_h = self.current_image.size
        old_zoom = getattr(self, '_last_zoom', self.zoom_percent) / 100.0
        new_zoom = self.zoom_percent / 100.0
        self._last_zoom = self.zoom_percent
        center_x = self.offset_x + canvas_w / 2
        center_y = self.offset_y + canvas_h / 2
        if old_zoom > 0:
            rel_x = center_x / old_zoom
            rel_y = center_y / old_zoom
            new_center_x = rel_x * new_zoom
            new_center_y = rel_y * new_zoom
            self.offset_x = int(new_center_x - canvas_w / 2)
            self.offset_y = int(new_center_y - canvas_h / 2)
        else:
            self.offset_x = 0
            self.offset_y = 0
        self._redraw_canvas()

    def _on_mouse_wheel(self, event):
        try:
            if hasattr(event, 'delta'):
                delta = event.delta
            elif event.num == 4:
                delta = 120
            else:
                delta = -120
        except Exception:
            delta = 0

        if delta > 0:
            new = min(self.zoom_max, self.zoom_percent + 10)
        else:
            new = max(self.zoom_min, self.zoom_percent - 10)
        self.zoom_percent = new
        try:
            self.zoom_slider.set(self.zoom_percent)
        except Exception:
            pass
        self._redraw_canvas()

    def _on_button_press(self, event):
        self._drag_data['x'] = event.x
        self._drag_data['y'] = event.y
        self._drag_data['start_off_x'] = self.offset_x
        self._drag_data['start_off_y'] = self.offset_y

    def _on_move_press(self, event):
        dx = event.x - self._drag_data['x']
        dy = event.y - self._drag_data['y']
        self.offset_x = int(self._drag_data['start_off_x'] - dx)
        self.offset_y = int(self._drag_data['start_off_y'] - dy)
        self._redraw_canvas()

    def _on_button_release(self, event):
        self._drag_data['x'] = 0
        self._drag_data['y'] = 0
        self._drag_data['start_off_x'] = 0
        self._drag_data['start_off_y'] = 0

    def add_to_history(self, image):
        self.image_history.append(image.copy())
        self.redo_history.clear()
        self.update_button_states()

    def detect_and_crop(self):
        """Open crop method dialog."""
        self.last_jpeg_quality = None
        SimpleCropDialog(self)

    def update_and_display_compressed(self, compressed_image):
        self.add_to_history(self.current_image)
        self.display_image(compressed_image)

    def open_analysis_options(self):
        if self.analysis_toplevel is None or not self.analysis_toplevel.winfo_exists():
            self.analysis_toplevel = AnalysisOptionsWindow(self)
        else:
            self.analysis_toplevel.focus()

    def show_analysis_report(self):
        if self.analysis_results:
            AnalysisReportWindow(self, self.analysis_results)

    def run_analysis_thread(self, targets_kb):
        thread = threading.Thread(target=self.run_analysis, args=(targets_kb,))
        thread.daemon = True
        thread.start()

    def run_analysis(self, targets_kb):
        try:
            self.analysis_results = []
            original_image_cv = np.array(self.image_history[0])
            original_image_cv_rgb = original_image_cv[:, :, ::-1]

            for target_kb in targets_kb:
                target_bytes = target_kb * 1024
                
                low = 1
                high = 100
                found_quality = -1 # Best quality found so far that is AT OR BELOW target

                while low <= high:
                    quality = (low + high) // 2
                    if quality == 0: break
                    
                    buffer = io.BytesIO()
                    self.image_history[0].save(buffer, "JPEG", quality=quality)
                    size_in_bytes = buffer.tell()
                    
                    if size_in_bytes <= target_bytes:
                        # This is a valid candidate, save it
                        found_quality = quality
                        # Try for a better quality (and larger size)
                        low = quality + 1
                    else:
                        # Size is too large, reduce quality
                        high = quality - 1
                
                # If no quality setting produces a file small enough, default to lowest quality
                if found_quality == -1:
                    found_quality = 1

                buffer = io.BytesIO()
                self.image_history[0].save(buffer, "JPEG", quality=found_quality)
                compressed_image = Image.open(buffer)
                compressed_image_cv = np.array(compressed_image)

                psnr_val = psnr(original_image_cv_rgb, compressed_image_cv)
                
                h, w, _ = original_image_cv_rgb.shape
                min_dim = min(h, w)
                win_size = min(7, min_dim)
                if win_size % 2 == 0:
                    win_size -= 1
                
                if win_size < 3:
                    ssim_val = 0.0
                else:
                    ssim_val = ssim(original_image_cv_rgb, compressed_image_cv, win_size=win_size, channel_axis=-1, data_range=255)

                mse_val = mse(original_image_cv_rgb, compressed_image_cv)

                self.analysis_results.append({
                    "target_kb": target_kb,
                    "actual_kb": buffer.tell() / 1024,
                    "quality": found_quality,
                    "psnr": psnr_val,
                    "ssim": ssim_val,
                    "mse": mse_val
                })

                if len(targets_kb) == 1:
                    self.last_jpeg_quality = found_quality
                    self.after(0, self.update_and_display_compressed, compressed_image)

            self.show_report_button.configure(state="normal")
            messagebox.showinfo("Analysis Complete", "The compression analysis is complete. Click 'Show Analysis Report' to see the results.")
        except Exception as e:
            messagebox.showerror("Analysis Error", f"An error occurred during analysis:\n{e}")

    def remove_glare(self):
        """Open advanced glare removal dialog."""
        self.last_jpeg_quality = None
        from advanced_glare_dialog import AdvancedGlareRemovalDialog
        
        dialog = AdvancedGlareRemovalDialog(self, self.current_image)
        # Wait for dialog to close
        self.wait_window(dialog)
        
        # If user selected a method, apply result
        if dialog.result is not None:
            self.add_to_history(self.current_image)
            self.display_image(dialog.result)

    def undo(self):
        if len(self.image_history) > 1:
            self.last_jpeg_quality = None
            self.redo_history.append(self.image_history.pop())
            self.display_image(self.image_history[-1])
            self.photo_cropper = None
            # Reset crop stage when undoing so you can crop again
            self.crop_stage = 1
        self.update_button_states()

    def redo(self):
        if self.redo_history:
            self.image_history.append(self.redo_history.pop())
            self.display_image(self.image_history[-1])
        self.update_button_states()
        
    def change_picture(self):
        plt.close('all')
        close_all_plots()
        
        self.photo_cropper = None
        self.last_jpeg_quality = None
        
        filepath = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=(("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*"))
        )
        if filepath:
            self.image_history.clear()
            self.redo_history.clear()
            self.analysis_results = None
            
            self.current_image = Image.open(filepath)
            self.current_image_path = filepath
            self.crop_stage = 1
            self.add_to_history(self.current_image)
            self.display_.image(self.current_image)
            
            self.show_report_button.configure(state="disabled")
            self.update_button_states()

    def update_button_states(self):
        self.back_button.configure(state="normal" if len(self.image_history) > 1 else "disabled")
        self.redo_button.configure(state="normal" if self.redo_history else "disabled")

    def save_image(self):
        filepath = filedialog.asksaveasfilename(
            title="Save Image",
            defaultextension=".png",
            filetypes=(("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All files", "*.*"))
        )
        if filepath:
            save_params = {}
            file_ext = os.path.splitext(filepath)[1].lower()

            if file_ext in ['.jpg', '.jpeg']:
                if self.last_jpeg_quality is not None:
                    save_params['quality'] = self.last_jpeg_quality
                    print(f"Saving as JPEG with remembered quality: {self.last_jpeg_quality}")
                else:
                    # If no quality is remembered, use a default high quality
                    save_params['quality'] = 95
                    print("Saving as JPEG with default quality (95)")
            
            self.current_image.save(filepath, **save_params)
            # Invalidate the quality after any save
            self.last_jpeg_quality = None


class AnalysisOptionsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.title("Analysis Options")
        self.geometry("300x350")
        self.transient(master)
        
        self.label = ctk.CTkLabel(self, text="Select a target file size:")
        self.label.pack(pady=10)

        self.buttons = []
        targets = {"30 KB": 30, "100 KB": 100, "500 KB": 500, "1 MB": 1024}
        for text, size_kb in targets.items():
            btn = ctk.CTkButton(self, text=text, command=lambda s=size_kb: self.start_analysis(s))
            btn.pack(pady=5, padx=20, fill="x")
            self.buttons.append(btn)
            
        self.run_all_button = ctk.CTkButton(self, text="Run All & Plot", command=self.run_all_analysis)
        self.run_all_button.pack(pady=15, padx=20, fill="x")
        self.buttons.append(self.run_all_button)

        self.progress_bar = ctk.CTkProgressBar(self, mode='indeterminate')
        
        self.after(20, self.grab_set)

    def start_analysis(self, target_size_kb):
        for btn in self.buttons:
            btn.configure(state="disabled")
        self.progress_bar.pack(pady=10, padx=20, fill="x")
        self.progress_bar.start()
        
        self.master.run_analysis_thread([target_size_kb])
        self.destroy()

    def run_all_analysis(self):
        for btn in self.buttons:
            btn.configure(state="disabled")
        self.progress_bar.pack(pady=10, padx=20, fill="x")
        self.progress_bar.start()

        targets_kb = [30, 100, 500, 1024]
        self.master.run_analysis_thread(targets_kb)
        self.destroy()


class AnalysisReportWindow(ctk.CTkToplevel):
    def __init__(self, master, results):
        super().__init__(master)
        self.title("Analysis Report")
        self.geometry("850x700")
        self.transient(master)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.plot_label = ctk.CTkLabel(self, text="")
        self.plot_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.generate_and_display_plot(results)

        self.textbox = ctk.CTkTextbox(self, wrap="word")
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.generate_report_text(results)
        self.textbox.configure(state="disabled")

        self.after(20, self.grab_set)

    def generate_and_display_plot(self, results):
        sizes = [r['actual_kb'] for r in results]
        psnr_vals = [r['psnr'] for r in results]

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(8, 4))
        
        ax.plot(sizes, psnr_vals, 'w-o', label='PSNR')
        ax.set_xlabel("File Size (KB)")
        ax.set_ylabel("PSNR (dB)")
        ax.set_title("Rate-Distortion Curve")
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax.legend()
        
        if len(sizes) > 2:
            slopes = [(psnr_vals[i+1] - psnr_vals[i]) / (sizes[i+1] - sizes[i]) for i in range(len(sizes)-1)]
            if slopes:
                optimal_index = np.argmax(np.diff(slopes)) + 1 if len(slopes) > 1 else 0
                ax.plot(sizes[optimal_index], psnr_vals[optimal_index], 'r*', markersize=15, label='Optimal Point')
                ax.legend()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plot_image = Image.open(buf)
        
        ctk_plot = ctk.CTkImage(light_image=plot_image, dark_image=plot_image, size=plot_image.size)
        self.plot_label.configure(image=ctk_plot)
        plt.close(fig)

    def generate_report_text(self, results):
        report = "Compression & Rate-Distortion Analysis\n"
        report += "=" * 40 + "\n\n"

        report += f"{ 'Target Size':<15}{'Actual Size':<15}{'Quality':<10}{'PSNR (dB)':<15}{'SSIM':<10}{'MSE':<10}\n"
        report += "-" * 75 + "\n"

        for r in sorted(results, key=lambda x: x['actual_kb']):
            report += f"{r['target_kb']:<15.0f}{r['actual_kb']:<15.2f}{r['quality']:<10}{r['psnr']:<15.2f}{r['ssim']:<10.4f}{r['mse']:<10.2f}\n"

        report += "\n\n" + "=" * 40 + "\n"
        report += "Subjective Analysis\n"
        report += "=" * 40 + "\n\n"

        for r in sorted(results, key=lambda x: x['actual_kb']):
            report += f"--- {r['target_kb']} KB Target ---\n"
            if r['actual_kb'] < 50:
                report += "Visual Quality: Poor.\nArtifacts: Heavy blocking, ringing, and color banding are very noticeable.\n\n"
            elif r['actual_kb'] < 200:
                report += "Visual Quality: Acceptable.\nArtifacts: Minor blocking and softness are visible upon inspection.\n\n"
            elif r['actual_kb'] < 800:
                report += "Visual Quality: Good.\nArtifacts: Very few artifacts. Slight softness might be visible in high-frequency areas.\n\n"
            else:
                report += "Visual Quality: Excellent.\nArtifacts: Essentially none.\n\n"
        
        report += "\n" + "=" * 40 + "\n"
        report += "Recommendation\n"
        report += "=" * 40 + "\n\n"
        report += "The 'Optimal Point' on the plot marks the 'knee' of the curve, where increasing the file size yields diminishing returns in quality.\n"
        report += "For a good balance of size and quality, the setting closest to this point is recommended. For high-quality archival, use the highest setting."

        self.textbox.insert("0.0", report)


if __name__ == "__main__":
    App()