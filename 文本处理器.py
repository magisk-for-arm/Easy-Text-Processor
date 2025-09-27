import sys
import os
import shutil
import codecs
import chardet
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QLabel, QGroupBox, QLineEdit,
    QFileDialog, QMessageBox, QComboBox, QCheckBox, QTextEdit, 
    QSpinBox, QTabWidget, QListWidgetItem, QDialog, QDialogButtonBox,
    QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

class PreviewDialog(QDialog):
    def __init__(self, changes, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.populate_list(changes)
        
    def setup_ui(self):
        self.setWindowTitle("预览更改")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("以下是将要进行的更改:"))
        
        self.preview_list = QListWidget()
        layout.addWidget(self.preview_list)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def populate_list(self, changes):
        for old_name, new_name in changes:
            self.preview_list.addItem(f"{old_name} → {new_name}")

class FileConflictDialog(QDialog):
    def __init__(self, file_name, parent=None):
        super().__init__(parent)
        self.setup_ui(file_name)
        self.result_value = None
    
    def setup_ui(self, file_name):
        self.setWindowTitle("文件冲突")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"文件 '{file_name}' 已存在。是否替换？"))
        
        self.apply_to_all = QCheckBox("应用于所有冲突文件")
        layout.addWidget(self.apply_to_all)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | 
            QDialogButtonBox.StandardButton.YesToAll |
            QDialogButtonBox.StandardButton.No |
            QDialogButtonBox.StandardButton.NoToAll |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 连接按钮信号
        buttons = {
            QDialogButtonBox.StandardButton.Yes: "yes",
            QDialogButtonBox.StandardButton.YesToAll: "yes_to_all",
            QDialogButtonBox.StandardButton.No: "no",
            QDialogButtonBox.StandardButton.NoToAll: "no_to_all",
            QDialogButtonBox.StandardButton.Cancel: "cancel"
        }
        for btn, value in buttons.items():
            button_box.button(btn).clicked.connect(lambda v=value: self.set_result(v))
    
    def set_result(self, value):
        self.result_value = value
        self.reject() if value == "cancel" else self.accept()
    
    def get_result(self):
        return self.result_value, self.apply_to_all.isChecked()

class FileListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.full_paths = {}
        self.file_encodings = {}
    
    def setup_ui(self):
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        event.acceptProposedAction() if event.mimeData().hasUrls() else super().dragEnterEvent(event)
    
    def dragMoveEvent(self, event):
        event.acceptProposedAction() if event.mimeData().hasUrls() else super().dragMoveEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                self.add_file(file_path) if os.path.isfile(file_path) else self.find_txt_files_in_folder(file_path)
            event.acceptProposedAction()
        else:
            # 保存当前选中项
            selected_items = self.selectedItems()
            selected_indices = [self.row(item) for item in selected_items]
            
            # 执行默认的拖放操作
            super().dropEvent(event)
            
            # 重新选中之前选中的项
            self.clearSelection()
            for idx in selected_indices:
                if idx < self.count():
                    self.item(idx).setSelected(True)
    
    def add_file(self, file_path):
        file_name = Path(file_path).name
        item = QListWidgetItem(file_name)
        item.setToolTip(file_path)
        self.addItem(item)
        self.full_paths[file_name] = file_path
        
        encoding = self.detect_encoding(file_path)
        self.file_encodings[file_name] = encoding
        item.setToolTip(f"{file_path}\n编码: {encoding}")
    
    def detect_encoding(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)
            
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'
            
            # 检测BOM标记
            bom_encodings = [
                (codecs.BOM_UTF8, 'utf-8-sig'),
                (codecs.BOM_UTF16_LE, 'utf-16-le'),
                (codecs.BOM_UTF16_BE, 'utf-16-be')
            ]
            
            for bom, enc in bom_encodings:
                if raw_data.startswith(bom):
                    encoding = enc
                    break
            
            return encoding
        except Exception:
            return 'utf-8'
    
    def find_txt_files_in_folder(self, folder_path):
        folder = Path(folder_path)
        for txt_file in folder.glob("**/*.txt"):
            self.add_file(str(txt_file))
    
    def get_full_path(self, file_name):
        return self.full_paths.get(file_name, "")
    
    def get_file_encoding(self, file_name):
        return self.file_encodings.get(file_name, "utf-8")
    
    def update_file_name(self, old_name, new_name, new_full_path):
        for i in range(self.count()):
            item = self.item(i)
            if item.text() == old_name:
                item.setText(new_name)
                encoding = self.file_encodings.get(old_name, "utf-8")
                item.setToolTip(f"{new_full_path}\n编码: {encoding}")
                
                # 更新内部映射
                if old_name in self.full_paths:
                    self.full_paths[new_name] = self.full_paths.pop(old_name)
                if old_name in self.file_encodings:
                    self.file_encodings[new_name] = self.file_encodings.pop(old_name)
                break
    
    def get_all_files(self):
        """返回所有文件的列表，按当前显示顺序"""
        return [self._get_file_info(i) for i in range(self.count())]
    
    def get_selected_files(self):
        """返回选中文件的列表，按当前显示顺序"""
        return [self._get_file_info(self.row(item)) for item in self.selectedItems()]
    
    def _get_file_info(self, index):
        name = self.item(index).text()
        return {
            'name': name,
            'path': self.get_full_path(name),
            'encoding': self.get_file_encoding(name)
        }

class BaseRenameTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
    
    def add_field(self, label_text, field_name):
        field_layout = QHBoxLayout()
        field_layout.addWidget(QLabel(label_text))
        field = QLineEdit()
        setattr(self, field_name, field)
        field_layout.addWidget(field)
        self.layout.addLayout(field_layout)
        return field
    
    def add_button(self, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        self.layout.addWidget(button)
        return button

class FileProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.file_conflict_policy = None
    
    def setup_ui(self):
        self.setWindowTitle("文件处理工具")
        self.setGeometry(100, 100, 1000, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧文件列表区域
        left_layout = self.create_file_list_section()
        
        # 右侧功能区域
        right_layout = self.create_function_section()
        
        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 2)
    
    def create_file_list_section(self):
        layout = QVBoxLayout()
        file_list_group = QGroupBox("文件列表 (可拖动调整顺序)")
        file_list_layout = QVBoxLayout()
        
        self.file_list = FileListWidget()
        self.file_list.itemSelectionChanged.connect(self.update_source_encoding_display)
        file_list_layout.addWidget(self.file_list)
        
        # 创建按钮
        buttons = [
            ("添加文件", self.add_files),
            ("添加文件夹", self.add_folder),
            ("移除选中", self.remove_selected_files),
            ("清空列表", self.clear_file_list),
            ("上移选中", self.move_selected_up),
            ("下移选中", self.move_selected_down)
        ]
        
        button_layout = QHBoxLayout()
        for text, callback in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            button_layout.addWidget(btn)
        
        file_list_layout.addLayout(button_layout)
        file_list_group.setLayout(file_list_layout)
        layout.addWidget(file_list_group)
        
        return layout
    
    def create_function_section(self):
        layout = QVBoxLayout()
        
        # 输出设置
        layout.addWidget(self.create_output_settings())
        
        # 重命名选项卡
        layout.addWidget(self.create_rename_section())
        
        # 编码转换功能
        layout.addWidget(self.create_encoding_section())
        
        # 导出文件名功能
        layout.addWidget(self.create_export_section())
        
        # 日志区域
        layout.addWidget(self.create_log_section())
        
        return layout
    
    def create_output_settings(self):
        group = QGroupBox("输出设置")
        layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("修改模式:"))
        self.modify_directly = QCheckBox("直接修改源文件")
        self.modify_directly.setChecked(True)
        self.modify_directly.stateChanged.connect(self.toggle_modify_mode)
        mode_layout.addWidget(self.modify_directly)
        layout.addLayout(mode_layout)
        
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(QLabel("输出文件夹:"))
        self.output_dir_edit = QLineEdit("output")
        self.output_dir_edit.setEnabled(False)
        output_dir_layout.addWidget(self.output_dir_edit)
        
        self.select_output_dir_btn = QPushButton("选择...")
        self.select_output_dir_btn.setEnabled(False)
        self.select_output_dir_btn.clicked.connect(self.select_output_directory)
        output_dir_layout.addWidget(self.select_output_dir_btn)
        
        layout.addLayout(output_dir_layout)
        group.setLayout(layout)
        return group
    
    def create_rename_section(self):
        group = QGroupBox("批量重命名")
        layout = QVBoxLayout()
        
        rename_tabs = QTabWidget()
        
        # 关键字替换选项卡
        self.replace_tab = self.create_replace_tab()
        rename_tabs.addTab(self.replace_tab, "关键字替换")
        
        # 添加前缀/后缀选项卡
        self.affix_tab = self.create_affix_tab()
        rename_tabs.addTab(self.affix_tab, "添加前缀/后缀")
        
        # 删除前缀/后缀选项卡
        self.remove_affix_tab = self.create_remove_affix_tab()
        rename_tabs.addTab(self.remove_affix_tab, "删除前缀/后缀")
        
        # 序号重命名选项卡
        self.sequence_tab = self.create_sequence_tab()
        rename_tabs.addTab(self.sequence_tab, "序号重命名")
        
        layout.addWidget(rename_tabs)
        group.setLayout(layout)
        return group
    
    def create_replace_tab(self):
        tab = BaseRenameTab()
        tab.add_field("查找:", "find_text")
        tab.add_field("替换为:", "replace_text")
        tab.add_button("预览", lambda: self.preview_rename("replace"))
        tab.add_button("执行替换", lambda: self.rename_files("replace"))
        return tab
    
    def create_affix_tab(self):
        tab = BaseRenameTab()
        tab.add_field("前缀:", "prefix_text")
        tab.add_field("后缀:", "suffix_text")
        tab.add_button("预览", lambda: self.preview_rename("affix"))
        tab.add_button("添加前缀/后缀", lambda: self.rename_files("affix"))
        return tab
    
    def create_remove_affix_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        remove_options_layout = QHBoxLayout()
        remove_options_layout.addWidget(QLabel("删除类型:"))
        
        # 将控件添加到选项卡对象，而不是self
        tab.remove_prefix_radio = QRadioButton("前缀")
        tab.remove_prefix_radio.setChecked(True)
        tab.remove_suffix_radio = QRadioButton("后缀")
        
        remove_type_group = QButtonGroup()
        remove_type_group.addButton(tab.remove_prefix_radio)
        remove_type_group.addButton(tab.remove_suffix_radio)
        
        remove_options_layout.addWidget(tab.remove_prefix_radio)
        remove_options_layout.addWidget(tab.remove_suffix_radio)
        remove_options_layout.addStretch()
        
        layout.addLayout(remove_options_layout)
        
        remove_count_layout = QHBoxLayout()
        remove_count_layout.addWidget(QLabel("删除字符个数:"))
        tab.remove_count = QSpinBox()
        tab.remove_count.setMinimum(1)
        tab.remove_count.setMaximum(100)
        tab.remove_count.setValue(1)
        remove_count_layout.addWidget(tab.remove_count)
        
        layout.addLayout(remove_count_layout)
        
        tab.remove_affix_preview_btn = QPushButton("预览")
        tab.remove_affix_preview_btn.clicked.connect(lambda: self.preview_rename("remove_affix"))
        layout.addWidget(tab.remove_affix_preview_btn)
        
        tab.remove_affix_btn = QPushButton("删除前缀/后缀")
        tab.remove_affix_btn.clicked.connect(lambda: self.rename_files("remove_affix"))
        layout.addWidget(tab.remove_affix_btn)
        
        return tab
    
    def create_sequence_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        sequence_options_layout = QHBoxLayout()
        sequence_options_layout.addWidget(QLabel("起始序号:"))
        
        # 将控件添加到选项卡对象，而不是self
        tab.start_number = QSpinBox()
        tab.start_number.setMinimum(1)
        tab.start_number.setValue(1)
        sequence_options_layout.addWidget(tab.start_number)
        
        sequence_options_layout.addWidget(QLabel("位数:"))
        tab.digit_count = QSpinBox()
        tab.digit_count.setMinimum(1)
        tab.digit_count.setMaximum(10)
        tab.digit_count.setValue(3)
        sequence_options_layout.addWidget(tab.digit_count)
        
        layout.addLayout(sequence_options_layout)
        
        # 序号重命名模式选择
        sequence_mode_layout = QHBoxLayout()
        sequence_mode_layout.addWidget(QLabel("序号模式:"))
        tab.sequence_append_radio = QRadioButton("追加序号")
        tab.sequence_append_radio.setChecked(True)
        tab.sequence_replace_radio = QRadioButton("替换名称")
        
        sequence_mode_group = QButtonGroup()
        sequence_mode_group.addButton(tab.sequence_append_radio)
        sequence_mode_group.addButton(tab.sequence_replace_radio)
        
        sequence_mode_layout.addWidget(tab.sequence_append_radio)
        sequence_mode_layout.addWidget(tab.sequence_replace_radio)
        sequence_mode_layout.addStretch()
        
        layout.addLayout(sequence_mode_layout)
        
        tab.sequence_preview_btn = QPushButton("预览")
        tab.sequence_preview_btn.clicked.connect(lambda: self.preview_rename("sequence"))
        layout.addWidget(tab.sequence_preview_btn)
        
        tab.sequence_btn = QPushButton("序号重命名")
        tab.sequence_btn.clicked.connect(lambda: self.rename_files("sequence"))
        layout.addWidget(tab.sequence_btn)
        
        return tab
    
    def create_encoding_section(self):
        group = QGroupBox("编码转换")
        layout = QVBoxLayout()
        
        auto_detect_layout = QHBoxLayout()
        self.auto_detect_encoding = QCheckBox("自动检测源编码")
        self.auto_detect_encoding.setChecked(True)
        self.auto_detect_encoding.stateChanged.connect(self.toggle_auto_detect)
        auto_detect_layout.addWidget(self.auto_detect_encoding)
        layout.addLayout(auto_detect_layout)
        
        encoding_options_layout = QHBoxLayout()
        encoding_options_layout.addWidget(QLabel("源编码:"))
        self.source_encoding = QComboBox()
        self.source_encoding.addItems(["utf-8", "utf-8-sig", "gbk", "gb2312", "ascii", "latin-1", "utf-16", "utf-16-le", "utf-16-be"])
        self.source_encoding.setEnabled(False)
        encoding_options_layout.addWidget(self.source_encoding)
        
        encoding_options_layout.addWidget(QLabel("目标编码:"))
        self.target_encoding = QComboBox()
        self.target_encoding.addItems(["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "gbk", "ascii"])
        encoding_options_layout.addWidget(self.target_encoding)
        
        layout.addLayout(encoding_options_layout)
        
        self.convert_preview_btn = QPushButton("预览")
        self.convert_preview_btn.clicked.connect(self.preview_encoding)
        layout.addWidget(self.convert_preview_btn)
        
        self.convert_encoding_btn = QPushButton("转换编码")
        self.convert_encoding_btn.clicked.connect(self.convert_encoding)
        layout.addWidget(self.convert_encoding_btn)
        
        group.setLayout(layout)
        return group
    
    def create_export_section(self):
        group = QGroupBox("导出文件名")
        layout = QVBoxLayout()
        
        export_options_layout = QHBoxLayout()
        export_options_layout.addWidget(QLabel("导出文件名:"))
        self.export_filename = QLineEdit("page.txt")
        export_options_layout.addWidget(self.export_filename)
        
        export_encoding_layout = QHBoxLayout()
        export_encoding_layout.addWidget(QLabel("导出编码:"))
        self.export_encoding = QComboBox()
        self.export_encoding.addItems(["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "gbk", "ascii"])
        self.export_encoding.setCurrentText("utf-8")
        export_encoding_layout.addWidget(self.export_encoding)
        
        layout.addLayout(export_options_layout)
        layout.addLayout(export_encoding_layout)
        
        self.export_btn = QPushButton("导出文件名")
        self.export_btn.clicked.connect(self.export_filenames)
        layout.addWidget(self.export_btn)
        
        group.setLayout(layout)
        return group
    
    def create_log_section(self):
        group = QGroupBox("操作日志")
        layout = QVBoxLayout()
        
        log_toolbar = QHBoxLayout()
        log_toolbar.addWidget(QLabel("操作日志:"))
        log_toolbar.addStretch()
        self.clear_log_btn = QPushButton("清除日志")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_toolbar.addWidget(self.clear_log_btn)
        layout.addLayout(log_toolbar)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        group.setLayout(layout)
        return group
    
    def toggle_modify_mode(self, state):
        enabled = state != Qt.CheckState.Checked.value
        self.output_dir_edit.setEnabled(enabled)
        self.select_output_dir_btn.setEnabled(enabled)
        mode = "输出到新文件夹" if enabled else "直接修改源文件"
        self.log_text.append(f"已切换到{mode}模式")
    
    def toggle_auto_detect(self, state):
        enabled = state != Qt.CheckState.Checked.value
        self.source_encoding.setEnabled(enabled)
        mode = "手动指定" if enabled else "自动检测"
        self.log_text.append(f"编码检测模式: {mode}")
    
    def update_source_encoding_display(self):
        if self.auto_detect_encoding.isChecked() and self.file_list.selectedItems():
            file_name = self.file_list.selectedItems()[0].text()
            encoding = self.file_list.get_file_encoding(file_name)
            self.source_encoding.setCurrentText(encoding)
    
    def select_output_directory(self):
        if directory := QFileDialog.getExistingDirectory(self, "选择输出目录"):
            self.output_dir_edit.setText(directory)
            self.log_text.append(f"设置输出目录为: {directory}")
    
    def clear_log(self):
        self.log_text.clear()
        self.log_text.append("日志已清除")
    
    def add_files(self):
        if files := QFileDialog.getOpenFileNames(self, "选择文件", "", "文本文件 (*.txt);;所有文件 (*.*)")[0]:
            for file in files:
                self.file_list.add_file(file)
            self.log_text.append(f"添加了 {len(files)} 个文件")
    
    def add_folder(self):
        if folder := QFileDialog.getExistingDirectory(self, "选择文件夹"):
            self.file_list.find_txt_files_in_folder(folder)
            self.log_text.append(f"添加了文件夹: {folder}")
    
    def remove_selected_files(self):
        if not (selected_items := self.file_list.selectedItems()):
            QMessageBox.warning(self, "警告", "请先选择要移除的文件")
            return
        
        for item in selected_items:
            file_name = item.text()
            self.file_list.takeItem(self.file_list.row(item))
            self.file_list.full_paths.pop(file_name, None)
            self.file_list.file_encodings.pop(file_name, None)
        self.log_text.append(f"移除了 {len(selected_items)} 个文件")
    
    def move_selected_up(self):
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要移动的文件")
            return
        
        # 获取所有选中项的行号并排序
        rows = sorted([self.file_list.row(item) for item in selected_items])
        
        # 如果第一项已经在最上面，无法上移
        if rows[0] == 0:
            return
        
        # 移动选中项
        for row in rows:
            if row > 0:
                item = self.file_list.takeItem(row)
                self.file_list.insertItem(row - 1, item)
                item.setSelected(True)
        
        self.log_text.append(f"已将 {len(selected_items)} 个文件上移")
    
    def move_selected_down(self):
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要移动的文件")
            return
        
        # 获取所有选中项的行号并排序（从大到小）
        rows = sorted([self.file_list.row(item) for item in selected_items], reverse=True)
        
        # 如果最后一项已经在最下面，无法下移
        if rows[0] == self.file_list.count() - 1:
            return
        
        # 移动选中项
        for row in rows:
            if row < self.file_list.count() - 1:
                item = self.file_list.takeItem(row)
                self.file_list.insertItem(row + 1, item)
                item.setSelected(True)
        
        self.log_text.append(f"已将 {len(selected_items)} 个文件下移")
    
    def clear_file_list(self):
        self.file_list.clear()
        self.file_list.full_paths.clear()
        self.file_list.file_encodings.clear()
        self.log_text.append("已清空文件列表")
    
    def get_files_to_process(self):
        """根据选择返回要处理的文件列表"""
        selected_files = self.file_list.get_selected_files()
        return selected_files if selected_files else self.file_list.get_all_files() or self.show_warning("文件列表为空")
    
    def show_warning(self, message):
        QMessageBox.warning(self, "警告", message)
        return None
    
    def get_output_path(self, original_path):
        if self.modify_directly.isChecked():
            return original_path
        
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            self.show_warning("请先设置输出文件夹")
            return None
        
        os.makedirs(output_dir, exist_ok=True)
        original_file = Path(original_path)
        output_path = Path(output_dir) / original_file.name
        
        counter = 1
        while output_path.exists():
            name_parts = original_file.stem.split('_')
            if name_parts and name_parts[-1].isdigit():
                name_parts[-1] = str(int(name_parts[-1]) + 1)
                new_name = '_'.join(name_parts) + original_file.suffix
            else:
                new_name = f"{original_file.stem}_{counter}{original_file.suffix}"
            
            output_path = Path(output_dir) / new_name
            counter += 1
        
        return str(output_path)
    
    def handle_file_conflict(self, file_path, new_name):
        """处理文件冲突，返回是否继续操作"""
        if self.file_conflict_policy:
            return self.file_conflict_policy
        
        # 检查目标文件是否已存在
        if self.modify_directly.isChecked():
            # 直接修改模式：检查新文件名是否已存在
            original_path = Path(file_path)
            new_path = original_path.parent / new_name
            if new_path.exists() and new_path != original_path:
                return self.show_conflict_dialog(new_name)
        else:
            # 输出到新文件夹模式：检查输出文件是否已存在
            output_dir = self.output_dir_edit.text().strip()
            if output_dir:
                output_path = Path(output_dir) / new_name
                if output_path.exists():
                    return self.show_conflict_dialog(new_name)
        
        return "continue"
    
    def show_conflict_dialog(self, file_name):
        dialog = FileConflictDialog(file_name, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result, apply_to_all = dialog.get_result()
            if apply_to_all:
                self.file_conflict_policy = result
            
            if result in ["yes", "yes_to_all"]:
                return "replace"
            elif result in ["no", "no_to_all"]:
                return "skip"
            else:  # cancel
                return "cancel"
        else:
            return "cancel"
    
    def preview_encoding(self):
        files = self.get_files_to_process()
        if not files:
            return
        
        source_enc = "自动检测" if self.auto_detect_encoding.isChecked() else self.source_encoding.currentText()
        target_enc = self.target_encoding.currentText()
        
        changes = [(file['name'], f"{file['name']} (编码: {source_enc} → {target_enc})") for file in files]
        
        preview_dialog = PreviewDialog(changes, self)
        if preview_dialog.exec() == QDialog.DialogCode.Accepted:
            self.convert_encoding()
    
    def convert_encoding(self):
        files = self.get_files_to_process()
        if not files:
            return
        
        # 重置文件冲突策略
        self.file_conflict_policy = None
        
        target_enc = self.target_encoding.currentText()
        success_count = 0
        canceled = False
        
        for file in files:
            if canceled:
                break
                
            file_name = file['name']
            file_path = file['path']
            if not (output_path := self.get_output_path(file_path)):
                return
            
            # 检查文件冲突
            conflict_action = self.handle_file_conflict(file_path, Path(output_path).name)
            if conflict_action == "cancel":
                canceled = True
                break
            elif conflict_action == "skip":
                self.log_text.append(f"跳过文件: {file_name}")
                continue
            
            if self.auto_detect_encoding.isChecked():
                source_enc = file['encoding']
                self.log_text.append(f"检测到文件 {file_name} 的编码: {source_enc}")
            else:
                source_enc = self.source_encoding.currentText()
            
            try:
                if source_enc.startswith('utf-16'):
                    with open(file_path, 'rb') as f:
                        content_bytes = f.read()
                    
                    actual_encoding = 'utf-16-be' if content_bytes.startswith(codecs.BOM_UTF16_BE) else \
                                     'utf-16-le' if content_bytes.startswith(codecs.BOM_UTF16_LE) else source_enc
                    
                    content = content_bytes.decode(actual_encoding)
                else:
                    with open(file_path, 'r', encoding=source_enc, errors='ignore') as f:
                        content = f.read()
                
                if target_enc.startswith('utf-16'):
                    with open(output_path, 'wb') as f:
                        if target_enc == 'utf-16-be':
                            f.write(codecs.BOM_UTF16_BE)
                        elif target_enc in ['utf-16-le', 'utf-16']:
                            f.write(codecs.BOM_UTF16_LE)
                            if target_enc == 'utf-16':
                                target_enc = 'utf-16-le'
                        
                        f.write(content.encode(target_enc))
                else:
                    with open(output_path, 'w', encoding=target_enc, errors='ignore') as f:
                        f.write(content)
                
                if self.modify_directly.isChecked():
                    self.file_list.update_file_name(file_name, file_name, output_path)
                
                success_count += 1
                self.log_text.append(f"转换成功: {file_path} -> {output_path}")
            except Exception as e:
                self.log_text.append(f"转换失败 {file_path}: {str(e)}")
        
        if not canceled:
            QMessageBox.information(self, "完成", f"编码转换完成，成功 {success_count} 个文件")
    
    def preview_rename(self, rename_type):
        files = self.get_files_to_process()
        if not files:
            return
        
        changes = []
        
        if rename_type == "replace":
            # 通过选项卡引用访问UI元素
            find_str = self.replace_tab.find_text.text()
            if not find_str:
                self.show_warning("请输入要查找的文本")
                return
            
            replace_str = self.replace_tab.replace_text.text()
            for file in files:
                file_name = file['name']
                changes.append((file_name, file_name.replace(find_str, replace_str)))
        
        elif rename_type == "affix":
            # 通过选项卡引用访问UI元素
            prefix = self.affix_tab.prefix_text.text()
            suffix = self.affix_tab.suffix_text.text()
            
            if not prefix and not suffix:
                self.show_warning("请至少输入前缀或后缀")
                return
            
            for file in files:
                file_name = file['name']
                name_parts = os.path.splitext(file_name)
                changes.append((file_name, f"{prefix}{name_parts[0]}{suffix}{name_parts[1]}"))
        
        elif rename_type == "remove_affix":
            # 通过选项卡引用访问UI元素
            remove_count = self.remove_affix_tab.remove_count.value()
            
            for file in files:
                file_name = file['name']
                name_parts = os.path.splitext(file_name)
                
                if self.remove_affix_tab.remove_prefix_radio.isChecked():
                    # 删除前缀字符
                    if len(name_parts[0]) > remove_count:
                        new_name = f"{name_parts[0][remove_count:]}{name_parts[1]}"
                    else:
                        new_name = name_parts[1]  # 如果文件名长度不足，只保留扩展名
                else:
                    # 删除后缀字符
                    if len(name_parts[0]) > remove_count:
                        new_name = f"{name_parts[0][:-remove_count]}{name_parts[1]}"
                    else:
                        new_name = name_parts[1]  # 如果文件名长度不足，只保留扩展名
                
                changes.append((file_name, new_name))
        
        elif rename_type == "sequence":
            # 通过选项卡引用访问UI元素
            start_num = self.sequence_tab.start_number.value()
            digits = self.sequence_tab.digit_count.value()
            
            for i, file in enumerate(files):
                file_name = file['name']
                seq_num = start_num + i
                seq_str = f"{seq_num:0{digits}d}"
                name_parts = os.path.splitext(file_name)
                
                if self.sequence_tab.sequence_replace_radio.isChecked():
                    # 替换模式：完全用序号替换原始名称
                    new_name = f"{seq_str}{name_parts[1]}"
                else:
                    # 追加模式：在原始名称后追加序号
                    new_name = f"{name_parts[0]}_{seq_str}{name_parts[1]}"
                
                changes.append((file_name, new_name))
        
        preview_dialog = PreviewDialog(changes, self)
        if preview_dialog.exec() == QDialog.DialogCode.Accepted:
            self.rename_files(rename_type)
    
    def rename_files(self, rename_type):
        files = self.get_files_to_process()
        if not files:
            return
        
        # 重置文件冲突策略
        self.file_conflict_policy = None
        
        success_count = 0
        canceled = False
        
        rename_operations = {
            "replace": self._rename_replace,
            "affix": self._rename_affix,
            "remove_affix": self._rename_remove_affix,
            "sequence": self._rename_sequence
        }
        
        if rename_type in rename_operations:
            success_count, canceled = rename_operations[rename_type](files)
        
        if not canceled:
            QMessageBox.information(self, "完成", f"重命名完成，成功 {success_count} 个文件")
    
    def _rename_replace(self, files):
        # 通过选项卡引用访问UI元素
        find_str = self.replace_tab.find_text.text()
        if not find_str:
            self.show_warning("请输入要查找的文本")
            return 0, False
        
        replace_str = self.replace_tab.replace_text.text()
        return self._process_rename_operation(files, lambda f: f.replace(find_str, replace_str))
    
    def _rename_affix(self, files):
        # 通过选项卡引用访问UI元素
        prefix = self.affix_tab.prefix_text.text()
        suffix = self.affix_tab.suffix_text.text()
        
        if not prefix and not suffix:
            self.show_warning("请至少输入前缀或后缀")
            return 0, False
        
        return self._process_rename_operation(files, lambda f: f"{prefix}{os.path.splitext(f)[0]}{suffix}{os.path.splitext(f)[1]}")
    
    def _rename_remove_affix(self, files):
        # 通过选项卡引用访问UI元素
        remove_count = self.remove_affix_tab.remove_count.value()
        
        def remove_affix_func(file_name):
            name_parts = os.path.splitext(file_name)
            if self.remove_affix_tab.remove_prefix_radio.isChecked():
                return f"{name_parts[0][remove_count:]}{name_parts[1]}" if len(name_parts[0]) > remove_count else name_parts[1]
            else:
                return f"{name_parts[0][:-remove_count]}{name_parts[1]}" if len(name_parts[0]) > remove_count else name_parts[1]
        
        return self._process_rename_operation(files, remove_affix_func)
    
    def _rename_sequence(self, files):
        # 通过选项卡引用访问UI元素
        start_num = self.sequence_tab.start_number.value()
        digits = self.sequence_tab.digit_count.value()
        
        def sequence_func(file_name, i):
            seq_num = start_num + i
            seq_str = f"{seq_num:0{digits}d}"
            name_parts = os.path.splitext(file_name)
            
            if self.sequence_tab.sequence_replace_radio.isChecked():
                return f"{seq_str}{name_parts[1]}"
            else:
                return f"{name_parts[0]}_{seq_str}{name_parts[1]}"
        
        return self._process_rename_operation(files, sequence_func, with_index=True)
    
    def _process_rename_operation(self, files, name_func, with_index=False):
        success_count = 0
        canceled = False
        
        for i, file in enumerate(files):
            if canceled:
                break
                
            file_name = file['name']
            file_path = file['path']
            if not (output_path := self.get_output_path(file_path)):
                return success_count, canceled
            
            new_name = name_func(file_name, i) if with_index else name_func(file_name)
            
            # 检查文件冲突
            conflict_action = self.handle_file_conflict(file_path, new_name)
            if conflict_action == "cancel":
                canceled = True
                break
            elif conflict_action == "skip":
                self.log_text.append(f"跳过文件: {file_name}")
                continue
            
            success_count += self.process_rename(file_name, file_path, output_path, new_name, conflict_action == "replace")
        
        return success_count, canceled
    
    def process_rename(self, file_name, file_path, output_path, new_name, overwrite=False):
        try:
            if self.modify_directly.isChecked():
                path_obj = Path(file_path)
                new_path = path_obj.parent / new_name
                
                # 如果目标文件已存在且需要覆盖，先删除它
                if overwrite and new_path.exists() and new_path != path_obj:
                    os.remove(new_path)
                
                path_obj.rename(new_path)
                self.file_list.update_file_name(file_name, new_name, str(new_path))
            else:
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # 如果目标文件已存在且需要覆盖，先删除它
                if overwrite and os.path.exists(output_path):
                    os.remove(output_path)
                
                shutil.copy2(file_path, output_path)
                
                output_path_obj = Path(output_path)
                new_output_path = output_path_obj.parent / new_name
                
                # 如果目标文件已存在且需要覆盖，先删除它
                if overwrite and new_output_path.exists() and new_output_path != output_path_obj:
                    os.remove(new_output_path)
                
                output_path_obj.rename(new_output_path)
                
                # 在输出到新文件夹模式下，不更新文件列表中的文件路径
                # 只记录操作日志
                self.log_text.append(f"复制并重命名: {file_name} -> {new_name} (输出到: {new_output_path})")
            
            self.log_text.append(f"重命名成功: {file_name} -> {new_name}")
            return 1
        except Exception as e:
            self.log_text.append(f"重命名失败 {file_path}: {str(e)}")
            return 0
    
    def export_filenames(self):
        files = self.get_files_to_process()
        if not files:
            return
        
        if not (export_filename := self.export_filename.text().strip()):
            self.show_warning("请输入导出文件名")
            return
        
        export_enc = self.export_encoding.currentText()
        
        if self.modify_directly.isChecked():
            export_path = export_filename
        else:
            if not (output_dir := self.output_dir_edit.text().strip()):
                self.show_warning("请先设置输出文件夹")
                return
            
            os.makedirs(output_dir, exist_ok=True)
            export_path = os.path.join(output_dir, export_filename)
        
        # 检查文件冲突
        if os.path.exists(export_path):
            dialog = FileConflictDialog(export_filename, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                result, apply_to_all = dialog.get_result()
                if result in ["no", "no_to_all", "cancel"]:
                    self.log_text.append("导出操作已取消")
                    return
        
        try:
            # 获取所有文件名并用逗号分隔
            filenames = [file['name'] for file in files]
            content = ','.join(filenames)
            
            if export_enc.startswith('utf-16'):
                with open(export_path, 'wb') as f:
                    if export_enc == 'utf-16-be':
                        f.write(codecs.BOM_UTF16_BE)
                    elif export_enc in ['utf-16-le', 'utf-16']:
                        f.write(codecs.BOM_UTF16_LE)
                        if export_enc == 'utf-16':
                            export_enc = 'utf-16-le'
                    
                    f.write(content.encode(export_enc))
            else:
                with open(export_path, 'w', encoding=export_enc) as f:
                    f.write(content)
            
            self.log_text.append(f"文件名已导出到: {export_path} (编码: {export_enc})")
            QMessageBox.information(self, "完成", f"文件名已导出到 {export_path} (编码: {export_enc})")
        except Exception as e:
            self.log_text.append(f"导出失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = FileProcessorApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()