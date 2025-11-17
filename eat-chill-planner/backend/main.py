# File: backend/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from geopy.distance import geodesic
from backend.osm_search import search_osm, get_osrm_route, matches_food_filters, matches_entertainment_filters

app = FastAPI()

class SearchRequest(BaseModel):
    lat: float
    lon: float
    category: str = None
    keyword: str = None
    filters: dict = None

@app.get("/")
def read_root():
    return {"message": "Welcome to Eat & Chill API"}

@app.post("/api/search")
def search_api(request: SearchRequest):
    # Use OpenStreetMap globally for search with filter matching
    query = request.keyword if request.keyword else (request.category or "")
    raw_results = search_osm(query, request.lat, request.lon, radius_km=5, limit=50)
    
    # Apply filter matching if filters provided
    if request.filters:
        category = request.filters.get("category", "")
        filtered_results = []
        
        for place in raw_results:
            # Extract tags from place dict
            place_tags = place.get("tags", {})
            
            if category == "Ăn uống":
                if matches_food_filters(place_tags, request.filters):
                    filtered_results.append(place)
            elif category == "Giải trí":
                if matches_entertainment_filters(place_tags, request.filters):
                    filtered_results.append(place)
            else:
                filtered_results.append(place)
        
        # Return top results after filtering
        return {"places": filtered_results[:20], "source": "OpenStreetMap"}
    
    return {"places": raw_results[:20], "source": "OpenStreetMap"}

# Thêm vào backend/main.py
from pydantic import BaseModel

# Biến toàn cục lưu lịch trình tạm trong RAM (Để đơn giản hóa, tắt server là mất)
# Nếu muốn lưu lâu dài thì dùng MongoDB như bài trước
current_itinerary = []

class ItineraryItem(BaseModel):
    name: str
    start_time: str # Định dạng "18:00"
    end_time: str   # Định dạng "20:00"
    place_name: str
    lat: float  # Thêm tọa độ
    lon: float  # Thêm tọa độ

@app.get("/api/itinerary")
def get_itinerary():
    # Sắp xếp theo giờ bắt đầu
    sorted_list = sorted(current_itinerary, key=lambda x: x['start_time'])
    
    # Tính toán khoảng cách tích lũy
    result_with_distance = []
    prev_loc = (10.762622, 106.660172) # Vị trí xuất phát mặc định (Quận 10)
    
    for item in sorted_list:
        current_loc = (item['lat'], item['lon'])
        try:
            # Tính khoảng cách từ điểm trước đến điểm này
            dist = round(geodesic(prev_loc, current_loc).km, 2)
        except:
            dist = 0
            
        item['step_distance'] = dist # Thêm thông tin khoảng cách di chuyển
        result_with_distance.append(item)
        
        # Cập nhật điểm trước đó thành điểm hiện tại cho vòng lặp sau
        prev_loc = current_loc
        
    return {"itinerary": result_with_distance}

@app.post("/api/itinerary")
def add_item(item: ItineraryItem):
    """Add an itinerary item with conflict detection."""
    # Check for time conflicts with existing items
    if current_itinerary:
        # Parse time strings for comparison
        new_start = item.start_time
        new_end = item.end_time
        
        for existing_item in current_itinerary:
            existing_start = existing_item.get('start_time')
            existing_end = existing_item.get('end_time')
            
            # Check if new activity overlaps with existing one
            # Overlap occurs if: new_start < existing_end AND new_end > existing_start
            if new_start < existing_end and new_end > existing_start:
                return {
                    "status": "error", 
                    "message": f"Xung đột thời gian! Hoạt động '{existing_item.get('name')}' chạy từ {existing_start} đến {existing_end}."
                }
    
    # No conflict, add the item
    item_dict = item.dict()
    current_itinerary.append(item_dict)
    return {"status": "success", "message": "Đã thêm hoạt động vào lịch trình!"}


# API Reset lịch trình (cho tiện test)
@app.post("/api/itinerary/reset")
def reset_itinerary():
    current_itinerary.clear()
    return {"status": "success"}


# ========== NEW: OpenStreetMap + OSRM APIs ==========

class OSMSearchRequest(BaseModel):
    query: str
    lat: float
    lon: float
    radius_km: float = 5
    limit: int = 10

@app.post("/api/search-osm")
def search_osm_api(request: OSMSearchRequest):
    """Search for places on OpenStreetMap using Nominatim"""
    results = search_osm(request.query, request.lat, request.lon, request.radius_km, request.limit)
    return {"places": results, "source": "OpenStreetMap"}


class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    waypoints: list = []  # List of [lat, lon] pairs

@app.post("/api/route")
def get_route_api(request: RouteRequest):
    """Get optimized route from OSRM"""
    route_data = get_osrm_route(
        request.start_lat, 
        request.start_lon,
        request.end_lat, 
        request.end_lon,
        request.waypoints
    )
    return route_data


class MultiRouteRequest(BaseModel):
    points: list  # List of [lat, lon] pairs to visit in order

@app.post("/api/route-multi")
def get_multi_route_api(request: MultiRouteRequest):
    """Get optimized route visiting multiple points"""
    if len(request.points) < 2:
        return {"status": "error", "message": "Need at least 2 points"}
    
    try:
        start = request.points[0]
        end = request.points[-1]
        waypoints = request.points[1:-1] if len(request.points) > 2 else []
        
        route_data = get_osrm_route(start[0], start[1], end[0], end[1], waypoints)
        return route_data
    except Exception as e:
        return {"status": "error", "message": str(e)}