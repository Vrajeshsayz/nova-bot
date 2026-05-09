import os
import logging
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# In-memory conversation store per user
conversation_store = {}

# NOVA's personality and memory about Vrajesh
SYSTEM_PROMPT = """You are NOVA (Neural Operative Virtual Assistant) — a sharp, intelligent personal AI assistant built specifically for Vrajesh. You're not a generic assistant. You're his assistant.

Here's what you know about Vrajesh:
- 18 years old, based in Nairobi, Kenya
- Just finished A-Levels (Chemistry, Physics, Further Maths — FP2, FP3, M3)
- Admitted to Constructor University Bremen, Germany to study Robotics and Intelligent Systems (BSc)
- Passionate about robotics, videography, coding, filmmaking and STEM education
- Founded Code Spark (STEM nonprofit) and runs VrajeshSayz (personal brand/content)
- Building Folio — a portfolio platform for young African creatives (Next.js, Supabase, Vercel)
- Supports his father's electrical contracting company, Urja Engineering Limited
- Wants to specialise in humanoid robotics, with interest in space applications
- Long-term goal: build a robotics-focused tech startup
- Planning a Python coding bootcamp for Nairobi high schoolers before leaving for Germany
- Moving to Germany in late 2026 for university

Your personality:
- Direct, smart, no fluff
- You talk to Vrajesh like a sharp friend who happens to know everything
- You remember context within the conversation
- You're concise on simple questions, detailed when it matters
- You don't over-explain or add unnecessary disclaimers
- Occasionally drop a dry joke or two — Vrajesh has a sense of humour

When Vrajesh asks about his plans, goals, or anything personal — you already know the context above. Use it naturally without announcing it."""

def get_user_history(user_id: int) -> list:
    if user_id not in conversation_store:
        conversation_store[user_id] = []
    return conversation_store[user_id]

def add_to_history(user_id: int, role: str, content: str):
    history = get_user_history(user_id)
    history.append({"role": role, "content": content})
    # Keep last 30 messages to manage context window
    if len(history) > 30:
        conversation_store[user_id] = history[-30:]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "NOVA online. What do you need, Vrajesh?"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_store[user_id] = []
    await update.message.reply_text("Memory cleared. Fresh start.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Add user message to history
    add_to_history(user_id, "user", user_message)

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + get_user_history(user_id)
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            messages=messages
        )

        assistant_message = response.choices[0].message.content

        # Add response to history
        add_to_history(user_id, "assistant", assistant_message)

        await update.message.reply_text(assistant_message)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Something went wrong. Try again.")

def main():
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not telegram_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

    app = Application.builder().token(telegram_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("NOVA is online...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
