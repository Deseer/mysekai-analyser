import json
import configs
from PIL import Image
from datetime import datetime
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from loader import LocalAssetLoader, UNKNOWN_IMG

SITE_ID_ORDER = (5, 7, 6, 8)
MOST_RARE_MYSEKAI_RES = ["mysekai_material_5", "mysekai_material_12", "mysekai_material_20", "mysekai_material_24", "mysekai_fixture_121", "material_17", "material_170"]
RARE_MYSEKAI_RES = ["mysekai_material_32", "mysekai_material_33", "mysekai_material_34", "mysekai_material_61", "mysekai_material_64", "mysekai_material_65", "mysekai_material_66"]
MYSEKAI_HARVEST_MAP_IMAGE_SCALE = 0.8
ENABLE_MAP_CROPPING = configs.ENABLE_MAP_CROPPING

SITE_MAP_CONFIGS = {
    5: {"image": "mysekai/site_map/5.png", "grid_size": 33.333, "offset_x": 0, "offset_z": -60, "dir_x": -1, "dir_z": -1, "rev_xz": True, "crop_bbox": [250, 150, 840, 560]},
    6: {"image": "mysekai/site_map/7.png", "grid_size": 20.6, "offset_x": -10, "offset_z": 90, "dir_x": 1, "dir_z": -1, "rev_xz": False, "crop_bbox": [350, 150, 840, 560]},
    7: {"image": "mysekai/site_map/6.png", "grid_size": 24.8, "offset_x": -55, "offset_z": 30, "dir_x": -1, "dir_z": -1, "rev_xz": True, "crop_bbox": [300, 120, 840, 560]},
    8: {"image": "mysekai/site_map/8.png", "grid_size": 21.3, "offset_x": 10, "offset_z": -120, "dir_x": 1, "dir_z": -1, "rev_xz": False, "crop_bbox": [350, 100, 840, 560]}
}

SUMMARY_PREVIEW_IMAGE_MAP = {
    5: "5.png",   # 草原(ID 5) -> 使用 5.png
    7: "6.png",   # 花园(ID 7) -> 使用 6.png
    6: "7.png",   # 海滩(ID 6) -> 使用 7.png
    8: "8.png"    # 废墟(ID 8) -> 使用 8.png
}


# --- Data Models ---
@dataclass
class WeatherInfo: phenomena_images: List[Image.Image]; current_phenomenon_id: int; current_phenomenon_index: int
@dataclass
class VisitedCharacter: sd_image: Image.Image
@dataclass
class ResourceItem: key: str; quantity: int; image: Image.Image; is_rare: bool; is_most_rare: bool; has_music_record: bool
@dataclass
class SiteResourceSummary: site_id: int; site_image: Image.Image; resources: List[ResourceItem]
@dataclass
class SummaryDrawData: weather: WeatherInfo; gate_icon: Image.Image; gate_level: int; visited_characters: List[VisitedCharacter]; site_summaries: List[SiteResourceSummary]
@dataclass
class HarvestPoint: image: Image.Image; x: int; y: int
@dataclass
class DroppedResource: image: Image.Image; quantity: int; x: int; z: int; size: int; draw_order: int; is_small_icon: bool; outline: Optional[Tuple[Tuple[int, int, int, int], int]]; light_size: Optional[int]
@dataclass
class HarvestMapDrawData: site_id: int; map_bg_image: Image.Image; draw_width: int; draw_height: int; spawn_point: Tuple[int, int]; harvest_points: List[HarvestPoint]; dropped_resources: List[DroppedResource]

# --- Helper Functions ---
def _get_resource_icon(loader: LocalAssetLoader, key: str) -> Image.Image:
    path = ""
    res_id = int(key.split("_")[-1])
    if key.startswith("mysekai_material"):
        data = loader.md.mysekai_materials.find_by_id(res_id); path = f"mysekai/thumbnail/material/{data['iconAssetbundleName']}.png" if data else ""
    elif key.startswith("material"): path = f"thumbnail/material/{res_id}.png"
    elif key.startswith("mysekai_item"):
        data = loader.md.mysekai_items.find_by_id(res_id); path = f"mysekai/thumbnail/item/{data['iconAssetbundleName']}.png" if data else ""
    elif key.startswith("mysekai_fixture"):
        data = loader.md.mysekai_fixtures.find_by_id(res_id); path = f"mysekai/thumbnail/fixture/{data['assetbundleName']}_1.png" if data else ""
    elif key.startswith("mysekai_music_record"):
        record_data = loader.md.mysekai_musicrecords.find_by_id(res_id)
        if record_data: music_data = loader.md.musics.find_by_id(record_data['externalId']); path = f"music/jacket/{music_data['assetbundleName']}/{music_data['assetbundleName']}.png" if music_data else ""
    if path:
        img = loader.rip.img(path)
        if img.width > 1: return img
    return UNKNOWN_IMG

def _get_character_sd_image(loader: LocalAssetLoader, cuid: int) -> Image.Image:
    return loader.rip.img(f"character/character_sd_l/chr_sp_{cuid}.png")

# --- Main Extractor Functions ---
def extract_summary_data(mysekai_info: dict, loader: LocalAssetLoader, show_harvested: bool) -> SummaryDrawData:
    upload_time = datetime.fromtimestamp(mysekai_info['updatedResources']['now'] / 1000)
    schedule = mysekai_info.get('mysekaiPhenomenaSchedules', [])
    phenom_imgs, phenom_ids = [], []
    for item in schedule:
        phenom_data = loader.md.mysekai_phenomenas.find_by_id(item['mysekaiPhenomenaId'])
        if phenom_data: phenom_imgs.append(loader.rip.img(f"mysekai/thumbnail/phenomena/{phenom_data['iconAssetbundleName']}.png")); phenom_ids.append(item['mysekaiPhenomenaId'])
    current_hour = upload_time.hour; phenom_idx = 1 if current_hour < 4 or current_hour >= 16 else 0
    current_phenomenon_id = phenom_ids[phenom_idx] if phenom_idx < len(phenom_ids) else 1
    weather = WeatherInfo(phenom_imgs, current_phenomenon_id, phenom_idx)
    chara_visit_data = mysekai_info.get('userMysekaiGateCharacterVisit', {}); user_gate = chara_visit_data.get('userMysekaiGate', {})
    gate_id, gate_level = user_gate.get('mysekaiGateId', 1), user_gate.get('mysekaiGateLevel', 1)
    gate_icon = loader.get(f'mysekai/gate_icon/gate_{gate_id}.png')
    visited_characters_raw = [_get_character_sd_image(loader, item['mysekaiGameCharacterUnitGroupId']) for item in chara_visit_data.get('userMysekaiGateCharacters', [])]
    visited_characters = [VisitedCharacter(img) for img in visited_characters_raw if img.width > 1]
    site_res_num = {site_id: {} for site_id in SITE_ID_ORDER}
    for site_map in mysekai_info.get('updatedResources', {}).get('userMysekaiHarvestMaps', []):
        site_id = site_map.get('mysekaiSiteId')
        if site_id not in site_res_num: continue
        for res_drop in site_map.get('userMysekaiSiteHarvestResourceDrops', []):
            if not show_harvested and res_drop.get('mysekaiSiteHarvestResourceDropStatus') != "before_drop": continue
            res_key = f"{res_drop['resourceType']}_{res_drop['resourceId']}"; site_res_num[site_id][res_key] = site_res_num[site_id].get(res_key, 0) + res_drop['quantity']
    user_music_records = {item['mysekaiMusicRecordId'] for item in mysekai_info.get('updatedResources', {}).get('userMysekaiMusicRecords', [])}

    site_summaries = []
    for site_id in SITE_ID_ORDER:
        res_map = site_res_num.get(site_id, {})
        if not res_map:
            print(f"[Extractor] Summary: No resource data found for site_id {site_id}. Skipping summary entry.")
            continue

        def get_res_order(item):
            key, num = item; order = num;
            if key in MOST_RARE_MYSEKAI_RES: order -= 1000000
            elif key in RARE_MYSEKAI_RES: order -= 100000
            return order

        sorted_res = sorted(res_map.items(), key=get_res_order, reverse=True)
        res_items = [ResourceItem(key, qty, _get_resource_icon(loader, key), key in RARE_MYSEKAI_RES, key in MOST_RARE_MYSEKAI_RES, (key.startswith("mysekai_music_record") and int(key.split("_")[-1]) in user_music_records)) for key, qty in sorted_res]

        correct_image_filename = SUMMARY_PREVIEW_IMAGE_MAP.get(site_id, f"{site_id}.png")
        site_img = loader.get(f"mysekai/site_map/{correct_image_filename}")

        site_summaries.append(SiteResourceSummary(site_id, site_img, res_items))

    return SummaryDrawData(weather, gate_icon, gate_level, visited_characters, site_summaries)

def extract_all_harvest_map_data(mysekai_info: dict, loader: LocalAssetLoader, show_harvested: bool) -> List[HarvestMapDrawData]:
    map_data_list = []
    maps_by_id = {site_map['mysekaiSiteId']: site_map for site_map in mysekai_info.get('updatedResources', {}).get('userMysekaiHarvestMaps', [])}
    for site_id in SITE_ID_ORDER:
        if site_id in maps_by_id:
            site_map_json = maps_by_id[site_id]
            map_data_list.append(_extract_single_harvest_map_data(site_map_json, loader, show_harvested))
        else:
            print(f"[Extractor] Map: No map data found for site_id {site_id}. Skipping map generation.")
    return map_data_list

def _extract_single_harvest_map_data(site_map_info: dict, loader: LocalAssetLoader, show_harvested: bool) -> HarvestMapDrawData:
    site_id = site_map_info['mysekaiSiteId']
    config = SITE_MAP_CONFIGS[site_id]
    scale = MYSEKAI_HARVEST_MAP_IMAGE_SCALE

    large_bg = loader.get(config['image'])
    large_bg_scaled = large_bg.resize((int(large_bg.width * scale), int(large_bg.height * scale)), Image.Resampling.LANCZOS)

    final_bg = large_bg_scaled; crop_x_offset, crop_y_offset = 0, 0
    if ENABLE_MAP_CROPPING and 'crop_bbox' in config:
        bbox = config['crop_bbox']
        crop_box = (int(bbox[0] * scale), int(bbox[1] * scale), int((bbox[0] + bbox[2]) * scale), int((bbox[1] + bbox[3]) * scale))
        final_bg = large_bg_scaled.crop(crop_box)
        crop_x_offset, crop_y_offset = int(bbox[0] * scale), int(bbox[1] * scale)

    def game_pos_to_draw_pos(x_game, z_game):
        scaled_grid = config['grid_size'] * scale
        offset_x = config['offset_x']
        offset_z = config['offset_z']

        if config['rev_xz']: x_game, z_game = z_game, x_game

        x_large = (x_game * scaled_grid * config['dir_x']) + large_bg_scaled.width / 2 + offset_x
        z_large = (z_game * scaled_grid * config['dir_z']) + large_bg_scaled.height / 2 + offset_z

        return int(x_large - crop_x_offset), int(z_large - crop_y_offset)

    harvest_points = []
    for item in site_map_info.get('userMysekaiSiteHarvestFixtures', []):
        if not show_harvested and item.get('userMysekaiSiteHarvestFixtureStatus') != "spawned": continue
        x, y = game_pos_to_draw_pos(item['positionX'], item['positionZ'])
        meta = loader.md.mysekai_site_harvest_fixtures.find_by_id(item['mysekaiSiteHarvestFixtureId'])
        img = UNKNOWN_IMG
        if meta:
            img_path = f"mysekai/harvest_fixture_icon/{meta['mysekaiSiteHarvestFixtureRarityType']}/{meta['assetbundleName']}.png"
            img = loader.get(img_path)
        point_img_size = int(160 * scale)
        resized_img = img.resize((point_img_size, point_img_size), Image.Resampling.LANCZOS) if img.width > 1 else img
        harvest_points.append(HarvestPoint(image=resized_img, x=x, y=y))

    all_res_aggregated = {}
    for item in site_map_info.get('userMysekaiSiteHarvestResourceDrops', []):
        if not show_harvested and item['mysekaiSiteHarvestResourceDropStatus'] != "before_drop": continue
        center_x, center_z = game_pos_to_draw_pos(item['positionX'], item['positionZ'])
        pkey = f"{center_x}_{center_z}"; res_key = f"{item['resourceType']}_{item['resourceId']}"
        if pkey not in all_res_aggregated: all_res_aggregated[pkey] = {}
        if res_key not in all_res_aggregated[pkey]: all_res_aggregated[pkey][res_key] = {'quantity': 0, 'center_x': center_x, 'center_z': center_z, 'key': res_key}
        all_res_aggregated[pkey][res_key]['quantity'] += item['quantity']

    dropped_resources = []
    point_img_size_for_offset = 160 * scale
    global_zoffset = -point_img_size_for_offset * 0.2
    for pkey, res_group in all_res_aggregated.items():
        pres = sorted(list(res_group.values()), key=lambda x: (-x['quantity'], x['key']))
        is_cotton = any(item['key'] in ['mysekai_material_21', 'mysekai_material_22'] for item in pres)
        has_mat = any(item['key'].startswith("mysekai_material") for item in pres)
        small_total, large_total, processed_pres = 0, 0, []
        for item in pres:
            is_small = False
            if ('mysekai_material_1' in item['key'] or 'mysekai_material_6' in item['key']) and item['quantity'] == 6: continue
            if not item['key'].startswith("mysekai_material") and has_mat: is_small = True
            if is_cotton and item['key'] not in ['mysekai_material_21', 'mysekai_material_22']: is_small = True
            if is_small: small_total += 1
            else: large_total += 1
            processed_pres.append((item, is_small))

        small_idx, large_idx = 0, 0
        for item, is_small in processed_pres:
            res_key = item['key']; large_size, small_size = int(35 * scale), int(17 * scale)
            size, light_size, outline = 0, None, None; center_x, center_z = item['center_x'], item['center_z']; top_left_x, top_left_z = 0, 0
            if is_small:
                size = small_size; top_left_x = int(center_x + 0.5 * large_size * large_total - 0.6 * small_size)
                top_left_z = int(center_z - 0.45 * large_size + 1.0 * small_size * small_idx + global_zoffset)
                small_idx += 1; outline = ((50, 50, 255, 100), 1)
            else:
                size = large_size; top_left_x = int(center_x - 0.5 * large_size * large_total + large_size * large_idx)
                top_left_z = int(center_z - 0.5 * large_size + global_zoffset); large_idx += 1
            if top_left_z <= 0: top_left_z += int(0.5 * large_size)
            if res_key in MOST_RARE_MYSEKAI_RES: outline = ((255, 50, 50, 150), 2); light_size = int(45 * scale * (3 if is_small else 6))
            draw_order = item['center_z'] * 1000 + item['center_x']
            if is_small: draw_order += 1000000
            elif res_key in MOST_RARE_MYSEKAI_RES: draw_order += 100000
            dropped_resources.append(DroppedResource(image=_get_resource_icon(loader, res_key), quantity=item['quantity'], x=top_left_x, z=top_left_z, size=size, draw_order=draw_order, is_small_icon=is_small, outline=outline, light_size=light_size))
    dropped_resources.sort(key=lambda r: r.draw_order)

    return HarvestMapDrawData(site_id, final_bg, final_bg.width, final_bg.height, spawn_point=game_pos_to_draw_pos(0, 0), harvest_points=harvest_points, dropped_resources=dropped_resources)