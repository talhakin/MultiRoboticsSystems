import asyncio
import math
import random
from mavsdk import System

async def connect_with_retry(drone, drone_name, system_address, retry_interval=2):
    print(f"[{drone_name}] {system_address} adresine bağlanıyor...")
    while True:
        try:
            await drone.connect(system_address=system_address)
            async for state in drone.core.connection_state():
                if state.is_connected:
                    print(f"[{drone_name}] BAĞLANDI!")
                    return
                else:
                    print(f"[{drone_name}] Henüz bağlı değil, {retry_interval} saniye sonra tekrar denenecek...")
                    await asyncio.sleep(retry_interval)
        except Exception as e:
            print(f"[{drone_name}] Bağlantı hatası: {e}")
            await asyncio.sleep(retry_interval)

async def arm_and_takeoff(drone, drone_name, altitude_m):
    print(f"[{drone_name}] Arm komutu gönderiliyor...")
    await drone.action.arm()
    print(f"[{drone_name}] Kalkış başlatılıyor (Hedef irtifa: {altitude_m} m)...")
    await drone.action.takeoff()
    await asyncio.sleep(10)
    print(f"[{drone_name}] Kalkış tamamlandı.")

async def land(drone, drone_name):
    print(f"[{drone_name}] İniş başlatılıyor...")
    await drone.action.land()
    await asyncio.sleep(10)
    print(f"[{drone_name}] İniş tamamlandı.")

def generate_random_targets(center_lat, center_lon, area_side_m=3.16, num_targets=25, altitude_m=10):
    """
    10 m² (yaklaşık 3.16 x 3.16 m) kare alan içinde random GPS noktaları üretir.
    """
    earth_radius = 6378137.0  # metre
    half_side = area_side_m / 2.0
    targets = set()

    while len(targets) < num_targets:
        dx = random.uniform(-half_side, half_side)
        dy = random.uniform(-half_side, half_side)

        d_lat = dy / earth_radius
        d_lon = dx / (earth_radius * math.cos(math.radians(center_lat)))

        lat = center_lat + math.degrees(d_lat)
        lon = center_lon + math.degrees(d_lon)

        targets.add((round(lat, 8), round(lon, 8)))  # hassasiyet + tekrar engelleme

    return [(lat, lon, altitude_m) for lat, lon in targets]

async def random_scan(drone, drone_name, altitude_m):
    print(f"[{drone_name}] Başlangıç konumu alınıyor...")
    async for position in drone.telemetry.position():
        center_lat = position.latitude_deg
        center_lon = position.longitude_deg
        break

    targets = generate_random_targets(center_lat, center_lon, area_side_m=3.16, num_targets=20, altitude_m=altitude_m)
    print(f"[{drone_name}] {len(targets)} adet rastgele hedef oluşturuldu.")

    for idx, (lat, lon, alt) in enumerate(targets):
        print(f"[{drone_name}] Hedef {idx+1}: Enlem={lat:.8f}, Boylam={lon:.8f}")
        await drone.action.goto_location(lat, lon, alt, 0)
        await asyncio.sleep(4)  # hedefe ulaşma süresi

    print(f"[{drone_name}] Tüm rastgele noktalar ziyaret edildi.")

async def run():
    drone = System()
    drone_name = "Drone2"
    drone_address = "udp://:14542"

    await connect_with_retry(drone, drone_name, drone_address)

    print(f"\n=== {drone_name} bağlandı. Görev başlıyor ===\n")
    altitude_task = asyncio.create_task(print_position(drone, drone_name))

    await arm_and_takeoff(drone, drone_name, altitude_m=10)

    await random_scan(drone, drone_name, altitude_m=10)

    print(f"\n=== Tarama tamamlandı. İniş başlıyor ===\n")
    await land(drone, drone_name)

    altitude_task.cancel()
    try:
        await altitude_task
    except asyncio.CancelledError:
        print(f"[{drone_name}] Pozisyon yazdırma durduruldu.")

    print("\n=== Görev tamamlandı. Script bitiyor ===")

async def print_position(drone, drone_name):
    async for position in drone.telemetry.position():
        alt = position.absolute_altitude_m or 0.0
        print(f"[{drone_name}] Enlem: {position.latitude_deg:.8f}, Boylam: {position.longitude_deg:.8f}, İrtifa: {alt:.2f} m")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run())
