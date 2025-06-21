import subprocess
import re
import math
import time

def parse_pose_block(pose_str):
    pos_match = re.search(r'position\s*{\s*x:\s*([^\s]+)\s*y:\s*([^\s]+)', pose_str)
    if pos_match:
        x, y = map(float, pos_match.groups())
        return x, y
    return None

def extract_id(pose_str):
    id_match = re.search(r'id:\s*(\d+)', pose_str)
    return int(id_match.group(1)) if id_match else None

def distance_2d(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

positions = {10: None, 88: None}

start_time = time.time()  # Kodun başladığı anın zamanı (epoch saniye)

process = subprocess.Popen(
    ['gz', 'topic', '-e', '-t', '/world/default/pose/info'],
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True
)

buffer = ""
for line in process.stdout:
    buffer += line
    if line.strip() == "}":
        entity_id = extract_id(buffer)
        pos = parse_pose_block(buffer)

        elapsed = time.time() - start_time  # Başlangıçtan geçen süre (saniye)
        sim_time = f"{elapsed:.2f}s"       # Formatlı simülasyon saati

        if entity_id in positions and pos:
            positions[entity_id] = pos

            if entity_id == 88:
                print(f"[{sim_time}] [BOX]  Pozisyon: x={pos[0]:.2f}, y={pos[1]:.2f}")

            elif entity_id == 10:
                print(f"[{sim_time}] [ARAÇ] Pozisyon: x={pos[0]:.2f}, y={pos[1]:.2f}")

            if positions[10] is not None and positions[88] is not None:
                dist = distance_2d(positions[10], positions[88])
                print(f"[{sim_time}] [MESAFE] Araç ile Kutu arası uzaklık: {dist:.2f} metre")

                if dist < 2.0:
                    print(f"\n[{sim_time}] [UYARI] Kargo tespit edildi!")
                    print(f"Kutu Pozisyonu: x={positions[88][0]:.2f}, y={positions[88][1]:.2f}")
                    print(f"Araç Pozisyonu: x={positions[10][0]:.2f}, y={positions[10][1]:.2f}")
                    print(f"Uzaklık: {dist:.2f} metre\n")
                    process.terminate()  # Alt süreci durdur
                    break  # Döngüyü kır ve scripti bitir

        buffer = ""

