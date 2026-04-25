import asyncio
import copy
import json
import os
import random

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8565554508:AAFqFViAgcFqPrj59IOwQUXahHG4AyAu8YA"
if not TOKEN:
    raise ValueError("BOT_TOKEN не знайдено")

SAVE_FILE = "players.json"
UPDATE_FILE = "latest_update.json"

GROUP_ID = int(os.getenv("GROUP_ID", "-5292706881"))
ADMINS = [
    int(x.strip())
    for x in os.getenv("ADMINS", "6449855887").split(",")
    if x.strip()
]

START_IMAGE = "images/last_hero.jpg.png"

players = {}

RARITY_EMOJI = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟠"
}

RARITY_NAME = {
    "common": "звичайний",
    "uncommon": "незвичайний",
    "rare": "рідкісний",
    "epic": "епічний",
    "legendary": "легендарний"
}

ITEMS = {
    "Зілля лікування": {
        "type": "consumable",
        "rarity": "common",
        "price": 15,
        "heal": 40
    },

    "Іржавий кинджал": {
        "type": "weapon",
        "rarity": "common",
        "price": 20,
        "damage": 3
    },
    "Кістяний меч": {
        "type": "weapon",
        "rarity": "uncommon",
        "price": 35,
        "damage": 5
    },
    "Мисливський спис": {
        "type": "weapon",
        "rarity": "rare",
        "price": 50,
        "damage": 7
    },
    "Залізний меч": {
        "type": "weapon",
        "rarity": "rare",
        "price": 70,
        "damage": 9
    },

    "Шкіряний шматок": {
        "type": "armor",
        "rarity": "common",
        "price": 10,
        "defense": 1
    },
    "Старий щит": {
        "type": "armor",
        "rarity": "common",
        "price": 25,
        "defense": 2
    },
    "Шкура вовка": {
        "type": "armor",
        "rarity": "uncommon",
        "price": 18,
        "defense": 2
    },
    "Шкіряна броня": {
        "type": "armor",
        "rarity": "rare",
        "price": 45,
        "defense": 4
    },
    "Залізний щит": {
        "type": "armor",
        "rarity": "rare",
        "price": 60,
        "defense": 5
    },

    "Ікло вовка": {
        "type": "material",
        "rarity": "common",
        "price": 8
    },
    "М'ясо вовка": {
        "type": "material",
        "rarity": "common",
        "price": 6
    },
    "Кіготь хижака": {
        "type": "material",
        "rarity": "uncommon",
        "price": 14
    },
    "Темний уламок": {
        "type": "material",
        "rarity": "rare",
        "price": 18
    },
    "Пустельний зуб": {
        "type": "material",
        "rarity": "uncommon",
        "price": 16
    },
    "Пісочна шкура": {
        "type": "material",
        "rarity": "rare",
        "price": 20
    }
}

LOCATIONS = {
    "forest": {
        "name": "🌲 Ліс",
        "level_range": "1-5",
        "enemies": [
            {
                "name": "Гоблін",
                "hp": 30,
                "damage": (5, 10),
                "image": "images/goblin.jpg.png",
                "drops": ["Іржавий кинджал", "Шкіряний шматок", "Зілля лікування"]
            },
            {
                "name": "Скелет",
                "hp": 40,
                "damage": (6, 12),
                "image": "images/skeleton.jpg.png",
                "drops": ["Кістяний меч", "Старий щит", "Зілля лікування"]
            },
            {
                "name": "Вовк",
                "hp": 35,
                "damage": (7, 11),
                "image": "images/wolf.jpg.png",
                "drops": ["Ікло вовка", "Шкура вовка", "М'ясо вовка"]
            },
            {
                "name": "Лісовий хижак",
                "hp": 45,
                "damage": (8, 13),
                "image": "images/wolf.jpg.png",
                "drops": ["Кіготь хижака", "Шкура вовка", "Зілля лікування"]
            }
        ]
    },
    "desert": {
        "name": "🏜️ Пустеля",
        "level_range": "4-10",
        "enemies": [
            {
                "name": "Пустельний розбійник",
                "hp": 55,
                "damage": (9, 14),
                "image": "images/goblin.jpg.png",
                "drops": ["Мисливський спис", "Пустельний зуб", "Зілля лікування"]
            },
            {
                "name": "Піщаний скелет",
                "hp": 60,
                "damage": (10, 15),
                "image": "images/skeleton.jpg.png",
                "drops": ["Залізний меч", "Залізний щит", "Темний уламок"]
            },
            {
                "name": "Пустельний вовк",
                "hp": 58,
                "damage": (9, 16),
                "image": "images/wolf.jpg.png",
                "drops": ["Пісочна шкура", "Пустельний зуб", "М'ясо вовка"]
            }
        ]
    }
}


def make_item(name):
    base = ITEMS.get(name)

    if not base:
        base = {
            "type": "material",
            "rarity": "common",
            "price": 5
        }

    item = {
        "name": name,
        "type": base.get("type", "material"),
        "rarity": base.get("rarity", "common"),
        "level": 0
    }

    if "damage" in base:
        item["damage"] = base["damage"]

    if "defense" in base:
        item["defense"] = base["defense"]

    if "heal" in base:
        item["heal"] = base["heal"]

    item["price"] = base.get("price", 5)

    return item


def item_display(item):
    rarity = item.get("rarity", "common")
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    name = item.get("name", "Невідомий предмет")
    level = item.get("level", 0)

    upgrade = f" +{level}" if level > 0 else ""
    return f"{emoji} {name}{upgrade}"


def item_stat_text(item):
    item_type = item.get("type")

    if item_type == "weapon":
        return f"+{get_item_damage(item)} урону"

    if item_type == "armor":
        return f"+{get_item_defense(item)} захисту"

    if item_type == "consumable":
        return f"+{item.get('heal', 0)} HP"

    return "матеріал"


def item_sell_price(item):
    base = item.get("price", 5)
    level = item.get("level", 0)
    return max(1, (base + level * 10) // 2)


def upgrade_cost(item):
    return 20 + item.get("level", 0) * 25


def get_item_damage(item):
    return item.get("damage", 0) + item.get("level", 0) * 2


def get_item_defense(item):
    return item.get("defense", 0) + item.get("level", 0)


def default_player():
    return {
        "hp": 100,
        "max_hp": 100,
        "xp": 0,
        "level": 1,
        "gold": 0,
        "enemy": None,
        "inventory": [],
        "current_location": "forest",
        "equipment": {
            "weapon": None,
            "armor": None
        }
    }


def normalize_player(player):
    defaults = default_player()

    for key, value in defaults.items():
        if key not in player:
            if isinstance(value, dict):
                player[key] = copy.deepcopy(value)
            elif isinstance(value, list):
                player[key] = []
            else:
                player[key] = value

    if not isinstance(player.get("equipment"), dict):
        player["equipment"] = {"weapon": None, "armor": None}

    if "weapon" not in player["equipment"]:
        player["equipment"]["weapon"] = None

    if "armor" not in player["equipment"]:
        player["equipment"]["armor"] = None

    if player.get("current_location") not in LOCATIONS:
        player["current_location"] = "forest"

    old_inventory = player.get("inventory", [])
    new_inventory = []

    for item in old_inventory:
        if isinstance(item, str):
            new_inventory.append(make_item(item))
        elif isinstance(item, dict):
            name = item.get("name")
            if name:
                fixed = make_item(name)
                fixed.update(item)
                new_inventory.append(fixed)

    player["inventory"] = new_inventory

    for slot in ["weapon", "armor"]:
        equipped = player["equipment"].get(slot)

        if isinstance(equipped, str):
            player["equipment"][slot] = make_item(equipped)

        elif isinstance(equipped, dict):
            name = equipped.get("name")
            if name:
                fixed = make_item(name)
                fixed.update(equipped)
                player["equipment"][slot] = fixed
            else:
                player["equipment"][slot] = None

        else:
            player["equipment"][slot] = None

    player["inventory"] = remove_equipped_duplicates(player)

    return player


def remove_equipped_duplicates(player):
    weapon = player["equipment"].get("weapon")
    armor = player["equipment"].get("armor")
    cleaned = []

    weapon_removed = False
    armor_removed = False

    for item in player["inventory"]:
        if weapon and item.get("name") == weapon.get("name") and item.get("type") == "weapon" and not weapon_removed:
            weapon_removed = True
            continue

        if armor and item.get("name") == armor.get("name") and item.get("type") == "armor" and not armor_removed:
            armor_removed = True
            continue

        cleaned.append(item)

    return cleaned


def save_players():
    with open(SAVE_FILE, "w", encoding="utf-8") as file:
        json.dump(players, file, ensure_ascii=False, indent=2)


def load_players():
    global players

    if not os.path.exists(SAVE_FILE):
        players = {}
        return

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            players = json.load(file)
    except Exception:
        players = {}

    for user_id in list(players.keys()):
        players[user_id] = normalize_player(players[user_id])

    save_players()


def save_latest_update(text):
    with open(UPDATE_FILE, "w", encoding="utf-8") as file:
        json.dump({"text": text}, file, ensure_ascii=False, indent=2)


def load_latest_update():
    if not os.path.exists(UPDATE_FILE):
        return None

    try:
        with open(UPDATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("text")
    except Exception:
        return None


def format_update_message(raw_text):
    parts = [part.strip() for part in raw_text.split(";") if part.strip()]

    if not parts:
        return ""

    lines = ["📢 ОНОВЛЕННЯ", ""]

    for part in parts:
        lines.append(f"• {part}")

    return "\n".join(lines)


def get_main_menu(current_section=None):
    buttons = []

    row1 = []
    if current_section != "character":
        row1.append("🧍 Персонаж")
    if current_section != "world":
        row1.append("🌍 Світ")
    if row1:
        buttons.append(row1)

    row2 = ["⚔️ Бій"]
    if current_section != "inventory":
        row2.append("🎒 Інвентар")
    buttons.append(row2)

    row3 = []
    if current_section != "equipment":
        row3.append("🛡️ Екіпіровка")
    if current_section != "shop":
        row3.append("🏪 Магазин")
    if row3:
        buttons.append(row3)

    row4 = []
    if current_section != "upgrade":
        row4.append("🔨 Покращення")
    if current_section != "update":
        row4.append("📢 Останнє оновлення")
    if row4:
        buttons.append(row4)

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


battle_menu = ReplyKeyboardMarkup(
    [["⚔️ Атакувати"], ["🧍 Персонаж", "🎒 Інвентар"]],
    resize_keyboard=True
)

world_menu = ReplyKeyboardMarkup(
    [["🌲 Ліс", "🏜️ Пустеля"], ["⬅️ Назад"]],
    resize_keyboard=True
)

shop_menu = ReplyKeyboardMarkup(
    [
        ["🛒 Купити зілля", "🛒 Купити меч"],
        ["🛒 Купити броню", "💰 Продати предмет"],
        ["⬅️ Назад"]
    ],
    resize_keyboard=True
)

equipment_menu = ReplyKeyboardMarkup(
    [
        ["⚔️ Одягнути зброю", "🛡️ Одягнути броню"],
        ["🧪 Використати зілля"],
        ["⬅️ Назад"]
    ],
    resize_keyboard=True
)

upgrade_menu = ReplyKeyboardMarkup(
    [
        ["🔨 Покращити зброю", "🔨 Покращити броню"],
        ["⬅️ Назад"]
    ],
    resize_keyboard=True
)


def get_player(user_id):
    user_id = str(user_id)

    if user_id not in players:
        players[user_id] = default_player()
    else:
        players[user_id] = normalize_player(players[user_id])

    save_players()
    return players[user_id]


def get_weapon_bonus(player):
    weapon = player["equipment"].get("weapon")
    if not weapon:
        return 0
    return get_item_damage(weapon)


def get_armor_bonus(player):
    armor = player["equipment"].get("armor")
    if not armor:
        return 0
    return get_item_defense(armor)


def get_total_damage_range(player):
    bonus = get_weapon_bonus(player)
    return 10 + bonus, 20 + bonus


def get_current_location_data(player):
    return LOCATIONS[player["current_location"]]


def check_level_up(player):
    leveled = False

    while player["xp"] >= player["level"] * 25:
        player["level"] += 1
        player["max_hp"] += 20
        player["hp"] = player["max_hp"]
        leveled = True

    return leveled


def roll_loot(enemy_name, location_key):
    enemies = LOCATIONS[location_key]["enemies"]
    enemy_data = next((enemy for enemy in enemies if enemy["name"] == enemy_name), None)

    if not enemy_data:
        return None

    if random.random() > 0.6:
        return None

    return make_item(random.choice(enemy_data["drops"]))


def find_best_item(player, item_type):
    candidates = [item for item in player["inventory"] if item.get("type") == item_type]

    if not candidates:
        return None

    if item_type == "weapon":
        return max(candidates, key=get_item_damage)

    if item_type == "armor":
        return max(candidates, key=get_item_defense)

    return None


def equip_best_item(player, item_type):
    best_item = find_best_item(player, item_type)

    if not best_item:
        return None

    player["inventory"].remove(best_item)

    slot = "weapon" if item_type == "weapon" else "armor"
    old_item = player["equipment"].get(slot)

    if old_item:
        player["inventory"].append(old_item)

    player["equipment"][slot] = best_item
    save_players()

    return best_item


def auto_equip_if_better(player, item):
    item_type = item.get("type")

    if item_type not in ["weapon", "armor"]:
        return []

    slot = "weapon" if item_type == "weapon" else "armor"
    current = player["equipment"].get(slot)

    if item_type == "weapon":
        new_power = get_item_damage(item)
        old_power = get_item_damage(current) if current else 0
    else:
        new_power = get_item_defense(item)
        old_power = get_item_defense(current) if current else 0

    if new_power <= old_power:
        return []

    player["inventory"].remove(item)

    if current:
        player["inventory"].append(current)

    player["equipment"][slot] = item

    if item_type == "weapon":
        return [f"⚔️ Автоматично одягнуто кращу зброю: {item_display(item)}"]
    return [f"🛡️ Автоматично одягнуто кращу броню: {item_display(item)}"]


def use_healing_potion(player):
    for item in player["inventory"]:
        if item.get("name") == "Зілля лікування":
            if player["hp"] >= player["max_hp"]:
                return "full"

            heal = item.get("heal", 40)
            player["inventory"].remove(item)
            player["hp"] = min(player["max_hp"], player["hp"] + heal)
            save_players()
            return heal

    return None


def sell_first_non_equipped_item(player):
    if not player["inventory"]:
        return None, 0

    item = player["inventory"].pop(0)
    price = item_sell_price(item)
    player["gold"] += price
    save_players()

    return item, price


def upgrade_equipped_item(player, slot):
    item = player["equipment"].get(slot)

    if not item:
        return "no_item"

    cost = upgrade_cost(item)

    if player["gold"] < cost:
        return "no_gold"

    player["gold"] -= cost
    item["level"] = item.get("level", 0) + 1
    save_players()

    return cost


async def send_enemy_intro(update, enemy):
    caption = (
        f"⚔️ Ти зустрів {enemy['name']}!\n"
        f"👹 HP: {enemy['hp']}\n\n"
        f"Натисни: ⚔️ Атакувати"
    )

    try:
        with open(enemy["image"], "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=caption,
                reply_markup=battle_menu
            )
    except Exception as error:
        print("Помилка картинки ворога:", error)
        await update.message.reply_text(caption, reply_markup=battle_menu)


async def send_start_image(update):
    try:
        with open(START_IMAGE, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=(
                    "🏹 Останній Герой\n\n"
                    "Попереду — Загублена Земля.\n"
                    "Темрява вже прокинулась."
                )
            )
    except Exception as error:
        print("Помилка стартової картинки:", error)
        await update.message.reply_text("🏹 Останній Герой")


async def update_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ Немає доступу")
        return

    raw_text = " ".join(context.args).strip()

    if not raw_text:
        await update.message.reply_text(
            "Напиши текст оновлення після /update\n\n"
            "Приклад:\n"
            "/update Додано магазин; Додано пустелю; Додано нових ворогів"
        )
        return

    message = format_update_message(raw_text)

    if not message:
        await update.message.reply_text("Не вдалося сформувати оновлення.")
        return

    try:
        await context.bot.send_message(chat_id=GROUP_ID, text=message)
        save_latest_update(message)
        await update.message.reply_text("✅ Оновлення відправлено в групу і збережено")
    except Exception as error:
        await update.message.reply_text(f"❌ Помилка відправки: {error}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player = get_player(update.effective_user.id)
    location = get_current_location_data(player)

    await send_start_image(update)

    first_message = await update.message.reply_text(
        "🌑 Темрява...\n\n"
        "Ти не пам'ятаєш, як тут опинився.\n\n"
        "Лише холод.\n"
        "Лише тиша."
    )

    await asyncio.sleep(1.5)

    await first_message.reply_text(
        "💀 Світ... мертвий.\n\n"
        "Міста зруйновані.\n"
        "Люди зникли.\n\n"
        "Ти один."
    )

    await asyncio.sleep(1.5)

    await first_message.reply_text(
        "🔥 Але щось всередині тебе каже:\n\n"
        "\"Ти ще не закінчив...\""
    )

    await asyncio.sleep(1.5)

    await first_message.reply_text(
        "🏹 ТИ — ОСТАННІЙ ГЕРОЙ\n\n"
        f"📍 Твоя перша локація: {location['name']}\n\n"
        "🌍 Загублена Земля чекає.\n\n"
        "Виживи. Стань сильнішим. Знайди інших.",
        reply_markup=get_main_menu()
    )


async def show_character(update, player):
    weapon = player["equipment"].get("weapon")
    armor = player["equipment"].get("armor")
    min_dmg, max_dmg = get_total_damage_range(player)
    defense = get_armor_bonus(player)
    location = get_current_location_data(player)["name"]

    weapon_text = item_display(weapon) if weapon else "Немає"
    armor_text = item_display(armor) if armor else "Немає"

    await update.message.reply_text(
        f"🧍 Персонаж\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
        f"⭐ Рівень: {player['level']}\n"
        f"✨ XP: {player['xp']}\n"
        f"💰 Золото: {player['gold']}\n"
        f"📍 Локація: {location}\n"
        f"🎒 Предметів у сумці: {len(player['inventory'])}\n"
        f"⚔️ Зброя: {weapon_text}\n"
        f"🛡️ Броня: {armor_text}\n"
        f"🗡️ Урон: {min_dmg}-{max_dmg}\n"
        f"🧱 Захист: {defense}",
        reply_markup=get_main_menu("character")
    )


async def show_world(update, player):
    current = get_current_location_data(player)

    await update.message.reply_text(
        f"🌍 Вибір локації\n"
        f"Поточна: {current['name']}\n\n"
        f"🌲 Ліс (1-5)\n"
        f"🏜️ Пустеля (4-10)",
        reply_markup=world_menu
    )


async def show_inventory(update, player):
    lines = ["🎒 Твій інвентар:"]

    weapon = player["equipment"].get("weapon")
    armor = player["equipment"].get("armor")

    lines.append("")
    lines.append("⚔️ Одягнута зброя:")
    lines.append(f"• {item_display(weapon)} — {item_stat_text(weapon)}" if weapon else "• Немає")

    lines.append("")
    lines.append("🛡️ Одягнута броня:")
    lines.append(f"• {item_display(armor)} — {item_stat_text(armor)}" if armor else "• Немає")

    lines.append("")
    lines.append("🎒 Сумка:")

    if not player["inventory"]:
        lines.append("• Порожньо")
    else:
        for index, item in enumerate(player["inventory"], start=1):
            rarity = RARITY_NAME.get(item.get("rarity", "common"), "звичайний")
            lines.append(
                f"{index}. {item_display(item)} — {item_stat_text(item)} — "
                f"{rarity} — продаж {item_sell_price(item)} зол."
            )

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=get_main_menu("inventory")
    )


async def show_equipment(update, player):
    weapon = player["equipment"].get("weapon")
    armor = player["equipment"].get("armor")

    weapon_text = "Немає"
    armor_text = "Немає"

    if weapon:
        weapon_text = f"{item_display(weapon)} — {item_stat_text(weapon)}"

    if armor:
        armor_text = f"{item_display(armor)} — {item_stat_text(armor)}"

    min_dmg, max_dmg = get_total_damage_range(player)
    defense = get_armor_bonus(player)

    await update.message.reply_text(
        f"🛡️ Екіпіровка\n\n"
        f"⚔️ Зброя: {weapon_text}\n"
        f"🛡️ Броня: {armor_text}\n\n"
        f"🗡️ Підсумковий урон: {min_dmg}-{max_dmg}\n"
        f"🧱 Підсумковий захист: {defense}\n\n"
        f"Кнопки:\n"
        f"⚔️ Одягнути зброю — одягне найкращу зброю із сумки\n"
        f"🛡️ Одягнути броню — одягне найкращу броню із сумки\n"
        f"🧪 Використати зілля — відновить HP",
        reply_markup=equipment_menu
    )


async def show_shop(update, player):
    await update.message.reply_text(
        f"🏪 Магазин\n"
        f"💰 Твоє золото: {player['gold']}\n\n"
        f"🛒 Купити зілля — 15 зол.\n"
        f"🛒 Купити меч — Залізний меч, 70 зол.\n"
        f"🛒 Купити броню — Шкіряна броня, 45 зол.\n"
        f"💰 Продати предмет — продає перший предмет із сумки",
        reply_markup=shop_menu
    )


async def show_upgrade(update, player):
    weapon = player["equipment"].get("weapon")
    armor = player["equipment"].get("armor")

    weapon_text = "Немає"
    armor_text = "Немає"

    if weapon:
        weapon_text = (
            f"{item_display(weapon)} — {item_stat_text(weapon)} — "
            f"ціна покращення {upgrade_cost(weapon)} зол."
        )

    if armor:
        armor_text = (
            f"{item_display(armor)} — {item_stat_text(armor)} — "
            f"ціна покращення {upgrade_cost(armor)} зол."
        )

    await update.message.reply_text(
        f"🔨 Покращення\n"
        f"💰 Золото: {player['gold']}\n\n"
        f"⚔️ Зброя: {weapon_text}\n"
        f"🛡️ Броня: {armor_text}",
        reply_markup=upgrade_menu
    )


async def show_latest_update(update):
    latest = load_latest_update()

    if not latest:
        await update.message.reply_text(
            "📢 Оновлень поки що немає.",
            reply_markup=get_main_menu("update")
        )
        return

    await update.message.reply_text(
        latest,
        reply_markup=get_main_menu("update")
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player = get_player(update.effective_user.id)
    text = update.message.text

    if text == "🧍 Персонаж":
        await show_character(update, player)

    elif text == "🌍 Світ":
        await show_world(update, player)

    elif text == "🌲 Ліс":
        if player["enemy"]:
            await update.message.reply_text("Спочатку закінчи бій.", reply_markup=battle_menu)
            return

        player["current_location"] = "forest"
        save_players()
        await update.message.reply_text("📍 Ти перемістився в Ліс.", reply_markup=get_main_menu("world"))

    elif text == "🏜️ Пустеля":
        if player["enemy"]:
            await update.message.reply_text("Спочатку закінчи бій.", reply_markup=battle_menu)
            return

        if player["level"] < 4:
            await update.message.reply_text("⛔ Пустеля доступна з 4 рівня.", reply_markup=world_menu)
            return

        player["current_location"] = "desert"
        save_players()
        await update.message.reply_text("📍 Ти перемістився в Пустелю.", reply_markup=get_main_menu("world"))

    elif text == "🎒 Інвентар":
        await show_inventory(update, player)

    elif text == "🛡️ Екіпіровка":
        await show_equipment(update, player)

    elif text == "🔨 Покращення":
        await show_upgrade(update, player)

    elif text == "⚔️ Одягнути зброю":
        item = equip_best_item(player, "weapon")
        if not item:
            await update.message.reply_text("⚔️ У сумці немає зброї.", reply_markup=equipment_menu)
            return
        await update.message.reply_text(f"✅ Одягнуто зброю: {item_display(item)}", reply_markup=equipment_menu)

    elif text == "🛡️ Одягнути броню":
        item = equip_best_item(player, "armor")
        if not item:
            await update.message.reply_text("🛡️ У сумці немає броні.", reply_markup=equipment_menu)
            return
        await update.message.reply_text(f"✅ Одягнуто броню: {item_display(item)}", reply_markup=equipment_menu)

    elif text == "🧪 Використати зілля":
        result = use_healing_potion(player)

        if result == "full":
            await update.message.reply_text("❤️ HP вже повне.", reply_markup=equipment_menu)
        elif result is None:
            await update.message.reply_text("🧪 У тебе немає зілля.", reply_markup=equipment_menu)
        else:
            await update.message.reply_text(f"🧪 Ти використав зілля.\n❤️ +{result} HP", reply_markup=equipment_menu)

    elif text == "🔨 Покращити зброю":
        result = upgrade_equipped_item(player, "weapon")

        if result == "no_item":
            await update.message.reply_text("⚔️ Немає зброї для покращення.", reply_markup=upgrade_menu)
        elif result == "no_gold":
            await update.message.reply_text("⛔ Недостатньо золота.", reply_markup=upgrade_menu)
        else:
            await update.message.reply_text(f"🔨 Зброю покращено!\n💰 Витрачено: {result} зол.", reply_markup=upgrade_menu)

    elif text == "🔨 Покращити броню":
        result = upgrade_equipped_item(player, "armor")

        if result == "no_item":
            await update.message.reply_text("🛡️ Немає броні для покращення.", reply_markup=upgrade_menu)
        elif result == "no_gold":
            await update.message.reply_text("⛔ Недостатньо золота.", reply_markup=upgrade_menu)
        else:
            await update.message.reply_text(f"🔨 Броню покращено!\n💰 Витрачено: {result} зол.", reply_markup=upgrade_menu)

    elif text == "🏪 Магазин":
        await show_shop(update, player)

    elif text == "📢 Останнє оновлення":
        await show_latest_update(update)

    elif text == "🛒 Купити зілля":
        item = make_item("Зілля лікування")
        price = item["price"]

        if player["gold"] < price:
            await update.message.reply_text("⛔ Недостатньо золота.", reply_markup=shop_menu)
            return

        player["gold"] -= price
        player["inventory"].append(item)
        save_players()
        await update.message.reply_text("✅ Куплено: Зілля лікування", reply_markup=shop_menu)

    elif text == "🛒 Купити меч":
        item = make_item("Залізний меч")
        price = item["price"]

        if player["gold"] < price:
            await update.message.reply_text("⛔ Недостатньо золота.", reply_markup=shop_menu)
            return

        player["gold"] -= price
        player["inventory"].append(item)
        save_players()
        await update.message.reply_text("✅ Куплено: Залізний меч", reply_markup=shop_menu)

    elif text == "🛒 Купити броню":
        item = make_item("Шкіряна броня")
        price = item["price"]

        if player["gold"] < price:
            await update.message.reply_text("⛔ Недостатньо золота.", reply_markup=shop_menu)
            return

        player["gold"] -= price
        player["inventory"].append(item)
        save_players()
        await update.message.reply_text("✅ Куплено: Шкіряна броня", reply_markup=shop_menu)

    elif text == "💰 Продати предмет":
        item, price = sell_first_non_equipped_item(player)

        if not item:
            await update.message.reply_text("⛔ У сумці немає предметів для продажу.", reply_markup=shop_menu)
            return

        await update.message.reply_text(
            f"💰 Продано: {item_display(item)}\n+{price} золота",
            reply_markup=shop_menu
        )

    elif text == "⬅️ Назад":
        await update.message.reply_text(
            "↩️ Повернення в меню.",
            reply_markup=get_main_menu()
        )

    elif text == "⚔️ Бій":
        if player["enemy"]:
            enemy = player["enemy"]

            await update.message.reply_text(
                f"⚠️ Ти вже в бою з {enemy['name']}!\n"
                f"👹 HP: {enemy['hp']}",
                reply_markup=battle_menu
            )
            return

        location_key = player["current_location"]
        location = get_current_location_data(player)
        enemy = copy.deepcopy(random.choice(location["enemies"]))
        enemy["location_key"] = location_key

        player["enemy"] = enemy
        save_players()

        await send_enemy_intro(update, enemy)

    elif text == "⚔️ Атакувати":
        if not player["enemy"]:
            await update.message.reply_text(
                "Ти не в бою!",
                reply_markup=get_main_menu()
            )
            return

        enemy = player["enemy"]
        log = []

        if random.random() < 0.2:
            log.append("🌀 Ворог ухилився!")
        else:
            base_dmg = random.randint(10, 20)
            weapon_bonus = get_weapon_bonus(player)
            damage = base_dmg + weapon_bonus

            if random.random() < 0.2:
                damage *= 2
                log.append(f"💥 КРИТ! Ти наніс {damage} урону")
            else:
                log.append(f"⚔️ Ти наніс {damage} урону")

            enemy["hp"] -= damage

        if enemy["hp"] <= 0:
            xp = random.randint(10, 20)
            gold = random.randint(8, 18)

            if enemy.get("location_key") == "desert":
                xp += 8
                gold += 8

            player["xp"] += xp
            player["gold"] += gold

            log.append(f"\n🏆 Ти переміг {enemy['name']}!")
            log.append(f"✨ +{xp} XP")
            log.append(f"💰 +{gold} золота")

            loot = roll_loot(enemy["name"], enemy.get("location_key", "forest"))

            if loot:
                player["inventory"].append(loot)
                log.append(f"🎁 Знайдено предмет: {item_display(loot)}")
                log.extend(auto_equip_if_better(player, loot))
            else:
                log.append("📦 Цього разу предмет не випав")

            if check_level_up(player):
                log.append(f"🎉 Новий рівень: {player['level']}!")

            player["enemy"] = None
            save_players()

            await update.message.reply_text(
                "\n".join(log),
                reply_markup=get_main_menu()
            )
            return

        if random.random() < 0.15:
            log.append("\n🛡️ Ти ухилився!")
        else:
            raw_enemy_dmg = random.randint(*enemy["damage"])
            armor_bonus = get_armor_bonus(player)
            enemy_dmg = max(0, raw_enemy_dmg - armor_bonus)
            player["hp"] -= enemy_dmg
            log.append(f"\n💥 {enemy['name']} наніс {enemy_dmg} урону")

        if player["hp"] <= 0:
            player["hp"] = player["max_hp"]
            player["enemy"] = None
            save_players()

            await update.message.reply_text(
                "💀 Ти помер... Відродження!",
                reply_markup=get_main_menu()
            )
            return

        log.append(f"\n❤️ Твоє HP: {player['hp']}/{player['max_hp']}")
        log.append(f"👹 HP ворога: {enemy['hp']}")

        save_players()

        await update.message.reply_text(
            "\n".join(log),
            reply_markup=battle_menu
        )

    else:
        await update.message.reply_text(
            "❓ Використовуй кнопки.",
            reply_markup=get_main_menu()
        )


async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⛔ Можна надсилати тільки текстові повідомлення.",
        reply_markup=get_main_menu()
    )


def main():
    load_players()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update", update_post))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(~filters.TEXT, handle_non_text))

    print("RPG Бот запущений...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
