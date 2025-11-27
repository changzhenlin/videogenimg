import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import glob

class ImageBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("图片浏览器")
        self.root.geometry("1024x768")
        self.root.minsize(800, 600)
        
        # 设置中文字体支持
        self.font_config = {"family": "SimHei", "size": 10}
        
        # 当前文件夹路径
        self.current_folder = ""
        # 原始图片路径列表（未筛选的完整列表）
        self.original_image_paths = []
        # 筛选后的图片路径列表
        self.image_paths = []
        # 当前选中的图片索引
        self.selected_index = -1
        # 当前预览窗口
        self.preview_window = None
        # 当前筛选关键词
        self.current_filter = ""
        
        # 创建UI
        self.create_ui()
    
    def create_ui(self):
        # 创建顶部菜单栏
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        # 文件菜单
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="文件", menu=self.file_menu)
        self.file_menu.add_command(label="选择文件夹", command=self.select_folder)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="退出", command=self.root.quit)
        
        # 操作菜单
        self.action_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="操作", menu=self.action_menu)
        self.action_menu.add_command(label="删除选中图片", command=self.delete_selected_image)
        self.action_menu.add_command(label="刷新列表", command=self.refresh_images)
        
        # 添加搜索筛选区域
        self.search_frame = tk.Frame(self.root)
        self.search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 搜索标签
        search_label = tk.Label(self.search_frame, text="搜索图片名称:", font=self.font_config)
        search_label.pack(side=tk.LEFT, padx=5)
        
        # 搜索输入框
        self.search_entry = tk.Entry(self.search_frame, font=self.font_config, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        # 支持回车键触发搜索
        self.search_entry.bind('<Return>', lambda event: self.filter_images())
        
        # 搜索按钮
        self.search_btn = tk.Button(
            self.search_frame, 
            text="搜索", 
            command=self.filter_images,
            font=self.font_config
        )
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        # 清除筛选按钮
        self.clear_filter_btn = tk.Button(
            self.search_frame, 
            text="清除筛选", 
            command=self.clear_filter,
            font=self.font_config,
            state=tk.DISABLED  # 初始禁用
        )
        self.clear_filter_btn.pack(side=tk.LEFT, padx=5)
        
        # 创建状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("请选择一个包含JPG图片的文件夹")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建主框架
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建左侧图片列表框架
        self.list_frame = tk.Frame(self.main_frame)
        self.list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # 创建滚动条
        self.scrollbar = tk.Scrollbar(self.list_frame, orient=tk.VERTICAL)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建列表框
        self.image_listbox = tk.Listbox(
            self.list_frame, 
            width=60,  # 增加宽度以显示完整路径
            height=30, 
            font=self.font_config,
            yscrollcommand=self.scrollbar.set,
            selectmode=tk.EXTENDED  # 支持多选
        )
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.image_listbox.yview)
        
        # 绑定列表框事件
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        self.image_listbox.bind('<Double-1>', self.on_image_double_click)
        
        # 创建右侧预览框架
        self.preview_frame = tk.Frame(self.main_frame, relief=tk.SUNKEN, bd=2)
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        self.preview_scrollbar = tk.Scrollbar(self.preview_frame, orient=tk.VERTICAL)
        self.preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建可滚动的画布
        self.preview_canvas = tk.Canvas(self.preview_frame, yscrollcommand=self.preview_scrollbar.set)
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.preview_scrollbar.config(command=self.preview_canvas.yview)
        
        # 创建内部框架用于放置图片网格
        self.image_grid_frame = tk.Frame(self.preview_canvas)
        self.preview_canvas.create_window((0, 0), window=self.image_grid_frame, anchor=tk.NW)
        
        # 绑定画布大小变化事件
        self.image_grid_frame.bind("<Configure>", self.on_frame_configure)
        self.preview_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 创建底部按钮
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        self.select_folder_btn = tk.Button(
            self.button_frame, 
            text="选择文件夹", 
            command=self.select_folder,
            font=self.font_config
        )
        self.select_folder_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_btn = tk.Button(
            self.button_frame, 
            text="删除选中图片", 
            command=self.delete_selected_image,
            font=self.font_config,
            state=tk.DISABLED
        )
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = tk.Button(
            self.button_frame, 
            text="刷新列表", 
            command=self.refresh_images,
            font=self.font_config
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
    
    def on_frame_configure(self, event):
        # 当内部框架大小变化时，更新画布的滚动区域
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        # 当画布大小变化时，更新内部框架的宽度
        width = event.width
        self.preview_canvas.itemconfig(self.preview_canvas.find_all()[0], width=width)
    
    def create_image_thumbnails(self):
        """创建并显示所有图片的缩略图"""
        # 清空现有缩略图
        for widget in self.image_grid_frame.winfo_children():
            widget.destroy()
        
        # 设置缩略图大小和布局
        thumbnail_width, thumbnail_height = 150, 150
        columns = 3  # 每行显示3张图片
        
        # 获取画布宽度，动态调整列数
        canvas_width = self.preview_canvas.winfo_width()
        if canvas_width > 0:
            columns = max(1, canvas_width // (thumbnail_width + 20))  # 20是边距
        
        # 创建缩略图
        for i, img_path in enumerate(self.image_paths):
            try:
                # 计算位置
                row = i // columns
                col = i % columns
                
                # 创建缩略图框架
                thumb_frame = tk.Frame(self.image_grid_frame, padx=5, pady=5)
                thumb_frame.grid(row=row, column=col, sticky=tk.NW)
                
                # 打开图片并调整大小
                image = Image.open(img_path)
                image.thumbnail((thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                
                # 创建图片按钮
                img_button = tk.Button(
                    thumb_frame, 
                    image=photo, 
                    bd=1, 
                    relief=tk.FLAT,
                    command=lambda path=img_path, idx=i: self.on_thumbnail_click(path, idx)
                )
                img_button.image = photo  # 保持引用
                img_button.pack(pady=(0, 2))
                
                # 创建文件名标签
                img_name = os.path.basename(img_path)
                name_label = tk.Label(
                    thumb_frame, 
                    text=img_name, 
                    font=(self.font_config["family"], 8),
                    wraplength=thumbnail_width,
                    anchor=tk.W,
                    justify=tk.LEFT
                )
                name_label.pack(side=tk.BOTTOM, fill=tk.X)
                
            except Exception as e:
                # 如果无法加载图片，显示错误信息
                error_label = tk.Label(
                    self.image_grid_frame,
                    text=f"无法加载: {os.path.basename(img_path)}",
                    font=(self.font_config["family"], 8),
                    fg="red",
                    wraplength=thumbnail_width
                )
                error_label.grid(row=i//columns, column=i%columns, padx=5, pady=5, sticky=tk.NW)
    
    def on_thumbnail_click(self, img_path, index):
        """点击缩略图时的处理函数，支持多选"""
        # 获取当前的选择状态
        current_selection = list(self.image_listbox.curselection())
        
        # 检查是否按住了Ctrl键或Shift键（通过检查当前选择是否包含此项）
        if index in current_selection:
            # 如果已经选中，则取消选择
            self.image_listbox.selection_clear(index)
        else:
            # 如果没有按住特殊键，则清除所有选择后选中当前项
            # 注意：Tkinter不直接提供键盘状态检测，这里使用简化逻辑
            # 完整实现需要绑定事件参数来检测keyboard state
            if len(current_selection) == 0 or (len(current_selection) == 1 and current_selection[0] == index):
                self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(index)
        
        self.image_listbox.see(index)
        
        # 更新选中索引（保留第一个选中项作为主要索引）
        new_selection = self.image_listbox.curselection()
        if new_selection:
            self.selected_index = new_selection[0]
            self.delete_btn.config(state=tk.NORMAL)
        else:
            self.selected_index = -1
            self.delete_btn.config(state=tk.DISABLED)
    
    def select_folder(self):
        """选择文件夹并加载其中的JPG图片"""
        folder_path = filedialog.askdirectory(title="选择图片文件夹")
        if folder_path:
            self.current_folder = folder_path
            self.load_images()
            self.status_var.set(f"当前文件夹: {folder_path}")
    
    def load_images(self):
        """加载当前文件夹及其所有子文件夹中的JPG图片"""
        # 清空列表
        self.image_listbox.delete(0, tk.END)
        self.image_paths = []
        self.original_image_paths = []
        
        # 递归查找所有JPG图片
        jpg_files = []
        for root, dirs, files in os.walk(self.current_folder):
            for file in files:
                if file.lower().endswith('.jpg'):
                    jpg_files.append(os.path.join(root, file))
        
        # 按文件名排序
        jpg_files.sort()
        
        # 更新原始图片列表
        self.original_image_paths = jpg_files.copy()
        
        # 根据当前是否有筛选条件决定显示哪些图片
        if self.current_filter:
            # 如果有筛选条件，应用筛选
            self.filter_images()
        else:
            # 没有筛选条件，显示所有图片
            self.image_paths = self.original_image_paths.copy()
            
            # 添加到列表
            for img_path in self.image_paths:
                # 显示完整路径
                self.image_listbox.insert(tk.END, img_path)
            
            # 更新状态栏
            self.status_var.set(f"找到 {len(self.image_paths)} 张图片 - {self.current_folder}")
            
            # 禁用删除按钮
            self.delete_btn.config(state=tk.DISABLED)
            
            # 创建并显示图片缩略图
            self.create_image_thumbnails()
    
    def on_image_select(self, event):
        """当选择图片时更新状态，支持多选"""
        selection = self.image_listbox.curselection()
        if selection:
            # 保留第一个选中项作为主要索引
            self.selected_index = selection[0]
            # 启用删除按钮
            self.delete_btn.config(state=tk.NORMAL)
            # 可选：在状态栏显示选中的图片数量
            if len(selection) > 1:
                self.status_var.set(f"已选择 {len(selection)} 张图片 - {self.current_folder}")
        else:
            # 没有选中项时重置状态
            self.selected_index = -1
            self.delete_btn.config(state=tk.DISABLED)
            # 恢复原始状态栏显示
            if self.current_folder:
                self.status_var.set(f"找到 {len(self.image_paths)} 张图片 - {self.current_folder}")
            else:
                self.status_var.set("请选择一个包含JPG图片的文件夹")
    
    def preview_image(self, index):
        """预览功能已被缩略图网格替代，此方法保留兼容性"""
        pass
    
    def on_image_double_click(self, event):
        """双击图片显示大图"""
        selection = self.image_listbox.curselection()
        if selection:
            index = selection[0]
            self.show_full_image(index)
    
    def show_full_image(self, index):
        """显示大图预览窗口"""
        if 0 <= index < len(self.image_paths):
            # 如果已存在预览窗口，先关闭
            if self.preview_window:
                self.preview_window.destroy()
            
            # 创建新的预览窗口
            self.preview_window = tk.Toplevel(self.root)
            self.preview_window.title(f"图片预览 - {os.path.basename(self.image_paths[index])}")
            self.preview_window.geometry("900x700")
            
            # 创建画布用于显示大图
            canvas = tk.Canvas(self.preview_window)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # 添加滚动条
            h_scrollbar = tk.Scrollbar(canvas, orient=tk.HORIZONTAL, command=canvas.xview)
            v_scrollbar = tk.Scrollbar(canvas, orient=tk.VERTICAL, command=canvas.yview)
            canvas.config(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            try:
                # 打开图片
                image = Image.open(self.image_paths[index])
                
                # 转换为Tkinter可用的格式
                photo = ImageTk.PhotoImage(image)
                
                # 在画布上显示图片
                canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                
                # 设置画布滚动区域
                canvas.config(scrollregion=canvas.bbox(tk.ALL))
                
                # 保持引用
                canvas.image = photo
            except Exception as e:
                messagebox.showerror("错误", f"无法显示大图: {str(e)}")
                self.preview_window.destroy()
    
    def delete_selected_image(self):
        """删除选中的图片（优化的多选删除功能）"""
        selection = list(self.image_listbox.curselection())
        if not selection:
            messagebox.showinfo("提示", "请先选择要删除的图片")
            return
        
        # 准备删除确认信息
        if len(selection) == 1:
            img_path = self.image_paths[selection[0]]
            confirm_msg = f"确定要删除图片 '{img_path}' 吗？"
        else:
            # 显示部分选中的图片信息，避免确认框过长
            sample_paths = [self.image_paths[idx] for idx in selection[:3]]
            sample_text = "\n".join([f"- {path}" for path in sample_paths])
            if len(selection) > 3:
                sample_text += f"\n- ... 等{len(selection)-3}张图片"
            confirm_msg = f"确定要删除选中的 {len(selection)} 张图片吗？\n\n{sample_text}"
        
        # 确认删除
        if messagebox.askyesno("确认删除", confirm_msg):
            try:
                deleted_count = 0
                failed_count = 0
                failed_paths = []
                
                # 获取要删除的图片路径列表
                paths_to_delete = [self.image_paths[idx] for idx in selection]
                
                # 按索引倒序删除，避免索引变化问题
                for index in sorted(selection, reverse=True):
                    try:
                        os.remove(self.image_paths[index])
                        self.image_listbox.delete(index)
                        self.image_paths.pop(index)
                        deleted_count += 1
                    except Exception as e:
                        failed_count += 1
                        failed_paths.append(f"{self.image_paths[index]}: {str(e)}")
                
                # 从原始列表中也删除这些图片
                for path in paths_to_delete:
                    if path in self.original_image_paths:
                        self.original_image_paths.remove(path)
                
                # 重置选中状态
                self.selected_index = -1
                
                # 禁用删除按钮
                self.delete_btn.config(state=tk.DISABLED)
                
                # 更新状态栏
                if deleted_count > 0:
                    if self.current_filter:
                        self.status_var.set(f"筛选结果: 已删除 {deleted_count} 张图片 - 剩余 {len(self.image_paths)} 张匹配图片")
                    else:
                        self.status_var.set(f"已删除 {deleted_count} 张图片 - 剩余 {len(self.image_paths)} 张图片")
                else:
                    # 恢复原始状态栏显示
                    if self.current_filter:
                        self.status_var.set(f"筛选结果: 找到 {len(self.image_paths)} 张匹配'{self.current_filter}'的图片")
                    elif self.current_folder:
                        self.status_var.set(f"找到 {len(self.image_paths)} 张图片 - {self.current_folder}")
                    else:
                        self.status_var.set("请选择一个包含JPG图片的文件夹")
                
                # 重建缩略图网格
                if deleted_count > 0:
                    self.create_image_thumbnails()
                
                # 显示删除结果
                result_msg = f"成功删除 {deleted_count} 张图片"
                if failed_count > 0:
                    result_msg += f"\n删除失败 {failed_count} 张图片:\n" + "\n".join(failed_paths[:3])
                    if len(failed_paths) > 3:
                        result_msg += f"\n... 等{len(failed_paths)-3}个错误"
                
                if failed_count > 0:
                    messagebox.showwarning("删除结果", result_msg)
                elif deleted_count > 0:
                    messagebox.showinfo("删除结果", result_msg)
                    
            except Exception as e:
                messagebox.showerror("错误", f"删除过程中发生错误: {str(e)}")
    
    def refresh_images(self):
        """刷新图片列表"""
        if self.current_folder:
            self.load_images()
    
    def filter_images(self):
        """根据输入的关键词筛选图片名称"""
        # 获取搜索关键词
        keyword = self.search_entry.get().strip().lower()
        self.current_filter = keyword
        
        if not keyword:
            # 如果关键词为空，直接调用清除筛选
            self.clear_filter()
            return
        
        # 根据关键词筛选图片
        self.image_paths = []
        for img_path in self.original_image_paths:
            # 获取文件名（不含扩展名）和扩展名
            img_name = os.path.basename(img_path).lower()
            # 检查关键词是否在文件名中
            if keyword in img_name:
                self.image_paths.append(img_path)
        
        # 更新UI显示
        self._update_display()
        
        # 启用清除筛选按钮
        self.clear_filter_btn.config(state=tk.NORMAL)
        
        # 更新状态栏
        self.status_var.set(f"筛选结果: 找到 {len(self.image_paths)} 张匹配'{keyword}'的图片")
    
    def clear_filter(self):
        """清除筛选条件，显示所有图片"""
        # 重置筛选关键词
        self.search_entry.delete(0, tk.END)
        self.current_filter = ""
        
        # 恢复原始图片列表
        self.image_paths = self.original_image_paths.copy()
        
        # 更新UI显示
        self._update_display()
        
        # 禁用清除筛选按钮
        self.clear_filter_btn.config(state=tk.DISABLED)
        
        # 更新状态栏
        self.status_var.set(f"找到 {len(self.image_paths)} 张图片 - {self.current_folder}")
    
    def _update_display(self):
        """更新列表框和缩略图显示"""
        # 清空列表
        self.image_listbox.delete(0, tk.END)
        
        # 添加筛选后的图片路径到列表
        for img_path in self.image_paths:
            self.image_listbox.insert(tk.END, img_path)
        
        # 重置选中状态
        self.selected_index = -1
        self.delete_btn.config(state=tk.DISABLED)
        
        # 重建缩略图网格
        self.create_image_thumbnails()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageBrowser(root)
    root.mainloop()