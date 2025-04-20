import discord
import json
from google import genai
from google.genai import types # type: ignore
import re

# --- Configuration Loading ---

def load_json(filename):
    """
    Loads data from a JSON file.

    Args:
        filename (str): The name of the JSON file (without the .json extension).

    Returns:
        dict: The data loaded from the JSON file.

    Raises:
        FileNotFoundError: If the specified JSON file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    filepath = f'{filename}.json' # Construct the full filepath
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{filepath}' not found.")
        # Depending on how critical these files are, you might want to exit here
        # import sys
        # sys.exit(1)
        raise # Re-raise the exception to halt execution if needed
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from '{filepath}'. Check the file format. Details: {e}")
        raise # Re-raise the exception

# Load configuration files
keys = load_json('keys')
prompts = load_json('prompts')
variables = load_json('variables')

# --- AI Client Initialization ---
# Initialize the Google Generative AI client using the API key
genai_client = genai.Client(api_key=keys["ai_studio_key"])

# --- Discord Bot Setup ---
# Define the intents (permissions) the bot needs
intents = discord.Intents.default()
intents.message_content = True # Required to read message content
intents.members = True         # Required for member join/leave events

# Initialize the Discord client with the specified intents
client = discord.Client(intents=intents)
# Create a command tree for handling slash commands
client.tree = discord.app_commands.CommandTree(client)

# --- Configuration ---
# Define the AI provider (currently set to Google AI Studio)
ai_provider = "ai_studio"
# Global flag to enable/disable adding available emojis to the AI prompt context. If True, the bot will fetch available emojis and instruct the AI on how to use them.
emojis_enabled = False

# --- Event Handlers ---

@client.event
async def on_ready():
    """
    Event handler called when the bot successfully connects to Discord.
    """
    print(f'Logged in as {client.user}')
    try:
        # Synchronize slash commands with Discord
        synced = await client.tree.sync()
        # Determine pluralization for the log message
        if (len(synced) == 1): plural = ""
        else: plural = 's'
        print(f"Synced {len(synced)} command{plural}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# --- Slash Commands ---

@client.tree.command(name="tags", description="Sends the Danbooru tag group wiki link and optionally tags a user.")
async def tags(interaction: discord.Interaction, user: discord.Member = None):
    """
    Slash command to send a link to the Danbooru tag group wiki.
    Optionally mentions a user in the message.
    """
    # Create the button linking to the wiki
    button = discord.ui.Button(label='Danbooru Tag Group Wiki', url='https://danbooru.donmai.us/wiki_pages/tag_group')
    view = discord.ui.View().add_item(button)

    # Send the response, mentioning the user if provided
    if user:
        await interaction.response.send_message(f"{user.mention} Here is the Danbooru tag group wiki.", view=view)
    else:
        await interaction.response.send_message('Here is the Danbooru tag group wiki.', view=view)

@client.tree.command(name="help", description="See more info about commands")
async def help_command(interaction: discord.Interaction):
    """
    Slash command to display help information about the bot's commands and features.
    """
    # Create an embed message to display the help information
    embed = discord.Embed(title="Command List", description="Here are the available commands:", color=0x00ff00)
    embed.add_field(name="/help", value="Displays this help message.", inline=False)
    embed.add_field(name="/tags", value="Sends the Danbooru tag group wiki link and optionally tags a user.", inline=False)
    embed.add_field(name="AI Features", value="To use the AI features, simply mention the bot in a message, or reply to a message the bot sent. The bot will reply to your message, taking the whole reply chain as context.", inline=False)
    embed.add_field(name="AI-based join and leave messages", value="Activate automatically when a member joins or leaves.", inline=False)
    # Send the embed as the response
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Member Event Handlers ---

@client.event
async def on_member_remove(member):
    """
    Event handler called when a member leaves the server.
    Sends an AI-generated goodbye message to the system channel.
    """
    # Check if a system channel exists to send the message
    if member.guild.system_channel:
        # Prepare the prompt for the AI
        prompt = f"\nServer Name: {member.guild.name}\nUser that left ID: {member.id}\nUser that left name: {member.display_name}"
        print(f"\n--------------------- MEMBER LEAVE ---------------------\n{prompt}") # Log the event
        # Generate the goodbye message using the AI
        if(ai_provider == "ai_studio"):
                output = await aistudio_request(prompt, prompts["system_prompt"] + prompts["goodbye_system_prompt"] + await emoji_prompt(), 1) # Use model index 1 for goodbye
        # Send the generated message
        await member.guild.system_channel.send(output)


# --- Message Event Handlers ---

@client.event
async def on_message(message):
    """
    Event handler called when a message is sent in a channel the bot can see.
    Handles AI interactions (mentions/replies) and new member welcome messages.
    """
    # Ignore messages sent by the bot itself
    if message.author == client.user:
        return

    # --- AI Interaction Handling ---
    # Check if the bot was mentioned or its display name is in the message content
    if client.user in message.mentions or (client.user.display_name and client.user.display_name in message.content):
        # Show typing indicator while processing
        async with message.channel.typing():
            # Format the initial prompt with sender info and message content
            prompt = f"Sender ID: {message.author.id}\nSender Name: {message.author.display_name}\nMessage: {message.content}"
            # Fetch the reply chain to build context
            prompt = await get_replies(message, prompt)
            print(f"\n----------------------- AI PROMPT -----------------------\n{prompt}") # Log the full prompt
            # Generate AI response based on the provider
            if(ai_provider == "ai_studio"):
                # Generate the AI response, including emoji instructions if enabled
                output = await aistudio_request(prompt, prompts["system_prompt"] + await emoji_prompt(), True)
        # Reply to the original message with the AI's output
        await message.reply(output)

    # --- New Member Welcome Message ---
    # Check if the message type indicates a new member joined (system message)
    if message.type == discord.MessageType.new_member:
        # Show typing indicator
        async with message.channel.typing():
            # Prepare the prompt for the welcome message AI
            prompt = f"New User ID: {message.author.id}\nNew User Name: {message.author.display_name}"
            print(f"\n--------------------- NEW MEMBER ---------------------\n{prompt}") # Log the event
            # Generate the welcome message using the AI
            if(ai_provider == "ai_studio"):
                # Use model index 1 for welcome message
                # Generate the AI response, including emoji instructions if enabled
                output = await aistudio_request(prompt, prompts["system_prompt"] + prompts["welcome_system_prompt"] + await emoji_prompt(), 1)
        # Reply to the welcome message (which is usually a system message)
        await message.reply(output)

# --- Helper Functions ---

async def aistudio_request(prompt, system_prompt, modelIndex = 0):
    """
    Sends a request to the Google AI Studio API (GenAI) to generate content.
    Includes basic error handling and fallback to the next model if available.

    Args:
        prompt (str): The user prompt and context.
        system_prompt (str): The system instruction for the AI model.
        modelIndex (int, optional): The index of the AI model to use from variables.json. Defaults to 0.

    Returns:
        str: The generated text response from the AI, or an error message.
    """
    try:
        # Attempt to generate content using the specified model
        response = genai_client.models.generate_content(
            model=variables["models"]["ai_studio"][modelIndex], # Select model by index
            config=types.GenerateContentConfig(
                system_instruction=system_prompt # Provide system instructions
            ),
            contents = prompt # Provide the main prompt/context
        )
        output = response.text
    except IndexError:
        # Handle case where modelIndex is out of bounds (no more models to try)
        print(f"\n------------------------- AI ERROR -------------------------\nError: No more models available to try after index {modelIndex}.")
        output = "Sorry, I encountered an issue processing your request with all available AI models."
    except Exception as e:
        # Handle other potential API errors
        print(f"\n------------------------- AI ERROR -------------------------\nError with model index {modelIndex}: {e}")
        # Recursively try the next model index if available
        try:
            print(f"Trying next model index: {modelIndex + 1}")
            output = await aistudio_request(prompt, system_prompt, modelIndex + 1) # Pass system_prompt in recursive call
        except IndexError: # Catch index error from the recursive call immediately
            print(f"\n------------------------- AI ERROR -------------------------\nError: No more models available to try after index {modelIndex}.")
            output = "Sorry, I encountered an issue processing your request with all available AI models."
        except Exception as final_e: # Catch any other error during retry
            print(f"\n------------------------- AI ERROR -------------------------\nError during retry: {final_e}")
            output = "Sorry, I encountered an unexpected error while processing your request."

    # Clean up potential metadata leakage from the AI response (optional, but good practice)
    # This regex removes lines like "Sender ID: 12345..." from the start of the output
    output = re.sub(r"(.|\n)*Message: ", "", output)
    return output


async def get_replies(message, string):
    """
    Traverses the reply chain of a message to build a conversation history string.

    Args:
        message (discord.Message): The starting message object.
        string (str): The initial string (usually the latest message).

    Returns:
        str: A string containing the conversation history, formatted for the AI.
    """
    cachingLog = "" # Log to track how messages were fetched (cache, resolved, fetch)
    # Loop while the current message is a reply and the referenced message exists
    while(message.reference and not isinstance(message.reference.resolved, discord.DeletedReferencedMessage)):
        # Prioritize cached message for efficiency
        if(message.reference.cached_message):
            message = message.reference.cached_message
            cachingLog += "C" # Log cache hit
        else:
            # Use resolved message if available (already fetched partially)
            if(message.reference.resolved):
                message = message.reference.resolved
                cachingLog += "R" # Log resolved hit
            # Otherwise, fetch the full message from Discord API
            else:
                try:
                    message = await message.channel.fetch_message(message.reference.message_id)
                    cachingLog += "X" # Log API fetch
                except discord.NotFound:
                    # Stop if the referenced message couldn't be found
                    print(f"Warning: Could not fetch referenced message {message.reference.message_id}. Stopping reply chain traversal.")
                    break
                except discord.HTTPException as e:
                    # Stop on other Discord API errors
                    print(f"Warning: Discord API error fetching message {message.reference.message_id}: {e}. Stopping reply chain traversal.")
                    break

        # Prepend the fetched message details to the context string
        string = f"Sender ID: {message.author.id}\nSender Name: {message.author.display_name}\nMessage: {message.content}\n{string}"

    # Log the caching strategy used for debugging
    if(cachingLog != ""):
        print(f"\n-------------------- REPLY CACHING LOG --------------------\n{cachingLog}")
    return string

async def emoji_prompt():
    """
    Fetches available client and application emojis and formats them into a string
    with instructions for the AI on how to use them in its responses.

    Returns:
        str: A formatted string containing available emojis and usage instructions,
            or an empty string if emojis_enabled is False.
    """
    # Only proceed if emoji usage is enabled globally
    if(emojis_enabled):
        # Fetch emojis specific to this application (e.g., bot-owned emojis)
        application_emojis = await client.fetch_application_emojis() # Load emojis
        # Initialize lists to store formatted emoji strings
        static_emojis = []
        animated_emojis = []

        # Iterate through emojis the bot has access to in guilds it's in
        for emoji in client.emojis:
            # Sort emojis into static and animated lists with Discord formatting
            if emoji.animated:
                animated_emojis.append(f"<a:{emoji.name}:{emoji.id}>")
            else:
                static_emojis.append(f"<:{emoji.name}:{emoji.id}>")

        # Iterate through the application-specific emojis
        for emoji in application_emojis:
            # Sort emojis into static and animated lists with Discord formatting
            if emoji.animated:
                animated_emojis.append(f"<a:{emoji.name}:{emoji.id}>")
            else:
                static_emojis.append(f"<:{emoji.name}:{emoji.id}>")

        # Construct the final prompt string with emoji lists and instructions
        # This tells the AI which emojis are available and how to format them correctly.
        return f"## Available emojis:\nStatic emojis: {", ".join(static_emojis)}\nAnimated emojis: {", ".join(animated_emojis)}\n{prompts['emoji_prompt']}"
    else:
        # Return an empty string if emojis are disabled, so nothing is added to the AI prompt
        return ""

# --- Bot Execution ---
# Run the bot using the client token from keys.json
client.run(keys["client_key"])
