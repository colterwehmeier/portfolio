import json
import os
from collections import defaultdict
import html
import re
import urllib.parse
import subprocess
import pathlib
import PIL
from PIL import Image, ExifTags
import imageio

data = []
json_files = [pos_json for pos_json in os.listdir('entries/') if pos_json.endswith('.json')]

# For each file, open it, load the JSON data, and add it to the list
for file_name in json_files:
    with open('entries/' + file_name, 'r') as file:
        file_data = json.load(file)
        data.extend(file_data)

def compress_video_if_needed(filename, max_filesize_bytes=500000000): # Set max_filesize_bytes to your desired max size
    file_size_bytes = os.path.getsize(filename)
    if file_size_bytes > max_filesize_bytes:
        base_name = os.path.basename(filename)
        dir_name = os.path.dirname(filename)
        name_without_ext, extension = os.path.splitext(base_name)

        # compressed_base_name = "_c_" + name_without_ext + extension
        compressed_base_name = "_c_" + name_without_ext + ".mp4"
        compressed_filename = os.path.join(dir_name, compressed_base_name)

        # Check if compressed file already exists
        if not os.path.isfile(compressed_filename):
            print(f"Compressing {filename} to {compressed_filename}")
            # subprocess.run(["ffmpeg", "-i", filename, "-vf", "scale=trunc(iw/2)*2:720", "-b:v", "1M", compressed_filename])
            subprocess.run(["ffmpeg", "-i", filename, "-vf", "scale='min(720,iw)':-2", "-b:v", "1M", compressed_filename])

        return compressed_filename

    return filename
def compress_image_if_needed(filename, max_filesize):
    if pathlib.Path(filename).suffix.lower() not in [".png", ".jpg", ".jpeg"]:
        print(f"{filename} is not a recognised image file.")
        return filename
    
    # Get the filesize
    file_size = os.path.getsize(filename)
    needs_compression = file_size > max_filesize
    needs_rotation = False

    # Open the image to check EXIF for rotation info
    with Image.open(filename) as img:
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = img._getexif()
            if exif is not None and exif[orientation] in [3, 6, 8]:
                needs_rotation = True

        except (AttributeError, KeyError, IndexError):
            # Image didn't have EXIF data
            pass

    # If the file size is over the limit or needs rotation
    if needs_compression or needs_rotation:
        # Define the new filename
        compressed_filename = f"_c_{os.path.basename(filename)}"
        compressed_filename = os.path.join(os.path.dirname(filename), compressed_filename)

        # If the compressed file does not exist
        if not os.path.isfile(compressed_filename):
            # Reopen the image file
            with Image.open(filename) as img:
                # Convert the image to RGB (removes alpha if present)
                img = img.convert('RGB')
                
                # Rotate image if needed
                if needs_rotation:
                    print(exif[orientation])
                    if exif[orientation] == 3:
                        img = img.rotate(180, expand=True)
                    elif exif[orientation] == 6:
                        img = img.rotate(270, expand=True)
                    elif exif[orientation] == 8:
                        img = img.rotate(90, expand=True)
                
                # Save the image as a compressed JPEG
                img.save(compressed_filename, "JPEG", optimize=True, quality=85)
        
        # Return the compressed filename
        return compressed_filename

    # If neither condition is met, return the original filename
    else:
        return filename


def sort_files(file_list):
    def get_sort_key(filename):
        name = os.path.splitext(os.path.basename(filename))[0]
        components = re.findall(r'_([^_]*)_?', name)
        if components and components[0].isdigit():
            return int(components[0]), name
        else:
            return float('inf'), name

    file_list = [file for file in file_list if '_x_' not in file and '_c_' not in file]
    file_list.sort(key=get_sort_key)
    return file_list
def get_image_dimensions(image_path):
    _, extension = os.path.splitext(image_path)
    extension = extension.lower()
    
    if extension != ".gif":
        with Image.open(image_path) as img:
            return img.size  # Returns (width, height)
    else:
        img = imageio.v2.imread(image_path)
        return img.shape[1], img.shape[0]  # Returns (width, height)



def get_video_dimensions(video_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height,width", "-of", "json", video_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    dimensions = json.loads(result.stdout)['streams'][0]
    return dimensions['width'], dimensions['height']
# Organize entries by theme and year
themes = defaultdict(lambda: defaultdict(list))
existing_folders = []
existing_ids = {}
entries_without_id = []
FileListForCopyingAtTheEnd = []
for entry in data:
    # Check if the entry has a non-empty id
    if entry['id']:
        # Check if the id already exists
        if entry['id'] in existing_ids:
            print(f"Id collision detected: {entry['id']}")
        else:
            existing_ids[entry['id']] = True

        theme_list = entry['theme'].split(',')
        folder_theme = theme_list[0].strip()  # Get the first theme and remove leading and trailing whitespaces

        folder_path = os.path.join('entries', folder_theme, entry['id'])
        os.makedirs(folder_path, exist_ok=True)

        # Check for files in the folder
        file_list = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        file_list = sort_files(file_list)

        updated_file_list = []
        for index, filename in enumerate(file_list):
            if 'DS_Store' in filename or filename.endswith('.psd'):
                continue
            # Get the base filename and the directory it's in
            base_name = os.path.basename(filename)
            dir_name = os.path.dirname(filename)
            
            # Split filename and extension
            name_without_ext, extension = os.path.splitext(base_name)
            
            # Make the extension lowercase
            extension = extension.lower()
            
            # Replace non-alphanumeric and non-dash characters with '_'
            sanitized_base_name = re.sub(r'[^\w-]+', '_', name_without_ext)
            
            # Replace multiple '_' with a single '_'
            cleaned_base_name = re.sub(r'_{2,}', '_', sanitized_base_name)

            # Append the extension back to the cleaned name
            cleaned_full_name = cleaned_base_name + extension

            # Check if cleaned name is different from the original
            if base_name != cleaned_full_name:
                print(f"Proposed filename change: '{base_name}' to '{cleaned_full_name}' in directory '{dir_name}'.")
                approval = input("Do you approve this change? (y/n): ")
                if approval.lower() == 'y':
                    new_filename = os.path.join(dir_name, cleaned_full_name)
                    # print(f"Would rename {filename} to {new_filename}")
                    os.rename(filename, new_filename)
                    base_name = cleaned_full_name
                    filename = new_filename
                        
            dir_name = os.path.dirname(filename)
            extension = pathlib.Path(filename).suffix.lower()
            if extension in [".mp4", ".avi", ".mkv", ".mov"]:  # Update the list of video file extensions as needed
                filename = compress_video_if_needed(filename, 1000000)
            elif extension in [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"]:  # Update the list of image file extensions as needed
                filename = compress_image_if_needed(filename, 1000000)

            updated_file_list.append(filename)


        fixed_width_ch = 60  # Fixed width in CH units
        ch_to_pixel_ratio = 8  # CH to pixel ratio; usually 1ch = 8px but may vary
        fixed_width_px = fixed_width_ch * ch_to_pixel_ratio
        maximumHeight = 500  # Maximum height in pixels

        # List to store constrained heights
        constrained_heights = []

        # Loop through files to get dimensions and calculate constrained heights
        for filename in updated_file_list:
            extension = pathlib.Path(filename).suffix.lower()
            
            if extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"]:
                original_width, original_height = get_image_dimensions(filename)
            elif extension in [".mp4", ".avi", ".mkv", ".mov"]:
                original_width, original_height = get_video_dimensions(filename)
            elif extension in [".yt"]:
                original_width, original_height = (16,9)
            else:
                continue  # skip unhandled file types

            # Calculate normalized height if the width were fixed at 50ch
            normalized_height = (fixed_width_px / original_width) * original_height

            # Constrain the height if it exceeds the maximum allowed value
            constrained_height = min(maximumHeight, normalized_height)

            constrained_heights.append(constrained_height)

        # Calculate the maximum of the constrained heights
        if len(constrained_heights) > 0:
            max_constrained_height = round(max(constrained_heights))
        else:
            max_constrained_height = 0  # Default value


        # Now, original_widths and original_heights store the dimensions in their original pixel sizes

        entry['lightbox_max_height'] = f"{max_constrained_height}px" if max_constrained_height > 0 else "0px"
        
        # Add file paths to entry
        entry['file_paths'] = updated_file_list
        FileListForCopyingAtTheEnd.append(updated_file_list)
        # Add to existing folders
        existing_folders.append(folder_path)
    else:
        print(f"Entry without id: {entry['title']}")
        entries_without_id.append(entry)

    # If multiple themes are defined, split them and add entry to each
    theme_list = entry['theme'].split(',')
    for theme in theme_list:
        theme = theme.strip()  # Remove leading and trailing whitespaces
        themes[theme][entry['year']].append(entry)
# Check for abandoned folders
for theme in themes.keys():
    theme_path = os.path.join('entries', theme)
    all_folders_in_theme = [os.path.join(theme_path, d) for d in os.listdir(theme_path) if os.path.isdir(os.path.join(theme_path, d))]
    for folder in all_folders_in_theme:
        if folder not in existing_folders:
            print(f"Abandoned folder: {folder}")

# Initialize HTML content
html_content = ""

# Iterate through themes and years and build HTML content
for theme, years in themes.items():
    html_content += f'<div class="subgroup {theme}text">\n'

    # Sort years in descending order
    for year in sorted(years.keys(), reverse=True):
        html_content += f'<p class="year">{year}</p>\n'
        # Iterate through entries for this theme and year
        for entry in years[year]:
            entry_json = json.dumps(entry)
            entry_json_escaped = html.escape(entry_json)
            if not entry["id"]:
                entry["locked"] = True
            locked_class = "lost " if entry['locked'] else ""
            # html_content += f'<p class="title"><a target="_blank" href="{entry["id"]}" data-entry=\'{entry_json_escaped}\' class="{locked_class}subtext"><span>{entry["span"]}</span> {entry["title"]}</a></p>\n'
            tags = entry.get("tags", "")
            first_tag = tags.split(",")[0] if tags else " "
            first_tag = first_tag.replace("-", " ").replace("_", " ")
            html_content += f'<p class="title"><a target="_blank" href="#{entry["id"]}" data-entry=\'{entry_json_escaped}\' class="{locked_class}subtext"><span class="small">{first_tag}</span> {entry["title"]}</a></p>\n'

    html_content += '</div>\n'

# Write to output file
with open('output.html', 'w') as file:
    file.write(html_content)

# Print entries without id
if entries_without_id:
    print("\nEntries without defined id:")
    for entry in entries_without_id:
        print(entry['title'])

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def generate_sitemap(themes, base_url="https://colter.us/"):
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for theme, years in themes.items():
        for year, entries in years.items():
            for entry in entries:
                # Assuming the URL is based on theme, year, and a unique identifier in the entry
                if 'id' in entry and entry['id']:  # Check if 'id' exists and is not empty
                    url = base_url + "#" + urllib.parse.quote(entry['id'])
                    url_element = SubElement(urlset, "url")
                    loc = SubElement(url_element, "loc")
                    loc.text = url

    # Pretty-print the XML
    rough_string = tostring(urlset, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    return pretty_xml

# Generate the sitemap
sitemap_xml = generate_sitemap(themes)
# Write the sitemap to a file
with open("../sitemap.xml", "w") as file:
    file.write(sitemap_xml)

print("Sitemap generated successfully.")



import shutil
import os
from pathlib import Path

# Define source and target directories
source_dir = Path(__file__).parent  # Assumes this script is in the source directory
target_dir = Path('/home/colter/git/portfolio')

print("copying over files to git")

# Specific files to copy
specific_files = [
    'favicon.ico',
    'index-source.html',
    'robots.txt',
    #'output.html', <- we actually change the filenames and links later on
    'sitemap.xml',
    'style.css',
    'assets/garden_fast.mp4',
    'compile.py'
]

# Directories to copy recursively
recursive_dirs = [
    'js',
    'fonts',
    'svg'
]

# Copy specific files
for file_path in specific_files:
    full_source_path = source_dir / file_path
    full_target_path = target_dir / file_path
    full_target_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure target directory exists
    shutil.copy(full_source_path, full_target_path)

# Copy directories recursively
for dir_path in recursive_dirs:
    full_source_path = source_dir / dir_path
    full_target_path = target_dir / dir_path
    if full_target_path.exists():
        shutil.rmtree(full_target_path)  # Ensure target directory is removed before copying
    shutil.copytree(full_source_path, full_target_path, dirs_exist_ok=True)  # Copy directory tree

#have to get rid of preceeding _ for github

# Copy entries files and rename if filename starts with _

all_copied_files = [item for sublist in FileListForCopyingAtTheEnd for item in sublist]  # Flatten list
renamed_files = []  # To keep track of original and new file names for further processing


# Function to remove leading underscore from filenames in a given path
def remove_leading_underscore_from_filename(file_path):
    path_parts = Path(file_path).parts
    new_filename = path_parts[-1].lstrip("_")
    new_path = Path(*path_parts[:-1], new_filename)
    return new_path

# Iterate over all copied files and process them
for file_path in all_copied_files:
    full_source_path = source_dir / file_path
    # Generate new target path with leading underscore removed from filename
    new_file_path = remove_leading_underscore_from_filename(file_path)
    full_target_path = target_dir / new_file_path
    # Ensure target directory exists
    full_target_path.parent.mkdir(parents=True, exist_ok=True)
    # Copy file from source to target
    shutil.copy(full_source_path, full_target_path)  # Uncomment this line in actual code
    # If the file was renamed, add original and new path to the list
    if new_file_path != Path(file_path):
        renamed_files.append((str(full_source_path), str(full_target_path)))


#html and pdf files are not referenced like images and must be copied over separately
#so any child folder of entries called html or pdf must also be copied over with its contained files

entries_source_dir = Path(source_dir) / 'entries'  # Update with actual source path
entries_target_dir = Path(target_dir) / 'entries'  # Update with actual target path

print()
# Function to copy specific folders ('html' and 'pdf') to target directory
def copy_specific_folders(source, target, folder_names):
    for folder_name in folder_names:
        # Iterate through the source directory to find 'html' or 'pdf' folders
        for path in source.rglob(f'*/{folder_name}'):
            # Define the target path for this folder
            target_path = target / path.relative_to(source)
            # Copy the folder and its contents to the target directory
            shutil.copytree(path, target_path, dirs_exist_ok=True)

# Copy 'html' and 'pdf' folders and their contents
copy_specific_folders(entries_source_dir, entries_target_dir, ['html', 'pdf'])


#manual copy of output.html with file paths fixed to address github limit
# Read the 'output.html' from the source directory
source_html_path = source_dir / 'output.html'
with open(source_html_path, 'r', encoding='utf-8') as file:
    html_content = file.read()

#hack to fix file names in the html output file
html_content = re.sub(r'(?<=/)_+', '', html_content)


#retarget to github
html_content = re.sub(
    r'entries/', 
    'https://colterwehmeier.github.io/portfolio/entries/', 
    html_content
)

# Write the modified html content to the target directory
target_html_path = target_dir / 'output.html'
with open(target_html_path, 'w', encoding='utf-8') as file:
    file.write(html_content)

#
print("constructing final index.html file at target dir")
print("injecting content into source index")
# Read the 'index-source.html' file
index_source_path = source_dir / 'index-source.html'
with open(index_source_path, 'r', encoding='utf-8') as file:
    index_content = file.read()

# Read the 'output.html' file
output_html_path = target_dir / 'output.html'
with open(output_html_path, 'r', encoding='utf-8') as file:
    output_content = file.read()

# Inject the 'output.html' content into the '<div id="container"></div>' element
modified_index_content = index_content.replace('<div id="container"></div>', f'<div id="container">{output_content}</div>')

# Save the modified index content as 'index.html' in the source directory
index_html_path = source_dir / 'index.html'
with open(index_html_path, 'w', encoding='utf-8') as file:
    file.write(modified_index_content)
index_html_path = target_dir / 'index.html'
with open(index_html_path, 'w', encoding='utf-8') as file:
    file.write(modified_index_content)


print("Site export completed successfully.")
