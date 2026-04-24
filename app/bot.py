from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord import app_commands
from discord.ext import commands, tasks

from app.apis import ApiError, PublicApiClient
from app.config import Settings
from app.database import Database


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("everyday-automation-bot")


def weather_code_label(code: int) -> str:
    mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Rain showers",
        95: "Thunderstorm",
    }
    return mapping.get(code, f"Weather code {code}")


class EverydayAutomationBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.db = Database(settings.database_path)
        self.apis = PublicApiClient()

    async def setup_hook(self) -> None:
        self._register_commands()
        await self.tree.sync()
        self.reminder_loop.start()
        logger.info("Slash commands synced.")

    async def on_ready(self) -> None:
        logger.info("Logged in as %s", self.user)

    def _register_commands(self) -> None:
        @self.tree.command(name="help", description="Show available commands and examples")
        async def help_command(interaction: discord.Interaction) -> None:
            embed = discord.Embed(
                title="Everyday Automation Bot - Help",
                description="One bot for daily info: weather, tech news, reading habits.",
                color=discord.Color.blurple(),
            )
            embed.add_field(
                name="Core",
                value=(
                    "/news [limit] - Top tech stories\n"
                    "/weather <city> - Current weather\n"
                    "/morning_brief <city> - Weather + top headlines"
                ),
                inline=False,
            )
            embed.add_field(
                name="Reading Tracker",
                value=(
                    "/read_add <pages> <book> - Log pages\n"
                    "/read_stats - View total pages and streak"
                ),
                inline=False,
            )
            embed.add_field(
                name="Reminders",
                value=(
                    "/remind_set <HH:MM> [timezone] [message] - Set daily reminder\n"
                    "/remind_off - Disable your reminder\n"
                    "/ping - Health check"
                ),
                inline=False,
            )
            embed.set_footer(text="Time format is 24-hour, e.g., 20:00 | timezone example: Africa/Lagos")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.tree.command(name="ping", description="Check bot health")
        async def ping_command(interaction: discord.Interaction) -> None:
            await interaction.response.send_message("Pong. Bot is online and responsive.")

        @self.tree.command(name="news", description="Get top Hacker News stories")
        @app_commands.describe(limit="Number of stories to fetch (1-10)")
        async def news_command(
            interaction: discord.Interaction, limit: app_commands.Range[int, 1, 10] = 5
        ) -> None:
            await interaction.response.defer(thinking=True)
            try:
                stories = await self.apis.get_top_tech_news(limit=limit)
                embed = discord.Embed(
                    title="Top Tech News",
                    description="Source: Hacker News",
                    color=discord.Color.green(),
                )
                for index, story in enumerate(stories, start=1):
                    embed.add_field(
                        name=f"{index}. {story.title}",
                        value=f"Score: {story.score} | [Open Story]({story.url})",
                        inline=False,
                    )
                await interaction.followup.send(embed=embed)
            except ApiError as exc:
                await interaction.followup.send(
                    f"Could not fetch news right now: {exc}", ephemeral=True
                )
            except Exception:
                logger.exception("Unexpected error in /news")
                await interaction.followup.send(
                    "Unexpected error while fetching news. Please try again shortly.",
                    ephemeral=True,
                )

        @self.tree.command(name="weather", description="Get weather for a city")
        @app_commands.describe(city="City name, e.g. Lagos")
        async def weather_command(interaction: discord.Interaction, city: str) -> None:
            await interaction.response.defer(thinking=True)
            try:
                report = await self.apis.get_weather(city=city)
                embed = discord.Embed(
                    title=f"Weather in {report.city}",
                    color=discord.Color.blue(),
                )
                embed.add_field(name="Condition", value=weather_code_label(report.weather_code))
                embed.add_field(name="Temp", value=f"{report.temperature_c:.1f} C")
                embed.add_field(name="Wind", value=f"{report.wind_kmh:.1f} km/h")
                embed.add_field(name="High", value=f"{report.temp_max_c:.1f} C")
                embed.add_field(name="Low", value=f"{report.temp_min_c:.1f} C")
                embed.set_footer(text="Source: Open-Meteo | Times in UTC")
                await interaction.followup.send(embed=embed)
            except ApiError as exc:
                await interaction.followup.send(
                    f"Could not fetch weather: {exc}", ephemeral=True
                )
            except Exception:
                logger.exception("Unexpected error in /weather")
                await interaction.followup.send(
                    "Unexpected error while fetching weather. Please try again.",
                    ephemeral=True,
                )

        @self.tree.command(name="read_add", description="Log your reading progress")
        @app_commands.describe(pages="Pages read today", book="Book title")
        async def read_add_command(
            interaction: discord.Interaction,
            pages: app_commands.Range[int, 1, 5000],
            book: app_commands.Range[str, 1, 120],
        ) -> None:
            try:
                self.db.add_reading_log(str(interaction.user.id), book.strip(), int(pages))
                stats = self.db.get_reading_stats(str(interaction.user.id))
                await interaction.response.send_message(
                    (
                        f"Logged {pages} pages for **{book}**.\n"
                        f"Total pages: **{stats.total_pages}** | Streak: **{stats.streak_days}** day(s)"
                    )
                )
            except Exception:
                logger.exception("Unexpected error in /read_add")
                await interaction.response.send_message(
                    "Could not save reading progress right now. Please try again.",
                    ephemeral=True,
                )

        @self.tree.command(name="read_stats", description="Show your reading stats")
        async def read_stats_command(interaction: discord.Interaction) -> None:
            try:
                stats = self.db.get_reading_stats(str(interaction.user.id))
                if stats.total_entries == 0:
                    await interaction.response.send_message(
                        "No reading logs yet. Start with /read_add pages:<n> book:<title>",
                        ephemeral=True,
                    )
                    return

                embed = discord.Embed(
                    title="Your Reading Progress",
                    color=discord.Color.orange(),
                )
                embed.add_field(name="Total pages", value=str(stats.total_pages))
                embed.add_field(name="Entries", value=str(stats.total_entries))
                embed.add_field(name="Pages today", value=str(stats.pages_today))
                embed.add_field(name="Streak", value=f"{stats.streak_days} day(s)")
                embed.add_field(name="Current book", value=stats.current_book or "Unknown", inline=False)
                await interaction.response.send_message(embed=embed)
            except Exception:
                logger.exception("Unexpected error in /read_stats")
                await interaction.response.send_message(
                    "Could not retrieve reading stats right now.",
                    ephemeral=True,
                )

        @self.tree.command(name="remind_set", description="Set your daily reading reminder")
        @app_commands.describe(
            time_local="Reminder time HH:MM (24h)",
            timezone_name="IANA timezone, e.g. Africa/Lagos (default: UTC)",
            message="Optional reminder text",
        )
        async def remind_set_command(
            interaction: discord.Interaction,
            time_local: str,
            timezone_name: str = "UTC",
            message: app_commands.Range[str, 1, 180] = "Time to log your reading progress.",
        ) -> None:
            parsed_time = _validate_hhmm(time_local)
            if not parsed_time:
                await interaction.response.send_message(
                    "Invalid time format. Use HH:MM in 24-hour format, e.g., 20:30.",
                    ephemeral=True,
                )
                return

            tz = _validate_timezone(timezone_name)
            if tz is None:
                await interaction.response.send_message(
                    "Invalid timezone. Use an IANA timezone like Africa/Lagos, Europe/London, or UTC.",
                    ephemeral=True,
                )
                return

            self.db.set_reminder(
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel_id),
                time_local=parsed_time,
                timezone=tz,
                message=message,
            )
            await interaction.response.send_message(
                f"Reminder saved for {parsed_time} in timezone {tz} each day."
            )

        @self.tree.command(name="remind_off", description="Disable your daily reminder")
        async def remind_off_command(interaction: discord.Interaction) -> None:
            removed = self.db.clear_reminder(str(interaction.user.id))
            if removed:
                await interaction.response.send_message("Your daily reminder has been disabled.")
            else:
                await interaction.response.send_message(
                    "You do not have an active reminder yet.",
                    ephemeral=True,
                )

        @self.tree.command(name="morning_brief", description="Get weather + headlines in one response")
        @app_commands.describe(city="City name for weather")
        async def morning_brief_command(interaction: discord.Interaction, city: str) -> None:
            await interaction.response.defer(thinking=True)
            try:
                weather_task = self.apis.get_weather(city=city)
                news_task = self.apis.get_top_tech_news(limit=3)
                weather, stories = await asyncio.gather(weather_task, news_task)

                embed = discord.Embed(
                    title="Your Morning Brief",
                    description=f"{weather.city} | {weather_code_label(weather.weather_code)}",
                    color=discord.Color.teal(),
                )
                embed.add_field(
                    name="Weather",
                    value=(
                        f"Temp: {weather.temperature_c:.1f} C\n"
                        f"High/Low: {weather.temp_max_c:.1f} C / {weather.temp_min_c:.1f} C"
                    ),
                    inline=False,
                )
                headlines = "\n".join(
                    [f"{idx}. [{s.title}]({s.url})" for idx, s in enumerate(stories, start=1)]
                )
                embed.add_field(name="Top Tech Headlines", value=headlines or "No headlines", inline=False)
                embed.set_footer(text="Sources: Open-Meteo + Hacker News")
                await interaction.followup.send(embed=embed)
            except ApiError as exc:
                await interaction.followup.send(f"Could not build brief: {exc}", ephemeral=True)
            except Exception:
                logger.exception("Unexpected error in /morning_brief")
                await interaction.followup.send(
                    "Unexpected error while building brief. Please try again.",
                    ephemeral=True,
                )

    @tasks.loop(minutes=1)
    async def reminder_loop(self) -> None:
        now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        rows = self.db.get_all_reminders()
        if not rows:
            return

        for row in rows:
            tz_name = row["timezone"] or "UTC"
            try:
                tz = ZoneInfo(tz_name)
            except ZoneInfoNotFoundError:
                tz = ZoneInfo("UTC")

            now_local = now_utc.astimezone(tz)
            due_hhmm = now_local.strftime("%H:%M")
            due_date = now_local.date().isoformat()

            if row["time_local"] != due_hhmm:
                continue
            if row["last_sent_date"] == due_date:
                continue

            channel = self.get_channel(int(row["channel_id"]))
            if channel is None:
                self.db.mark_reminder_sent(str(row["user_id"]), due_date)
                continue

            text = f"<@{row['user_id']}> {row['message']}"
            try:
                await channel.send(text)
                self.db.mark_reminder_sent(str(row["user_id"]), due_date)
            except Exception:
                logger.exception("Failed to send reminder for user %s", row["user_id"])

    @reminder_loop.before_loop
    async def before_reminder_loop(self) -> None:
        await self.wait_until_ready()


def _validate_hhmm(raw: str) -> str | None:
    text = raw.strip()
    try:
        parsed = datetime.strptime(text, "%H:%M")
        return parsed.strftime("%H:%M")
    except ValueError:
        return None


def _validate_timezone(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    try:
        ZoneInfo(text)
        return text
    except ZoneInfoNotFoundError:
        return None


def run_bot() -> None:
    settings = Settings.from_env()
    bot = EverydayAutomationBot(settings)
    bot.run(settings.discord_token)
