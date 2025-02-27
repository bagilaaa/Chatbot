import asyncio
import subprocess
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters, MessageHandler
import openai
import traceback

# OpenAI API key
openai.api_key = "openaikey"

# It stores last analysis
last_analysis = {}

# Asynchronous /start command
async def start(update, context):
    menu_text = (
        "*Hello! I am a bot for web penetration testing.*\n\n"
        "Here's what I can do:\n\n"
        "1. /chat - *Ask me any penetration testing questions!*\n"
        "2. /code - *Send me your code for vulnerability analysis.*\n"
        "3. /pentest - *Run penetration testing tools.*\n\n"
        "*Enter a command to get started!*"
    )
    await update.message.reply_text(menu_text, parse_mode='Markdown')

async def pentest_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_text = (
        "*Pentesting Tools Menu:*\n\n"
        "1. /nikto <URL> - *Scan a website using Nikto for identifying common vulnerabilities and misconfigurations.*\n"
        "2. /sqlmap <URL> - *Scan a website using SQLMap for detecting SQL injection vulnerabilities.*\n"
        "3. /fetchpage <URL> - *Extract all links from a web page for analyzing the site structure and finding potential entry points.*\n"
        "*Enter a command to get started!!*"
    )
    await update.message.reply_text(menu_text, parse_mode='Markdown')

# Asynchronous /chat command
async def chat(update, context):
    user_input = update.message.text.strip()

    try:
        # Send user input for a response
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Use a suitable GPT model
            messages=[{"role": "system", "content": "You are an expert in web application security and penetration testing. Answer the following user questions."},
                      {"role": "user", "content": user_input}]
        )

        # Get response from GPT
        gpt_reply = response['choices'][0]['message']['content']

        # Send a simplified response
        await update.message.reply_text(gpt_reply, parse_mode='Markdown')

    except Exception as e:
        error_message = traceback.format_exc()
        print(f"Error: {error_message}")
        await update.message.reply_text("An error occurred while processing your request. Please try again later.")

# Asynchronous /code command
async def code(update, context):
    user_input = update.message.text.strip()

    if user_input == "/code":
        # Ask to send code
        await update.message.reply_text("*Please send me the code you'd like to analyze for vulnerabilities.*")
        return

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Use a suitable GPT model
            messages=[{"role": "system", "content": "You are an expert in web application security. Please analyze the code and identify any vulnerabilities. Provide only the name and a brief definition of the vulnerability."},
                      {"role": "user", "content": user_input}]
        )

        gpt_reply = response['choices'][0]['message']['content']

        # Save analysis for report
        last_analysis['code_analysis'] = gpt_reply

        analysis_message = (
            "*Vulnerability Summary:*\n\n"
            f"{gpt_reply}\n\n"
            "*For a detailed report, use the /report command.*"
        )

        await update.message.reply_text(analysis_message, parse_mode='Markdown')

    except Exception as e:
        error_message = traceback.format_exc()
        print(f"Error: {error_message}")
        await update.message.reply_text("An error occurred while processing your request. Please try again later.")

# /report command
async def report(update, context):
    try:
        if 'code_analysis' in last_analysis:
            analysis = last_analysis['code_analysis']

            # Generate a report
            report_text = "*Vulnerability Report:*\n\n"

            # Include a brief summary of the vulnerabilities identified
            report_text += f"*Vulnerabilities Identified:*\n{analysis[:1500]}\n\n"

            # Protection methods and suggested tools
            prompt = f"Based on the following vulnerability analysis: {analysis[:1500]}, suggest protection methods and tools for fixing these vulnerabilities."
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are an expert in web application security."},
                          {"role": "user", "content": prompt}]
            )
            recommendations = response['choices'][0]['message']['content']

            # Generated recommendations
            report_text += "*Protection Methods and Tools:*"
            report_text += "\n" + recommendations

            # If the message exceeds Telegram's character limit
            if len(report_text) > 4096:
                # If too large, split it into multiple messages
                part1 = report_text[:2000]
                part2 = report_text[2000:]
                await update.message.reply_text(part1, parse_mode='Markdown')
                await update.message.reply_text(part2, parse_mode='Markdown')
            else:
                await update.message.reply_text(report_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("No code analysis has been performed yet. Please run the /code command first.", parse_mode='Markdown')
    except Exception as e:
        error_message = traceback.format_exc()
        print(f"Error while generating the report: {error_message}")
        await update.message.reply_text("An error occurred while generating the report. Please try again later.")


# Function to perform Nikto scan asynchronously
async def nikto_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = ' '.join(context.args)  # Get the URL from command arguments
    if not url:
        await update.message.reply_text("Пожалуйста, укажите URL для сканирования с помощью Nikto.")
        return

    try:
        await update.message.reply_text(f"Начинаю сканирование {url}...")

        # Start Nikto scan using subprocess in async mode
        command = ["nikto", "-h", url]
        process = await asyncio.create_subprocess_exec(
            *command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Function to read and send output in chunks
        async def read_and_send_output(stream, is_stderr=False):
            buffer = ""
            while True:
                line = await stream.readline()
                if not line:
                    break
                buffer += line.decode().strip() + "\n"
                # Send output in chunks of 10 lines or when buffer is too large
                if buffer.count("\n") >= 10 or len(buffer) >= 4096:
                    if is_stderr:
                        await update.message.reply_text(f"Ошибка: {buffer}")
                    else:
                        await update.message.reply_text(buffer)
                    buffer = ""
            # Send remaining output
            if buffer:
                if is_stderr:
                    await update.message.reply_text(f"Ошибка: {buffer}")
                else:
                    await update.message.reply_text(buffer)

        # Read stdout and stderr concurrently
        await asyncio.gather(
            read_and_send_output(process.stdout),
            read_and_send_output(process.stderr, is_stderr=True)
        )

        # Check the return code
        return_code = await process.wait()
        if return_code != 0:
            await update.message.reply_text(f"Команда завершилась с кодом {return_code}.")

        # Notify that the scan is complete
        await update.message.reply_text("Сканирование завершено. Вы можете запустить новое сканирование, отправив команду /nikto <URL>.")

    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка при запуске Nikto: {e}")


# Function for scanning with SQLMap
async def sqlmap_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = ' '.join(context.args)
    if not url:
        await update.message.reply_text("Please provide a URL to scan with SQLMap. Example: /sqlmap https://example.com")
        return

    try:
        await update.message.reply_text(f"Starting SQLMap scan for {url}...")

        command = ["sqlmap", "-u", url, "--batch"]
        process = await asyncio.create_subprocess_exec(
            *command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Collect all output
        full_output = []
        while True:
            output = await process.stdout.readline()
            if output:
                output_text = output.decode().strip()
                if output_text:
                    full_output.append(output_text)
            else:
                break

        # Save output to a file
        with open("sqlmap_output.txt", "w") as file:
            file.write("\n".join(full_output))

        # Send the file to the user
        with open("sqlmap_output.txt", "rb") as file:
            await update.message.reply_document(document=file, caption="SQLMap Scan Results")

        # Check stderr for errors
        stderr = await process.stderr.read()
        if stderr:
            stderr_text = stderr.decode().strip()
            if stderr_text:
                await update.message.reply_text(f"Error: {stderr_text}")

        # Check the return code
        return_code = await process.wait()
        if return_code != 0:
            await update.message.reply_text(f"SQLMap exited with code {return_code}.")

        # Notification of completion
        await update.message.reply_text("Scan completed. To start a new scan, send /sqlmap <URL>.")

    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# Function for extracting all links from a web page
async def fetchpage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = ' '.join(context.args)  # Get URL from command arguments
    if not url:
        await update.message.reply_text("Please provide a URL to extract links from. Example: /fetchpage https://example.com")
        return

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract all links (<a> tags) from the page
        links = soup.find_all('a', href=True)

        # If links are found, send them to the user
        if links:
            links_list = "\n".join([link['href'] for link in links])
            await update.message.reply_text(f"Found links on the page:\n{links_list}")
        else:
            await update.message.reply_text("No links found on the page.")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"An error occurred while fetching the page: {e}")

# Основная функция для запуска бота
def main():
    telegram_token = "tgtoken"
    application = Application.builder().token(telegram_token).build()

    # обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chat", chat))
    application.add_handler(CommandHandler("code", code))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("pentest", pentest_menu))
    application.add_handler(CommandHandler("nikto", nikto_scan))
    application.add_handler(CommandHandler("sqlmap", sqlmap_scan))
    application.add_handler(CommandHandler("fetchpage", fetchpage))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))  # Chat messages without command

    application.run_polling()


if __name__ == "__main__":
    main()
