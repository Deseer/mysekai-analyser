import asyncio
import json
import os
from typing import Set

import aiohttp
import aiofiles
from tqdm.asyncio import tqdm_asyncio

import configs
# --- 配置区 ---
RESOURCE_PATH = configs.RESOURCE_PATH
TARGET_REGION = configs.TARGET_REGION
METADATA_BASE_URL = configs.METADATA_BASE_URL
ASSET_BASE_URL = configs.ASSET_BASE_URL

# --- 文件清单 ---
METADATA_FILES = [
    "mysekaiMaterials", "mysekaiPhenomenas", "mysekaiSiteHarvestFixtures",
    "gameCharacterUnits", "mysekaiGameCharacterUnitGroups", "mysekaiMusicRecords",
    "musics", "mysekaiItems", "mysekaiFixtures",
]

STATIC_FILES = [
    "mysekai/mark.png",
    "mysekai/light.png",
    "mysekai/music_record.png",
    *[f"mysekai/gate_icon/gate_{i}.png" for i in range(1, 6)],
]

# --- 核心下载逻辑 ---

async def download_file(session: aiohttp.ClientSession, url: str, dest_path: str) -> bool:
    """异步下载单个文件并保存。"""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                async with aiofiles.open(dest_path, 'wb') as f:
                    await f.write(await response.read())
                return True
            return False
    except (asyncio.TimeoutError, aiohttp.ClientError):
        return False
    except Exception as e:
        return False

async def download_asset(session: aiohttp.ClientSession, path: str, dest_base: str) -> bool:
    """
    下载单个Asset/Static资源，自动尝试 'ondemand' 和 'startapp' 两个目录。
    """
    path_no_rip = path.replace("_rip", "")
    dest_path = os.path.join(dest_base, path_no_rip)

    if os.path.exists(dest_path):
        return True

    # 优先尝试 ondemand 目录
    url_ondemand = f"{ASSET_BASE_URL}ondemand/{path_no_rip}"
    if await download_file(session, url_ondemand, dest_path):
        return True

    # 如果失败，再尝试 startapp 目录
    url_startapp = f"{ASSET_BASE_URL}startapp/{path_no_rip}"
    if await download_file(session, url_startapp, dest_path):
        return True

    return False

async def main():
    """主执行函数"""
    print("Asset Updator for MySekai Analyser\n")

    metadata_dest_dir = os.path.join(RESOURCE_PATH, "metadata", TARGET_REGION)

    # --- 1. 下载 Metadata ---
    print(f"Phase 1: Downloading Metadata from {METADATA_BASE_URL}...")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        tasks = []
        for table_name in METADATA_FILES:
            url = f"{METADATA_BASE_URL}{table_name}.json"
            dest = os.path.join(metadata_dest_dir, f"{table_name}.json")
            tasks.append(download_file(session, url, dest))
        await tqdm_asyncio.gather(*tasks, desc="Downloading Metadata")
    print("Metadata download complete.\n")

    # --- 2. 提取动态资源路径 ---
    print("Phase 2: Extracting dynamic asset paths...")
    asset_paths: Set[str] = set()
    static_paths: Set[str] = set()

    def load_json_table(filename):
        try:
            with open(os.path.join(metadata_dest_dir, filename), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: return []

    # 采集点图标 -> static_images
    for fixture in load_json_table("mysekaiSiteHarvestFixtures.json"):
        static_paths.add(f"mysekai/harvest_fixture_icon/{fixture['mysekaiSiteHarvestFixtureRarityType']}/{fixture['assetbundleName']}.png")

    # 天气相关 -> assets 和 static_images
    for phenom in load_json_table("mysekaiPhenomenas.json"):
        asset_paths.add(f"mysekai/thumbnail/phenomena/{phenom['iconAssetbundleName']}.png")
        static_paths.add(f"mysekai/phenom_bg/{phenom['id']}.png")

    # MySekai 专属资源 -> assets
    for mat in load_json_table("mysekaiMaterials.json"):
        asset_paths.add(f"mysekai/thumbnail/material/{mat['iconAssetbundleName']}.png")
    for item in load_json_table("mysekaiItems.json"):
        asset_paths.add(f"mysekai/thumbnail/item/{item['iconAssetbundleName']}.png")
    for fixture in load_json_table("mysekaiFixtures.json"):
        name = fixture['assetbundleName']
        for i in range(1, 7): # 下载所有可能的颜色变体
            asset_paths.add(f"mysekai/thumbnail/fixture/{name}_{i}.png")

    # 唱片封面 -> assets
    musics_map = {m['id']: m['assetbundleName'] for m in load_json_table("musics.json")}
    for record in load_json_table("mysekaiMusicRecords.json"):
        music_id = record.get('externalId')
        if music_id in musics_map:
            asset_paths.add(f"music/jacket/{musics_map[music_id]}/{musics_map[music_id]}.png")

    # 固定的资源路径
    # 区域缩略图 -> assets
    asset_paths.update({f"mysekai/site/sitemap/texture/{i}.png" for i in (5, 6, 7, 8)})
    # 通用材料 -> assets
    asset_paths.update({f"thumbnail/material/{i}.png" for i in [17, 170, 173]})
    # SD小人 -> assets
    asset_paths.update({f"character/character_sd_l/chr_sp_{i}.png" for i in range(1, 41)})
    asset_paths.update({f"character/character_sd_l/chr_sp_{i}.png" for i in range(701, 741)})

    print(f"Extracted {len(asset_paths)} asset paths and {len(static_paths)} static paths.")

    # --- 3. 下载所有文件 ---
    print(f"\nPhase 3: Downloading all files...")
    asset_dest_dir = os.path.join(RESOURCE_PATH, "assets", TARGET_REGION)
    static_dest_dir = os.path.join(RESOURCE_PATH, "static_images")

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        all_tasks = []
        for path in asset_paths:
            all_tasks.append(download_asset(session, path, asset_dest_dir))
        for path in static_paths.union(STATIC_FILES):
            all_tasks.append(download_asset(session, path, static_dest_dir))

        await tqdm_asyncio.gather(*all_tasks, desc="Downloading Resources")

    print("\nAsset update process complete!")
    print(f"Resources are saved in: {os.path.abspath(RESOURCE_PATH)}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDownload interrupted by user.")