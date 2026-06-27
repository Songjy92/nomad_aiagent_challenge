import streamlit as st
from agents import function_tool, AgentHooks, Agent, Tool, RunContextWrapper
from models import UserAccountContext
import random
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

# =============================================================================
# RESTAURANT MOCK DATABASE & STORES
# =============================================================================

MENU_DATABASE = {
    "beef": {
        "등심": {
            "price": 32000,
            "description": "부드럽고 고소한 소고기 등심 (200g).",
            "ingredients": ["소고기(등심)"],
            "allergens": []
        },
        "안심": {
            "price": 32000,
            "description": "가장 부드러운 소고기 안심 (200g).",
            "ingredients": ["소고기(안심)"],
            "allergens": []
        },
        "채끝등심": {
            "price": 32000,
            "description": "부드러운 소고기 채끝등심 (200g).",
            "ingredients": ["소고기(채끝등심)"],
            "allergens": []
        }
    },
    "pork": {
        "삼겹살": {
            "price": 15000,
            "description": "국민 고기 삼겹살 (200g).",
            "ingredients": ["돼지고기(삼겹살)"],
            "allergens": []
        },
        "오겹살": {
            "price": 15000,
            "description": "쫄깃한 껍질이 매력적인 오겹살 (200g).",
            "ingredients": ["돼지고기(오겹살)"],
            "allergens": []
        },
        "목살": {
            "price": 15000,
            "description": "담백하고 쫄깃한 돼지 목살 (200g).",
            "ingredients": ["돼지고기(목살)"],
            "allergens": []
        },
        "갈매기살": {
            "price": 16000,
            "description": "육즙이 풍부하고 부드러운 갈매기살 (200g).",
            "ingredients": ["돼지고기(갈매기살)"],
            "allergens": []
        }
    },
    "sides": {
        "냉면": {
            "price": 7000,
            "description": "시원한 물냉면 또는 매콤한 비빔냉면.",
            "ingredients": ["냉면사리", "냉면육수", "삶은계란", "오이", "절임무"],
            "allergens": ["밀", "계란"]
        },
        "김치찌개": {
            "price": 8000,
            "description": "칼칼하고 얼큰한 돼지고기 김치찌개 (공기밥 포함).",
            "ingredients": ["김치", "돼지고기", "두부", "대파"],
            "allergens": ["대두"]
        },
        "된장찌개": {
            "price": 8000,
            "description": "구수한 차돌 된장찌개 (공기밥 포함).",
            "ingredients": ["된장", "차돌박이", "두부", "애호박", "양파", "대파", "청양고추"],
            "allergens": ["대두"]
        }
    },
    "drinks": {
        "소주": {
            "price": 5000,
            "description": "국민 술 소주.",
            "ingredients": ["주정", "물"],
            "allergens": []
        },
        "맥주": {
            "price": 5000,
            "description": "시원한 병맥주.",
            "ingredients": ["맥아", "홉", "물"],
            "allergens": ["밀"]
        },
        "음료수": {
            "price": 2000,
            "description": "콜라, 사이다, 환타 등.",
            "ingredients": ["탄산수", "설탕"],
            "allergens": []
        }
    }
}

ORDERS_STORE = {}
RESERVATIONS_STORE = {}
COMPLAINTS_STORE = {}

# =============================================================================
# MENU AGENT TOOLS
# =============================================================================

@function_tool
def list_menu(context: UserAccountContext, category: str = "all") -> str:
    """
    List restaurant menu items, optionally filtered by category.

    Args:
        category: Menu category ('all', 'beef', 'pork', 'sides', 'drinks')
    """
    cat = category.lower()
    if cat != "all" and cat not in MENU_DATABASE:
        valid_cats = ", ".join(["all"] + list(MENU_DATABASE.keys()))
        return f"❌ Invalid category '{category}'. Valid categories are: {valid_cats}."

    result = "🍽️ **Restaurant Menu** 🍽️\n\n"
    categories_to_show = MENU_DATABASE.keys() if cat == "all" else [cat]

    for c in categories_to_show:
        result += f"### 📌 {c.capitalize()}\n"
        for name, details in MENU_DATABASE[c].items():
            result += f"- **{name}** (${details['price']}): {details['description']}\n"
        result += "\n"

    return result.strip()


@function_tool
def get_menu_item_details(context: UserAccountContext, item_name: str) -> str:
    """
    Get detailed information about a specific menu item, including ingredients and allergens.

    Args:
        item_name: The exact name of the menu item
    """
    item_lower = item_name.strip().lower()
    for cat, items in MENU_DATABASE.items():
        for name, details in items.items():
            if name.lower() == item_lower:
                allergens_str = ", ".join(details["allergens"]) if details["allergens"] else "None"
                ingredients_str = ", ".join(details["ingredients"])
                return f"""
📖 **Menu Item Details: {name}**
💵 **Price:** {details['price']}원
📝 **Description:** {details['description']}
🥕 **Ingredients:** {ingredients_str}
⚠️ **Allergens:** {allergens_str}
                """.strip()
    
    return f"❌ Menu item '{item_name}' was not found. Please check spelling or list the menu to see options."


# =============================================================================
# ORDER AGENT TOOLS
# =============================================================================

class OrderItem(BaseModel):
    name: str = Field(description="Name of the menu item (e.g., 삼겹살, 목살, 소주)")
    quantity: int = Field(description="Quantity of the item (must be 1 or more)")

@function_tool
def place_order(context: UserAccountContext, items: list[OrderItem]) -> str:
    """
    Place a new food and drink order for the customer.

    Args:
        items: List of items to order with their quantities
    """
    if not items:
        return "❌ Order items cannot be empty."

    found_items = []
    missing_items = []
    total_price = 0.0

    for item in items:
        o_item = item.name.strip()
        o_qty = item.quantity
        if o_qty <= 0:
            continue
        o_item_lower = o_item.lower()
        matched = False
        for cat, items_dict in MENU_DATABASE.items():
            for name, details in items_dict.items():
                if name.lower() == o_item_lower:
                    found_items.append({"name": name, "quantity": o_qty})
                    total_price += details["price"] * o_qty
                    matched = True
                    break
            if matched:
                break
        if not matched:
            missing_items.append(o_item)

    if missing_items:
        return f"❌ Could not place order. The following items do not exist on the menu: {', '.join(missing_items)}."

    if not found_items:
        return "❌ Order items cannot be empty."

    order_id = f"ORD-{random.randint(10000, 99999)}"
    order_data = {
        "customer_id": context.customer_id,
        "customer_name": context.name,
        "items": found_items,
        "total_price": round(total_price, 2),
        "status": "cooking",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Store order
    ORDERS_STORE[order_id] = order_data

    prep_time = 15 if context.tier != "basic" else 25 # Premium perk: priority queue

    items_display_str = ", ".join([f"{item['name']} x{item['quantity']}" for item in found_items])

    return f"""
✅ **Order Placed Successfully!**
🆔 **Order ID:** {order_id}
👤 **Customer:** {context.name} (Tier: {context.tier})
📋 **Items:** {items_display_str}
💰 **Total Amount:** {order_data['total_price']}원
⏱️ **Estimated Prep Time:** {prep_time} minutes
🧑‍🍳 **Status:** Cook is preparing your meal
    """.strip()


@function_tool
def get_order_status(context: UserAccountContext, order_id: str) -> str:
    """
    Look up the status and details of an existing order.

    Args:
        order_id: The unique Order ID (e.g., ORD-12345)
    """
    o_id = order_id.strip().upper()
    if o_id not in ORDERS_STORE:
        return f"❌ Order ID '{order_id}' not found. Please double check the ID."

    order = ORDERS_STORE[o_id]
    
    items_display_str = ", ".join([f"{item['name']} x{item['quantity']}" for item in order['items']])

    return f"""
📦 **Order Status for {o_id}**
👤 **Customer Name:** {order['customer_name']}
📋 **Ordered Items:** {items_display_str}
💰 **Total Paid:** {order['total_price']}원
📅 **Placed At:** {order['created_at']}
🏷️ **Current Status:** {order['status'].capitalize()}
    """.strip()


@function_tool
def add_to_order(context: UserAccountContext, order_id: str, items: list[OrderItem]) -> str:
    """
    Add new food or drink items to an existing order.

    Args:
        order_id: The unique Order ID (e.g., ORD-12345)
        items: List of additional items to order with their quantities
    """
    o_id = order_id.strip().upper()
    if o_id not in ORDERS_STORE:
        return f"❌ Order ID '{order_id}' not found. Please double check the ID."

    order = ORDERS_STORE[o_id]
    if order["status"] == "cancelled":
        return f"❌ Cannot add items. Order '{o_id}' has already been cancelled."
        
    if order["status"] in ("served", "delivered"):
        return f"❌ Cannot add items. Order '{o_id}' has already been served."

    if not items:
        return "❌ Order items cannot be empty."

    validated_items = []
    missing_items = []
    
    for item in items:
        o_item = item.name.strip()
        o_qty = item.quantity
        if o_qty <= 0:
            continue
        o_item_lower = o_item.lower()
        matched = False
        for cat, items_dict in MENU_DATABASE.items():
            for name, details in items_dict.items():
                if name.lower() == o_item_lower:
                    validated_items.append({"name": name, "quantity": o_qty, "price": details["price"]})
                    matched = True
                    break
            if matched:
                break
        if not matched:
            missing_items.append(o_item)
            
    if missing_items:
        return f"❌ Could not add items. The following items do not exist on the menu: {', '.join(missing_items)}."
        
    if not validated_items:
        return "❌ No valid items were provided to add."

    # Update the order
    for val_item in validated_items:
        name = val_item["name"]
        o_qty = val_item["quantity"]
        price = val_item["price"]
        
        found_existing = False
        for existing_item in order["items"]:
            if existing_item["name"] == name:
                existing_item["quantity"] += o_qty
                found_existing = True
                break
        if not found_existing:
            order["items"].append({"name": name, "quantity": o_qty})
            
        order["total_price"] += price * o_qty
        
    order["total_price"] = round(order["total_price"], 2)

    added_items_str = ", ".join([f"{item['name']} x{item['quantity']}" for item in validated_items])
    all_items_str = ", ".join([f"{item['name']} x{item['quantity']}" for item in order['items']])
    
    return f"""
✅ **Items Added to Order Successfully!**
🆔 **Order ID:** {o_id}
➕ **Added Items:** {added_items_str}
📋 **Updated Total Items:** {all_items_str}
💰 **New Total Amount:** {order['total_price']}원
    """.strip()


@function_tool
def cancel_order(context: UserAccountContext, order_id: str) -> str:
    """
    Cancel a cooking or pending order.

    Args:
        order_id: The unique Order ID (e.g., ORD-12345)
    """
    o_id = order_id.strip().upper()
    if o_id not in ORDERS_STORE:
        return f"❌ Order ID '{order_id}' not found."

    order = ORDERS_STORE[o_id]
    if order["status"] == "cancelled":
        return f"⚠️ Order '{o_id}' is already cancelled."
        
    if order["status"] == "served" or order["status"] == "delivered":
        return f"❌ Cannot cancel order '{o_id}'. It has already been served."

    # Update status to cancelled
    order["status"] = "cancelled"
    return f"🗑️ **Order '{o_id}' has been successfully cancelled.** Refund will be processed back to your payment method."


# =============================================================================
# RESERVATION AGENT TOOLS
# =============================================================================

@function_tool
def get_today_date(context: UserAccountContext) -> str:
    """
    Get today's date and current time to help calculate relative dates
    such as 'tomorrow', 'next week', 'this weekend', etc.
    Always call this tool first when the user mentions a relative date.
    """
    now = datetime.now()
    weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    tomorrow = now + timedelta(days=1)
    day_after_tomorrow = now + timedelta(days=2)
    next_saturday = now + timedelta(days=(5 - now.weekday()) % 7 or 7)
    next_sunday = now + timedelta(days=(6 - now.weekday()) % 7 or 7)
    return f"""
📅 **현재 날짜/시간 정보**
- 오늘 (Today): {now.strftime("%Y-%m-%d")} ({weekday_names[now.weekday()]})
- 내일 (Tomorrow): {tomorrow.strftime("%Y-%m-%d")} ({weekday_names[tomorrow.weekday()]})
- 모레 (Day after tomorrow): {day_after_tomorrow.strftime("%Y-%m-%d")} ({weekday_names[day_after_tomorrow.weekday()]})
- 이번 주 토요일 (This Saturday): {next_saturday.strftime("%Y-%m-%d")}
- 이번 주 일요일 (This Sunday): {next_sunday.strftime("%Y-%m-%d")}
- 현재 시각 (Current time): {now.strftime("%H:%M")}

Use these dates when converting relative expressions (e.g., '내일', 'tomorrow', '다음 주말') into exact YYYY-MM-DD format for reservations.
    """.strip()


@function_tool
def make_reservation(context: UserAccountContext, date: str, time: str, guests: int) -> str:
    """
    Book a table at the restaurant.

    Args:
        date: Date in YYYY-MM-DD format (e.g., "2026-07-01")
        time: Time in HH:MM format (e.g., "19:30")
        guests: Number of people (guests) in the reservation
    """
    if guests <= 0:
        return "❌ Number of guests must be at least 1."

    # Parse date to ensure format is valid
    try:
        parsed_date = datetime.strptime(date.strip(), "%Y-%m-%d")
        if parsed_date.date() < datetime.now().date():
            return "❌ Cannot book a reservation in the past."
    except ValueError:
        return "❌ Invalid date format. Please use YYYY-MM-DD."

    res_id = f"RES-{random.randint(10000, 99999)}"
    res_data = {
        "customer_id": context.customer_id,
        "customer_name": context.name,
        "date": date.strip(),
        "time": time.strip(),
        "guests": guests,
        "status": "confirmed",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    RESERVATIONS_STORE[res_id] = res_data
    
    table_type = "Window VIP Table" if context.tier != "basic" else "Standard Table"

    return f"""
📅 **Reservation Confirmed!**
🆔 **Reservation ID:** {res_id}
👤 **Name:** {context.name} (Tier: {context.tier})
📆 **Date:** {date}
⏰ **Time:** {time}
👥 **Guests:** {guests} people
🪑 **Assigned Seat:** {table_type}
    """.strip()


@function_tool
def get_reservation_details(context: UserAccountContext, reservation_id: str) -> str:
    """
    Retrieve information about an existing table reservation.

    Args:
        reservation_id: The unique Reservation ID (e.g., RES-12345)
    """
    r_id = reservation_id.strip().upper()
    if r_id not in RESERVATIONS_STORE:
        return f"❌ Reservation ID '{reservation_id}' not found."

    res = RESERVATIONS_STORE[r_id]
    return f"""
🔍 **Reservation Info: {r_id}**
👤 **Customer Name:** {res['customer_name']}
📆 **Date:** {res['date']}
⏰ **Time:** {res['time']}
👥 **Guests:** {res['guests']} people
🏷️ **Status:** {res['status'].capitalize()}
    """.strip()


@function_tool
def cancel_reservation(context: UserAccountContext, reservation_id: str) -> str:
    """
    Cancel a table reservation.

    Args:
        reservation_id: The unique Reservation ID (e.g., RES-12345)
    """
    r_id = reservation_id.strip().upper()
    if r_id not in RESERVATIONS_STORE:
        return f"❌ Reservation ID '{reservation_id}' not found."

    res = RESERVATIONS_STORE[r_id]
    if res["status"] == "cancelled":
        return f"⚠️ Reservation '{r_id}' is already cancelled."

    res["status"] = "cancelled"
    return f"🗑️ **Reservation '{r_id}' has been successfully cancelled.** We hope to host you another time."

@function_tool
def change_reservation(context: UserAccountContext, reservation_id: str, new_date: str, new_time: str, new_guests: int) -> str:
    """
    Change the date and/or time of an existing table reservation.

    Args:
        reservation_id: The unique Reservation ID (e.g., RES-12345)
        new_date: The new date for the reservation (e.g., "2025-01-01")
        new_time: The new time for the reservation (e.g., "19:00")
        new_guests: The new number of guests (e.g., 2)
    """
    r_id = reservation_id.strip().upper()
    if r_id not in RESERVATIONS_STORE:
        return f"❌ Reservation ID '{reservation_id}' not found."

    res = RESERVATIONS_STORE[r_id]
    if res["status"] == "cancelled":
        return f"⚠️ Reservation '{r_id}' is already cancelled."
    res["date"] = new_date
    res["time"] = new_time
    res["guests"] = new_guests
    return f"📅 **Reservation '{r_id}' has been successfully updated.** New date: {new_date}, New time: {new_time}, New guests: {new_guests}"

# =============================================================================
# COMPLAINTS AGENT TOOLS
# =============================================================================

@function_tool
def register_complaint(context: UserAccountContext, issue_description: str, department: str = "general") -> str:
    """
    Register a customer complaint or feedback regarding their restaurant experience.

    Args:
        issue_description: Description of the customer complaint (e.g., cold food, slow service)
        department: Department target ('food', 'service', 'hygiene', 'general')
    """
    if not issue_description.strip():
        return "❌ Complaint description cannot be empty."

    comp_id = f"CMP-{random.randint(10000, 99999)}"
    comp_data = {
        "customer_id": context.customer_id,
        "customer_name": context.name,
        "description": issue_description.strip(),
        "department": department.lower(),
        "status": "investigating",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    COMPLAINTS_STORE[comp_id] = comp_data

    # Premium customers get instant escalation or discount voucher
    resolution = ""
    if context.tier != "basic":
        resolution = "Priority: High. A Manager has been notified, and we've applied a complimentary $15 credit to your account as an apology."
    else:
        resolution = "Priority: Standard. Our customer service team will review this within 24 hours."

    return f"""
⚠️ **Complaint Registered**
🆔 **Complaint ID:** {comp_id}
👤 **Customer:** {context.name}
🏢 **Department:** {department.capitalize()}
📝 **Details:** {issue_description}
⚡ **Resolution Path:** {resolution}
    """.strip()


@function_tool
def get_complaint_status(context: UserAccountContext, complaint_id: str) -> str:
    """
    Check the status and resolution path of a registered complaint.

    Args:
        complaint_id: The unique Complaint ID (e.g., CMP-12345)
    """
    c_id = complaint_id.strip().upper()
    if c_id not in COMPLAINTS_STORE:
        return f"❌ Complaint ID '{complaint_id}' not found."

    comp = COMPLAINTS_STORE[c_id]
    return f"""
🔍 **Complaint Investigation: {c_id}**
👤 **Customer Name:** {comp['customer_name']}
🏢 **Department:** {comp['department'].capitalize()}
📝 **Details:** {comp['description']}
🏷️ **Status:** {comp['status'].capitalize()}
📅 **Submitted At:** {comp['created_at']}
    """.strip()


# =============================================================================
# HOOKS & UTILITIES
# =============================================================================

class AgentToolUsageLoggingHooks(AgentHooks):

    async def on_tool_start(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        tool: Tool,
    ):
        with st.sidebar:
            st.write(f"🔧 **{agent.name}** starting tool: `{tool.name}`")

    async def on_tool_end(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        tool: Tool,
        result: str,
    ):
        with st.sidebar:
            st.write(f"🔧 **{agent.name}** used tool: `{tool.name}`")
            st.code(result)

    async def on_handoff(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        source: Agent[UserAccountContext],
    ):
        with st.sidebar:
            st.write(f"🔄 Handoff: **{source.name}** → **{agent.name}**")

    async def on_start(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
    ):
        with st.sidebar:
            st.write(f"🚀 **{agent.name}** activated")

    async def on_end(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        output,
    ):
        with st.sidebar:
            st.write(f"🏁 **{agent.name}** completed")