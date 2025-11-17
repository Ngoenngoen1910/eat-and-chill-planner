# File: backend/osm_search.py
# OpenStreetMap Search + OSRM Routing Integration

from geopy.distance import geodesic
import requests

OSRM_API = "http://router.project-osrm.org/route/v1/driving"
OVERPASS_API = "https://overpass-api.de/api/interpreter"


def search_osm_overpass(query: str, lat: float, lon: float, radius_km: float = 5, limit: int = 10):
    """Search for POIs using Overpass API"""
    try:
        # Map keywords to OSM tags
        osm_tag_map = {
            "restaurant": "amenity=restaurant",
            "cafe": "amenity=cafe",
            "coffee": "amenity=cafe",
            "nhà hàng": "amenity=restaurant",
            "quán": "amenity=restaurant",
            "cà phê": "amenity=cafe",
            "ăn": "amenity=restaurant",
        }
        
        # Find matching tag
        osm_tag = None
        query_lower = query.lower().strip()
        for key, tag in osm_tag_map.items():
            if key in query_lower:
                osm_tag = tag
                break
        
        if not osm_tag:
            osm_tag = "amenity=restaurant"
        
        # Calculate bounding box
        radius_deg = radius_km / 111.0
        bbox_str = f"{lat - radius_deg},{lon - radius_deg},{lat + radius_deg},{lon + radius_deg}"
        
        # Overpass query
        overpass_query = f"""
        [out:json];
        (
          node[{osm_tag}]({bbox_str});
          way[{osm_tag}]({bbox_str});
          relation[{osm_tag}]({bbox_str});
        );
        out center;
        """
        
        response = requests.post(OVERPASS_API, data=overpass_query, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        user_loc = (lat, lon)
        
        for element in data.get('elements', [])[:limit*2]:
            try:
                if 'center' in element:
                    el_lat = element['center']['lat']
                    el_lon = element['center']['lon']
                elif 'lat' in element:
                    el_lat = element['lat']
                    el_lon = element['lon']
                else:
                    continue
                
                name = element.get('tags', {}).get('name', 'Unnamed')
                place_loc = (el_lat, el_lon)
                distance = geodesic(user_loc, place_loc).km
                
                if distance > radius_km:
                    continue
                
                rating = None
                if 'tags' in element:
                    rating_str = element['tags'].get('rating')
                    if rating_str:
                        try:
                            rating = float(rating_str)
                        except:
                            rating = None
                
                # Include all OSM tags for filtering later
                tags = element.get('tags', {})
                
                results.append({
                    "name": name,
                    "address": tags.get('addr:full', name),
                    "lat": el_lat,
                    "lon": el_lon,
                    "distance": round(distance, 2),
                    "rating": rating,
                    "place_id": element.get('id', ''),
                    "source": "OpenStreetMap (Overpass)",
                    "tags": tags  # Include full OSM tags
                })
                
                if len(results) >= limit:
                    break
                    
            except:
                continue
        
        results.sort(key=lambda x: x['distance'])
        return results
        
    except Exception as e:
        print(f"Overpass Error: {e}")
        return []


def search_osm(query: str, lat: float, lon: float, radius_km: float = 5, limit: int = 10):
    """Search for places on OpenStreetMap"""
    results = search_osm_overpass(query, lat, lon, radius_km, limit)
    return results


def matches_food_filters(place_tags: dict, filters: dict) -> bool:
    """Check if a food place matches the user's filters."""
    tags = place_tags or {}
    
    # Check loại hình (food_type): nhà hàng, quán ăn, cafe, bar, buffet
    if filters.get("food_type"):
        amenity = tags.get('amenity', '').lower()
        name = tags.get('name', '').lower()
        food_types_lower = [ft.lower() for ft in filters["food_type"]]
        
        matched = False
        if 'quán ăn' in food_types_lower or 'nhà hàng' in food_types_lower:
            if amenity in ['restaurant', 'fast_food'] or 'nhà hàng' in name or 'quán ăn' in name:
                matched = True
        if 'cafe' in food_types_lower or 'đồ uống' in food_types_lower:
            if amenity in ['cafe', 'bar', 'pub'] or 'cafe' in name or 'coffee' in name:
                matched = True
        if 'bar' in food_types_lower:
            if amenity in ['bar', 'pub'] or 'bar' in name:
                matched = True
        if 'buffet' in food_types_lower:
            if 'buffet' in name:
                matched = True
        
        if not matched:
            return False
    
    # Check ẩm thực: Món Việt, Món Á, Món Âu, Chay
    if filters.get("cuisine"):
        cuisine_tag = tags.get('cuisine', '').lower()
        name = tags.get('name', '').lower()
        cuisine_filter_lower = [c.lower() for c in filters["cuisine"]]
        
        matched = False
        for cuisine_filter in cuisine_filter_lower:
            if 'món việt' in cuisine_filter:
                if 'vietnamese' in cuisine_tag or 'phở' in name or 'bún' in name or 'cơm' in name:
                    matched = True
            if 'mon á' in cuisine_filter or 'món á' in cuisine_filter:
                if 'asian' in cuisine_tag or 'japanese' in cuisine_tag or 'korean' in cuisine_tag or 'thai' in cuisine_tag:
                    matched = True
            if 'mon âu' in cuisine_filter or 'món âu' in cuisine_filter:
                if 'french' in cuisine_tag or 'italian' in cuisine_tag or 'european' in cuisine_tag:
                    matched = True
            if 'chay' in cuisine_filter:
                if 'vegan' in cuisine_tag or 'vegetarian' in cuisine_tag:
                    matched = True
        
        # If filters specified, only return if matched
        if cuisine_filter_lower and not matched:
            return False
    
    # Check không khí: yên tĩnh, lãng mạn, sôi động
    if filters.get("atmosphere"):
        outdoor = tags.get('outdoor_seating', 'no').lower() == 'yes'
        atmosphere_lower = [a.lower() for a in filters["atmosphere"]]
        
        if 'yên tĩnh' in atmosphere_lower and outdoor:
            return False  # Outdoor usually means noisier
        if 'lãng mạn' in atmosphere_lower:
            name_lower = tags.get('name', '').lower()
            if 'fast_food' in name_lower or 'quick' in name_lower:
                return False
    
    # Check mức giá
    if filters.get("price"):
        price_tag = tags.get('price', '').lower()
        price_filter = filters["price"].lower()
        
        if price_tag:
            dollar_count = price_tag.count('$')
            if price_filter == 'cao' and dollar_count < 2:
                return False  # Expect $$$
            if price_filter == 'thấp' and dollar_count > 1:
                return False  # Expect $
    
    return True


def matches_entertainment_filters(place_tags: dict, filters: dict) -> bool:
    """Check if an entertainment place matches the user's filters."""
    tags = place_tags or {}
    
    # Check loại hình hoạt động
    if filters.get("activity_type"):
        amenity = tags.get('amenity', '').lower()
        name = tags.get('name', '').lower()
        activity_types_lower = [at.lower() for at in filters["activity_type"]]
        
        matched = False
        for activity_filter in activity_types_lower:
            if 'xem phim' in activity_filter:
                if 'cinema' in amenity or 'theater' in amenity or 'phim' in name:
                    matched = True
            if 'triển lãm' in activity_filter:
                if 'museum' in amenity or 'gallery' in amenity or 'triển lãm' in name:
                    matched = True
            if 'thể thao' in activity_filter:
                if 'sports' in amenity or 'gym' in amenity or 'fitness' in amenity:
                    matched = True
            if 'karaoke' in activity_filter:
                if 'karaoke' in amenity or 'karaoke' in name:
                    matched = True
            if 'mua sắm' in activity_filter:
                if 'shop' in amenity or 'mall' in amenity or 'market' in amenity or 'shop' in name:
                    matched = True
        
        if activity_types_lower and not matched:
            return False
    
    # Check không gian: trong nhà, ngoài trời
    if filters.get("space"):
        outdoor = tags.get('outdoor_seating', 'no').lower() == 'yes'
        space = filters["space"].lower()
        
        if 'trong nhà' in space and outdoor:
            return False
        # Don't exclude based on 'ngoài trời' since not all places have outdoor_seating tag
    
    # Check mức giá
    if filters.get("price"):
        price_tag = tags.get('price', '').lower()
        price_filter = filters["price"].lower()
        
        if price_tag:
            dollar_count = price_tag.count('$')
            if price_filter == 'cao' and dollar_count < 2:
                return False
            if price_filter == 'thấp' and dollar_count > 1:
                return False
    
    return True


def get_osrm_route(start_lat: float, start_lon: float, 
                   end_lat: float, end_lon: float,
                   waypoints: list = None):
    """Get routing coordinates from OSRM"""
    try:
        coords = f"{start_lon},{start_lat}"
        
        if waypoints:
            for wp in waypoints:
                coords += f";{wp[1]},{wp[0]}"
        
        coords += f";{end_lon},{end_lat}"
        
        url = f"{OSRM_API}/{coords}"
        params = {
            "overview": "full",
            "steps": "true",
            "geometries": "geojson"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('code') != 'Ok':
            return {
                "route": [(start_lat, start_lon), (end_lat, end_lon)],
                "distance_km": round(geodesic((start_lat, start_lon), (end_lat, end_lon)).km, 2),
                "duration_seconds": 0,
                "source": "fallback"
            }
        
        route = data.get('routes', [{}])[0]
        geometry = route.get('geometry', {}).get('coordinates', [])
        route_points = [(coord[1], coord[0]) for coord in geometry]
        
        return {
            "route": route_points,
            "distance_km": round(route.get('distance', 0) / 1000, 2),
            "duration_seconds": int(route.get('duration', 0)),
            "duration_minutes": round(route.get('duration', 0) / 60, 1),
            "source": "OSRM"
        }
    
    except Exception as e:
        print(f"OSRM Error: {e}")
        return {
            "route": [(start_lat, start_lon), (end_lat, end_lon)],
            "distance_km": round(geodesic((start_lat, start_lon), (end_lat, end_lon)).km, 2),
            "duration_seconds": 0,
            "source": "fallback"
        }
