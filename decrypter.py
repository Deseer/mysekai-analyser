import orjson
import msgpack
import asyncio
import configs
import aiofiles
from pathlib import Path
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def decrypt_aes_cbc_pkcs7(encrypted_data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    使用 AES 解密数据
    """
    if isinstance(key, bytearray):
        key = bytes(key)
    if isinstance(iv, bytearray):
        iv = bytes(iv)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    unpadded_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()

    return unpadded_data

# 解密并解析 JSON/MessagePack 的函数
async def decrypt_and_parse_data(encrypted_data_bytes: bytes) -> dict:
    """
    解密数据
    """
    aes_key_bytes = configs.aes_key_bytes
    aes_iv_bytes = configs.aes_iv_bytes

    # 解密数据
    decrypted_bytes = decrypt_aes_cbc_pkcs7(encrypted_data_bytes, aes_key_bytes, aes_iv_bytes)
    print(f"解密后的原始字节数据长度: {len(decrypted_bytes)}")
    parsed_data = msgpack.unpackb(decrypted_bytes, raw=False)
    print("成功使用 MessagePack 解包。")
    return parsed_data

async def main():
    profile_file_path = Path("mysekai.bin")

    if not profile_file_path.exists():
        print(f"错误：文件 '{profile_file_path}' 不存在。请确保文件路径正确。")
        return

    try:
        async with aiofiles.open(profile_file_path, "rb") as f:
            encrypted_data_from_file = await f.read()

        print(f"成功读取加密文件：{profile_file_path}，大小：{len(encrypted_data_from_file)} 字节。")

        decoded_data = await decrypt_and_parse_data(encrypted_data_from_file)

        print(orjson.dumps(decoded_data, option=orjson.OPT_INDENT_2).decode('utf-8'))
        with open(f"{profile_file_path}".replace(".bin", ".json"), "wb") as f:
            f.write(orjson.dumps(decoded_data, option=orjson.OPT_INDENT_2))

    except Exception as e:
        print(f"处理文件或解密时发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())