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
import math
from collections import Counter

data = []
json_files = [pos_json for pos_json in os.listdir('entries/') if pos_json.endswith('.json')]

# For each file, open it, load the JSON data, and add it to the list
for file_name in json_files:
    with open('entries/' + file_name, 'r') as file:
        file_data = json.load(file)
        data.extend(file_data)

def process_files(file_list):
    """Updated process_files function with WebM-only video handling"""
    updated_file_list = []
    
    for filename in file_list:
        if 'DS_Store' in filename or filename.endswith('.psd'):
            continue
            
        # Get the base filename and directory
        base_name = os.path.basename(filename)
        dir_name = os.path.dirname(filename)
        
        # Clean filename
        name_without_ext, extension = os.path.splitext(base_name)
        extension = extension.lower()
        sanitized_base_name = re.sub(r'[^\w-]+', '_', name_without_ext)
        cleaned_base_name = re.sub(r'_{2,}', '_', sanitized_base_name)
        cleaned_full_name = cleaned_base_name + extension
        
        # Handle file renaming if needed
        if base_name != cleaned_full_name:
            print(f"Proposed filename change: '{base_name}' to '{cleaned_full_name}' in directory '{dir_name}'.")
            approval = input("Do you approve this change? (y/n): ")
            if approval.lower() == 'y':
                new_filename = os.path.join(dir_name, cleaned_full_name)
                os.rename(filename, new_filename)
                filename = new_filename
        
        # Handle video conversion (always convert to WebM)
        if extension in [".mp4", ".avi", ".mkv", ".mov"]:
            filename = compress_video_if_needed(filename, 1000000)
        # Handle image compression
        elif extension in [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"]:
            filename = compress_image_if_needed(filename, 1000000)
            
        updated_file_list.append(filename)
    
    # Filter out original videos if WebM versions exist
    filtered_file_list = filter_video_files(updated_file_list)
    
    return filtered_file_list


def calculate_max_height(file_list):
    """Updated to handle .webm extension"""
    fixed_width_ch = 60
    ch_to_pixel_ratio = 8
    fixed_width_px = fixed_width_ch * ch_to_pixel_ratio
    maximumHeight = 500
    
    constrained_heights = []
    for filename in file_list:
        try:
            extension = pathlib.Path(filename).suffix.lower()
            if extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"]:
                dimensions = get_image_dimensions(filename)
            elif extension in [".webm", ".mp4", ".avi", ".mkv", ".mov"]:  # Added .webm
                dimensions = get_video_dimensions(filename)
            elif extension in [".yt"]:
                dimensions = (16, 9)
            else:
                continue
                
            if dimensions:
                original_width, original_height = dimensions
                normalized_height = (fixed_width_px / original_width) * original_height
                constrained_height = min(maximumHeight, normalized_height)
                constrained_heights.append(constrained_height)
        except Exception as e:
            print(f"Error processing dimensions for {filename}: {e}")
    
    return round(max(constrained_heights)) if constrained_heights else 0

# Add this function alongside your other image/video processing functions
def generate_image_thumbnail(image_path, thumbs_base_dir, size=(400, 400)):
    """
    Creates a small, compressed thumbnail for a given image.
    """
    try:
        # Create a unique, stable filename using a hash
        hash_obj = hashlib.md5(image_path.encode())
        hash_name = hash_obj.hexdigest()
        thumb_filename = f"{hash_name}.jpg"
        
        # Define paths
        thumb_rel_path = f"static/thumbs/{thumb_filename}"
        thumb_full_path = os.path.join(thumbs_base_dir, thumb_filename)
        
        # If thumbnail doesn't already exist, create it
        if not os.path.exists(thumb_full_path):
            with Image.open(image_path) as img:
                # Handle EXIF orientation just in case
                try:
                    for orientation in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[orientation] == 'Orientation':
                            break
                    exif = img._getexif()
                    if exif and exif.get(orientation) in [3, 6, 8]:
                        if exif[orientation] == 3: img = img.rotate(180, expand=True)
                        elif exif[orientation] == 6: img = img.rotate(270, expand=True)
                        elif exif[orientation] == 8: img = img.rotate(90, expand=True)
                except (AttributeError, KeyError, IndexError):
                    pass # No EXIF data

                img = img.convert('RGB')
                img.thumbnail(size, PIL.Image.Resampling.LANCZOS)
                img.save(thumb_full_path, "JPEG", quality=80, optimize=True)
                print(f"  ✓ Generated thumbnail for {os.path.basename(image_path)}")

        return thumb_rel_path
    except Exception as e:
        print(f"  ✗ Failed to create thumbnail for {image_path}: {e}")
        return None

import hashlib
import requests
from pathlib import Path

def extract_youtube_id(yt_file_path):
    """Extract YouTube video ID from .yt file"""
    try:
        with open(yt_file_path, 'r') as f:
            content = f.read().strip()
        
        # Handle various YouTube URL formats
        video_id = ''
        if 'watch?v=' in content:
            from urllib.parse import urlparse, parse_qs
            url = urlparse(content)
            params = parse_qs(url.query)
            video_id = params.get('v', [''])[0]
        elif 'youtu.be/' in content:
            video_id = content.split('youtu.be/')[-1].split('?')[0]
        else:
            # Assume it's just the video ID
            video_id = content.split('?')[0].strip()
        
        return video_id
    except Exception as e:
        print(f"Error reading .yt file {yt_file_path}: {e}")
        return None

def download_youtube_thumbnail(video_id, output_path):
    """Download YouTube thumbnail for given video ID"""
    # Try different quality thumbnails in order of preference
    thumbnail_urls = [
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",  # 1280x720
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",      # 480x360
        f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",      # 320x180
    ]
    
    for url in thumbnail_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Check if it's not the default "not found" image
                if len(response.content) > 1000:  # YouTube's 404 image is tiny
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return True
        except Exception as e:
            print(f"Error downloading thumbnail from {url}: {e}")
            continue
    
    return False

def process_youtube_thumbnails(entry, folder_path, thumbs_base_dir):
    """Process YouTube thumbnails for an entry - only if .yt is the thumbnail"""
    file_paths = entry.get('file_paths', [])
    
    # Only process if the FIRST file is a .yt file (would be used as thumbnail)
    if not file_paths or not file_paths[0].endswith('.yt'):
        return None
    
    # Extract YouTube ID from the first file
    yt_file_path = file_paths[0]
    full_path = os.path.join(folder_path, os.path.basename(yt_file_path))
    video_id = extract_youtube_id(full_path)
    
    if not video_id:
        return None
    
    # Generate hash for filename
    hash_obj = hashlib.md5(video_id.encode())
    hash_name = hash_obj.hexdigest()
    
    # Create thumbnail path
    thumb_filename = f"{hash_name}.jpg"
    #public is served as static by node
    thumb_rel_path = f"static/thumbs/{thumb_filename}"
    thumb_full_path = os.path.join(thumbs_base_dir, thumb_filename)
    
    # Ensure thumbs directory exists
    os.makedirs(os.path.dirname(thumb_full_path), exist_ok=True)
    
    # Check if thumbnail already exists
    if not os.path.exists(thumb_full_path):
        print(f"Downloading thumbnail for {entry['title']} (YouTube: {video_id})...")
        if download_youtube_thumbnail(video_id, thumb_full_path):
            print(f"  ✓ Saved to {thumb_rel_path}")
            return thumb_rel_path
        else:
            print(f"  ✗ Failed to download thumbnail")
    else:
        # Thumbnail already exists, just return the path
        return thumb_rel_path
    
    return None

def calculate_media_dimensions(file_path):
    """Calculate and return dimensions for any media file"""
    try:
        extension = pathlib.Path(file_path).suffix.lower()
        
        if extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"]:
            return get_image_dimensions(file_path)
        elif extension in [".webm", ".mp4", ".avi", ".mkv", ".mov"]:
            return get_video_dimensions(file_path)
        elif extension in [".yt"]:
            return (16, 9)  # Standard YouTube aspect ratio
        else:
            return None
    except Exception as e:
        print(f"Error getting dimensions for {file_path}: {e}")
        return None


def process_entries(data):
    """Simplified version without dimension calculations"""
    themes = defaultdict(lambda: defaultdict(list))
    existing_folders = []
    existing_ids = {}
    entries_without_id = []
    FileListForCopyingAtTheEnd = []
    
    # Create thumbs directory if it doesn't exist
    thumbs_base_dir = 'public/thumbs'
    os.makedirs(thumbs_base_dir, exist_ok=True)
    
    for entry in data:
        # Initialize thumbnail_override field
        entry['thumbnail_override'] = ''
        
        if not entry['id']:
            print(f"Entry without id: {entry['title']}")
            entries_without_id.append(entry)
            continue
            
        if entry['id'] in existing_ids:
            print(f"Id collision detected: {entry['id']}")
        else:
            existing_ids[entry['id']] = True
        
        theme_list = [theme.strip() for theme in entry['theme'].split(',')]
        folder_theme = theme_list[0]
        folder_path = os.path.join('entries', folder_theme, entry['id'])
        os.makedirs(folder_path, exist_ok=True)
        
        file_list = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                    if os.path.isfile(os.path.join(folder_path, f))]
        file_list = sort_files(file_list)
        
        updated_file_list = process_files(file_list)
        entry['file_paths'] = updated_file_list
        FileListForCopyingAtTheEnd.append(updated_file_list)
        # Check if a thumbnail can be generated from the first image
        if updated_file_list:
            first_file = updated_file_list[0]
            extension = pathlib.Path(first_file).suffix.lower()
            if extension in [".jpg", ".jpeg", ".png", ".webp"]:
                # Generate an image thumbnail and assign it to thumbnail_override
                img_thumb_path = generate_image_thumbnail(first_file, thumbs_base_dir)
                if img_thumb_path:
                    entry['thumbnail_override'] = img_thumb_path
        
        # Process YouTube thumbnails
        thumbnail_path = process_youtube_thumbnails(entry, folder_path, thumbs_base_dir)
        if thumbnail_path:
            entry['thumbnail_override'] = thumbnail_path
        
        # We can remove the max_height calculation if not needed elsewhere
        # max_height = calculate_max_height(updated_file_list)
        # entry['lightbox_max_height'] = f"{max_height}px" if max_height > 0 else "0px"
        
        existing_folders.append(folder_path)
        
        # Create a copy of the entry for each theme
        for theme in theme_list:
            theme = theme.strip()
            entry_copy = entry.copy()
            entry_copy['theme'] = theme
            themes[theme][entry['year']].append(entry_copy)
    
    return themes, existing_folders, entries_without_id, FileListForCopyingAtTheEnd
def generate_html_content(themes):
    html_content = ""
    year_themes = {}
    all_entries = []
    
    # Collect all entries and their themes
    for theme, year_entries in themes.items():
        for year, entries in year_entries.items():
            for entry in entries:
                # Create a new entry with all themes for display
                display_entry = entry.copy()
                all_entries.append(display_entry)
                
                # Track themes for each year
                if year not in year_themes:
                    year_themes[year] = set()
                year_themes[year].add(theme.lower())
    
    # Sort entries by year
    try:
        all_entries.sort(key=lambda x: int(x['year']), reverse=True)
    except Exception as e:
        print(f"Error sorting entries: {e}")
        print("Entries will be unsorted")
    
    # Generate HTML
    html_content += '<div class="subgroup">'
    current_year = None
    
    for entry in all_entries:
        if entry['year'] != current_year:
            current_year = entry['year']
            year_theme_classes = ' '.join([f"{theme}text" for theme in year_themes[current_year]])
            html_content += f'<p class="year {year_theme_classes}">{current_year}</p>\n'
        
        entry_json = json.dumps(entry)
        entry_json_escaped = html.escape(entry_json)
        locked_class = "lost " if entry.get('locked', False) else ""
        theme_class = f"{entry['theme'].lower()}text"
        
        tags = entry.get("tags", "")
        first_tag = tags.split(",")[0] if tags else " "
        first_tag = first_tag.replace("-", " ").replace("_", " ")
        
        html_content += f'<p class="title {theme_class}"><a target="_blank" href="#{entry["id"]}" data-entry=\'{entry_json_escaped}\' class="{locked_class}subtext"><span class="small">{first_tag}</span> {entry["title"]}</a></p>\n'
    
    html_content += '</div>'
    return html_content

def compress_video_if_needed(filename, max_filesize_bytes=500000000):
    """Convert videos to WebM format, with size-based quality adjustment"""
    
    # Skip already compressed files
    base_name = os.path.basename(filename)
    if base_name.startswith('c_') or '_c_' in base_name:
        return filename
    
    file_size_bytes = os.path.getsize(filename)
    dir_name = os.path.dirname(filename)
    name_without_ext, extension = os.path.splitext(base_name)
    
    # Always convert to WebM for web compatibility
    webm_filename = os.path.join(dir_name, f"_c_{name_without_ext}.webm")
    
    if not os.path.isfile(webm_filename):
        print(f"Converting {filename} → WebM: {webm_filename}")
        
        # Adjust quality based on original file size
        if file_size_bytes > max_filesize_bytes:
            # High compression for large files
            bitrate = "600k"
            crf = "32"
            speed = "2"  # Faster encoding, good quality
        else:
            # Higher quality for smaller files
            bitrate = "1200k"
            crf = "28"
            speed = "1"  # Slower encoding, better quality
        
        try:
            subprocess.run([
                "ffmpeg", "-i", filename,
                "-c:v", "libvpx-vp9",           # VP9 codec
                "-c:a", "libopus",              # Opus audio
                "-vf", "scale='min(720,iw)':-2", # Scale down if needed
                "-b:v", bitrate,
                "-crf", crf,
                "-speed", speed,
                "-row-mt", "1",                 # Multi-threading
                "-y",                           # Overwrite output files
                webm_filename
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error converting {filename}: {e}")
            return filename  # Return original if conversion fails
    
    return webm_filename

def filter_video_files(file_list):
    """Filter file list to exclude original MP4s when WebM exists"""
    filtered_files = []
    
    for filename in file_list:
        base_name = os.path.basename(filename)
        name_without_ext, extension = os.path.splitext(base_name)
        dir_name = os.path.dirname(filename)
        
        # If it's an MP4, check if WebM version exists
        if extension.lower() in [".mp4", ".avi", ".mkv", ".mov"]:
            # Look for corresponding WebM file
            webm_name = f"_c_{name_without_ext}.webm"
            webm_path = os.path.join(dir_name, webm_name)
            
            if os.path.exists(webm_path):
                # WebM exists, skip this original video
                continue
        
        filtered_files.append(filename)
    
    return filtered_files

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
    """Updated to handle WebM files"""
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", 
               "-show_entries", "stream=height,width", "-of", "json", video_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, 
                              stderr=subprocess.STDOUT, text=True, check=True)
        dimensions = json.loads(result.stdout)['streams'][0]
        return dimensions['width'], dimensions['height']
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Error getting video dimensions for {video_path}: {e}")
        return (16, 9)  # Fallback aspect ratio
# Process entries and generate HTML
themes, existing_folders, entries_without_id, FileListForCopyingAtTheEnd = process_entries(data)
html_content = generate_html_content(themes)

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

# --- GENERATE FINAL JSON OUTPUT ---
# The 'data' list has been modified in-place by 'process_entries'
# Now we save this enriched data structure to a single file.

import math
import re
from collections import Counter, defaultdict

def compute_recommendations(data, max_recommendations=4):
    """
    Multi-modal content-based recommendation system.
    Combines text similarity, tag similarity, and temporal proximity.
    """
    
    class SparseVector:
        """Efficient sparse vector representation."""
        
        def __init__(self, dimension):
            self.dimension = dimension
            self.values = {}  # Only store non-zero values
            
        def set(self, index, value):
            if value != 0:
                self.values[index] = value
            elif index in self.values:
                del self.values[index]
                
        def get(self, index):
            return self.values.get(index, 0)
        
        def dot(self, other):
            """Compute dot product with another sparse vector."""
            result = 0
            # Iterate over the smaller vector for efficiency
            if len(self.values) <= len(other.values):
                for idx, val in self.values.items():
                    result += val * other.get(idx)
            else:
                for idx, val in other.values.items():
                    result += val * self.get(idx)
            return result
        
        def norm(self):
            """Compute L2 norm."""
            return math.sqrt(sum(v * v for v in self.values.values()))
        
        def normalize(self):
            """Normalize to unit length."""
            n = self.norm()
            if n > 0:
                for idx in list(self.values.keys()):
                    self.values[idx] /= n
    
    class TextVectorizer:
        """TF-IDF vectorization for text data."""
        
        def __init__(self, max_features=300, min_df=2):
            self.max_features = max_features
            self.min_df = min_df
            self.vocabulary = {}
            self.idf_weights = {}
            self.stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
                'that', 'these', 'those', 'very', 'just', 'only'
            }
            
        def _tokenize(self, text):
            """Extract tokens and bigrams from text."""
            if not text:
                return []
            
            # Clean text
            text = re.sub(r'<[^>]+>', ' ', text.lower())
            text = re.sub(r'[^a-z0-9\s\-_]', ' ', text)
            
            # Get tokens
            tokens = [t for t in text.split() if t and t not in self.stop_words and len(t) > 2]
            
            # Add bigrams
            bigrams = []
            for i in range(len(tokens) - 1):
                bigram = f"{tokens[i]} {tokens[i+1]}"
                bigrams.append(bigram)
            
            return tokens + bigrams
        
        def fit_transform(self, texts):
            """Fit the model and transform texts to vectors."""
            # First pass: count document frequencies
            doc_freq = defaultdict(int)
            term_counts = Counter()
            all_doc_terms = []
            
            for text in texts:
                terms = self._tokenize(text)
                all_doc_terms.append(terms)
                unique_terms = set(terms)
                
                for term in unique_terms:
                    doc_freq[term] += 1
                term_counts.update(terms)
            
            # Select features: frequent terms that appear in multiple docs
            eligible_terms = [
                term for term, count in term_counts.items()
                if doc_freq[term] >= self.min_df
            ]
            
            # Sort by frequency and take top features
            eligible_terms.sort(key=lambda t: term_counts[t], reverse=True)
            selected_terms = eligible_terms[:self.max_features]
            
            # Build vocabulary
            self.vocabulary = {term: idx for idx, term in enumerate(selected_terms)}
            
            # Calculate IDF weights
            n_docs = len(texts)
            for term, idx in self.vocabulary.items():
                # Add 1 for smoothing
                self.idf_weights[idx] = math.log((n_docs + 1) / (doc_freq[term] + 1)) + 1
            
            # Second pass: create vectors
            vectors = []
            for terms in all_doc_terms:
                vec = SparseVector(len(self.vocabulary))
                
                # Calculate term frequencies
                term_freq = Counter(terms)
                total_terms = len(terms)
                
                # Build TF-IDF vector
                for term, freq in term_freq.items():
                    if term in self.vocabulary:
                        idx = self.vocabulary[term]
                        tf = freq / total_terms if total_terms > 0 else 0
                        vec.set(idx, tf * self.idf_weights[idx])
                
                vec.normalize()
                vectors.append(vec)
            
            return vectors
    
    class TagVectorizer:
        """Vectorization for categorical tag data."""
        
        def __init__(self):
            self.vocabulary = {}
            self.idf_weights = {}
            
        def fit_transform(self, tag_lists):
            """Fit the model and transform tags to vectors."""
            # Count document frequencies
            doc_freq = defaultdict(int)
            all_tags = []
            
            for tags in tag_lists:
                # Normalize tags
                normalized_tags = [t.strip().lower().replace('-', '').replace('_', '') 
                                 for t in tags if t.strip()]
                all_tags.append(normalized_tags)
                
                unique_tags = set(normalized_tags)
                for tag in unique_tags:
                    doc_freq[tag] += 1
            
            # Build vocabulary
            unique_tags = list(set(sum(all_tags, [])))
            self.vocabulary = {tag: idx for idx, tag in enumerate(unique_tags)}
            
            # Calculate IDF weights
            n_docs = len(tag_lists)
            for tag, idx in self.vocabulary.items():
                self.idf_weights[idx] = math.log((n_docs + 1) / (doc_freq[tag] + 1)) + 1
            
            # Create vectors
            vectors = []
            for tags in all_tags:
                vec = SparseVector(len(self.vocabulary))
                
                for tag in tags:
                    if tag in self.vocabulary:
                        idx = self.vocabulary[tag]
                        vec.set(idx, self.idf_weights[idx])
                
                vec.normalize()
                vectors.append(vec)
            
            return vectors
    
    def cosine_similarity(vec1, vec2):
        """Compute cosine similarity between normalized vectors."""
        return vec1.dot(vec2)
    
    def gaussian_kernel(diff, sigma=2.0):
        """Gaussian similarity for temporal proximity."""
        return math.exp(-(diff ** 2) / (2 * sigma ** 2))
    
    # Filter valid entries
    valid_entries = []
    entry_map = {}
    
    for entry in data:
        if entry.get('id') and (entry.get('title') or entry.get('description')):
            idx = len(valid_entries)
            valid_entries.append(entry)
            entry_map[entry['id']] = idx
    
    if not valid_entries:
        return data
    
    print(f"Processing {len(valid_entries)} entries...")
    
    # Prepare data for vectorization
    texts = []
    tag_lists = []
    years = []
    
    for entry in valid_entries:
        # Combine title and description
        title = entry.get('title', '')
        description = entry.get('description', '')
        # Weight title more heavily
        combined_text = f"{title} {title} {title} {description}"
        texts.append(combined_text)
        
        # Extract tags
        tags_str = entry.get('tags', '')
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        tag_lists.append(tags)
        
        # Extract year
        year_str = str(entry.get('year', '0'))
        years.append(int(year_str) if year_str.isdigit() else 0)
    
    # Vectorize text and tags
    print("Building text vectors...")
    text_vectorizer = TextVectorizer(max_features=300, min_df=1)
    text_vectors = text_vectorizer.fit_transform(texts)
    
    print("Building tag vectors...")
    tag_vectorizer = TagVectorizer()
    tag_vectors = tag_vectorizer.fit_transform(tag_lists)
    
    # Compute recommendations
    print("Computing similarities...")
    recommendations = {}
    
    for i, entry in enumerate(valid_entries):
        similarities = []
        
        for j, other_entry in enumerate(valid_entries):
            if i == j:
                continue
            
            # Skip locked entries
            if other_entry.get('locked', False):
                continue
            
            # Compute text similarity
            text_sim = cosine_similarity(text_vectors[i], text_vectors[j])
            
            # Compute tag similarity
            tag_sim = cosine_similarity(tag_vectors[i], tag_vectors[j])
            
            # Compute temporal similarity
            year_diff = abs(years[i] - years[j]) if years[i] and years[j] else 5
            temporal_sim = gaussian_kernel(year_diff, sigma=3.0)
            
            # Adaptive weighting
            if text_sim > 0.6:
                # Strong text match
                content_weight = 0.8
                text_weight = 0.75
            elif text_sim > 0.3:
                # Moderate text match
                content_weight = 0.85
                text_weight = 0.6
            elif tag_sim > 0.5:
                # Strong tag match, weak text
                content_weight = 0.9
                text_weight = 0.3
            else:
                # Default weights
                content_weight = 0.9
                text_weight = 0.5
            
            # Combine similarities
            tag_weight = 1 - text_weight
            content_sim = text_weight * text_sim + tag_weight * tag_sim
            temporal_weight = 1 - content_weight
            
            final_score = content_weight * content_sim + temporal_weight * temporal_sim
            
            if final_score > 0:
                similarities.append((j, final_score, text_sim, tag_sim))
        
        # Sort and get top recommendations
        similarities.sort(key=lambda x: x[1], reverse=True)
        rec_ids = [valid_entries[idx]['id'] for idx, _, _, _ in similarities[:max_recommendations]]
        recommendations[entry['id']] = rec_ids
    
    # Add recommendations to all entries
    for entry in data:
        entry_id = entry.get('id')
        entry['recommended_ids'] = recommendations.get(entry_id, [])
    
    # Debug output
    print(f"\n=== Recommendation Summary ===")
    print(f"Text vocabulary size: {len(text_vectorizer.vocabulary)}")
    print(f"Tag vocabulary size: {len(tag_vectorizer.vocabulary)}")
    
    # Show some statistics
    bigrams = [t for t in text_vectorizer.vocabulary.keys() if ' ' in t]
    if bigrams:
        print(f"Sample bigrams found: {bigrams[:5]}")
    
    # Validation
    print("\n=== Sample Recommendations ===")
    for i, entry in enumerate(valid_entries[:5]):
        if entry.get('recommended_ids'):
            print(f"\n{entry['title']}:")
            for rec_id in entry['recommended_ids'][:2]:
                rec_idx = entry_map.get(rec_id)
                if rec_idx is not None:
                    rec_entry = valid_entries[rec_idx]
                    print(f"  → {rec_entry['title']}")
    
    return data

# Add recommendation computation:
print("\nComputing project recommendations...")
data = compute_recommendations(data, max_recommendations=4)



print("Generating compiled.json for the Node.js app...")
# The 'data' variable already contains all the entries that were processed
# by process_entries, including the updated 'file_paths'.
with open('entries/compiled/compiled.json', 'w') as json_file:
    json.dump(data, json_file, indent=2)

print("✅ compiled.json created successfully.")

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
print("constructing final index.html file at target dir and source dir")
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
