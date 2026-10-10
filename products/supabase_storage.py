
import io
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from PIL import Image, ImageOps
from decouple import config
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

# Enable HEIC/HEIF format support for Apple iPhone uploads if pillow-heif is installed
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

# Allow high-resolution smartphone camera captures without decompression bomb errors
Image.MAX_IMAGE_PIXELS = None


def convert_to_webp(name, file_bytes):
    """
    Converts an uploaded image payload to optimized WebP in-memory using Pillow.
    - Optimized for mobile uploads: downscales large smartphone photos (12MP-108MP)
      to e-commerce max dimensions (2048px) to prevent Out-Of-Memory (OOM) 502 crashes.
    - Applies EXIF orientation correction.
    - Preserves alpha transparency (RGBA) if present.
    - Uses fast & efficient WebP method=4 (10x faster than method=6 with no visual loss).
    - Uses configurable WEBP_QUALITY from Django settings / decouple config.
    - Updates file extension to .webp and MIME type to image/webp.
    - If conversion fails or file is not an image, returns original name, bytes, and octet-stream fallback.
    """
    quality = getattr(settings, "WEBP_QUALITY", config("WEBP_QUALITY", default=82, cast=int))
    max_dimension = getattr(settings, "MAX_IMAGE_DIMENSION", 2048)

    clean_name = name.replace("\\", "/")
    base, ext = os.path.splitext(clean_name)
    ext_lower = ext.lower()

    # Skip conversion if file is already a WebP image and under dimension limits
    if ext_lower == ".webp":
        return clean_name, file_bytes, "image/webp"

    try:
        image = Image.open(io.BytesIO(file_bytes))

        # 1. EXIF Orientation correction (crucial for mobile camera photos)
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass

        # 2. Downscale huge smartphone photos to max 2048px to save RAM and avoid 502 timeouts
        if image.width > max_dimension or image.height > max_dimension:
            # Use Image.Resampling.LANCZOS if available, fallback to Image.LANCZOS
            resample_filter = getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)
            image.thumbnail((max_dimension, max_dimension), resample_filter)

        # 3. Transparency detection & mode handling
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")

        # 4. Save as WebP to in-memory BytesIO buffer using balanced method=4 (fast & lightweight)
        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=quality, method=4)
        webp_bytes = buffer.getvalue()

        # 5. Generate .webp filename
        new_name = f"{base}.webp"
        return new_name, webp_bytes, "image/webp"

    except Exception as e:
        # Fallback to original file if non-image or Pillow error
        print(f"WebP conversion fallback for {name}: {e}")
        return clean_name, file_bytes, "application/octet-stream"


@deconstructible
class SupabaseStorage(Storage):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.supabase_url = config("SUPABASE_URL").rstrip("/")
        self.supabase_key = config("SUPABASE_KEY")
        self.bucket_name = config("SUPABASE_BUCKET")

    def _save(self, name, content):
        file_data = content.read()

        # Convert image to WebP before uploading to Supabase
        clean_name, file_data, content_type = convert_to_webp(name, file_data)

        upload_url = (
            f"{self.supabase_url}/storage/v1/object/"
            f"{self.bucket_name}/{clean_name}"
        )

        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apikey": self.supabase_key,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        request = Request(
            upload_url,
            data=file_data,
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(request) as response:
                if response.status not in (200, 201):
                    raise RuntimeError(
                        f"Supabase upload failed: HTTP {response.status}"
                    )

        except HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")

            raise RuntimeError(
                f"Supabase upload failed: HTTP {e.code} - {error_body}"
            ) from e

        except URLError as e:
            raise RuntimeError(
                f"Could not connect to Supabase: {e.reason}"
            ) from e

        return clean_name

    def url(self, name):
        clean_name = name.replace("\\", "/")

        return (
            f"{self.supabase_url}/storage/v1/object/public/"
            f"{self.bucket_name}/{clean_name}"
        )

    def exists(self, name):
        return False

    def delete(self, name):
        """
        Deletes a single file object from Supabase Storage.
        """
        if not name:
            return

        clean_name = str(name).replace("\\", "/").strip("/")
        public_prefix = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/"
        if clean_name.startswith(public_prefix):
            clean_name = clean_name[len(public_prefix):]

        delete_url = (
            f"{self.supabase_url}/storage/v1/object/"
            f"{self.bucket_name}/{clean_name}"
        )

        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apikey": self.supabase_key,
        }

        request = Request(
            delete_url,
            headers=headers,
            method="DELETE",
        )

        try:
            with urlopen(request) as response:
                if response.status not in (200, 204):
                    print(f"Supabase delete file warning: HTTP {response.status}")
        except HTTPError as e:
            print(f"Supabase delete HTTP error: {e.code}")
        except Exception as e:
            print(f"Could not delete file from Supabase: {e}")

    def delete_folder(self, folder_path):
        """
        Recursively deletes all object files inside a folder prefix from Supabase Storage.
        Handles nested subfolders (e.g. products/<product_id>/<color_slug>/<filename>).
        """
        if not folder_path:
            return

        clean_folder = str(folder_path).replace("\\", "/").strip("/")
        list_url = f"{self.supabase_url}/storage/v1/object/list/{self.bucket_name}"

        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apikey": self.supabase_key,
            "Content-Type": "application/json",
        }

        import json

        files_to_delete = []

        def _scan_prefix(prefix):
            payload = json.dumps({
                "prefix": prefix,
                "limit": 100,
                "offset": 0,
            }).encode("utf-8")

            req = Request(list_url, data=payload, headers=headers, method="POST")
            try:
                with urlopen(req) as resp:
                    items = json.loads(resp.read().decode("utf-8"))
                    if isinstance(items, list):
                        for item in items:
                            item_name = item.get("name")
                            if not item_name:
                                continue

                            full_path = f"{prefix}/{item_name}" if not item_name.startswith(prefix) else item_name

                            # Subfolder check: id is null and metadata is null
                            if item.get("id") is None and item.get("metadata") is None:
                                _scan_prefix(full_path)
                            else:
                                files_to_delete.append(full_path)
            except Exception as e:
                print(f"Error scanning prefix '{prefix}': {e}")

        _scan_prefix(clean_folder)

        if files_to_delete:
            delete_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}"
            # Delete in chunks of 100
            for i in range(0, len(files_to_delete), 100):
                chunk = files_to_delete[i:i+100]
                del_payload = json.dumps({"prefixes": chunk}).encode("utf-8")
                del_req = Request(delete_url, data=del_payload, headers=headers, method="DELETE")
                try:
                    with urlopen(del_req) as del_resp:
                        print(f"Successfully deleted {len(chunk)} files from '{clean_folder}' in Supabase.")
                except Exception as e:
                    print(f"Failed to delete chunk of files from '{clean_folder}': {e}")


    def move(self, source_path, destination_path):
        """
        Moves/renames a single file object in Supabase Storage from source_path to destination_path.
        Returns True if successful, False otherwise.
        """
        if not source_path or not destination_path or source_path == destination_path:
            return False

        clean_src = str(source_path).replace("\\", "/").strip("/")
        clean_dest = str(destination_path).replace("\\", "/").strip("/")

        public_prefix = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/"
        if clean_src.startswith(public_prefix):
            clean_src = clean_src[len(public_prefix):]
        if clean_dest.startswith(public_prefix):
            clean_dest = clean_dest[len(public_prefix):]

        move_url = f"{self.supabase_url}/storage/v1/object/move"

        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apikey": self.supabase_key,
            "Content-Type": "application/json",
        }

        import json
        payload = json.dumps({
            "bucketId": self.bucket_name,
            "sourceKey": clean_src,
            "destinationKey": clean_dest,
        }).encode("utf-8")

        req = Request(move_url, data=payload, headers=headers, method="POST")

        try:
            with urlopen(req) as resp:
                if resp.status in (200, 201):
                    return True
        except HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            print(f"Supabase move error from {clean_src} to {clean_dest}: HTTP {e.code} - {err}")
        except Exception as e:
            print(f"Supabase move failed from {clean_src} to {clean_dest}: {e}")

        return False

    def move_folder(self, src_folder, dest_folder):
        """
        Moves all files inside src_folder to dest_folder in Supabase Storage.
        """
        if not src_folder or not dest_folder or src_folder == dest_folder:
            return

        clean_src = str(src_folder).replace("\\", "/").strip("/")
        clean_dest = str(dest_folder).replace("\\", "/").strip("/")

        list_url = f"{self.supabase_url}/storage/v1/object/list/{self.bucket_name}"
        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apikey": self.supabase_key,
            "Content-Type": "application/json",
        }
        import json

        files_to_move = []

        def _scan_prefix(prefix):
            payload = json.dumps({
                "prefix": prefix,
                "limit": 100,
                "offset": 0,
            }).encode("utf-8")

            req = Request(list_url, data=payload, headers=headers, method="POST")
            try:
                with urlopen(req) as resp:
                    items = json.loads(resp.read().decode("utf-8"))
                    if isinstance(items, list):
                        for item in items:
                            item_name = item.get("name")
                            if not item_name:
                                continue
                            full_path = f"{prefix}/{item_name}" if not item_name.startswith(prefix) else item_name
                            if item.get("id") is None and item.get("metadata") is None:
                                _scan_prefix(full_path)
                            else:
                                files_to_move.append(full_path)
            except Exception as e:
                print(f"Error scanning prefix for move '{prefix}': {e}")

        _scan_prefix(clean_src)

        for src_file in files_to_move:
            if src_file.startswith(clean_src):
                relative_path = src_file[len(clean_src):].lstrip("/")
                dest_file = f"{clean_dest}/{relative_path}"
                self.move(src_file, dest_file)


supabase_storage = SupabaseStorage()


