
async def sqlmap_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = ' '.join(context.args)
    if not url:
        await update.message.reply_text("Пожалуйста, укажите URL для сканирования с помощью SQLMap.")
        return

    try:
        await update.message.reply_text(f"Начинаю сканирование {url} с помощью SQLMap...")

        command = ["sqlmap", "-u", url, "--batch"]
        process = await asyncio.create_subprocess_exec(
            *command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Собираем весь вывод
        full_output = []
        while True:
            output = await process.stdout.readline()
            if output:
                output_text = output.decode().strip()
                if output_text:
                    full_output.append(output_text)
            else:
                break

        # Сохраняем вывод в файл
        with open("sqlmap_output.txt", "w") as file:
            file.write("\n".join(full_output))

        # Отправляем файл пользователю
        with open("sqlmap_output.txt", "rb") as file:
            await update.message.reply_document(document=file, caption="Результаты сканирования SQLMap")

        # Проверяем stderr
        stderr = await process.stderr.read()
        if stderr:
            stderr_text = stderr.decode().strip()
            if stderr_text:
                await update.message.reply_text(f"Ошибка: {stderr_text}")

        # Проверяем код завершения
        return_code = await process.wait()
        if return_code != 0:
            await update.message.reply_text(f"SQLMap завершился с кодом {return_code}.")

        # Уведомление о завершении
        await update.message.reply_text("Сканирование завершено. Для нового сканирования отправьте /sqlmap <URL>.")

    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")
