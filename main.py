import os
import json
from datetime import datetime


from loader import LocalAssetLoader
from drawer import draw_summary_image, combine_and_save_maps
from extractor import extract_summary_data, extract_all_harvest_map_data

import configs

RESOURCE_PATH = configs.RESOURCE_PATH
INPUT_FILE = configs.INPUT_FILE
TARGET_REGION = configs.TARGET_REGION
SHOW_HARVESTED = configs.SHOW_HARVESTED
OUTPUT_SUMMARY_FILENAME = configs.OUTPUT_SUMMARY_FILENAME
OUTPUT_MAPS_FILENAME = configs.OUTPUT_MAPS_FILENAME

def main():
    """程序的主执行函数"""
    start_time = datetime.now()
    print("========================================")
    print(" MySekai Analyser - Image Generator ")
    print("========================================")

    if not os.path.exists(INPUT_FILE):
        print(f"\n[ERROR] Input file not found: {INPUT_FILE}")
        return

    # 1. 初始化
    print("\n[1/4] Initializing resources...")
    loader = LocalAssetLoader(resource_path=RESOURCE_PATH, region=TARGET_REGION)
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        mysekai_data = json.load(f)
    print("-> Resources initialized.")

    # 2. 提取数据
    print("\n[2/4] Extracting data...")
    summary_data = extract_summary_data(mysekai_data, loader, SHOW_HARVESTED)
    map_data_list = extract_all_harvest_map_data(mysekai_data, loader, SHOW_HARVESTED)
    print("-> Data extracted.")

    # 3. 绘制图片
    print("\n[3/4] Drawing images... (This may take a moment)")

    summary_image = draw_summary_image(summary_data, loader)
    combine_and_save_maps(map_data_list, loader, OUTPUT_MAPS_FILENAME)

    print("-> Images drawn and saved.")

    # 4. 保存主图
    print("\n[4/4] Saving summary image...")
    summary_image.save(OUTPUT_SUMMARY_FILENAME)

    duration = (datetime.now() - start_time).total_seconds()
    print("\n========================================")
    print(f"🎉 All finished! (Took {duration:.2f} seconds)")
    print("========================================")
    print("Please check the output files:")
    print(f"- {OUTPUT_SUMMARY_FILENAME}")
    print(f"- {OUTPUT_MAPS_FILENAME}")

if __name__ == "__main__":
    main()