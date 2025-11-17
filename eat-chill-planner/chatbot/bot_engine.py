# File: chatbot/bot_engine.py
import json
import requests
from chatbot.prompts import SYSTEM_PROMPT

BACKEND_URL = "http://127.0.0.1:8000/api/search"

def chat_with_ollama(user_message):
    """Chat with Ollama and execute backend logic based on intent."""
    try:
        # Check if Ollama is available
        import ollama
    except ImportError:
        # Fallback: Ollama not installed — perform a simple keyword-based search via backend
        low = user_message.lower()
        # Simple intent detection fallback
        if any(w in low for w in ["chào", "xin chào", "hi", "hello"]):
            return "Chào bạn! Mình là trợ lý Eat & Chill. Bạn cần tìm quán ăn hay chỗ chơi?"

        # Build a heuristic search payload
        keyword = ""
        filters = {}
        category = "Ăn uống" if any(w in low for w in ["ăn", "quán", "nhà hàng", "cafe"]) else ""

        if "hàn" in low or "korean" in low:
            # Match documents with attributes.cuisine == "Hàn Quốc"
            filters["cuisine"] = "Hàn Quốc"
        if "phở" in low:
            keyword = "phở"
        if "lẩu" in low:
            keyword = "lẩu"

        payload = {
            "lat": 10.762622,
            "lon": 106.660172,
            "keyword": keyword,
            "category": category,
            "filters": filters
        }
        try:
            api_res = requests.post(BACKEND_URL, json=payload, timeout=5)
            if api_res.status_code == 200:
                places = api_res.json().get("places", [])
                if not places:
                    return "Mình tìm rồi nhưng không thấy địa điểm phù hợp."
                reply = f"Mình tìm thấy {len(places)} địa điểm:\n"
                for p in places[:3]:
                    reply += f"- {p['name']} ({p.get('distance',0)}km) - ⭐{p.get('rating','N/A')}\n"
                return reply
            else:
                return f"Lỗi kết nối backend (status {api_res.status_code})."
        except Exception:
            return "Lỗi: Không thể kết nối backend để tìm quán (fallback)."
    
    try:
        # 1. Call Ollama to extract intent and entities
        # Use llama3.2:1b if llama3 is not available
        response = ollama.chat(model='llama3.2:1b', messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_message},
        ])
        ai_content = response['message']['content']
        
        # Clean up JSON string (sometimes Ollama adds extra text or markdown)
        json_str = ai_content.strip()
        # Remove markdown code blocks
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        # Remove ### (heading markers)
        json_str = json_str.replace("### ", "").strip()
        # Try to find and extract JSON object from the response
        if "{" in json_str and "}" in json_str:
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            json_str = json_str[start:end]
        
        print(f"DEBUG: Parsed JSON string: {json_str[:100]}")
        data = json.loads(json_str)
        intent = data.get("intent", "").lower()
        entities = data.get("entities", {})
        
        # For cases where intent contains multiple values (greeting|search_place), prioritize search
        if "|" in intent:
            intents = intent.split("|")
            # Prefer search over greeting if both are present
            if any(w in intents for w in ["search_place", "tim", "find", "search"]):
                intent = "search_place"
            else:
                intent = intents[0]

        # 2. Handle different intents (match common variations)
        if any(w in intent for w in ["greeting", "chao", "hello", "hi"]):
            return "Chào bạn! Mình là trợ lý Eat & Chill. Bạn cần tìm quán ăn hay chỗ chơi?"

        elif any(w in intent for w in ["search", "search_place", "tim", "find"]):
            # Call backend API with keyword/category
            keyword = entities.get("keyword", "")
            category = entities.get("category", "")
            
            # User coordinates (mock location - ideally pass from frontend)
            payload = {
                "lat": 10.762622, 
                "lon": 106.660172, 
                "keyword": "",  # Don't use keyword search (text index not working properly)
                "category": category or "Ăn uống",  # Default to food category
                "filters": {}
            }
            
            try:
                api_res = requests.post(BACKEND_URL, json=payload, timeout=5)
                if api_res.status_code == 200:
                    places = api_res.json().get("places", [])
                    if not places:
                        return "Mình tìm rồi nhưng không thấy quán nào phù hợp."
                    
                    # Build response with top 3 places
                    reply = f"Mình tìm thấy {len(places)} địa điểm cho bạn:\n"
                    for p in places[:3]:
                        distance = p.get('distance', 0)
                        rating = p.get('rating', 'N/A')
                        reply += f"- {p['name']} ({distance}km) - ⭐{rating}\n"
                        reply += f"  Địa chỉ: {p.get('address', 'N/A')}\n"
                    return reply
                else:
                    return f"Lỗi kết nối backend (status {api_res.status_code})."
            except requests.exceptions.Timeout:
                return "Lỗi: Backend không phản hồi. Vui lòng kiểm tra server."
            except requests.exceptions.ConnectionError:
                return "Lỗi: Không thể kết nối đến backend. Kiểm tra xem http://127.0.0.1:8000 có chạy không?"
            except Exception as e:
                return f"Lỗi gọi API: {e}"

        elif any(w in intent for w in ["add", "itinerary", "lich", "schedule"]):
            return "Tính năng thêm vào lịch qua chat đang phát triển. Bạn dùng nút trên web nhé!"

        else:
            return "Xin lỗi, mình chưa hiểu ý bạn. Bạn thử hỏi 'Tìm quán lẩu' xem sao?"

    except json.JSONDecodeError as jde:
        # If JSON parsing fails, use fallback keyword-based logic
        print(f"DEBUG: JSON decode error: {jde}, trying fallback...")
        low = user_message.lower()
        
        # Check for greeting
        if any(w in low for w in ["chào", "hello", "hi", "xin chào"]):
            return "Chào bạn! Mình là trợ lý Eat & Chill. Bạn cần tìm quán ăn hay chỗ chơi?"
        
        # Check for search intent (more specific keywords)
        is_search = any(w in low for w in ["tìm", "find", "search", "quán", "nhà hàng", "cafe", "phở", "lẩu", "hàn", "việt"])
        
        # Default to food category search
        payload = {
            "lat": 10.762622,
            "lon": 106.660172,
            "keyword": "",
            "category": "Ăn uống" if is_search else "",
            "filters": {}
        }
        try:
            api_res = requests.post(BACKEND_URL, json=payload, timeout=5)
            if api_res.status_code == 200:
                places = api_res.json().get("places", [])
                if not places:
                    return "Mình tìm rồi nhưng không thấy quán nào phù hợp."
                reply = f"Mình tìm thấy {len(places)} địa điểm:\n"
                for p in places[:3]:
                    reply += f"- {p['name']} ({p.get('distance',0)}km) - ⭐{p.get('rating','N/A')}\n"
                    reply += f"  Địa chỉ: {p.get('address', 'N/A')}\n"
                return reply
            else:
                return f"Lỗi backend (status {api_res.status_code})."
        except Exception as e:
            return f"Lỗi kết nối backend: {e}"
    
    except KeyError as e:
        return f"Lỗi: Thiếu field {e} trong response từ Ollama."
    except Exception as e:
        print(f"Lỗi Bot: {e}")
        return f"Bot đang bị lỗi: {str(e)[:100]}"