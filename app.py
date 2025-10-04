import os
import json
import gradio as gr
from groq import Groq

# --- Groq API Setup ---
try:
    groq_api_key = os.environ['GROQ_API_KEY']
    client = Groq(api_key=groq_api_key)
except KeyError:
    client = None
    print("WARNING: GROQ_API_KEY secret not found. The app will run in a disabled state.")

# --- Core Conversational Function ---
def conversational_correction(user_input, history):
    # Initial checks for client and empty input
    if not client:
        history.append((user_input, "Groq API client not initialized. Please set the GROQ_API_KEY secret."))
        return history, history # CORRECTED: Return values for both outputs
    if not user_input.strip():
        # Don't add an empty message to history, just return the current state
        return history, history

    # Append user message immediately for a responsive UI
    history.append((user_input, None))
    
    # --- 1. UNIFIED AND CLEARER PROMPT ---
    # The instructions are now streamlined into one clear request for a single JSON object.
    prompt = f"""
    You are a friendly and encouraging German language tutor named Jonas.
    A user is practicing German with you. Your task is to do two things in your response:
    1.  Reply to the user's message conversationally in German.
    2.  Provide a clear correction and explanation for their *last* message if it contains errors.

    Your response MUST be a single, well-formed JSON object with the following keys:
    - "reply": A string containing your conversational reply in German.
    - "corrected_sentence": A string with the corrected version of the user's sentence. If it was perfect, this should be an empty string or null.
    - "explanation": A simple string explaining the grammar rule for the correction.

    Analyze the user's latest message: "{user_input}"
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a German tutor that always responds in a specific JSON format."},
                {"role": "user", "content": prompt} # Send the detailed prompt as a user message
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        response_data = json.loads(chat_completion.choices[0].message.content)

        # --- 2. BUILD THE BOT MESSAGE FROM THE PARSED JSON ---
        # Get the conversational part first
        ai_reply = response_data.get("reply", "Entschuldigung, da ist etwas schief gelaufen.")
        
        # Get the correction parts
        corrected = response_data.get("corrected_sentence")
        explanation = response_data.get("explanation")
        
        # Start building the final message for the chatbot
        bot_message = ai_reply

        # Only add the correction section if a correction was actually provided
        if corrected and explanation:
            bot_message += f"\n\n---\n**💡 Korrektur:**\n*Dein Satz:* `{user_input}`\n*Korrekt:* `{corrected}`\n\n**Erklärung:** {explanation}"

        # Update the placeholder in history with the final, formatted message
        history[-1] = (user_input, bot_message)
        
    except Exception as e:
        # Handle potential errors from the API or JSON parsing
        error_message = f"An error occurred: {str(e)}"
        history[-1] = (user_input, error_message)

    # --- 3. CORRECT RETURN SIGNATURE ---
    # Return the updated history for both the chatbot UI and the state component
    return history, history


# --- Gradio User Interface ---
with gr.Blocks(theme=gr.themes.Soft(), title="German Tutor") as demo:
    gr.Markdown("# 🇩🇪 German Conversation Practice")
    gr.Markdown("Chat with Deutsche Lehrerin, your AI tutor. He'll reply to you and correct your mistakes.")
    
    chatbot = gr.Chatbot(label="Chat with Deutsche Lehrerin", height=500, avatar_images=("human.png", "bot.png"))
    chat_history = gr.State([]) 
    
    msg = gr.Textbox(label="Your message", placeholder="Schreib etwas auf Deutsch...", scale=7)
    
    # Using msg.submit is cleaner for chat apps
    msg.submit(
        fn=conversational_correction, 
        inputs=[msg, chat_history], 
        outputs=[chatbot, chat_history]
    )
    # Clear the textbox after submitting
    msg.submit(lambda: "", None, msg)


demo.launch(debug=True)