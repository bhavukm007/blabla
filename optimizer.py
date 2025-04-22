# optimizer.py

import osmnx as ox
import networkx as nx
import folium
import pyproj
from geopy.geocoders import Nominatim
from shapely.geometry import LineString
from shapely.ops import transform

geolocator = Nominatim(user_agent="my_geo_app")

mode_speed_map = {
    "Car": 60,
    "Bus": 40,
    "Bike": 50,
    "Walking": 5
}

def get_location(city):
    location = geolocator.geocode(city)
    return (location.latitude, location.longitude) if location else None

def compute_route(start, end, fuel_price, mode, override_speed=None):
    source_coords = get_location(start)
    destination_coords = get_location(end)
    if not source_coords or not destination_coords:
        return None, "Invalid start or end location."

    lat_center = (source_coords[0] + destination_coords[0]) / 2
    lon_center = (source_coords[1] + destination_coords[1]) / 2
    G = ox.graph_from_point((lat_center, lon_center), dist=5000, network_type='drive')

    orig_node = ox.distance.nearest_nodes(G, X=source_coords[1], Y=source_coords[0])
    dest_node = ox.distance.nearest_nodes(G, X=destination_coords[1], Y=destination_coords[0])
    shortest_route = nx.shortest_path(G, orig_node, dest_node, weight="length")

    def compute_path_info(path):
        edges = list(zip(path[:-1], path[1:]))
        total_length_m = sum(G[u][v][0].get("length", 0) for u, v in edges)
        return total_length_m / 1000  # in km

    def offset_coords(coords, offset_meters):
        if len(coords) < 2:
            return coords
        proj = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
        back_proj = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
        line = LineString([(lon, lat) for lat, lon in coords])
        line_proj = transform(proj, line)
        offset_line = line_proj.parallel_offset(offset_meters, 'left', join_style=2)
        offset_back = transform(back_proj, offset_line)
        return [(lat, lon) for lon, lat in offset_back.coords]

    G_temp = G.copy()
    second_route = None
    if len(shortest_route) > 1:
        edge_to_remove = (shortest_route[0], shortest_route[1])
        if G_temp.has_edge(*edge_to_remove):
            G_temp.remove_edge(*edge_to_remove)
        try:
            second_route = nx.shortest_path(G_temp, orig_node, dest_node, weight="length")
        except nx.NetworkXNoPath:
            pass

    speed = override_speed if override_speed else mode_speed_map.get(mode, 60)

    def route_stats(route, color):
        coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
        distance_km = compute_path_info(route)
        time = distance_km / speed
        cost = distance_km * fuel_price
        return {
            "coords": coords,
            "distance": round(distance_km, 2),
            "time": round(time, 2),
            "hours": int(time),
            "minutes": int((time - int(time)) * 60),
            "cost": round(cost, 2),
            "color": color
        }

    paths = {"shortest": route_stats(shortest_route, "green")}
    if second_route:
        second = route_stats(second_route, "red")
        second["coords"] = offset_coords(second["coords"], 6)
        paths["second_shortest"] = second

    m = folium.Map(location=source_coords, zoom_start=13)
    folium.Marker(source_coords, popup="Start: " + start, icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(destination_coords, popup="End: " + end, icon=folium.Icon(color="red")).add_to(m)

    for key in paths:
        folium.PolyLine(locations=paths[key]["coords"], color=paths[key]["color"], weight=6, opacity=0.9).add_to(m)

    m.save("templates/map.html")

    paths["shortest"]["start_coords"] = source_coords
    paths["shortest"]["end_coords"] = destination_coords

    return paths, None
