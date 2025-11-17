# frontend/app.py
import sys
import os
from pathlib import Path

# Add project root to sys.path so imports work from any directory
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

# Cấu hình trang
st.set_page_config(page_title="Eat & Chill Planner", layout="wide")

# Backend server
BACKEND_URL = "http://127.0.0.1:8000"

# Default location - Quận 10, HCMC
DEFAULT_LAT = 10.762622
DEFAULT_LON = 106.660172

st.title("Eat & Chill Planner 🗺️")

# --- Khởi tạo Session State ---
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = []
if 'user_lat' not in st.session_state:
    st.session_state['user_lat'] = DEFAULT_LAT
if 'user_lon' not in st.session_state:
    st.session_state['user_lon'] = DEFAULT_LON
if 'user_address' not in st.session_state:
    st.session_state['user_address'] = ''

# --- Sidebar (Giữ nguyên) ---
with st.sidebar:
    st.header("🔍 Bộ lọc tìm kiếm")
    
    # Location Selection
    st.subheader("📍 Vị trí xuất phát")
    location_option = st.radio("Chọn vị trí:", ["Vị trí hiện tại", "Nhập địa chỉ"])
    
    if location_option == "Vị trí hiện tại":
        st.session_state['user_lat'] = st.session_state.get('user_lat', DEFAULT_LAT)
        st.session_state['user_lon'] = st.session_state.get('user_lon', DEFAULT_LON)
        # (Phần code geocoding... giữ nguyên)
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="eat_chill_planner")
            loc = geolocator.reverse((st.session_state['user_lat'], st.session_state['user_lon']), language='vi')
            if loc and loc.address:
                st.session_state['user_address'] = loc.address
        except Exception:
            pass
        addr = st.session_state.get('user_address')
        if addr:
            st.info(f"📌 Vị trí: {addr}")
        else:
            st.info(f"📌 Vị trí: ({st.session_state['user_lat']:.4f}, {st.session_state['user_lon']:.4f})")
    else:
        # (Phần code nhập địa chỉ... giữ nguyên)
        address_input = st.text_input("Nhập địa chỉ (vd: 227 Nguyễn Văn Cừ...):")
        # ... (Toàn bộ logic xử lý gợi ý địa chỉ giữ nguyên như file của bạn)
        if 'address_suggestions' not in st.session_state: st.session_state['address_suggestions'] = []
        if 'last_suggestions_query' not in st.session_state: st.session_state['last_suggestions_query'] = ''
        query = (address_input or '').strip()
        if len(query) >= 3 and query != st.session_state['last_suggestions_query']:
            try:
                with st.spinner('Đang lấy gợi ý địa chỉ...'):
                    url = 'https://nominatim.openstreetmap.org/search'
                    params = {'q': query, 'format': 'json', 'addressdetails': 1, 'limit': 6, 'accept-language': 'vi'}
                    headers = {'User-Agent': 'eat_chill_planner'}
                    resp = requests.get(url, params=params, headers=headers, timeout=8)
                    suggestions = []
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data:
                            display = item.get('display_name'); lat = float(item.get('lat')); lon = float(item.get('lon')); addr = item.get('address', {}) or {}; has_house = False
                            if isinstance(addr, dict) and addr.get('house_number'): has_house = True
                            try:
                                if any(char.isdigit() for char in display.split(',')[0]): has_house = True
                            except Exception: pass
                            suggestions.append({'display_name': display, 'lat': lat, 'lon': lon, 'has_house': has_house})
                    exact = [s for s in suggestions if s.get('has_house')]
                    if exact: st.session_state['address_suggestions'] = exact
                    else:
                        if any(ch.isdigit() for ch in query):
                            filtered = [s for s in suggestions if query.lower() in (s.get('display_name','').lower())]
                            st.session_state['address_suggestions'] = filtered if filtered else suggestions
                        else: st.session_state['address_suggestions'] = suggestions
                    st.session_state['last_suggestions_query'] = query
            except Exception: st.session_state['address_suggestions'] = []
        suggestions = st.session_state.get('address_suggestions', [])
        if suggestions:
            options = ['-- Chọn gợi ý --'] + [s['display_name'] for s in suggestions]
            sel = st.selectbox('Gợi ý địa chỉ', options=options, index=0)
            if sel and sel != '-- Chọn gợi ý --':
                chosen = next((s for s in suggestions if s['display_name'] == sel), None)
                if chosen:
                    st.session_state['user_lat'] = chosen['lat']; st.session_state['user_lon'] = chosen['lon']; st.session_state['user_address'] = chosen['display_name']; st.session_state['last_suggestions_query'] = sel
        else:
            if query: st.info('Không có gợi ý. Vui lòng kiểm tra lại nội dung tìm kiếm.')

    st.divider()

    # --- Sidebar: Search Filters (Giữ nguyên) ---
    st.header("🔍 Bộ lọc tìm kiếm")
    category = st.selectbox("📂 Danh mục:", ["Ăn uống", "Giải trí"])
    filters = {}
    
    if category == "Ăn uống":
        st.subheader("Ăn uống")
        filters["food_type"] = st.multiselect("🍴 Loại hình:", ["Quán ăn", "Đồ uống", "Ăn vặt", "Bar", "Buffet"], default=[])
        filters["cuisine"] = st.multiselect("🍜 Ẩm thực:", ["Món Việt", "Món Á", "Món Âu", "Chay"], default=[])
        filters["atmosphere"] = st.multiselect("🎵 Không khí:", ["Yên tĩnh", "Lãng mạn", "Sôi động"], default=[])
        filters["price"] = st.radio("💰 Mức giá:", ["Thấp", "Trung bình", "Cao"], index=1)
    
    elif category == "Giải trí":
        st.subheader("Giải trí")
        filters["activity_type"] = st.multiselect("🎬 Loại hình hoạt động:", ["Xem Phim", "Triển lãm", "Thể thao", "Karaoke", "Mua sắm", "Du lịch", "Workshop"], default=[])
        filters["price"] = st.radio("💰 Mức giá:", ["Thấp", "Trung bình", "Cao"], index=1)
        filters["space"] = st.radio("🏠 Không gian:", ["Trong nhà", "Ngoài trời"])
        filters["audience"] = st.multiselect("👥 Đối tượng:", ["Cá nhân", "Cặp đôi", "Nhóm bạn", "Gia đình"], default=[])
    
    radius = st.slider("📍 Bán kính tìm kiếm (km):", 1, 50, 5)
    btn_search = st.button("🔍 Tìm kiếm", use_container_width=True)

# --- Main Content: Search Execution (Giữ nguyên) ---
if btn_search:
    # Build query
    query_parts = [category]
    if category == "Ăn uống":
        if filters.get("food_type"): query_parts.extend(filters["food_type"])
        if filters.get("cuisine"): query_parts.extend(filters["cuisine"])
        if filters.get("atmosphere"): query_parts.extend(filters["atmosphere"])
    elif category == "Giải trí":
        if filters.get("activity_type"): query_parts.extend(filters["activity_type"])
        if filters.get("space"): query_parts.append(filters["space"])
        if filters.get("audience"): query_parts.extend(filters["audience"])
    query = " ".join(query_parts)
    filters["category"] = category
    
    payload = {
        "query": query, "lat": st.session_state['user_lat'], "lon": st.session_state['user_lon'],
        "category": category, "filters": filters
    }
    try:
        with st.spinner("🌍 Tìm kiếm từ OpenStreetMap..."):
            response = requests.post(f"{BACKEND_URL}/api/search", json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json().get("places", [])
                st.session_state['search_results'] = data
                if data:
                    st.success(f"✅ OpenStreetMap tìm thấy {len(data)} kết quả phù hợp!")
                else:
                    st.warning("⚠️ Không tìm thấy kết quả nào phù hợp với bộ lọc của bạn")
            else:
                st.error(f"Lỗi Server: {response.status_code}")
    except requests.exceptions.Timeout:
        st.error("❌ Timeout - OpenStreetMap không phản hồi (có thể bận)")
    except Exception as e:
        st.error(f"❌ Lỗi OSM: {str(e)[:200]}")

# --- (ĐÃ XÓA) Phần "Lịch trình & Bản đồ" preview ở đây ---

st.markdown("---")

# --- BỐ CỤC MỚI: Tách 2 cột trên cùng ---
top_col1, top_col2 = st.columns([1, 1])

with top_col1:
    # --- PHẦN 1: Danh sách quán đề xuất ---
    st.subheader("🌟 Danh sách quán đề xuất")
    if 'search_results' in st.session_state and st.session_state['search_results']:
        results = st.session_state['search_results']
        
        # Tạo container scroll
        list_container = st.container(height=400) # Đặt chiều cao cố định
        
        for idx, place in enumerate(results):
            rating_display = f"⭐ {place.get('rating', 'N/A')}" if place.get('rating') else "⭐ Chưa có đánh giá"
            with list_container.expander(f"{place['name']} ({place['distance']} km) - {rating_display}"):
                st.write(f"📍 Đ/c: {place.get('address', 'N/A')}")
                st.write(f"💰 Giá: {place.get('attributes', {}).get('price', 'N/A')}")
                unique_key = place.get('_id') or place.get('place_id') or f"place_{idx}"
                
                # Nút 'Thêm vào lịch' sẽ tự động cập nhật Form bên cạnh
                # (Lưu ý: Cách tốt nhất là bấm nút này, nó tự điền vào Form)
                # Để đơn giản, ta giữ logic Form riêng biệt
                
    else:
        st.info("Nhấn 'Tìm kiếm' ở cột bên trái để thấy kết quả.")

with top_col2:
    # --- PHẦN 2: Lịch trình (Form thêm) ---
    st.subheader("📅 Thêm vào lịch trình")
    
    with st.form("add_schedule"):
        st.caption("Chọn địa điểm từ danh sách bên trái và thêm vào lịch:")
        
        if 'search_results' in st.session_state and st.session_state['search_results']:
            place_options = {p['name']: p for p in st.session_state['search_results']}
            selected_name = st.selectbox("Chọn địa điểm:", list(place_options.keys()))
            selected_place_data = place_options.get(selected_name)
        else:
            st.warning("Tìm kiếm địa điểm trước...")
            selected_place_data = None

        act_name = st.text_input("Tên hoạt động (vd: Ăn tối)", value="Ăn uống")
        c1, c2 = st.columns(2)
        t_start = c1.time_input("Bắt đầu")
        t_end = c2.time_input("Kết thúc")
        
        sub_btn = st.form_submit_button("Thêm vào lịch")
        
        if sub_btn and selected_place_data:
            if 'location' in selected_place_data and 'coordinates' in selected_place_data['location']:
                coords = selected_place_data['location']['coordinates']
                lat, lon = coords[1], coords[0]
            else:
                lat = selected_place_data.get('lat', selected_place_data.get('latitude'))
                lon = selected_place_data.get('lon', selected_place_data.get('longitude'))
            
            payload = {
                "name": act_name, "place_name": selected_place_data['name'],
                "start_time": str(t_start)[:5], "end_time": str(t_end)[:5],
                "lat": lat, "lon": lon
            }
            
            try:
                res = requests.post(f"{BACKEND_URL}/api/itinerary", json=payload)
                if res.json().get("status") == "success":
                    st.success("Đã thêm!")
                    st.rerun() # Tải lại để cập nhật bản đồ
                else:
                    st.error(res.json().get("message"))
            except:
                st.error("Lỗi kết nối Server")

st.markdown("---")

# --- PHẦN 3: Lộ trình di chuyển (Bản đồ OSRM) ---
st.subheader("🗺️ Lộ trình di chuyển (OSRM Routing)")
try:
    res_iti_map = requests.get(f"{BACKEND_URL}/api/itinerary")
    items_map = res_iti_map.json().get("itinerary", [])
    
    user_lat_map = st.session_state.get('user_lat', DEFAULT_LAT)
    user_lon_map = st.session_state.get('user_lon', DEFAULT_LON)
    m = folium.Map(location=[user_lat_map, user_lon_map], zoom_start=14)
    folium.Marker([user_lat_map, user_lon_map], icon=folium.Icon(color="red", icon="home"), popup="🏠 Xuất phát").add_to(m)

    total_distance_osrm = 0
    total_duration = 0
    route_segments_map = [] # Dùng để tính toán

    if items_map:
        all_points = [[user_lat_map, user_lon_map]]
        for item in items_map:
            all_points.append([item['lat'], item['lon']])

        for i in range(len(all_points) - 1):
            try:
                route_payload = {
                    "start_lat": all_points[i][0], "start_lon": all_points[i][1],
                    "end_lat": all_points[i+1][0], "end_lon": all_points[i+1][1]
                }
                route_res = requests.post(f"{BACKEND_URL}/api/route", json=route_payload, timeout=10)
                route_data = route_res.json()
                route_segments_map.append(route_data)

                if "distance_km" in route_data:
                    total_distance_osrm += route_data.get("distance_km", 0)
                    total_duration += route_data.get("duration_seconds", 0)
            except Exception:
                route_segments_map.append({"route": [all_points[i], all_points[i+1]]})

        colors = ["blue", "green", "purple", "orange", "darkred"]
        for idx, segment in enumerate(route_segments_map):
            if "route" in segment and segment["route"]:
                color = colors[idx % len(colors)]
                folium.PolyLine(segment["route"], color=color, weight=3, opacity=0.8).add_to(m)

        for i, item in enumerate(items_map):
            folium.Marker([item['lat'], item['lon']], popup=f"<b>{item['start_time']}-{item['end_time']}</b><br>{item['name']}<br>{item['place_name']}", icon=folium.Icon(color="blue", icon=str(i+1), prefix='fa')).add_to(m)
        
    st_folium(m, width=None, height=450, returned_objects=[])

except Exception as e:
    st.error(f"Chưa tải được bản đồ: {e}")

st.markdown("---")

# --- PHẦN 4: Kết quả lịch trình (Text Summary) ---
st.subheader("📝 Kết quả lịch trình của bạn")
try:
    # Gọi lại API hoặc dùng biến đã có (nếu cấu trúc phức tạp hơn)
    # Tạm thời gọi lại để đảm bảo tính độc lập của module
    res_iti_summary = requests.get(f"{BACKEND_URL}/api/itinerary")
    items_summary = res_iti_summary.json().get("itinerary", [])
    
    if items_summary:
        # Tính toán lại tổng quãng đường cho phần text (hoặc lấy từ session_state nếu có)
        # (Để đơn giản, code này chỉ hiển thị danh sách)
        
        st.markdown(f"**📊 Tổng quãng đường OSRM:** {total_distance_osrm:.2f} km | **Thời gian:** {int(total_duration/60)} phút")
        
        for i, item in enumerate(items_summary):
            # Lấy thông tin quãng đường từ bản đồ (nếu có)
            if i < len(route_segments_map):
                segment_data = route_segments_map[i]
                segment_dist = segment_data.get("distance_km", "?")
                segment_time = int(segment_data.get("duration_seconds", 0) / 60)
            else:
                segment_dist = "?"
                segment_time = "?"

            st.markdown(f"**{i+1}. [{item['start_time']}-{item['end_time']}]** {item['name']}\n"
                        f"- 📍 {item['place_name']}\n"
                        f"- 🚗 Tuyến đường: {segment_dist} km | ⏱️ {segment_time} phút (OSRM)")
    else:
        st.info("Chưa có lịch trình. Thêm địa điểm vào lịch để vẽ tuyến.")
except Exception as e:
    st.error(f"Lỗi tải tóm tắt lịch trình: {e}")

st.markdown("---")

# --- PHẦN 5: CHATBOT (Dưới dạng expander) ---
with st.expander("🤖 Chat với AI (Click để mở)"):
    # Lưu lịch sử chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Hiển thị lịch sử
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Ô nhập liệu
    if prompt := st.chat_input("Hỏi gì đi (vd: Tìm quán cafe):"):
        # Hiện câu hỏi user
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Gọi hàm xử lý Chatbot
        try:
            from chatbot.bot_engine import chat_with_ollama
            with st.spinner("Bot đang suy nghĩ..."):
                ai_reply = chat_with_ollama(prompt)
        except ImportError as ie:
            ai_reply = f"❌ Lỗi import: {str(ie)[:100]}\n\nKiểm tra:\n- File `chatbot/bot_engine.py` có tồn tại?\n- Chạy: `pip install ollama requests`"
        except ModuleNotFoundError as me:
            ai_reply = f"❌ Module không tìm thấy: {str(me)[:100]}"
        except Exception as e:
            error_msg = str(e)
            if "Connection" in error_msg or "connect" in error_msg.lower():
                ai_reply = f"❌ Lỗi kết nối Ollama:\n\n{error_msg[:200]}\n\nHướng dẫn:\n1. Mở Ollama (ứng dụng desktop)\n2. Chạy: `ollama run llama3`\n3. Thử chat lại"
            else:
                ai_reply = f"❌ Lỗi: {error_msg[:150]}"

        # Hiện câu trả lời AI
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        with st.chat_message("assistant"):
            st.write(ai_reply)