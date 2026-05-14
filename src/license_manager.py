import json
import os
import logging

logger = logging.getLogger("LicenseManager")

class LicenseManager:
    def __init__(self, log_file="license_log.json"):
        self.log_file = log_file
        self.allowed_licenses = ["CC0", "CC-BY", "Public Domain", "Pixabay License", "Pexels License", "NASA Public Domain"]

    def log_asset(self, filename, source, license_type, author="Unknown"):
        try:
            data = {}
            if os.path.exists(self.log_file):
                with open(self.log_file, "r") as f:
                    data = json.load(f)
            
            data[filename] = {
                "source": source,
                "license": license_type,
                "author": author,
                "is_safe": any(l in license_type for l in self.allowed_licenses)
            }
            
            with open(self.log_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to log license: {e}")

    def verify_safety(self, filename):
        if not os.path.exists(self.log_file): return False
        with open(self.log_file, "r") as f:
            data = json.load(f)
        return data.get(filename, {}).get("is_safe", False)
