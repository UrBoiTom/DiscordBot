"""
Discord bot integrating with Google Generative AI for various features,
including conversational AI, welcome/goodbye messages, and utility commands.
"""

import discord
import json
from google import genai
from google.genai import types as genai_types #type:ignore
import re
from datetime import timedelta
import logging # Use standard logging
import sys # For potential exit on config load failure

# --- Constants ---
CONFIG_DIR = 'variables' # Directory for configuration files

# --- Logging Setup ---
# Configure logging for better diagnostics
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration Loading ---

def load_json(filename: str) -> dict:
    """
    Loads data from a JSON file located in the CONFIG_DIR.

    Args:
        filename (str): The name of the JSON file (without the .json extension).

    Returns:
        dict: The data loaded from the JSON file.

    Raises:
        FileNotFoundError: If the specified JSON file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        SystemExit: If loading critical configuration fails.
    """
    filepath = f'{CONFIG_DIR}/{filename}.json' # Construct the full filepath using constant
    try:
        with open(filepath, 'r', encoding='utf-8') as f: # Specify encoding
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file '{filepath}' not found.")
        raise # Re-raise the exception to halt execution if needed
    except json.JSONDecodeError as e:
        logger.error(f"Could not decode JSON from '{filepath}'. Check format. Details: {e}")
        raise # Re-raise the exception

# --- Load Configuration ---
try:
    keys = load_json('keys')
    prompts = load_json('prompts')
    variables = load_json('general')
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit("Exiting due to critical configuration loading errors.") # Exit if essential configs fail

# --- AI Client Initialization ---
try:
    # Initialize the Google Generative AI client using the API key
    genai_client = genai.Client(api_key=keys["ai_studio_key"])
    logger.info("Google Generative AI client initialized.")
except KeyError:
    logger.error("API key 'ai_studio_key' is invalid.")
    sys.exit("Exiting due to missing AI API key.")
except Exception as e:
    logger.error(f"Failed to initialize Google Generative AI client: {e}")
    sys.exit("Exiting due to AI client initialization error.")


# --- Discord Bot Setup ---
# Define the intents (permissions) the bot needs
intents = discord.Intents.default()
intents.message_content = True # Required to read message content
intents.members = True         # Required for member join/leave events and fetching members

# Initialize the Discord client with the specified intents
client = discord.Client(intents=intents)
# Create a command tree for handling slash commands
# It's conventional to name this 'tree' directly if it's closely tied to the client
tree = discord.app_commands.CommandTree(client)

# --- Configuration ---
# Global flag to enable/disable adding available emojis to the AI prompt context.
# If True, the bot will fetch available emojis and instruct the AI on how to use them.
emojis_enabled: bool = variables.get("emojis_enabled", False)
default_ai_model_index = variables.get("default_ai_model_index", 0)
welcome_goodbye_model_index = variables.get("welcome_goodbye_model_index", 1)
timeout_duration_minutes = variables.get("timeout_duration_minutes", 5)
timeout_reason = variables.get("timeout_reason", "")

# --- Event Handlers ---

@client.event
async def on_ready():
    """
    Event handler called when the bot successfully connects to Discord
    and is ready to operate. Synchronizes slash commands.
    """
    logger.info(f'Logged in as {client.user} (ID: {client.user.id})')
    logger.info('Synchronizing slash commands...')
    try:
        # Synchronize slash commands with Discord.
        # Syncing globally can take time; consider syncing per-guild for faster updates during development.
        synced = await tree.sync()
        # Simplified pluralization
        plural = 's' if len(synced) != 1 else ''
        logger.info(f"Synced {len(synced)} command{plural}.")
    except Exception as e:
        logger.exception(f"Failed to sync commands: {e}") # Use logger.exception to include traceback

# --- Slash Commands ---

@tree.command(name="tags", description="Sends the Danbooru tag group wiki link and optionally tags a user.")
async def tags(interaction: discord.Interaction, user: discord.Member = None):
    """
    Slash command to send a link to the Danbooru tag group wiki.
    Optionally mentions a user in the message.

    Args:
        interaction: The interaction object representing the command invocation.
        user: The optional user to mention in the response.
    """
    # Create the button linking to the wiki
    button = discord.ui.Button(
        label='Danbooru Tag Group Wiki',
        url='https://danbooru.donmai.us/wiki_pages/tag_group',
        style=discord.ButtonStyle.link # Explicitly set style for clarity
    )
    view = discord.ui.View().add_item(button)

    # Construct the response message
    content = 'Here is the Danbooru tag group wiki.'
    if user:
        content = f"{user.mention} {content}" # Prepend mention if user is provided

    # Send the response
    await interaction.response.send_message(content, view=view)

@tree.command(name="help", description="See more info about commands")
async def help_command(interaction: discord.Interaction):
    """
    Slash command to display help information about the bot's commands and features.

    Args:
        interaction: The interaction object representing the command invocation.
    """
    # Create an embed message to display the help information
    embed = discord.Embed(
        title="Command List & Bot Info",
        description="Here are the available commands and features:",
        color=discord.Color.green() # Use discord.Color constants
    )
    embed.add_field(name="/help", value="Displays this help message.", inline=False)
    embed.add_field(name="/tags [user]", value="Sends the Danbooru tag group wiki link. Optionally mention a user.", inline=False)
    embed.add_field(
        name="AI Chat",
        value=(
            "Mention the bot or reply to one of its messages "
            "to start a conversation. The bot uses the message history as context."
        ),
        inline=False
    )
    embed.add_field(
        name="AI Welcome & Goodbye",
        value="Generates messages automatically when a member joins or leaves the server.",
        inline=False
    )
    # Send the embed as an ephemeral response (only visible to the user who invoked the command)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Member Event Handlers ---

@client.event
async def on_member_remove(member: discord.Member):
    """
    Event handler called when a member leaves or is kicked/banned from the server.
    Sends an AI-generated goodbye message to the system channel if configured.

    Args:
        member: The member who left the server.
    """
    # Check if a system channel exists to send the message
    if member.guild.system_channel:
        # Prepare the prompt for the AI
        prompt = (
            f"Server Name: {member.guild.name}\n"
            f"User that left ID: {member.id}\n"
            f"User that left name: {member.display_name}"
        )
        logger.info(f"Member Left: {member.display_name} ({member.id}) from {member.guild.name}. Generating goodbye message.")
        logger.debug(f"Goodbye Prompt Context:\n{prompt}") # Log prompt at debug level

        try:
            # Combine system prompts and emoji instructions (if enabled)
            system_prompt_combined = prompts["system_prompt"] + prompts["goodbye_system_prompt"] + await emoji_prompt(member.guild) # Pass guild for context
            # Generate the goodbye message using the AI
            output = await aistudio_request(prompt, system_prompt_combined, welcome_goodbye_model_index)
            # Send the generated message
            await member.guild.system_channel.send(output)
            logger.info(f"Sent AI goodbye message for {member.display_name}.")
        except KeyError as e:
            logger.error(f"Missing prompt key in prompts.json: {e}")
        except Exception as e:
            logger.exception(f"Failed to generate or send goodbye message for {member.display_name}: {e}")


# --- Message Event Handlers ---

# Precompile regex for efficiency if used often
TIMEOUT_REGEX = re.compile(r"!Timeout <@([0-9]+)>")
USER_ID_REGEX = re.compile(r"[0-9]+")

@client.event
async def on_message(message: discord.Message):
    """
    Event handler called when a message is sent in a channel the bot can see.
    Handles:
    1. Ignoring messages from the bot itself.
    2. A hidden command for timing out users (triggered by the bot's own message).
    3. AI interactions when the bot is mentioned or replied to.
    4. AI-generated welcome messages for new members joining.

    Args:
        message: The message object that was sent.
    """
    # 1. Ignore messages sent by the bot itself
    if message.author == client.user:
        # 2. Hidden Timeout Feature (Triggered by bot's own specific message format)
        # Note: This is an unusual pattern. Consider a dedicated command or interaction.
        timeout_match = TIMEOUT_REGEX.search(message.content)
        if timeout_match:
            try:
                user_id_str = timeout_match.group(1) # Get user ID from the first capture group
                user_id = int(user_id_str)
                member = message.guild.get_member(user_id)
                if member:
                    await member.timeout(timedelta(minutes=timeout_duration_minutes), reason=timeout_reason)
                    logger.info(f"Timed out {member.display_name} ({user_id}) for {timeout_duration_minutes} minutes.")
                else:
                    logger.warning(f"Could not find member with ID {user_id} to time out in guild {message.guild.name}.")
            except (ValueError, IndexError):
                logger.error(f"Failed to parse user ID from timeout command: {message.content}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to time out member {user_id} in {message.guild.name}.")
            except discord.HTTPException as e:
                logger.error(f"Failed to time out member {user_id} due to API error: {e}")
        return # Stop processing after handling bot's own message

    # --- AI Interaction Handling ---
    # 3. Check if the bot was mentioned or replied to
    is_mention = client.user in message.mentions  or client.user.display_name in message.content
    is_reply_to_bot = message.reference and message.reference.resolved and message.reference.resolved.author == client.user

    if is_mention or is_reply_to_bot:
        async with message.channel.typing(): # Show typing indicator
            try:
                # Format the initial prompt with sender info and message content
                latest_message_prompt = (
                    f"Sender ID: {message.author.id}\n"
                    f"Sender Name: {message.author.display_name}\n"
                    f"Message: {message.content}"
                )
                # Fetch the reply chain to build context
                full_prompt = await get_replies(message, latest_message_prompt)
                logger.info(f"Received AI query from {message.author.display_name} ({message.author.id}). Generating response.")
                logger.debug(f"AI Prompt Context:\n{full_prompt}") # Log full prompt at debug level

                # Combine system prompt and emoji instructions (if enabled)
                system_prompt_combined = prompts["system_prompt"] + await emoji_prompt(message.guild) # Pass guild for context

                # Generate AI response
                output = await aistudio_request(full_prompt, system_prompt_combined, default_ai_model_index)

                # Reply to the original message with the AI's output
                await message.reply(output)
                logger.info(f"Sent AI reply to {message.author.display_name}.")

            except KeyError as e:
                logger.error(f"Missing prompt key in prompts.json: {e}")
                await message.reply("Sorry, I encountered a configuration error and couldn't process that.")
            except Exception as e:
                logger.exception(f"Error during AI interaction processing: {e}")
                await message.reply("Sorry, something went wrong while generating a response.")
        return # Don't process as a new member message if it was an AI interaction

    # --- New Member Welcome Message ---
    # 4. Check if the message type indicates a new member joined (system message)
    if message.type == discord.MessageType.new_member:
        # Ensure the author is the user who joined (for standard welcome messages)
        if message.author == message.author: # This check seems redundant, maybe meant message.author == member who joined?
                                             # The message.author *is* the member who joined for this message type.
            async with message.channel.typing():
                try:
                    # Prepare the prompt for the welcome message AI
                    prompt = (
                        f"New User ID: {message.author.id}\n"
                        f"New User Name: {message.author.display_name}"
                    )
                    logger.info(f"New member joined: {message.author.display_name} ({message.author.id}). Generating welcome message.")
                    logger.debug(f"Welcome Prompt Context:\n{prompt}") # Log prompt at debug level

                    # Combine system prompts and emoji instructions (if enabled)
                    system_prompt_combined = prompts["system_prompt"] + prompts["welcome_system_prompt"] + await emoji_prompt(message.guild) # Pass guild for context
                    # Generate the welcome message using the AI
                    output = await aistudio_request(prompt, system_prompt_combined, welcome_goodbye_model_index)

                    # Reply to the system's welcome message with the AI's generated message
                    await message.reply(output)
                    logger.info(f"Sent AI welcome message for {message.author.display_name}.")
                except KeyError as e:
                    logger.error(f"Missing prompt key in prompts.json: {e}")
                except Exception as e:
                    logger.exception(f"Failed to generate or send welcome message for {message.author.display_name}: {e}")
        return # Handled as new member message

# --- Helper Functions ---

async def aistudio_request(prompt: str, system_prompt: str, model_index: int = 0) -> str:
    """
    Sends a request to the Google AI Studio API (GenAI) to generate content.
    Includes error handling and fallback to the next model if available.

    Args:
        prompt: The user prompt and conversation context.
        system_prompt: The system instruction for the AI model.
        model_index: The index of the AI model to use from variables.json.

    Returns:
        The generated text response from the AI, or a user-friendly error message.
    """
    available_models = variables.get("models", {}).get("ai_studio", [])
    if not available_models:
        logger.error("No AI Studio models defined in variables.json under models.ai_studio")
        return "Sorry, the AI models are not configured correctly."

    if model_index >= len(available_models):
        logger.error(f"Initial model index {model_index} is out of bounds (only {len(available_models)} models defined).")
        return "Sorry, I encountered an issue selecting an AI model."

    current_model_name = available_models[model_index]
    logger.debug(f"Attempting AI request with model: {current_model_name} (Index: {model_index})")

    try:
        # Attempt to generate content using the specified model
        response = genai_client.models.generate_content(
            model=current_model_name,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt
            ),
            contents=prompt
        )
        # Basic cleanup: remove potential leading metadata lines added by the prompt structure.
        # This regex is safer than the previous one, only removing lines that *start* with "Sender ID:", "Sender Name:", or "Message: ".
        # It might still remove legitimate starting lines if the AI generates them, but it's less aggressive.
        output = re.sub(r"^(Sender ID:|Sender Name:|Message:).*\n?", "", response.text, flags=re.MULTILINE).strip()
        # Check if the response is empty after potential cleanup or if the API returned empty
        if not output:
            logger.warning(f"AI model {current_model_name} returned an empty response.")
            # Consider falling back or returning a specific message
            raise ValueError("AI returned empty response") # Trigger fallback logic
        return output

    except IndexError: # Should not happen with the initial check, but good for safety.
        logger.error(f"Model index {model_index} became invalid unexpectedly.")
        return "Sorry, I encountered an internal error selecting an AI model."
    except Exception as e:
        logger.warning(f"Error with AI model {current_model_name} (Index {model_index}): {e}")
        # Try the next model index if available
        next_model_index = model_index + 1
        if next_model_index < len(available_models):
            logger.info(f"Trying next AI model index: {next_model_index}")
            # Recursive call to try the next model
            return await aistudio_request(prompt, system_prompt, next_model_index)
        else:
            # No more models left to try
            logger.error(f"No more AI models available to try after index {model_index}.")
            return "Sorry, I encountered an issue processing your request with all available AI models."


async def get_replies(message: discord.Message, current_prompt_str: str) -> str:
    """
    Traverses the reply chain of a message upwards to build a conversation history string,
    starting from the oldest message in the chain.

    Args:
        message: The starting message object (the most recent one).
        current_prompt_str: The formatted string for the most recent message.

    Returns:
        A string containing the conversation history, formatted for the AI,
        ordered from oldest to newest message.
    """
    history = [current_prompt_str] # Start with the latest message
    caching_log = "" # Log to track how messages were fetched

    current_message = message # Start traversal from the initial message

    # Loop while the current message is a reply and we can resolve the reference
    while current_message.reference and current_message.reference.message_id:
        ref = current_message.reference
        referenced_message = None

        # 1. Check cache first
        if ref.cached_message:
            referenced_message = ref.cached_message
            caching_log += "C" # Log cache hit
        # 2. Check resolved (partially fetched) message
        elif isinstance(ref.resolved, discord.Message):
            referenced_message = ref.resolved
            caching_log += "R" # Log resolved hit
        # 3. Fetch from API as a last resort
        else:
            try:
                # Ensure channel is fetchable
                if isinstance(message.channel, (discord.TextChannel, discord.Thread)):
                    referenced_message = await message.channel.fetch_message(ref.message_id)
                    caching_log += "F" # Log API fetch
                else:
                    logger.warning(f"Cannot fetch message {ref.message_id} from channel type {type(message.channel)}. Stopping reply chain.")
                    break
            except discord.NotFound:
                logger.warning(f"Could not fetch referenced message {ref.message_id} (Not Found). Stopping reply chain.")
                break
            except discord.Forbidden:
                logger.warning(f"Could not fetch referenced message {ref.message_id} (Forbidden). Stopping reply chain.")
                break
            except discord.HTTPException as e:
                logger.warning(f"Discord API error fetching message {ref.message_id}: {e}. Stopping reply chain.")
                break

        # If we successfully got the referenced message
        if referenced_message:
            # Format the message details and add to the *beginning* of the history list
            history.insert(0, (
                f"Sender ID: {referenced_message.author.id}\n"
                f"Sender Name: {referenced_message.author.display_name}\n"
                f"Message: {referenced_message.content}"
            ))
            # Move up the chain
            current_message = referenced_message
        else:
            # Stop if we couldn't get the message for any reason
            break

    # Log the caching strategy used for debugging if any fetching occurred
    if caching_log:
        logger.debug(f"Reply Caching Log (C=Cache, R=Resolved, F=Fetch): {caching_log}")

    # Join the history list into a single string, ordered oldest to newest
    return "\n".join(history)


async def emoji_prompt(guild: discord.Guild | None) -> str:
    """
    Fetches available custom emojis (guild-specific and application-owned)
    and formats them into a string with instructions for the AI.

    Args:
        guild: The guild context to fetch emojis from. Can be None if context is unavailable.

    Returns:
        A formatted string containing available emojis and usage instructions,
        or an empty string if emojis_enabled is False or no emojis are found.
    """
    if not emojis_enabled:
        return "" # Return early if the feature is disabled

    static_emojis = []
    animated_emojis = []

    # 1. Guild Emojis (if in a guild context)
    if guild:
        for emoji in guild.emojis:
            if emoji.available: # Only include usable emojis
                if emoji.animated:
                    animated_emojis.append(f"<a:{emoji.name}:{emoji.id}>")
                else:
                    static_emojis.append(f"<:{emoji.name}:{emoji.id}>")

    # 2. Application (Bot-owned) Emojis - These might be usable across guilds
    # Note: fetch_application_emojis requires special permissions/setup for bot-owned emojis.
    # If you don't have specific bot-owned emojis, this might return an empty list or error.
    try:
        application_emojis = await client.fetch_application_emojis()
        for emoji in application_emojis:
            if emoji.available:
                formatted_emoji = f"<{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>"
                # Avoid duplicates if an app emoji is also somehow in guild.emojis
                if emoji.animated and formatted_emoji not in animated_emojis:
                    animated_emojis.append(formatted_emoji)
                elif not emoji.animated and formatted_emoji not in static_emojis:
                    static_emojis.append(formatted_emoji)
    except discord.HTTPException as e:
        logger.warning(f"Could not fetch application emojis: {e}") # Log if fetching app emojis fails
    except AttributeError:
        logger.warning("client.fetch_application_emojis() not available or failed.")


    # Only add the emoji section to the prompt if emojis were actually found
    if static_emojis or animated_emojis:
        emoji_list_str = ""
        if static_emojis:
            emoji_list_str += f"Static emojis: {', '.join(static_emojis)}\n"
        if animated_emojis:
            emoji_list_str += f"Animated emojis: {', '.join(animated_emojis)}\n"

        # Construct the final prompt string with emoji lists and instructions
        # Ensure 'emoji_prompt' exists in your prompts.json
        emoji_instructions = prompts.get("emoji_prompt", "Use the provided emojis in your response where appropriate by including their full code (e.g., <:name:id> or <a:name:id>).")
        return f"\n## Available Emojis:\n{emoji_list_str}{emoji_instructions}"
    else:
        logger.debug("No available custom emojis found for emoji prompt.")
        return "" # Return empty string if no emojis are available


# --- Bot Execution ---
if __name__ == "__main__":
    try:
        client_token = keys["client_key"]
        if not client_token:
            raise ValueError("Client token is empty.")
        logger.info("Starting bot...")
        client.run(client_token, log_handler=None) # Use internal discord.py logging configured above
    except KeyError:
        logger.error("Discord client token 'client_key' not found in keys.json.")
    except ValueError as e:
        logger.error(f"Invalid Discord client token: {e}")
    except discord.LoginFailure:
        logger.error("Failed to log in to Discord. Check the client token.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during bot execution: {e}")

