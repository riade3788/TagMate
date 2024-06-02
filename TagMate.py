import os
import json
import logging
import tkinter as tk
import ttkthemes


from tkinter import filedialog, messagebox, simpledialog, ttk
from shutil import move, rmtree, copy2, copyfile

# Setup logging
logging.basicConfig(filename='tagmate2.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

CONFIG_FILE = 'tagmate2_config.json'
CHANGE_LOG_FILE = 'tagmate2_changes.json'

# Log actions
def log_action(action):
    logging.info(action)
    print(action)  # Print to console for real-time feedback

# Parse .civitai.info file
def parse_info_file(info_path):
    with open(info_path, 'r', encoding='utf-8') as info_file:
        data = json.load(info_file)
     
        return data


# Parse .json file
def parse_json_file(json_path):
    with open(json_path, 'r', encoding='utf-8') as json_file:
        return json.load(json_file)

# Find related files
def find_related_files(directory, base_name):
    extensions = ['.safetensors', '.ckpt', '.pt', '.bin']
    related_files = {}

    for ext in extensions:
        model_path = os.path.join(directory, base_name + ext)
        if os.path.exists(model_path):
            related_files['model'] = model_path

    info_path = os.path.join(directory, base_name + '.civitai.info')
    if os.path.exists(info_path):
        related_files['info'] = info_path

    json_path = os.path.join(directory, base_name + '.json')
    if os.path.exists(json_path):
        related_files['json'] = json_path

    preview_path = os.path.join(directory, base_name + '.preview.png')
    if os.path.exists(preview_path):
        related_files['preview'] = preview_path

    return related_files

# Sanitize folder names
def sanitize_folder_name(name):
    return "".join(c for c in name if c.isalnum() or c in "._- ")

def rename_file(directory, old_name, new_name):
    old_path = os.path.join(directory, old_name)
    print(f"Old Path: {old_path}")

    # Split the file name and extension
    base, ext = os.path.splitext(old_name)

    # Construct the new file name with the extension
    new_name_with_ext = new_name + ext
    print(f"New name with extension: {new_name_with_ext}")

    new_path = os.path.join(directory, new_name_with_ext)
    print(f"New Path: {new_path}")

    if os.path.exists(new_path):
        base, ext = os.path.splitext(new_name_with_ext)
        counter = 1
        while os.path.exists(new_path):
            new_path = os.path.join(directory, f"{base}_{counter}{ext}")
            print(f"Conflict detected, new path: {new_path}")
            counter += 1

    os.rename(old_path, new_path)
    print(f"Renamed {old_name} to {new_name_with_ext}")
    log_action(f"Renamed {old_name} to {new_name_with_ext}")
    return new_path




# Move file with retry and tracking
def move_file_with_retry(src, dest, changes):
    try:
        move(src, dest)
        changes.append({'src': src, 'dest': dest})
        log_action(f"Moved {src} to {dest}")
    except Exception as e:
        log_action(f"Failed to move {src} to {dest}: {e}")

# Get subfolder name based on tags
def get_subfolder_name(info_data, tags_list, concatenate_tags):
    matched_tags = []

    # Check if 'tags' key exists in 'model' dictionary
    if 'tags' in info_data['model']:
        info_tags = info_data['model']['tags']
    else:
        info_tags = []

    for default_tag in tags_list:
        for info_tag in info_tags:
            if default_tag.lower() == info_tag.lower():
                matched_tags.append(default_tag)

    if concatenate_tags:
        return "_".join(matched_tags)
    else:
        return matched_tags[0] if matched_tags else "Uncategorized"



# Delete empty folders
def delete_empty_folders(folder_path):
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
                log_action(f"Deleted empty folder {dir_path}")

# Categorize files and track changes
def categorize_files(input_dir, output_dir, tags_list, concatenate_tags, rename_files, model_type_first, nsfw_status_second, use_sd_version_third, sd_version_or_base_model, changes):
    processed_count = 0
    model_names_seen = set()
    for file_name in os.listdir(input_dir):
        if file_name.endswith('.civitai.info'):
            base_name = file_name.replace('.civitai.info', '')
            related_files = find_related_files(input_dir, base_name)

            if 'info' in related_files:
                info_data = parse_info_file(related_files['info'])
                model_name = sanitize_folder_name(info_data['model']['name'])

                # Handle duplicate model names
                original_model_name = model_name
                counter = 1
                while model_name in model_names_seen:
                    model_name = f"{original_model_name}_{counter}"
                    counter += 1
                model_names_seen.add(model_name)

                model_type = sanitize_folder_name(info_data['model']['type'])
                nsfw_status = 'NSFW' if info_data['model']['nsfw'] else 'SFW'
                base_model = sanitize_folder_name(info_data['baseModel'])

                if 'json' in related_files:
                    json_data = parse_json_file(related_files['json'])
                    sd_version = sanitize_folder_name(json_data.get('sd_version', base_model))

                if model_type_first:
                    first_level = model_type
                    second_level = nsfw_status if nsfw_status_second else None
                    third_level = sd_version if use_sd_version_third and sd_version_or_base_model == "sd_version" else base_model if use_sd_version_third else None
                else:
                    first_level = nsfw_status if nsfw_status_second else None
                    second_level = sd_version if use_sd_version_third and sd_version_or_base_model == "sd_version" else base_model if use_sd_version_third else None
                    third_level = None

                if first_level:
                    subfolder = os.path.join(output_dir, first_level)
                else:
                    subfolder = output_dir
                if second_level:
                    subfolder = os.path.join(subfolder, second_level)
                if third_level:
                    subfolder = os.path.join(subfolder, third_level)

                os.makedirs(subfolder, exist_ok=True)

                tag_folder = sanitize_folder_name(get_subfolder_name(info_data, tags_list, concatenate_tags))
                subfolder = os.path.join(subfolder, tag_folder)
                os.makedirs(subfolder, exist_ok=True)

                for key, file_path in related_files.items():
                    new_name = model_name
                    if rename_files:
                        if key == 'info':
                            new_name = f"{model_name}.civitai.info"
                        elif key == 'preview':
                            new_name = f"{model_name}.preview.png"
                        else:
                            new_name = f"{model_name}{os.path.splitext(file_path)[1]}"
                        
                        new_file_path = os.path.join(subfolder, new_name)
                    else:
                        new_file_path = os.path.join(subfolder, os.path.basename(file_path))

                    move_file_with_retry(file_path, new_file_path, changes)

                processed_count += 1
                log_action(f"Processed {base_name}")
    return processed_count




# Save configuration to file
def save_config(config):
    with open(CONFIG_FILE, 'w') as config_file:
        json.dump(config, config_file)

# Load configuration from file
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as config_file:
            return json.load(config_file)
    return {}

# Save changes log
def save_changes_log(changes):
    with open(CHANGE_LOG_FILE, 'w') as change_log_file:
        json.dump(changes, change_log_file)

# Load changes log
def load_changes_log():
    if os.path.exists(CHANGE_LOG_FILE):
        with open(CHANGE_LOG_FILE, 'r') as change_log_file:
            return json.load(change_log_file)
    return []

# Rollback changes and delete empty folders
def rollback_changes(changes, output_dir):
    for change in reversed(changes):
        src = change['dest']
        dest = change['src']
        try:
            move(src, dest)
            log_action(f"Rolled back move from {src} to {dest}")
        except FileNotFoundError:
            log_action(f"File not found during rollback: {src}")
        except Exception as e:
            log_action(f"Error during rollback: {e}")
    delete_empty_folders(output_dir)

# GUI Application Class
class TagMateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TagMate 2")
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('TButton', font=('Helvetica', 10), padding=5)
        style.configure('TLabel', font=('Helvetica', 10))
        style.configure('TCheckbutton', font=('Helvetica', 10))
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.concatenate_tags = tk.BooleanVar()
        self.rename_files = tk.BooleanVar()
        self.model_type_first = tk.BooleanVar()
        self.nsfw_status_second = tk.BooleanVar()
        self.use_sd_version_third = tk.BooleanVar()
        self.sd_version_or_base_model = tk.StringVar()
        self.tags_list = ["Character", "Concept", "Style", "Celebrity", "Clothing", "Fashion", "Objects", "Building", "Poses", "Animal", "Action", "Vehicle", "Assets", "Tool", "Anime"]

        config = load_config()
        self.input_dir.set(config.get('input_dir', ''))
        self.output_dir.set(config.get('output_dir', ''))
        self.concatenate_tags.set(config.get('concatenate_tags', False))
        self.rename_files.set(config.get('rename_files', False))
        self.model_type_first.set(config.get('model_type_first', False))
        self.nsfw_status_second.set(config.get('nsfw_status_second', False))
        self.use_sd_version_third.set(config.get('use_sd_version_third', False))
        self.sd_version_or_base_model.set(config.get('sd_version_or_base_model', 'sd_version'))

        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10)

        ttk.Label(frame, text="Input Folder:").grid(row=0, column=0, sticky='e')
        ttk.Entry(frame, textvariable=self.input_dir, width=50).grid(row=0, column=1)
        ttk.Button(frame, text="Browse", command=self.browse_input).grid(row=0, column=2)

        ttk.Label(frame, text="Output Folder:").grid(row=1, column=0, sticky='e')
        ttk.Entry(frame, textvariable=self.output_dir, width=50).grid(row=1, column=1)
        ttk.Button(frame, text="Browse", command=self.browse_output).grid(row=1, column=2)

        ttk.Checkbutton(frame, text="Concatenate Tags", variable=self.concatenate_tags).grid(row=2, column=0, columnspan=2, sticky='w')
        ttk.Checkbutton(frame, text="Rename Files", variable=self.rename_files).grid(row=3, column=0, columnspan=2, sticky='w')
        ttk.Checkbutton(frame, text="Sort by Model Type", variable=self.model_type_first).grid(row=4, column=0, columnspan=2, sticky='w')
        ttk.Checkbutton(frame, text="Sort by NSFW Status", variable=self.nsfw_status_second).grid(row=5, column=0, columnspan=2, sticky='w')
        ttk.Checkbutton(frame, text="Sort by SD Ver/Base Model", variable=self.use_sd_version_third).grid(row=6, column=0, columnspan=2, sticky='w')

        ttk.Label(frame, text="Sorting Criteria:").grid(row=7, column=0, sticky='e')
        ttk.Combobox(frame, textvariable=self.sd_version_or_base_model, values=["sd_version", "base_model"], state="readonly").grid(row=7, column=1)

        ttk.Button(frame, text="Add Tag", command=self.add_tag).grid(row=8, column=0, sticky='e')
        ttk.Button(frame, text="Remove Tag", command=self.remove_tag).grid(row=8, column=1, sticky='w')
        ttk.Button(frame, text="Move Tag Up", command=self.move_tag_up).grid(row=9, column=0, sticky='e')
        ttk.Button(frame, text="Move Tag Down", command=self.move_tag_down).grid(row=9, column=1, sticky='w')

        self.tag_listbox = tk.Listbox(frame, height=10, selectmode=tk.SINGLE, exportselection=False)
        tag_listbox_scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tag_listbox.yview)
        self.tag_listbox.config(yscrollcommand=tag_listbox_scrollbar.set)
        self.tag_listbox.grid(row=10, column=0, columnspan=2)
        tag_listbox_scrollbar.grid(row=10, column=2, sticky='ns')
        self.update_tag_listbox()

        ttk.Button(frame, text="Start Categorization", command=self.start_categorization).grid(row=11, column=0, columnspan=3, pady=10)
        ttk.Button(frame, text="Rollback", command=self.rollback_changes).grid(row=12, column=0, columnspan=3, pady=10)

        self.status_label = ttk.Label(frame, text="Status: Idle")
        self.status_label.grid(row=13, column=0, columnspan=3)

    def browse_input(self):
        folder = filedialog.askdirectory()
        self.input_dir.set(folder)

    def browse_output(self):
        folder = filedialog.askdirectory()
        self.output_dir.set(folder)

    def update_tag_listbox(self):
        self.tag_listbox.delete(0, tk.END)
        for tag in self.tags_list:
            self.tag_listbox.insert(tk.END, tag)

    def add_tag(self):
        new_tag = simpledialog.askstring("Add Tag", "Enter new tag:")
        if new_tag:
            self.tags_list.append(new_tag)
            self.update_tag_listbox()

    def remove_tag(self):
        selected_tag_index = self.tag_listbox.curselection()
        if selected_tag_index:
            del self.tags_list[selected_tag_index[0]]
            self.update_tag_listbox()

    def move_tag_up(self):
        selected_tag_index = self.tag_listbox.curselection()
        if selected_tag_index and selected_tag_index[0] > 0:
            idx = selected_tag_index[0]
            self.tags_list[idx], self.tags_list[idx - 1] = self.tags_list[idx - 1], self.tags_list[idx]
            self.update_tag_listbox()
            self.tag_listbox.select_set(idx - 1)

    def move_tag_down(self):
        selected_tag_index = self.tag_listbox.curselection()
        if selected_tag_index and selected_tag_index[0] < len(self.tags_list) - 1:
            idx = selected_tag_index[0]
            self.tags_list[idx], self.tags_list[idx + 1] = self.tags_list[idx + 1], self.tags_list[idx]
            self.update_tag_listbox()
            self.tag_listbox.select_set(idx + 1)

    def start_categorization(self):
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()

        if not input_dir or not output_dir:
            messagebox.showerror("Error", "Please select both input and output directories.")
            return

        changes = load_changes_log()

        # Call categorize_files with the determined sorting criteria
        processed_count = categorize_files(
            input_dir, output_dir, self.tags_list,
            self.concatenate_tags.get(), self.rename_files.get(),
            self.model_type_first.get(), self.nsfw_status_second.get(),
            self.use_sd_version_third.get(), self.sd_version_or_base_model.get(),  # Pass the choice from combobox
            changes
        )

        # Save changes log
        save_changes_log(changes)

        # Save configuration
        config = {
            'input_dir': input_dir,
            'output_dir': output_dir,
            'concatenate_tags': self.concatenate_tags.get(),
            'rename_files': self.rename_files.get(),
            'model_type_first': self.model_type_first.get(),
            'nsfw_status_second': self.nsfw_status_second.get(),
            'use_sd_version_third': self.use_sd_version_third.get(),
            'sd_version_or_base_model': self.sd_version_or_base_model.get(),
        }
        save_config(config)

        self.status_label.config(text=f"Status: Categorized {processed_count} files.")

    def rollback_changes(self):
        changes = load_changes_log()
        rollback_changes(changes, self.output_dir.get())
        save_changes_log([])  # Clear changes log after rollback
        self.status_label.config(text="Status: Rollback completed")

# Main
if __name__ == "__main__":
    root = ttkthemes.themed_tk.ThemedTk(theme='azure')
    # Set the application icon using the file name
    root.iconbitmap(default='TagMate.ico')
    app = TagMateApp(root)
    root.mainloop()
