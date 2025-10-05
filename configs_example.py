# asset
RESOURCE_PATH = "./resources"
TARGET_REGION = "jp"
MASTERDATA_BASE_URL = ""
ASSET_BASE_URL = f"https:///{TARGET_REGION}-assets/" #补url端点，保留/{TARGET_REGION}-assets/，史山发力了

# fonts(随便拖点字体进来就行)
DEFAULT_FONT_PATH = ""
DEFAULT_BOLD_FONT_PATH = ""
DEFAULT_HEAVY_FONT_PATH = ""

# main
INPUT_FILE = "./mysekai.json"
SHOW_HARVESTED = True
OUTPUT_SUMMARY_FILENAME = "output_summary.png"
OUTPUT_MAPS_FILENAME = "output_maps.png"

# extractor
ENABLE_MAP_CROPPING = True #裁剪地图到合适大小

aes_key_bytes = b''
aes_iv_bytes = b''