import asyncio
import math
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
            print(f"[{drone_name}] {retry_interval} saniye sonra tekrar denenecek...")
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

async def print_position(drone, drone_name):
    async for position in drone.telemetry.position():
        altitude = position.absolute_altitude_m or 0.0
        latitude = position.latitude_deg
        longitude = position.longitude_deg
        print(f"[{drone_name}] Enlem: {latitude:.8f}, Boylam: {longitude:.8f}, Yükseklik: {altitude:.2f} m")
        await asyncio.sleep(1)

def get_circle_waypoints(center_lat, center_lon, radius_m, altitude_m, num_points=36):
    earth_radius = 6378137.0  # Dünya yarıçapı (metre)
    waypoints = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        d_lat = (radius_m * math.cos(angle)) / earth_radius
        d_lon = (radius_m * math.sin(angle)) / (earth_radius * math.cos(math.radians(center_lat)))
        lat = center_lat + math.degrees(d_lat)
        lon = center_lon + math.degrees(d_lon)
        waypoints.append((lat, lon, altitude_m))
    return waypoints

async def fly_circle(drone, drone_name, center_lat, center_lon, radius_m, altitude_m):
    waypoints = get_circle_waypoints(center_lat, center_lon, radius_m, altitude_m)
    print(f"[{drone_name}] {len(waypoints)} noktadan oluşan çember uçuşu başlıyor (Yarıçap: {radius_m:.1f} m)")

    for idx, (lat, lon, alt) in enumerate(waypoints):
        print(f"[{drone_name}] Nokta {idx+1}: Enlem={lat:.8f}, Boylam={lon:.8f}, İrtifa={alt:.2f} m")
        await drone.action.goto_location(lat, lon, alt, 0)
        await asyncio.sleep(2)  # Noktalar arası bekleme süresi

    print(f"[{drone_name}] {radius_m:.1f} m yarıçaplı çember tamamlandı.")

async def spiral_scan(drone, drone_name, initial_radius, min_radius, step_radius, altitude_m):
    # Başlangıç konumu merkez olarak alınır
    print(f"[{drone_name}] Başlangıç konumu alınıyor...")
    async for position in drone.telemetry.position():
        center_lat = position.latitude_deg
        center_lon = position.longitude_deg
        break

    current_radius = initial_radius

    while current_radius >= min_radius:
        await fly_circle(drone, drone_name, center_lat, center_lon, current_radius, altitude_m)
        current_radius -= step_radius

    print(f"[{drone_name}] Spiral tarama tamamlandı.")

async def run():
    drone = System()
    drone_address = "udp://:14541"
    drone_name = "Drone1"

    await connect_with_retry(drone, drone_name, drone_address)
    print("\n=== Drone bağlandı. Görev başlatılıyor ===\n")

    # Pozisyon yazdırma görevi paralel çalışsın
    altitude_task = asyncio.create_task(print_position(drone, drone_name))

    await arm_and_takeoff(drone, drone_name, 20)

    # Spiral tarama parametreleri
    initial_radius = 8  # metre
    min_radius = 1       # metre
    step_radius = 2      # her turda ne kadar küçülsün
    spiral_altitude = 10 # metre

    await spiral_scan(drone, drone_name, initial_radius, min_radius, step_radius, spiral_altitude)

    print("\n=== Spiral tarama tamamlandı. İniş başlıyor ===\n")

    await land(drone, drone_name)

    # Pozisyon yazdırma görevini durdur
    altitude_task.cancel()
    try:
        await altitude_task
    except asyncio.CancelledError:
        print(f"[{drone_name}] Pozisyon yazdırma durduruldu.")

    print("\n=== Görev tamamlandı. Script bitiyor ===")

if __name__ == "__main__":
    asyncio.run(run())

