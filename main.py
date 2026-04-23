import asyncio
import json
import os
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
SAVE_FILE = "players.json"
UPDATE_FILE = "latest_update.json"

GROUP_ID = -5292706881
ADMINS = [6449855887]

START_IMAGE = "images/last_hero.jpg.png"

players = {}

WEAPONS = {
    "Іржавий кинджал": 3,
    "Кістяний меч": 5,
    "Мисливський спис": 7,
    "Залізний меч": 9
}

ARMORS = {
    "Шкіряний шматок": 1,
    "Старий щит": 2,
    "Шкура вовка": 2,
    "Шкіряна броня": 4,
    "Залізний щит": 5
}

HEAL_ITEMS = {
    "Зілля лікування": 30
}

ITEM_PRICES = {
    "Зілля лікування": 15,
    "Іржавий кинджал": 20,
    "Кістяний меч": 35,
    "Мисливський спис": 50,
    "Залізний меч": 70,
    "Шкіряний шматок": 10,
    "Старий щит": 25,
    "Шкура вовка": 18,
    "Шкіряна броня": 45,
    "Залізний щит": 60,
    "Ікло вовка": 8,
    "М'ясо вовка": 6,
    "Кіготь хижака": 14,
    "Темний уламок": 18,
    "Пустельний зуб": 16,
    "Пісочна шкура": 20
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
                player[key] = value.copy()
            elif isinstance(value, list):
                player[key] = value.copy()
            else:
                player[key] = value

    if "equipment" not in player or not isinstance(player["equipment"], dict):
        player["equipment"] = {"weapon": None, "armor": None}

    if "weapon" not in player["equipment"]:
        player["equipment"]["weapon"] = None

    if "armor" not in player["equipment"]:
        player["equipment"]["armor"] = None

    if "inventory" not in player or not isinstance(player["inventory"], list):
        player["inventory"] = []

    if "enemy" not in player:
        player["enemy"] = None

    if "current_location" not in player or player["current_location"] not in LOCATIONS:
        player["current_location"] = "forest"

    return player


def save_players():
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)


def load_players():
    global players

    if not os.path.exists(SAVE_FILE):
        players = {}
        return

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            players = json.load(f)
    except Exception:
        players = {}
        return

    changed = False
    for user_id in list(players.keys()):
        before = json.dumps(players[user_id], ensure_ascii=False, sort_keys=True)
        players[user_id] = normalize_player(players[user_id])
        after = json.dumps(players[user_id], ensure_ascii=False, sort_keys=True)
        if before != after:
            changed = True

    if changed:
        save_players()


def save_latest_update(text: str):
    data = {"text": text}
    with open(UPDATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_latest_update():
    if not os.path.exists(UPDATE_FILE):
        return None

    try:
        with open(UPDATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("text")
    except Exception:
        return None


def format_update_message(raw_text: str) -> str:
    raw_text = raw_text.strip()
    if not raw_text:
        return ""

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


def get_player(user_id):
    user_id = str(user_id)

    if user_id not in players:
        players[user_id] = default_player()
        save_players()
    else:
        players[user_id] = normalize_player(players[user_id])

    return players[user_id]


def get_weapon_bonus(player):
    weapon = player["equipment"]["weapon"]
    if not weapon:
        return 0
    return WEAPONS.get(weapon, 0)


def get_armor_bonus(player):
    armor = player["equipment"]["armor"]
    if not armor:
        return 0
    return ARMORS.get(armor, 0)


def get_total_damage_range(player):
    weapon_bonus = get_weapon_bonus(player)
    return 10 + weapon_bonus, 20 + weapon_bonus


def auto_equip(player):
    equipped_messages = []

    if player["equipment"]["weapon"] is None:
        for item in player["inventory"]:
            if item in WEAPONS:
                player["equipment"]["weapon"] = item
                equipped_messages.append(f"⚔️ Автоматично екіпіровано зброю: {item}")
                break

    if player["equipment"]["armor"] is None:
        for item in player["inventory"]:
            if item in ARMORS:
                player["equipment"]["armor"] = item
                equipped_messages.append(f"🛡️ Автоматично екіпіровано броню: {item}")
                break

    return equipped_messages


def check_level_up(player):
    leveled = False
    while player["xp"] >= player["level"] * 25:
        player["level"] += 1
        player["max_hp"] += 20
        player["hp"] = player["max_hp"]
        leveled = True
    return leveled


def get_current_location_data(player):
    player = normalize_player(player)
    return LOCATIONS[player["current_location"]]


def roll_loot(enemy_name: str, location_key: str):
    enemies = LOCATIONS[location_key]["enemies"]
    enemy_data = next((enemy for enemy in enemies if enemy["name"] == enemy_name), None)
    if not enemy_data:
        return None

    if random.random() > 0.6:
        return None

    return random.choice(enemy_data["drops"])


def sell_first_non_equipped_item(player):
    equipped_weapon = player["equipment"]["weapon"]
    equipped_armor = player["equipment"]["armor"]

    for item in player["inventory"]:
        if item != equipped_weapon and item != equipped_armor:
            player["inventory"].remove(item)
            price = max(1, ITEM_PRICES.get(item, 10) // 2)
            player["gold"] += price
            save_players()
            return item, price

    return None, 0


async def send_enemy_intro(update: Update, enemy: dict):
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
    except Exception as e:
        print("Помилка картинки ворога:", e)
        await update.message.reply_text(caption, reply_markup=battle_menu)


async def send_start_image(update: Update):
    caption = (
        "🏹 Останній Герой\n\n"
        "Попереду — Загублена Земля.\n"
        "Темрява вже прокинулась."
    )

    try:
        with open(START_IMAGE, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=caption)
    except Exception as e:
        print("Помилка стартової картинки:", e)
        await update.message.reply_text("🏹 Останній Герой")


async def update_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMINS:
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

    formatted_message = format_update_message(raw_text)

    if not formatted_message:
        await update.message.reply_text("Не вдалося сформувати текст оновлення.")
        return

    try:
        await context.bot.send_message(chat_id=GROUP_ID, text=formatted_message)
        save_latest_update(formatted_message)
        await update.message.reply_text("✅ Оновлення відправлено в групу і збережено")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка відправки: {e}")


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


async def show_character(update: Update, player):
    weapon = player["equipment"]["weapon"] or "Немає"
    armor = player["equipment"]["armor"] or "Немає"
    min_dmg, max_dmg = get_total_damage_range(player)
    defense = get_armor_bonus(player)
    location_name = get_current_location_data(player)["name"]

    await update.message.reply_text(
        f"🧍 Персонаж\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
        f"⭐ Рівень: {player['level']}\n"
        f"✨ XP: {player['xp']}\n"
        f"💰 Золото: {player['gold']}\n"
        f"📍 Локація: {location_name}\n"
        f"🎒 Предметів: {len(player['inventory'])}\n"
        f"⚔️ Зброя: {weapon}\n"
        f"🛡️ Броня: {armor}\n"
        f"🗡️ Урон: {min_dmg}-{max_dmg}\n"
        f"🧱 Захист: {defense}",
        reply_markup=get_main_menu("character")
    )


async def show_world(update: Update, player):
    current = get_current_location_data(player)
    await update.message.reply_text(
        f"🌍 Вибір локації\n"
        f"Поточна: {current['name']}\n\n"
        f"🌲 Ліс (1-5)\n"
        f"🏜️ Пустеля (4-10)",
        reply_markup=world_menu
    )


async def show_inventory(update: Update, player):
    if not player["inventory"]:
        await update.message.reply_text(
            "🎒 Інвентар порожній.",
            reply_markup=get_main_menu("inventory")
        )
        return

    lines = ["🎒 Твій інвентар:"]
    for i, item in enumerate(player["inventory"], start=1):
        marker = ""
        if item == player["equipment"]["weapon"]:
            marker = " [⚔️ екіпіровано]"
        elif item == player["equipment"]["armor"]:
            marker = " [🛡️ екіпіровано]"

        price = ITEM_PRICES.get(item, 0)
        lines.append(f"{i}. {item}{marker} — {price} зол.")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=get_main_menu("inventory")
    )


async def show_equipment(update: Update, player):
    weapon = player["equipment"]["weapon"]
    armor = player["equipment"]["armor"]

    weapon_text = "Немає"
    armor_text = "Немає"

    if weapon:
        weapon_text = f"{weapon} (+{get_weapon_bonus(player)} урону)"
    if armor:
        armor_text = f"{armor} (-{get_armor_bonus(player)} урону)"

    min_dmg, max_dmg = get_total_damage_range(player)
    defense = get_armor_bonus(player)

    await update.message.reply_text(
        f"🛡️ Екіпіровка\n"
        f"⚔️ Зброя: {weapon_text}\n"
        f"🛡️ Броня: {armor_text}\n"
        f"🗡️ Підсумковий урон: {min_dmg}-{max_dmg}\n"
        f"🧱 Підсумковий захист: {defense}",
        reply_markup=get_main_menu("equipment")
    )


async def show_shop(update: Update, player):
    await update.message.reply_text(
        f"🏪 Магазин\n"
        f"💰 Твоє золото: {player['gold']}\n\n"
        f"🛒 Купити зілля — 15 зол.\n"
        f"🛒 Купити меч (Залізний меч) — 70 зол.\n"
        f"🛒 Купити броню (Шкіряна броня) — 45 зол.\n"
        f"💰 Продати предмет — продає перший неекіпірований предмет за пів ціни",
        reply_markup=shop_menu
    )


async def show_latest_update(update: Update):
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

    elif text == "🏪 Магазин":
        await show_shop(update, player)

    elif text == "📢 Останнє оновлення":
        await show_latest_update(update)

    elif text == "🛒 Купити зілля":
        price = ITEM_PRICES["Зілля лікування"]
        if player["gold"] < price:
            await update.message.reply_text("⛔ Недостатньо золота.", reply_markup=shop_menu)
            return
        player["gold"] -= price
        player["inventory"].append("Зілля лікування")
        save_players()
        await update.message.reply_text("✅ Куплено: Зілля лікування", reply_markup=shop_menu)

    elif text == "🛒 Купити меч":
        price = ITEM_PRICES["Залізний меч"]
        if player["gold"] < price:
            await update.message.reply_text("⛔ Недостатньо золота.", reply_markup=shop_menu)
            return
        player["gold"] -= price
        player["inventory"].append("Залізний меч")
        if player["equipment"]["weapon"] is None:
            player["equipment"]["weapon"] = "Залізний меч"
        save_players()
        await update.message.reply_text("✅ Куплено: Залізний меч", reply_markup=shop_menu)

    elif text == "🛒 Купити броню":
        price = ITEM_PRICES["Шкіряна броня"]
        if player["gold"] < price:
            await update.message.reply_text("⛔ Недостатньо золота.", reply_markup=shop_menu)
            return
        player["gold"] -= price
        player["inventory"].append("Шкіряна броня")
        if player["equipment"]["armor"] is None:
            player["equipment"]["armor"] = "Шкіряна броня"
        save_players()
        await update.message.reply_text("✅ Куплено: Шкіряна броня", reply_markup=shop_menu)

    elif text == "💰 Продати предмет":
        item, price = sell_first_non_equipped_item(player)
        if not item:
            await update.message.reply_text(
                "⛔ Немає предмета для продажу. Екіпіровані речі не продаються автоматично.",
                reply_markup=shop_menu
            )
            return
        await update.message.reply_text(
            f"💰 Продано: {item}\n+{price} золота",
            reply_markup=shop_menu
        )

    elif text == "⬅️ Назад":
        await update.message.reply_text("↩️ Повернення в меню.", reply_markup=get_main_menu())

    elif text == "⚔️ Бій":
        if player["enemy"]:
            enemy = player["enemy"]
            await update.message.reply_text(
                f"⚠️ Ти вже в бою з {enemy['name']}!\n👹 HP: {enemy['hp']}",
                reply_markup=battle_menu
            )
            return

        location_key = player["current_location"]
        base_enemy = random.choice(LOCATIONS[location_key]["enemies"])

        player["enemy"] = {
            "name": base_enemy["name"],
            "hp": base_enemy["hp"],
            "damage": base_enemy["damage"],
            "image": base_enemy["image"],
            "location_key": location_key
        }
        save_players()

        await send_enemy_intro(update, player["enemy"])

    elif text == "⚔️ Атакувати":
        if not player["enemy"]:
            await update.message.reply_text("Ти не в бою!", reply_markup=get_main_menu())
            return

        enemy = player["enemy"]
        log = []

        if random.random() < 0.2:
            log.append("🌀 Ворог ухилився!")
        else:
            base_dmg = random.randint(10, 20)
            weapon_bonus = get_weapon_bonus(player)
            dmg = base_dmg + weapon_bonus

            if random.random() < 0.2:
                dmg *= 2
                log.append(f"💥 КРИТ! Ти наніс {dmg} урону")
            else:
                log.append(f"⚔️ Ти наніс {dmg} урону")

            enemy["hp"] -= dmg

        if enemy["hp"] <= 0:
            xp = random.randint(10, 20)
            gold = random.randint(8, 18)

            if enemy["location_key"] == "desert":
                xp += 8
                gold += 8

            player["xp"] += xp
            player["gold"] += gold

            log.append(f"\n🏆 Ти переміг {enemy['name']}!")
            log.append(f"✨ +{xp} XP")
            log.append(f"💰 +{gold} золота")

            loot = roll_loot(enemy["name"], enemy["location_key"])
            if loot:
                player["inventory"].append(loot)
                log.append(f"🎁 Знайдено предмет: {loot}")
                log.extend(auto_equip(player))
            else:
                log.append("📦 Цього разу предмет не випав")

            if check_level_up(player):
                log.append(f"🎉 Новий рівень: {player['level']}!")

            player["enemy"] = None
            save_players()
            await update.message.reply_text("\n".join(log), reply_markup=get_main_menu())
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
            await update.message.reply_text("💀 Ти помер... Відродження!", reply_markup=get_main_menu())
            return

        log.append(f"\n❤️ Твоє HP: {player['hp']}/{player['max_hp']}")
        log.append(f"👹 HP ворога: {enemy['hp']}")

        save_players()
        await update.message.reply_text("\n".join(log), reply_markup=battle_menu)

    else:
        await update.message.reply_text("❓ Використовуй кнопки", reply_markup=get_main_menu())


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
    app.add_handler(
        MessageHandler(
            filters.PHOTO
            | filters.VIDEO
            | filters.Document.ALL
            | filters.VOICE
            | filters.AUDIO
            | filters.Sticker.ALL
            | filters.VIDEO_NOTE
            | filters.CONTACT
            | filters.LOCATION,
            handle_non_text
        )
    )

    print("RPG Бот запущений...")
    app.run_polling()


if __name__ == "__main__":
    main()